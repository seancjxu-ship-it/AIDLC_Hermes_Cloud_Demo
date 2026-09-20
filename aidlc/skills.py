from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from aidlc.settings import settings


@dataclass(frozen=True)
class Skill:
    name: str
    path: Path
    source: str
    content: str


STAGE_SKILLS = {
    "REQUIREMENT": ["openspec-explore", "openspec-propose"],
    "PLAN": ["openspec-propose", "aidlc-orchestration"],
    "DEVELOPMENT": ["openspec-apply-change", "aidlc-python-development"],
    "TESTING": ["aidlc-test-execution"],
    "REVIEW": ["aidlc-code-review", "aidlc-security-review"],
    "DEPLOYMENT": ["aidlc-swr-delivery"],
    "EVIDENCE": ["aidlc-evidence-collector"],
}


def discover_skills(root: Path | None = None) -> dict[str, Skill]:
    base = (root or settings.root) / ".hermes" / "skills"
    result: dict[str, Skill] = {}
    if not base.exists():
        return result
    for path in sorted(base.glob("*/SKILL.md")):
        name = path.parent.name
        result[name] = Skill(
            name=name,
            path=path,
            source="OpenSpec official" if name.startswith("openspec-") else "AIDLC platform",
            content=path.read_text(encoding="utf-8"),
        )
    return result


def load_skill_context(names: list[str], root: Path | None = None) -> str:
    catalog = discover_skills(root)
    missing = [name for name in names if name not in catalog]
    if missing:
        raise KeyError(f"Unregistered skills: {', '.join(missing)}")
    return "\n\n".join(
        f"## SKILL: {catalog[name].name}\n{catalog[name].content}" for name in names
    )


def architecture_payload() -> dict:
    catalog = discover_skills()
    return {
        "name": "AI-DLC Software Factory",
        "version": "3.0",
        "execution_region": "Huawei Cloud sa-brazil-1",
        "model_region": "Huawei Cloud ap-southeast-1",
        "model": settings.maas_model,
        "components": [
            "Customer UI / API", "Hermes Orchestrator", "Dev Worker", "QA Worker",
            "Review Worker", "Deploy Worker", "Huawei Cloud DCS Redis",
            "Huawei Cloud SWR", "GitHub Pull Request",
        ],
        "stage_skills": STAGE_SKILLS,
        "skills": [
            {"name": skill.name, "source": skill.source, "path": str(skill.path.relative_to(settings.root))}
            for skill in catalog.values()
        ],
    }

