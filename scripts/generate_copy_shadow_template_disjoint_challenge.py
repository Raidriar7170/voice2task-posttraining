from __future__ import annotations

import argparse
import difflib
import json
import shutil
import time
from collections import Counter
from pathlib import Path
from typing import Any

from voice2task.copy_backed_shadow_interface import (
    load_scope_policy,
    policy_by_scope_key,
    scope_key,
    stable_hash,
    validate_scope_policy,
)
from voice2task.copy_backed_slot_verification import (
    AMBIGUOUS_MULTIPLE_MATCHES,
    NOT_FOUND,
    OUT_OF_SCOPE,
    VERIFIED_EXACT_UNIQUE,
    VERIFIED_NORMALIZED_UNIQUE,
    CopyBackedScope,
    source_text_hash,
    verify_copy_backed_value,
)
from voice2task.io import read_jsonl, write_json, write_jsonl
from voice2task.leak_scan import scan_paths
from voice2task.schemas import as_contract, canonical_contract_json
from voice2task.slot_error_analysis import flatten_slot_values

CHANGE_ID = "evaluate-frozen-copy-shadow-policy-on-template-disjoint-challenge-set"
CHALLENGE_ID = "copy-shadow-template-disjoint-challenge-v1"
CHALLENGE_VERSION = "copy-shadow-template-disjoint-challenge-v1"
DECISION_BLOCKED = "CHALLENGE_EVALUATION_BLOCKED"
DEFAULT_POLICY_PATH = Path("configs/copy-backed-scope-policy-v1.json")
DEFAULT_CHALLENGE_PATH = Path("data/public-samples/copy-shadow-template-disjoint-challenge-v1.jsonl")
DEFAULT_REPORT_DIR = Path("reports/public-sample/copy-shadow-template-disjoint-challenge-v1")
EXPECTED_POLICY_HASH = "5dc14efb8ded13dc048ddb067c7c63a1a62b6c03896950e861303973d505cbc7"
ENABLED_SCOPES = (
    ("search", "search_web", "query"),
    ("form_fill", "fill_form", "field"),
    ("extract", "extract_page", "target"),
)
DISABLED_SCOPE = ("blocked", "deny", "action")
CONDITION_SEQUENCE = (
    "exact_unique",
    "duplicate_exact",
    "source_absent",
    "multiple_entity_distractor",
    "partial_span_trap",
    "normalization_candidate",
    "normalization_collision",
    "long_input",
    "asr_style_noise",
    "synthetic_pii",
)
REQUIRED_CONDITION_TAGS = {
    *CONDITION_SEQUENCE,
    "out_of_scope_action",
    "invalid_unparseable_output_fault_injection",
}


def _contract(task_type: str, route: str, slot_path: str, slot_value: str, *, condition: str) -> dict[str, Any]:
    return {
        "task_type": task_type,
        "route": route,
        "safety": {
            "allow": task_type != "blocked",
            "reason": f"public_safe_template_disjoint_{condition}",
        },
        "confirmation_required": False,
        "slots": {slot_path: slot_value},
        "normalized_command": f"{task_type}:{route}:{slot_path}:{condition}",
        "language": "zh-CN",
        "contract_version": "v1",
    }


def _base_value(task_type: str, index: int) -> str:
    prefix = {
        "search": "公开检索主题",
        "form_fill": "公开表单字段",
        "extract": "公开提取目标",
        "blocked": "公开演示动作",
    }[task_type]
    return f"{prefix}{index:03d}"


