from __future__ import annotations

import hashlib

from voice2task.runtime.capabilities import CAPABILITY_REGISTRY
from voice2task.runtime.models import (
    BrowserTaskContractPayload,
    CheckType,
    ExecutionOutcome,
    ExecutionPlan,
    SessionContext,
    VerificationCheck,
    VerificationResult,
)


def _check(
    check_type: CheckType,
    *,
    passed: bool,
    expected: str,
    observed: str,
    evidence_ref: str | None = None,
) -> VerificationCheck:
    return VerificationCheck(
        check_type=check_type,
        passed=passed,
        expected=expected,
        observed=observed,
        evidence_ref=evidence_ref,
    )


def verify_execution(
    plan: ExecutionPlan,
    contract: BrowserTaskContractPayload,
    context: SessionContext,
    outcome: ExecutionOutcome,
) -> VerificationResult:
    checks: list[VerificationCheck] = []
    if plan.route in {"deny", "clarify"}:
        expected = "browser_context_created=false;action_count=0"
        observed = (
            f"browser_context_created={str(outcome.browser_context_created).lower()};"
            f"action_count={outcome.action_count}"
        )
        checks.append(
            _check(
                CheckType.NO_EXECUTION,
                passed=not outcome.browser_context_created and outcome.action_count == 0,
                expected=expected,
                observed=observed,
            )
        )
    elif plan.capability_id is None or plan.capability_id not in CAPABILITY_REGISTRY:
        checks.append(
            _check(
                CheckType.NO_EXECUTION,
                passed=False,
                expected="allowlisted capability",
                observed="missing or unknown capability",
            )
        )
    else:
        capability = CAPABILITY_REGISTRY[plan.capability_id]
        checks.append(
            _check(
                CheckType.URL_MATCHES,
                passed=outcome.final_url_path == capability.path,
                expected=capability.path,
                observed=outcome.final_url_path or "<none>",
            )
        )
        if plan.capability_id == "demo_search":
            query = str(contract.slots["query"])
            field_value = outcome.values.get("query_input", "")
            results = outcome.values.get("results", "")
            checks.extend(
                [
                    _check(
                        CheckType.FIELD_VALUE_EQUALS,
                        passed=field_value == query,
                        expected=query,
                        observed=field_value,
                    ),
                    _check(
                        CheckType.RESULTS_CONTAIN,
                        passed=query in results,
                        expected=f"contains:{query}",
                        observed=results,
                    ),
                ]
            )
        elif plan.capability_id == "demo_help":
            heading = outcome.values.get("heading", "")
            expected_heading = capability.heading or ""
            checks.append(
                _check(
                    CheckType.TEXT_EQUALS,
                    passed=heading == expected_heading,
                    expected=expected_heading,
                    observed=heading,
                )
            )
        elif plan.capability_id == "demo_product":
            extracted = outcome.values.get("product_price", "")
            dom_value = outcome.values.get("product_price_dom", "")
            content_hash = hashlib.sha256(dom_value.encode()).hexdigest()
            checks.append(
                _check(
                    CheckType.TEXT_EQUALS,
                    passed=bool(extracted) and extracted == dom_value,
                    expected=dom_value or "non-empty DOM product price",
                    observed=extracted,
                    evidence_ref=f"locator:product_price;sha256:{content_hash}",
                )
            )
        elif plan.capability_id == "demo_profile_form":
            observed_email = outcome.values.get("email_input", "")
            expected_email = context.profile.email
            checks.append(
                _check(
                    CheckType.FIELD_VALUE_EQUALS,
                    passed=observed_email == expected_email,
                    expected=expected_email,
                    observed=observed_email,
                )
            )
    passed = bool(checks) and all(check.passed for check in checks)
    return VerificationResult(
        passed=passed,
        checks=checks,
        failure_code=None if passed else "VERIFICATION_FAILED",
    )
