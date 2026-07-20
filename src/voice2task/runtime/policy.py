from __future__ import annotations

from datetime import datetime, timezone

from voice2task.runtime.capabilities import CAPABILITY_REGISTRY
from voice2task.runtime.models import ExecutionPlan, PolicyResult

ALLOWED_VALUE_SOURCES = frozenset(
    {
        None,
        "contract.slots.query",
        "execution.values.product_price",
        "session.profile.email",
    }
)
ALLOWED_ROUTES = frozenset({"search_web", "open_url", "extract_page", "fill_form"})


def _blocked(code: str, message: str, *, requires_confirmation: bool = False) -> PolicyResult:
    return PolicyResult(
        allowed=False,
        requires_confirmation=requires_confirmation,
        reason_code=code,
        message=message,
    )


def evaluate_policy(
    plan: ExecutionPlan,
    *,
    now: datetime | None = None,
    confirmation_consumed: bool = False,
) -> PolicyResult:
    current = now or datetime.now(timezone.utc)
    if current > plan.expires_at:
        return _blocked("PLAN_EXPIRED", "The controlled plan has expired.")
    if plan.route == "deny":
        return _blocked("UNSAFE_PAYMENT", "Payment execution is not allowed.")
    if plan.route == "clarify":
        return _blocked("CLARIFICATION_REQUIRED", "Clarification is required before any execution.")
    if plan.route not in ALLOWED_ROUTES:
        return _blocked("UNSAFE_ROUTE", "The plan route is not allowlisted.")
    if plan.capability_id is None or plan.capability_id not in CAPABILITY_REGISTRY:
        return _blocked("CAPABILITY_NOT_ALLOWLISTED", "The plan capability is not allowlisted.")
    capability = CAPABILITY_REGISTRY[plan.capability_id]
    if capability.route != plan.route:
        return _blocked("CAPABILITY_ROUTE_MISMATCH", "The capability does not match the plan route.")
    for action in plan.actions:
        if action.capability_id != plan.capability_id or action.kind not in capability.allowed_actions:
            return _blocked("UNSAFE_ACTION", "The plan contains an action outside the capability registry.")
        if action.locator_id is not None and action.locator_id not in capability.locators:
            return _blocked("LOCATOR_NOT_ALLOWLISTED", "The plan locator is not allowlisted.")
        if action.value_source not in ALLOWED_VALUE_SOURCES:
            return _blocked("VALUE_SOURCE_NOT_ALLOWLISTED", "The plan value source is not allowlisted.")
    if capability.requires_confirmation and not confirmation_consumed:
        return _blocked(
            "CONFIRMATION_REQUIRED",
            "Explicit confirmation is required before this local write.",
            requires_confirmation=True,
        )
    return PolicyResult(
        allowed=True,
        requires_confirmation=capability.requires_confirmation,
        reason_code="POLICY_ALLOWED",
        message="Plan is restricted to an allowlisted localhost capability.",
    )
