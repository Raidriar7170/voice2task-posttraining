from __future__ import annotations

import json
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import MappingProxyType
from typing import Any, Literal

from voice2task.contract_v2_projection import deterministic_normalized_command_renderer
from voice2task.evaluation import evaluate_predictions, run_execution_smoke
from voice2task.io import read_jsonl, write_json
from voice2task.layered_evaluation import evaluate_layered_predictions
from voice2task.schemas import (
    ROUTES,
    TASK_TYPES,
    BrowserTaskContract,
    SFTDatasetRow,
    ValidationError,
    as_contract,
    canonical_contract_json,
)

CORE_FIELDS = ("task_type", "route", "safety", "confirmation_required", "slots")
ENVELOPE_FIELDS = ("normalized_command", "language", "contract_version")
PROVENANCE_LEGACY_PRESERVED: Literal["legacy_preserved"] = "legacy_preserved"
PROVENANCE_DETERMINISTIC_RENDERED: Literal["deterministic_rendered"] = "deterministic_rendered"
PROVENANCE_UNSUPPORTED: Literal["unsupported"] = "unsupported"
ENVELOPE_BUILD_MODES = ("preserve_legacy", "derive_display")
EVALUATOR_REGRESSION_METRICS = (
    "json_parse_rate",
    "strict_schema_valid_rate",
    "semantic_contract_valid_rate",
    "contract_exact_match_strict",
    "strict_slot_f1",
    "slot_value_exact_f1",
    "slot_value_normalized_f1",
    "executable_contract_pass_rate",
    "schema_validity",
    "json_valid_rate",
    "route_accuracy",
    "task_type_accuracy",
    "safety_recall",
    "unsafe_false_negative_rate",
    "requires_confirmation_accuracy",
)


class ContractCoreV2Error(ValidationError):
    """Raised when the internal Contract V2 Core boundary cannot be satisfied."""


class UnsupportedRendererError(ContractCoreV2Error):
    """Raised when derive_display cannot render a deterministic V1 display field."""


def _copy_jsonable(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False))


def _freeze_jsonable(value: Any) -> Any:
    copied = _copy_jsonable(value)
    if isinstance(copied, dict):
        return MappingProxyType({str(key): _freeze_jsonable(item) for key, item in copied.items()})
    if isinstance(copied, list):
        return tuple(_freeze_jsonable(item) for item in copied)
    return copied


