"""Runs one Claude Agent SDK session inside a prepared workspace."""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    query,
)

from devagent.config import PROJECT_ROOT, Settings

MCP_SERVER = PROJECT_ROOT / "mcp_server" / "repo_intel.py"

AGENT_TOOLS = [
    "Read", "Edit", "Write", "Glob", "Grep",
    "mcp__repo_intel__run_tests",
    "mcp__repo_intel__lint_check",
    "mcp__repo_intel__repo_map",
]

@dataclass
class AgentResult :
    subtype: str = "unknown"
    cost_usd: float | None = None
    num_turns: int | None = None
    duration_s : float = 0.0
    final_text: str = ""
    tool_calls: list[str] = field(default_factory=list)

async def run_agent(
    repo_dir : Path,
    system_prompt : str,
    task_prompt : str,
    settings : Settings,
    transcript_path : Path
) -> AgentResult:
    options = ClaudeAgentOptions(
        cwd=str(repo_dir),
        model=settings.model,
        system_prompt=system_prompt,
        allowed_tools=AGENT_TOOLS,
        disallowed_tools=["Bash", "WebSearch", "WebFetch"],
        permission_mode="acceptEdits",
        max_turns=settings.max_turns,
        setting_sources=[],

        mcp_servers={
            "repo_intel": {
                "type" : "stdio",
                "command" : sys.executable,
                "args" : [str(MCP_SERVER)],
                "env" : {
                    "REPO_DIR" : str(repo_dir),
                    "TEST_CMD" : settings.test_cmd,
                    "LINT_CMD" : settings.lint_cmd,
                },
            }
        },
    )

    result = AgentResult()
    start = time.monotonic()
    with transcript_path.open("w", encoding="utf-8") as transcript:
        async for message in query(prompt=task_prompt, options= options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if hasattr(block, "text"):
                        result.final_text = block.text
                        transcript.write(block.text + "\n\n")
                    elif hasattr(block, "name"):
                        result.tool_calls.append(block.name)
                        transcript.write(f"-> tool : {block.name}\n")
                transcript.flush()
            elif isinstance(message, ResultMessage):
                result.subtype = getattr(message, "subtype", "unknown")
                result.cost_usd = getattr(message, "total_cost_usd", None)
                result.num_turns = getattr(message, "num_turns", None)
    result.duration_s = round(time.monotonic() - start, 1)
    return result