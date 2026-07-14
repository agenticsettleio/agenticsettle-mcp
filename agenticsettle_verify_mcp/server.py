"""
AgenticSettle Verify MCP Server

VOP(Verified Output Protocol) verification, exposed as MCP tools — the
free-tier, verification-only surface of the AgenticSettle platform. Lets
Claude and any MCP-compatible AI agent objectively score task outputs 0-100
and get a PASS/PARTIAL/FAIL verdict, with no account setup, no escrow, and
no financial transaction of any kind.

This package intentionally does NOT include the paid escrow/settlement
tools (submit_task, complete_task, settle_payment, cancel_task,
register_token, get_token_balance, create_criteria, sign_criteria,
get_criteria, list_tasks, get_task) — those move tokens between two
parties and are out of scope for this MCP Directory submission by design
(see README.md "Why this is a separate, smaller server"). They remain
available via the main AgenticSettle API/SDK for customers who need
escrow-gated settlement.

환경변수:
  AGENTIC_SETTLE_BASE_URL      백엔드 URL (default: https://app.agenticsettle.io)
  AGENTIC_SETTLE_API_KEY       x-api-key (필수)
  AGENTIC_SETTLE_TIMEOUT       HTTP 요청당 타임아웃(초, default: 90.0 — 2026-07-14,
                               백엔드가 VOP_M1_STRATEGY=grounded로 전환되며 검증
                               1건이 웹검색 포함 최대 ~53s까지 걸릴 수 있어 기존
                               30.0 기본값으로는 매 호출이 타임아웃되던 것을 확인,
                               여유를 두고 상향)
  AGENTIC_SETTLE_RETRY_MAX     429/502/503/504 재시도 최대 횟수(default: 3)
  AGENTIC_SETTLE_RETRY_BACKOFF 재시도 간 대기(초, 콤마 구분, default: "5.0,15.0")
                               — 기본값 기준 최악의 경우 ~290초/호출
                               (3×90s + 5s+15s); 대화형 세션에서 더 빠른
                               응답이 필요하면 예: RETRY_MAX=1 로 낮추기
  AGENTIC_SETTLE_FEEDBACK_URL  submit_feedback 1차 전송 대상 웹훅(Slack/Notion 등,
                               선택). 미설정 시 백엔드 /v2/user-feedback로 직행

실행 (stdio transport):
  python -m agenticsettle_verify_mcp

Claude Code 연동:
  claude mcp add agenticsettle-verify -- python -m agenticsettle_verify_mcp
"""

from __future__ import annotations

import os
import site

# ─── .mcpb vendored-lib bootstrap ────────────────────────────────────────────
# manifest.json sets PYTHONPATH=${__dirname}/lib for the packaged .mcpb
# install, which only appends that directory to sys.path *raw* — it does NOT
# process any .pth files inside it (that only happens for directories site.py
# scans at interpreter startup, e.g. real site-packages). On Windows, `mcp`
# unconditionally imports pywintypes/win32api/win32con/win32job, which
# pywin32 exposes via a `.pth` file that redirects into lib/win32/lib/ —
# without this, the packaged server fails to import at all on any machine
# that doesn't happen to have a separate global pywin32 install (2026-07-14,
# caught by testing the packaged layout in true isolation with `python -S`,
# not by anything short of that — a plain PYTHONPATH-based smoke test on a
# dev machine with pywin32 already installed globally silently "passes" by
# using that global copy instead of the vendored one).
_LIB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lib")
if os.path.isdir(_LIB_DIR):
    site.addsitedir(_LIB_DIR)

import asyncio  # noqa: E402
from typing import Any  # noqa: E402

import httpx  # noqa: E402
from dotenv import load_dotenv  # noqa: E402
from mcp.server.fastmcp import FastMCP  # noqa: E402
from mcp.types import ToolAnnotations  # noqa: E402

load_dotenv()

# ─── 설정 ────────────────────────────────────────────────────────────────────

_BASE_URL = os.getenv("AGENTIC_SETTLE_BASE_URL", "https://app.agenticsettle.io").rstrip("/")
_API_KEY: str = os.getenv("AGENTIC_SETTLE_API_KEY") or ""
_TIMEOUT = float(os.getenv("AGENTIC_SETTLE_TIMEOUT", "90.0"))
_SDK_VER = "verify-mcp-1.0.0"
_MAX_CONTENT_LEN = 200_000  # characters — prevents oversized payloads

