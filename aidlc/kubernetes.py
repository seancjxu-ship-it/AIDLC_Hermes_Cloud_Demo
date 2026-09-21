from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass
from typing import Any

import httpx


SERVICE_ACCOUNT = "/var/run/secrets/kubernetes.io/serviceaccount"


def resource_name(prefix: str, run_id: str) -> str:
    suffix = re.sub(r"[^a-z0-9-]", "-", run_id.lower()).strip("-")[-20:]
    return f"{prefix}-{suffix}"[:63].rstrip("-")


@dataclass
class KubernetesClient:
    namespace: str

    def __post_init__(self) -> None:
        host = os.getenv("KUBERNETES_SERVICE_HOST")
        port = os.getenv("KUBERNETES_SERVICE_PORT_HTTPS", "443")
        if not host:
            raise RuntimeError("Kubernetes in-cluster API is unavailable")
        token = open(f"{SERVICE_ACCOUNT}/token", encoding="utf-8").read().strip()
        self.client = httpx.Client(
            base_url=f"https://{host}:{port}",
            headers={"Authorization": f"Bearer {token}"},
            verify=f"{SERVICE_ACCOUNT}/ca.crt",
            timeout=30,
        )

    def request(self, method: str, path: str, **kwargs: Any) -> Any:
        response = self.client.request(method, path, **kwargs)
        if response.status_code >= 400:
            detail = response.text[-2000:]
            raise RuntimeError(f"Kubernetes API {method} {path}: HTTP {response.status_code}: {detail}")
        if not response.content:
            return {}
        return response.json()

    def get(self, path: str, **kwargs: Any) -> Any:
        return self.request("GET", path, **kwargs)

    def create(self, path: str, body: dict[str, Any]) -> Any:
        return self.request("POST", path, json=body)

    def delete(self, path: str, *, ignore_not_found: bool = False) -> Any:
        response = self.client.request("DELETE", path)
        if response.status_code == 404 and ignore_not_found:
            return {}
        if response.status_code >= 400:
            detail = response.text[-2000:]
            raise RuntimeError(f"Kubernetes API DELETE {path}: HTTP {response.status_code}: {detail}")
        if not response.content:
            return {}
        return response.json()

    def pod_logs(self, pod: str, container: str, tail_lines: int = 160) -> str:
        response = self.client.get(
            f"/api/v1/namespaces/{self.namespace}/pods/{pod}/log",
            params={"container": container, "tailLines": tail_lines},
        )
        if response.status_code >= 400:
            return f"log unavailable: HTTP {response.status_code}"
        return response.text[-12000:]

    def list_pods(self, selector: str) -> list[dict[str, Any]]:
        data = self.get(
            f"/api/v1/namespaces/{self.namespace}/pods",
            params={"labelSelector": selector},
        )
        return data.get("items", [])

    def list_deployments(self, selector: str) -> list[dict[str, Any]]:
        data = self.get(
            f"/apis/apps/v1/namespaces/{self.namespace}/deployments",
            params={"labelSelector": selector},
        )
        return data.get("items", [])

    def list_jobs(self, selector: str) -> list[dict[str, Any]]:
        data = self.get(
            f"/apis/batch/v1/namespaces/{self.namespace}/jobs",
            params={"labelSelector": selector},
        )
        return data.get("items", [])

    def delete_job(self, name: str) -> None:
        self.delete(
            f"/apis/batch/v1/namespaces/{self.namespace}/jobs/{name}",
            ignore_not_found=True,
        )

    def delete_deployment(self, name: str) -> None:
        self.delete(
            f"/apis/apps/v1/namespaces/{self.namespace}/deployments/{name}",
            ignore_not_found=True,
        )

    def delete_service(self, name: str) -> None:
        self.delete(
            f"/api/v1/namespaces/{self.namespace}/services/{name}",
            ignore_not_found=True,
        )

    def cleanup_build_jobs(self) -> list[str]:
        removed: list[str] = []
        for job in self.list_jobs("app.kubernetes.io/name=aidlc-image-build"):
            name = job.get("metadata", {}).get("name", "")
            if name:
                self.delete_job(name)
                removed.append(name)
        return removed

    def prune_previews(self, retain: int, current_name: str) -> list[str]:
        deployments = sorted(
            self.list_deployments("app.kubernetes.io/name=aidlc-order-preview"),
            key=lambda item: (
                item.get("metadata", {}).get("creationTimestamp", ""),
                item.get("metadata", {}).get("name", ""),
            ),
            reverse=True,
        )
        keep = {current_name}
        for deployment in deployments:
            name = deployment.get("metadata", {}).get("name", "")
            if name and len(keep) < max(1, retain):
                keep.add(name)
        removed: list[str] = []
        for deployment in deployments:
            name = deployment.get("metadata", {}).get("name", "")
            if name and name not in keep:
                self.delete_deployment(name)
                self.delete_service(name)
                removed.append(name)
        return removed

    def wait_for_job(self, name: str, timeout: int) -> dict[str, Any]:
        path = f"/apis/batch/v1/namespaces/{self.namespace}/jobs/{name}"
        deadline = time.monotonic() + timeout
        last_status: dict[str, Any] = {}
        while time.monotonic() < deadline:
            job = self.get(path)
            last_status = job.get("status", {})
            pods = self.list_pods(f"job-name={name}")
            if last_status.get("succeeded", 0) >= 1:
                pod = pods[0] if pods else {}
                pod_name = pod.get("metadata", {}).get("name", "")
                digest = ""
                for item in pod.get("status", {}).get("containerStatuses", []):
                    if item.get("name") == "kaniko":
                        digest = item.get("state", {}).get("terminated", {}).get("message", "").strip()
                return {
                    "job": name,
                    "pod": pod_name,
                    "digest": digest,
                    "completion_time": last_status.get("completionTime"),
                    "logs": self.pod_logs(pod_name, "kaniko") if pod_name else "",
                }
            if last_status.get("failed", 0) >= 1:
                pod_name = pods[0].get("metadata", {}).get("name", "") if pods else ""
                logs = self.pod_logs(pod_name, "kaniko") if pod_name else ""
                raise RuntimeError(f"Image build job {name} failed: {logs[-4000:]}")
            time.sleep(3)
        raise TimeoutError(f"Image build job {name} timed out; last status={last_status}")

    def wait_for_deployment(self, name: str, timeout: int) -> dict[str, Any]:
        path = f"/apis/apps/v1/namespaces/{self.namespace}/deployments/{name}"
        deadline = time.monotonic() + timeout
        last_status: dict[str, Any] = {}
        while time.monotonic() < deadline:
            deployment = self.get(path)
            generation = deployment.get("metadata", {}).get("generation")
            last_status = deployment.get("status", {})
            if (
                last_status.get("observedGeneration") == generation
                and last_status.get("availableReplicas", 0) >= 1
                and last_status.get("updatedReplicas", 0) >= 1
            ):
                pods = self.list_pods(f"app={name}")
                pod = pods[0] if pods else {}
                image_id = ""
                for item in pod.get("status", {}).get("containerStatuses", []):
                    if item.get("name") == "order-demo":
                        image_id = item.get("imageID", "")
                return {
                    "deployment": name,
                    "pod": pod.get("metadata", {}).get("name", ""),
                    "pod_ip": pod.get("status", {}).get("podIP", ""),
                    "image_id": image_id,
                    "available_replicas": last_status.get("availableReplicas", 0),
                }
            time.sleep(3)
        pods = self.list_pods(f"app={name}")
        phases = [item.get("status", {}).get("phase") for item in pods]
        raise TimeoutError(f"Preview deployment {name} timed out; status={last_status}; pods={phases}")


