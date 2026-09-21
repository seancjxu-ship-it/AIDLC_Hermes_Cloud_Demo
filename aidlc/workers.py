from __future__ import annotations

import ast
import json
import os
import re
import shutil
import time
from pathlib import Path
from typing import Any

import httpx

from aidlc.gitops import clone_repository, create_pull_request, push_branch, run_command
from aidlc.kubernetes import KubernetesClient, build_job_manifest, preview_manifests, resource_name
from aidlc.maas import MaaSClient
from aidlc.models import AgentTask, TaskResult
from aidlc.settings import settings
from aidlc.skills import load_skill_context


FALLBACK_SOURCE = '''"""Tiny order service used by the AIDLC demo."""


class OrderService:
    def __init__(self) -> None:
        self.orders = {"ORDER-1001": {"status": "PAID"}}
        self.audit_events: list[dict[str, str]] = []
        self.replay_cache: dict[str, dict[str, str]] = {}

    def cancel_order(self, order_id: str, idempotency_key: str) -> dict[str, str]:
        if not idempotency_key:
            raise ValueError("IDEMPOTENCY_KEY_REQUIRED")
        cache_key = f"{order_id}:{idempotency_key}"
        replay = self.replay_cache.get(cache_key)
        if replay is not None:
            return replay
        order = self.orders.get(order_id)
        if order is None:
            raise ValueError("ORDER_NOT_FOUND")
        if order["status"] == "CANCELLED":
            raise ValueError("ORDER_ALREADY_CANCELLED")
        order["status"] = "CANCELLED"
        result = {"order_id": order_id, "status": "CANCELLED"}
        self.replay_cache[cache_key] = result
        self.audit_events.append({"event": "ORDER_CANCELLED", "order_id": order_id})
        return result
'''


DEMO_DOCKERFILE = """FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

WORKDIR /app
COPY src ./src
COPY app.py .
RUN useradd --system --uid 10001 --create-home appuser \
    && chown -R appuser:appuser /app
USER 10001
EXPOSE 8080
CMD ["python", "app.py"]
"""


DEMO_APP = '''"""Minimal HTTP runtime for the AIDLC order-service preview."""

from __future__ import annotations

import json
import os
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from src.order_service import OrderService


SERVICE = OrderService()


class Handler(BaseHTTPRequestHandler):
    def send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/health":
            self.send_json(200, {
                "status": "ok",
                "service": "simple-order-demo",
                "run_id": os.getenv("AIDLC_RUN_ID", "local"),
                "commit": os.getenv("AIDLC_COMMIT_SHA", "local"),
            })
            return
        self.send_json(404, {"error": "NOT_FOUND"})

    def do_POST(self) -> None:
        match = re.fullmatch(r"/orders/([^/]+)/cancel", self.path)
        if not match:
            self.send_json(404, {"error": "NOT_FOUND"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length) or b"{}")
            result = SERVICE.cancel_order(match.group(1), payload.get("idempotency_key", ""))
            self.send_json(200, result)
        except (ValueError, json.JSONDecodeError) as exc:
            self.send_json(400, {"error": str(exc)})

    def log_message(self, format: str, *args: object) -> None:
        return


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", int(os.getenv("PORT", "8080"))), Handler).serve_forever()
'''


def clean_python(content: str) -> str:
    text = content.strip()
    if text.startswith("```"):
        lines = text.splitlines()[1:]
        if lines and lines[-1].strip() == "```":
            lines.pop()
        text = "\n".join(lines)
    ast.parse(text)
    return text.rstrip() + "\n"


def read_if_exists(workspace: Path, relative: str) -> str:
    path = workspace / relative
    return path.read_text(encoding="utf-8") if path.exists() else ""


def quality_gate(workspace: Path) -> dict:
    return run_command(["python", "-m", "unittest", "discover", "-s", "tests", "-v"], workspace)


def prepare_workspace(task: AgentTask, branch: str | None = None) -> Path:
    workspace = settings.work_root / task.run_id / f"{task.role}-{task.task_id}"
    if workspace.exists():
        shutil.rmtree(workspace)
    clone_repository(task.payload["repository"], branch or task.payload["base_branch"], workspace)
    return workspace


def ensure_demo_container_files(workspace: Path) -> list[str]:
    added: list[str] = []
    if not settings.allow_demo_scaffold:
        return added
    files = {workspace / "Dockerfile": DEMO_DOCKERFILE, workspace / "app.py": DEMO_APP}
    for path, content in files.items():
        if not path.exists():
            path.write_text(content, encoding="utf-8")
            added.append(path.name)
    return added