# 피드백 전송 대상: 백엔드 /v2/user-feedback 또는 Slack/Notion 웹훅 URL
_FEEDBACK_URL: str | None = os.getenv("AGENTIC_SETTLE_FEEDBACK_URL")

_FEEDBACK_CATEGORIES = {
    "wrong_verdict",   # VOP 판정이 틀렸다고 생각함
    "feature_request", # 새 기능 요청
    "bug",             # 도구 오류/예외
    "praise",          # 잘 작동함
    "other",           # 기타
}

# 503/502/504 재시도 설정 — 백엔드 배포 중 잠깐 끊기는 구간을 투명하게 처리
_RETRY_STATUSES = {429, 502, 503, 504}
_RETRY_MAX = int(os.getenv("AGENTIC_SETTLE_RETRY_MAX", "3"))
_RETRY_BACKOFF = [
    float(x) for x in os.getenv("AGENTIC_SETTLE_RETRY_BACKOFF", "5.0,15.0").split(",") if x.strip()
]


def _backoff_for(attempt: int) -> float:
    """Sleep duration before retrying `attempt`. Clamps into _RETRY_BACKOFF
    so a custom AGENTIC_SETTLE_RETRY_MAX larger than len(_RETRY_BACKOFF)+1
    can't IndexError — repeats the last configured backoff instead."""
    if not _RETRY_BACKOFF:
        return 0.0
    return _RETRY_BACKOFF[min(attempt, len(_RETRY_BACKOFF) - 1)]


mcp = FastMCP(
    "AgenticSettle Verify",
    instructions=(
        "VOP (Verified Output Protocol) verification for AI agent workflows — "
        "free tier only, no account setup or escrow required. "
        "Use verify_output to score any agent output 0-100 and get a "
        "PASS/PARTIAL/FAIL verdict. If the user just pastes or shares "
        "content (including a file attachment) and asks you to check/verify/"
        "review it without stating an explicit task or requirements, do NOT "
        "ask them to supply a task_description — infer a reasonable one "
        "yourself from what the content appears to be (e.g. 'Write a clear, "
        "complete, well-structured piece of content on the given subject') "
        "and call verify_output immediately with the content as "
        "result_content. Only ask the user for a task_description if they "
        "clearly intended to specify requirements but didn't paste any "
        "content yet. Use check_verdict to retrieve a prior "
        "result by report_id, list_verifications to browse past results, "
        "and get_insights for an agent's aggregate track record. "
        "submit_appeal/check_appeal dispute a verdict with a deterministic "
        "tamper check. submit_feedback reports issues or suggestions. "
        "list_criteria_templates discovers bundled domain rubrics. "
        "get_manager_alerts lists this account's own oversight incidents "
        "(never another account's — there is no customer_id/agent_id "
        "parameter to query with). "
        "This server does not move money, tokens, or any financial asset — "
        "it only scores and reports on already-produced output. "
        "Error contract: on invalid input or a backend 4xx response, tools "
        "return {'error': str, 'status_code': int} instead of raising — "
        "check for an 'error' key rather than wrapping calls in "
        "try/except. Two things raise instead of returning that dict: a "
        "missing AGENTIC_SETTLE_API_KEY (raises immediately, since no tool "
        "can function without it), and the backend being unreachable after "
        "all retries (raises RuntimeError — a connectivity failure, not a "
        "4xx/5xx response, so there is no status_code to return). "
        "Requires AGENTIC_SETTLE_API_KEY environment variable — "
        "request a free key by emailing agenticsettleio@gmail.com"
    ),
    website_url="https://agenticsettle.io",
)


def _require_api_key() -> None:
    """Raise ValueError if AGENTIC_SETTLE_API_KEY is not configured."""
    if not _API_KEY:
        raise ValueError(
            "AGENTIC_SETTLE_API_KEY not configured. "
            "Request a free API key by emailing agenticsettleio@gmail.com, "
            "then set the environment variable."
        )


def _headers() -> dict[str, str]:
    return {
        "x-api-key": _API_KEY,
        "content-type": "application/json",
        "user-agent": f"agentic-settle-verify/{_SDK_VER}",
    }


def _error_response(r: httpx.Response) -> dict[str, Any]:
    """Convert an error backend response into a structured error dict —
    tools return this instead of raising so a calling agent can branch on
    result["error"]/result["status_code"] without a try/except."""
    message: Any = r.text
    try:
        body = r.json()
        if isinstance(body, dict):
            message = body.get("detail") or body.get("error") or body.get("message") or r.text
    except Exception:
        pass
    return {"error": str(message), "status_code": r.status_code}


