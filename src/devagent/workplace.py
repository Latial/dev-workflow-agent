import re
import subprocess
from pathlib import Path

class Workspace:
    NOTE_FILES = ("SOLUTIONS.md", "BLOCKED.md") #agent delivarables, never committed

    def __init__(self, runs_dir: Path, run_id : str, repo: str, token : str):
        self.root = runs_dir / run_id
        self.repo_dir = self.root / "repo"
        self.repo = repo
        self._token = token
        self.branch : str | None = None

    # ---- internals -------------------------------------------------------
    def _git(self, *args : str, check: bool = True) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["git", *args], cwd = self.repo_dir, check = check,
            capture_output= True, text = True, timeout=300,
        )

    @property
    def _remote_url(self) -> str:
        return f"https://x-access-token:{self._token}@github.com/{self.repo}.git"

    # ---- lifecycle -------------------------------------------------------