def dev_task(task: AgentTask) -> TaskResult:
    workspace = prepare_workspace(task)
    source_path = workspace / "src" / "order_service.py"
    round1 = quality_gate(workspace)
    run_suffix = task.run_id.replace("-", "")[-14:]
    branch = f"aidlc/openspec-{run_suffix}"
    run_command(["git", "checkout", "-b", branch], workspace)
    skills = load_skill_context(task.skill_names)
    prompt = {
        "requirement": read_if_exists(workspace, task.payload["requirement_file"]),
        "spec": read_if_exists(workspace, "sdd/spec.md"),
        "design": read_if_exists(workspace, "sdd/design.md"),
        "tasks": read_if_exists(workspace, "sdd/tasks.yaml"),
        "current_source": source_path.read_text(encoding="utf-8"),
        "tests": read_if_exists(workspace, "tests/test_order_service.py"),
        "initial_gate": round1["stdout"] + round1["stderr"],
    }
    fallback_used = False
    model_result: dict[str, Any] = {"usage": {}, "request_id": None, "model": settings.maas_model}
    try:
        model_result = MaaSClient().complete(
            "You are the Hermes development worker. Follow the approved skills and return only the complete Python source file.\n" + skills,
            json.dumps(prompt, ensure_ascii=False),
        )
        source_path.write_text(clean_python(model_result["content"]), encoding="utf-8")
    except Exception as exc:
        if not settings.allow_fallback:
            raise
        source_path.write_text(FALLBACK_SOURCE, encoding="utf-8")
        fallback_used = True
        model_result["error"] = type(exc).__name__
    round2 = quality_gate(workspace)
    if not round2["passed"] and settings.allow_fallback and not fallback_used:
        source_path.write_text(FALLBACK_SOURCE, encoding="utf-8")
        fallback_used = True
        round2 = quality_gate(workspace)
    if not round2["passed"]:
        return TaskResult(task_id=task.task_id, run_id=task.run_id, role=task.role, passed=False,
                          summary="Deterministic test gate denied the change / 确定性测试门禁拒绝变更",
                          outputs={"round1": round1, "round2": round2})
    scaffold_files = ensure_demo_container_files(workspace)
    compile_targets = ["src", "tests", *scaffold_files]
    compile_gate = run_command(["python", "-m", "compileall", "-q", *compile_targets], workspace)
    if not compile_gate["passed"]:
        return TaskResult(
            task_id=task.task_id,
            run_id=task.run_id,
            role=task.role,
            passed=False,
            summary="Container runtime compilation failed / \u5bb9\u5668\u8fd0\u884c\u5165\u53e3\u7f16\u8bd1\u5931\u8d25",
            outputs={"round1": round1, "round2": round2, "compile": compile_gate},
        )
    run_command(["git", "config", "user.name", "AIDLC Hermes Agent"], workspace)
    run_command(["git", "config", "user.email", "aidlc-demo@local.invalid"], workspace)
    changed_files = ["src/order_service.py", *scaffold_files]
    run_command(["git", "add", *changed_files], workspace)
    commit = run_command(["git", "commit", "-m", "fix: implement approved OpenSpec change"], workspace)
    if not commit["passed"]:
        raise RuntimeError(commit["stderr"] or commit["stdout"])
    commit_sha = run_command(["git", "rev-parse", "HEAD"], workspace)["stdout"].strip()
    pushed = False
    if task.payload.get("execution_mode") == "live" and settings.github_write:
        push_branch(workspace, branch)
        pushed = True
    return TaskResult(
        task_id=task.task_id, run_id=task.run_id, role=task.role, passed=True,
        summary="Code implemented and deterministic gate passed / 代码已实现且通过确定性门禁",
        outputs={
            "branch": branch, "commit": commit_sha, "pushed": pushed,
            "round1": round1, "round2": round2, "fallback_used": fallback_used,
            "changed_files": changed_files, "container_scaffold_added": scaffold_files,
            "model": {k: v for k, v in model_result.items() if k != "content"},
            "updated_source": source_path.read_text(encoding="utf-8"),
        },
    )


def qa_task(task: AgentTask) -> TaskResult:
    branch = task.payload.get("branch") if task.payload.get("pushed") else None
    workspace = prepare_workspace(task, branch)
    if not branch and task.payload.get("updated_source"):
        (workspace / "src" / "order_service.py").write_text(task.payload["updated_source"], encoding="utf-8")
    gate = quality_gate(workspace)
    return TaskResult(
        task_id=task.task_id, run_id=task.run_id, role=task.role, passed=gate["passed"],
        summary="QA gate passed / QA 门禁通过" if gate["passed"] else "QA gate denied / QA 门禁拒绝",
        outputs={"gate": gate},
    )


