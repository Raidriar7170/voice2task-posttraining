from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from voice2task.io import read_json, write_json

SPLITS = ("dev", "test")

FAMILY_SPECS: tuple[dict[str, Any], ...] = (
    {"family": "slot_key_mismatch", "source": ("slot_key",), "strategy": "SCHEMA_CANONICALIZATION"},
    {"family": "slot_value_mismatch", "source": ("slot_value",), "strategy": "SCHEMA_CANONICALIZATION"},
    {"family": "missing_slot", "source": ("missing_slot",), "strategy": "DATA_REMEDIATION"},
    {"family": "extra_slot", "source": ("extra_slot",), "strategy": "DATA_REMEDIATION"},
    {
        "family": "normalized_command_mismatch",
        "source": ("normalized_command",),
        "strategy": "SCHEMA_CANONICALIZATION",
    },
    {
        "family": "success_criteria_mismatch",
        "source": ("success_criteria",),
        "strategy": "DETERMINISTIC_POSTPROCESSOR",
    },
    {
        "family": "allowed_actions_mismatch",
        "source": ("allowed_actions",),
        "strategy": "DETERMINISTIC_POSTPROCESSOR",
    },
    {"family": "route_mismatch", "source": ("route",), "strategy": "DEFER"},
    {"family": "task_type_mismatch", "source": ("task_type",), "strategy": "DEFER"},
    {"family": "risk_level_mismatch", "source": ("risk_level",), "strategy": "SAFETY_REPAIR"},
    {
        "family": "requires_confirmation_mismatch",
        "source": ("confirmation",),
        "strategy": "SAFETY_REPAIR",
    },
    {
        "family": "refusal_or_clarify_mismatch",
        "source": ("refusal_or_clarify",),
        "strategy": "SAFETY_REPAIR",
    },
    {"family": "unsafe_false_negative", "source": ("unsafe_false_negative",), "strategy": "SAFETY_REPAIR"},
    {"family": "extra_field", "source": ("extra_field",), "strategy": "DEFER"},
    {"family": "missing_field", "source": ("missing_field",), "strategy": "DEFER"},
    {
        "family": "invalid_or_unparseable_output",
        "source": ("invalid_output", "invalid_or_unparseable_output"),
        "strategy": "DEFER",
    },
)

METRIC_FIELDS = (
    ("sample_count", ("summary", "total")),
    ("strict_exact", ("metrics", "contract_exact_match_strict")),
    ("executable_contract_pass_rate", ("metrics", "executable_contract_pass_rate")),
    ("slot_key_f1", ("metrics", "slot_key_f1")),
    ("slot_value_exact_f1", ("metrics", "slot_value_exact_f1")),
    ("slot_value_normalized_f1", ("metrics", "slot_value_normalized_f1")),
    ("route_accuracy", ("metrics", "route_accuracy")),
    ("task_type_accuracy", ("metrics", "task_type_accuracy")),
    ("risk_level_accuracy", ("metrics", "risk_level_accuracy")),
    ("requires_confirmation_accuracy", ("metrics", "requires_confirmation_accuracy")),
    ("unsafe_false_negative_rate", ("metrics", "unsafe_false_negative_rate")),
    ("refusal_or_clarify_accuracy", ("metrics", "refusal_or_clarify_accuracy")),
)

FORBIDDEN_SCOPE = {
    "training_run": False,
    "prediction_run": False,
    "data_mutation": False,
    "data_expansion": False,
    "candidate_merge": False,
    "split_change": False,
    "dpo_expansion": False,
    "lora_or_base_model_change": False,
    "evaluator_metric_change": False,
    "evaluator_relaxation": False,
    "llm_judge": False,
    "semantic_equivalence_scoring": False,
    "prediction_repair": False,
    "checkpoint_or_adapter_release": False,
}

CLAIM_BOUNDARIES = {
    "model_improvement_claim": False,
    "held_out_recovery_claim": False,
    "production_readiness_claim": False,
    "safety_readiness_claim": False,
    "live_browser_benchmark_improvement_claim": False,
    "normalized_slot_metrics_diagnostic_only": True,
    "strict_exact_canonical_diagnostic": True,
    "executable_contract_pass_deterministic_layered_metric": True,
}


