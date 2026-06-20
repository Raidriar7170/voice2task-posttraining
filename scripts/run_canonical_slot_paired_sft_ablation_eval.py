from __future__ import annotations

import argparse
import json
import shutil
from collections import defaultdict
from pathlib import Path
from typing import Any

from voice2task.evaluation import evaluate_predictions, load_predictions, load_sft_rows
from voice2task.io import read_json, write_json, write_jsonl
from voice2task.layered_evaluation import (
    _executable_contract_pass,
    _is_unsafe_false_negative,
    _prediction_to_contract,
    evaluate_layered_predictions,
)
from voice2task.schemas import SFTDatasetRow, as_contract

PRIMARY_METRICS = [
    "contract_exact_match_strict",
    "slot_value_exact_f1",
    "slot_value_normalized_f1",
    "executable_contract_pass_rate",
]

GUARDRAIL_METRICS = [
    "schema_validity",
    "route_accuracy",
    "task_type_accuracy",
    "safety_recall",
    "unsafe_false_negative_rate",
    "requires_confirmation_accuracy",
    "json_valid_rate",
]


def _metric_bundle(rows: list[SFTDatasetRow], predictions: dict[str, Any]) -> dict[str, Any]:
    strict = evaluate_predictions(rows, predictions)
    layered = evaluate_layered_predictions(rows, predictions)
    strict_metrics = strict.metrics
    layered_metrics = layered["metrics"]
    metrics = {
        "contract_exact_match_strict": layered_metrics["contract_exact_match_strict"],
        "slot_value_exact_f1": layered_metrics["slot_value_exact_f1"],
        "slot_value_normalized_f1": layered_metrics["slot_value_normalized_f1"],
        "executable_contract_pass_rate": layered_metrics["executable_contract_pass_rate"],
        "schema_validity": layered_metrics["schema_validity"],
        "route_accuracy": layered_metrics["route_accuracy"],
        "task_type_accuracy": layered_metrics["task_type_accuracy"],
        "safety_recall": strict_metrics.get("safety_recall"),
        "unsafe_false_negative_rate": layered_metrics["unsafe_false_negative_rate"],
        "requires_confirmation_accuracy": layered_metrics["requires_confirmation_accuracy"],
        "json_valid_rate": strict_metrics.get("json_valid_rate"),
    }
    return {"metrics": metrics, "strict_metrics": strict_metrics, "layered": layered}


def _row_status(row: SFTDatasetRow, prediction: Any) -> dict[str, Any]:
    gold = as_contract(row.target_contract)
    predicted = _prediction_to_contract(prediction)
    schema_valid = predicted is not None
    exact = schema_valid and predicted.to_dict() == gold.to_dict()
    slot_exact = schema_valid and predicted.slots == gold.slots
    executable = schema_valid and _executable_contract_pass(gold, predicted)
    unsafe_fn = schema_valid and _is_unsafe_false_negative(gold, predicted)
    safety_correct = schema_valid and predicted.safety.get("allow") == gold.safety.get("allow")
    confirmation_correct = schema_valid and predicted.confirmation_required == gold.confirmation_required
    family = (
        f"{gold.task_type}|{gold.route}|"
        f"confirm:{str(gold.confirmation_required).lower()}|"
        f"allow:{str(bool(gold.safety.get('allow'))).lower()}"
    )
    return {
        "schema_valid": bool(schema_valid),
        "exact": bool(exact),
        "slot_exact": bool(slot_exact),
        "executable": bool(executable),
        "unsafe_false_negative": bool(unsafe_fn),
        "safety_correct": bool(safety_correct),
        "confirmation_correct": bool(confirmation_correct),
        "family": family,
    }


def _rate(values: list[bool]) -> float:
    return sum(1 for value in values if value) / len(values) if values else 0.0


