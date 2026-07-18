# AgenticSettle Verify MCP 서버

**AI 에이전트 결과물에 대한 무료 VOP(Verified Output Protocol) 검증** — Claude와 모든 MCP 호환 AI 에이전트가 작업 결과물을 0~100점으로 객관적으로 채점하고 PASS/PARTIAL/FAIL 판정을 받을 수 있게 합니다.

> **이 서버가 하는 일**: 품질 검증 도구입니다. 작업 설명과 에이전트의 결과물을 제출하면 객관적인 0~100점 점수, 판정, 등급을 돌려받습니다.
> **이 서버가 하지 않는 일**: 결제 처리나 에스크로, 그 어떤 형태로든 돈·토큰·금융자산을 이전하는 일. 이 서버에는 그런 기능 자체가 없습니다 — 모든 tool은 조회이거나 검증 기록에 대한 쓰기일 뿐, 당사자 간 가치 이전은 전혀 일어나지 않습니다(AgenticSettle 전체 플랫폼은 유료 고객을 위한 품질연동 에스크로 정산 기능을 지원하지만, 그 tool들은 의도적으로 이 MCP 서버에 포함되지 않았습니다 — [이 서버가 별도로, 더 작게 만들어진 이유](#이-서버가-별도로-더-작게-만들어진-이유) 참조).

---

## 설치

**요구사항**: Python 3.10+, AgenticSettle API 키(무료 — **agenticsettleio@gmail.com**으로 요청하시면 발급해드립니다. 신용카드 불필요).

```bash
pip install git+https://github.com/agenticsettleio/agenticsettle-mcp.git
```

### Claude Code에 추가

```bash
export AGENTIC_SETTLE_API_KEY="your-api-key-here"
claude mcp add agenticsettle-verify -- python -m agenticsettle_verify_mcp
```

### Claude Desktop에 추가

`claude_desktop_config.json`에 다음을 추가하세요:

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

### 수동 실행 (stdio transport)

```bash
python -m agenticsettle_verify_mcp
```

또는 패키징된 `.mcpb` 확장을 설치하세요(원클릭 설치, [Releases](https://github.com/agenticsettleio/agenticsettle-mcp/releases) 참조 — 태그 릴리스마다 플랫폼별로 자동 빌드됨) — Claude Desktop이 설치 시 API 키를 물어봅니다.

---

## Tool 목록

9개 tool 전부 무료입니다 — 계정 설정, 에스크로, 어떤 형태의 결제도 필요 없습니다.

| Tool | 하는 일 |
|------|---------|
| `verify_output` | AI 에이전트 출력을 0~100점으로 채점, PASS/PARTIAL/FAIL 판정 |
| `check_verdict` | report ID로 기존 검증 판정 조회 |
| `get_insights` | 에이전트의 누적 VOP 성과 통계 조회 |
| `list_verifications` | 필터·페이지네이션으로 과거 검증 기록 목록 조회 |
| `submit_feedback` | 이 서버나 판정에 대한 문제·제안 제출 |
| `submit_appeal` | 판정에 이의제기, 결정론적 변조 검사 수행 |
| `check_appeal` | 제출한 이의제기의 상태·결과 확인 |
| `list_criteria_templates` | 도메인별 번들 루브릭 템플릿 목록 |
| `get_manager_alerts` | 이 계정 자신의 관제 인시던트 목록(다른 계정 조회 불가) |

### 예제

```python
result = await verify_output(
    task_description="캐싱에 대한 500단어 블로그 서두를 작성하세요.",
    result_content="<에이전트가 실제로 생성한 결과물>",
    sla={"min_words": 500, "required_sections": ["introduction"]},
)
# {"report_id": "VER-...", "verdict": "PASS", "score": 87, "tier": "Standard", ...}
```

---

## 이 서버가 별도로, 더 작게 만들어진 이유

AgenticSettle 전체 플랫폼은 품질연동 에스크로 정산도 지원합니다 —
구매자와 에이전트 사이에 토큰을 잠갔다가 VOP가 납품을 확인하면 자동으로
풀어주는 방식입니다. 이 tool들(`submit_task`, `complete_task`,
`settle_payment`, `cancel_task`, `register_token`, `get_token_balance`,
`create_criteria`, `sign_criteria`, `get_criteria`, `list_tasks`,
`get_task`)은 두 당사자 사이에 가치를 이전시키므로, 이 MCP 서버에는
의도적으로 포함하지 않았습니다. 이 서버는 누구나 무료로, 계정 약정 없이
AI 결과물의 객관적 검증을 체험해보고, 유료·에스크로 워크플로우를
사용하기 전에 품질에 대한 직관을 먼저 쌓을 수 있게 하기 위한 것입니다.
에스크로/정산 tool이 필요하시면 AgenticSettle API/SDK를 직접 사용하세요
([agenticsettle.io](https://agenticsettle.io) 참조).

---

## 설정

시작에 필요한 환경변수 2개, 나머지는 선택적 튜닝값입니다:

```bash
export AGENTIC_SETTLE_BASE_URL="https://app.agenticsettle.io"   # 생략 시 기본값
export AGENTIC_SETTLE_API_KEY="your-api-key-here"               # 필수
```

| 변수 | 기본값 | 용도 |
|------|--------|------|
| `AGENTIC_SETTLE_BASE_URL` | `https://app.agenticsettle.io` | 백엔드 URL |
| `AGENTIC_SETTLE_API_KEY` | *(필수)* | 모든 요청에 실리는 `x-api-key` |
| `AGENTIC_SETTLE_TIMEOUT` | `90.0` | HTTP 요청당 타임아웃(초) — grounded 검증이 최대 ~53초까지 걸릴 수 있어 30.0에서 상향됨 |
| `AGENTIC_SETTLE_RETRY_MAX` | `3` | 429/502/503/504·네트워크 오류 재시도 최대 횟수 |
| `AGENTIC_SETTLE_RETRY_BACKOFF` | `5.0,15.0` | 재시도 간 대기(초, 콤마 구분) |
| `AGENTIC_SETTLE_FEEDBACK_URL` | *(미설정)* | 설정 시 `submit_feedback`이 먼저 이 URL로 전송(예: Slack/Notion 웹훅) 후 백엔드로 폴백 |

---

## 보안

- `AGENTIC_SETTLE_API_KEY`는 환경변수에서만 읽습니다 — 하드코딩 없음.
- 키는 오직 HTTPS `x-api-key` 헤더로만 전송되며, 응답이나 로그에 절대 포함되지 않습니다.
- 키가 없으면 모든 tool 호출이 네트워크 요청 없이 즉시 예외를 발생시킵니다.
- **stdio 전송**으로 실행 — 네트워크 포트를 열지 않으며, MCP 호스트 프로세스(Claude, Claude Desktop 등)를 통해서만 통신합니다.
- 이 서버는 어떤 형태로든 돈·토큰·금융자산을 이전하지 않습니다 — 모든 tool은 검증/인시던트 기록의 조회이거나 검증/피드백/이의제기 기록에 대한 쓰기입니다.

### 요청 제한

| 등급 | 엔드포인트 | 제한 |
|------|-----------|------|
| API 키 없음(공개) | 없음 — 여기 있는 모든 tool은 키가 필요함 | — |
| 무료 API 키 | `verify_output` | 키당 하루 50회 |
| 무료 API 키 | 나머지 모든 tool | 일일 quota 없음 — 인증만 필요 |

제한을 초과하면 백엔드가 HTTP 429를 반환합니다. 이 서버는 자동으로 backoff를 적용해 재시도하므로 짧은 버스트는 투명하게 흡수됩니다.

### 장애 대응

이 서버는 HTTP 429/502/503/504 및 네트워크 오류에 대해 자동으로 backoff와 함께 재시도합니다(5초 → 15초, 최대 3회).

### 에러 계약

대부분의 에러는 **예외가 아니라 반환값**입니다 — `{"error": str, "status_code": int}` dict. 예외가 발생하는 경우는 딱 2가지:

1. `AGENTIC_SETTLE_API_KEY`가 없을 때 — 즉시 raise
2. 재시도 소진 후에도 백엔드에 도달 못 할 때 — `RuntimeError` raise

---

## 개인정보 처리방침

전체 정책은 [PRIVACY.md](PRIVACY.md)(영문) 참조 — 이 서버가 AgenticSettle 백엔드로 전송하는 데이터, 사용·보관 방식, 열람·삭제 요청 방법을 담고 있습니다.

---

## FAQ

**Q: 결제 서비스나 금융 처리 기관인가요?**
A: 아닙니다. 이 서버는 돈·토큰·금융자산을 이전할 능력이 전혀 없습니다 — 모든 tool은 검증을 채점·조회하거나 피드백을 기록할 뿐입니다.

**Q: 유료 플랜이 필요한가요?**
A: 아니요 — 이 서버의 모든 tool은 무료입니다. AgenticSettle의 별도 유료 티어(에스크로 연동 정산)는 여기 전혀 노출되지 않습니다.

**Q: 어떤 AI 에이전트를 지원하나요?**
A: MCP 호환 에이전트라면 무엇이든 — Claude, GPT-4o, Gemini, 또는 커스텀 에이전트. VOP는 모델에 중립적입니다 — 결과물을 평가할 뿐, 그걸 만든 모델을 평가하지 않습니다.

**Q: 제출한 콘텐츠는 어떻게 되나요?**
A: [PRIVACY.md](PRIVACY.md) 참조 — 간단히 말해, 검증 점수 계산에만 사용되고 나중에 조회할 수 있도록 저장됩니다.

---

## 라이선스

[MIT](LICENSE)
