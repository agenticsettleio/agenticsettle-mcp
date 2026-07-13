"""
AgenticSettle Verify MCP — unit tests.

Strategy: intercept httpx calls via unittest.mock.patch, no real backend
needed. Verifies each tool's request shape, response passthrough, local
input validation, and tool annotations (title/readOnlyHint/etc — required
by Anthropic's MCP directory pre-submission checklist).
"""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

os.environ.setdefault("AGENTIC_SETTLE_BASE_URL", "http://test-backend:8000")


@pytest.fixture(autouse=True)
def _patch_api_key(monkeypatch):
    monkeypatch.setattr("agenticsettle_verify_mcp.server._API_KEY", "test-key")


import agenticsettle_verify_mcp.server as _srv  # noqa: E402
from agenticsettle_verify_mcp.server import (  # noqa: E402
    check_appeal,
    check_verdict,
    get_insights,
    get_manager_alerts,
    list_criteria_templates,
    list_verifications,
    submit_appeal,
    submit_feedback,
    verify_output,
)


def _mock_response(json_data: dict, status_code: int = 200) -> MagicMock:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.text = str(json_data)
    return resp


def _mock_error_response(status_code: int, detail: str = "error") -> MagicMock:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.text = detail
    resp.json.return_value = {"detail": detail}
    return resp


@pytest.fixture
def mock_client():
    client = MagicMock()
    client.post = AsyncMock()
    client.get = AsyncMock()
    client.is_closed = False
    with patch("agenticsettle_verify_mcp.server._get_http", return_value=client):
        yield client


# ─── Tool registration + annotations ───────────────────────────────────────

def test_tools_are_registered():
    """Exactly 9 free tools — no escrow/settlement tools present."""
    tools = _srv.mcp._tool_manager._tools
    expected = {
        "verify_output", "check_verdict", "get_insights", "list_verifications",
        "submit_feedback", "submit_appeal", "check_appeal",
        "list_criteria_templates", "get_manager_alerts",
    }
    assert expected == set(tools.keys()), f"registered tools: {set(tools.keys())}"


def test_no_financial_tools_present():
    """Regression guard: none of the escrow/settlement tool names ever
    appear here — this server must never grow money-moving capability."""
    forbidden = {
        "submit_task", "complete_task", "settle_payment", "cancel_task",
        "register_token", "get_token_balance", "create_criteria",
        "sign_criteria", "get_criteria", "list_tasks", "get_task",
    }
    tools = set(_srv.mcp._tool_manager._tools.keys())
    assert not (forbidden & tools), f"financial tools leaked in: {forbidden & tools}"


@pytest.mark.parametrize("name", [
    "verify_output", "check_verdict", "get_insights", "list_verifications",
    "submit_feedback", "submit_appeal", "check_appeal",
    "list_criteria_templates", "get_manager_alerts",
])
def test_every_tool_has_title_and_readonly_hint(name):
    """Anthropic's pre-submission checklist requires every tool to declare
    a title and the applicable readOnlyHint/destructiveHint."""
    tool = _srv.mcp._tool_manager._tools[name]
    assert tool.annotations is not None, f"{name} has no annotations"
    assert tool.annotations.title, f"{name} has no title"
    assert tool.annotations.readOnlyHint is not None, f"{name} has no readOnlyHint"


def test_read_only_tools_marked_correctly():
    read_only = {
        "check_verdict", "get_insights", "list_verifications",
        "check_appeal", "list_criteria_templates", "get_manager_alerts",
    }
    write_tools = {"verify_output", "submit_feedback", "submit_appeal"}
    tools = _srv.mcp._tool_manager._tools
    for name in read_only:
        assert tools[name].annotations.readOnlyHint is True, name
    for name in write_tools:
        assert tools[name].annotations.readOnlyHint is False, name


# ─── verify_output ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_verify_output_success(mock_client):
    mock_client.post.return_value = _mock_response({
        "report_id": "VER-1", "verdict": "PASS", "score": 90, "tier": "Platinum",
        "fail_codes": [], "settlement": None, "agent_performance": None,
    })
    result = await verify_output(task_description="Write a summary.", result_content="A summary.")
    assert result["verdict"] == "PASS"
    assert result["settlement"] is None
    call_path = mock_client.post.call_args.args[0]
    assert call_path.endswith("/v2/verify")


@pytest.mark.asyncio
async def test_verify_output_rejects_oversized_content():
    result = await verify_output(task_description="x", result_content="a" * 200_001)
    assert result["error"]
    assert result["status_code"] == 400


