"""repo-intel — a standalone MCP server exposing safe, purpose-built dev tools.

Launched by the pipeline as a subprocess of the agent (stdio transport).
It learns which repo to operate on from environment variables:
  REPO_DIR  — absolute path of the workspace clone (required)
  TEST_CMD  — command that runs the test suite   (default: pytest)
  LINT_CMD  — command that runs the linter        (default: none)

IMPORTANT: a stdio MCP server must NEVER print() to stdout — stdout carries
the protocol. Log to stderr if you must log.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

try:                                        # mcp v2 API (docs.modelcontextprotocol.io, mid-2026)
    from mcp.server import MCPServer
except ImportError:                         # mcp v1.x — same decorator API, older name
    from mcp.server.fastmcp import FastMCP as MCPServer

mcp = MCPServer("repo-intel")

REPO_DIR = Path(os.environ["REPO_DIR"])
TEST_CMD = os.environ.get("TEST_CMD", "python -m pytest -x -q")
LINT_CMD = os.environ.get("LINT_CMD", "")
MAX_OUTPUT = 8_000            # chars returned to the model — context discipline

def _run(cmd:str, timeout : int = 600) -> str:
    """Run a configured command in the repo; return exit code + tail of output."""
    try:
        proc = subprocess.run(
            cmd, shell=True, cwd=REPO_DIR,
            capture_output=True, text=True, timeout=timeout
        )
    except subprocess.TimeoutExpired:
        return f"Timeout after {timeout}s running; {cmd}"
    out = (proc.stdout + "\n" + proc.stderr).strip()
    if len(out) > MAX_OUTPUT:
        out = "...(output truncated, showing the end)...\n" + out[-MAX_OUTPUT:]
    return f"exit code: {proc.returncode}\n{out}"

@mcp.tool()
def run_tests(selector : str = "") -> str:
    """Run the repository's test suite. Returns the exit code and output tail.

    Args:
        selector: optional — a test file or filter expression appended to the
            test command, e.g. "tests/test_parser.py" or "-k empty_config".
            Use it to run just the relevant test quickly; run with no selector
            for the full suite before finishing.
    """
    return _run(f"{TEST_CMD} {selector}".strip())

@mcp.tool()
def lint_check() -> str:
    """Run the repository's configured linter and return its findings."""
    if not LINT_CMD:
        return "No linter configured for this repository"
    return _run(LINT_CMD)

@mcp.tool()
def repo_map(max_depth : int = 3) -> str:
    """Return a directory tree of the repository so you can orient yourself.

    Args:
        max_depth: how many directory levels to include (default 3).
    """
    skip = {
        ".git", "node_modules", ".venv", "venv", "__pycache__",
        "dist", "build", ".next", "target", ".pytest_cache"
    } 
    lines: list[str] = []

    def walk(d: Path, depth : int, prefix : str) -> None:
        if depth > max_depth:
            return
        for entry in sorted(d.iterdir(), key= lambda p: (p.is_file(), p.name)):
            if entry.name in skip or entry.name.startswith("."):
                continue
            lines.append(f"{prefix}{entry.name}{'/' if entry.is_dir() else ''}")
            if entry.is_dir():
                walk(entry, depth + 1, prefix + " ")

                
    walk(REPO_DIR, 1, "")
    return "\n".join(lines)[:MAX_OUTPUT] or "(empty repository)"

if __name__ == "__main__" :
    mcp.run(transport="stdio")       