def _local_error(message: str, status_code: int = 400) -> dict[str, Any]:
    """Structured error dict for input validation failures caught before any network call."""
    return {"error": message, "status_code": status_code}


# Shared client — recreated when the event loop changes (pytest-asyncio per-function loops).
_http: httpx.AsyncClient | None = None
_http_loop: object | None = None


def _get_http() -> httpx.AsyncClient:
    global _http, _http_loop
    try:
        current_loop: object | None = asyncio.get_running_loop()
    except RuntimeError:
        current_loop = None
    if isinstance(_http, httpx.AsyncClient):
        if _http_loop is not current_loop or _http.is_closed:
            _http = httpx.AsyncClient(timeout=_TIMEOUT)
            _http_loop = current_loop
    elif _http is None:
        _http = httpx.AsyncClient(timeout=_TIMEOUT)
        _http_loop = current_loop
    return _http


async def _post(path: str, body: dict[str, Any]) -> dict[str, Any]:
    last_exc: Exception | None = None
    for attempt in range(_RETRY_MAX):
        try:
            r = await _get_http().post(f"{_BASE_URL}{path}", json=body, headers=_headers())
            if r.status_code in _RETRY_STATUSES and attempt < _RETRY_MAX - 1:
                await asyncio.sleep(_backoff_for(attempt))
                continue
            if r.status_code >= 400:
                return _error_response(r)
            return r.json()
        except httpx.RequestError as exc:
            last_exc = exc
            if attempt < _RETRY_MAX - 1:
                await asyncio.sleep(_backoff_for(attempt))
    raise RuntimeError(
        f"AgenticSettle API unreachable after {_RETRY_MAX} attempts"
    ) from last_exc


async def _get(path: str, *, params: dict[str, Any] | None = None) -> dict[str, Any]:
    last_exc: Exception | None = None
    for attempt in range(_RETRY_MAX):
        try:
            r = await _get_http().get(f"{_BASE_URL}{path}", params=params, headers=_headers())
            if r.status_code in _RETRY_STATUSES and attempt < _RETRY_MAX - 1:
                await asyncio.sleep(_backoff_for(attempt))
                continue
            if r.status_code >= 400:
                return _error_response(r)
            return r.json()
        except httpx.RequestError as exc:
            last_exc = exc
            if attempt < _RETRY_MAX - 1:
                await asyncio.sleep(_backoff_for(attempt))
    raise RuntimeError(
        f"AgenticSettle API unreachable after {_RETRY_MAX} attempts"
    ) from last_exc


# ─── 도구 1: verify_output ───────────────────────────────────────────────────

