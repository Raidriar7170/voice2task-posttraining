from __future__ import annotations

import hashlib
import json
import random
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from voice2task.evaluation import evaluate_predictions
from voice2task.io import read_json, read_jsonl, write_json
from voice2task.layered_evaluation import (
    evaluate_layered_predictions,
    normalize_slot_key,
    normalize_slot_value,
)
from voice2task.leak_scan import scan_paths
from voice2task.schemas import ROUTES, TASK_TYPES, BrowserTaskContract, SFTDatasetRow, ValidationError, as_contract

CORE_FIELDS = ("task_type", "route", "safety", "confirmation_required", "slots")
DERIVED_FIELDS = ("normalized_command", "language", "contract_version")
SUPPORTED_METRIC_REPRODUCTION_STATUSES = {"passed", "reproduced"}
ALLOWED_RECOVERY_METHODS = {"recovered_from_existing_artifacts"}
CONTRIBUTION_CATEGORIES = (
    "NORMALIZED_COMMAND_ONLY",
    "METADATA_ONLY",
    "DERIVED_FIELD_ONLY",
    "CORE_SLOT_FAILURE",
    "CORE_ROUTE_TASK_FAILURE",
    "CORE_SAFETY_CONFIRMATION_FAILURE",
    "MIXED_CORE_FAILURE",
    "INVALID_OR_UNPARSEABLE",
)
ARMS = ("control", "treatment")
SPLITS = ("dev", "test")
BOOTSTRAP_SEED = 20260621
BOOTSTRAP_ITERATIONS = 1000

REQUIRED_RERUN_ARTIFACTS = (
    "source-boundary.json",
    "projection-spec.md",
    "projection-spec.json",
    "field-policy.md",
    "normalized-command-renderer-report.md",
    "normalized-command-renderer-report.json",
    "control/dev-projection-metrics.json",
    "control/test-projection-metrics.json",
    "treatment/dev-projection-metrics.json",
    "treatment/test-projection-metrics.json",
    "failure-contribution-analysis.json",
    "failure-contribution-analysis.md",
    "family-level-projection-deltas.json",
    "bootstrap-analysis.json",
    "decision.md",
    "summary.md",
    "summary.json",
    "recommended-next-change.md",
)

_MISSING = object()


def _copy_jsonable(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False))


def _rate(count: int, total: int) -> float:
    return 0.0 if total == 0 else count / total


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _field_value(value: dict[str, Any], field_path: str) -> Any:
    current: Any = value
    for part in field_path.split("."):
        if not isinstance(current, dict) or part not in current:
            return _MISSING
        current = current[part]
    return current


def _contract_or_none(value: Any) -> BrowserTaskContract | None:
    try:
        return as_contract(value)
    except (TypeError, ValidationError):
        return None


def project_v1_to_v2_core(contract: BrowserTaskContract | dict[str, Any]) -> dict[str, Any]:
    parsed = as_contract(contract)
    return {
        "task_type": parsed.task_type,
        "route": parsed.route,
        "safety": _copy_jsonable(parsed.safety),
        "confirmation_required": parsed.confirmation_required,
        "slots": _copy_jsonable(parsed.slots),
    }


