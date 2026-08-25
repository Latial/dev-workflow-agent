"""Deterministic gates between 'the agent claims done' and 'a PR exists'."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass

from devagent.config import Settings
from devagent.workspace import Workspace

@dataclass
class GateResult:
    name : str
    passed : bool
    detail : str = ""

def run_gates(ws : Workspace, settings: Settings) -> tuple[list[GateResult], bool]:
    gates: list[GateResult] = []
    repo = ws.repo_dir

    # Gate 0 - did the agent invoke its escape hatch?
    blocked = (repo / "BLOCKED.md").exists()
    gates.append(GateResult(
        "agent_not_blocked", not blocked,
        "agent wrote BLOCKED.md - read it; no PR will be opened" if blocked else "",
    ))
    if blocked:
        return gates, False

    # Gate 1 - real code changes exist (SOLUTION.md alone is not a fix)
    code_changes = ws.code_changed_files()
    gates.append(GateResult("changes_exist", bool(code_changes),
                            f"{len(code_changes)} files changed"))   
    
    # Gate 2 - nothing in the blast-radius denylist was touched
    touched = [f for f in code_changes
               for p in settings.protected_paths if f.startswith(p)]
    gates.append(GateResult("protected_paths_untouched", not touched,
                            f"touched : {touched}" if touched else ""))

    # Gate 3 — the output contract was honored
    gates.append(GateResult("solution_note_exists", (repo / "SOLUTION.md").exists()))

    # Gate 4 — the diff is reviewable, not a rewrite  
    lines = ws.diff_line_count()
    gates.append(GateResult("diff_size_sane", lines <= settings.max_changed_lines,
                            f"{lines} changed lines (max {settings.max_changed_lines})"))

    # Gate 5 — trust, but verify: OUR OWN test run, independent of any claim
    try:
        proc = subprocess.run(settings.test_cmd, shell= True, cwd=repo,
                              capture_output=True, text=True, timeout=900)
        gates.append(GateResult("tests_pass", proc.returncode == 0,
                                "" if proc.returncode == 0
                                else (proc.stdout + proc.stderr)[-1500:]))
    except subprocess.TimeoutExpired:
        gates.append(GateResult("tests_pass", False, "test run timed out"))

    return gates, all(g.passed for g in gates) 