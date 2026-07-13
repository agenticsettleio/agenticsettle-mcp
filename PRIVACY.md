# Privacy Policy — AgenticSettle Verify MCP Server

**Last updated:** 2026-07-13

This policy covers the `agenticsettle-verify-mcp` server specifically (the
free-tier VOP verification tools). It does not cover the broader
AgenticSettle platform or its paid escrow/settlement features, which this
server does not expose.

## Data we collect

When you use this server's tools, the following data is sent to the
AgenticSettle backend (`https://app.agenticsettle.io` by default, or
whatever `AGENTIC_SETTLE_BASE_URL` you configure) over HTTPS:

- **Content you submit for verification** — the task description and
  result content you pass to `verify_output` or `submit_appeal`.
- **Identifiers you provide** — `agent_id`, `report_id`, `appeal_id`, and
  similar values. These are arbitrary strings you choose; this server does
  not verify them against any real-world identity.
- **Feedback you submit** — rating, category, and free-text comment via
  `submit_feedback`.
- **Your API key** — sent with every request in the `x-api-key` header to
  authenticate you. It is never written to logs, never stored in a
  verification record, and never echoed back in any tool response.

This server does not read your conversation history, chat memory, or any
local files — it only sees the specific arguments you (or the calling
agent) pass to a tool.

## How we use it

- Submitted task/result content is used to compute a VOP score, tier, and
  verdict — nothing else.
- Verification records (the score, verdict, cryptographic hashes, and the
  submitted content) are stored so you can retrieve them later via
  `check_verdict`/`list_verifications`, and so `submit_appeal` can
  cryptographically re-verify that a stored score was not altered after
  the fact.
- Feedback is reviewed by the AgenticSettle team to improve the product.
  If you configure `AGENTIC_SETTLE_FEEDBACK_URL` yourself (e.g. pointing
  it at your own Slack or Notion webhook), feedback is additionally sent
  there — that destination is one you choose and control, not one we add.

## Storage & retention

- Data is stored on AWS infrastructure, encrypted in transit (HTTPS) and
  at rest.
- Verification records are retained until you request deletion (see
  below) or your account is closed.
- API keys are credentials, not data records — they are never persisted
  in plaintext logs.

## Third-party sharing

We do not sell your submitted content or share it with third parties for
marketing or advertising. The only outbound sharing this server can
trigger is the optional, user-configured `AGENTIC_SETTLE_FEEDBACK_URL`
webhook described above.

## Your rights

You can request export or erasure of your verification records at any
time. Contact us (below) and we will process the request — the platform
already supports data export and erasure as part of its GDPR-alignment
work.

## Contact

Questions, data requests, or concerns: **agenticsettleio@gmail.com**