@pytest.mark.asyncio
async def test_verify_output_no_criteria_id_param():
    """This server never binds a criteria_id (that's a paid-tier concept
    tied to escrow tasks) — confirm the parameter doesn't exist."""
    import inspect
    sig = inspect.signature(verify_output)
    assert "criteria_id" not in sig.parameters


# ─── check_verdict ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_check_verdict_invalid_audience():
    result = await check_verdict(report_id="VER-1", audience="admin")
    assert result["error"]
    assert result["status_code"] == 400


@pytest.mark.asyncio
async def test_check_verdict_success(mock_client):
    mock_client.get.return_value = _mock_response({"report_id": "VER-1", "verdict": "PASS"})
    result = await check_verdict(report_id="VER-1")
    assert result["verdict"] == "PASS"


# ─── get_insights / list_verifications ──────────────────────────────────────

@pytest.mark.asyncio
async def test_get_insights_success(mock_client):
    mock_client.get.return_value = _mock_response({"agent_id": "a1", "total_jobs": 10})
    result = await get_insights(agent_id="a1")
    assert result["agent_id"] == "a1"
    call_path = mock_client.get.call_args.args[0]
    assert call_path.endswith("/v2/agents/a1/performance")


@pytest.mark.asyncio
async def test_list_verifications_success(mock_client):
    mock_client.get.return_value = _mock_response({"total": 0, "items": []})
    result = await list_verifications(limit=10)
    assert result["items"] == []


# ─── submit_feedback ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_submit_feedback_invalid_rating():
    result = await submit_feedback(rating=6, category="bug", comment="broken")
    assert result["error"]


@pytest.mark.asyncio
async def test_submit_feedback_invalid_category():
    result = await submit_feedback(rating=3, category="not-a-real-category", comment="hi")
    assert result["error"]


@pytest.mark.asyncio
async def test_submit_feedback_empty_comment():
    result = await submit_feedback(rating=3, category="bug", comment="   ")
    assert result["error"]


@pytest.mark.asyncio
async def test_submit_feedback_success(mock_client):
    mock_client.post.return_value = _mock_response({"received": True, "feedback_id": "F-1", "message": "ok"})
    result = await submit_feedback(rating=5, category="praise", comment="Great tool!")
    assert result["received"] is True


# ─── submit_appeal / check_appeal ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_submit_appeal_success(mock_client):
    mock_client.post.return_value = _mock_response({
        "appeal_id": "APL-1", "verification_id": "VER-1", "status": "OPEN",
    })
    result = await submit_appeal(
        verification_id="VER-1", request_content="task", result_content="result",
    )
    assert result["status"] == "OPEN"


@pytest.mark.asyncio
async def test_check_appeal_success(mock_client):
    mock_client.get.return_value = _mock_response({"appeal_id": "APL-1", "status": "RESOLVED"})
    result = await check_appeal(appeal_id="APL-1")
    assert result["status"] == "RESOLVED"


# ─── list_criteria_templates / get_manager_alerts ───────────────────────────

@pytest.mark.asyncio
async def test_list_criteria_templates_success(mock_client):
    mock_client.get.return_value = _mock_response({"templates": []})
    result = await list_criteria_templates()
    assert result["templates"] == []


@pytest.mark.asyncio
async def test_get_manager_alerts_success(mock_client):
    mock_client.get.return_value = _mock_response({"total": 0, "incidents": []})
    result = await get_manager_alerts()
    assert result["incidents"] == []
    call_path = mock_client.get.call_args.args[0]
    assert call_path.endswith("/v2/manager/incidents/mine")


def test_get_manager_alerts_has_no_tenant_id_params():
    """Structural guard: no customer_id/agent_id parameter exists, so it's
    impossible to query another tenant's alerts."""
    import inspect
    sig = inspect.signature(get_manager_alerts)
    assert "customer_id" not in sig.parameters
    assert "agent_id" not in sig.parameters


# ─── error contract ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_missing_api_key_raises(monkeypatch):
    monkeypatch.setattr("agenticsettle_verify_mcp.server._API_KEY", "")
    with pytest.raises(ValueError, match="AGENTIC_SETTLE_API_KEY not configured"):
        await verify_output(task_description="x", result_content="y")


@pytest.mark.asyncio
async def test_backend_error_returns_dict_not_raise(mock_client):
    mock_client.post.return_value = _mock_error_response(404, "task not found")
    result = await verify_output(task_description="x", result_content="y")
    assert result["status_code"] == 404
    assert "error" in result