def _thaw_jsonable(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _thaw_jsonable(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_jsonable(item) for item in value]
    return _copy_jsonable(value)


@dataclass(frozen=True)
class ContractCoreV2:
    task_type: str
    route: str
    safety: Mapping[str, Any]
    confirmation_required: bool
    slots: Mapping[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(self, "safety", _freeze_jsonable(self.safety))
        object.__setattr__(self, "slots", _freeze_jsonable(self.slots))
        _validate_core_values(
            {
                "task_type": self.task_type,
                "route": self.route,
                "safety": self.safety,
                "confirmation_required": self.confirmation_required,
                "slots": self.slots,
            }
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_type": self.task_type,
            "route": self.route,
            "safety": _thaw_jsonable(self.safety),
            "confirmation_required": self.confirmation_required,
            "slots": _thaw_jsonable(self.slots),
        }


@dataclass(frozen=True)
class ContractEnvelopeMetadata:
    normalized_command: str
    language: str = "zh-CN"
    contract_version: str = "v1"
    normalized_command_provenance: Literal["legacy_preserved", "deterministic_rendered", "unsupported"] = (
        PROVENANCE_LEGACY_PRESERVED
    )

    def __post_init__(self) -> None:
        if not isinstance(self.normalized_command, str) or not self.normalized_command.strip():
            raise ContractCoreV2Error("normalized_command must be a non-empty string")
        if self.language != "zh-CN":
            raise ContractCoreV2Error("language must be zh-CN")
        if self.contract_version != "v1":
            raise ContractCoreV2Error("contract_version must be v1")
        if self.normalized_command_provenance not in {
            PROVENANCE_LEGACY_PRESERVED,
            PROVENANCE_DETERMINISTIC_RENDERED,
            PROVENANCE_UNSUPPORTED,
        }:
            raise ContractCoreV2Error("unsupported normalized_command_provenance")

    def to_dict(self) -> dict[str, str]:
        return {
            "language": self.language,
            "contract_version": self.contract_version,
            "normalized_command": self.normalized_command,
            "normalized_command_provenance": self.normalized_command_provenance,
        }


def _validate_core_values(values: Mapping[str, Any]) -> None:
    if values["task_type"] not in TASK_TYPES:
        raise ContractCoreV2Error(f"task_type must be one of {sorted(TASK_TYPES)}")
    if values["route"] not in ROUTES:
        raise ContractCoreV2Error(f"route must be one of {sorted(ROUTES)}")
    safety = values["safety"]
    if not isinstance(safety, Mapping):
        raise ContractCoreV2Error("safety must be an object")
    safety_fields = {str(key) for key in safety}
    if safety_fields != {"allow", "reason"}:
        missing = sorted({"allow", "reason"} - safety_fields)
        extra = sorted(safety_fields - {"allow", "reason"})
        details = []
        if missing:
            details.append(f"missing: {', '.join(missing)}")
        if extra:
            details.append(f"extra: {', '.join(extra)}")
        raise ContractCoreV2Error(f"safety must contain exactly allow and reason ({'; '.join(details)})")
    if not isinstance(safety.get("allow"), bool):
        raise ContractCoreV2Error("safety.allow must be a boolean")
    reason = safety.get("reason")
    if not isinstance(reason, str) or not reason.strip():
        raise ContractCoreV2Error("safety.reason must be a non-empty string")
    if not isinstance(values["confirmation_required"], bool):
        raise ContractCoreV2Error("confirmation_required must be a boolean")
    if not isinstance(values["slots"], Mapping):
        raise ContractCoreV2Error("slots must be an object")


def validate_contract_core_v2(core: ContractCoreV2 | Mapping[str, Any]) -> ContractCoreV2:
    if isinstance(core, ContractCoreV2):
        return core
    if not isinstance(core, Mapping):
        raise ContractCoreV2Error("ContractCoreV2 must be an object")
    fields = set(core)
    expected = set(CORE_FIELDS)
    missing = sorted(expected - fields)
    extra = sorted(fields - expected)
    if missing:
        raise ContractCoreV2Error(f"missing ContractCoreV2 fields: {', '.join(missing)}")
    if extra:
        raise ContractCoreV2Error(f"extra ContractCoreV2 fields: {', '.join(extra)}")
    return ContractCoreV2(
        task_type=str(core["task_type"]),
        route=str(core["route"]),
        safety=_copy_jsonable(core["safety"]),
        confirmation_required=core["confirmation_required"],
        slots=_copy_jsonable(core["slots"]),
    )


def project_v1_to_core_v2(v1_contract: BrowserTaskContract | Mapping[str, Any]) -> ContractCoreV2:
    try:
        parsed = as_contract(v1_contract if isinstance(v1_contract, BrowserTaskContract) else dict(v1_contract))
    except (TypeError, ValidationError) as exc:
        raise ContractCoreV2Error(str(exc)) from exc
    return ContractCoreV2(
        task_type=parsed.task_type,
        route=parsed.route,
        safety=parsed.safety,
        confirmation_required=parsed.confirmation_required,
        slots=parsed.slots,
    )


def extract_v1_envelope_metadata(v1_contract: BrowserTaskContract | Mapping[str, Any]) -> ContractEnvelopeMetadata:
    try:
        parsed = as_contract(v1_contract if isinstance(v1_contract, BrowserTaskContract) else dict(v1_contract))
    except (TypeError, ValidationError) as exc:
        raise ContractCoreV2Error(str(exc)) from exc
    return ContractEnvelopeMetadata(
        normalized_command=parsed.normalized_command,
        language=parsed.language,
        contract_version=parsed.contract_version,
        normalized_command_provenance=PROVENANCE_LEGACY_PRESERVED,
    )


def build_v1_compatible_envelope(
    core: ContractCoreV2 | Mapping[str, Any],
    metadata: ContractEnvelopeMetadata | None = None,
    *,
    mode: Literal["preserve_legacy", "derive_display"] = "preserve_legacy",
) -> BrowserTaskContract:
    parsed_core = validate_contract_core_v2(core)
    core_dict = parsed_core.to_dict()
    if mode == "preserve_legacy":
        if metadata is None:
            raise ContractCoreV2Error("preserve_legacy mode requires envelope metadata")
        normalized_command = metadata.normalized_command
        language = metadata.language
        contract_version = metadata.contract_version
    elif mode == "derive_display":
        rendered = deterministic_normalized_command_renderer(core_dict)
        if not rendered.get("supported"):
            reason = str(rendered.get("reason") or "unsupported")
            raise UnsupportedRendererError(f"derive_display unsupported: {reason}")
        normalized_command = str(rendered["normalized_command"])
        language = "zh-CN"
        contract_version = "v1"
    else:
        raise ContractCoreV2Error(f"unsupported envelope build mode: {mode}")
    try:
        return BrowserTaskContract.from_dict(
            {
                **core_dict,
                "normalized_command": normalized_command,
                "language": language,
                "contract_version": contract_version,
            }
        )
    except ValidationError as exc:
        raise ContractCoreV2Error(str(exc)) from exc


def roundtrip_v1_through_core(v1_contract: BrowserTaskContract | Mapping[str, Any]) -> BrowserTaskContract:
    metadata = extract_v1_envelope_metadata(v1_contract)
    core = project_v1_to_core_v2(v1_contract)
    return build_v1_compatible_envelope(core, metadata=metadata, mode="preserve_legacy")


def canonical_core_v2_json(core: ContractCoreV2 | Mapping[str, Any]) -> str:
    return json.dumps(
        validate_contract_core_v2(core).to_dict(),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def compare_v1_roundtrip(
    original: BrowserTaskContract | Mapping[str, Any],
    rebuilt: BrowserTaskContract | Mapping[str, Any],
) -> dict[str, Any]:
    original_contract = as_contract(original if isinstance(original, BrowserTaskContract) else dict(original))
    rebuilt_contract = as_contract(rebuilt if isinstance(rebuilt, BrowserTaskContract) else dict(rebuilt))
    original_dict = original_contract.to_dict()
    rebuilt_dict = rebuilt_contract.to_dict()
    roundtrip_exact = canonical_contract_json(original_contract) == canonical_contract_json(rebuilt_contract)
    return {
        "roundtrip_exact": roundtrip_exact,
        "safety_preserved": rebuilt_dict["safety"] == original_dict["safety"],
        "confirmation_preserved": rebuilt_dict["confirmation_required"] == original_dict["confirmation_required"],
        "slots_preserved": rebuilt_dict["slots"] == original_dict["slots"],
        "normalized_command_preserved": rebuilt_dict["normalized_command"] == original_dict["normalized_command"],
        "language_preserved": rebuilt_dict["language"] == original_dict["language"],
        "contract_version_preserved": rebuilt_dict["contract_version"] == original_dict["contract_version"],
        "failure_reason": None if roundtrip_exact else "canonical_v1_roundtrip_mismatch",
    }


def check_v1_core_compatibility(v1_contract: BrowserTaskContract | Mapping[str, Any]) -> dict[str, Any]:
    base: dict[str, Any] = {
        "v1_valid": False,
        "core_valid": False,
        "roundtrip_exact": False,
        "safety_preserved": False,
        "confirmation_preserved": False,
        "slots_preserved": False,
        "normalized_command_preserved": False,
        "language_preserved": False,
        "contract_version_preserved": False,
        "failure_reason": None,
    }
    try:
        raw_contract = v1_contract.to_dict() if isinstance(v1_contract, BrowserTaskContract) else v1_contract
        original = as_contract(_copy_jsonable(raw_contract))
        base["v1_valid"] = True
        core = project_v1_to_core_v2(original)
        validate_contract_core_v2(core)
        base["core_valid"] = True
        rebuilt = build_v1_compatible_envelope(core, metadata=extract_v1_envelope_metadata(original))
        comparison = compare_v1_roundtrip(original, rebuilt)
    except (TypeError, ValidationError, ContractCoreV2Error) as exc:
        base["failure_reason"] = str(exc)
        return base
    return {**base, **comparison, "v1_valid": True, "core_valid": True}


def generate_internal_contract_v2_core_report(repo_root: Path, output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    contract_records = list(_iter_current_public_contracts(repo_root))
    matrix = _compatibility_matrix(contract_records)
    regression = _evaluator_regression(repo_root)
    decision = _decision_label(matrix, regression)
    summary = _summary(repo_root, output_dir, matrix, regression, decision)

    write_json(output_dir / "compatibility-matrix.json", matrix)
    write_json(output_dir / "evaluator-regression.json", regression)
    write_json(output_dir / "summary.json", summary)
    (output_dir / "summary.md").write_text(_summary_markdown(summary), encoding="utf-8")
    (output_dir / "decision.md").write_text(_decision_markdown(summary), encoding="utf-8")
    return {"decision_label": decision, "output_dir": _relative_path(repo_root, output_dir), "summary": summary}


def _iter_current_public_contracts(repo_root: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    sources = (
        ("formal_seed_target", repo_root / "data/public-samples/seed_traces.jsonl", "target_contract", "id"),
        ("sft_target", repo_root / "data/public-samples/sft_public_sample.jsonl", "target_contract", "id"),
    )
    for source_kind, path, contract_key, id_key in sources:
        for row in read_jsonl(path):
            records.append(
                {
                    "source_kind": source_kind,
                    "source_path": _relative_path(repo_root, path),
                    "id": str(row.get(id_key, "")),
                    "contract": row.get(contract_key),
                }
            )

    raw_inputs = repo_root / "reports/public-sample/step-matched-canonical-slot-ablation/raw-inputs"
    for split in ("dev", "test"):
        gold_path = raw_inputs / "gold" / f"{split}_gold.jsonl"
        for row in read_jsonl(gold_path):
            records.append(
                {
                    "source_kind": f"{split}_gold",
                    "source_path": _relative_path(repo_root, gold_path),
                    "id": str(row.get("sample_id", "")),
                    "contract": row.get("gold_contract"),
                }
            )
        for arm in ("control", "treatment"):
            pred_path = raw_inputs / arm / f"{split}_predictions.jsonl"
            for row in read_jsonl(pred_path):
                records.append(
                    {
                        "source_kind": f"{arm}_{split}_prediction",
                        "source_path": _relative_path(repo_root, pred_path),
                        "id": str(row.get("sample_id", "")),
                        "contract": row.get("prediction_contract"),
                    }
                )
    return records


def _compatibility_matrix(records: list[dict[str, Any]]) -> dict[str, Any]:
    source_counts: Counter[str] = Counter()
    failures: Counter[str] = Counter()
    unsupported_reasons: Counter[str] = Counter()
    total = v1_valid = core_valid = roundtrip = 0
    safety = confirmation = slots = normalized = language = version = 0
    derive_supported = 0
    for record in records:
        total += 1
        source_counts.update([str(record["source_kind"])])
        result = check_v1_core_compatibility(record["contract"])
        if result["v1_valid"]:
            v1_valid += 1
        if result["core_valid"]:
            core_valid += 1
        if result["roundtrip_exact"]:
            roundtrip += 1
        if result["safety_preserved"]:
            safety += 1
        if result["confirmation_preserved"]:
            confirmation += 1
        if result["slots_preserved"]:
            slots += 1
        if result["normalized_command_preserved"]:
            normalized += 1
        if result["language_preserved"]:
            language += 1
        if result["contract_version_preserved"]:
            version += 1
        if result["failure_reason"]:
            failures.update([str(result["failure_reason"])])
        try:
            rendered = deterministic_normalized_command_renderer(project_v1_to_core_v2(record["contract"]).to_dict())
        except ContractCoreV2Error as exc:
            unsupported_reasons.update([str(exc)])
            continue
        if rendered.get("supported"):
            derive_supported += 1
        else:
            unsupported_reasons.update([str(rendered.get("reason") or "unsupported")])
    return {
        "evidence_kind": "internal_contract_v2_core_compatibility_matrix",
        "total_contracts_checked": total,
        "v1_valid_count": v1_valid,
        "core_projection_success_count": core_valid,
        "preserve_roundtrip_exact_count": roundtrip,
        "preserve_roundtrip_exact_rate": _rate(roundtrip, total),
        "safety_preservation_rate": _rate(safety, total),
        "confirmation_preservation_rate": _rate(confirmation, total),
        "slots_preservation_rate": _rate(slots, total),
        "normalized_command_preservation_rate": _rate(normalized, total),
        "language_preservation_rate": _rate(language, total),
        "contract_version_preservation_rate": _rate(version, total),
        "derive_display_supported_count": derive_supported,
        "derive_display_supported_rate": _rate(derive_supported, total),
        "derive_display_unsupported_count": total - derive_supported,
        "derive_display_unsupported_reasons": dict(sorted(unsupported_reasons.items())),
        "failures_by_reason": dict(sorted(failures.items())),
        "source_counts": dict(sorted(source_counts.items())),
        "execution_smoke_fixture_covered": True,
        "execution_smoke_fixture": "data/public-samples/execution_smoke_target.json",
        "claims": _claims(),
    }


def _evaluator_regression(repo_root: Path) -> dict[str, Any]:
    by_arm_split: dict[str, Any] = {}
    metric_deltas: dict[str, list[float]] = {metric: [] for metric in EVALUATOR_REGRESSION_METRICS}
    for arm in ("control", "treatment"):
        for split in ("dev", "test"):
            rows, before_predictions = _load_recovered_split(repo_root, arm, split)
            after_predictions = {
                row_id: _roundtrip_prediction_contract(prediction)
                for row_id, prediction in before_predictions.items()
            }
            before = _selected_metrics(rows, before_predictions)
            after = _selected_metrics(rows, after_predictions)
            deltas = {metric: after[metric] - before[metric] for metric in EVALUATOR_REGRESSION_METRICS}
            key = f"{arm}_{split}"
            by_arm_split[key] = {
                "before": before,
                "after": after,
                "absolute_delta": {metric: abs(delta) for metric, delta in deltas.items()},
            }
            for metric, delta in deltas.items():
                metric_deltas[metric].append(abs(delta))

    smoke = _smoke_regression(repo_root)
    metrics = {
        metric: {
            "before": {key: value["before"][metric] for key, value in by_arm_split.items()},
            "after": {key: value["after"][metric] for key, value in by_arm_split.items()},
            "absolute_delta": max(values) if values else 0.0,
            "passed": (max(values) if values else 0.0) == 0,
        }
        for metric, values in metric_deltas.items()
    }
    passed = all(metric["passed"] for metric in metrics.values()) and smoke["unchanged"]
    return {
        "evidence_kind": "internal_contract_v2_core_evaluator_regression",
        "passed": passed,
        "metrics": metrics,
        "by_arm_split": by_arm_split,
        "execution_smoke": smoke,
        "claims": _claims(),
    }


def _load_recovered_split(repo_root: Path, arm: str, split: str) -> tuple[list[SFTDatasetRow], dict[str, Any]]:
    raw_inputs = repo_root / "reports/public-sample/step-matched-canonical-slot-ablation/raw-inputs"
    gold_rows = read_jsonl(raw_inputs / "gold" / f"{split}_gold.jsonl")
    prediction_rows = read_jsonl(raw_inputs / arm / f"{split}_predictions.jsonl")
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
    predictions = {str(row["sample_id"]): row.get("prediction_contract") for row in prediction_rows}
    return rows, predictions


def _roundtrip_prediction_contract(prediction: Any) -> Any:
    try:
        return roundtrip_v1_through_core(prediction).to_dict()
    except (TypeError, ValidationError, ContractCoreV2Error):
        return prediction


def _selected_metrics(rows: list[SFTDatasetRow], predictions: dict[str, Any]) -> dict[str, Any]:
    strict = evaluate_predictions(rows, predictions)
    layered = evaluate_layered_predictions(rows, predictions)
    return {
        "json_parse_rate": strict.metrics["json_parse_rate"],
        "strict_schema_valid_rate": strict.metrics["strict_schema_valid_rate"],
        "semantic_contract_valid_rate": strict.metrics["semantic_contract_valid_rate"],
        "contract_exact_match_strict": layered["metrics"]["contract_exact_match_strict"],
        "strict_slot_f1": strict.metrics["slot_f1"],
        "slot_value_exact_f1": layered["metrics"]["slot_value_exact_f1"],
        "slot_value_normalized_f1": layered["metrics"]["slot_value_normalized_f1"],
        "executable_contract_pass_rate": layered["metrics"]["executable_contract_pass_rate"],
        "schema_validity": layered["metrics"]["schema_validity"],
        "json_valid_rate": strict.metrics["json_valid_rate"],
        "route_accuracy": layered["metrics"]["route_accuracy"],
        "task_type_accuracy": layered["metrics"]["task_type_accuracy"],
        "safety_recall": strict.metrics["safety_recall"],
        "unsafe_false_negative_rate": layered["metrics"]["unsafe_false_negative_rate"],
        "requires_confirmation_accuracy": layered["metrics"]["requires_confirmation_accuracy"],
    }


def _smoke_regression(repo_root: Path) -> dict[str, Any]:
    rows, predictions = _load_recovered_split(repo_root, "control", "dev")
    rows = rows[:12]
    prediction_subset = {row.id: predictions[row.id] for row in rows}
    after_subset = {row_id: _roundtrip_prediction_contract(pred) for row_id, pred in prediction_subset.items()}
    target = repo_root / "data/public-samples/execution_smoke_target.json"
    before = run_execution_smoke(rows, prediction_subset, enabled=True, target_path=target).to_dict()
    after = run_execution_smoke(rows, after_subset, enabled=True, target_path=target).to_dict()
    return {
        "fixture": "data/public-samples/execution_smoke_target.json",
        "sample_size": len(rows),
        "before": _public_smoke_result(repo_root, before),
        "after": _public_smoke_result(repo_root, after),
        "unchanged": before == after,
    }


def _public_smoke_result(repo_root: Path, value: dict[str, Any]) -> dict[str, Any]:
    cleaned = dict(value)
    target = cleaned.get("target")
    if isinstance(target, str):
        cleaned["target"] = _relative_path(repo_root, Path(target))
    return cleaned


def _decision_label(matrix: dict[str, Any], regression: dict[str, Any]) -> str:
    preserve_ok = (
        matrix["preserve_roundtrip_exact_rate"] == 1.0
        and matrix["safety_preservation_rate"] == 1.0
        and matrix["confirmation_preservation_rate"] == 1.0
        and matrix["slots_preservation_rate"] == 1.0
        and regression["passed"]
    )
    if not preserve_ok:
        return "V1_COMPATIBILITY_BLOCKED"
    if matrix["derive_display_unsupported_count"] == 0:
        return "INTERNAL_V2_CORE_READY_V1_COMPATIBLE"
    return "INTERNAL_V2_CORE_READY_RENDERER_PARTIAL"


def _summary(
    repo_root: Path,
    output_dir: Path,
    matrix: dict[str, Any],
    regression: dict[str, Any],
    decision_label: str,
) -> dict[str, Any]:
    return {
        "evidence_kind": "internal_contract_v2_core_summary",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "decision_label": decision_label,
        "default_external_schema": "BrowserTaskContract V1",
        "training_target_changed": False,
        "downstream_runtime_changed": False,
        "core_fields": list(CORE_FIELDS),
        "envelope_metadata_fields": [*ENVELOPE_FIELDS, "normalized_command_provenance"],
        "normalized_command_provenance_internal_only": True,
        "preserve_roundtrip_exact_rate": matrix["preserve_roundtrip_exact_rate"],
        "safety_preservation_rate": matrix["safety_preservation_rate"],
        "confirmation_preservation_rate": matrix["confirmation_preservation_rate"],
        "slots_preservation_rate": matrix["slots_preservation_rate"],
        "derive_display_supported_rate": matrix["derive_display_supported_rate"],
        "derive_display_unsupported_count": matrix["derive_display_unsupported_count"],
        "v1_evaluator_metrics_zero_delta": regression["passed"],
        "execution_smoke_unchanged": regression["execution_smoke"]["unchanged"],
        "source_artifacts": {
            "formal_seed_contracts": "data/public-samples/seed_traces.jsonl",
            "sft_target_contracts": "data/public-samples/sft_public_sample.jsonl",
            "recovered_raw_inputs": "reports/public-sample/step-matched-canonical-slot-ablation/raw-inputs",
            "execution_smoke_fixture": "data/public-samples/execution_smoke_target.json",
        },
        "report_artifacts": {
            "compatibility_matrix": _artifact_path(repo_root, output_dir / "compatibility-matrix.json"),
            "evaluator_regression": _artifact_path(repo_root, output_dir / "evaluator-regression.json"),
            "decision": _artifact_path(repo_root, output_dir / "decision.md"),
        },
        "claims": _claims(),
        "cannot_claim": [
            "model improvement",
            "executable quality improvement",
            "slot error solution",
            "public production V2 schema",
            "V2 training target",
            "downstream runtime migration",
            "production readiness",
            "safety readiness",
        ],
        "recommended_next_change": "analyze-slot-error-mechanisms-and-design-slot-representation",
        "repo_root": _relative_path(repo_root, repo_root),
    }


def _summary_markdown(summary: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Internal Contract V2 Core Summary",
            "",
            f"- Decision label: `{summary['decision_label']}`",
            f"- Default external schema: `{summary['default_external_schema']}`",
            f"- Core fields: `{summary['core_fields']}`",
            f"- Envelope metadata fields: `{summary['envelope_metadata_fields']}`",
            f"- Preserve roundtrip exact rate: `{summary['preserve_roundtrip_exact_rate']}`",
            f"- Safety preservation rate: `{summary['safety_preservation_rate']}`",
            f"- Confirmation preservation rate: `{summary['confirmation_preservation_rate']}`",
            f"- Slots preservation rate: `{summary['slots_preservation_rate']}`",
            f"- Derive-display supported rate: `{summary['derive_display_supported_rate']}`",
            f"- Derive-display unsupported count: `{summary['derive_display_unsupported_count']}`",
            f"- V1 evaluator metrics zero delta: `{summary['v1_evaluator_metrics_zero_delta']}`",
            f"- Execution smoke unchanged: `{summary['execution_smoke_unchanged']}`",
            "",
            "No training, prediction rerun, evaluator relaxation, V1 schema migration, "
            "or downstream runtime migration occurred.",
            "",
        ]
    )


def _decision_markdown(summary: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Internal Contract V2 Core Decision",
            "",
            f"Decision: `{summary['decision_label']}`.",
            "",
            "This decision means the internal core boundary is available for shadow compatibility checks while "
            "BrowserTaskContract V1 remains the external schema and current training target.",
            "",
            "Still not claimed: model improvement, executable quality improvement, slot-error resolution, "
            "production readiness, safety readiness, public V2 schema migration, or downstream runtime migration.",
            "",
            f"Recommended next technical change: `{summary['recommended_next_change']}`.",
            "",
        ]
    )


def _claims() -> dict[str, bool]:
    return {
        "training_performed": False,
        "prediction_rerun_performed": False,
        "data_mutation_performed": False,
        "split_change_performed": False,
        "prompt_change_performed": False,
        "decoding_change_performed": False,
        "evaluator_relaxation_performed": False,
        "prediction_repair_performed": False,
        "llm_judge_used": False,
        "semantic_equivalence_scoring_used": False,
        "external_v1_schema_changed": False,
        "v2_training_target_enabled": False,
        "downstream_runtime_migrated": False,
        "adapter_or_checkpoint_release": False,
        "model_improvement_claim": False,
        "executable_quality_improvement_claim": False,
        "safety_or_production_readiness_claim": False,
    }


def _rate(count: int, total: int) -> float:
    return 0.0 if total == 0 else count / total


def _relative_path(repo_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.name


def _artifact_path(repo_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return f"{path.parent.name}/{path.name}"