@dataclass(frozen=True)
class RemediationTargetInputs:
    manifest_id: str
    layered_by_split: dict[str, dict[str, Any]]
    residual_by_split: dict[str, dict[str, Any]]
    artifact_paths: dict[str, str]


def _resolve_artifact(base_dir: Path, candidates: tuple[str, ...]) -> Path:
    for candidate in candidates:
        path = base_dir / candidate
        if path.exists():
            return path
    joined = ", ".join(candidates)
    raise FileNotFoundError(f"none of the expected artifacts exists under {base_dir}: {joined}")


def _public_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return "/".join(path.parts[-3:])


def load_remediation_target_inputs(
    *,
    layered_eval_dir: Path,
    residual_diagnosis_dir: Path,
) -> RemediationTargetInputs:
    layered_by_split: dict[str, dict[str, Any]] = {}
    residual_by_split: dict[str, dict[str, Any]] = {}
    artifact_paths: dict[str, str] = {}
    manifest_ids: set[str] = set()

    for split in SPLITS:
        layered_path = _resolve_artifact(layered_eval_dir, (f"{split}.json", f"{split}/metrics.json"))
        residual_path = _resolve_artifact(
            residual_diagnosis_dir,
            (f"{split}.json", f"{split}/residual_diagnosis.json"),
        )
        layered = read_json(layered_path)
        residual = read_json(residual_path)
        layered_by_split[split] = layered
        residual_by_split[split] = residual
        artifact_paths[f"layered_{split}"] = _public_path(layered_path)
        artifact_paths[f"residual_{split}"] = _public_path(residual_path)
        for payload in (layered, residual):
            manifest_id = payload.get("manifest_id")
            if isinstance(manifest_id, str) and manifest_id:
                manifest_ids.add(manifest_id)

    if len(manifest_ids) != 1:
        raise ValueError(f"expected one manifest id across inputs, found {sorted(manifest_ids)!r}")
    return RemediationTargetInputs(
        manifest_id=next(iter(manifest_ids)),
        layered_by_split=layered_by_split,
        residual_by_split=residual_by_split,
        artifact_paths=artifact_paths,
    )


def _nested_value(payload: dict[str, Any], path: tuple[str, str]) -> float | int:
    parent = payload.get(path[0])
    if not isinstance(parent, dict):
        return 0
    value = parent.get(path[1], 0)
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int | float):
        return value
    return 0


def _metrics_by_split(inputs: RemediationTargetInputs) -> dict[str, dict[str, float | int]]:
    return {
        split: {field: _nested_value(payload, path) for field, path in METRIC_FIELDS}
        for split, payload in inputs.layered_by_split.items()
    }


def _family_counts_by_source(residual_payload: dict[str, Any]) -> dict[str, int]:
    summary = residual_payload.get("summary")
    family_counts = summary.get("family_counts") if isinstance(summary, dict) else None
    if isinstance(family_counts, dict):
        return {str(key): int(value) for key, value in family_counts.items() if isinstance(value, int | float)}
    families = residual_payload.get("families")
    if not isinstance(families, dict):
        return {}
    counts: dict[str, int] = {}
    for name, entry in families.items():
        if isinstance(entry, dict) and isinstance(entry.get("count"), int | float):
            counts[str(name)] = int(entry["count"])
    return counts


def _residuals_for_sources(residual_payload: dict[str, Any], sources: tuple[str, ...]) -> list[dict[str, Any]]:
    residuals = residual_payload.get("residuals")
    if isinstance(residuals, list):
        return [
            item
            for item in residuals
            if isinstance(item, dict) and isinstance(item.get("family"), str) and item["family"] in sources
        ]
    families = residual_payload.get("families")
    if not isinstance(families, dict):
        return []
    examples: list[dict[str, Any]] = []
    for source in sources:
        entry = families.get(source)
        if isinstance(entry, dict) and isinstance(entry.get("examples"), list):
            examples.extend(item for item in entry["examples"] if isinstance(item, dict))
    return examples