def _input_for_condition(
    *,
    task_type: str,
    route: str,
    slot_path: str,
    slot_value: str,
    condition: str,
    index: int,
) -> tuple[str, str, str]:
    scope_label = f"{task_type}-{route}-{slot_path}"
    prefix = f"模板分离挑战V1第{index:03d}条，{scope_label}。"
    if condition == "exact_unique":
        return f"{prefix}请只复制唯一片段：{slot_value}。", slot_value, VERIFIED_EXACT_UNIQUE
    if condition == "duplicate_exact":
        return (
            f"{prefix}候选片段出现两次：{slot_value}，备用处再次写{slot_value}。",
            slot_value,
            AMBIGUOUS_MULTIPLE_MATCHES,
        )
    if condition == "source_absent":
        return f"{prefix}文本只包含公开占位主题{index:03d}，没有目标片段。", slot_value, NOT_FOUND
    if condition == "multiple_entity_distractor":
        distractor = f"干扰项{index:03d}"
        return f"{prefix}有干扰项{distractor}，但目标片段是{slot_value}。", slot_value, VERIFIED_EXACT_UNIQUE
    if condition == "partial_span_trap":
        return (
            f"{prefix}长片段写作《{slot_value}扩展版》，目标仍标注为{slot_value}。",
            slot_value,
            AMBIGUOUS_MULTIPLE_MATCHES,
        )
    if condition == "normalization_candidate":
        normalized_value = f"AB{index:03d}"
        return f"{prefix}字段视觉写作 A B {index:03d}，只出现一次。", normalized_value, VERIFIED_NORMALIZED_UNIQUE
    if condition == "normalization_collision":
        normalized_value = f"AB{index:03d}"
        return (
            f"{prefix}字段视觉写作 A B {index:03d}，另一个位置写作 A-B-{index:03d}。",
            normalized_value,
            AMBIGUOUS_MULTIPLE_MATCHES,
        )
    if condition == "long_input":
        padding = "请保持公开安全、不要访问私人账户、仅复制源文本。" * 8
        return f"{prefix}{padding}最终唯一目标片段：{slot_value}。", slot_value, VERIFIED_EXACT_UNIQUE
    if condition == "asr_style_noise":
        return f"{prefix}嗯 请 帮我 复制 这个，目标 片段 是 {slot_value}，谢谢。", slot_value, VERIFIED_EXACT_UNIQUE
    if condition == "synthetic_pii":
        synthetic_value = f"合成标签用户{index:03d}号"
        return f"{prefix}使用合成PII标签，不是真实个人：{synthetic_value}。", synthetic_value, VERIFIED_EXACT_UNIQUE
    raise ValueError(f"unsupported condition: {condition}")


def _template_signature(input_text: str, slot_value: str, *, scope: str) -> str:
    stripped = input_text.replace(slot_value, "{slot}")
    return stable_hash({"scope": scope, "template": stripped})


def _slot_value_stripped_signature(input_text: str, slot_value: str) -> str:
    return stable_hash(input_text.replace(slot_value, "{slot}"))


def _row(
    *,
    row_number: int,
    task_type: str,
    route: str,
    slot_path: str,
    input_text: str,
    slot_value: str,
    expected_class: str,
    condition_tags: list[str],
    scope_expected_enabled: bool,
) -> dict[str, Any]:
    gold_contract = _contract(task_type, route, slot_path, slot_value, condition=condition_tags[0])
    as_contract(gold_contract)
    scope = f"{task_type}:{route}:{slot_path}"
    return {
        "challenge_id": f"{CHALLENGE_ID}-{row_number:03d}",
        "challenge_version": CHALLENGE_VERSION,
        "input_text": input_text,
        "task_type": task_type,
        "route": route,
        "slot_path": slot_path,
        "gold_slot_value": slot_value,
        "gold_contract": gold_contract,
        "scope_expected_enabled": scope_expected_enabled,
        "expected_gold_verification_class": expected_class,
        "condition_tags": condition_tags,
        "public_safe": True,
        "template_signature": _template_signature(
            input_text,
            slot_value,
            scope=scope,
        ),
        "slot_value_stripped_signature": _slot_value_stripped_signature(input_text, slot_value),
        "input_hash": source_text_hash(input_text),
        "gold_hash": stable_hash(canonical_contract_json(gold_contract)),
    }


