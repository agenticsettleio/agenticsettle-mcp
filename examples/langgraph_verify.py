"""
langgraph_verify.py — a verification gate inside a LangGraph graph
==================================================================

A two-node graph: a stand-in `draft` node produces an output, then a `verify`
node asks AgenticSettle (VOP) whether that output satisfies the task. A
conditional edge routes to `accept` on PASS and to `rework` otherwise.

No LLM key is needed to run this file: `draft` returns a canned string. Replace
it with your own agent node.

Prerequisites
-------------
    pip install agentic-settle langgraph
    export AGENTIC_SETTLE_API_KEY="your-api-key-here"   # free key works (verify only)

Run
---
    python examples/langgraph_verify.py

Note: the free tier is limited per key per day. This script makes one call.
"""

from __future__ import annotations

import os
from typing import TypedDict

from agentic_settle import SettleClient
from langgraph.graph import END, START, StateGraph

client = SettleClient(
    base_url=os.environ.get("AGENTIC_SETTLE_BASE_URL", "https://app.agenticsettle.io"),
    api_key=os.environ["AGENTIC_SETTLE_API_KEY"],
)


class State(TypedDict, total=False):
    task: str
    output: str
    verdict: dict
    decision: str


def draft(state: State) -> State:
    # Stand-in for your agent / LLM node.
    return {"output": (
        "Python's list.sort() sorts a list in place and returns None, while sorted() returns a new "
        "sorted list and leaves the original unchanged. Use list.sort() when you no longer need the "
        "original order and want to avoid the copy; use sorted() when you need a new list or when the "
        "input is any iterable, not only a list. Both accept key= and reverse= arguments."
    )}


def verify(state: State) -> State:
    return {"verdict": client.verify(request_content=state["task"], result_content=state["output"])}


def route(state: State) -> str:
    return "accept" if state["verdict"]["verdict"] == "PASS" else "rework"


graph = StateGraph(State)
graph.add_node("draft", draft)
graph.add_node("verify", verify)
graph.add_node("accept", lambda s: {"decision": "accepted"})
graph.add_node("rework", lambda s: {"decision": "send back to the agent"})
graph.add_edge(START, "draft")
graph.add_edge("draft", "verify")
graph.add_conditional_edges("verify", route, {"accept": "accept", "rework": "rework"})
graph.add_edge("accept", END)
graph.add_edge("rework", END)
app = graph.compile()

if __name__ == "__main__":
    final = app.invoke({"task": "Explain the difference between list.sort() and sorted() in Python."})
    v = final["verdict"]
    print(f"verdict   : {v['verdict']}")
    print(f"score     : {v['score']}")
    print(f"fail_codes: {v['fail_codes']}")
    print(f"decision  : {final['decision']}")