def _infer_hint(row_id: str) -> tuple[str, str, str]:
    lowered = row_id.lower().replace("-", "_")
    if "blocked_payment" in lowered or "blocked" in lowered:
        return ("blocked_payment", "blocked", "deny")
    if "clarify" in lowered:
        return ("clarify", "clarify", "clarify")
    if "form_fill" in lowered or "form" in lowered:
        return ("form_fill", "form_fill", "fill_form")
    if "search" in lowered:
        return ("search", "search", "search_web")
    if "extract" in lowered:
        return ("extract", "extract", "extract_info")
    if "navigate" in lowered or "open" in lowered:
        return ("navigation", "navigate", "open_url")
    return ("unknown", "unknown", "unknown")


def _top_hint(residuals: list[dict[str, Any]], index: int) -> str:
    counter: Counter[str] = Counter()
    for residual in residuals:
        row_id = residual.get("row_id")
        if isinstance(row_id, str):
            counter[_infer_hint(row_id)[index]] += 1
    if not counter:
        return "unknown"
    return counter.most_common(1)[0][0]


def _example_from_residual(residual: dict[str, Any], family: str) -> dict[str, str]:
    return {
        "split": str(residual.get("split", "unknown")),
        "row_id": str(residual.get("row_id", "unknown")),
        "family": family,
        "field_path": str(residual.get("field_path", "unknown")),
        "gold_value_summary": str(residual.get("gold_value_summary", "unavailable")),
        "prediction_value_summary": str(residual.get("prediction_value_summary", "unavailable")),
    }


def _unsafe_false_negative_count(inputs: RemediationTargetInputs, split: str) -> int:
    summary = inputs.layered_by_split.get(split, {}).get("summary")
    if not isinstance(summary, dict):
        return 0
    value = summary.get("unsafe_false_negative_count", 0)
    return int(value) if isinstance(value, int | float) else 0


def _unsafe_false_negative_examples(inputs: RemediationTargetInputs) -> list[dict[str, str]]:
    examples: list[dict[str, str]] = []
    for split in SPLITS:
        count = _unsafe_false_negative_count(inputs, split)
        if count:
            examples.append(
                {
                    "split": split,
                    "row_id": f"layered-eval-{split}-unsafe-false-negative",
                    "family": "unsafe_false_negative",
                    "field_path": "safety.allow",
                    "gold_value_summary": f"unsafe examples requiring denial or confirmation: {count}",
                    "prediction_value_summary": "model output did not preserve the unsafe boundary",
                }
            )
    return examples[:3]


def _failure_families(inputs: RemediationTargetInputs) -> list[dict[str, Any]]:
    split_counts_by_source = {
        split: _family_counts_by_source(payload) for split, payload in inputs.residual_by_split.items()
    }
    total_counts: dict[str, int] = {}
    split_counts: dict[str, dict[str, int]] = {}

    for spec in FAMILY_SPECS:
        family = spec["family"]
        sources = tuple(spec["source"])
        by_split: dict[str, int] = {}
        for split in SPLITS:
            if family == "unsafe_false_negative":
                count = _unsafe_false_negative_count(inputs, split)
            else:
                source_counts = split_counts_by_source.get(split, {})
                count = sum(int(source_counts.get(source, 0)) for source in sources)
            by_split[split] = count
        split_counts[family] = by_split
        total_counts[family] = sum(by_split.values())

    total_residual_count = sum(total_counts.values())
    families: list[dict[str, Any]] = []
    for spec in FAMILY_SPECS:
        family = spec["family"]
        sources = tuple(spec["source"])
        residuals: list[dict[str, Any]] = []
        if family == "unsafe_false_negative":
            examples = _unsafe_false_negative_examples(inputs)
        else:
            for split in SPLITS:
                residuals.extend(_residuals_for_sources(inputs.residual_by_split[split], sources))
            examples = [_example_from_residual(item, family) for item in residuals[:3]]
        count = total_counts[family]
        families.append(
            {
                "family": family,
                "source_families": list(sources),
                "count": count,
                "proportion_of_all_residuals": (count / total_residual_count) if total_residual_count else 0.0,
                "dev_count": split_counts[family].get("dev", 0),
                "test_count": split_counts[family].get("test", 0),
                "top_affected_family": _top_hint(residuals, 0) if residuals else "safety" if count else "unknown",
                "top_affected_task_type": _top_hint(residuals, 1) if residuals else "blocked" if count else "unknown",
                "top_affected_route": _top_hint(residuals, 2) if residuals else "deny" if count else "unknown",
                "top_affected_hint_source": (
                    "row_id_inference" if residuals else "layered_eval_summary" if count else "none"
                ),
                "strategy": spec["strategy"],
                "examples": examples,
            }
        )
    return sorted(families, key=lambda item: (-int(item["count"]), str(item["family"])))


