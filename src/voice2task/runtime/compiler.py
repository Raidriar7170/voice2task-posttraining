from __future__ import annotations

import hashlib
import json
from datetime import timedelta
from typing import Any

from voice2task.runtime.capabilities import CAPABILITY_REGISTRY, REGISTRY_VERSION
from voice2task.runtime.models import (
    ActionKind,
    BrowserTaskContractPayload,
    CheckType,
    CompileResult,
    ExecutionAction,
    ExecutionPlan,
    Postcondition,
    SessionContext,
)


def _rejected(code: str, message: str) -> CompileResult:
    return CompileResult(outcome="rejected", reason_code=code, message=message)


def _validate_slots(
    slots: dict[str, Any], *, required: frozenset[str], optional: frozenset[str] = frozenset()
) -> str | None:
    keys = frozenset(slots)
    if not required.issubset(keys) or not keys.issubset(required | optional):
        return "UNKNOWN_SLOT"
    if any(not isinstance(value, str) or not value.strip() for value in slots.values()):
        return "INVALID_SLOT_VALUE"
    return None


def _plan_id(contract: BrowserTaskContractPayload, context: SessionContext) -> str:
    material = {
        "contract": contract.model_dump(mode="json"),
        "context": context.model_dump(mode="json"),
        "registry_version": REGISTRY_VERSION,
    }
    encoded = json.dumps(material, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return f"plan-{hashlib.sha256(encoded.encode()).hexdigest()[:32]}"


def _make_plan(
    contract: BrowserTaskContractPayload,
    context: SessionContext,
    *,
    capability_id: str | None,
    actions: list[ExecutionAction],
    postconditions: list[Postcondition],
) -> ExecutionPlan:
    return ExecutionPlan(
        plan_id=_plan_id(contract, context),
        session_id=context.session_id,
        plan_version=context.plan_version,
        route=contract.route,
        capability_id=capability_id,
        requires_confirmation=contract.confirmation_required,
        actions=actions,
        postconditions=postconditions,
        expires_at=context.plan_issued_at + timedelta(minutes=5),
    )


def compile_contract_to_plan(
    contract: BrowserTaskContractPayload, context: SessionContext
) -> CompileResult:
    task_type = contract.task_type
    slots = contract.slots
    capability_id: str | None
    actions: list[ExecutionAction]
    postconditions: list[Postcondition]

    if task_type == "search":
        error = _validate_slots(slots, required=frozenset({"query"}))
        if error:
            return _rejected(error, "Search requires exactly one non-empty query slot.")
        capability_id = "demo_search"
        actions = [
            ExecutionAction(
                action_id="action-1",
                kind=ActionKind.NAVIGATE,
                capability_id=capability_id,
            ),
            ExecutionAction(
                action_id="action-2",
                kind=ActionKind.FILL,
                capability_id=capability_id,
                locator_id="query_input",
                value_source="contract.slots.query",
            ),
            ExecutionAction(
                action_id="action-3",
                kind=ActionKind.CLICK,
                capability_id=capability_id,
                locator_id="search_button",
            ),
        ]
        postconditions = [
            Postcondition(check_type=CheckType.URL_MATCHES, capability_id=capability_id),
            Postcondition(
                check_type=CheckType.FIELD_VALUE_EQUALS,
                capability_id=capability_id,
                locator_id="query_input",
                expected_source="contract.slots.query",
            ),
            Postcondition(
                check_type=CheckType.RESULTS_CONTAIN,
                capability_id=capability_id,
                locator_id="results",
                expected_source="contract.slots.query",
            ),
        ]
    elif task_type == "navigate":
        error = _validate_slots(slots, required=frozenset({"url"}))
        if error:
            return _rejected(error, "Navigate requires exactly one non-empty URL alias.")
        if slots["url"] not in CAPABILITY_REGISTRY["demo_help"].aliases:
            return _rejected("CAPABILITY_NOT_ALLOWLISTED", "Navigation alias is not allowlisted.")
        capability_id = "demo_help"
        actions = [
            ExecutionAction(
                action_id="action-1",
                kind=ActionKind.NAVIGATE,
                capability_id=capability_id,
            )
        ]
        postconditions = [
            Postcondition(check_type=CheckType.URL_MATCHES, capability_id=capability_id),
            Postcondition(
                check_type=CheckType.TEXT_EQUALS,
                capability_id=capability_id,
                locator_id="heading",
                expected_source="registry.heading",
            ),
        ]
    elif task_type == "extract":
        error = _validate_slots(slots, required=frozenset({"target"}))
        if error:
            return _rejected(error, "Extract requires exactly one non-empty target slot.")
        if slots["target"] not in CAPABILITY_REGISTRY["demo_product"].aliases:
            return _rejected("CAPABILITY_NOT_ALLOWLISTED", "Extraction target is not allowlisted.")
        capability_id = "demo_product"
        actions = [
            ExecutionAction(
                action_id="action-1",
                kind=ActionKind.NAVIGATE,
                capability_id=capability_id,
            ),
            ExecutionAction(
                action_id="action-2",
                kind=ActionKind.EXTRACT_TEXT,
                capability_id=capability_id,
                locator_id="product_price",
                value_source="execution.action_outputs.product_price",
            ),
        ]
        postconditions = [
            Postcondition(check_type=CheckType.URL_MATCHES, capability_id=capability_id),
            Postcondition(
                check_type=CheckType.TEXT_EQUALS,
                capability_id=capability_id,
                locator_id="product_price",
                expected_source="registry.expected.product_price",
            ),
        ]
    elif task_type == "form_fill":
        error = _validate_slots(slots, required=frozenset({"field"}))
        if error:
            return _rejected(error, "Form fill requires exactly one non-empty field slot.")
        if slots["field"] not in CAPABILITY_REGISTRY["demo_profile_form"].aliases:
            return _rejected("CAPABILITY_NOT_ALLOWLISTED", "Form field is not allowlisted.")
        capability_id = "demo_profile_form"
        actions = [
            ExecutionAction(
                action_id="action-1",
                kind=ActionKind.NAVIGATE,
                capability_id=capability_id,
            ),
            ExecutionAction(
                action_id="action-2",
                kind=ActionKind.FILL,
                capability_id=capability_id,
                locator_id="email_input",
                value_source="session.profile.email",
            ),
        ]
        postconditions = [
            Postcondition(
                check_type=CheckType.FIELD_VALUE_EQUALS,
                capability_id=capability_id,
                locator_id="email_input",
                expected_source="session.profile.email",
            )
        ]
    elif task_type == "clarify":
        error = _validate_slots(slots, required=frozenset({"ambiguity"}))
        if error:
            return _rejected(error, "Clarify requires one known ambiguity slot.")
        plan = _make_plan(
            contract,
            context,
            capability_id=None,
            actions=[],
            postconditions=[Postcondition(check_type=CheckType.NO_EXECUTION, capability_id="clarify")],
        )
        return CompileResult(
            outcome="clarification_required",
            plan=plan,
            reason_code="CLARIFICATION_REQUIRED",
            message="More information is required; no browser will be started.",
        )
    elif task_type == "blocked":
        error = _validate_slots(
            slots,
            required=frozenset({"reason"}),
            optional=frozenset({"action"}),
        )
        if error:
            return _rejected(error, "Blocked requests require known reason/action slots.")
        if slots["reason"] != "payment_requires_user_control":
            return _rejected("CAPABILITY_NOT_ALLOWLISTED", "Blocked reason is not recognized.")
        plan = _make_plan(
            contract,
            context,
            capability_id=None,
            actions=[],
            postconditions=[Postcondition(check_type=CheckType.NO_EXECUTION, capability_id="blocked")],
        )
        return CompileResult(
            outcome="blocked",
            plan=plan,
            reason_code="UNSAFE_PAYMENT",
            message="Payment remains under user control; no browser will be started.",
        )
    else:
        return _rejected("CAPABILITY_NOT_ALLOWLISTED", "Task type is not executable.")

    if context.selected_capability not in {None, capability_id}:
        return _rejected("CAPABILITY_CONTEXT_MISMATCH", "Selected capability does not match the contract.")
    plan = _make_plan(
        contract,
        context,
        capability_id=capability_id,
        actions=actions,
        postconditions=postconditions,
    )
    return CompileResult(outcome="ready", plan=plan, message="Controlled plan compiled.")
