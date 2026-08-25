from pathlib import Path
from devagent.workspace import Workspace

def test_branch_sluug(tmp_path: Path):
    ws = Workspace(tmp_path, "run1", "me/repo", "tok")
    ws.repo_dir.mkdir(parents=True)
    ws._git = lambda *a, **k:None
    branch = ws.create_branch(42, "Crash When cofig file is EMPTY!!")
    assert branch == "agent/issue-42-crash-when-config-file-is-empty"