def build_job_manifest(
    *,
    namespace: str,
    run_id: str,
    repository: str,
    branch: str,
    image: str,
    runtime_image: str,
    kaniko_image: str,
    pull_secret: str,
    timeout: int,
) -> dict[str, Any]:
    name = resource_name("aidlc-build", run_id)
    return {
        "apiVersion": "batch/v1",
        "kind": "Job",
        "metadata": {
            "name": name,
            "namespace": namespace,
            "labels": {"app.kubernetes.io/name": "aidlc-image-build", "aidlc.run-id": run_id},
        },
        "spec": {
            "backoffLimit": 0,
            "activeDeadlineSeconds": timeout,
            "ttlSecondsAfterFinished": 3600,
            "template": {
                "metadata": {"labels": {"app": name, "aidlc.run-id": run_id}},
                "spec": {
                    "restartPolicy": "Never",
                    "imagePullSecrets": [{"name": pull_secret}],
                    "initContainers": [{
                        "name": "git-checkout",
                        "image": runtime_image,
                        "imagePullPolicy": "IfNotPresent",
                        "command": ["git"],
                        "args": ["clone", "--depth", "1", "--branch", branch, repository, "/workspace"],
                        "env": [
                            {"name": "GIT_TERMINAL_PROMPT", "value": "0"},
                            {"name": "GIT_ASKPASS", "value": "/app/scripts/git-askpass.sh"},
                            {"name": "GITHUB_TOKEN", "valueFrom": {"secretKeyRef": {"name": "aidlc-secrets", "key": "GITHUB_TOKEN"}}},
                        ],
                        "volumeMounts": [{"name": "workspace", "mountPath": "/workspace"}],
                        "resources": {"requests": {"cpu": "25m", "memory": "32Mi"}, "limits": {"cpu": "250m", "memory": "256Mi"}},
                    }],
                    "containers": [{
                        "name": "kaniko",
                        "image": kaniko_image,
                        "args": [
                            "--context=/workspace",
                            "--dockerfile=/workspace/Dockerfile",
                            f"--destination={image}",
                            "--digest-file=/dev/termination-log",
                            "--snapshot-mode=redo",
                            "--cache=false",
                        ],
                        "volumeMounts": [
                            {"name": "workspace", "mountPath": "/workspace"},
                            {"name": "docker-config", "mountPath": "/kaniko/.docker", "readOnly": True},
                        ],
                        "resources": {"requests": {"cpu": "100m", "memory": "128Mi"}, "limits": {"cpu": "1", "memory": "1Gi"}},
                    }],
                    "volumes": [
                        {"name": "workspace", "emptyDir": {}},
                        {"name": "docker-config", "secret": {"secretName": pull_secret, "items": [{"key": ".dockerconfigjson", "path": "config.json"}]}},
                    ],
                },
            },
        },
    }


