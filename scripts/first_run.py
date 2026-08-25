import asyncio, datetime as dt
from devagent.config import load_settings
from devagent.github_client import GitHubClient
from devagent import prompts
from devagent.workspace import Workspace
from devagent.agent_runner import run_agent

s = load_settings()
gh = GitHubClient(s.github_token, s.target_repo)
issue = gh.get_issue(5)                     # <- your toy issue's number
run_id = dt.datetime.now().strftime("%Y%m%d-%H%M%S") + f"-i{issue.number}"
ws = Workspace(s.runs_dir, run_id, s.target_repo, s.github_token)
ws.clone()
ws.create_branch(issue.number, issue.title)
res = asyncio.run(run_agent(ws.repo_dir, prompts.system_prompt(),
                            prompts.task_prompt(issue, s.target_repo),
                            s, ws.root / "transcript.md"))
print(res.subtype, "| turns:", res.num_turns, "| cost:", res.cost_usd,
      "| seconds:", res.duration_s)
print("tools used:", res.tool_calls)
print("inspect:", ws.root)