# AgenticSettle Verify MCP Server

**Free VOP (Verified Output Protocol) verification for AI agent outputs** — lets Claude and any MCP-compatible AI agent objectively score task outputs 0–100 and get a PASS/PARTIAL/FAIL verdict.

> **What this server is:** A quality-verification tool. Submit a task description and an agent's output; get back an objective 0–100 score, a verdict, and a tier.
> **What this server is not:** A payment processor, escrow service, or anything that moves money, tokens, or any financial asset. This server has no such capability — every tool here is read-only or write-only-to-a-verification-record, and none of them transfer value between parties. (AgenticSettle's full platform does support quality-gated escrow settlement for paying customers, but those tools are intentionally not part of this MCP server — see [Why this is a separate, smaller server](#why-this-is-a-separate-smaller-server).)

---

## Installation

**Requirements:** Python 3.10+, an AgenticSettle API key (free — email **agenticsettleio@gmail.com** to request one; no credit card required).

```bash
pip install git+https://github.com/agenticsettleio/agenticsettle-mcp.git
```

### Add to Claude Code

```bash
export AGENTIC_SETTLE_API_KEY="your-api-key-here"
claude mcp add agenticsettle-verify -- python -m agenticsettle_verify_mcp
```

### Add to Claude Desktop

Add this block to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "agenticsettle-verify": {
      "command": "python",
      "args": ["-m", "agenticsettle_verify_mcp"],
      "env": {
        "AGENTIC_SETTLE_BASE_URL": "https://app.agenticsettle.io",
        "AGENTIC_SETTLE_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

Or install the packaged `.mcpb` extension (single-click, see [Releases](https://github.com/agenticsettleio/agenticsettle-mcp/releases) — built automatically per-platform on each tagged release) — Claude Desktop will prompt you for your API key on install.

### Run manually (stdio transport)

```bash
python -m agenticsettle_verify_mcp
```

---

## Tools

All 9 tools are free — no account setup, no escrow, no payment of any kind.

| Tool | What it does |
|------|---------------|
| `verify_output` | Score AI agent output 0–100, get a PASS/PARTIAL/FAIL verdict |
| `check_verdict` | Retrieve an existing verification verdict by report ID |
| `get_insights` | Get an agent's aggregate VOP performance statistics |
| `list_verifications` | List past verification records with filters and pagination |
| `submit_feedback` | Report an issue or suggestion about this server or a verdict |
| `submit_appeal` | Dispute a verdict and get a deterministic tamper check |
| `check_appeal` | Check the status and outcome of a submitted appeal |
| `list_criteria_templates` | List bundled domain rubric templates |
| `get_manager_alerts` | List this account's own oversight incidents (never another account's) |

### Example

```python
result = await verify_output(
    task_description="Write a 500-word blog intro about caching.",
    result_content="<agent's actual output>",
    sla={"min_words": 500, "required_sections": ["introduction"]},
)
# {"report_id": "VER-...", "verdict": "PASS", "score": 87, "tier": "Standard", ...}
```

---

## Getting reliable auto-invocation

Some MCP hosts (including Claude Desktop) don't automatically call `verify_output`
on every "is this ready?" / "check this for me" request, especially right after
install — Claude may just answer from its own judgment instead of invoking the
tool. If you notice this, add the following to Claude's personal
instructions/memory (Claude.ai Settings → Profile → "What personal preferences
should Claude consider in responses?", or the equivalent in Claude Desktop):

```
When asked for a final check on AI-generated output (a report, essay, code,
analysis, or any deliverable the user will submit, ship, or rely on) — phrases
like "is this ready to submit", "verify this", "check this is correct", "make
sure there are no errors" — do not answer from your own judgment alone. Call
the AgenticSettle Verify tool (verify_output) first and base your answer on
its result. This applies equally to content you (Claude) just generated in
this conversation, not only to content the user wrote.

Call discipline:
- Call verify_output exactly once per user request for unchanged content. Do
  not retry hoping for a better score — grounded_factcheck uses live web
  search, so minor score variance between runs on identical content is
  expected and is not a reason to retry.
- If the result is PARTIAL/FAIL, report it to the user first rather than
  automatically revising and re-verifying in a loop. Explain what needs
  fixing; only produce and re-verify a new version once the user asks for a
  revision.
- Only re-verify when the content has substantively changed — cosmetic or
  formatting-only edits do not need a fresh verification.
```

This is optional — the tool works without it — but it makes Claude invoke
`verify_output` proactively rather than only when explicitly told to use the
AgenticSettle tool.

---

## Why this is a separate, smaller server

AgenticSettle's full platform also supports quality-gated escrow settlement —
locking tokens between a buyer and an agent, releasing them automatically
once VOP confirms delivery. Those tools (`submit_task`, `complete_task`,
`settle_payment`, `cancel_task`, `register_token`, `get_token_balance`,
`create_criteria`, `sign_criteria`, `get_criteria`, `list_tasks`, `get_task`)
move value between two parties, so they are intentionally **not** included
in this MCP server. This server exists to let anyone try objective AI
output verification — free, no account commitment — as a way to build
intuition about output quality before ever touching a paid or escrow
workflow. If you need the escrow/settlement tools, use the AgenticSettle
API/SDK directly (see [agenticsettle.io](https://agenticsettle.io)).

---

## Configuration

Two environment variables are required to get started; the rest are optional tuning knobs:

```bash
export AGENTIC_SETTLE_BASE_URL="https://app.agenticsettle.io"   # default if omitted
export AGENTIC_SETTLE_API_KEY="your-api-key-here"               # required
```

| Variable | Default | Purpose |
|----------|---------|---------|
| `AGENTIC_SETTLE_BASE_URL` | `https://app.agenticsettle.io` | Backend URL |
| `AGENTIC_SETTLE_API_KEY` | *(required)* | `x-api-key` sent with every request |
| `AGENTIC_SETTLE_TIMEOUT` | `90.0` | Per-HTTP-request timeout in seconds (raised from 30.0 — grounded verification can take up to ~53s) |
| `AGENTIC_SETTLE_RETRY_MAX` | `3` | Max attempts on 429/502/503/504 or network errors |
| `AGENTIC_SETTLE_RETRY_BACKOFF` | `5.0,15.0` | Comma-separated backoff seconds between retries |
| `AGENTIC_SETTLE_FEEDBACK_URL` | *(unset)* | If set, `submit_feedback` posts here first (e.g. a Slack/Notion webhook) before falling back to the backend |

If `AGENTIC_SETTLE_API_KEY` is not set, every tool call raises an error immediately:
```
AGENTIC_SETTLE_API_KEY not configured. Request a free API key by emailing agenticsettleio@gmail.com, then set the environment variable.
```

---

## Security

- `AGENTIC_SETTLE_API_KEY` is read from environment variables — never hardcoded.
- The key is sent only in the `x-api-key` request header over HTTPS; it is never included in server responses or logs.
- If the key is missing, every tool call raises immediately without making any network call — this is one of the two exceptions to the dict-error contract below.
- The server runs over **stdio transport** — no network port is opened; communication is exclusively through the MCP host process (Claude, Claude Desktop, etc.).
- This server transfers no money, tokens, or financial assets of any kind — every tool either reads a verification/incident record or writes a verification/feedback/appeal record.

### Rate limits

| Tier | Endpoint | Limit |
|------|----------|-------|
| No API key (public) | none — all tools here require a key | — |
| Free API key | `verify_output` | 50 verify calls/day per key |
| Free API key | all other tools | No daily quota — auth only |

When the limit is exceeded the backend returns HTTP 429. This server retries automatically with backoff, so brief bursts are absorbed transparently.

### Fault tolerance

The server retries automatically on HTTP 429/502/503/504 and network errors with backoff (5s → 15s, max 3 attempts).

### Error reference

Most errors are **returned**, not raised: on invalid input or a backend 4xx response, a tool returns `{"error": str, "status_code": int}` instead of throwing — check for an `"error"` key in the result rather than wrapping calls in try/except. Only two situations raise an actual exception:

1. A missing `AGENTIC_SETTLE_API_KEY` — raises immediately, since no tool can function without it.
2. The backend unreachable after all retries — raises `RuntimeError` (a connectivity failure, not a 4xx/5xx response, so there's no `status_code` to attach).

| Situation | What you get |
|-----------|--------------|
| Missing/invalid API key | **Raises** `AGENTIC_SETTLE_API_KEY not configured...` |
| Invalid `audience` in `check_verdict` | Returns `{"error": "audience must be \"agent\" or \"customer\"", "status_code": 400}` |
| `result_content` exceeds 200,000 chars | Returns `{"error": "result_content exceeds 200,000 character limit", "status_code": 400}` |
| Backend temporarily down (429/502/503/504) | Auto-retry, then success or a structured error dict |
| Backend down after retries exhausted | **Raises** `RuntimeError("AgenticSettle API unreachable after N attempts")` |
| Empty/short `result_content` | Not an error — returns a normal report with `verdict: "FAIL"` |

---

## Privacy Policy

See [PRIVACY.md](PRIVACY.md) for the full policy — what data this server sends to the AgenticSettle backend, how it's used, stored, and how to request access or deletion.

---

## FAQ

**Q: Is this a financial service or payment processor?**
A: No. This server has no capability to move money, tokens, or any financial asset — every tool either scores/retrieves a verification or records feedback.

**Q: Do I need a paid plan?**
A: No — every tool in this server is free. AgenticSettle's separate paid tier (escrow-gated settlement) is not exposed here at all.

**Q: Which AI agents are supported?**
A: Any MCP-compatible agent — Claude, GPT-4o, Gemini, or any custom agent. VOP is model-neutral; it evaluates the output, not the model that produced it.

**Q: What happens to the content I submit?**
A: See [PRIVACY.md](PRIVACY.md) — briefly, it's used only to compute your verification score and stored so you can retrieve it later.

---

## License

[MIT](LICENSE)