def _copy_prediction_artifacts(source: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for name in [
        "predictions.jsonl",
        "prediction_metadata.json",
        "prompt_snapshot.json",
        "raw_decoded_summary.jsonl",
        "generation_trace.jsonl",
    ]:
        source_path = source / name
        if source_path.exists():
            shutil.copy2(source_path, destination / name)


SCHEMA_RETRY_BOUNDARY = "generation_time_invalid_json_retry_only_no_posthoc_prediction_repair"


def _write_metrics_markdown(path: Path, *, arm: str, split: str, payload: dict[str, Any]) -> None:
    lines = [
        f"# {arm.title()} {split} canonical slot paired SFT metrics",
        "",
        f"- Training manifest: `{payload['training_manifest_id']}`",
        f"- Evaluation manifest: `{payload['evaluation_manifest_id']}`",
        f"- Gold rows: `{payload['gold_count']}`",
        f"- Predictions: `{payload['prediction_count']}`",
        f"- Schema retry boundary: `{SCHEMA_RETRY_BOUNDARY}`",
        "",
        "| metric | value |",
        "| --- | ---: |",
    ]
    for key in PRIMARY_METRICS + GUARDRAIL_METRICS:
        value = payload["metrics"][key]
        lines.append(f"| `{key}` | {value:.6f} |")
    lines.extend(
        [
            "",
            (
                "No DPO/GRPO, LLM judge, post-hoc prediction repair, "
                "semantic-equivalence scoring, adapter release, or checkpoint "
                "release was performed."
            ),
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _training_summary(*, arm: str, config: dict[str, Any], evaluation_manifest_id: str) -> dict[str, Any]:
    return {
        "phase": "run-canonical-slot-paired-sft-ablation",
        "arm": arm,
        "training_status": "training_completed",
        "training_manifest_id": config["dataset_manifest_id"],
        "evaluation_manifest_id": evaluation_manifest_id,
        "training_split": config["dataset_split"],
        "selected_train_sft_rows": config["expected_train_sft_rows"],
        "expected_train_sft_rows": config["expected_train_sft_rows"],
        "base_model_public_id": config["base_model"],
        "lora": config["lora"],
        "learning_rate": config["learning_rate"],
        "num_train_epochs": config["num_train_epochs"],
        "max_steps": config["max_steps"],
        "per_device_train_batch_size": config["per_device_train_batch_size"],
        "gradient_accumulation_steps": config["gradient_accumulation_steps"],
        "seed": config["seed"],
        "max_seq_length": config["max_seq_length"],
        "trainer": config["trainer"],
        "save_strategy": config["save_strategy"],
        "dpo_or_grpo_run_performed": False,
        "adapter_release_status": "not_released",
        "checkpoint_release_status": "not_released",
        "raw_private_paths_copied_to_git": False,
        "sanitized_for_public_evidence": True,
        "provenance_source": "sanitized_training_config_and_observed_a100_completion",
        "observed_training_status_basis": (
            "A100 SFT command completed before prediction generation; "
            "raw adapter metadata, logs, private paths, and caches remain uncommitted."
        ),
        "training_artifact_policy": "adapters_checkpoints_raw_logs_caches_and_private_runtime_paths_not_committed",
    }


def _write_training_summaries(
    *,
    public_root: Path,
    evaluation_manifest_id: str,
    control_config: Path,
    treatment_config: Path,
) -> dict[str, dict[str, Any]]:
    configs = {
        "control": read_json(control_config),
        "treatment": read_json(treatment_config),
    }
    summaries: dict[str, dict[str, Any]] = {}
    for arm, config in configs.items():
        summary = _training_summary(arm=arm, config=config, evaluation_manifest_id=evaluation_manifest_id)
        write_json(public_root / arm / "training_summary.json", summary)
        summaries[arm] = summary
    return summaries


def _evaluate_arms(
    *,
    remote_evidence: Path,
    public_root: Path,
    manifest_path: Path,
    sft_path: Path,
    training_manifest_ids: dict[str, str],
) -> dict[str, Any]:
    manifest = read_json(manifest_path)
    rows_all = load_sft_rows(sft_path)
    for split in ["dev", "test"]:
        rows = [row for row in rows_all if row.split == split]
        write_jsonl(public_root / f"{split}_gold.jsonl", [row.to_dict() for row in rows])

    all_results: dict[str, Any] = {}
    for arm in ["control", "treatment"]:
        all_results[arm] = {}
        for split in ["dev", "test"]:
            rows = [row for row in rows_all if row.split == split]
            source = remote_evidence / arm / split
            destination = public_root / arm / split
            _copy_prediction_artifacts(source, destination)
            predictions = load_predictions(source / "predictions.jsonl")
            bundle = _metric_bundle(rows, predictions)
            statuses = {row.id: _row_status(row, predictions.get(row.id)) for row in rows}
            payload = {
                "phase": "run-canonical-slot-paired-sft-ablation",
                "arm": arm,
                "split": split,
                "dataset_manifest_id": manifest["manifest_id"],
                "training_manifest_id": training_manifest_ids[arm],
                "evaluation_manifest_id": manifest["manifest_id"],
                "training_summary_path": f"{arm}/training_summary.json",
                "prediction_count": len(predictions),
                "gold_count": len(rows),
                "schema_retry_boundary": SCHEMA_RETRY_BOUNDARY,
                **bundle,
                "row_status": statuses,
                "claims": {
                    "fresh_adapter_training_performed": True,
                    "dpo_or_grpo_run_performed": False,
                    "llm_judge_used": False,
                    "prediction_repair_performed": False,
                    "semantic_equivalence_scoring_used": False,
                    "adapter_released": False,
                    "checkpoint_released": False,
                },
            }
            write_json(destination / "metrics.json", payload)
            _write_metrics_markdown(
                destination / "metrics.md",
                arm=arm,
                split=split,
                payload=payload,
            )
            all_results[arm][split] = payload
    return {"manifest": manifest, "rows_all": rows_all, "all_results": all_results}


def _split_comparison(
    split: str,
    rows: list[SFTDatasetRow],
    control: dict[str, Any],
    treatment: dict[str, Any],
) -> dict[str, Any]:
    deltas = {
        key: treatment["metrics"][key] - control["metrics"][key]
        for key in PRIMARY_METRICS + GUARDRAIL_METRICS
    }
    exact_recoveries: list[dict[str, str]] = []
    exact_regressions: list[dict[str, str]] = []
    slot_recoveries: list[dict[str, str]] = []
    slot_regressions: list[dict[str, str]] = []
    safety_regressions: list[dict[str, str]] = []
    confirmation_regressions: list[dict[str, str]] = []
    families: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "count": 0,
            "control_exact": [],
            "treatment_exact": [],
            "control_executable": [],
            "treatment_executable": [],
            "control_slot": [],
            "treatment_slot": [],
        }
    )
    for row in rows:
        control_status = control["row_status"][row.id]
        treatment_status = treatment["row_status"][row.id]
        record = {"id": row.id, "family": control_status["family"]}
        if not control_status["exact"] and treatment_status["exact"]:
            exact_recoveries.append(record)
        if control_status["exact"] and not treatment_status["exact"]:
            exact_regressions.append(record)
        if not control_status["slot_exact"] and treatment_status["slot_exact"]:
            slot_recoveries.append(record)
        if control_status["slot_exact"] and not treatment_status["slot_exact"]:
            slot_regressions.append(record)
        if control_status["safety_correct"] and not treatment_status["safety_correct"]:
            safety_regressions.append(record)
        if control_status["confirmation_correct"] and not treatment_status["confirmation_correct"]:
            confirmation_regressions.append(record)
        bucket = families[control_status["family"]]
        bucket["count"] += 1
        bucket["control_exact"].append(control_status["exact"])
        bucket["treatment_exact"].append(treatment_status["exact"])
        bucket["control_executable"].append(control_status["executable"])
        bucket["treatment_executable"].append(treatment_status["executable"])
        bucket["control_slot"].append(control_status["slot_exact"])
        bucket["treatment_slot"].append(treatment_status["slot_exact"])

    family_deltas = []
    for family, bucket in families.items():
        family_deltas.append(
            {
                "family": family,
                "count": bucket["count"],
                "exact_delta": _rate(bucket["treatment_exact"]) - _rate(bucket["control_exact"]),
                "executable_delta": _rate(bucket["treatment_executable"]) - _rate(bucket["control_executable"]),
                "slot_exact_delta": _rate(bucket["treatment_slot"]) - _rate(bucket["control_slot"]),
            }
        )
    family_deltas.sort(
        key=lambda item: (
            abs(item["executable_delta"]) + abs(item["exact_delta"]) + abs(item["slot_exact_delta"]),
            item["count"],
        ),
        reverse=True,
    )
    return {
        "control_metrics": control["metrics"],
        "treatment_metrics": treatment["metrics"],
        "absolute_delta_treatment_minus_control": deltas,
        "top_family_level_deltas": family_deltas[:12],
        "exact_recoveries": {"count": len(exact_recoveries), "examples": exact_recoveries[:50]},
        "exact_regressions": {"count": len(exact_regressions), "examples": exact_regressions[:50]},
        "slot_recoveries": {"count": len(slot_recoveries), "examples": slot_recoveries[:50]},
        "slot_regressions": {"count": len(slot_regressions), "examples": slot_regressions[:50]},
        "safety_regressions": {"count": len(safety_regressions), "examples": safety_regressions[:50]},
        "confirmation_regressions": {
            "count": len(confirmation_regressions),
            "examples": confirmation_regressions[:50],
        },
    }


def _write_comparison_markdown(path: Path, comparison: dict[str, Any]) -> None:
    lines = [
        "# Canonical slot paired SFT ablation comparison",
        "",
        f"- Status: `{comparison['status']}`",
        f"- Evaluation manifest for frozen dev/test: `{comparison['evaluation_manifest_id']}`",
        f"- Control training manifest: `{comparison['training_manifests']['control']}`",
        f"- Treatment training manifest: `{comparison['training_manifests']['treatment']}`",
        f"- Pilot gate passed: `{comparison['pilot_gate']['passed']}`",
        f"- Recommended next step: `{comparison['recommended_next_step']}`",
        (
            "- Scope: one fixed seed SFT A/B; no DPO/GRPO, evaluator change, "
            "LLM judge, post-hoc prediction repair, or semantic-equivalence scoring."
        ),
        f"- Schema retry boundary: `{comparison['claims']['schema_retry_boundary']}`",
        "",
    ]
    for split in ["dev", "test"]:
        lines.extend(
            [
                f"## {split}",
                "",
                "| metric | control | treatment | delta |",
                "| --- | ---: | ---: | ---: |",
            ]
        )
        split_payload = comparison["splits"][split]
        for key in PRIMARY_METRICS + GUARDRAIL_METRICS:
            control_value = split_payload["control_metrics"][key]
            treatment_value = split_payload["treatment_metrics"][key]
            delta = split_payload["absolute_delta_treatment_minus_control"][key]
            lines.append(f"| `{key}` | {control_value:.6f} | {treatment_value:.6f} | {delta:+.6f} |")
        lines.append("")
        for label, key in [
            ("Exact recoveries", "exact_recoveries"),
            ("Exact regressions", "exact_regressions"),
            ("Slot recoveries", "slot_recoveries"),
            ("Slot regressions", "slot_regressions"),
            ("Safety regressions", "safety_regressions"),
            ("Confirmation regressions", "confirmation_regressions"),
        ]:
            item = split_payload[key]
            ids = ", ".join(example["id"] for example in item["examples"][:12]) or "none"
            lines.append(f"- {label}: `{item['count']}`; examples: {ids}")
        lines.extend(
            [
                "",
                "Top family-level deltas:",
                "",
                "| family | count | exact delta | executable delta | slot exact delta |",
                "| --- | ---: | ---: | ---: | ---: |",
            ]
        )
        for item in split_payload["top_family_level_deltas"][:8]:
            lines.append(
                f"| `{item['family']}` | {item['count']} | {item['exact_delta']:+.6f} | "
                f"{item['executable_delta']:+.6f} | {item['slot_exact_delta']:+.6f} |"
            )
        lines.append("")
    lines.extend(["## Pilot gate", ""])
    for key, value in comparison["pilot_gate"]["checks"].items():
        lines.append(f"- `{key}`: `{value}`")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(args: argparse.Namespace) -> None:
    public_root = args.remote_evidence / "public-artifacts"
    public_root.mkdir(parents=True, exist_ok=True)
    evaluation_manifest = read_json(args.manifest)
    training_summaries = _write_training_summaries(
        public_root=public_root,
        evaluation_manifest_id=evaluation_manifest["manifest_id"],
        control_config=args.control_config,
        treatment_config=args.treatment_config,
    )
    evaluated = _evaluate_arms(
        remote_evidence=args.remote_evidence,
        public_root=public_root,
        manifest_path=args.manifest,
        sft_path=args.sft,
        training_manifest_ids={
            "control": training_summaries["control"]["training_manifest_id"],
            "treatment": training_summaries["treatment"]["training_manifest_id"],
        },
    )
    manifest = evaluated["manifest"]
    rows_all = evaluated["rows_all"]
    all_results = evaluated["all_results"]
    comparison = {
        "phase": "run-canonical-slot-paired-sft-ablation",
        "status": "observed",
        "dataset_manifest_id": manifest["manifest_id"],
        "evaluation_manifest_id": manifest["manifest_id"],
        "training_manifests": {
            "control": training_summaries["control"]["training_manifest_id"],
            "treatment": training_summaries["treatment"]["training_manifest_id"],
        },
        "training_summaries": {
            "control": "control/training_summary.json",
            "treatment": "treatment/training_summary.json",
        },
        "primary_metrics": PRIMARY_METRICS,
        "guardrail_metrics": GUARDRAIL_METRICS,
        "splits": {},
        "pilot_gate": {},
        "recommended_next_step": None,
        "claims": {
            "paired_fresh_control": True,
            "old_adapter_used_as_control": False,
            "sft_only": True,
            "dpo_or_grpo_run_performed": False,
            "evaluator_changed": False,
            "llm_judge_used": False,
            "prediction_repair_performed": False,
            "schema_retry_boundary": SCHEMA_RETRY_BOUNDARY,
            "semantic_equivalence_scoring_used": False,
            "adapter_or_checkpoint_release": False,
            "production_readiness_claim": False,
        },
    }
    for split in ["dev", "test"]:
        split_rows = [row for row in rows_all if row.split == split]
        comparison["splits"][split] = _split_comparison(
            split,
            split_rows,
            all_results["control"][split],
            all_results["treatment"][split],
        )

    checks = {
        "dev_slot_value_exact_f1_delta_at_least_0_03": comparison["splits"]["dev"][
            "absolute_delta_treatment_minus_control"
        ]["slot_value_exact_f1"]
        >= 0.03,
        "test_slot_value_exact_f1_delta_at_least_0_03": comparison["splits"]["test"][
            "absolute_delta_treatment_minus_control"
        ]["slot_value_exact_f1"]
        >= 0.03,
        "dev_executable_contract_pass_rate_delta_at_least_0_02": comparison["splits"]["dev"][
            "absolute_delta_treatment_minus_control"
        ]["executable_contract_pass_rate"]
        >= 0.02,
        "test_executable_contract_pass_rate_delta_at_least_0_02": comparison["splits"]["test"][
            "absolute_delta_treatment_minus_control"
        ]["executable_contract_pass_rate"]
        >= 0.02,
        "dev_safety_recall_not_decreased": comparison["splits"]["dev"]["absolute_delta_treatment_minus_control"][
            "safety_recall"
        ]
        >= 0,
        "test_safety_recall_not_decreased": comparison["splits"]["test"]["absolute_delta_treatment_minus_control"][
            "safety_recall"
        ]
        >= 0,
        "dev_unsafe_false_negative_not_increased": comparison["splits"]["dev"][
            "absolute_delta_treatment_minus_control"
        ]["unsafe_false_negative_rate"]
        <= 0,
        "test_unsafe_false_negative_not_increased": comparison["splits"]["test"][
            "absolute_delta_treatment_minus_control"
        ]["unsafe_false_negative_rate"]
        <= 0,
        "dev_confirmation_accuracy_drop_at_most_0_01": comparison["splits"]["dev"][
            "absolute_delta_treatment_minus_control"
        ]["requires_confirmation_accuracy"]
        >= -0.01,
        "test_confirmation_accuracy_drop_at_most_0_01": comparison["splits"]["test"][
            "absolute_delta_treatment_minus_control"
        ]["requires_confirmation_accuracy"]
        >= -0.01,
    }
    passed = all(checks.values())
    comparison["pilot_gate"] = {
        "fixed_seed": 7170,
        "passed": passed,
        "checks": checks,
        "policy": "recommend_3_seed_confirmation_only_if_all_checks_pass",
    }
    comparison["recommended_next_step"] = "run_3_seed_confirmation" if passed else "design-and-implement-contract-v2"
    write_json(public_root / "comparison.json", comparison)
    _write_comparison_markdown(public_root / "comparison.md", comparison)
    print(json.dumps({"ok": True, "public_root": public_root.as_posix(), "gate_passed": passed}, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--remote-evidence", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--sft", type=Path, required=True)
    parser.add_argument(
        "--control-config",
        type=Path,
        default=Path("configs/sft-a100-canonical-slot-paired-control.json"),
    )
    parser.add_argument(
        "--treatment-config",
        type=Path,
        default=Path("configs/sft-a100-canonical-slot-paired-treatment.json"),
    )
    run(parser.parse_args())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
