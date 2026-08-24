from __future__ import annotations

from devagent.config import PROJECT_ROOT
from devagent.github_client import Issue

PROMPTS_DIR = PROJECT_ROOT / "prompts"

def system_prompt() -> str:
    return (PROMPTS_DIR / "system.md").read_text(encoding="utf-8")

def task_prompt(issue: Issue, repo : str) -> str:
    template = (PROMPTS_DIR / "task.md").read_text(encoding="utf-8")
    return template.format(
        repo=repo,
        number=issue.number,
        title=issue.title,
        labels= ", ".join(issue.labels) or "(none)",
        url=issue.url,
        body=issue.body
    )

def pr_body(issue : Issue, solution : str, cost_usd: float | None,
            num_turns : int | None) -> str:
    return(
        f"Resolves #{issue.number}.\n\n"
        f"> [!NOTE]\n"
        f"> Drafted by [dev-workflow-agent]"
        f"(https://github.com/YOURNAME/dev-workflow-agent) — "
        f"AI-generated, opened for human review. "
        f"Agent run: {num_turns or '?'} turns, ~${cost_usd or 0:.2f}.\n\n"
        f"{solution}"
    )