@mcp.tool(
    annotations=ToolAnnotations(
        title="Verify AI Output",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=True,
    )
)
async def verify_output(
    task_description: str,
    result_content: str,
    agent_id: str | None = None,
    sla: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Verify ANY AI-generated output — including your own responses, not just
    another agent's — using VOP (Verified Output Protocol). Free tier, no
    account or escrow setup required.

    Call this BEFORE presenting AI-generated content as a finished deliverable
    (a report, essay, code, analysis, or any output the user will submit, ship,
    or otherwise rely on as final) — including content you yourself generated
    in this conversation. This is the single most important use case: an LLM's
    own confidence about its output is not evidence of factual correctness,
    which is exactly what this tool independently checks via grounded web
    search rather than the model's own judgment.

    Call this AGAIN, on the new content, whenever you revise or regenerate
    previously-verified output (e.g. after the user asks you to fix issues
    this tool flagged) — a prior PASS/FAIL result does not carry over to a
    changed version, and presenting a revision as "corrected" without
    re-verifying it defeats the purpose of having verified the original.

    Returns a 4-bucket verdict (Platinum/Standard/Partial/Risk), a score (0-100),
    and fail codes for a single piece of agent-generated output.

    Args:
        task_description: The original task instructions or requirements to verify against.
        result_content: The agent-generated output text to be evaluated.
            Maximum 200,000 characters.
        agent_id: Agent identifier (optional). Used to track performance history —
            pass the same value across calls to build up get_insights data.
        sla: Inline evaluation criteria dict (optional). Supported keys:
              "required_sections": list[str] — headings that must appear in the output
              "min_words": int — minimum word count (hard-fail if violated)
              "min_chars": int — minimum character count
              "max_chars": int — maximum character count (0 = no limit)
              "min_numbers": int — minimum numeric data points required
              "min_citations": int — minimum citation/reference count required
            Example: {"min_words": 500, "min_citations": 3,
                       "required_sections": ["introduction", "conclusion"]}

    Returns:
        dict with keys: report_id, verdict ("PASS"|"PARTIAL"|"FAIL"), score (0-100),
        tier ("Platinum"|"Standard"|"Partial"|"Risk"), fail_codes (list),
        settlement (always None — this server has no settlement capability),
        agent_performance
    """
    _require_api_key()
    if len(result_content) > _MAX_CONTENT_LEN:
        return _local_error(
            f"result_content exceeds {_MAX_CONTENT_LEN:,} character limit "
            f"(received {len(result_content):,} characters)"
        )
    return await _post("/v2/verify", {
        "request_content": task_description,
        "result_content": result_content,
        "agent_id": agent_id,
        "sla": sla,
        "audience": "agent",
    })


# ─── 도구 2: check_verdict ───────────────────────────────────────────────────

@mcp.tool(
    annotations=ToolAnnotations(title="Check Verdict", readOnlyHint=True, openWorldHint=True)
)
async def check_verdict(
    report_id: str,
    audience: str = "agent",
) -> dict[str, Any]:
    """Retrieve an existing VOP verification verdict by report ID.

    Use the report_id returned by verify_output to fetch full verdict details.

    Args:
        report_id: The verification ID returned by verify_output (the report_id field).
        audience: Response detail level.
            "agent" (default) — machine-readable verdict for agent consumption.
            "customer" — adds human-readable explanations for presenting results to end users.
            Do not use "admin" — it is reserved for platform operators only.

    Returns:
        dict with keys: report_id, verdict, score, tier, fail_codes,
        issued_at (ISO 8601), settlement (always None), agent_performance
    """
    _require_api_key()
    if audience not in {"agent", "customer"}:
        return _local_error('audience must be "agent" or "customer"')
    return await _get(
        f"/v2/verifications/{report_id}",
        params={"audience": audience},
    )


# ─── 도구 3: get_insights ────────────────────────────────────────────────────

@mcp.tool(
    annotations=ToolAnnotations(title="Get Agent Insights", readOnlyHint=True, openWorldHint=True)
)
async def get_insights(agent_id: str) -> dict[str, Any]:
    """Retrieve VOP performance statistics for an agent. Free tier.

    Aggregates verdict counts and average score across this agent's verify_output
    history. Use to evaluate an agent's track record before relying on its output.

    Args:
        agent_id: The agent identifier to look up.

    Returns:
        dict with keys: agent_id, total_jobs (int), pass_count (int),
        partial_count (int), fail_count (int), pass_rate_pct (float, 0-100 —
        NOT a 0.0-1.0 fraction), avg_vop_score (float, 0-100).
    """
    _require_api_key()
    return await _get(f"/v2/agents/{agent_id}/performance")


# ─── 도구 4: list_verifications ──────────────────────────────────────────────

@mcp.tool(
    annotations=ToolAnnotations(title="List Verifications", readOnlyHint=True, openWorldHint=True)
)
async def list_verifications(
    agent_id: str | None = None,
    verdict: str | None = None,
    tier: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """List VOP verification records with optional filters and pagination. Free tier.

    Returns verifications in reverse chronological order.

    Args:
        agent_id: Filter by agent ID (optional).
        verdict: Filter by verdict (optional). Values: "PASS", "FAIL", "PARTIAL"
        tier: Filter by tier (optional). Values: "Platinum", "Standard", "Partial", "Risk"
        date_from: ISO 8601 date lower bound, inclusive (optional). Example: "2026-06-01"
        date_to: ISO 8601 date upper bound, inclusive (optional). Example: "2026-06-30"
        limit: Maximum number of records to return (1–500, default 50).
        offset: Pagination offset — number of records to skip (default 0).

    Returns:
        dict with keys: total (int), limit (int), offset (int),
        items (list of verification dicts with keys: verification_id, agent_id,
        verdict, score, tier, fail_codes, created_at)
    """
    _require_api_key()
    limit = max(1, min(int(limit), 500))
    offset = max(0, int(offset))
    params: dict[str, Any] = {"limit": limit, "offset": offset}
    if agent_id is not None:
        params["agent_id"] = agent_id
    if verdict is not None:
        params["verdict"] = verdict.upper()
    if tier is not None:
        params["tier"] = tier
    if date_from is not None:
        params["date_from"] = date_from
    if date_to is not None:
        params["date_to"] = date_to
    return await _get("/v2/verifications", params=params)


# ─── 도구 5: submit_feedback ──────────────────────────────────────────────────

@mcp.tool(
    annotations=ToolAnnotations(
        title="Submit Feedback", readOnlyHint=False, destructiveHint=False,
        idempotentHint=False, openWorldHint=True,
    )
)
async def submit_feedback(
    rating: int,
    category: str,
    comment: str,
    tool_name: str | None = None,
    report_id: str | None = None,
) -> dict[str, Any]:
    """Submit feedback about this MCP server or a VOP verification result. Free tier.

    Use after any tool call to report issues, request features, or share what worked well.
    Feedback is reviewed weekly and drives product improvements.

    Args:
        rating: Satisfaction score 1–5 (1 = very poor, 5 = excellent).
        category: Feedback type. One of:
            "wrong_verdict"   — VOP verdict seems incorrect for the output
            "feature_request" — request a new capability or parameter
            "bug"             — tool raised an error or behaved unexpectedly
            "praise"          — something worked especially well
            "other"           — anything else
        comment: Description of the issue or suggestion (max 2,000 characters).
        tool_name: The MCP tool name this feedback is about (optional).
            Example: "verify_output", "check_verdict"
        report_id: The report_id from a specific verification (optional).
            Helps correlate feedback with the exact VOP result.

    Returns:
        dict with keys: received (bool), feedback_id (str), message (str)
    """
    if not (1 <= rating <= 5):
        return _local_error("rating must be between 1 and 5")
    if category not in _FEEDBACK_CATEGORIES:
        return _local_error(
            f"category must be one of: {', '.join(sorted(_FEEDBACK_CATEGORIES))}"
        )
    if not comment or not comment.strip():
        return _local_error("comment must not be empty")
    if len(comment) > 2000:
        return _local_error("comment must be 2,000 characters or fewer")

    payload: dict[str, Any] = {
        "rating": rating,
        "category": category,
        "comment": comment,
        "sdk_version": _SDK_VER,
    }
    if tool_name is not None:
        payload["tool_name"] = tool_name
    if report_id is not None:
        payload["report_id"] = report_id

    if _FEEDBACK_URL:
        last_err: Exception | None = None
        for _attempt in range(2):
            try:
                r = await _get_http().post(
                    _FEEDBACK_URL,
                    json=payload,
                    headers={"user-agent": f"agentic-settle-verify/{_SDK_VER}"},
                    timeout=10.0,
                )
                r.raise_for_status()
                return {"received": True, "feedback_id": "", "message": "Feedback received. Thank you!"}
            except Exception as exc:
                last_err = exc
                if _attempt == 0:
                    await asyncio.sleep(3.0)
        try:
            return await _post("/v2/user-feedback", payload)
        except Exception:
            raise RuntimeError(
                f"Feedback delivery failed (webhook and backend both unreachable): {last_err}"
            ) from last_err

    return await _post("/v2/user-feedback", payload)


# ─── 도구 6: submit_appeal ────────────────────────────────────────────────────

@mcp.tool(
    annotations=ToolAnnotations(
        title="Submit Appeal", readOnlyHint=False, destructiveHint=False,
        idempotentHint=False, openWorldHint=True,
    )
)
async def submit_appeal(
    verification_id: str,
    request_content: str,
    result_content: str,
    appellant: str | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    """Dispute a VOP verdict and get a deterministic tamper check. Free tier.

    Re-runs the SAME engine version on the same inputs and compares the
    recomputed evidence hash to the one stored at issue time. A hash
    match proves the stored score was not altered after issue (the
    dispute is about scoring quality, not tampering); a mismatch signals
    engine version drift or a stored-score discrepancy that warrants
    manual review.

    You must supply the EXACT original task_description (as
    request_content) and result_content used in the disputed
    verify_output call — they are hash-checked against the stored
    verification, so reconstructed or paraphrased text will be rejected.
    There is a time window to appeal after a verdict is issued (window
    length is server-configured); appealing after it closes returns an error.

    Args:
        verification_id: The report_id from the disputed verify_output/check_verdict call.
        request_content: The exact original task_description/instructions
            (must hash-match what was stored).
        result_content: The exact original output text that was verified
            (must hash-match what was stored).
        appellant: Who is appealing (optional free text, e.g. "agent",
            "customer", or an identifier).
        reason: Why the verdict is being disputed (optional, recommended).

    Returns:
        dict with keys: appeal_id, verification_id, status ("OPEN"),
        appeal_window (dict: window_hours, issued_at, deadline, enforced),
        tamper_check (dict: hash_match (bool) — false does NOT necessarily
        mean tampering, see interpretation; original_evidence_hash,
        recomputed_evidence_hash, interpretation (str)),
        original (dict: score, verdict), recomputed (dict: score, verdict,
        confidence, review_recommended, review_reasons)
    """
    _require_api_key()
    body: dict[str, Any] = {
        "request_content": request_content,
        "result_content": result_content,
        "appellant": appellant,
        "reason": reason,
    }
    return await _post(f"/v2/verifications/{verification_id}/appeal", body)


# ─── 도구 7: check_appeal ─────────────────────────────────────────────────────

@mcp.tool(
    annotations=ToolAnnotations(title="Check Appeal Status", readOnlyHint=True, openWorldHint=True)
)
async def check_appeal(appeal_id: str) -> dict[str, Any]:
    """Retrieve an appeal's status and tamper-check result. Free tier.

    Args:
        appeal_id: The appeal_id returned by submit_appeal.

    Returns:
        dict with keys: appeal_id, verification_id, appellant, reason,
        original_score, original_verdict, original_evidence_hash,
        recomputed_score, recomputed_verdict, recomputed_evidence_hash,
        hash_match (bool), status ("OPEN"|"RESOLVED"),
        outcome (None|"UPHELD"|"OVERTURNED" — set once resolved),
        resolution_score, resolution_note, created_at, resolved_at
    """
    _require_api_key()
    return await _get(f"/v2/appeals/{appeal_id}")


# ─── 도구 8: list_criteria_templates ──────────────────────────────────────────

@mcp.tool(
    annotations=ToolAnnotations(title="List Criteria Templates", readOnlyHint=True, openWorldHint=True)
)
async def list_criteria_templates(domain: str | None = None) -> dict[str, Any]:
    """List bundled domain criteria templates showing what a well-specified
    verification rubric looks like. Free tier.

    Args:
        domain: Filter by domain name (optional, e.g. "data_analysis").
            Matches domain equality or a template_id prefix match.

    Returns:
        dict with key: templates (list of dicts, each with template_id,
        domain, items (list of {id, name, weight}), pass_threshold,
        partial_range ([low, high]))
    """
    _require_api_key()
    return await _get("/v2/criteria/templates", params={"domain": domain} if domain else None)


# ─── 도구 9: get_manager_alerts ───────────────────────────────────────────────

@mcp.tool(
    annotations=ToolAnnotations(title="Get Manager Alerts", readOnlyHint=True, openWorldHint=True)
)
async def get_manager_alerts(
    domain: str | None = None,
    severity: str | None = None,
    status: str | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    """List Manager AI oversight alerts (incidents) for this account. Free tier.

    Manager AI continuously watches for customer-behavior anomalies (repeat
    rework, repeat disputes) and verification-quality anomalies in the
    background, and raises an incident when something looks off. This tool
    is always scoped to the account behind this server's own API key — there
    is no customer_id/agent_id parameter, so it is impossible to query
    another tenant's alerts.

    Args:
        domain: Filter by domain (optional). Values seen in practice:
            "customer_behavior", "vop_quality", "verification_audit".
        severity: Filter by severity (optional). Values seen in practice:
            "info", "low", "medium", "high", "critical".
        status: Filter by status (optional). Values: "open", "resolved".
        limit: Maximum number of incidents to return (1-500, default 50).

    Returns:
        dict with keys: total (int), incidents (list of dicts with keys:
        incident_id, domain, severity, signal, evidence (dict), status,
        created_at)
    """
    _require_api_key()
    limit = max(1, min(int(limit), 500))
    params: dict[str, Any] = {"limit": limit}
    if domain is not None:
        params["domain"] = domain
    if severity is not None:
        params["severity"] = severity
    if status is not None:
        params["status"] = status
    return await _get("/v2/manager/incidents/mine", params=params)


# ─── 진입점 ──────────────────────────────────────────────────────────────────

def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