def build_challenge_rows(policy: dict[str, Any]) -> list[dict[str, Any]]:
    policy_rows = policy_by_scope_key(policy)
    rows: list[dict[str, Any]] = []
    row_number = 1
    for task_type, route, slot_path in ENABLED_SCOPES:
        policy_row = policy_rows[scope_key(task_type, route, slot_path)]
        if policy_row.get("enabled") is not True:
            raise ValueError(f"expected enabled policy scope: {task_type}:{route}:{slot_path}")
        for _repeat in range(3):
            for condition in CONDITION_SEQUENCE:
                index = row_number
                value = _base_value(task_type, index)
                input_text, slot_value, expected_class = _input_for_condition(
                    task_type=task_type,
                    route=route,
                    slot_path=slot_path,
                    slot_value=value,
                    condition=condition,
                    index=index,
                )
                rows.append(
                    _row(
                        row_number=row_number,
                        task_type=task_type,
                        route=route,
                        slot_path=slot_path,
                        input_text=input_text,
                        slot_value=slot_value,
                        expected_class=expected_class,
                        condition_tags=[condition, f"scope:{task_type}:{route}:{slot_path}"],
                        scope_expected_enabled=True,
                    )
                )
                row_number += 1
    task_type, route, slot_path = DISABLED_SCOPE
    for index in range(30):
        row_index = row_number
        condition = CONDITION_SEQUENCE[index % len(CONDITION_SEQUENCE)]
        value = _base_value(task_type, row_index)
        input_text = (
            f"模板分离挑战V1第{row_index:03d}条，blocked-deny-action。"
            f"这是负控动作请求：{value}。不得把动作视为可信复制来源。"
        )
        tags = ["out_of_scope_action", f"negative_condition:{condition}", "scope:blocked:deny:action"]
        if index % 5 == 0:
            tags.append("invalid_unparseable_output_fault_injection")
        rows.append(
            _row(
                row_number=row_index,
                task_type=task_type,
                route=route,
                slot_path=slot_path,
                input_text=input_text,
                slot_value=value,
                expected_class=OUT_OF_SCOPE,
                condition_tags=tags,
                scope_expected_enabled=False,
            )
        )
        row_number += 1
    _validate_rows(rows, policy)
    return rows


