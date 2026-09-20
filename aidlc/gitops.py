from __future__ import annotations

import base64
import os
import subprocess
from pathlib import Path
from urllib.parse import urlparse

import httpx


def run_command(args: list[str], cwd: Path, timeout: int = 180) -> dict:
    completed = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    return {
        "command": " ".join(args),
        "exit_code": completed.returncode,
        "stdout": completed.stdout[-16000:],
        "stderr": completed.stderr[-16000:],
        "passed": completed.returncode == 0,
    }


def git_environment() -> dict[str, str]:
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GIT_ASKPASS"] = "/app/scripts/git-askpass.sh"
    return env


def clone_repository(url: str, branch: str, destination: Path) -> dict:
    destination.parent.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(
        ["git", "clone", "--depth", "1", "--branch", branch, url, str(destination)],
        cwd=destination.parent,
        capture_output=True,
        text=True,
        timeout=180,
        env=git_environment(),
    )
    result = {
        "command": "git clone --depth 1 --branch <branch> <repository>",
        "exit_code": completed.returncode,
        "stdout": completed.stdout[-8000:],
        "stderr": completed.stderr[-8000:],
        "passed": completed.returncode == 0,
    }
    if not result["passed"]:
        raise RuntimeError(result["stderr"] or result["stdout"])
    return result


def push_branch(workspace: Path, branch: str) -> dict:
    completed = subprocess.run(
        ["git", "push", "--set-upstream", "origin", branch],
        cwd=workspace,
        capture_output=True,
        text=True,
        timeout=180,
        env=git_environment(),
    )
    result = {
        "command": "git push --set-upstream origin <feature-branch>",
        "exit_code": completed.returncode,
        "stdout": completed.stdout[-8000:],
        "stderr": completed.stderr[-8000:],
        "passed": completed.returncode == 0,
    }
    if not result["passed"]:
        raise RuntimeError(result["stderr"] or result["stdout"])
    return result


def repository_slug(repository_url: str) -> str:
    path = urlparse(repository_url).path.strip("/")
    return path[:-4] if path.endswith(".git") else path


def create_pull_request(repository_url: str, head: str, base: str, title: str, body: str) -> dict:
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        raise RuntimeError("GITHUB_TOKEN is not configured")
    slug = repository_slug(repository_url)
    response = httpx.post(
        f"https://api.github.com/repos/{slug}/pulls",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        json={"title": title, "head": head, "base": base, "body": body},
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()
    return {"number": data["number"], "url": data["html_url"], "state": data["state"]}


def basic_git_header() -> str:
    token = os.environ.get("GITHUB_TOKEN", "")
    return base64.b64encode(f"x-access-token:{token}".encode()).decode()

