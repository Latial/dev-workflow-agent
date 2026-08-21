import re
import subprocess
from pathlib import Path

class Workspace:
    NOTE_FILES = ("SOLUTION.md", "BLOCKED.md") #agent delivarables, never committed

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
    def clone(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["git", "clone", self._remote_url, str(self.repo_dir)],
            check=True, capture_output=True, text=True, timeout=600,
        )
    def create_branch(self, issue_number : int, title : str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:40]
        self.branch = f"agent/issue-{issue_number}-{slug}"
        self._git("checkout", "-b", self.branch)
        return self.branch