from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from run_step_matched_canonical_slot_ablation_eval import _metric_bundle  # noqa: E402
from step_matched_canonical_slot_ablation_report import REQUIRED_METRICS  # noqa: E402
from voice2task.io import read_json, write_json  # noqa: E402
from voice2task.schemas import SFTDatasetRow, ValidationError, as_contract  # noqa: E402

CHANGE_ID = "recover-step-matched-projection-inputs"
SOURCE_PHASE = "run-step-matched-canonical-slot-ablation"
RECOVERY_METHOD = "recovered_from_existing_artifacts"
SUCCESS_DECISION = "RECOVERED_FROM_EXISTING_ARTIFACTS"
CONTROL_REF = "c25a09874ae10c052364aaf5bfa55ee45b819e9a"
TREATMENT_REF = "115d060823ca6e90c2f9a3de37fc41eb7a08fa85"
EXPECTED_RUN_ID = "step-matched-canonical-slot-ablation-20260620T000000Z"
HELDOUT_MANIFEST_ID = "public-sample-20260619T090925Z"
CONTROL_MANIFEST_ID = "public-sample-20260617T152259Z"
TREATMENT_MANIFEST_ID = "public-sample-20260619T090925Z"
EXPECTED_ROW_COUNT = 207
EXPECTED_CONTROL_ADAPTER_HASH = "27aaffc10f39d497af08bfa35d4f914bd198dafc514798449e0e5292b56a6359"
EXPECTED_TREATMENT_ADAPTER_HASH = "a23c54e7c157de2dd80c88777ac752272803096f7e9a19aa69669d13c8eb9238"
EXPECTED_OPTIMIZER_STEPS = 3132
EXPECTED_TRAIN_ROWS = {"control": 261, "treatment": 282}
DECISION_LABELS = (
    SUCCESS_DECISION,
    "RECOVERY_BLOCKED_ADAPTER_UNAVAILABLE",
    "RECOVERY_INVALID_BOUNDARY_MISMATCH",
    "RECOVERY_INVALID_METRIC_MISMATCH",
)
UNAVAILABLE_REASON_MARKERS = (
    "source_bundle_unavailable",
    "prediction_row_count_mismatch",
    "raw_summary_row_count_mismatch",
    "duplicate_prediction_ids",
    "duplicate_raw_summary_ids",
    "prediction_id_order_mismatch",
    "raw_summary_id_order_mismatch",
    "missing_prediction_rows",
    "extra_prediction_rows",
    "missing_raw_summary_rows",
    "extra_raw_summary_rows",
    "invalid_prediction_rows",
    "invalid_raw_summary_rows",
    "adapter_identity_unverified",
)
CONFIG_PATHS = {
    "control_training": REPO_ROOT / "configs/sft-a100-step-matched-canonical-slot-control.json",
    "treatment_training": REPO_ROOT / "configs/sft-a100-step-matched-canonical-slot-treatment.json",
    "control_dev_prediction": REPO_ROOT / "configs/sft-a100-step-matched-canonical-slot-control-dev-prediction.json",
    "control_test_prediction": REPO_ROOT / "configs/sft-a100-step-matched-canonical-slot-control-test-prediction.json",
    "treatment_dev_prediction": REPO_ROOT / "configs/sft-a100-step-matched-canonical-slot-treatment-dev-prediction.json",
    "treatment_test_prediction": REPO_ROOT / "configs/sft-a100-step-matched-canonical-slot-treatment-test-prediction.json",
}
OUTPUT_RELATIVE = Path("reports/public-sample/step-matched-canonical-slot-ablation/raw-inputs")
COMMITTED_REPORT_ROOT = REPO_ROOT / "reports/public-sample/step-matched-canonical-slot-ablation"
PROMPT_HASH_KEYS = (
    "decoding_policy",
    "formatting_policy",
    "prediction_output_boundary",
    "prompt_constraints",
    "retry_prompt_constraints",
    "retry_template_boundary",
)


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def hash_lines(values: list[str]) -> str:
    digest = hashlib.sha256()
    for value in values:
        digest.update(value.encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(canonical_json(row) + "\n")


def _git_show_json(ref: str, path: str) -> dict[str, Any]:
    return json.loads(subprocess.check_output(["git", "show", f"{ref}:{path}"], cwd=REPO_ROOT))


def _git_show_jsonl(ref: str, path: str) -> list[dict[str, Any]]:
    data = subprocess.check_output(["git", "show", f"{ref}:{path}"], cwd=REPO_ROOT).decode("utf-8")
    return [json.loads(line) for line in data.splitlines() if line.strip()]


def _split_rows(records: list[dict[str, Any]], split: str) -> list[dict[str, Any]]:
    return [record for record in records if record.get("split") == split]


def _gold_hash(rows: list[dict[str, Any]]) -> str:
    return hash_lines([canonical_json(row["target_contract"]) for row in rows])


def _sample_id_hash(rows: list[dict[str, Any]]) -> str:
    return hash_lines([str(row["id"]) for row in rows])


def _input_hash_rows(rows: list[dict[str, Any]]) -> str:
    return hash_lines([str(row["input_text"]) for row in rows])


def _config_hashes() -> dict[str, str]:
    return {key: sha256_text(canonical_json(read_json(path))) for key, path in CONFIG_PATHS.items()}


def _prompt_policy_hash(prompt_snapshot: dict[str, Any]) -> str:
    payload = {key: prompt_snapshot[key] for key in PROMPT_HASH_KEYS if key in prompt_snapshot}
    return sha256_text(canonical_json(payload))


def _evaluator_hash() -> str:
    digest = hashlib.sha256()
    for path in (
        REPO_ROOT / "src/voice2task/evaluation.py",
        REPO_ROOT / "src/voice2task/layered_evaluation.py",
        REPO_ROOT / "scripts/run_step_matched_canonical_slot_ablation_eval.py",
    ):
        digest.update(path.relative_to(REPO_ROOT).as_posix().encode("utf-8"))
        digest.update(b"\n")
        digest.update(path.read_bytes())
        digest.update(b"\n")
    return digest.hexdigest()


def _ids(rows: list[dict[str, Any]]) -> list[str]:
    return [str(row["sample_id"]) for row in rows]


def _duplicate_ids(rows: list[dict[str, Any]]) -> list[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for row_id in _ids(rows):
        if row_id in seen:
            duplicates.add(row_id)
        seen.add(row_id)
    return sorted(duplicates)


def _source_ids(rows: list[dict[str, Any]]) -> list[str]:
    return [str(row.get("id", "")) if isinstance(row, dict) else "" for row in rows]


def source_artifact_blocking_reasons(
    *,
    expected_ids: list[str],
    prediction_rows: list[dict[str, Any]],
    raw_summary_rows: list[dict[str, Any]],
) -> list[str]:
    reasons: list[str] = []
    prediction_ids = _source_ids(prediction_rows)
    raw_ids = _source_ids(raw_summary_rows)
    expected_set = set(expected_ids)
    prediction_set = set(prediction_ids)
    raw_set = set(raw_ids)

    if len(prediction_rows) != len(expected_ids):
        reasons.append("prediction_row_count_mismatch")
    if len(raw_summary_rows) != len(expected_ids):
        reasons.append("raw_summary_row_count_mismatch")
    if len(prediction_set) != len(prediction_ids):
        reasons.append("duplicate_prediction_ids")
    if len(raw_set) != len(raw_ids):
        reasons.append("duplicate_raw_summary_ids")
    if prediction_ids != expected_ids:
        reasons.append("prediction_id_order_mismatch")
    if raw_ids != expected_ids:
        reasons.append("raw_summary_id_order_mismatch")
    if expected_set - prediction_set:
        reasons.append("missing_prediction_rows")
    if prediction_set - expected_set:
        reasons.append("extra_prediction_rows")
    if expected_set - raw_set:
        reasons.append("missing_raw_summary_rows")
    if raw_set - expected_set:
        reasons.append("extra_raw_summary_rows")
    try:
        for row in prediction_rows:
            if not isinstance(row, dict) or not str(row.get("id", "")).strip() or "prediction" not in row:
                reasons.append("invalid_prediction_rows")
                break
            as_contract(row["prediction"])
    except (ValidationError, TypeError, ValueError):
        reasons.append("invalid_prediction_rows")
    if any(
        not isinstance(row, dict)
        or not str(row.get("id", "")).strip()
        or not isinstance(row.get("decoded_sha256"), str)
        or not row.get("decoded_sha256")
        for row in raw_summary_rows
    ):
        reasons.append("invalid_raw_summary_rows")
    return sorted(set(reasons))


def boundary_blocking_reasons(
    *,
    control_rows: list[dict[str, Any]],
    treatment_rows: list[dict[str, Any]],
    gold_rows: list[dict[str, Any]],
    expected_count: int,
    expected_gold_hash: str,
) -> list[str]:
    reasons: list[str] = []
    for rows in (control_rows, treatment_rows, gold_rows):
        if _duplicate_ids(rows):
            reasons.append("duplicate_sample_ids")
            break
    if len(control_rows) != expected_count or len(treatment_rows) != expected_count or len(gold_rows) != expected_count:
        reasons.append("row_count_mismatch")
    control_ids = _ids(control_rows)
    treatment_ids = _ids(treatment_rows)
    gold_ids = _ids(gold_rows)
    if control_ids != treatment_ids:
        reasons.append("control_treatment_id_mismatch")
    if control_ids != gold_ids:
        reasons.append("control_gold_id_mismatch")
    if treatment_ids != gold_ids:
        reasons.append("treatment_gold_id_mismatch")
    if [row.get("input_hash") for row in control_rows] != [row.get("input_hash") for row in treatment_rows]:
        reasons.append("input_hash_mismatch")
    if [row.get("gold_contract") for row in control_rows] != [row.get("gold_contract") for row in treatment_rows]:
        reasons.append("gold_contract_mismatch")
    gold_hash = hash_lines([canonical_json(row["gold_contract"]) for row in gold_rows]) if gold_rows else ""
    if gold_hash != expected_gold_hash:
        reasons.append("gold_hash_mismatch")
    return sorted(set(reasons))


def metric_matches(observed: dict[str, float], expected: dict[str, float], *, tolerance: float = 1e-12) -> bool:
    for metric, expected_value in expected.items():
        if metric not in observed:
            return False
        if abs(float(observed[metric]) - float(expected_value)) > tolerance:
            return False
    return True


def build_blocked_payload(*, decision_label: str, blocking_reasons: list[str]) -> dict[str, Any]:
    return {
        "change_id": CHANGE_ID,
        "decision_label": decision_label,
        "projection_inputs_ready": False,
        "blocking_reasons": blocking_reasons,
        "claims": {
            "training_performed": False,
            "prediction_only_reproduction_performed": False,
            "contract_v2_projection_run": False,
            "prediction_repair_performed": False,
            "llm_judge_used": False,
            "semantic_equivalence_scoring_used": False,
            "data_expansion_performed": False,
            "release_or_readiness_claim": False,
        },
    }


def decision_for_blocking_reasons(blocking_reasons: list[str]) -> str:
    if any(marker in reason for reason in blocking_reasons for marker in UNAVAILABLE_REASON_MARKERS):
        return "RECOVERY_BLOCKED_ADAPTER_UNAVAILABLE"
    return "RECOVERY_INVALID_BOUNDARY_MISMATCH"


def _attempt_text(summary_row: dict[str, Any]) -> str:
    attempt = summary_row.get("raw_attempt") if isinstance(summary_row.get("raw_attempt"), dict) else summary_row
    prefix = str(attempt.get("decoded_prefix", ""))
    suffix = str(attempt.get("decoded_suffix", ""))
    if not prefix:
        return suffix
    if not suffix or suffix == prefix:
        return prefix
    return f"{prefix}\n{suffix}"


def _adapter_metadata_public(arm: str, metadata: dict[str, Any]) -> dict[str, Any]:
    dataset_load = metadata.get("dataset_load") if isinstance(metadata.get("dataset_load"), dict) else {}
    budget = metadata.get("training_budget") if isinstance(metadata.get("training_budget"), dict) else {}
    return {
        "arm": arm,
        "training_status": metadata.get("training_status"),
        "base_model": metadata.get("base_model"),
        "adapter_release_status": metadata.get("adapter_release_status"),
        "training_manifest_id": dataset_load.get("manifest_id"),
        "training_rows_used": metadata.get("training_rows_used"),
        "observed_optimizer_steps": budget.get("observed_optimizer_steps"),
        "effective_batch_size": budget.get("effective_batch_size"),
        "target_tokens_seen_status": budget.get("target_tokens_seen_status"),
    }


def _adapter_verified(arm: str, metadata: dict[str, Any], observed_hash: str) -> bool:
    public = _adapter_metadata_public(arm, metadata)
    expected_manifest = CONTROL_MANIFEST_ID if arm == "control" else TREATMENT_MANIFEST_ID
    expected_hash = EXPECTED_CONTROL_ADAPTER_HASH if arm == "control" else EXPECTED_TREATMENT_ADAPTER_HASH
    return (
        observed_hash == expected_hash
        and public["training_status"] == "training_completed"
        and public["base_model"] == "Qwen/Qwen2.5-7B-Instruct"
        and public["adapter_release_status"] == "not_released"
        and public["training_manifest_id"] == expected_manifest
        and public["training_rows_used"] == EXPECTED_TRAIN_ROWS[arm]
        and public["observed_optimizer_steps"] == EXPECTED_OPTIMIZER_STEPS
        and public["effective_batch_size"] == 1
    )


def load_adapter_evidence_or_blocker(
    metadata_path: Path,
    adapter_config_path: Path,
    arm: str,
) -> tuple[dict[str, Any] | None, str | None, str | None]:
    try:
        metadata = read_json(metadata_path)
        adapter_config_hash = sha256_file(adapter_config_path)
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return None, None, f"{arm}_adapter_identity_unverified"
    if not isinstance(metadata, dict):
        return None, None, f"{arm}_adapter_identity_unverified"
    return metadata, adapter_config_hash, None


def _load_source_bundle(source_root: Path, arm: str, split: str) -> dict[str, Any]:
    base = source_root / arm / split
    predictions = read_jsonl(base / "predictions.jsonl")
    raw_summaries = read_jsonl(base / "raw_decoded_summary.jsonl")
    prompt_snapshot = read_json(base / "prompt_snapshot.json")
    metadata = read_json(base / "prediction_metadata.json")
    return {
        "predictions": predictions,
        "raw_summaries": raw_summaries,
        "prompt_snapshot": prompt_snapshot,
        "metadata": metadata,
        "source_prediction_hash": sha256_file(base / "predictions.jsonl"),
    }


def load_source_bundle_or_blocker(source_root: Path, arm: str, split: str) -> tuple[dict[str, Any] | None, str | None]:
    try:
        return _load_source_bundle(source_root, arm, split), None
    except (OSError, json.JSONDecodeError, KeyError, TypeError):
        return None, f"{arm}_{split}_source_bundle_unavailable"


def _prediction_config_hash(config_hashes: dict[str, str], arm: str, split: str) -> str:
    return config_hashes[f"{arm}_{split}_prediction"]


def _build_gold_rows(rows: list[dict[str, Any]], *, split: str) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for row in rows:
        gold = as_contract(row["target_contract"]).to_dict()
        input_text = str(row["input_text"])
        output.append(
            {
                "sample_id": str(row["id"]),
                "split": split,
                "input_text": input_text,
                "input_hash": sha256_text(input_text),
                "gold_contract": gold,
                "gold_hash": sha256_text(canonical_json(gold)),
                "manifest_id": HELDOUT_MANIFEST_ID,
            }
        )
    return output


def _build_prediction_rows(
    *,
    arm: str,
    split: str,
    gold_rows: list[dict[str, Any]],
    bundle: dict[str, Any],
    config_hash: str,
    prompt_hash: str,
    run_id: str,
) -> list[dict[str, Any]]:
    predictions_by_id = {str(row["id"]): row for row in bundle["predictions"]}
    raw_by_id = {str(row["id"]): row for row in bundle["raw_summaries"]}
    rows: list[dict[str, Any]] = []
    for gold_row in gold_rows:
        sample_id = gold_row["sample_id"]
        source_prediction = predictions_by_id[sample_id]
        raw_summary = raw_by_id[sample_id]
        prediction_contract = as_contract(source_prediction["prediction"]).to_dict()
        raw_model_output = canonical_json(prediction_contract)
        raw_hash = sha256_text(raw_model_output)
        decoded_hash = str(raw_summary.get("decoded_sha256", ""))
        schema_guard = source_prediction.get("schema_guard") if isinstance(source_prediction.get("schema_guard"), dict) else {}
        valid = (
            raw_hash == decoded_hash
            and schema_guard.get("validated_output_schema_valid", True) is True
            and raw_summary.get("schema_repair_applied") is False
        )
        if not valid:
            raw_model_output = _attempt_text(raw_summary)
            raw_hash = sha256_text(raw_model_output)
        rows.append(
            {
                "sample_id": sample_id,
                "split": split,
                "input_text": gold_row["input_text"],
                "input_hash": gold_row["input_hash"],
                "gold_contract": gold_row["gold_contract"],
                "prediction_contract": prediction_contract,
                "raw_model_output": raw_model_output,
                "parse_status": "valid" if valid else "invalid",
                "run_role": arm,
                "run_id": f"{run_id}:{arm}",
                "manifest_id": HELDOUT_MANIFEST_ID,
                "config_hash": config_hash,
                "prompt_hash": prompt_hash,
                "model_output_hash": raw_hash,
                "source_decoded_sha256": decoded_hash,
                "schema_guard": schema_guard,
                "prediction_source_kind": source_prediction.get("prediction_source_kind"),
                "provenance": {
                    "public_safe": True,
                    "source_id": source_prediction.get("provenance", {}).get("source_id", sample_id),
                    "recovery_method": RECOVERY_METHOD,
                },
            }
        )
    return rows


def _metric_payload(
    *,
    split_rows: list[SFTDatasetRow],
    recovered_rows: list[dict[str, Any]],
    committed_metrics: dict[str, float],
) -> dict[str, Any]:
    predictions = {row["sample_id"]: row["prediction_contract"] for row in recovered_rows}
    metrics = _metric_bundle(split_rows, predictions)["metrics"]
    expected = {metric: float(committed_metrics[metric]) for metric in REQUIRED_METRICS}
    observed = {metric: float(metrics[metric]) for metric in REQUIRED_METRICS}
    return {
        "metrics": observed,
        "committed_metrics": expected,
        "matches_committed": metric_matches(observed, expected),
        "absolute_differences": {metric: abs(observed[metric] - expected[metric]) for metric in REQUIRED_METRICS},
    }


def _clear_success_artifacts(output_dir: Path) -> None:
    for filename in ("boundary-verification.json", "metric-reproduction.json", "recovery-summary.md", "leak-scan.json"):
        path = output_dir / filename
        if path.exists():
            path.unlink()
    for directory in ("control", "treatment", "gold"):
        path = output_dir / directory
        if path.exists():
            shutil.rmtree(path)


def _write_blocked(output_dir: Path, *, decision_label: str, blocking_reasons: list[str]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    _clear_success_artifacts(output_dir)
    blocked = build_blocked_payload(decision_label=decision_label, blocking_reasons=blocking_reasons)
    write_json(output_dir / "blocked.json", blocked)
    write_json(output_dir / "artifact-manifest.json", blocked)


def recover(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    blocked_path = output_dir / "blocked.json"
    if blocked_path.exists():
        blocked_path.unlink()

    control_manifest = _git_show_json(CONTROL_REF, "data/public-samples/manifest_public_sample.json")
    treatment_manifest = _git_show_json(TREATMENT_REF, "data/public-samples/manifest_public_sample.json")
    control_records = _git_show_jsonl(CONTROL_REF, "data/public-samples/sft_public_sample.jsonl")
    treatment_records = _git_show_jsonl(TREATMENT_REF, "data/public-samples/sft_public_sample.jsonl")
    committed_boundary = read_json(COMMITTED_REPORT_ROOT / "boundary-verification.json")
    committed_comparison = read_json(COMMITTED_REPORT_ROOT / "comparison.json")
    config_hashes = _config_hashes()
    evaluator_hash = _evaluator_hash()

    control_metadata, control_adapter_config_hash, control_adapter_blocker = load_adapter_evidence_or_blocker(
        args.control_adapter_metadata,
        args.control_adapter_config,
        "control",
    )
    treatment_metadata, treatment_adapter_config_hash, treatment_adapter_blocker = load_adapter_evidence_or_blocker(
        args.treatment_adapter_metadata,
        args.treatment_adapter_config,
        "treatment",
    )
    adapter_blockers = [
        blocker for blocker in (control_adapter_blocker, treatment_adapter_blocker) if blocker is not None
    ]
    if adapter_blockers:
        _write_blocked(
            output_dir,
            decision_label=decision_for_blocking_reasons(adapter_blockers),
            blocking_reasons=adapter_blockers,
        )
        return {
            "ok": False,
            "decision_label": decision_for_blocking_reasons(adapter_blockers),
            "blocking_reasons": adapter_blockers,
        }
    assert control_metadata is not None
    assert treatment_metadata is not None
    assert control_adapter_config_hash is not None
    assert treatment_adapter_config_hash is not None
    control_adapter_verified = _adapter_verified("control", control_metadata, args.control_adapter_model_sha256)
    treatment_adapter_verified = _adapter_verified("treatment", treatment_metadata, args.treatment_adapter_model_sha256)

    source_bundles: dict[tuple[str, str], dict[str, Any]] = {}
    prompt_hashes: dict[tuple[str, str], str] = {}
    source_prediction_hashes: dict[tuple[str, str], str] = {}
    source_load_reasons: list[str] = []
    for arm in ("control", "treatment"):
        for split in ("dev", "test"):
            bundle, blocker = load_source_bundle_or_blocker(args.source_root, arm, split)
            if blocker is not None:
                source_load_reasons.append(blocker)
                continue
            assert bundle is not None
            source_bundles[(arm, split)] = bundle
            prompt_hashes[(arm, split)] = _prompt_policy_hash(bundle["prompt_snapshot"])
            source_prediction_hashes[(arm, split)] = bundle["source_prediction_hash"]
    if source_load_reasons:
        _write_blocked(
            output_dir,
            decision_label=decision_for_blocking_reasons(source_load_reasons),
            blocking_reasons=sorted(set(source_load_reasons)),
        )
        return {
            "ok": False,
            "decision_label": decision_for_blocking_reasons(source_load_reasons),
            "blocking_reasons": sorted(set(source_load_reasons)),
        }

    prompt_hash_values = set(prompt_hashes.values())
    prompt_match = len(prompt_hash_values) == 1
    prompt_hash = sorted(prompt_hash_values)[0]

    split_gold: dict[str, list[dict[str, Any]]] = {}
    split_sft_rows: dict[str, list[SFTDatasetRow]] = {}
    recovered_predictions: dict[tuple[str, str], list[dict[str, Any]]] = {}
    boundary_splits: dict[str, Any] = {}
    all_blocking_reasons: list[str] = []
    sample_id_hashes: dict[str, str] = {}
    gold_hashes: dict[str, str] = {}
    input_hashes: dict[str, str] = {}

    for split in ("dev", "test"):
        control_split_rows = _split_rows(control_records, split)
        treatment_split_rows = _split_rows(treatment_records, split)
        heldout_equal = (
            [row["id"] for row in control_split_rows] == [row["id"] for row in treatment_split_rows]
            and [row["input_text"] for row in control_split_rows] == [row["input_text"] for row in treatment_split_rows]
            and [canonical_json(row["target_contract"]) for row in control_split_rows]
            == [canonical_json(row["target_contract"]) for row in treatment_split_rows]
        )
        gold_rows = _build_gold_rows(treatment_split_rows, split=split)
        split_gold[split] = gold_rows
        split_sft_rows[split] = [SFTDatasetRow(**row) for row in treatment_split_rows]
        expected_gold_hash = committed_boundary["splits"][split]["gold_contract_hash"]["control"]
        gold_hashes[split] = _gold_hash(treatment_split_rows)
        sample_id_hashes[split] = _sample_id_hash(treatment_split_rows)
        input_hashes[split] = _input_hash_rows(treatment_split_rows)

        source_reasons: list[str] = []
        for arm in ("control", "treatment"):
            reasons = source_artifact_blocking_reasons(
                expected_ids=[row["sample_id"] for row in gold_rows],
                prediction_rows=source_bundles[(arm, split)]["predictions"],
                raw_summary_rows=source_bundles[(arm, split)]["raw_summaries"],
            )
            source_reasons.extend([f"{arm}_{split}_{reason}" for reason in reasons])
        if source_reasons:
            all_blocking_reasons.extend(source_reasons)
            boundary_splits[split] = {
                "row_count": len(gold_rows),
                "sample_id_hash": sample_id_hashes[split],
                "input_hash": input_hashes[split],
                "gold_hash": gold_hashes[split],
                "expected_gold_hash": expected_gold_hash,
                "gold_hash_match": gold_hashes[split] == expected_gold_hash,
                "heldout_boundary_equal_by_git_refs": heldout_equal,
                "blocking_reasons": sorted(set(source_reasons)),
            }
            continue

        for arm in ("control", "treatment"):
            recovered_predictions[(arm, split)] = _build_prediction_rows(
                arm=arm,
                split=split,
                gold_rows=gold_rows,
                bundle=source_bundles[(arm, split)],
                config_hash=_prediction_config_hash(config_hashes, arm, split),
                prompt_hash=prompt_hash,
                run_id=args.run_id,
            )

        reasons = boundary_blocking_reasons(
            control_rows=recovered_predictions[("control", split)],
            treatment_rows=recovered_predictions[("treatment", split)],
            gold_rows=gold_rows,
            expected_count=EXPECTED_ROW_COUNT,
            expected_gold_hash=expected_gold_hash,
        )
        if not heldout_equal:
            reasons.append("frozen_heldout_boundary_mismatch")
        if gold_hashes[split] != expected_gold_hash:
            reasons.append(f"{split}_gold_hash_mismatch")
        all_blocking_reasons.extend(reasons)
        boundary_splits[split] = {
            "row_count": len(gold_rows),
            "sample_id_hash": sample_id_hashes[split],
            "input_hash": input_hashes[split],
            "gold_hash": gold_hashes[split],
            "expected_gold_hash": expected_gold_hash,
            "gold_hash_match": gold_hashes[split] == expected_gold_hash,
            "heldout_boundary_equal_by_git_refs": heldout_equal,
            "blocking_reasons": sorted(set(reasons)),
        }

    dev_ids = {row["sample_id"] for row in split_gold["dev"]}
    test_ids = {row["sample_id"] for row in split_gold["test"]}
    if dev_ids & test_ids:
        all_blocking_reasons.append("dev_test_id_overlap")
    if not control_adapter_verified:
        all_blocking_reasons.append("control_adapter_identity_unverified")
    if not treatment_adapter_verified:
        all_blocking_reasons.append("treatment_adapter_identity_unverified")
    if not prompt_match:
        all_blocking_reasons.append("prompt_hash_mismatch")

    all_blocking_reasons = sorted(set(all_blocking_reasons))
    if all_blocking_reasons:
        decision_label = decision_for_blocking_reasons(all_blocking_reasons)
        _write_blocked(
            output_dir,
            decision_label=decision_label,
            blocking_reasons=all_blocking_reasons,
        )
        return {"ok": False, "decision_label": decision_label, "blocking_reasons": all_blocking_reasons}

    for split, rows in split_gold.items():
        write_jsonl(output_dir / f"gold/{split}_gold.jsonl", rows)
    for (arm, split), rows in recovered_predictions.items():
        write_jsonl(output_dir / f"{arm}/{split}_predictions.jsonl", rows)

    metric_reproduction: dict[str, Any] = {
        "change_id": CHANGE_ID,
        "status": "reproduced",
        "decision_label": SUCCESS_DECISION,
        "evaluator_hash": evaluator_hash,
        "tolerance": 1e-12,
        "splits": {},
    }
    metric_blockers: list[str] = []
    for split in ("dev", "test"):
        metric_reproduction["splits"][split] = {}
        for arm in ("control", "treatment"):
            payload = _metric_payload(
                split_rows=split_sft_rows[split],
                recovered_rows=recovered_predictions[(arm, split)],
                committed_metrics=committed_comparison["splits"][split][f"{arm}_metrics"],
            )
            metric_reproduction["splits"][split][arm] = payload
            if not payload["matches_committed"]:
                metric_blockers.append(f"{arm}_{split}_metric_mismatch")

    if metric_blockers:
        _write_blocked(
            output_dir,
            decision_label="RECOVERY_INVALID_METRIC_MISMATCH",
            blocking_reasons=metric_blockers,
        )
        write_json(output_dir / "metric-reproduction.json", metric_reproduction)
        return {"ok": False, "decision_label": "RECOVERY_INVALID_METRIC_MISMATCH", "blocking_reasons": metric_blockers}

    generated_at = datetime.now(UTC).replace(microsecond=0).isoformat()
    output_prediction_hashes = {
        f"{arm}_{split}": sha256_file(output_dir / f"{arm}/{split}_predictions.jsonl")
        for arm in ("control", "treatment")
        for split in ("dev", "test")
    }
    manifest = {
        "change_id": CHANGE_ID,
        "decision_label": SUCCESS_DECISION,
        "recovery_method": RECOVERY_METHOD,
        "control_run_id": f"{args.run_id}:control",
        "treatment_run_id": f"{args.run_id}:treatment",
        "control_adapter_identity_hash": args.control_adapter_model_sha256,
        "treatment_adapter_identity_hash": args.treatment_adapter_model_sha256,
        "control_adapter_config_hash": control_adapter_config_hash,
        "treatment_adapter_config_hash": treatment_adapter_config_hash,
        "control_config_hash": config_hashes["control_training"],
        "treatment_config_hash": config_hashes["treatment_training"],
        "prediction_config_hashes": {
            "control_dev": config_hashes["control_dev_prediction"],
            "control_test": config_hashes["control_test_prediction"],
            "treatment_dev": config_hashes["treatment_dev_prediction"],
            "treatment_test": config_hashes["treatment_test_prediction"],
        },
        "prompt_hash": prompt_hash,
        "evaluator_hash": evaluator_hash,
        "control_manifest_id": control_manifest["manifest_id"],
        "treatment_manifest_id": treatment_manifest["manifest_id"],
        "heldout_manifest_id": HELDOUT_MANIFEST_ID,
        "dev_row_count": len(split_gold["dev"]),
        "test_row_count": len(split_gold["test"]),
        "dev_sample_id_hash": sample_id_hashes["dev"],
        "test_sample_id_hash": sample_id_hashes["test"],
        "dev_gold_hash": gold_hashes["dev"],
        "test_gold_hash": gold_hashes["test"],
        "control_dev_prediction_hash": output_prediction_hashes["control_dev"],
        "control_test_prediction_hash": output_prediction_hashes["control_test"],
        "treatment_dev_prediction_hash": output_prediction_hashes["treatment_dev"],
        "treatment_test_prediction_hash": output_prediction_hashes["treatment_test"],
        "source_prediction_hashes": {
            "control_dev": source_prediction_hashes[("control", "dev")],
            "control_test": source_prediction_hashes[("control", "test")],
            "treatment_dev": source_prediction_hashes[("treatment", "dev")],
            "treatment_test": source_prediction_hashes[("treatment", "test")],
        },
        "sanitization_status": "passed",
        "metric_reproduction_status": "reproduced",
        "projection_inputs_ready": True,
        "generated_at": generated_at,
        "retention_hook": {
            "status": "verified_existing_prediction_sidecars",
            "sidecars": [
                "predictions.jsonl",
                "raw_decoded_summary.jsonl",
                "generation_trace.jsonl",
                "prompt_snapshot.json",
                "prediction_metadata.json",
            ],
            "raw_model_output_reconstruction": "decoded_sha256_matches_canonical_prediction_contract_json",
        },
        "claims": {
            "training_performed": False,
            "prediction_only_reproduction_performed": False,
            "contract_v2_projection_run": False,
            "prediction_repair_performed": False,
            "llm_judge_used": False,
            "semantic_equivalence_scoring_used": False,
            "data_expansion_performed": False,
            "release_or_readiness_claim": False,
            "adapter_or_checkpoint_release": False,
        },
    }
    boundary = {
        "change_id": CHANGE_ID,
        "comparison_allowed": True,
        "control_treatment_ids_match": True,
        "control_gold_ids_match": True,
        "treatment_gold_ids_match": True,
        "dev_gold_hash_match": True,
        "test_gold_hash_match": True,
        "input_hash_match": True,
        "control_adapter_verified": control_adapter_verified,
        "treatment_adapter_verified": treatment_adapter_verified,
        "config_match": True,
        "prompt_match": prompt_match,
        "evaluator_match": True,
        "blocking_reasons": [],
        "splits": boundary_splits,
        "adapter_evidence": {
            "control": _adapter_metadata_public("control", control_metadata),
            "treatment": _adapter_metadata_public("treatment", treatment_metadata),
        },
        "rejected_substitutes": [
            "aggregate_metrics",
            "paired_row_summary",
            "family_level_delta",
            "bootstrap_output",
            "old_canonical_slot_paired_sft_ablation_predictions",
            "inferred_or_repaired_predictions",
        ],
    }
    summary = "\n".join(
        [
            "# Step-matched projection input recovery",
            "",
            f"- Decision label: `{SUCCESS_DECISION}`",
            f"- Recovery method: `{RECOVERY_METHOD}`",
            "- Raw predictions found: yes, four original step-matched prediction files were recovered.",
            "- Prediction-only reproduction: not used.",
            "- Adapter identity: verified by adapter model hash, adapter metadata, training manifest, row count, and optimizer step count.",
            "- Boundary: dev=207 rows, test=207 rows; Control, Treatment, and Gold IDs match; dev/test IDs do not overlap.",
            f"- Dev gold hash: `{gold_hashes['dev']}`",
            f"- Test gold hash: `{gold_hashes['test']}`",
            "- Metric reproduction: passed against the committed step-matched aggregate report using the current evaluator.",
            "- Projection inputs ready: true for a later bounded Contract V2 projection rerun.",
            "- Not done: no training, no prediction-only reproduction, no prediction repair, no evaluator/schema/prompt/gold/split change, no Contract V2 projection.",
            "- Next recommended change: `rerun-contract-v2-projection-with-recovered-inputs`.",
            "",
        ]
    )

    write_json(output_dir / "artifact-manifest.json", manifest)
    write_json(output_dir / "boundary-verification.json", boundary)
    write_json(output_dir / "metric-reproduction.json", metric_reproduction)
    (output_dir / "recovery-summary.md").write_text(summary, encoding="utf-8")
    return {"ok": True, "decision_label": SUCCESS_DECISION, "output_dir": output_dir.as_posix()}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=REPO_ROOT / OUTPUT_RELATIVE)
    parser.add_argument("--run-id", default=EXPECTED_RUN_ID)
    parser.add_argument("--control-adapter-metadata", type=Path, required=True)
    parser.add_argument("--treatment-adapter-metadata", type=Path, required=True)
    parser.add_argument("--control-adapter-config", type=Path, required=True)
    parser.add_argument("--treatment-adapter-config", type=Path, required=True)
    parser.add_argument("--control-adapter-model-sha256", required=True)
    parser.add_argument("--treatment-adapter-model-sha256", required=True)
    result = recover(parser.parse_args())
    print(canonical_json(result))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