def _family_by_name(families: list[dict[str, Any]], family: str) -> dict[str, Any]:
    for item in families:
        if item["family"] == family:
            return item
    return {"count": 0}


def _claim_boundaries() -> list[str]:
    return [
        "Do not claim held-out recovery.",
        "Do not claim model improvement.",
        "Do not claim production readiness.",
        "Do not claim safety readiness.",
        "Do not claim live-browser benchmark improvement.",
        "Do not treat normalized slot metrics as recovery evidence.",
    ]


def _selected_targets(families: list[dict[str, Any]]) -> list[dict[str, Any]]:
    targets: list[dict[str, Any]] = []
    unsafe = _family_by_name(families, "unsafe_false_negative")
    if int(unsafe.get("count", 0)) > 0:
        targets.append(
            {
                "target_id": "safety-repair-unsafe-false-negative",
                "target_family": "unsafe_false_negative",
                "strategy": "SAFETY_REPAIR",
                "evidence_count": unsafe["count"],
                "why_it_matters": (
                    "Unsafe false negatives can incorrectly downgrade blocked, payment, delete, send, upload, "
                    "login, or other high-risk instructions into executable contracts."
                ),
                "proposed_next_change_id": "design-safety-repair-candidates",
                "allowed_operations": [
                    "design public-safe safety repair candidates",
                    "define fail-closed safety policy examples",
                    "add deterministic safety-boundary tests",
                ],
                "non_goals": [
                    "no training",
                    "no prediction repair",
                    "no production safety claim",
                    "no evaluator relaxation",
                ],
                "expected_measurable_effect": (
                    "Future bounded phase should reduce unsafe false negatives and preserve or improve "
                    "requires-confirmation/risk-level accuracy without lowering strict exact."
                ),
                "what_not_to_claim": _claim_boundaries(),
            }
        )

    slot_related = [
        _family_by_name(families, "slot_key_mismatch"),
        _family_by_name(families, "slot_value_mismatch"),
        _family_by_name(families, "missing_slot"),
        _family_by_name(families, "extra_slot"),
    ]
    slot_count = sum(int(item.get("count", 0)) for item in slot_related)
    if slot_count and len(targets) < 2:
        slot_value = _family_by_name(families, "slot_value_mismatch")
        targets.append(
            {
                "target_id": "slot-value-canonicalization-policy",
                "target_family": "slot_related_mismatches",
                "strategy": "SCHEMA_CANONICALIZATION",
                "evidence_count": slot_count,
                "dominant_family_count": int(slot_value.get("count", 0)),
                "why_it_matters": (
                    "Slot value mismatches dominate residual fields while slot keys are comparatively stable, "
                    "so the next bounded phase should decide canonical wording and value-policy boundaries "
                    "before another training run."
                ),
                "proposed_next_change_id": "design-slot-canonicalization-policy",
                "allowed_operations": [
                    "design slot value canonicalization policy",
                    "classify alias/wording boundaries",
                    "define later public-safe candidate criteria",
                ],
                "non_goals": [
                    "no data materialization in this phase",
                    "no formal sample merge",
                    "no training",
                    "no evaluator relaxation",
                ],
                "expected_measurable_effect": (
                    "Future bounded phase should improve slot value exact/normalized diagnostics and "
                    "executable contract pass rate only after separate implementation/evaluation evidence."
                ),
                "what_not_to_claim": _claim_boundaries(),
            }
        )

    derived_count = int(_family_by_name(families, "allowed_actions_mismatch").get("count", 0)) + int(
        _family_by_name(families, "success_criteria_mismatch").get("count", 0)
    )
    if derived_count and len(targets) < 2:
        targets.append(
            {
                "target_id": "derived-field-contract-postprocessor",
                "target_family": "allowed_actions_or_success_criteria",
                "strategy": "DETERMINISTIC_POSTPROCESSOR",
                "evidence_count": derived_count,
                "why_it_matters": (
                    "Allowed actions and success criteria can often be derived from task type, route, and "
                    "risk policy instead of leaving the model to invent them."
                ),
                "proposed_next_change_id": "add-contract-postprocessor-for-derived-fields",
                "allowed_operations": ["design deterministic derived-field rules", "add postprocessor tests"],
                "non_goals": ["no evaluator relaxation", "no prediction repair", "no training"],
                "expected_measurable_effect": (
                    "Future bounded phase should improve executable contract pass rate for derived fields "
                    "without changing strict evaluator semantics."
                ),
                "what_not_to_claim": _claim_boundaries(),
            }
        )

    normalized = _family_by_name(families, "normalized_command_mismatch")
    if int(normalized.get("count", 0)) and not targets:
        targets.append(
            {
                "target_id": "normalized-command-diagnostic-boundary",
                "target_family": "normalized_command_mismatch",
                "strategy": "SCHEMA_CANONICALIZATION",
                "evidence_count": normalized["count"],
                "why_it_matters": (
                    "Normalized command mismatches are frequent but may not block execution, so the next phase "
                    "should decide whether to template or downgrade the field to diagnostic status."
                ),
                "proposed_next_change_id": "downgrade-normalized-command-to-diagnostic",
                "allowed_operations": ["design diagnostic boundary policy"],
                "non_goals": ["no evaluator relaxation", "no model-quality claim"],
                "expected_measurable_effect": "Future reports should make normalized-command impact explicit.",
                "what_not_to_claim": _claim_boundaries(),
            }
        )
    return targets[:2]


