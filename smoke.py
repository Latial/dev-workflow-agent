import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage

async def main():
    async for m in query(
        prompt="Reply with exactly: toolchain OK",
        options=ClaudeAgentOptions(max_turns=1, allowed_tools=[], setting_sources=[]),
    ):
        if isinstance(m, ResultMessage):
            print(getattr(m, "result", None) or "done")
asyncio.run(main())