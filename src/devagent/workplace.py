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
    
    # ---- state inspection ------------------------------------------------
    def changed_files(self) -> list[str]:
        out = self._git("status", "--porcelain").stdout
        return [line[3:].strip() for line in out.splitlines() if line.strip()]

    def code_changed_files(self) -> list[str]:
        return [f for f in self.changed_files() if f not in self.NOTE_FILES]

    def _stage_all(self) -> None:
        self._git("add", "-A", check=False)

    def diff_line_count(self) -> int:
        self._stage_all()
        out = self._git("diff", "--cached", "--numstat").stdout
        total = 0
        for line in out.splitlines():
            added, deleted, *_ = line.split("\t")
            if added != "":
                total += int(added) + int(deleted)
        return total

    def diff_text(self, limit :int = 40_000) -> str:
        self._stage_all()
        return self._git("diff", "--cached").stdout[:limit]
    
    # ---- publishing ------------------------------------------------------ 
    def commit_all(self, message:str) -> None:
        self._stage_all()
        self._git(
            "-c" , "user.name=Dev-Worlflow-Agent",
            "-c", "user.email=devagent@users.noreply.github.com",
            "commit", "-m", message,
        ) 
    def push(self) -> None:
        assert self.branch, "create_branch() must run first"
        self._git("push", "-u", "origin", self.branch)
    