def review_task(task: AgentTask) -> TaskResult:
    branch = task.payload.get("branch") if task.payload.get("pushed") else None
    workspace = prepare_workspace(task, branch)
    if not branch and task.payload.get("updated_source"):
        (workspace / "src" / "order_service.py").write_text(task.payload["updated_source"], encoding="utf-8")
    compile_targets = ["src", "tests"] + (["app.py"] if (workspace / "app.py").exists() else [])
    compile_check = run_command(["python", "-m", "compileall", "-q", *compile_targets], workspace)
    source = (workspace / "src" / "order_service.py").read_text(encoding="utf-8")
    secret_patterns = [r"ghp_[A-Za-z0-9]{20,}", r"AKIA[A-Z0-9]{16}", r"(?i)password\s*=\s*['\"][^'\"]+"]
    secret_hits = [pattern for pattern in secret_patterns if re.search(pattern, source)]
    model_review: dict[str, Any] = {}
    try:
        model_review = MaaSClient().complete(
            "You are a concise secure code reviewer. Return a short JSON review with risks and recommendation.\n" + load_skill_context(task.skill_names),
            source,
        )
        model_review.pop("content", None)
    except Exception as exc:
        model_review = {"error": type(exc).__name__}
    passed = compile_check["passed"] and not secret_hits
    return TaskResult(
        task_id=task.task_id, run_id=task.run_id, role=task.role, passed=passed,
        summary="Review and security gates passed / 评审与安全门禁通过" if passed else "Review gate denied / 评审门禁拒绝",
        outputs={"compile": compile_check, "secret_hits": secret_hits, "model_review": model_review},
    )


def planned_deploy_task(task: AgentTask) -> TaskResult:
    commit = task.payload.get("commit", "unknown")
    digest = hashlib.sha256(f"{task.run_id}:{commit}".encode()).hexdigest()
    image = f"{settings.swr_image_repo}:{commit[:12]}" if settings.swr_image_repo else "SWR_NOT_CONFIGURED"
    manifest = {
        "image": image,
        "content_digest": f"sha256:{digest}",
        "runtime": "Huawei Cloud CCE",
        "delivery_worker": "hermes-sf-deploy",
        "build_policy": "immutable commit tag; no latest tag",
    }
    return TaskResult(
        task_id=task.task_id, run_id=task.run_id, role=task.role, passed=bool(settings.swr_image_repo),
        summary="SWR delivery manifest created / 已生成 SWR 交付清单",
        outputs={"manifest": manifest},
    )


def delivery_event(
    task: AgentTask,
    stage: str,
    detail: str,
    result: str = "RUNNING",
    metadata: dict[str, Any] | None = None,
) -> None:
    from aidlc.bus import RedisBus

    RedisBus().event(task.run_id, stage, "hermes-sf-deploy", detail, result, metadata)


def smoke_preview(service_url: str, run_id: str, commit: str) -> dict[str, Any]:
    health_response: dict[str, Any] | None = None
    last_error = ""
    for _ in range(25):
        try:
            response = httpx.get(f"{service_url}/health", timeout=5)
            response.raise_for_status()
            health_response = response.json()
            if health_response.get("status") == "ok":
                break
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
        time.sleep(2)
    if not health_response or health_response.get("status") != "ok":
        raise RuntimeError(f"Preview health check failed: {last_error or health_response}")
    if health_response.get("run_id") != run_id or health_response.get("commit") != commit:
        raise RuntimeError(f"Preview provenance mismatch: {health_response}")

    idempotency_key = f"smoke-{run_id}"
    response = httpx.post(
        f"{service_url}/orders/ORDER-1001/cancel",
        json={"idempotency_key": idempotency_key},
        timeout=10,
    )
    response.raise_for_status()
    functional_response = response.json()
    if functional_response.get("status") != "CANCELLED":
        raise RuntimeError(f"Functional smoke test failed: {functional_response}")
    replay = httpx.post(
        f"{service_url}/orders/ORDER-1001/cancel",
        json={"idempotency_key": idempotency_key},
        timeout=10,
    )
    replay.raise_for_status()
    if replay.json() != functional_response:
        raise RuntimeError("Idempotency smoke test returned a different replay response")
    return {
        "passed": True,
        "health": health_response,
        "functional": functional_response,
        "idempotency_replay": "PASS",
    }


