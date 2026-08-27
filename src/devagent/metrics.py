from __future__ import annotations
import json

from dataclasses import asdict, dataclass
from datetime import datetime, timezone

from devagent.config import PROJECT_ROOT

RUNS_FILE = PROJECT_ROOT / "runs" / "runs.jsonl"

FAILURE_MODES = [
    "wrong-root-cause",        # fixed a symptom, not the bug
    "incomplete-fix",          # bug partially remains / edge cases missed
    "test-gamed",              # test passes but doesn't actually test the bug
    "scope-creep",             # correct fix buried in unrequested changes
    "style-violation",         # works, but doesn't match house conventions
    "hallucinated-api",        # called functions/APIs that don't exist
    "env-or-plumbing-failure", # YOUR pipeline broke, not the agent
    "blocked-wrongly",         # wrote BLOCKED.md on a solvable issue
    "other",
]

@dataclass
class RunRecord:
    run_id : str
    timestamp: str
    issue: int
    issue_title: str
    model: str
    branch: str
    pr_url: str
    agent_subtype:str
    gates: dict
    cost_usd: float | None
    num_turns: int | None
    duration_s: float
    verdict: str | None = None
    failure_mode: str | None = None
    notes: str = ""

def record(**kwargs) -> None:
    RUNS_FILE.parent.mkdir(parents=True, exist_ok=True)
    rec = RunRecord(
        timestamp=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        **kwargs,
    )
    with RUNS_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(rec)) + "\n")

def _load() -> list[dict]:
    if not RUNS_FILE.exists():
        return []
    return [json.loads(line)
            for line in RUNS_FILE.read_text(encoding="utf-8").splitlines()
            if line.strip()]

def set_verdict(run_id: str, verdict: str,
                 failure_mode: str | None, notes:str) -> None:
    rows = _load()
    matches = [r for r in rows if r["run_id"] == run_id]
    if not matches:
        raise SystemExit(f"no run with id {run_id!r} "
                         f"(known: {[r['run_id'] for r in rows][-5:]})")
    for r in matches:
        r["verdict"], r["failure_mode"], r["notes"] = verdict, failure_mode, notes
    RUNS_FILE.write_text(
        "\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8"
    )

def report() -> str:
    rows = _load()
    if not rows:
        return "No runs recorded yet."
    prs = [r for r in rows if r["pr_url"]]
    judged = [r for r in prs if r.get("verdict")]
    accepted = [r for r in judged if r["verdict"] in ("accepted", "edited")]

    lines = [f"runs: {len(rows)}  PRs opened: {len(prs)}  judged: {len(judged)}"]
    if judged:
        lines.append(
            "accepted rate (accepted + accepted-with-edits): "
            f"{len(accepted)}/{len(judged)} = {100 * len(accepted) / len(judged):.0f}%"
        )
    costs = [r["cost_usd"] for r in rows if r.get("cost_usd")]
    if costs:
        lines.append(f"costs: total ${sum(costs):.2f}, "
                     f"mean ${sum(costs) / len(costs):.2f}/run")
    modes: dict[str, int] = {}
    for r in rows:
        if r.get("failure_mode"):
            modes[r["failure_mode"]] = modes.get(r["failure_mode"], 0) + 1
    if modes:
        lines.append("failure modes: " + ", ".join(
            f"{k} x{v}" for k, v in sorted(modes.items(), key=lambda kv: -kv[1])))
    return "\n".join(lines)