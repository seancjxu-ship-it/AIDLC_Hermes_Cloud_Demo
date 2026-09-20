from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    root: Path = Path(__file__).resolve().parents[1]
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    repository_url: str = os.getenv(
        "GITHUB_REPO_URL",
        "https://github.com/seancjxu-ship-it/AIDLC_Simple_Order_Demo",
    )
    default_branch: str = os.getenv("GITHUB_DEFAULT_BRANCH", "main")
    github_write: bool = os.getenv("AIDLC_GITHUB_WRITE", "false").lower() == "true"
    maas_base_url: str = os.getenv(
        "MAAS_BASE_URL",
        "https://api-ap-southeast-1.modelarts-maas.com/openai/v1",
    )
    maas_model: str = os.getenv("MAAS_MODEL", "glm-5.2")
    swr_image_repo: str = os.getenv("SWR_IMAGE_REPO", "")
    runtime_image: str = os.getenv(
        "AIDLC_RUNTIME_IMAGE",
        "swr.sa-brazil-1.myhuaweicloud.com/aidlc-demo/aidlc-factory:3.0.0",
    )
    kubernetes_namespace: str = os.getenv("AIDLC_K8S_NAMESPACE", "aidlc-demo")
    image_pull_secret: str = os.getenv("AIDLC_IMAGE_PULL_SECRET", "swr-pull")
    kaniko_image: str = os.getenv("AIDLC_KANIKO_IMAGE", "gcr.io/kaniko-project/executor:v1.23.2-debug")
    preview_port: int = int(os.getenv("AIDLC_PREVIEW_PORT", "8080"))
    build_timeout: int = int(os.getenv("AIDLC_BUILD_TIMEOUT", "900"))
    deploy_timeout: int = int(os.getenv("AIDLC_DEPLOY_TIMEOUT", "300"))
    allow_demo_scaffold: bool = os.getenv("AIDLC_ALLOW_DEMO_SCAFFOLD", "true").lower() == "true"
    allow_fallback: bool = os.getenv("AIDLC_ALLOW_FALLBACK", "true").lower() == "true"
    work_root: Path = Path(os.getenv("AIDLC_WORK_ROOT", "/tmp/aidlc-runs"))
    task_timeout: int = int(os.getenv("AIDLC_TASK_TIMEOUT", "600"))


settings = Settings()