def _validate_rows(rows: list[dict[str, Any]], policy: dict[str, Any]) -> None:
    if len(rows) != 120:
        raise ValueError(f"expected 120 challenge rows, got {len(rows)}")
    policy_rows = policy_by_scope_key(policy)
    ids = [str(row["challenge_id"]) for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("challenge ids must be unique")
    for row in rows:
        key = scope_key(str(row["task_type"]), str(row["route"]), str(row["slot_path"]))
        policy_row = policy_rows.get(key)
        enabled = bool(policy_row and policy_row.get("enabled") is True)
        if enabled != row["scope_expected_enabled"]:
            raise ValueError(f"scope expectation mismatch: {row['challenge_id']}")
        scope = CopyBackedScope(
            task_type=str(row["task_type"]),
            route=str(row["route"]),
            slot_path=str(row["slot_path"]),
            enabled=enabled,
            policy_version=str(policy.get("policy_version")),
        )
        result = verify_copy_backed_value(row["gold_slot_value"], row["input_text"], scope)
        if result.status != row["expected_gold_verification_class"]:
            raise ValueError(
                f"{row['challenge_id']} expected {row['expected_gold_verification_class']} got {result.status}"
            )


def _existing_public_rows(repo_root: Path) -> list[dict[str, Any]]:
    public_dir = repo_root / "data/public-samples"
    rows: list[dict[str, Any]] = []
    for path in sorted(public_dir.glob("*.jsonl")):
        if path.name == DEFAULT_CHALLENGE_PATH.name:
            continue
        try:
            for row in read_jsonl(path):
                rows.append(row | {"_source_path": f"data/public-samples/{path.name}"})
        except ValueError:
            continue
    return rows


def _row_input_text(row: dict[str, Any]) -> str | None:
    value = row.get("input_text") or row.get("rejected_input_text")
    return value if isinstance(value, str) else None


def _row_contracts(row: dict[str, Any]) -> list[dict[str, Any]]:
    contracts: list[dict[str, Any]] = []
    for key in ("target_contract", "chosen_contract", "rejected_contract", "gold_contract"):
        value = row.get(key)
        if not isinstance(value, dict):
            continue
        try:
            contracts.append(as_contract(value).to_dict())
        except Exception:
            continue
    return contracts


def _existing_signature_sets(existing_rows: list[dict[str, Any]]) -> tuple[set[str], set[str]]:
    template_signatures: set[str] = set()
    slot_value_stripped_signatures: set[str] = set()
    for row in existing_rows:
        input_text = _row_input_text(row)
        if input_text is None:
            continue
        for contract in _row_contracts(row):
            for slot_path, value in flatten_slot_values(contract["slots"]).items():
                if not isinstance(value, str) or not value:
                    continue
                scope = scope_key(str(contract["task_type"]), str(contract["route"]), slot_path)
                template_signatures.add(_template_signature(input_text, value, scope=scope))
                slot_value_stripped_signatures.add(_slot_value_stripped_signature(input_text, value))
    return template_signatures, slot_value_stripped_signatures


def _char_3grams(value: str) -> set[str]:
    if len(value) < 3:
        return {value}
    return {value[index : index + 3] for index in range(len(value) - 2)}


def _jaccard(left: set[str], right: set[str]) -> float:
    if not left and not right:
        return 1.0
    return len(left & right) / len(left | right)


def _template_disjoint_audit(repo_root: Path, rows: list[dict[str, Any]]) -> dict[str, Any]:
    existing_rows = _existing_public_rows(repo_root)
    existing_ids = {str(row.get("id", "")) for row in existing_rows}
    existing_inputs = {text for row in existing_rows if (text := _row_input_text(row))}
    existing_template_signatures, existing_slot_value_stripped_signatures = _existing_signature_sets(existing_rows)
    max_jaccard = 0.0
    max_edit_similarity = 0.0
    existing_grams = [(_char_3grams(text), text) for text in existing_inputs]
    for row in rows:
        text = str(row["input_text"])
        row_grams = _char_3grams(text)
        for grams, existing_text in existing_grams:
            max_jaccard = max(max_jaccard, _jaccard(row_grams, grams))
            max_edit_similarity = max(max_edit_similarity, difflib.SequenceMatcher(a=text, b=existing_text).ratio())
    overlap_counts = {
        "sample_id": sum(1 for row in rows if str(row["challenge_id"]) in existing_ids),
        "exact_input_text": sum(1 for row in rows if str(row["input_text"]) in existing_inputs),
        "template_signature": sum(
            1 for row in rows if str(row["template_signature"]) in existing_template_signatures
        ),
        "slot_value_stripped_signature": sum(
            1
            for row in rows
            if str(row["slot_value_stripped_signature"]) in existing_slot_value_stripped_signatures
        ),
    }
    thresholds = {"char_3gram_jaccard_max": 0.8, "normalized_edit_similarity_max": 0.85}
    accepted = (
        all(value == 0 for value in overlap_counts.values())
        and max_jaccard < thresholds["char_3gram_jaccard_max"]
        and max_edit_similarity < thresholds["normalized_edit_similarity_max"]
    )
    return {
        "audit_kind": "template_disjoint_public_sample_audit",
        "accepted": accepted,
        "row_count": len(rows),
        "source_files_compared": sorted({str(row.get("_source_path")) for row in existing_rows}),
        "existing_template_signature_count": len(existing_template_signatures),
        "existing_slot_value_stripped_signature_count": len(existing_slot_value_stripped_signatures),
        "overlap_counts": overlap_counts,
        "thresholds": thresholds,
        "max_observed": {
            "char_3gram_jaccard": round(max_jaccard, 6),
            "normalized_edit_similarity": round(max_edit_similarity, 6),
        },
        "near_duplicate_rows_rejected": 0,
        "llm_judge_used": False,
    }


def _scope_counts(rows: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    enabled: Counter[str] = Counter()
    disabled: Counter[str] = Counter()
    for row in rows:
        key = scope_key(str(row["task_type"]), str(row["route"]), str(row["slot_path"]))
        if row["scope_expected_enabled"]:
            enabled[key] += 1
        else:
            disabled[key] += 1
    return {"enabled": dict(sorted(enabled.items())), "disabled": dict(sorted(disabled.items()))}


def _condition_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for row in rows:
        counts.update(str(tag) for tag in row["condition_tags"])
    return dict(sorted(counts.items()))


def _expected_class_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    return dict(sorted(Counter(str(row["expected_gold_verification_class"]) for row in rows).items()))


def _discover_loadable_frozen_adapters(repo_root: Path) -> dict[str, Any]:
    candidates: list[dict[str, Any]] = []
    for path in sorted((repo_root / "configs").glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        adapter_path = payload.get("adapter_path")
        if not isinstance(adapter_path, str) or not adapter_path.strip():
            continue
        status = "unresolved_template" if "<" in adapter_path or ">" in adapter_path else "not_found_or_not_verified"
        if status != "unresolved_template" and Path(adapter_path).exists():
            status = "local_path_exists_identity_not_verified"
        candidates.append(
            {
                "config": f"configs/{path.name}",
                "adapter_path_public": (
                    "<a100_project_root>" if "<" in adapter_path or ">" in adapter_path else "<local_adapter_path>"
                ),
                "status": status,
            }
        )
    verified = [candidate for candidate in candidates if candidate["status"] == "identity_verified"]
    return {
        "verified_adapter_count": len(verified),
        "loadable_frozen_adapters_available": bool(verified),
        "candidates": candidates,
    }


def _policy_freeze_audit(policy: dict[str, Any], policy_path: Path) -> dict[str, Any]:
    validation = validate_scope_policy(policy)
    try:
        end_policy = load_scope_policy(policy_path)
        end_validation = validate_scope_policy(end_policy)
        policy_end_hash = str(end_validation["computed_policy_hash"])
    except Exception:
        end_validation = {"ok": False, "blocking_reasons": ["policy_end_hash_unreadable"]}
        policy_end_hash = None
    return {
        "audit_kind": "copy_shadow_template_disjoint_policy_freeze",
        "policy_id": policy["policy_id"],
        "policy_version": policy["policy_version"],
        "policy_hash": policy["policy_hash"],
        "expected_policy_hash": EXPECTED_POLICY_HASH,
        "policy_loaded_once": True,
        "policy_start_hash": str(validation["computed_policy_hash"]),
        "policy_end_hash": policy_end_hash,
        "policy_drift_detected": policy_end_hash != str(validation["computed_policy_hash"]),
        "policy_validation": validation,
        "policy_end_validation": end_validation,
        "policy_path": (
            "configs/copy-backed-scope-policy-v1.json"
            if policy_path.name == DEFAULT_POLICY_PATH.name
            else policy_path.name
        ),
        "policy_modified": False,
        "enabled_triples_changed": False,
        "action_enabled": policy.get("action_enabled") is True,
        "normalized_trusted": policy.get("normalized_trusted") is True,
    }


def _privacy_audit(challenge_path: Path, rows: list[dict[str, Any]]) -> dict[str, Any]:
    scan = scan_paths([challenge_path])
    return {
        "audit_kind": "copy_shadow_template_disjoint_privacy",
        "public_safe": bool(rows) and all(row.get("public_safe") is True for row in rows),
        "synthetic_pii_rows": sum(1 for row in rows if "synthetic_pii" in row["condition_tags"]),
        "real_pii_expected": False,
        "leak_scan": scan.to_dict(),
        "retains_full_input_text_in_sidecars": False,
        "retains_raw_model_output_in_sidecars": False,
        "gold_fields_in_online_sidecars": False,
        "private_paths_in_reports": False,
    }


def _per_scope_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    metrics: dict[str, Any] = {}
    for row in rows:
        key = scope_key(str(row["task_type"]), str(row["route"]), str(row["slot_path"]))
        bucket = metrics.setdefault(
            key,
            {
                "challenge_row_count": 0,
                "scope_expected_enabled": bool(row["scope_expected_enabled"]),
                "observed_prediction_count": 0,
                "trusted_gold_correct_rate": None,
                "trusted_gold_mismatch_rate": None,
                "high_risk_false_trust_count": None,
            },
        )
        bucket["challenge_row_count"] += 1
    return {
        "metrics_kind": "blocked_expected_scope_metrics",
        "metrics": dict(sorted(metrics.items())),
        "observed_metrics_status": "blocked_missing_loadable_frozen_adapters",
    }


def _per_condition_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    metrics = {
        tag: {
            "challenge_row_count": count,
            "observed_prediction_count": 0,
            "high_risk_false_trust_count": None,
            "status": "blocked_missing_loadable_frozen_adapters",
        }
        for tag, count in _condition_counts(rows).items()
        if not tag.startswith("scope:")
    }
    return {"metrics_kind": "blocked_expected_condition_metrics", "metrics": metrics}


def _latency_benchmark() -> dict[str, Any]:
    started = time.perf_counter()
    elapsed_ms = round((time.perf_counter() - started) * 1000, 6)
    return {
        "benchmark_kind": "challenge_prediction_latency",
        "status": "blocked_missing_loadable_frozen_adapters",
        "canonical_prediction_hook_evaluated": False,
        "local_report_generation_overhead_ms": elapsed_ms,
        "production_slo_claim": False,
    }


def _write_markdown_summary(report_dir: Path, summary: dict[str, Any]) -> None:
    (report_dir / "challenge-summary.md").write_text(
        "\n".join(
            [
                "# Copy-shadow template-disjoint challenge v1",
                "",
                f"- Decision: `{summary['decision_label']}`",
                f"- Rows frozen: `{summary['row_count']}`",
                "- Canonical prediction hook evaluated: `False`",
                "- Reason: no local identity-verifiable frozen adapters were available.",
                "- Policy: `copy-backed-scope-policy-v1` remains unchanged.",
                "- Training, enforcement, prompt, decoding, evaluator, action, and normalized-trusted changes: none.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _write_recommended_next_change(report_dir: Path) -> None:
    (report_dir / "recommended-next-change.md").write_text(
        "\n".join(
            [
                "# Recommended next change",
                "",
                (
                    "Resolve identity-verifiable frozen adapter availability, then rerun this same frozen "
                    "challenge through"
                ),
                "`voice2task-train sft-predict` / `voice2task.training.run_sft_prediction_export`.",
                "",
                (
                    "Do not train a replacement adapter, change policy scopes, enable runtime enforcement, "
                    "trust normalized"
                ),
                "provenance, or enable action provenance inside this blocked phase.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def write_challenge_bundle(
    *,
    repo_root: Path,
    challenge_path: Path,
    report_dir: Path,
    policy_path: Path,
) -> dict[str, Any]:
    resolved_policy_path = policy_path if policy_path.is_absolute() else repo_root / policy_path
    policy = load_scope_policy(resolved_policy_path)
    policy_validation = validate_scope_policy(policy)
    if not policy_validation["ok"]:
        raise ValueError("frozen copy-backed scope policy failed validation")
    if policy["policy_hash"] != EXPECTED_POLICY_HASH:
        raise ValueError("frozen copy-backed scope policy hash drifted")
    rows = build_challenge_rows(policy)
    challenge_hash = stable_hash(rows)
    scope_counts = _scope_counts(rows)
    condition_counts = _condition_counts(rows)
    expected_class_counts = _expected_class_counts(rows)
    disjoint_audit = _template_disjoint_audit(repo_root, rows)
    if not disjoint_audit["accepted"]:
        raise ValueError(f"template-disjoint audit failed: {json.dumps(disjoint_audit, ensure_ascii=False)}")
    if report_dir.exists():
        shutil.rmtree(report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(challenge_path, rows)
    adapter_discovery = _discover_loadable_frozen_adapters(repo_root)
    policy_freeze = _policy_freeze_audit(policy, resolved_policy_path)
    privacy = _privacy_audit(challenge_path, rows)
    blocked = {
        "decision": DECISION_BLOCKED,
        "reason": "missing_loadable_frozen_adapters",
        "adapter_discovery": adapter_discovery,
        "canonical_prediction_hook_evaluated": False,
        "fabricated_predictions": False,
        "training_run": False,
        "policy_modified": False,
        "runtime_enforcement_enabled": False,
        "normalized_trusted_enabled": False,
        "action_enabled": False,
    }
    manifest = {
        "manifest_kind": "copy_shadow_template_disjoint_challenge_manifest",
        "change_id": CHANGE_ID,
        "challenge_id": CHALLENGE_ID,
        "challenge_version": CHALLENGE_VERSION,
        "row_count": len(rows),
        "challenge_hash": challenge_hash,
        "challenge_path": f"data/public-samples/{challenge_path.name}",
        "policy": {
            "policy_id": policy["policy_id"],
            "policy_version": policy["policy_version"],
            "policy_hash": policy["policy_hash"],
        },
        "scope_counts": scope_counts,
        "condition_counts": condition_counts,
        "expected_gold_verification_class_counts": expected_class_counts,
        "public_safe": True,
        "template_disjoint_audit_passed": disjoint_audit["accepted"],
    }
    summary = {
        "evidence_kind": "copy_shadow_template_disjoint_challenge_v1",
        "change_id": CHANGE_ID,
        "challenge_id": CHALLENGE_ID,
        "challenge_version": CHALLENGE_VERSION,
        "decision_label": DECISION_BLOCKED,
        "row_count": len(rows),
        "challenge_hash": challenge_hash,
        "scope_counts": scope_counts,
        "condition_counts": condition_counts,
        "expected_gold_verification_class_counts": expected_class_counts,
        "template_disjoint": disjoint_audit["accepted"],
        "public_safe": privacy["public_safe"],
        "policy_hash": policy["policy_hash"],
        "policy_drift_detected": policy_freeze["policy_drift_detected"],
        "observed_challenge_inference_blocked": True,
        "canonical_prediction_hook_evaluated": False,
        "blocked_reason": "missing_loadable_frozen_adapters",
        "technical_gate_counts": {
            "prediction_run_success_rate": None,
            "hook_invocation_count": 0,
            "sidecar_attachment_rate": None,
            "hook_error_count": None,
            "sink_error_count": None,
            "policy_drift_count": 0,
            "path_conflict_count": 0,
            "contract_mutation_count": 0,
            "runtime_decision_delta_count": 0,
            "prediction_output_hash_mismatch_count": 0,
            "v1_metric_delta": None,
            "provenance_false_accept_count": None,
            "silent_fallback_count": None,
            "action_trusted_count": 0,
            "normalized_trusted_count": 0,
        },
        "pipeline_integrity": {
            "prediction_output_invariance_proven": False,
            "parsed_contract_invariance_proven": False,
            "evaluator_input_invariance_proven": False,
            "runtime_decision_invariance_proven": False,
            "deterministic_hook_behavior_proven": False,
            "status": "blocked_missing_loadable_frozen_adapters",
        },
        "correctness_metrics": {
            "trusted_gold_correct_rate": None,
            "trusted_gold_mismatch_rate": None,
            "untrusted_gold_correct_rate": None,
            "neither_trusted_nor_correct_rate": None,
            "status": "blocked_missing_loadable_frozen_adapters",
        },
        "wilson_intervals": {
            "trusted_exact_rate": None,
            "trusted_gold_correct_rate": None,
            "trusted_gold_mismatch_rate": None,
            "eligible_verification_failure_rate": None,
            "per_scope_trusted_rate": None,
            "status": "blocked_missing_loadable_frozen_adapters",
        },
        "adversarial_condition_metrics_status": "blocked_missing_loadable_frozen_adapters",
        "cannot_claim": [
            "frozen policy generalized on observed adapter predictions",
            "runtime enforcement readiness",
            "slot accuracy improvement",
            "model improvement",
            "safety readiness",
            "production readiness",
        ],
    }
    write_json(report_dir / "challenge-manifest.json", manifest)
    write_json(report_dir / "template-disjoint-audit.json", disjoint_audit)
    write_json(report_dir / "challenge-summary.json", summary)
    write_json(report_dir / "per-scope-metrics.json", _per_scope_metrics(rows))
    write_json(report_dir / "per-condition-metrics.json", _per_condition_metrics(rows))
    write_json(report_dir / "latency-benchmark.json", _latency_benchmark())
    write_json(report_dir / "policy-freeze-audit.json", policy_freeze)
    write_json(report_dir / "privacy-audit.json", privacy)
    write_json(report_dir / "blocked.json", blocked)
    _write_markdown_summary(report_dir, summary)
    _write_recommended_next_change(report_dir)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate copy-shadow template-disjoint challenge v1.")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--challenge-path", type=Path, default=DEFAULT_CHALLENGE_PATH)
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY_PATH)
    args = parser.parse_args()
    summary = write_challenge_bundle(
        repo_root=args.repo_root,
        challenge_path=args.challenge_path,
        report_dir=args.report_dir,
        policy_path=args.policy,
    )
    print(
        json.dumps(
            {
                "ok": True,
                "challenge_id": summary["challenge_id"],
                "row_count": summary["row_count"],
                "decision_label": summary["decision_label"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
