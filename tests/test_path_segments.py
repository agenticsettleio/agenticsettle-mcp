"""도구 인자가 백엔드 경로를 벗어나지 못한다(공개 제출용 MCP 서버)."""
from __future__ import annotations

import os
from unittest.mock import AsyncMock, patch

import pytest

os.environ.setdefault("AGENTIC_SETTLE_BASE_URL", "http://test-backend:8000")
os.environ.setdefault("AGENTIC_SETTLE_ALLOW_INSECURE_URL", "1")


@pytest.fixture(autouse=True)
def _patch_api_key(monkeypatch):
    monkeypatch.setattr("agenticsettle_verify_mcp.server._API_KEY", "test-key")


import agenticsettle_verify_mcp.server as srv  # noqa: E402


def test_path_segment_encodes_escapes_and_rejects_dot_segments():
    assert srv._path_segment("../../v2/manager/incidents") == "..%2F..%2Fv2%2Fmanager%2Fincidents"
    assert srv._path_segment("abc?admin=1#") == "abc%3Fadmin%3D1%23"
    assert srv._path_segment("RPT-1") == "RPT-1"
    for bad in ("", ".", ".."):
        with pytest.raises(ValueError):
            srv._path_segment(bad)


async def test_read_tools_send_only_encoded_paths():
    with patch("agenticsettle_verify_mcp.server._get", new=AsyncMock(return_value={})) as get:
        await srv.check_verdict("../../v2/manager/incidents")
        await srv.get_insights("a/../../manager/dashboard")
        await srv.check_appeal("x?y=1")
    paths = [c.args[0] for c in get.call_args_list]
    assert paths == [
        "/v2/verifications/..%2F..%2Fv2%2Fmanager%2Fincidents",
        "/v2/agents/a%2F..%2F..%2Fmanager%2Fdashboard/performance",
        "/v2/appeals/x%3Fy%3D1",
    ]


async def test_submit_appeal_sends_an_encoded_path_and_bad_ids_become_local_errors():
    with patch("agenticsettle_verify_mcp.server._post", new=AsyncMock(return_value={})) as post:
        await srv.submit_appeal("../x", "req", "res", "customer", "why")
        assert post.call_args.args[0] == "/v2/verifications/..%2Fx/appeal"
    with patch("agenticsettle_verify_mcp.server._get", new=AsyncMock()) as get:
        out = await srv.check_appeal("..")
        assert out["status_code"] == 400 and "valid identifier" in out["error"]
        get.assert_not_called()