def _recommended_next_change(targets: list[dict[str, Any]]) -> dict[str, Any]:
    if not targets:
        return {
            "proposed_change_id": "defer-remediation-target-selection",
            "problem_statement": "No remediation target has enough public-safe evidence in current artifacts.",
            "scope": ["defer until more public-safe residual evidence exists"],
            "acceptance_criteria": ["Document why no target is selected."],
            "non_goals": ["no training", "no evaluator changes"],
            "expected_metrics_to_watch": [],
            "claim_boundaries": _claim_boundaries(),
        }
    first = targets[0]
    return {
        "proposed_change_id": first["proposed_next_change_id"],
        "problem_statement": first["why_it_matters"],
        "evidence_from_current_artifacts": {
            "target_family": first["target_family"],
            "evidence_count": first["evidence_count"],
            "strategy": first["strategy"],
            "primary_source": (
                "layered_eval_summary"
                if first["target_family"] == "unsafe_false_negative"
                else "residual_diagnosis"
            ),
            "supporting_sources": ["layered_eval", "residual_diagnosis"],
        },
        "scope": first["allowed_operations"],
        "acceptance_criteria": [
            "Preserve strict evaluator semantics and existing layered/residual artifacts.",
            "Keep all artifacts public-safe and leak-scan clean.",
            (
                "Measure the next bounded phase against strict exact, executable contract pass, "
                "slot metrics, and safety metrics as applicable."
            ),
        ],
        "non_goals": first["non_goals"],
        "expected_metrics_to_watch": [
            "contract_exact_match_strict",
            "executable_contract_pass_rate",
            "slot_value_exact_f1",
            "slot_value_normalized_f1",
            "unsafe_false_negative_rate",
            "requires_confirmation_accuracy",
            "risk_level_accuracy",
        ],
        "claim_boundaries": first["what_not_to_claim"],
    }


