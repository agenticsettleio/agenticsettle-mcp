# Privacy Policy — AgenticSettle Verify MCP Server

**Last updated:** 2026-11-07

This policy covers the `agenticsettle-verify-mcp` server specifically (the
free-tier VOP verification tools). It does not cover the broader
AgenticSettle platform or its paid escrow/settlement features, which this
server does not expose. The platform's full privacy policy (retention
periods, international transfers, and your rights in detail) is at
https://agenticsettle.io/privacy.html.

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
- **Free API key sign-up** — the email address you register with and the IP
  address at sign-up.
- **Your API key** — sent with every request in the `x-api-key` header to
  authenticate you. We store only a one-way hash of it. It is never written
  to logs, never stored in a verification record, and never echoed back in
  any tool response.

This server does not read your conversation history, chat memory, or any
local files — it only sees the specific arguments you (or the calling
agent) pass to a tool.

## How we use it

- Submitted task/result content is sent to an external AI service
  (Anthropic PBC, USA), which may also run web searches for fact-checking,
  to compute a VOP score, tier, and verdict — nothing else.
- A verification record stores the score, tier, verdict, cryptographic
  hashes of the request and result, and short claim, evidence, and summary
  text that the AI extracted. It does not store the full text you submitted.
  Records are kept so you can retrieve them later via
  `check_verdict`/`list_verifications`. When you call `submit_appeal` you
  provide the original content again, and the server checks it against the
  stored hashes to confirm the stored score was not altered after the fact.
- Feedback is reviewed by the AgenticSettle team to improve the product.
  If you configure `AGENTIC_SETTLE_FEEDBACK_URL` yourself (e.g. pointing
  it at your own Slack or Notion webhook), feedback is additionally sent
  there — that destination is one you choose and control, not one we add.

## Storage & retention

- Data is stored on AWS infrastructure in the USA (us-east-1), encrypted in
  transit (HTTPS) and at rest.
- Retention periods for each kind of data are listed in Section 6 of the full
  privacy policy: https://agenticsettle.io/privacy.html. You can also request
  deletion at any time (see below).
- API keys are credentials, not data records — they are never persisted
  in plaintext logs.

## Third-party sharing

We do not sell your submitted content or share it with third parties for
marketing or advertising. Two service providers process data on our behalf:
Amazon Web Services (hosting) and Anthropic PBC (AI verification of the
content you submit). Beyond those, the only outbound sharing this server can
trigger is the optional, user-configured `AGENTIC_SETTLE_FEEDBACK_URL`
webhook described above.

## Your rights

You can request export or erasure of your verification records at any
time. Contact us (below) and we will process the request — the platform
already supports data export and erasure as part of its GDPR-alignment
work.

## Contact

Questions, data requests, or concerns: **agenticsettleio@gmail.com**
