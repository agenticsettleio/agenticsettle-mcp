"""
crewai_verify.py — AgenticSettle verification as a CrewAI tool
==============================================================

Wraps `verify` from the agentic-settle SDK in a CrewAI `@tool`, so any CrewAI
agent can check an output against its task before handing it over.

Running this file calls the tool directly (no LLM key needed). Wiring it into
an agent is shown as a commented snippet at the bottom. It is illustrative and
was not executed: it needs your own LLM provider set up for CrewAI (for example
the matching `crewai[...]` extra and an API key).

Prerequisites
-------------
    pip install agentic-settle crewai       # CrewAI requires Python 3.10-3.13
    export AGENTIC_SETTLE_API_KEY="your-api-key-here"   # free key works (verify only)

Run
---
    python examples/crewai_verify.py

Note: the free tier is limited per key per day. This script makes one call.
"""

from __future__ import annotations

import os

from agentic_settle import SettleClient
from crewai.tools import tool

client = SettleClient(
    base_url=os.environ.get("AGENTIC_SETTLE_BASE_URL", "https://app.agenticsettle.io"),
    api_key=os.environ["AGENTIC_SETTLE_API_KEY"],
)


@tool("verify_output")
def verify_output(task_description: str, result_content: str) -> str:
    """Verify an output against the task it was written for. Returns the verdict, score and fail codes."""
    v = client.verify(request_content=task_description, result_content=result_content)
    return f"verdict={v['verdict']} score={v['score']} fail_codes={v['fail_codes']}"


if __name__ == "__main__":
    print(verify_output.run(
        task_description="Explain the difference between list.sort() and sorted() in Python.",
        result_content=(
            "list.sort() sorts a list in place and returns None, while sorted() returns a new sorted "
            "list and leaves the original unchanged. Use list.sort() when you no longer need the "
            "original order; use sorted() when you need a new list or when the input is any iterable. "
            "Both accept key= and reverse= arguments."
        ),
    ))

    # Wiring into an agent (needs your own LLM credentials to actually run a crew):
    #
    #   from crewai import Agent
    #   reviewer = Agent(role="Reviewer", goal="Only approve outputs that verify_output passes",
    #                    backstory="You check deliverables before they are sent.",
    #                    tools=[verify_output], llm="<your model>")
