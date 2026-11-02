# Examples

Three small, runnable examples that put AgenticSettle's free **verification** step inside popular agent frameworks.
They only verify and read: no escrow, no payment, no money moves.

## Prerequisites

Get a free API key (an email is required, no credit card):

```bash
curl -sX POST https://app.agenticsettle.io/v2/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com"}'
```

The key is shown once. Export it:

```bash
export AGENTIC_SETTLE_API_KEY="your-api-key-here"
```

A free key allows up to 10 `verify_output` calls per day, and a shared daily cap across all free keys may apply first.
Each example below makes one verification call.

## `langgraph_verify.py` - a verification gate in a LangGraph graph

A small graph: a stand-in `draft` node, a `verify` node that calls AgenticSettle (VOP), and a conditional edge that
routes to `accept` on PASS and `rework` otherwise. No LLM key is needed: the draft node returns a canned string, so
replace it with your own agent. Uses the `agentic-settle` SDK.

```bash
pip install agentic-settle langgraph
python examples/langgraph_verify.py
```

## `crewai_verify.py` - verification as a CrewAI tool

Wraps the SDK's `verify` in a CrewAI `@tool` so an agent can check an output against its task. Running the file calls
the tool directly (no LLM key needed). The agent wiring is a commented snippet and is not executed by the script.
CrewAI requires Python 3.10-3.13.

```bash
pip install agentic-settle crewai
python examples/crewai_verify.py
```

## `crewai_mcp_verify.py` - the hosted MCP server from CrewAI

AgenticSettle runs a hosted, verification-only MCP server over Streamable HTTP at `https://app.agenticsettle.io/mcp`.
Listing its tools needs no key; calling one needs your API key (sent as the `x-api-key` header). This example connects
with CrewAI's built-in MCP client, lists the six tools and calls `verify_output` once. Nothing is installed locally.
The agent wiring at the bottom is a commented snippet and is not executed. On a Windows console that is not UTF-8,
set `PYTHONUTF8=1`.

```bash
pip install crewai
python examples/crewai_mcp_verify.py
```

## What was tested

Each example was run once against the hosted API on Python 3.12 with crewai 1.15.34, langgraph 1.2.19 and
agentic-settle 1.0.2, and returned a PASS verdict. The CrewAI agent snippets and any other framework versions were not
tested. A verdict is an automated assessment and can be wrong; see the main [README](../README.md) for what the server
does and does not do.