def deploy_task(task: AgentTask) -> TaskResult:
    commit = task.payload.get("commit", "")
    branch = task.payload.get("branch", "")
    if task.payload.get("execution_mode") != "live":
        return planned_deploy_task(task)
    if not (settings.swr_image_repo and commit and branch and task.payload.get("pushed")):
        return TaskResult(
            task_id=task.task_id,
            run_id=task.run_id,
            role=task.role,
            passed=False,
            summary="Live delivery prerequisites are missing / \u5b9e\u65f6\u4ea4\u4ed8\u524d\u7f6e\u6761\u4ef6\u7f3a\u5931",
            outputs={"required": ["SWR_IMAGE_REPO", "commit", "branch", "pushed=true"]},
        )

    namespace = settings.kubernetes_namespace
    image_tag = commit[:12]
    image = f"{settings.swr_image_repo}:{image_tag}"
    client = KubernetesClient(namespace)
    client.cleanup_build_jobs()
    build_manifest = build_job_manifest(
        namespace=namespace,
        run_id=task.run_id,
        repository=task.payload["repository"],
        branch=branch,
        image=image,
        runtime_image=settings.runtime_image,
        kaniko_image=settings.kaniko_image,
        pull_secret=settings.image_pull_secret,
        timeout=settings.build_timeout,
    )
    job_name = build_manifest["metadata"]["name"]
    delivery_event(
        task,
        "IMAGE_BUILD",
        f"Kaniko build started from {branch}@{commit[:12]} / Kaniko \u5df2\u5f00\u59cb\u6784\u5efa",
        "START",
        {"task_id": task.task_id, "job": job_name, "image": image, "commit": commit},
    )
    build_started = time.perf_counter()
    job_created = False
    try:
        client.create(f"/apis/batch/v1/namespaces/{namespace}/jobs", build_manifest)
        job_created = True
        build = client.wait_for_job(job_name, settings.build_timeout)
    finally:
        if job_created:
            client.delete_job(job_name)
    build_seconds = round(time.perf_counter() - build_started, 2)
    digest = build.get("digest", "").strip()
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
        matches = re.findall(r"sha256:[0-9a-f]{64}", build.get("logs", ""))
        digest = matches[-1] if matches else ""
    if not digest:
        raise RuntimeError("Kaniko completed but no registry image digest was returned")
    immutable_image = f"{settings.swr_image_repo}@{digest}"
    delivery_event(
        task,
        "SWR_PUSH",
        f"Image pushed to Huawei Cloud SWR: {image} / \u955c\u50cf\u5df2\u63a8\u9001\u81f3\u534e\u4e3a\u4e91 SWR",
        "PASS",
        {"task_id": task.task_id, "job": job_name, "build_pod": build["pod"], "digest": digest, "duration_seconds": build_seconds},
    )

    deployment, service = preview_manifests(
        namespace=namespace,
        run_id=task.run_id,
        image=immutable_image,
        commit=commit,
        pull_secret=settings.image_pull_secret,
        port=settings.preview_port,
    )
    preview_name = deployment["metadata"]["name"]
    delivery_event(
        task,
        "CCE_DEPLOY",
        f"Creating CCE preview deployment {preview_name} / \u6b63\u5728\u521b\u5efa CCE \u9884\u89c8\u73af\u5883",
        "START",
        {"task_id": task.task_id, "deployment": preview_name, "namespace": namespace, "image": immutable_image},
    )
    try:
        client.create(f"/api/v1/namespaces/{namespace}/services", service)
        client.create(f"/apis/apps/v1/namespaces/{namespace}/deployments", deployment)
        rollout_started = time.perf_counter()
        rollout = client.wait_for_deployment(preview_name, settings.deploy_timeout)
        rollout_seconds = round(time.perf_counter() - rollout_started, 2)
        delivery_event(
            task,
            "CCE_ROLLOUT",
            f"Preview pod is Ready: {rollout['pod']} / \u9884\u89c8 Pod \u5df2\u5c31\u7eea",
            "PASS",
            {"task_id": task.task_id, "deployment": preview_name, "pod": rollout["pod"], "duration_seconds": rollout_seconds},
        )

        service_url = f"http://{preview_name}.{namespace}.svc.cluster.local:{settings.preview_port}"
        delivery_event(
            task,
            "SMOKE_TEST",
            "Running health, functional and idempotency smoke tests / \u6267\u884c\u5065\u5eb7\u3001\u529f\u80fd\u4e0e\u5e42\u7b49\u5192\u70df\u6d4b\u8bd5",
            "START",
            {"task_id": task.task_id, "service": preview_name},
        )
        smoke = smoke_preview(service_url, task.run_id, commit)
        delivery_event(
            task,
            "SMOKE_TEST",
            "Preview smoke tests passed / \u9884\u89c8\u73af\u5883\u5192\u70df\u6d4b\u8bd5\u901a\u8fc7",
            "PASS",
            {"task_id": task.task_id, "health_status": 200, "functional_status": "CANCELLED", "idempotency": "PASS"},
        )
    except Exception:
        client.delete_deployment(preview_name)
        client.delete_service(preview_name)
        raise

    removed_previews = client.prune_previews(settings.preview_retention, preview_name)
    if removed_previews:
        delivery_event(
            task,
            "CCE_RETENTION",
            "Old preview environments removed / \u5df2\u6e05\u7406\u8fc7\u671f\u9884\u89c8\u73af\u5883",
            "PASS",
            {"task_id": task.task_id, "removed": removed_previews, "retention": settings.preview_retention},
        )

    delivery = {
        "mode": "real",
        "source": {"repository": task.payload["repository"], "branch": branch, "commit": commit},
        "build": {
            "engine": "Kaniko on Huawei Cloud CCE",
            "job": job_name,
            "pod": build["pod"],
            "duration_seconds": build_seconds,
            "log_tail": build.get("logs", "")[-4000:],
        },
        "registry": {
            "provider": "Huawei Cloud SWR",
            "repository": settings.swr_image_repo,
            "tag": image_tag,
            "image": image,
            "digest": digest,
            "immutable_image": immutable_image,
        },
        "runtime": {
            "provider": "Huawei Cloud CCE",
            "namespace": namespace,
            "deployment": preview_name,
            "service": preview_name,
            "pod": rollout["pod"],
            "pod_ip": rollout["pod_ip"],
            "image_id": rollout["image_id"],
            "available_replicas": rollout["available_replicas"],
            "rollout_seconds": rollout_seconds,
            "internal_url": service_url,
            "preview_path": f"/preview/{task.run_id}/health",
            "retention": settings.preview_retention,
            "removed_previews": removed_previews,
        },
        "smoke_test": smoke,
    }
    manifest = {
        "image": image,
        "content_digest": digest,
        "immutable_image": immutable_image,
        "runtime": "Huawei Cloud CCE",
        "deployment": preview_name,
        "pod": rollout["pod"],
        "smoke_test": "PASS",
        "build_policy": "immutable commit tag and registry digest; no latest tag",
    }
    return TaskResult(
        task_id=task.task_id,
        run_id=task.run_id,
        role=task.role,
        passed=True,
        summary="Image built, pushed to SWR, deployed to CCE and verified / \u955c\u50cf\u5df2\u6784\u5efa\u3001\u63a8\u9001 SWR\u3001\u90e8\u7f72 CCE \u5e76\u5b8c\u6210\u9a8c\u8bc1",
        outputs={"manifest": manifest, "delivery": delivery},
    )