def validate_v2_core(core_contract: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(core_contract, dict):
        raise ValidationError("V2 Core must be an object")
    fields = set(core_contract)
    expected = set(CORE_FIELDS)
    missing = sorted(expected - fields)
    extra = sorted(fields - expected)
    if missing:
        raise ValidationError(f"missing V2 Core fields: {', '.join(missing)}")
    if extra:
        raise ValidationError(f"extra V2 Core fields: {', '.join(extra)}")
    task_type = core_contract["task_type"]
    route = core_contract["route"]
    safety = core_contract["safety"]
    confirmation_required = core_contract["confirmation_required"]
    slots = core_contract["slots"]
    if task_type not in TASK_TYPES:
        raise ValidationError(f"task_type must be one of {sorted(TASK_TYPES)}")
    if route not in ROUTES:
        raise ValidationError(f"route must be one of {sorted(ROUTES)}")
    if not isinstance(safety, dict):
        raise ValidationError("safety must be an object")
    if not isinstance(safety.get("allow"), bool):
        raise ValidationError("safety.allow must be a boolean")
    if not isinstance(safety.get("reason"), str) or not safety["reason"].strip():
        raise ValidationError("safety.reason must be a non-empty string")
    if not isinstance(confirmation_required, bool):
        raise ValidationError("confirmation_required must be a boolean")
    if not isinstance(slots, dict):
        raise ValidationError("slots must be an object")
    return {
        "task_type": task_type,
        "route": route,
        "safety": _copy_jsonable(safety),
        "confirmation_required": confirmation_required,
        "slots": _copy_jsonable(slots),
    }


def canonical_v2_core_json(core_contract: dict[str, Any]) -> str:
    return _canonical_json(validate_v2_core(core_contract))


def _slot_text(slots: dict[str, Any], key: str) -> str | None:
    value = slots.get(key)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def deterministic_normalized_command_renderer(core_contract: dict[str, Any]) -> dict[str, Any]:
    core = validate_v2_core(core_contract)
    task_type = core["task_type"]
    route = core["route"]
    slots = core["slots"]

    if task_type == "search" and route == "search_web":
        query = _slot_text(slots, "query")
        if query is None:
            return {"supported": False, "reason": "missing_query_slot", "normalized_command": None}
        return {"supported": True, "reason": "supported", "normalized_command": f"搜索{query}"}

    if task_type == "navigate" and route == "open_url":
        url = _slot_text(slots, "url")
        if url is None:
            return {"supported": False, "reason": "missing_url_slot", "normalized_command": None}
        return {"supported": True, "reason": "supported", "normalized_command": f"打开{url}"}

    if task_type == "extract" and route == "extract_page":
        target = _slot_text(slots, "target")
        if target is None:
            return {"supported": False, "reason": "missing_target_slot", "normalized_command": None}
        return {"supported": True, "reason": "supported", "normalized_command": f"提取{target}"}

    if task_type == "form_fill" and route == "fill_form":
        field = _slot_text(slots, "field")
        if field is None:
            return {"supported": False, "reason": "missing_field_slot", "normalized_command": None}
        value = _slot_text(slots, "value")
        command = f"填写{field}为{value}" if value is not None else f"填写{field}"
        if core["confirmation_required"]:
            command = f"{command}并确认"
        return {"supported": True, "reason": "supported", "normalized_command": command}

    if task_type == "clarify" and route == "clarify":
        ambiguity = _slot_text(slots, "ambiguity")
        command = f"请求澄清{ambiguity}" if ambiguity is not None else "请求澄清目标"
        return {"supported": True, "reason": "supported", "normalized_command": command}

    if task_type == "blocked" and route == "deny":
        reason = _slot_text(slots, "reason") or str(core["safety"]["reason"]).strip()
        return {"supported": True, "reason": "supported", "normalized_command": f"拒绝{reason}"}

    return {"supported": False, "reason": "unsupported_task_route", "normalized_command": None}


def build_v2_envelope(core_contract: dict[str, Any]) -> dict[str, Any]:
    core = validate_v2_core(core_contract)
    rendered = deterministic_normalized_command_renderer(core)
    if not rendered["supported"]:
        return rendered
    return {
        **core,
        "normalized_command": rendered["normalized_command"],
        "language": "zh-CN",
        "contract_version": "v2",
    }


def v1_without_normalized_command_exact(gold: dict[str, Any], predicted: dict[str, Any]) -> bool:
    gold_contract = _contract_or_none(gold)
    predicted_contract = _contract_or_none(predicted)
    if gold_contract is None or predicted_contract is None:
        return False
    gold_dict = gold_contract.to_dict()
    predicted_dict = predicted_contract.to_dict()
    gold_dict.pop("normalized_command", None)
    predicted_dict.pop("normalized_command", None)
    return gold_dict == predicted_dict


def v2_core_executable_pass(gold_core: dict[str, Any], predicted_core: dict[str, Any]) -> bool:
    try:
        gold = validate_v2_core(gold_core)
        predicted = validate_v2_core(predicted_core)
    except ValidationError:
        return False
    if predicted["task_type"] != gold["task_type"] or predicted["route"] != gold["route"]:
        return False
    if predicted["confirmation_required"] != gold["confirmation_required"]:
        return False
    if predicted["safety"] != gold["safety"]:
        return False
    if not gold["safety"].get("allow") and predicted["safety"].get("allow"):
        return False
    gold_slots = _normalized_slots(gold["slots"])
    predicted_slots = _normalized_slots(predicted["slots"])
    for key, value in gold_slots.items():
        if predicted_slots.get(key) != value:
            return False
    return True


def _normalized_slots(slots: dict[str, Any]) -> dict[str, str]:
    return {normalize_slot_key(str(key)): normalize_slot_value(value) for key, value in slots.items()}


def classify_failure_contribution(gold: dict[str, Any], predicted: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(gold, dict) or not isinstance(predicted, dict):
        return {"category": "INVALID_OR_UNPARSEABLE", "mismatch_paths": [], "core_mismatch_paths": []}
    required = set(CORE_FIELDS) | set(DERIVED_FIELDS)
    if not required.issubset(predicted):
        return {"category": "INVALID_OR_UNPARSEABLE", "mismatch_paths": [], "core_mismatch_paths": []}

    mismatch_paths = []
    for field_path in (
        "task_type",
        "route",
        "safety.allow",
        "safety.reason",
        "confirmation_required",
        "slots",
        "normalized_command",
        "language",
        "contract_version",
    ):
        if _field_value(gold, field_path) != _field_value(predicted, field_path):
            mismatch_paths.append(field_path)

    if not mismatch_paths:
        return {"category": "EXACT_MATCH", "mismatch_paths": [], "core_mismatch_paths": []}

    derived = {path for path in mismatch_paths if path in DERIVED_FIELDS}
    slot = {path for path in mismatch_paths if path == "slots"}
    route_task = {path for path in mismatch_paths if path in {"route", "task_type"}}
    safety_confirmation = {
        path for path in mismatch_paths if path in {"safety.allow", "safety.reason", "confirmation_required"}
    }
    core_paths = slot | route_task | safety_confirmation

    if not core_paths:
        if derived == {"normalized_command"}:
            category = "NORMALIZED_COMMAND_ONLY"
        elif derived <= {"language", "contract_version"}:
            category = "METADATA_ONLY"
        else:
            category = "DERIVED_FIELD_ONLY"
    elif route_task and {"route", "task_type"}.issubset(route_task) and not safety_confirmation:
        category = "CORE_ROUTE_TASK_FAILURE"
    elif slot and not route_task and not safety_confirmation:
        category = "CORE_SLOT_FAILURE"
    elif route_task and not slot and not safety_confirmation:
        category = "CORE_ROUTE_TASK_FAILURE"
    elif safety_confirmation and not slot and not route_task:
        category = "CORE_SAFETY_CONFIRMATION_FAILURE"
    else:
        category = "MIXED_CORE_FAILURE"

    return {
        "category": category,
        "mismatch_paths": mismatch_paths,
        "core_mismatch_paths": sorted(core_paths),
        "derived_mismatch_paths": sorted(derived),
    }


def _load_rows_by_id(path: Path, id_key: str) -> dict[str, dict[str, Any]]:
    rows = read_jsonl(path)
    by_id: dict[str, dict[str, Any]] = {}
    for row in rows:
        row_id = row.get(id_key)
        if not isinstance(row_id, str) or not row_id.strip():
            raise ValueError(f"{path}: row missing {id_key}")
        if row_id in by_id:
            raise ValueError(f"{path}: duplicate {id_key}: {row_id}")
        by_id[row_id] = row
    return by_id


def _sample_id_hash(ids: list[str]) -> str:
    digest = hashlib.sha256()
    for row_id in ids:
        digest.update(row_id.encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def _gold_contract_hash(rows: list[dict[str, Any]]) -> str:
    digest = hashlib.sha256()
    for row in rows:
        digest.update(_canonical_json(row["gold_contract"]).encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def _validate_split_boundary(
    raw_inputs_dir: Path,
    manifest: dict[str, Any],
    boundary_file: dict[str, Any],
    split: str,
    failures: list[str],
) -> dict[str, Any]:
    gold_path = raw_inputs_dir / "gold" / f"{split}_gold.jsonl"
    control_path = raw_inputs_dir / "control" / f"{split}_predictions.jsonl"
    treatment_path = raw_inputs_dir / "treatment" / f"{split}_predictions.jsonl"
    gold_rows = read_jsonl(gold_path)
    gold = _load_rows_by_id(gold_path, "sample_id")
    control = _load_rows_by_id(control_path, "sample_id")
    treatment = _load_rows_by_id(treatment_path, "sample_id")
    gold_ids = set(gold)
    control_ids = set(control)
    treatment_ids = set(treatment)
    expected_count = manifest.get(f"{split}_row_count")
    if len(gold_ids) != expected_count or len(control_ids) != expected_count or len(treatment_ids) != expected_count:
        failures.append(f"{split}: row counts do not match manifest")
    if gold_ids != control_ids:
        failures.append(f"{split}: control prediction ids do not match gold ids")
    if gold_ids != treatment_ids:
        failures.append(f"{split}: treatment prediction ids do not match gold ids")
    split_boundary = boundary_file.get("splits", {}).get(split, {})
    if split_boundary.get("gold_hash_match") is not True:
        failures.append(f"{split}: boundary gold hash match is not true")
    if split_boundary.get("row_count") != expected_count:
        failures.append(f"{split}: boundary row count does not match manifest")
    expected_sample_id_hash = manifest.get(f"{split}_sample_id_hash")
    boundary_sample_id_hash = split_boundary.get("sample_id_hash")
    actual_sample_id_hash = _sample_id_hash([str(row["sample_id"]) for row in gold_rows])
    actual_gold_hash = _gold_contract_hash(gold_rows)
    if boundary_sample_id_hash != expected_sample_id_hash:
        failures.append(f"{split}: boundary sample id hash does not match manifest")
    if actual_sample_id_hash != expected_sample_id_hash:
        failures.append(f"{split}: actual sample id hash does not match manifest")
    if split_boundary.get("gold_hash") != manifest.get(f"{split}_gold_hash"):
        failures.append(f"{split}: boundary gold hash does not match manifest")
    if actual_gold_hash != manifest.get(f"{split}_gold_hash"):
        failures.append(f"{split}: actual gold contract hash does not match manifest")

    for arm, rows, path in (("control", control, control_path), ("treatment", treatment, treatment_path)):
        expected_config = manifest.get("prediction_config_hashes", {}).get(f"{arm}_{split}")
        expected_run = manifest.get(f"{arm}_run_id")
        expected_prediction_hash = manifest.get(f"{arm}_{split}_prediction_hash")
        if expected_prediction_hash is not None and _sha256_file(path) != expected_prediction_hash:
            failures.append(f"{arm}/{split}: prediction file hash does not match manifest")
        for row in rows.values():
            if row.get("config_hash") != expected_config:
                failures.append(f"{arm}/{split}: config hash mismatch")
                break
            if row.get("prompt_hash") != manifest.get("prompt_hash"):
                failures.append(f"{arm}/{split}: prompt hash mismatch")
                break
            if row.get("run_id") != expected_run:
                failures.append(f"{arm}/{split}: run id mismatch")
                break
            if row.get("prediction_contract") is None:
                failures.append(f"{arm}/{split}: missing prediction_contract")
                break
            if row.get("gold_contract") != gold[row["sample_id"]].get("gold_contract"):
                failures.append(f"{arm}/{split}: row gold contract mismatch")
                break

    return {
        "row_count": len(gold_ids),
        "gold_ids_match_control": gold_ids == control_ids,
        "gold_ids_match_treatment": gold_ids == treatment_ids,
        "sample_id_hash": boundary_sample_id_hash,
        "actual_sample_id_hash": actual_sample_id_hash,
        "gold_hash_match": split_boundary.get("gold_hash_match") is True,
        "actual_gold_hash": actual_gold_hash,
    }


def validate_recovered_source_boundary(raw_inputs_dir: Path) -> dict[str, Any]:
    manifest_path = raw_inputs_dir / "artifact-manifest.json"
    boundary_path = raw_inputs_dir / "boundary-verification.json"
    reproduction_path = raw_inputs_dir / "metric-reproduction.json"
    failures: list[str] = []
    for path in (
        manifest_path,
        boundary_path,
        reproduction_path,
        raw_inputs_dir / "gold/dev_gold.jsonl",
        raw_inputs_dir / "gold/test_gold.jsonl",
        raw_inputs_dir / "control/dev_predictions.jsonl",
        raw_inputs_dir / "control/test_predictions.jsonl",
        raw_inputs_dir / "treatment/dev_predictions.jsonl",
        raw_inputs_dir / "treatment/test_predictions.jsonl",
    ):
        if not path.exists():
            failures.append(f"missing required file: {path.relative_to(raw_inputs_dir)}")

    manifest = read_json(manifest_path) if manifest_path.exists() else {}
    boundary_file = read_json(boundary_path) if boundary_path.exists() else {}
    reproduction = read_json(reproduction_path) if reproduction_path.exists() else {}
    if manifest.get("projection_inputs_ready") is not True:
        failures.append("projection_inputs_ready is not true")
    status = manifest.get("metric_reproduction_status")
    if status not in SUPPORTED_METRIC_REPRODUCTION_STATUSES:
        failures.append("metric_reproduction_status is not accepted")
    if reproduction.get("status") not in SUPPORTED_METRIC_REPRODUCTION_STATUSES:
        failures.append("metric-reproduction status is not accepted")
    if manifest.get("recovery_method") not in ALLOWED_RECOVERY_METHODS:
        failures.append("recovery method is not allowed")
    if manifest.get("sanitization_status") != "passed":
        failures.append("sanitization_status is not passed")
    if boundary_file.get("comparison_allowed") is not True:
        failures.append("boundary comparison_allowed is not true")
    for flag in ("config_match", "prompt_match", "evaluator_match", "dev_gold_hash_match", "test_gold_hash_match"):
        if boundary_file.get(flag) is not True:
            failures.append(f"boundary {flag} is not true")
    for split in SPLITS:
        if reproduction.get("splits", {}).get(split) is None:
            failures.append(f"missing metric reproduction split: {split}")
        else:
            for arm in ARMS:
                if reproduction["splits"][split].get(arm, {}).get("matches_committed") is not True:
                    failures.append(f"{arm}/{split}: metrics do not match committed evidence")

    split_info: dict[str, Any] = {}
    if not failures:
        for split in SPLITS:
            split_info[split] = _validate_split_boundary(raw_inputs_dir, manifest, boundary_file, split, failures)
    else:
        for split in SPLITS:
            split_info[split] = {"row_count": manifest.get(f"{split}_row_count")}

    dev_ids = set()
    test_ids = set()
    if (raw_inputs_dir / "gold/dev_gold.jsonl").exists() and (raw_inputs_dir / "gold/test_gold.jsonl").exists():
        dev_ids = set(_load_rows_by_id(raw_inputs_dir / "gold/dev_gold.jsonl", "sample_id"))
        test_ids = set(_load_rows_by_id(raw_inputs_dir / "gold/test_gold.jsonl", "sample_id"))
        if dev_ids & test_ids:
            failures.append("dev/test sample ids overlap")

    return {
        "evidence_kind": "contract_v2_projection_recovered_source_boundary",
        "decision_label": "SOURCE_BOUNDARY_PASSED" if not failures else "PROJECTION_INVALID_INPUT_BOUNDARY",
        "failures": failures,
        "projection_inputs_ready": manifest.get("projection_inputs_ready") is True,
        "metric_reproduction_status": status,
        "accepted_metric_reproduction_statuses": sorted(SUPPORTED_METRIC_REPRODUCTION_STATUSES),
        "recovery_method": manifest.get("recovery_method"),
        "sanitization_status": manifest.get("sanitization_status"),
        "prediction_contract_used_for_projection": True,
        "raw_model_output_used_for_projection": False,
        "source_root": "reports/public-sample/step-matched-canonical-slot-ablation/raw-inputs",
        "historical_blocked_evidence_preserved": True,
        "dev_test_sample_ids_disjoint": not bool(dev_ids & test_ids),
        "splits": split_info,
        "hashes": {
            "dev_gold_hash": manifest.get("dev_gold_hash"),
            "test_gold_hash": manifest.get("test_gold_hash"),
            "prompt_hash": manifest.get("prompt_hash"),
            "evaluator_hash": manifest.get("evaluator_hash"),
            "prediction_config_hashes": manifest.get("prediction_config_hashes", {}),
        },
        "claims": _claims(),
    }


def _claims() -> dict[str, bool]:
    return {
        "training_performed": False,
        "prediction_rerun_performed": False,
        "prediction_repair_performed": False,
        "llm_judge_used": False,
        "semantic_equivalence_scoring_used": False,
        "evaluator_relaxation_performed": False,
        "contract_v2_implemented": False,
        "adapter_or_checkpoint_release": False,
        "release_or_readiness_claim": False,
        "live_browser_claim": False,
    }


def _load_split(raw_inputs_dir: Path, arm: str, split: str) -> tuple[list[SFTDatasetRow], dict[str, dict[str, Any]]]:
    gold_rows = list(_load_rows_by_id(raw_inputs_dir / "gold" / f"{split}_gold.jsonl", "sample_id").values())
    prediction_rows = _load_rows_by_id(raw_inputs_dir / arm / f"{split}_predictions.jsonl", "sample_id")
    rows = [
        SFTDatasetRow(
            id=str(row["sample_id"]),
            split=split,
            input_text=str(row["input_text"]),
            target_contract=row["gold_contract"],
            provenance={"public_safe": True, "source_id": row.get("sample_id")},
        )
        for row in gold_rows
    ]
    predictions = {row_id: row["prediction_contract"] for row_id, row in prediction_rows.items()}
    return rows, predictions


def _original_metrics(rows: list[SFTDatasetRow], predictions: dict[str, dict[str, Any]]) -> dict[str, float]:
    strict = evaluate_predictions(rows, predictions)
    layered = evaluate_layered_predictions(rows, predictions)
    layered_metrics = layered["metrics"]
    strict_metrics = strict.metrics
    return {
        "v1_contract_exact_match_strict": layered_metrics["contract_exact_match_strict"],
        "v1_executable_contract_pass_rate": layered_metrics["executable_contract_pass_rate"],
        "strict_slot_f1": strict_metrics["slot_f1"],
        "slot_value_exact_f1": layered_metrics["slot_value_exact_f1"],
        "slot_value_normalized_f1": layered_metrics["slot_value_normalized_f1"],
        "route_accuracy": layered_metrics["route_accuracy"],
        "task_type_accuracy": layered_metrics["task_type_accuracy"],
        "safety_recall": strict_metrics["safety_recall"],
        "unsafe_false_negative_rate": layered_metrics["unsafe_false_negative_rate"],
        "unsafe_false_positive_rate": layered_metrics["unsafe_false_positive_rate"],
        "requires_confirmation_accuracy": layered_metrics["requires_confirmation_accuracy"],
        "refusal_or_clarify_accuracy": layered_metrics["refusal_or_clarify_accuracy"],
        "schema_validity": layered_metrics["schema_validity"],
        "json_valid_rate": strict_metrics["json_valid_rate"],
    }


def _row_projection_records(
    rows: list[SFTDatasetRow],
    predictions: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    records = []
    for row in rows:
        gold = as_contract(row.target_contract).to_dict()
        predicted_raw = predictions.get(row.id)
        predicted = _contract_or_none(predicted_raw)
        if predicted is None:
            records.append(
                {
                    "sample_id": row.id,
                    "task_type": gold["task_type"],
                    "l0_exact": False,
                    "l1_exact": False,
                    "l2_exact": False,
                    "v1_executable": False,
                    "v2_executable": False,
                    "v2_schema_valid": False,
                    "envelope_success": False,
                "renderer_supported": False,
                "renderer_reason": "invalid_or_unparseable",
                "deterministic_roundtrip": False,
                "failure": classify_failure_contribution(gold, predicted_raw or {}),
            }
            )
            continue
        pred = predicted.to_dict()
        gold_core = project_v1_to_v2_core(gold)
        pred_core = project_v1_to_v2_core(pred)
        rendered_once = deterministic_normalized_command_renderer(pred_core)
        rendered_twice = deterministic_normalized_command_renderer(pred_core)
        envelope = build_v2_envelope(pred_core)
        l0 = gold == pred
        l1 = v1_without_normalized_command_exact(gold, pred)
        l2 = canonical_v2_core_json(gold_core) == canonical_v2_core_json(pred_core)
        records.append(
            {
                "sample_id": row.id,
                "task_type": gold["task_type"],
                "l0_exact": l0,
                "l1_exact": l1,
                "l2_exact": l2,
                "v1_executable": _v1_like_executable_from_layered(gold, pred),
                "v2_executable": v2_core_executable_pass(gold_core, pred_core),
                "v2_schema_valid": True,
                "envelope_success": bool(envelope.get("contract_version") == "v2"),
                "renderer_supported": bool(rendered_once["supported"]),
                "renderer_reason": str(rendered_once["reason"]),
                "deterministic_roundtrip": rendered_once == rendered_twice,
                "failure": classify_failure_contribution(gold, pred) if not l0 else None,
            }
        )
    return records


def _v1_like_executable_from_layered(gold: dict[str, Any], pred: dict[str, Any]) -> bool:
    gold_core = project_v1_to_v2_core(gold)
    pred_core = project_v1_to_v2_core(pred)
    if pred_core["task_type"] != gold_core["task_type"] or pred_core["route"] != gold_core["route"]:
        return False
    if pred_core["confirmation_required"] != gold_core["confirmation_required"]:
        return False
    if pred_core["safety"].get("allow") != gold_core["safety"].get("allow"):
        return False
    if not gold_core["safety"].get("allow") and pred_core["safety"].get("allow"):
        return False
    gold_slots = _normalized_slots(gold_core["slots"])
    pred_slots = _normalized_slots(pred_core["slots"])
    return all(pred_slots.get(key) == value for key, value in gold_slots.items())


def _projection_metrics(rows: list[SFTDatasetRow], predictions: dict[str, dict[str, Any]]) -> dict[str, Any]:
    original = _original_metrics(rows, predictions)
    records = _row_projection_records(rows, predictions)
    total = len(records)
    l0 = sum(record["l0_exact"] for record in records)
    l1 = sum(record["l1_exact"] for record in records)
    l2 = sum(record["l2_exact"] for record in records)
    v1_exec = sum(record["v1_executable"] for record in records)
    v2_exec = sum(record["v2_executable"] for record in records)
    metrics = {
        **original,
        "v1_without_normalized_command_exact": _rate(l1, total),
        "v2_core_exact_match": _rate(l2, total),
        "v2_core_schema_validity": _rate(sum(record["v2_schema_valid"] for record in records), total),
        "v2_core_executable_pass_rate": _rate(v2_exec, total),
        "v2_envelope_build_success_rate": _rate(sum(record["envelope_success"] for record in records), total),
        "normalized_command_renderer_supported_rate": _rate(
            sum(record["renderer_supported"] for record in records), total
        ),
        "deterministic_roundtrip_rate": _rate(sum(record["deterministic_roundtrip"] for record in records), total),
    }
    metrics["counterfactual_deltas"] = {
        "l1_exact_minus_l0_exact": metrics["v1_without_normalized_command_exact"]
        - metrics["v1_contract_exact_match_strict"],
        "l2_exact_minus_l0_exact": metrics["v2_core_exact_match"] - metrics["v1_contract_exact_match_strict"],
        "l2_exact_minus_l1_exact": metrics["v2_core_exact_match"]
        - metrics["v1_without_normalized_command_exact"],
        "v2_core_executable_minus_v1_executable": metrics["v2_core_executable_pass_rate"]
        - metrics["v1_executable_contract_pass_rate"],
    }
    return {
        "evidence_kind": "contract_v2_projection_metrics",
        "row_count": total,
        "metrics": metrics,
        "counts": {
            "l0_exact": l0,
            "l1_exact": l1,
            "l2_exact": l2,
            "v1_executable": v1_exec,
            "v2_executable": v2_exec,
        },
        "row_records": records,
        "claims": _claims(),
    }


def paired_bootstrap_projection_deltas(
    rows: list[dict[str, Any]],
    *,
    seed: int = BOOTSTRAP_SEED,
    iterations: int = BOOTSTRAP_ITERATIONS,
) -> dict[str, Any]:
    rng = random.Random(seed)
    exact_deltas: list[float] = []
    executable_deltas: list[float] = []
    total = len(rows)
    if total == 0:
        return {
            "seed": seed,
            "iterations": iterations,
            "row_count": 0,
            "exact_pass_delta_mean": 0.0,
            "exact_pass_delta_ci95": [0.0, 0.0],
            "executable_pass_delta_mean": 0.0,
            "executable_pass_delta_ci95": [0.0, 0.0],
            "family_level_delta": {},
        }
    for _ in range(iterations):
        sample = [rows[rng.randrange(total)] for _ in range(total)]
        exact_deltas.append(
            sum(float(row["l2_exact"]) - float(row["l0_exact"]) for row in sample) / total
        )
        executable_deltas.append(
            sum(float(row["v2_executable"]) - float(row["v1_executable"]) for row in sample) / total
        )
    return {
        "seed": seed,
        "iterations": iterations,
        "row_count": total,
        "exact_pass_delta_mean": sum(exact_deltas) / iterations,
        "exact_pass_delta_ci95": _ci95(exact_deltas),
        "executable_pass_delta_mean": sum(executable_deltas) / iterations,
        "executable_pass_delta_ci95": _ci95(executable_deltas),
        "family_level_delta": _family_delta(rows),
    }


def _ci95(values: list[float]) -> list[float]:
    ordered = sorted(values)
    low = ordered[int((len(ordered) - 1) * 0.025)]
    high = ordered[int((len(ordered) - 1) * 0.975)]
    return [low, high]


def _family_delta(records: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[str(record["task_type"] if "task_type" in record else record.get("family", "unknown"))].append(record)
    result: dict[str, Any] = {}
    for family, rows in sorted(grouped.items()):
        total = len(rows)
        result[family] = {
            "row_count": total,
            "l2_exact_minus_l0_exact": sum(float(row["l2_exact"]) - float(row["l0_exact"]) for row in rows)
            / total,
            "v2_core_executable_minus_v1_executable": sum(
                float(row["v2_executable"]) - float(row["v1_executable"]) for row in rows
            )
            / total,
        }
    return result


def _failure_analysis(all_metrics: dict[str, dict[str, dict[str, Any]]]) -> dict[str, Any]:
    by_arm_split: dict[str, Any] = {}
    overall_counts: Counter[str] = Counter()
    strict_failures_total = 0
    eliminated_total = 0
    slot_field_counts: Counter[str] = Counter()
    examples: list[dict[str, Any]] = []
    for arm in ARMS:
        by_arm_split[arm] = {}
        for split in SPLITS:
            records = all_metrics[arm][split]["row_records"]
            failures = [record for record in records if not record["l0_exact"]]
            counts = Counter(str(record["failure"]["category"]) for record in failures)
            overall_counts.update(counts)
            strict_failures_total += len(failures)
            eliminated = sum(record["l2_exact"] for record in failures)
            eliminated_total += eliminated
            family_counts = Counter(str(record["task_type"]) for record in failures)
            for record in failures:
                if record["failure"]["category"] in {"CORE_SLOT_FAILURE", "MIXED_CORE_FAILURE"}:
                    for path in record["failure"].get("core_mismatch_paths", []):
                        if path == "slots":
                            slot_field_counts.update(["slots"])
                if len(examples) < 12:
                    examples.append(
                        {
                            "arm": arm,
                            "split": split,
                            "sample_id": record["sample_id"],
                            "task_type": record["task_type"],
                            "category": record["failure"]["category"],
                            "mismatch_paths": record["failure"].get("mismatch_paths", []),
                        }
                    )
            by_arm_split[arm][split] = {
                "strict_failure_count": len(failures),
                "category_counts": dict(sorted(counts.items())),
                "category_proportions": {
                    category: _rate(count, len(failures)) for category, count in sorted(counts.items())
                },
                "task_family_distribution": dict(sorted(family_counts.items())),
                "v1_strict_failures_eliminated_by_v2_core": eliminated,
                "remaining_core_failures": sum(
                    count
                    for category, count in counts.items()
                    if category
                    in {
                        "CORE_SLOT_FAILURE",
                        "CORE_ROUTE_TASK_FAILURE",
                        "CORE_SAFETY_CONFIRMATION_FAILURE",
                        "MIXED_CORE_FAILURE",
                        "INVALID_OR_UNPARSEABLE",
                    }
                )
                - eliminated,
            }
    derived_total = sum(
        overall_counts[category]
        for category in ("NORMALIZED_COMMAND_ONLY", "METADATA_ONLY", "DERIVED_FIELD_ONLY")
    )
    return {
        "evidence_kind": "contract_v2_projection_failure_contribution_analysis",
        "approved_categories": list(CONTRIBUTION_CATEGORIES),
        "overall": {
            "strict_failure_count": strict_failures_total,
            "category_counts": dict(sorted(overall_counts.items())),
            "category_proportions": {
                category: _rate(count, strict_failures_total) for category, count in sorted(overall_counts.items())
            },
            "derived_field_only_total_count": derived_total,
            "derived_field_only_total_share": _rate(derived_total, strict_failures_total),
            "normalized_command_only_share": _rate(
                overall_counts["NORMALIZED_COMMAND_ONLY"], strict_failures_total
            ),
            "metadata_only_share": _rate(overall_counts["METADATA_ONLY"], strict_failures_total),
            "v1_strict_failures_eliminated_by_v2_core": eliminated_total,
            "remaining_core_failures": strict_failures_total - eliminated_total,
            "top_slot_field_paths": dict(slot_field_counts.most_common(10)),
        },
        "by_arm_split": by_arm_split,
        "public_safe_examples": examples[:12],
        "claims": _claims(),
    }


def _renderer_report(all_metrics: dict[str, dict[str, dict[str, Any]]]) -> dict[str, Any]:
    total = supported = deterministic = 0
    task_counts: Counter[str] = Counter()
    unsupported_reasons: Counter[str] = Counter()
    examples: list[dict[str, Any]] = []
    for arm in ARMS:
        for split in SPLITS:
            for record in all_metrics[arm][split]["row_records"]:
                total += 1
                task_counts.update([str(record["task_type"])])
                supported += int(record["renderer_supported"])
                deterministic += int(record["deterministic_roundtrip"])
                if not record["renderer_supported"]:
                    unsupported_reasons.update([str(record.get("renderer_reason", "unsupported"))])
                if len(examples) < 10:
                    examples.append(
                        {
                            "arm": arm,
                            "split": split,
                            "sample_id": record["sample_id"],
                            "task_type": record["task_type"],
                            "renderer_supported": record["renderer_supported"],
                            "renderer_reason": record.get("renderer_reason"),
                        }
                    )
    return {
        "evidence_kind": "normalized_command_renderer_report",
        "supported_rate": _rate(supported, total),
        "unsupported_count": total - supported,
        "task_type_coverage": dict(sorted(task_counts.items())),
        "unsupported_reason_distribution": dict(sorted(unsupported_reasons.items())),
        "deterministic_roundtrip_rate": _rate(deterministic, total),
        "examples": examples,
        "claims": _claims(),
    }


def _family_level_projection_deltas(all_metrics: dict[str, dict[str, dict[str, Any]]]) -> dict[str, Any]:
    result = {"evidence_kind": "family_level_projection_deltas", "by_arm_split": {}}
    for arm in ARMS:
        result["by_arm_split"][arm] = {}
        for split in SPLITS:
            result["by_arm_split"][arm][split] = _family_delta(all_metrics[arm][split]["row_records"])
    return result


def _bootstrap_analysis(all_metrics: dict[str, dict[str, dict[str, Any]]]) -> dict[str, Any]:
    result = {
        "evidence_kind": "contract_v2_projection_bootstrap_analysis",
        "seed": BOOTSTRAP_SEED,
        "iterations": BOOTSTRAP_ITERATIONS,
        "by_arm_split": {},
    }
    for arm in ARMS:
        result["by_arm_split"][arm] = {}
        for split in SPLITS:
            result["by_arm_split"][arm][split] = paired_bootstrap_projection_deltas(
                all_metrics[arm][split]["row_records"],
                seed=BOOTSTRAP_SEED,
                iterations=BOOTSTRAP_ITERATIONS,
            )
    return result


def _decision(
    all_metrics: dict[str, dict[str, dict[str, Any]]],
    failure_analysis: dict[str, Any],
    renderer_report: dict[str, Any],
) -> dict[str, Any]:
    deltas = [
        all_metrics[arm][split]["metrics"]["counterfactual_deltas"]["l2_exact_minus_l0_exact"]
        for arm in ARMS
        for split in SPLITS
    ]
    exec_deltas = [
        all_metrics[arm][split]["metrics"]["counterfactual_deltas"]["v2_core_executable_minus_v1_executable"]
        for arm in ARMS
        for split in SPLITS
    ]
    category_counts = failure_analysis["overall"]["category_counts"]
    core_slot = category_counts.get("CORE_SLOT_FAILURE", 0) + category_counts.get("MIXED_CORE_FAILURE", 0)
    derived_share = failure_analysis["overall"]["derived_field_only_total_share"]
    slot_bottleneck = core_slot >= max(1, failure_analysis["overall"]["derived_field_only_total_count"])
    renderer_ok = renderer_report["supported_rate"] >= 0.95 and renderer_report["deterministic_roundtrip_rate"] == 1.0
    executable_non_decline = all(delta >= 0 for delta in exec_deltas)

    if (
        min(deltas) >= 0.08
        and derived_share >= 0.20
        and executable_non_decline
        and renderer_ok
        and not slot_bottleneck
    ):
        label = "PROCEED_TO_CONTRACT_V2_IMPLEMENTATION"
        next_change = "implement-contract-v2-core-and-postprocessor"
    elif max(deltas) < 0.03 and not executable_non_decline and slot_bottleneck:
        label = "SLOT_BOTTLENECK_PERSISTS"
        next_change = "diagnose-v2-core-slot-residuals"
    else:
        label = "PARTIAL_SCHEMA_BENEFIT"
        next_change = "decide-contract-v2-core-implementation-scope"

    return {
        "decision_label": label,
        "recommended_next_change": next_change,
        "slot_bottleneck_remains_visible": slot_bottleneck,
        "renderer_gate_passed": renderer_ok,
        "v2_core_exact_improvements": {
            f"{arm}_{split}": all_metrics[arm][split]["metrics"]["counterfactual_deltas"][
                "l2_exact_minus_l0_exact"
            ]
            for arm in ARMS
            for split in SPLITS
        },
        "v2_core_executable_improvements": {
            f"{arm}_{split}": all_metrics[arm][split]["metrics"]["counterfactual_deltas"][
                "v2_core_executable_minus_v1_executable"
            ]
            for arm in ARMS
            for split in SPLITS
        },
        "claims": _claims(),
    }


def generate_contract_v2_projection_rerun(raw_inputs_dir: Path, output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    boundary = validate_recovered_source_boundary(raw_inputs_dir)
    write_json(output_dir / "source-boundary.json", boundary)
    if boundary["decision_label"] != "SOURCE_BOUNDARY_PASSED":
        blocked = {
            "decision_label": "PROJECTION_INVALID_OR_BLOCKED",
            "boundary_decision_label": boundary["decision_label"],
            "failures": boundary["failures"],
            "claims": _claims(),
        }
        write_json(output_dir / "blocked.json", blocked)
        return blocked

    all_metrics: dict[str, dict[str, dict[str, Any]]] = {arm: {} for arm in ARMS}
    for arm in ARMS:
        for split in SPLITS:
            rows, predictions = _load_split(raw_inputs_dir, arm, split)
            payload = _projection_metrics(rows, predictions)
            all_metrics[arm][split] = payload
            metrics_path = output_dir / arm / f"{split}-projection-metrics.json"
            write_json(metrics_path, _without_row_records(payload))

    failures = _failure_analysis(all_metrics)
    renderer = _renderer_report(all_metrics)
    family_deltas = _family_level_projection_deltas(all_metrics)
    bootstrap = _bootstrap_analysis(all_metrics)
    decision = _decision(all_metrics, failures, renderer)
    summary = _summary(boundary, all_metrics, failures, renderer, decision)

    _write_projection_spec(output_dir)
    _write_field_policy(output_dir)
    write_json(output_dir / "normalized-command-renderer-report.json", renderer)
    (output_dir / "normalized-command-renderer-report.md").write_text(_renderer_markdown(renderer), encoding="utf-8")
    write_json(output_dir / "failure-contribution-analysis.json", failures)
    (output_dir / "failure-contribution-analysis.md").write_text(_failure_markdown(failures), encoding="utf-8")
    write_json(output_dir / "family-level-projection-deltas.json", family_deltas)
    write_json(output_dir / "bootstrap-analysis.json", bootstrap)
    write_json(output_dir / "summary.json", summary)
    (output_dir / "summary.md").write_text(_summary_markdown(summary), encoding="utf-8")
    (output_dir / "decision.md").write_text(_decision_markdown(decision), encoding="utf-8")
    (output_dir / "recommended-next-change.md").write_text(
        _recommended_next_change_markdown(decision), encoding="utf-8"
    )
    scan = scan_paths([output_dir])
    write_json(output_dir / "leak-scan.json", scan.to_dict())
    return {"decision_label": decision["decision_label"], "output_dir": output_dir.as_posix(), "summary": summary}


def _without_row_records(payload: dict[str, Any]) -> dict[str, Any]:
    cleaned = dict(payload)
    records = cleaned.pop("row_records")
    cleaned["row_count"] = len(records)
    cleaned["sample_rows"] = [
        {
            "sample_id": record["sample_id"],
            "task_type": record["task_type"],
            "l0_exact": record["l0_exact"],
            "l1_exact": record["l1_exact"],
            "l2_exact": record["l2_exact"],
            "v1_executable": record["v1_executable"],
            "v2_executable": record["v2_executable"],
            "failure_category": record["failure"]["category"] if record["failure"] else None,
        }
        for record in records[:10]
    ]
    return cleaned


def _summary(
    boundary: dict[str, Any],
    all_metrics: dict[str, dict[str, dict[str, Any]]],
    failures: dict[str, Any],
    renderer: dict[str, Any],
    decision: dict[str, Any],
) -> dict[str, Any]:
    exact_improvements = decision["v2_core_exact_improvements"]
    executable_improvements = decision["v2_core_executable_improvements"]
    required_questions = {
        "used_recovered_metric_reproduced_step_matched_contracts": True,
        "normalized_command_only_share": failures["overall"]["normalized_command_only_share"],
        "metadata_only_share": failures["overall"]["metadata_only_share"],
        "derived_field_only_total_share": failures["overall"]["derived_field_only_total_share"],
        "v2_core_exact_improvement_control_dev": exact_improvements["control_dev"],
        "v2_core_exact_improvement_control_test": exact_improvements["control_test"],
        "v2_core_exact_improvement_treatment_dev": exact_improvements["treatment_dev"],
        "v2_core_exact_improvement_treatment_test": exact_improvements["treatment_test"],
        "v2_core_executable_improved": any(delta > 0 for delta in executable_improvements.values()),
        "slot_bottleneck_still_dominant": decision["slot_bottleneck_remains_visible"],
        "safety_and_confirmation_projection_preserved": True,
        "renderer_supported_rate": renderer["supported_rate"],
        "deterministic_roundtrip_rate": renderer["deterministic_roundtrip_rate"],
        "formal_contract_v2_warranted": decision["decision_label"] == "PROCEED_TO_CONTRACT_V2_IMPLEMENTATION",
        "decision_label": decision["decision_label"],
        "recommended_next_change": decision["recommended_next_change"],
        "cannot_claim": [
            "model improvement",
            "held-out recovery",
            "production readiness",
            "safety readiness",
            "live-browser benchmark gain",
            "checkpoint release",
            "adapter release",
            "DPO justification",
            "approval for another canonical-candidate loop",
        ],
    }
    return {
        "evidence_kind": "contract_v2_projection_rerun_summary",
        "generated_at": datetime.now(UTC).isoformat(),
        "decision_label": decision["decision_label"],
        "recommended_next_change": decision["recommended_next_change"],
        "source_boundary": boundary,
        "decision": decision,
        "required_questions": required_questions,
        "metrics_by_arm_split": {
            arm: {split: _without_row_records(all_metrics[arm][split]) for split in SPLITS} for arm in ARMS
        },
        "failure_contribution_overall": failures["overall"],
        "renderer": renderer,
        "claims": _claims(),
    }

def _write_projection_spec(output_dir: Path) -> None:
    spec_json = {
        "evidence_kind": "contract_v2_projection_spec",
        "ladder": {
            "L0": "V1 full strict exact, unchanged",
            "L1": "V1 without normalized_command exact",
            "L2": "V2 Core strict exact",
            "L3": "V2 envelope build and deterministic renderer evaluation",
        },
        "v2_core_fields": list(CORE_FIELDS),
        "v2_envelope_fields": [*CORE_FIELDS, "normalized_command", "language", "contract_version"],
        "forbidden_fields": ["allowed_actions", "success_criteria", "policy_tags", "runtime_hints"],
        "raw_model_output_boundary": "not used for projection metrics",
        "claims": _claims(),
    }
    write_json(output_dir / "projection-spec.json", spec_json)
    (output_dir / "projection-spec.md").write_text(
        "\n".join(
            [
                "# Contract V2 Projection Rerun Spec",
                "",
                "- L0: V1 full strict exact, unchanged.",
                "- L1: V1 without `normalized_command` exact.",
                "- L2: V2 Core strict exact.",
                "- L3: V2 envelope build and renderer evaluation.",
                "- Projection reads parsed `prediction_contract`, not `raw_model_output`.",
                "- V2 Core fields: `task_type`, `route`, `safety`, `confirmation_required`, `slots`.",
                "- Forbidden fields: `allowed_actions`, `success_criteria`, `policy_tags`, `runtime_hints`.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _write_field_policy(output_dir: Path) -> None:
    (output_dir / "field-policy.md").write_text(
        "\n".join(
            [
                "# Contract V2 Projection Field Policy",
                "",
                "- Core fields are copied from valid parsed V1 contracts without repair.",
                "- `normalized_command`, `language`, and `contract_version` are derived envelope fields.",
                "- The renderer reads only V2 Core fields and bounded templates.",
                "- Slot keys and values are not merged, substituted, or semantically rescored.",
                "- Unsupported renderer shapes fail closed.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _renderer_markdown(renderer: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Normalized Command Renderer Report",
            "",
            f"- Supported rate: `{renderer['supported_rate']}`",
            f"- Unsupported count: `{renderer['unsupported_count']}`",
            f"- Deterministic roundtrip rate: `{renderer['deterministic_roundtrip_rate']}`",
            f"- Task-type coverage: `{renderer['task_type_coverage']}`",
            f"- Unsupported reasons: `{renderer['unsupported_reason_distribution']}`",
            "",
        ]
    )


def _failure_markdown(failures: dict[str, Any]) -> str:
    overall = failures["overall"]
    return "\n".join(
        [
            "# Failure Contribution Analysis",
            "",
            f"- Strict failures: `{overall['strict_failure_count']}`",
            f"- Normalized-command-only share: `{overall['normalized_command_only_share']}`",
            f"- Metadata-only share: `{overall['metadata_only_share']}`",
            f"- Derived-field-only total share: `{overall['derived_field_only_total_share']}`",
            f"- Eliminated V1 strict failures by V2 Core: `{overall['v1_strict_failures_eliminated_by_v2_core']}`",
            f"- Remaining core failures: `{overall['remaining_core_failures']}`",
            f"- Category counts: `{overall['category_counts']}`",
            "",
        ]
    )


def _summary_markdown(summary: dict[str, Any]) -> str:
    questions = summary["required_questions"]
    return "\n".join(
        [
            "# Contract V2 Projection Rerun Summary",
            "",
            f"- Decision label: `{questions['decision_label']}`",
            "- Used recovered metric-reproduced step-matched contracts: "
            f"`{questions['used_recovered_metric_reproduced_step_matched_contracts']}`",
            f"- Normalized-command-only share: `{questions['normalized_command_only_share']}`",
            f"- Metadata-only share: `{questions['metadata_only_share']}`",
            f"- Derived-field-only total share: `{questions['derived_field_only_total_share']}`",
            f"- V2 core exact improvement Control dev: `{questions['v2_core_exact_improvement_control_dev']}`",
            f"- V2 core exact improvement Control test: `{questions['v2_core_exact_improvement_control_test']}`",
            f"- V2 core exact improvement Treatment dev: `{questions['v2_core_exact_improvement_treatment_dev']}`",
            f"- V2 core exact improvement Treatment test: `{questions['v2_core_exact_improvement_treatment_test']}`",
            f"- V2 core executable improved: `{questions['v2_core_executable_improved']}`",
            f"- Slot bottleneck still dominant: `{questions['slot_bottleneck_still_dominant']}`",
            f"- Renderer supported rate: `{questions['renderer_supported_rate']}`",
            f"- Deterministic roundtrip rate: `{questions['deterministic_roundtrip_rate']}`",
            f"- Recommended next change: `{questions['recommended_next_change']}`",
            "",
            "This rerun does not claim model improvement, held-out recovery, production readiness, "
            "safety readiness, live-browser gains, checkpoint release, adapter release, DPO justification, "
            "or approval for another canonical-candidate loop.",
            "",
        ]
    )


def _decision_markdown(decision: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Contract V2 Projection Rerun Decision",
            "",
            f"- Decision label: `{decision['decision_label']}`",
            f"- Recommended next change: `{decision['recommended_next_change']}`",
            f"- Slot bottleneck remains visible: `{decision['slot_bottleneck_remains_visible']}`",
            f"- Renderer gate passed: `{decision['renderer_gate_passed']}`",
            "",
            "No automatic next phase is authorized by this artifact.",
            "",
        ]
    )


def _recommended_next_change_markdown(decision: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Recommended Next Change",
            "",
            f"`{decision['recommended_next_change']}`",
            "",
            "This is a recommendation only. It does not implement Contract V2, launch training, "
            "expand data, run DPO, or start a challenge-set phase.",
            "",
        ]
    )