def select_residual_driven_remediation_targets(inputs: RemediationTargetInputs) -> dict[str, Any]:
    metrics_by_split = _metrics_by_split(inputs)
    families = _failure_families(inputs)
    targets = _selected_targets(families)
    top_five = [item["family"] for item in families[:5]]
    return {
        "evidence_kind": "residual_driven_remediation_target_selection",
        "manifest_id": inputs.manifest_id,
        "source_artifacts": inputs.artifact_paths,
        "summary": {
            "manifest_id": inputs.manifest_id,
            "top_failure_families": top_five,
            "selected_target_count": len(targets),
            "selected_targets": [target["target_id"] for target in targets],
            "recommended_next_change_id": targets[0]["proposed_next_change_id"] if targets else "defer",
            "strict_exact_is_canonical_diagnostic": True,
            "executable_contract_pass_is_deterministic_layered_metric": True,
            "normalized_slot_metrics_are_diagnostic_only": True,
            "current_stage_does_not_claim_model_improvement": True,
        },
        "metrics_by_split": metrics_by_split,
        "failure_families": families,
        "selected_targets": targets,
        "recommended_next_change": _recommended_next_change(targets),
        "execution_scope": dict(FORBIDDEN_SCOPE),
        "claims": dict(CLAIM_BOUNDARIES),
    }


def _format_rate(value: Any) -> str:
    if isinstance(value, int | float):
        return f"{value:.4f}"
    return str(value)


def _format_markdown_value(value: Any) -> str:
    if isinstance(value, list):
        return ", ".join(f"`{item}`" for item in value)
    return f"`{value}`"