HANDLERS = {"dev": dev_task, "qa": qa_task, "review": review_task, "deploy": deploy_task}


def run_worker(role: str) -> None:
    from aidlc.bus import wait_for_redis

    if role not in HANDLERS:
        raise ValueError(f"Unknown worker role: {role}")
    bus = wait_for_redis()
    while True:
        task = bus.next_task(role)
        if task is None:
            continue
        started = time.perf_counter()
        bus.event(
            task.run_id,
            task.stage,
            f"hermes-sf-{role}",
            f"Task {task.task_id} started; loaded skills: {', '.join(task.skill_names)} / 任务开始并加载 Skills",
            "START",
            {"task_id": task.task_id, "skills": task.skill_names},
        )
        try:
            result = HANDLERS[role](task)
        except Exception as exc:
            result = TaskResult(
                task_id=task.task_id, run_id=task.run_id, role=role, passed=False,
                summary=f"{type(exc).__name__}: {exc}", outputs={},
            )
        bus.complete_task(result)
        bus.event(
            task.run_id,
            task.stage,
            f"hermes-sf-{role}",
            result.summary,
            "PASS" if result.passed else "DENY",
            {"task_id": task.task_id, "duration_ms": round((time.perf_counter() - started) * 1000)},
        )
        time.sleep(0.1)
