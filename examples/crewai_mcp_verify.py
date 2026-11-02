"""
crewai_mcp_verify.py — use AgenticSettle's hosted MCP server from CrewAI
========================================================================

AgenticSettle runs a hosted, verification-only MCP server over Streamable HTTP:

    https://app.agenticsettle.io/mcp

Listing its tools needs no key; calling a tool needs your API key (sent as the
`x-api-key` header). Nothing is installed locally and no money moves: the six
tools only verify and read.

This script connects with CrewAI's built-in MCP client, lists the tools, and calls
`verify_output` once. No LLM key is needed to run it. The lines at the bottom show how to
hand the same server to a CrewAI agent; that snippet is illustrative and was not executed.

Prerequisites
-------------
    pip install crewai                                   # Python 3.10-3.13
    export AGENTIC_SETTLE_API_KEY="your-api-key-here"    # free key works

Run
---
    python examples/crewai_mcp_verify.py

Note: the free tier is limited per key per day. This script makes one verification call.
CrewAI also prints its own MCP event panels. On a Windows console that is not UTF-8, set
`PYTHONUTF8=1` so those panels do not raise encoding errors.
"""

from __future__ import annotations

import asyncio
import json
import os

from crewai.mcp import MCPClient
from crewai.mcp.transports.http import HTTPTransport

URL = os.environ.get("AGENTIC_SETTLE_MCP_URL", "https://app.agenticsettle.io/mcp")


async def main() -> None:
    transport = HTTPTransport(url=URL, headers={"x-api-key": os.environ["AGENTIC_SETTLE_API_KEY"]})
    client = MCPClient(transport)
    await client.connect()
    try:
        tools = await client.list_tools()
        print("tools:", ", ".join(t["name"] for t in tools))
        result = await client.call_tool(
            "verify_output",
            {
                "task_description": "Explain the difference between list.sort() and sorted() in Python.",
                "result_content": (
                    "list.sort() sorts a list in place and returns None, while sorted() returns a new sorted "
                    "list and leaves the original unchanged. Use list.sort() when you no longer need the "
                    "original order; use sorted() when you need a new list or when the input is any iterable. "
                    "Both accept key= and reverse= arguments."
                ),
            },
        )
        data = json.loads(result) if isinstance(result, str) else result
        print("verdict   :", data.get("verdict"))
        print("score     :", data.get("score"))
        print("fail_codes:", data.get("fail_codes"))
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())

    # Handing the same server to a CrewAI agent (needs your own LLM provider set up; not executed here):
    #
    #   from crewai import Agent
    #   from crewai.mcp import MCPServerHTTP
    #   reviewer = Agent(
    #       role="Reviewer", goal="Only approve outputs that verify_output passes",
    #       backstory="You check deliverables before they are sent.",
    #       mcps=[MCPServerHTTP(url="https://app.agenticsettle.io/mcp",
    #                           headers={"x-api-key": "<your key>"})],
    #       llm="<your model>",
    #   )