def preview_manifests(
    *,
    namespace: str,
    run_id: str,
    image: str,
    commit: str,
    pull_secret: str,
    port: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    name = resource_name("order-preview", run_id)
    labels = {"app": name, "app.kubernetes.io/name": "aidlc-order-preview", "aidlc.run-id": run_id}
    deployment = {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {"name": name, "namespace": namespace, "labels": labels},
        "spec": {
            "replicas": 1,
            "selector": {"matchLabels": {"app": name}},
            "template": {
                "metadata": {"labels": labels},
                "spec": {
                    "imagePullSecrets": [{"name": pull_secret}],
                    "securityContext": {"runAsNonRoot": True},
                    "containers": [{
                        "name": "order-demo",
                        "image": image,
                        "imagePullPolicy": "Always",
                        "ports": [{"name": "http", "containerPort": port}],
                        "env": [
                            {"name": "PORT", "value": str(port)},
                            {"name": "AIDLC_RUN_ID", "value": run_id},
                            {"name": "AIDLC_COMMIT_SHA", "value": commit},
                        ],
                        "readinessProbe": {"httpGet": {"path": "/health", "port": "http"}, "initialDelaySeconds": 2, "periodSeconds": 3},
                        "livenessProbe": {"httpGet": {"path": "/health", "port": "http"}, "initialDelaySeconds": 8, "periodSeconds": 10},
                        "resources": {"requests": {"cpu": "50m", "memory": "64Mi"}, "limits": {"cpu": "250m", "memory": "256Mi"}},
                        "securityContext": {"allowPrivilegeEscalation": False, "capabilities": {"drop": ["ALL"]}},
                    }],
                },
            },
        },
    }
    service = {
        "apiVersion": "v1",
        "kind": "Service",
        "metadata": {"name": name, "namespace": namespace, "labels": labels},
        "spec": {"selector": {"app": name}, "ports": [{"name": "http", "port": port, "targetPort": "http"}]},
    }
    return deployment, service
