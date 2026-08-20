from __future__ import annotations
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]   # src/devagent/config.py -> repo root
load_dotenv(PROJECT_ROOT / ".env")                 # populates os.environ for everything downstream

@dataclass(frozen=True)
class Settings:
    github_token: str
    target_repo: str                                  # "owner/name"
    model: str
    max_turns: int
    test_cmd: str
    lint_cmd: str
    max_changed_lines: int
    protected_paths: tuple[str, ...] = (
        ".github/", ".git/", ".env", "Dockerfile", "docker-compose",
    )
    runs_dir: Path = PROJECT_ROOT / "runs"

def load_settings() -> Settings:
    missing = [k for k in ("ANTHROPIC_API_KEY", "GITHUB_TOKEN", "TARGET_REPO")
               if not os.getenv(k)]
    if missing:
        raise SystemExit(
            f"Missing enviroment variable : {', '.join (missing)}."
            "Copy .env.example to .env and fill them in."
        )
    return Settings(
        github_token=os.environ["GITHUB_TOKEN"],
        target_repo=os.environ["TARGET_REPO"],
        model=os.getenv("DEVAGENT_MODEL", "claude-sonnet-5"),
        max_turns=int(os.getenv("DEVAGENT_MAX_TURNS", "60")),
        test_cmd=os.getenv("DEVAGENT_TEST_CMD", "python -m pytest -x -q"),
        lint_cmd=os.getenv("DEVAGENT_LINT_CMD", ""),
        max_changed_lines=int(os.getenv("DEVAGENT_MAX_CHANGED_LINES", "500"))
    ) 
