"""Stretch: a second agent that reviews the first agent's work."""

from __future__ import annotations

import sys
from pathlib import Path

from claude_agent_sdk import ClaudeAgentOptions, ResultMessage, query

from devagent.config import PROJECT_ROOT, Settings
from devagent.github_client import Issue

MCP_SERVER = PROJECT_ROOT / "mcp_server" / "repo_intel.py"

REVIEWER_TOOLS = [
    "Read", "Glob", "Grep", "Write",          # Write: REVIEW.md only (by prompt)
    "mcp__repo_intel__run_tests",
]

async def run_reviewer(repo_dir: Path, issue: Issue, diff_text: str,
                       settings: Settings) -> str:
    system = (PROJECT_ROOT / "prompts" / "reviewer.md").read_text(encoding="utf-8")
    task = (
        f"Review the drafted change for issue #{issue.number}: {issue.title}\n"
        f"Issue URL: {issue.url}\n\n"
        f"--- DIFF UNDER REVIEW ---\n{diff_text}\n--- END DIFF ---\n\n"
        f"The full repository (with the change applied) is your working "
        f"directory. Investigate as needed, then write REVIEW.md."        
    )
    options = ClaudeAgentOptions(
        cwd=str(repo_dir),
        model=settings.model,
        system_prompt=system,
        allowed_tools=REVIEWER_TOOLS,
        disallowed_tools=["Bash", "Edit", "WebSearch", "WebFetch"],
        permission_mode="acceptEdits",
        max_turns=30,
        setting_sources=[],
        mcp_servers={
            "repo_intel": {
                "type": "stdio",
                "command": sys.executable,
                "args": [str(MCP_SERVER)],
                "env": {"REPO_DIR": str(repo_dir),
                        "TEST_CMD": settings.test_cmd,
                        "LINT_CMD": settings.lint_cmd},
            }
        },
    )
    async for message in query(prompt=task, options=options):
        if isinstance(message, ResultMessage):
            pass
    review_file = repo_dir / "REVIEW.md"
    return(review_file.read_text(encoding="utf-8")
           if review_file.exists()
           else "## Verdict: REQUEST_CHANGES\nReviewer produced no REVIEW.md")