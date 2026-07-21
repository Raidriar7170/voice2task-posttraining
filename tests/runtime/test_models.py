from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from voice2task.runtime import models as runtime_models
from voice2task.runtime.models import (
    BrowserTaskContractPayload,
    ExecutionAction,
    ExecutionOutcome,
    SessionContext,
    sanitize_public_payload,
)


def _search_contract() -> dict[str, object]:
    return {
        "task_type": "search",
        "route": "search_web",
        "safety": {"allow": True, "reason": "public_readonly"},
        "confirmation_required": False,
        "slots": {"query": "北京明天天气"},
        "normalized_command": "搜索北京明天天气",
        "language": "zh-CN",
        "contract_version": "v1",
    }


def test_contract_payload_delegates_to_existing_schema_and_semantics() -> None:
    contract = BrowserTaskContractPayload.model_validate(_search_contract())

    assert contract.to_domain().task_type == "search"
    assert contract.validation_status["strict_schema_valid"] is True
    assert contract.validation_status["semantic_valid"] is True


def test_contract_payload_rejects_semantic_mismatch() -> None:
    payload = _search_contract()
    payload["route"] = "open_url"

    with pytest.raises(ValueError, match="semantic"):
        BrowserTaskContractPayload.model_validate(payload)


def test_runtime_models_forbid_selector_and_extra_fields() -> None:
    with pytest.raises(ValidationError):
        ExecutionAction.model_validate(
            {
                "action_id": "action-1",
                "kind": "fill",
                "capability_id": "demo_search",
                "locator_id": "query_input",
                "value_source": "contract.slots.query",
                "timeout_ms": 5000,
                "selector": "#unsafe",
            }
        )

    schema_text = str(ExecutionAction.model_json_schema())
    assert "selector" not in schema_text
    assert "javascript" not in schema_text.lower()


def test_execution_evidence_is_strict_and_replaces_shared_values() -> None:
    evidence_type = getattr(runtime_models, "ExecutionEvidence", None)

    assert evidence_type is not None, "ExecutionEvidence must be a public runtime model"
    evidence = evidence_type(
        action_outputs={"product_price": "¥198.00"},
        dom_snapshot={"product_price": "¥199.00"},
    )
    outcome = ExecutionOutcome(
        browser_context_created=True,
        action_count=2,
        evidence=evidence,
    )

    assert outcome.evidence.action_outputs == {"product_price": "¥198.00"}
    assert outcome.evidence.dom_snapshot == {"product_price": "¥199.00"}
    assert outcome.model_dump(mode="json")["evidence"] == {
        "action_outputs": {"product_price": "¥198.00"},
        "dom_snapshot": {"product_price": "¥199.00"},
    }
    assert "values" not in ExecutionOutcome.model_json_schema()["properties"]
    with pytest.raises(ValidationError):
        evidence_type(
            action_outputs={},
            dom_snapshot={},
            values={"product_price": "¥199.00"},
        )
    with pytest.raises(ValidationError):
        ExecutionOutcome(
            browser_context_created=True,
            action_count=2,
            values={"product_price": "¥199.00"},
        )


@pytest.mark.parametrize("kind", ["login", "upload", "download", "script"])
def test_runtime_action_model_rejects_forbidden_action_kinds(kind: str) -> None:
    with pytest.raises(ValidationError):
        ExecutionAction(
            action_id="unsafe-action",
            kind=kind,
            capability_id="demo_search",
        )


def test_session_context_is_strict_and_timezone_aware() -> None:
    context = SessionContext(
        session_id="session-1",
        profile={"email": "demo@example.com"},
        selected_capability="demo_profile_form",
        plan_version=1,
        plan_issued_at=datetime(2026, 7, 20, tzinfo=timezone.utc),
    )

    assert context.profile.email == "demo@example.com"
    with pytest.raises(ValidationError):
        SessionContext.model_validate({**context.model_dump(), "unexpected": True})
    with pytest.raises(ValidationError):
        SessionContext.model_validate({**context.model_dump(), "plan_issued_at": "2026-07-20"})


def test_public_payload_sanitization_is_recursive() -> None:
    value = {
        "message": "failed at /Users/example/private/model with token=abcdefgh12345678",
        "nested": ["host=my-mac.local pid=4412 GPU-deadbeef-dead-beef-dead-beefdeadbeef"],
        "traceback": "private stack",
    }

    sanitized = sanitize_public_payload(value)

    rendered = str(sanitized)
    assert "/Users/" not in rendered
    assert "abcdefgh12345678" not in rendered
    assert "my-mac.local" not in rendered
    assert "4412" not in rendered
    assert "deadbeef" not in rendered
    assert "traceback" not in sanitized
