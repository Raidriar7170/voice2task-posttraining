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
    extract_failure_code: str | None = None
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
            field_value = outcome.evidence.dom_snapshot.get("query_input", "")
            results = outcome.evidence.dom_snapshot.get("results", "")
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
            heading = outcome.evidence.dom_snapshot.get("heading", "")
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
            extracted = outcome.evidence.action_outputs.get("product_price", "")
            dom_value = outcome.evidence.dom_snapshot.get("product_price", "")
            expected_values = capability.expected_values or {}
            registry_expected = expected_values.get("product_price", "")
            content_hash = hashlib.sha256(dom_value.encode()).hexdigest()
            checks.extend(
                [
                    _check(
                        CheckType.TEXT_EQUALS,
                        passed=bool(extracted),
                        expected="non-empty action output",
                        observed=extracted or "<missing>",
                        evidence_ref="action_output:product_price",
                    ),
                    _check(
                        CheckType.TEXT_EQUALS,
                        passed=bool(dom_value),
                        expected="non-empty DOM snapshot",
                        observed=dom_value or "<missing>",
                        evidence_ref=f"locator:product_price;sha256:{content_hash}",
                    ),
                    _check(
                        CheckType.TEXT_EQUALS,
                        passed=bool(extracted) and bool(dom_value) and extracted == dom_value,
                        expected=dom_value or "<missing DOM snapshot>",
                        observed=extracted or "<missing action output>",
                        evidence_ref="action_output:product_price;dom_snapshot:product_price",
                    ),
                    _check(
                        CheckType.TEXT_EQUALS,
                        passed=bool(dom_value)
                        and bool(registry_expected)
                        and dom_value == registry_expected,
                        expected=registry_expected or "<missing registry expected value>",
                        observed=dom_value or "<missing DOM snapshot>",
                        evidence_ref="registry:demo_product.expected_values.product_price",
                    ),
                ]
            )
            if not extracted:
                extract_failure_code = "EXTRACT_ACTION_OUTPUT_MISSING"
            elif not dom_value:
                extract_failure_code = "EXTRACT_DOM_SNAPSHOT_MISSING"
            elif extracted != dom_value:
                extract_failure_code = "EXTRACT_EVIDENCE_MISMATCH"
            elif dom_value != registry_expected:
                extract_failure_code = "EXTRACT_EXPECTED_VALUE_MISMATCH"
        elif plan.capability_id == "demo_profile_form":
            observed_email = outcome.evidence.dom_snapshot.get("email_input", "")
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
        failure_code=None if passed else extract_failure_code or "VERIFICATION_FAILED",
    )
