from __future__ import annotations

import json
import os
import time
from typing import Any

from redis import Redis

from aidlc.models import AgentTask, TaskResult, utc_now
from aidlc.settings import settings


class RedisBus:
    def __init__(self, url: str | None = None) -> None:
        self.redis = Redis.from_url(url or settings.redis_url, decode_responses=True)

    def ping(self) -> bool:
        return bool(self.redis.ping())

    def create_run(self, run_id: str, request: dict[str, Any]) -> None:
        state = {
            "run_id": run_id,
            "status": "QUEUED",
            "request": request,
            "created_at": utc_now(),
            "updated_at": utc_now(),
            "final_decision": None,
        }
        self.redis.set(f"aidlc:run:{run_id}", json.dumps(state))
        self.event(run_id, "QUEUED", "api", "Run accepted / 运行已受理")

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        value = self.redis.get(f"aidlc:run:{run_id}")
        return json.loads(value) if value else None

    def update_run(self, run_id: str, **changes: Any) -> dict[str, Any]:
        state = self.get_run(run_id)
        if state is None:
            raise KeyError(run_id)
        state.update(changes)
        state["updated_at"] = utc_now()
        self.redis.set(f"aidlc:run:{run_id}", json.dumps(state))
        return state

    def list_runs(self, limit: int = 50) -> list[dict[str, Any]]:
        keys = list(self.redis.scan_iter("aidlc:run:*"))
        result = []
        for key in keys:
            value = self.redis.get(key)
            if value:
                result.append(json.loads(value))
        result.sort(key=lambda item: item.get("created_at", ""), reverse=True)
        return result[:limit]

    def event(
        self,
        run_id: str,
        stage: str,
        actor: str,
        detail: str,
        result: str = "OK",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        key = f"aidlc:events:{run_id}"
        event = {
            "sequence": int(self.redis.incr(f"aidlc:event-sequence:{run_id}")),
            "at": utc_now(),
            "stage": stage,
            "actor": actor,
            "pod": os.getenv("HOSTNAME", "local-process"),
            "detail": detail,
            "result": result,
        }
        if metadata:
            event["metadata"] = metadata
        self.redis.rpush(key, json.dumps(event))
        self.redis.expire(key, 86400)

    def events(self, run_id: str) -> list[dict[str, Any]]:
        return [json.loads(item) for item in self.redis.lrange(f"aidlc:events:{run_id}", 0, -1)]

    def submit_run(self, run_id: str) -> None:
        self.redis.lpush("aidlc:queue:orchestrator", run_id)

    def next_run(self, timeout: int = 5) -> str | None:
        item = self.redis.brpop("aidlc:queue:orchestrator", timeout=timeout)
        return item[1] if item else None

    def submit_task(self, task: AgentTask) -> None:
        self.redis.lpush(f"aidlc:queue:{task.role}", task.model_dump_json())

    def next_task(self, role: str, timeout: int = 5) -> AgentTask | None:
        item = self.redis.brpop(f"aidlc:queue:{role}", timeout=timeout)
        return AgentTask.model_validate_json(item[1]) if item else None

    def complete_task(self, result: TaskResult) -> None:
        key = f"aidlc:result:{result.task_id}"
        self.redis.lpush(key, result.model_dump_json())
        self.redis.expire(key, 3600)

    def wait_result(self, task_id: str, timeout: int | None = None) -> TaskResult:
        item = self.redis.brpop(f"aidlc:result:{task_id}", timeout=timeout or settings.task_timeout)
        if not item:
            raise TimeoutError(f"Agent task timed out: {task_id}")
        return TaskResult.model_validate_json(item[1])

    def save_evidence(self, run_id: str, evidence: dict[str, Any]) -> None:
        self.redis.setex(f"aidlc:evidence:{run_id}", 86400, json.dumps(evidence))

    def evidence(self, run_id: str) -> dict[str, Any] | None:
        value = self.redis.get(f"aidlc:evidence:{run_id}")
        return json.loads(value) if value else None


def wait_for_redis(max_seconds: int = 60) -> RedisBus:
    bus = RedisBus()
    deadline = time.time() + max_seconds
    while time.time() < deadline:
        try:
            if bus.ping():
                return bus
        except Exception:
            time.sleep(2)
    raise RuntimeError("Redis/DCS is not reachable")