def _summary_markdown(selection: dict[str, Any]) -> str:
    lines = [
        "# Residual-Driven Remediation Target Selection",
        "",
        (
            "This is analysis and target-selection evidence only: strict exact is the canonical "
            "diagnostic, executable contract pass is a deterministic layered metric, normalized slot "
            "metrics are diagnostic only, and the current stage does not claim model improvement."
        ),
        "",
        "## Current Evaluation State",
        "",
        (
            "| split | samples | strict exact | executable contract pass | slot key F1 | "
            "slot value exact F1 | slot value normalized F1 | route acc | task type acc | "
            "risk acc | confirmation acc | unsafe FN rate | refusal/clarify acc |"
        ),
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for split in SPLITS:
        metrics = selection["metrics_by_split"][split]
        lines.append(
            "| "
            + " | ".join(
                [
                    split,
                    str(metrics["sample_count"]),
                    _format_rate(metrics["strict_exact"]),
                    _format_rate(metrics["executable_contract_pass_rate"]),
                    _format_rate(metrics["slot_key_f1"]),
                    _format_rate(metrics["slot_value_exact_f1"]),
                    _format_rate(metrics["slot_value_normalized_f1"]),
                    _format_rate(metrics["route_accuracy"]),
                    _format_rate(metrics["task_type_accuracy"]),
                    _format_rate(metrics["risk_level_accuracy"]),
                    _format_rate(metrics["requires_confirmation_accuracy"]),
                    _format_rate(metrics["unsafe_false_negative_rate"]),
                    _format_rate(metrics["refusal_or_clarify_accuracy"]),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Selected Next Targets",
            "",
        ]
    )
    for target in selection["selected_targets"]:
        lines.extend(
            [
                f"### {target['target_id']}",
                "",
                f"- Strategy: `{target['strategy']}`",
                f"- Target family: `{target['target_family']}`",
                f"- Evidence count: `{target['evidence_count']}`",
                f"- Proposed next change: `{target['proposed_next_change_id']}`",
                f"- Why it matters: {target['why_it_matters']}",
                f"- Expected measurable effect: {target['expected_measurable_effect']}",
                "",
            ]
        )
    lines.extend(
        [
            "## Boundaries",
            "",
            (
                "- No training, prediction rerun, data expansion, candidate merge, split change, "
                "DPO expansion, LoRA/base-model change, evaluator relaxation, LLM judge, "
                "semantic scoring, or prediction repair was performed."
            ),
            (
                "- Do not claim held-out recovery, production readiness, safety readiness, "
                "released checkpoint/adapter, or live-browser benchmark improvement."
            ),
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def _top_failures_markdown(selection: dict[str, Any]) -> str:
    lines = [
        "# Top Residual Failure Families",
        "",
        (
            "| rank | family | count | residual proportion | dev | test | strategy | "
            "inferred task hint | inferred route hint | inferred source-family hint | hint source |"
        ),
        "| ---: | --- | ---: | ---: | ---: | ---: | --- | --- | --- | --- | --- |",
    ]
    for rank, family in enumerate(selection["failure_families"], start=1):
        lines.append(
            "| "
            + " | ".join(
                [
                    str(rank),
                    f"`{family['family']}`",
                    str(family["count"]),
                    _format_rate(family["proportion_of_all_residuals"]),
                    str(family["dev_count"]),
                    str(family["test_count"]),
                    f"`{family['strategy']}`",
                    f"`{family['top_affected_task_type']}`",
                    f"`{family['top_affected_route']}`",
                    f"`{family['top_affected_family']}`",
                    f"`{family['top_affected_hint_source']}`",
                ]
            )
            + " |"
        )
    lines.extend(["", "## Sanitized Examples", ""])
    for family in selection["failure_families"]:
        if not family["examples"]:
            continue
        lines.extend([f"### {family['family']}", ""])
        for example in family["examples"][:3]:
            lines.append(
                "- "
                f"`{example['row_id']}` ({example['split']}, `{example['field_path']}`): "
                f"gold {example['gold_value_summary']} -> prediction {example['prediction_value_summary']}"
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _recommended_next_change_markdown(selection: dict[str, Any]) -> str:
    recommendation = selection["recommended_next_change"]
    lines = [
        "# Recommended Next OpenSpec Change",
        "",
        f"- proposed change id: `{recommendation['proposed_change_id']}`",
        "",
        "## Problem Statement",
        "",
        str(recommendation["problem_statement"]),
        "",
        "## Evidence from Current Layered/Residual Artifacts",
        "",
    ]
    evidence = recommendation.get("evidence_from_current_artifacts", {})
    if isinstance(evidence, dict):
        for key, value in evidence.items():
            lines.append(f"- {key}: {_format_markdown_value(value)}")
    lines.extend(["", "## Scope", ""])
    for item in recommendation.get("scope", []):
        lines.append(f"- {item}")
    lines.extend(["", "## Acceptance Criteria", ""])
    for item in recommendation.get("acceptance_criteria", []):
        lines.append(f"- {item}")
    lines.extend(["", "## Non-goals", ""])
    for item in recommendation.get("non_goals", []):
        lines.append(f"- {item}")
    lines.extend(["", "## Expected Metrics to Watch", ""])
    for item in recommendation.get("expected_metrics_to_watch", []):
        lines.append(f"- `{item}`")
    lines.extend(["", "## Claim boundaries", ""])
    for item in recommendation.get("claim_boundaries", []):
        lines.append(f"- {item}")
    return "\n".join(lines).rstrip() + "\n"


def write_remediation_target_selection_reports(
    selection: dict[str, Any],
    output_dir: Path,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_json = output_dir / "summary.json"
    summary_md = output_dir / "summary.md"
    top_failures_md = output_dir / "top-failures.md"
    recommended_next_change_md = output_dir / "recommended-next-change.md"

    write_json(summary_json, selection)
    summary_md.write_text(_summary_markdown(selection), encoding="utf-8")
    top_failures_md.write_text(_top_failures_markdown(selection), encoding="utf-8")
    recommended_next_change_md.write_text(_recommended_next_change_markdown(selection), encoding="utf-8")
    return {
        "summary_json": summary_json,
        "summary_md": summary_md,
        "top_failures_md": top_failures_md,
        "recommended_next_change_md": recommended_next_change_md,
    }
