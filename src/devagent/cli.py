"""devagent CLI — the deterministic pipeline wrapped around the agent."""

from __future__ import annotations

import argparse
import asyncio
import dataclasses
import datetime as dt

from devagent import metrics, prompts
from devagent.agent_runner import run_agent
from devagent.config import load_settings
from devagent.github_client import GitHubClient
from devagent.validation import run_gates
from devagent.workspace import Workspace
from devagent.reviewer import run_reviewer

def cmd_run(args: argparse.Namespace) -> None:
    settings = load_settings()
    if args.model:
        settings = dataclasses.replace(settings, model=args.model)
    gh = GitHubClient(settings.github_token, settings.target_repo)
    issue = gh.get_issue(args.issue)

    run_id = dt.datetime.now().strftime("%Y%m%d-%H%M%S") + f"-i{issue.number}"
    ws = Workspace(settings.runs_dir, run_id, settings.target_repo, settings.github_token)
    print(f"[{run_id}] cloning {settings.target_repo} ...")
    ws.clone()
    branch = ws.create_branch(issue.number, issue.title)

    print(f"[{run_id}] agent started on #{issue.number} : {issue.title!r} " f"(model={settings.model})")
    result = asyncio.run(run_agent(
        repo_dir=ws.repo_dir,
        system_prompt=prompts.system_prompt(),
        task_prompt=prompts.task_prompt(issue, settings.target_repo),
        settings=settings,
        transcript_path=ws.root / "transcript.md",
    ))
    print(f"[{run_id}] agent finished: {result.subtype} " 
          f"({result.num_turns} turns, ${result.cost_usd or 0:.2f}, "
          f"{result.duration_s}s)")

    gates, ok = run_gates(ws, settings)
    for g in gates:
        print(f" gate {'PASS' if g.passed else 'FAIL'} {g.name} {g.detail}")

    (ws.root / "diff.patch").write_text(ws.diff_text(), encoding="utf-8")

    pr_url = ""
    if ok and not args.dry_run:
        solution_file = ws.repo_dir / "SOLUTION.md"
        solution = solution_file.read_text(encoding="utf-8")
        solution_file.unlink()
        ws.commit_all(f"Fix #{issue.number}: {issue.title}\n\n"
                      f"Drafted by dev-workflow-agent for human review.")
        ws.push()
        pr_url = gh.create_pr(
            head=branch,
            base=gh.default_branch(),
            title=f"Fix #{issue.number}: {issue.title}",
            body=prompts.pr_body(issue, solution, result.cost_usd, result.num_turns),
        )
        print(f"[{run_id}] draft PR opened: {pr_url}")
    elif ok:
        print(f"[{run_id}] dry run - gates passed, no PR. "
              f"Diff {ws.root / 'diff.patch'}")
    else:
        print(f"[{run_id}] no PR, Inspect {ws.root} "
              f"(transcript.md, diff.patch, BLOCKED.md if present)")

    metrics.record(
        run_id=run_id, issue=issue.number, issue_title=issue.title,
        model=settings.model, branch=branch, pr_url=pr_url,
        agent_subtype=result.subtype,
        gates={g.name : g.passed for g in gates},
        cost_usd=result.cost_usd, num_turns=result.num_turns,
        duration_s=result.duration_s,
    )
    if pr_url and args.review:
        diff = ws.diff_text()
        review = asyncio.run(run_reviewer(ws.repo_dir, issue, diff, settings))
        (ws.repo_dir / "REVIEW.md").unlink(missing_ok=True)   # keep repo clean
        (ws.root / "review.md").write_text(review, encoding="utf-8")
        gh.comment(issue.number,
                   f"**Automated review of the draft PR** ({pr_url}):\n\n{review}")
        print(f"[{run_id}] review posted "
              f"({'APPROVE' if 'Verdict: APPROVE' in review else 'CHANGES REQUESTED'})")

def cmd_verdict(args:argparse.Namespace) -> None:
    metrics.set_verdict(args.run_id, args.verdict, args.failure_mode, args.notes)
    print("recorded.")

def cmd_report(_: argparse.Namespace) -> None:
    print(metrics.report())

def cmd_issues(_:argparse.Namespace) -> None:
    settings = load_settings()
    gh = GitHubClient(settings.github_token, settings.target_repo)
    for i in gh.list_open_issues():
        print(f"#{i.number:<5} {i.title} [{', '.join(i.labels)}]")

def main() -> None:
    p = argparse.ArgumentParser(prog="devagent",
                                description="Issue -> fix -> draft PR pipeline")
    sub = p.add_subparsers(required=True)

    r = sub.add_parser("run", help="resolve one issue end-to-end")
    r.add_argument("issue", type=int)
    r.add_argument("--dry-run", action="store_true",
                   help="stop after gates; write diff, open no PR")
    r.add_argument("--model", default=None,
                   help="override model, e.g. claude-opus-5 for a hard issue")
    r.set_defaults(func=cmd_run)

    v = sub.add_parser("verdict", help="record your review of a run's PR")
    v.add_argument("run_id")
    v.add_argument("verdict", choices=["accepted", "edited", "rejected"])
    v.add_argument("--failure-mode", default=None, choices=metrics.FAILURE_MODES)
    v.add_argument("--notes", default="")
    v.set_defaults(func=cmd_verdict)

    sub.add_parser("report", help="acceptance rate, costs, failure modes") \
        .set_defaults(func=cmd_report)
    sub.add_parser("issues", help = "list open issues on the target repo") \
        .set_defaults(func=cmd_issues)

    args = p.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()