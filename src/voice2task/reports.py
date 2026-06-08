from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from voice2task.evaluation import EvaluationResult
from voice2task.io import write_json
from voice2task.schemas import PRIVATE_IP_RE, PRIVATE_PATH_RE, SECRET_RE

PRIVATE_REPORT_PATH_RE = re.compile(r"(/(?:mnt/data|Users|root|tmp|private)/[^\s\"')]+)")


def write_metrics_report(
    result: EvaluationResult,
    output_dir: Path,
    title: str = "Voice2Task contract metrics",
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "metrics.json"
    markdown_path = output_dir / "metrics.md"
    write_json(json_path, result.to_dict())
    lines = [
        f"# {title}",
        "",
        (
            "This report summarizes contract-level metrics only. "
            "No live-browser improvement claim is made from these numbers."
        ),
        "",
        "## Metrics",
        "",
    ]
    for name, value in sorted(result.metrics.items()):
        lines.append(f"- `{name}`: {value:.4f}")
    lines.extend(["", "## Failure Slices", ""])
    for name, entry in sorted(result.failure_slices.items()):
        examples = ", ".join(entry["examples"]) if entry["examples"] else "none"
        lines.append(f"- `{name}`: {entry['count']} examples ({examples})")
    markdown_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": json_path, "markdown": markdown_path}


def write_schema_diagnostics_report(
    diagnostics: dict[str, Any],
    output_dir: Path,
    title: str = "Voice2Task schema diagnostics",
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "schema_diagnostics.json"
    markdown_path = output_dir / "schema_diagnostics.md"
    write_json(json_path, diagnostics)

    summary = diagnostics["summary"]
    lines = [
        f"# {title}",
        "",
        (
            "This diagnostic is evidence-only: invalid predictions remain invalid. "
            "It does not repair, normalize, or convert private-adapter predictions into valid contracts."
        ),
        "",
        "## Boundary",
        "",
        "- This is not a checkpoint release.",
        "- This is not an adapter release.",
        "- This makes no production-readiness claim.",
        "- This makes no full-private-corpus claim.",
        "- This is not a live-browser benchmark or benchmark-improvement claim.",
        "",
        "## Summary",
        "",
        f"- Gold rows: `{summary['gold_row_count']}`",
        f"- Predictions: `{summary['prediction_count']}`",
        f"- Invalid predictions: `{summary['invalid_prediction_count']}`",
        "",
        "## Issue Counts",
        "",
    ]
    issue_counts = summary.get("issue_counts", {})
    if issue_counts:
        for category, count in sorted(issue_counts.items()):
            lines.append(f"- `{category}`: `{count}`")
    else:
        lines.append("- none")
    lines.extend(["", "## Row Issues", ""])
    for row in diagnostics.get("rows", []):
        lines.append(f"### `{row['row_id']}`")
        lines.append("")
        for issue in row["issues"]:
            lines.append(
                "- "
                f"`{issue['field_path']}` "
                f"({issue['issue_category']}): observed {issue['observed_value_summary']}; "
                f"expected {issue['expected_constraint']}"
            )
        lines.append("")

    markdown_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return {"json": json_path, "markdown": markdown_path}


def write_constrained_decoding_diagnosis_report(
    diagnostics: dict[str, Any],
    output_dir: Path,
    title: str = "Voice2Task constrained decoding diagnosis",
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "constrained_decoding_diagnosis.json"
    markdown_path = output_dir / "constrained_decoding_diagnosis.md"
    write_json(json_path, diagnostics)

    summary = diagnostics["summary"]
    examples = diagnostics.get("examples", {})
    claims = diagnostics.get("claims", {})
    if claims.get("local_decoder_output_shape_hardening_only", False):
        boundary_sentence = (
            "This diagnosis is local decoder/output-shape hardening evidence only: "
            "invalid predictions remain invalid, and the report does not repair, normalize, "
            "coerce, or replace model outputs."
        )
    elif claims.get("a100_prediction_rerun_evidence", False):
        boundary_sentence = (
            "This diagnosis is A100 prediction-rerun evidence with a strict non-repair boundary: "
            "model outputs are not repaired, normalized, coerced, replaced, re-scored, or relaxed."
        )
    else:
        boundary_sentence = (
            "This diagnosis is evidence-only: model outputs are not repaired, normalized, "
            "coerced, replaced, re-scored, or relaxed."
        )
    lines = [
        f"# {title}",
        "",
        boundary_sentence,
        "",
        "## Boundary",
        "",
        "- This is not a checkpoint release.",
        "- This is not an adapter release.",
        "- This is not a model recovery claim.",
        "- This is not held-out generalization evidence.",
        "- This makes no production-readiness claim.",
        "- This makes no full-private-corpus claim.",
        "- This is not a live-browser benchmark or benchmark-improvement claim.",
        "",
        "## Summary",
        "",
        f"- Predictions: `{summary['prediction_count']}`",
        f"- Decoded summary rows: `{summary['decoded_summary_row_count']}`",
        f"- Prediction schema-valid count: `{summary['prediction_schema_valid_count']}`",
        f"- Invalid predictions: `{summary['invalid_prediction_count']}`",
        f"- Raw attempt schema-valid count: `{summary['raw_attempt_schema_valid_count']}`",
        f"- Retry attempt schema-valid count: `{summary['retry_attempt_schema_valid_count']}`",
        f"- Validated output schema-valid count: `{summary['validated_output_schema_valid_count']}`",
        f"- Legacy task_type alias count: `{summary['legacy_task_type_alias_count']}`",
        f"- Path-like route count: `{summary['path_like_route_count']}`",
        f"- Prose/Markdown wrapper count: `{summary['prose_markdown_wrapper_count']}`",
        "",
        "## Parse Status Counts",
        "",
    ]
    for source_name, counts in sorted(summary.get("parse_status_counts", {}).items()):
        lines.append(f"### `{source_name}`")
        lines.append("")
        if counts:
            for parse_status, count in sorted(counts.items()):
                lines.append(f"- `{parse_status}`: `{count}`")
        else:
            lines.append("- none")
        lines.append("")

    lines.append("## Symptom Examples")
    lines.append("")
    for symptom_name in ("legacy_task_type_alias", "path_like_route", "prose_markdown_wrapper"):
        lines.append(f"### `{symptom_name}`")
        lines.append("")
        symptom_examples = examples.get(symptom_name, []) if isinstance(examples, dict) else []
        if symptom_examples:
            for example in symptom_examples:
                observed = (
                    example.get("task_type")
                    or example.get("route")
                    or example.get("parse_status")
                    or "observed"
                )
                lines.append(f"- `{example['row_id']}` `{example['source']}`: {observed}")
        else:
            lines.append("- none")
        lines.append("")

    markdown_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return {"json": json_path, "markdown": markdown_path}


def write_alignment_diagnostics_report(
    diagnostics: dict[str, Any],
    output_dir: Path,
    title: str = "Voice2Task alignment diagnostics",
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "alignment_diagnostics.json"
    markdown_path = output_dir / "alignment_diagnostics.md"
    write_json(json_path, diagnostics)

    summary = diagnostics["summary"]
    lines = [
        f"# {title}",
        "",
        (
            "This diagnostic is evidence-only: invalid predictions remain invalid. "
            "It reports field-level public-sample evidence only and does not repair, normalize, "
            "coerce, or replace prediction fields."
        ),
        "",
        "## Boundary",
        "",
        "- This is not a checkpoint release.",
        "- This is not an adapter release.",
        "- This makes no production-readiness claim.",
        "- This makes no full-private-corpus claim.",
        "- This is not a live-browser benchmark or benchmark-improvement claim.",
        "",
        "## Summary",
        "",
        f"- Gold rows: `{summary['gold_row_count']}`",
        f"- Predictions: `{summary['prediction_count']}`",
        f"- Rows with mismatches: `{summary['row_mismatch_count']}`",
        f"- Schema-invalid predictions: `{summary['schema_invalid_prediction_count']}`",
        "",
        "## Field Mismatch Counts",
        "",
    ]
    field_counts = summary.get("field_mismatch_counts", {})
    if field_counts:
        for field_path, count in sorted(field_counts.items()):
            lines.append(f"- `{field_path}`: `{count}`")
    else:
        lines.append("- none")
    lines.extend(["", "## Mismatch Category Counts", ""])
    category_counts = summary.get("mismatch_category_counts", {})
    if category_counts:
        for category, count in sorted(category_counts.items()):
            lines.append(f"- `{category}`: `{count}`")
    else:
        lines.append("- none")
    lines.extend(["", "## Row Mismatches", ""])
    for row in diagnostics.get("rows", []):
        lines.append(f"### `{row['row_id']}`")
        lines.append("")
        for mismatch in row["mismatches"]:
            lines.append(
                "- "
                f"`{mismatch['field_path']}` "
                f"({mismatch['mismatch_category']}): gold {mismatch['gold_value_summary']}; "
                f"prediction {mismatch['prediction_value_summary']}"
            )
        lines.append("")

    markdown_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return {"json": json_path, "markdown": markdown_path}


def write_confirmation_rerun_row_mismatch_report(
    diagnostics: dict[str, Any],
    output_dir: Path,
    title: str = "Confirmation-rerun row mismatch diagnosis",
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "row_mismatch_diagnosis.json"
    markdown_path = output_dir / "row_mismatch_diagnosis.md"
    write_json(json_path, diagnostics)

    summary = diagnostics["summary"]
    lines = [
        f"# {title}",
        "",
        (
            "This is a local evidence-only analysis derived from prior public-sample artifacts. "
            "It does not repair, normalize, coerce, replace, or re-score predictions."
        ),
        "",
        "## Boundary",
        "",
        "- No A100 execution was performed in this phase.",
        "- No training, prediction rerun, prompt change, decoding change, or evaluator metric change was performed.",
        "- This is not a checkpoint release.",
        "- This is not an adapter release.",
        "- This is not held-out generalization evidence.",
        "- This makes no production-readiness claim.",
        "- This makes no public full-corpus release claim.",
        "- This is not a live-browser benchmark improvement claim.",
        "- This is not model-quality improvement evidence.",
        "",
        "## Summary",
        "",
        f"- Gold rows: `{summary['gold_row_count']}`",
        f"- Predictions: `{summary['prediction_count']}`",
        f"- Rows with mismatches: `{summary['row_mismatch_count']}`",
        f"- Schema-invalid predictions: `{summary['schema_invalid_prediction_count']}`",
        f"- Strict final JSON-valid rate remains `{summary.get('strict_final_json_valid_rate')}`",
        f"- Strict final contract_exact_match remains `{summary.get('strict_final_contract_exact_match')}`",
        "",
        "## Failure Families",
        "",
    ]
    family_counts = summary.get("family_counts", {})
    if family_counts:
        for family, count in sorted(family_counts.items()):
            lines.append(f"- `{family}`: `{count}`")
    else:
        lines.append("- none")

    lines.extend(["", "## Field Mismatch Counts", ""])
    field_counts = summary.get("field_mismatch_counts", {})
    if field_counts:
        for field_path, count in sorted(field_counts.items()):
            lines.append(f"- `{field_path}`: `{count}`")
    else:
        lines.append("- none")

    lines.extend(["", "## Mismatch Category Counts", ""])
    category_counts = summary.get("mismatch_category_counts", {})
    if category_counts:
        for category, count in sorted(category_counts.items()):
            lines.append(f"- `{category}`: `{count}`")
    else:
        lines.append("- none")

    lines.extend(["", "## Source Artifacts", ""])
    source_artifacts = diagnostics.get("source_artifacts", {})
    if source_artifacts:
        for name, path in sorted(source_artifacts.items()):
            lines.append(f"- `{name}`: `{path}`")
    else:
        lines.append("- none")

    lines.extend(["", "## Row Diagnosis", ""])
    for row in diagnostics.get("rows", []):
        lines.append(f"### `{row['row_id']}`")
        lines.append("")
        lines.append(f"- Primary failure family: `{row['primary_failure_family']}`")
        status = row.get("source_prediction_status", {})
        lines.append(f"- Source schema-valid prediction: `{status.get('schema_valid_prediction')}`")
        lines.append(f"- Validated output schema-valid: `{status.get('validated_output_schema_valid')}`")
        lines.append(f"- Validated output source: `{status.get('validated_output_source')}`")
        mismatches = row.get("mismatches", [])
        if mismatches:
            for mismatch in mismatches:
                lines.append(
                    "- "
                    f"`{mismatch['field_path']}` "
                    f"({mismatch['mismatch_category']}): gold {mismatch['gold_value_summary']}; "
                    f"prediction {mismatch['prediction_value_summary']}"
                )
        else:
            lines.append("- no field mismatch")
        lines.append("")

    markdown_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return {"json": json_path, "markdown": markdown_path}


def write_a100_normalized_rerun_row_mismatch_report(
    diagnostics: dict[str, Any],
    output_dir: Path,
    title: str = "A100 normalized-command rerun row mismatch diagnosis",
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "row_mismatch_diagnosis.json"
    markdown_path = output_dir / "row_mismatch_diagnosis.md"
    write_json(json_path, diagnostics)

    summary = diagnostics["summary"]
    lines = [
        f"# {title}",
        "",
        (
            "This is a local evidence-only analysis derived from prior public-sample artifacts. "
            "It does not repair, normalize, semantically score, coerce, replace, or re-score predictions."
        ),
        "",
        "## Boundary",
        "",
        "- No A100 execution was performed in this phase.",
        (
            "- No training, prediction rerun, prompt change, decoding change, schema change, parser change, "
            "retry change, or evaluator metric change was performed."
        ),
        "- Invalid source predictions remain invalid.",
        "- This is not semantic-equivalence scoring.",
        "- This is not normalized-command normalization.",
        "- This is not a checkpoint release.",
        "- This is not an adapter release.",
        "- This is not held-out generalization evidence.",
        "- This makes no production-readiness claim.",
        "- This makes no public full-corpus release claim.",
        "- This is not a live-browser benchmark improvement claim.",
        "- This is not model-quality improvement evidence.",
        "",
        "## Summary",
        "",
        f"- Gold rows: `{summary['gold_row_count']}`",
        f"- Predictions: `{summary['prediction_count']}`",
        f"- Rows with mismatches: `{summary['row_mismatch_count']}`",
        f"- Schema-invalid predictions: `{summary['schema_invalid_prediction_count']}`",
        f"- Validated output schema-valid rows: `{summary.get('validated_output_schema_valid_count')}`",
        f"- Normalized-command exact-string matches: `{summary.get('normalized_command_exact_match_count')}`",
        f"- Normalized-command mismatches: `{summary.get('normalized_command_mismatch_count')}`",
        f"- Strict final JSON-valid rate remains `{summary.get('strict_final_json_valid_rate')}`",
        f"- Strict final contract_exact_match remains `{summary.get('strict_final_contract_exact_match')}`",
        "",
        "## Failure Families",
        "",
    ]
    family_counts = summary.get("family_counts", {})
    if family_counts:
        for family, count in sorted(family_counts.items()):
            lines.append(f"- `{family}`: `{count}`")
    else:
        lines.append("- none")

    lines.extend(["", "## Field Mismatch Counts", ""])
    field_counts = summary.get("field_mismatch_counts", {})
    if field_counts:
        for field_path, count in sorted(field_counts.items()):
            lines.append(f"- `{field_path}`: `{count}`")
    else:
        lines.append("- none")

    lines.extend(["", "## Mismatch Category Counts", ""])
    category_counts = summary.get("mismatch_category_counts", {})
    if category_counts:
        for category, count in sorted(category_counts.items()):
            lines.append(f"- `{category}`: `{count}`")
    else:
        lines.append("- none")

    lines.extend(["", "## Source Artifacts", ""])
    source_artifacts = diagnostics.get("source_artifacts", {})
    if source_artifacts:
        for name, path in sorted(source_artifacts.items()):
            lines.append(f"- `{name}`: `{path}`")
    else:
        lines.append("- none")

    lines.extend(["", "## Row Diagnosis", ""])
    for row in diagnostics.get("rows", []):
        lines.append(f"### `{row['row_id']}`")
        lines.append("")
        lines.append(f"- Primary failure family: `{row['primary_failure_family']}`")
        status = row.get("source_prediction_status", {})
        lines.append(f"- Source schema-valid prediction: `{status.get('schema_valid_prediction')}`")
        lines.append(f"- Validated output schema-valid: `{status.get('validated_output_schema_valid')}`")
        lines.append(f"- Validated output source: `{status.get('validated_output_source')}`")
        missing_fields = status.get("raw_attempt_missing_required_fields", [])
        missing_fields_summary = ", ".join(missing_fields) if missing_fields else "none"
        lines.append(f"- Raw attempt missing required fields: `{missing_fields_summary}`")
        error = status.get("raw_attempt_validation_error")
        lines.append(f"- Raw attempt validation error: `{error if error else 'none'}`")
        mismatches = row.get("mismatches", [])
        if mismatches:
            for mismatch in mismatches:
                lines.append(
                    "- "
                    f"`{mismatch['field_path']}` "
                    f"({mismatch['mismatch_category']}): gold {mismatch['gold_value_summary']}; "
                    f"prediction {mismatch['prediction_value_summary']}"
                )
        else:
            lines.append("- no field mismatch")
        lines.append("")

    markdown_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return {"json": json_path, "markdown": markdown_path}


def write_normalized_command_mismatch_report(
    diagnostics: dict[str, Any],
    output_dir: Path,
    title: str = "Normalized-command string mismatch diagnosis",
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "normalized_command_mismatch_diagnosis.json"
    markdown_path = output_dir / "normalized_command_mismatch_diagnosis.md"
    write_json(json_path, diagnostics)

    summary = diagnostics["summary"]
    lines = [
        f"# {title}",
        "",
        (
            "This is a local evidence-only analysis derived from prior public-sample row-mismatch artifacts. "
            "It does not normalize or semantically score `normalized_command` strings, "
            "does not mark `搜索/查询` or `明天的天气/明天天气` as equivalent, and "
            "does not repair, coerce, replace, or re-score predictions."
        ),
        "",
        "## Boundary",
        "",
        "- No A100 execution was performed in this phase.",
        (
            "- No training, prediction rerun, prompt change, decoding change, schema change, parser change, "
            "retry change, or evaluator metric change was performed."
        ),
        "- This is not semantic-equivalence scoring.",
        "- This is not a checkpoint release.",
        "- This is not an adapter release.",
        "- This is not held-out generalization evidence.",
        "- This makes no production-readiness claim.",
        "- This makes no public full-corpus release claim.",
        "- This is not a live-browser benchmark improvement claim.",
        "- This is not model-quality improvement evidence.",
        "",
        "## Summary",
        "",
        f"- Normalized-command mismatch rows: `{summary['normalized_command_mismatch_count']}`",
        f"- Strict string-only rows: `{summary['string_only_count']}`",
        f"- Co-occurs with schema failure: `{summary['co_occurs_with_schema_failure_count']}`",
        (
            "- Co-occurs with task/route/safety mismatch: "
            f"`{summary['co_occurs_with_semantic_task_route_safety_count']}`"
        ),
        f"- Strict metrics preserved: `{summary['strict_metrics_preserved']}`",
        f"- Strict final JSON-valid rate remains `{summary.get('strict_final_json_valid_rate')}`",
        f"- Strict final contract_exact_match remains `{summary.get('strict_final_contract_exact_match')}`",
        "",
        "## Context Counts",
        "",
    ]
    context_counts = summary.get("context_counts", {})
    if context_counts:
        for context_kind, count in sorted(context_counts.items()):
            lines.append(f"- `{context_kind}`: `{count}`")
    else:
        lines.append("- none")

    lines.extend(["", "## Source Artifacts", ""])
    source_artifacts = diagnostics.get("source_artifacts", {})
    if source_artifacts:
        for name, path in sorted(source_artifacts.items()):
            lines.append(f"- `{name}`: `{path}`")
    else:
        lines.append("- none")

    lines.extend(["", "## Transitive Source Artifacts", ""])
    lines.append(
        "These artifacts are inherited through the source row-mismatch diagnosis for traceability only; "
        "this phase derives its counts from the row-mismatch diagnosis artifacts above."
    )
    transitive_source_artifacts = diagnostics.get("transitive_source_artifacts", {})
    if transitive_source_artifacts:
        for name, path in sorted(transitive_source_artifacts.items()):
            lines.append(f"- `{name}`: `{path}`")
    else:
        lines.append("- none")

    lines.extend(["", "## Row Diagnosis", ""])
    for row in diagnostics.get("rows", []):
        lines.append(f"### `{row['row_id']}`")
        lines.append("")
        lines.append(f"- Context: `{row['context_kind']}`")
        lines.append(f"- Source primary failure family: `{row.get('source_primary_failure_family')}`")
        co_occurring = row.get("co_occurring_field_paths", [])
        lines.append(f"- Co-occurring field paths: `{', '.join(co_occurring) if co_occurring else 'none'}`")
        mismatch = row.get("mismatch", {})
        lines.append(
            "- "
            f"`normalized_command` ({mismatch.get('mismatch_category')}): "
            f"gold {mismatch.get('gold_value_summary')}; "
            f"prediction {mismatch.get('prediction_value_summary')}"
        )
        lines.append("")

    markdown_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return {"json": json_path, "markdown": markdown_path}


def write_retry_template_slot_exact_match_mismatch_report(
    diagnostics: dict[str, Any],
    output_dir: Path,
    title: str = "Retry-template slot exact-match mismatch diagnosis",
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "slot_exact_match_mismatch_diagnosis.json"
    markdown_path = output_dir / "slot_exact_match_mismatch_diagnosis.md"
    write_json(json_path, diagnostics)

    summary = diagnostics["summary"]
    lines = [
        f"# {title}",
        "",
        (
            "This is a local evidence-only analysis derived from prior public-sample artifacts. "
            "It explains strict slot exact-match failures only; it does not perform slot normalization, "
            "semantic-equivalence scoring, prediction repair, prediction replacement, or re-score."
        ),
        "",
        "## Boundary",
        "",
        "- No A100 execution was performed in this phase.",
        (
            "- No training, prediction rerun, prompt change, decoding change, schema change, parser change, "
            "retry change, or evaluator metric change was performed."
        ),
        "- This is not slot normalization.",
        "- This is not normalized-command normalization.",
        "- This is not semantic-equivalence scoring.",
        "- This is not a checkpoint release.",
        "- This is not an adapter release.",
        "- This is not held-out generalization evidence.",
        "- This makes no production-readiness claim.",
        "- This makes no public full-corpus release claim.",
        "- This is not a live-browser benchmark improvement claim.",
        "- This is not model-quality improvement evidence.",
        "",
        "## Summary",
        "",
        f"- Gold rows: `{summary['gold_row_count']}`",
        f"- Predictions: `{summary['prediction_count']}`",
        f"- Rows with mismatches: `{summary['row_mismatch_count']}`",
        f"- Schema-invalid predictions: `{summary['schema_invalid_prediction_count']}`",
        f"- Validated output schema-valid rows: `{summary.get('validated_output_schema_valid_count')}`",
        f"- Normalized-command mismatches: `{summary.get('normalized_command_mismatch_count')}`",
        f"- Strict final JSON-valid rate remains `{summary.get('strict_final_json_valid_rate')}`",
        f"- Strict final slot_f1 remains `{summary.get('strict_final_slot_f1')}`",
        f"- Strict final contract_exact_match remains `{summary.get('strict_final_contract_exact_match')}`",
        "",
        "## Slot Families",
        "",
    ]
    slot_counts = summary.get("slot_family_counts", {})
    if slot_counts:
        for family, count in sorted(slot_counts.items()):
            lines.append(f"- `{family}`: `{count}`")
    else:
        lines.append("- none")

    lines.extend(["", "## Field Mismatch Counts", ""])
    field_counts = summary.get("field_mismatch_counts", {})
    if field_counts:
        for field_path, count in sorted(field_counts.items()):
            lines.append(f"- `{field_path}`: `{count}`")
    else:
        lines.append("- none")

    lines.extend(["", "## Source Artifacts", ""])
    source_artifacts = diagnostics.get("source_artifacts", {})
    if source_artifacts:
        for name, path in sorted(source_artifacts.items()):
            lines.append(f"- `{name}`: `{path}`")
    else:
        lines.append("- none")

    lines.extend(["", "## Row Diagnosis", ""])
    for row in diagnostics.get("rows", []):
        lines.append(f"### `{row['row_id']}`")
        lines.append("")
        lines.append(f"- Primary slot mismatch family: `{row['primary_slot_mismatch_family']}`")
        lines.append(
            "- Normalized-command mismatch present: "
            f"`{row.get('normalized_command_mismatch_present')}`"
        )
        status = row.get("source_prediction_status", {})
        lines.append(f"- Source schema-valid prediction: `{status.get('schema_valid_prediction')}`")
        lines.append(f"- Validated output schema-valid: `{status.get('validated_output_schema_valid')}`")
        lines.append(f"- Validated output source: `{status.get('validated_output_source')}`")
        mismatches = row.get("mismatches", [])
        if mismatches:
            for mismatch in mismatches:
                lines.append(
                    "- "
                    f"`{mismatch['field_path']}` "
                    f"({mismatch['mismatch_category']}): gold {mismatch['gold_value_summary']}; "
                    f"prediction {mismatch['prediction_value_summary']}"
                )
        else:
            lines.append("- no field mismatch")
        lines.append("")

    markdown_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return {"json": json_path, "markdown": markdown_path}


def write_sft_target_template_alignment_report(
    diagnostics: dict[str, Any],
    output_dir: Path,
    title: str = "Voice2Task source diagnostics",
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    alignment = diagnostics["sft_target_template_alignment"]
    json_path = output_dir / "sft_target_template_alignment.json"
    markdown_path = output_dir / "sft_target_template_alignment.md"
    write_json(json_path, alignment)

    summary = alignment["summary"]
    label_mask = alignment["label_mask_evidence"]
    chat_template = alignment["chat_template_evidence"]
    metadata = alignment["metadata_alignment"]
    lines = [
        f"# SFT Target-Template Alignment - {title}",
        "",
        (
            "This diagnostic compares public-sample SFT training rendering with prediction prompts. "
            "It does not run private prediction, retrain, repair outputs, or replace prior diagnostic artifacts."
        ),
        "",
        "## Boundary",
        "",
        "- This is not a checkpoint release.",
        "- This is not an adapter release.",
        "- This is not dev/test generalization evidence.",
        "- This makes no production-readiness claim.",
        "- This is not a live-browser benchmark improvement claim.",
        "",
        "## Summary",
        "",
        f"- Diagnostic status: `{summary['diagnostic_status']}`",
        f"- Rows compared: `{summary['row_count']}`",
        f"- Prediction split: `{summary['prediction_split']}`",
        f"- Same system/user prefix for all rows: `{summary['all_rows_share_system_user_prefix']}`",
        f"- Same core system/user prefix for all rows: `{summary.get('all_rows_share_core_system_user_prefix')}`",
        "- Prediction output boundary visible in all prediction prompts: "
        f"`{summary.get('all_prediction_prompts_include_prediction_output_boundary')}`",
        f"- Assistant target in all training text: `{summary['all_training_text_contains_assistant_target']}`",
        f"- Assistant target excluded from all prediction prompts: "
        f"`{summary['all_prediction_prompts_exclude_assistant_target']}`",
        f"- Structural target span status: `{summary['structural_target_span_status']}`",
        "",
        "## Label-Mask Evidence",
        "",
        f"- Status: `{label_mask['status']}`",
        f"- True label-mask status: `{label_mask['true_label_mask_status']}`",
        f"- Prompt tokens masked: `{label_mask['prompt_tokens_masked']}`",
        f"- Assistant tokens carry loss: `{label_mask['assistant_tokens_carry_loss']}`",
        f"- Evidence gaps: `{label_mask['evidence_gaps']}`",
        "",
        "## Chat Template Evidence",
        "",
        f"- Rendering source: `{chat_template['rendering_source']}`",
        f"- Fallback policy: `{chat_template['fallback_policy']}`",
        f"- Tokenizer template status: `{chat_template['tokenizer_template_status']}`",
        f"- Evidence gaps: `{chat_template['evidence_gaps']}`",
        "",
        "## Adapter/Base Metadata Alignment",
        "",
        f"- Base model status: `{metadata['base_model']['status']}`",
        f"- Base model training config: `{metadata['base_model']['training_config']}`",
        f"- Base model prediction metadata: `{metadata['base_model']['prediction_metadata']}`",
        f"- Model source matches: `{metadata['model_source']['matches']}`",
        f"- Stack matches: `{metadata['stack']['matches']}`",
        f"- Prediction split matches: `{metadata['prediction_split']['matches']}`",
        f"- Adapter gate: `{metadata['adapter_gate']}`",
        f"- Adapter release status: `{metadata['adapter_release_status']}`",
        f"- Prediction source kind: `{metadata['prediction_source_kind']}`",
        f"- Formatting policy matches: `{metadata['formatting_policy']['matches']}`",
        "",
        "## Prior Artifacts Linked",
        "",
    ]
    prior_artifacts = alignment.get("prior_artifacts", {})
    if prior_artifacts:
        for name, path in sorted(prior_artifacts.items()):
            lines.append(f"- `{name}`: `{path}`")
    else:
        lines.append("- none")
    lines.extend(["", "## Row Evidence", ""])
    for row in alignment.get("rows", []):
        lines.extend(
            [
                f"### `{row['row_id']}`",
                "",
                f"- Same system/user prefix: `{row['same_system_user_prefix']}`",
                f"- Same core system/user prefix: `{row.get('same_core_system_user_prefix')}`",
                "- Prediction-only output boundary suffix visible: "
                f"`{row.get('prediction_only_boundary_suffix_visible')}`",
                f"- Assistant target in training text: `{row['assistant_contract_target_in_training_text']}`",
                f"- Assistant target in prediction prompt: `{row['assistant_contract_target_in_prediction_prompt']}`",
                f"- Prediction prompt ends with generation boundary: "
                f"`{row['prediction_prompt_ends_with_generation_boundary']}`",
                f"- Structural proxy status: `{row['structural_proxy_status']}`",
                f"- Assistant target span: `{row['assistant_target_span']}`",
                f"- Training text SHA-256: `{row['training_text_sha256']}`",
                f"- Prediction prompt SHA-256: `{row['prediction_prompt_sha256']}`",
                f"- Assistant target SHA-256: `{row['assistant_contract_target_sha256']}`",
                f"- Training text characters: `{row['training_text_char_count']}`",
                f"- Prediction prompt characters: `{row['prediction_prompt_char_count']}`",
                f"- Assistant target characters: `{row['assistant_contract_target_char_count']}`",
                "",
            ]
        )

    markdown_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return {"sft_target_template_alignment_json": json_path, "sft_target_template_alignment_markdown": markdown_path}


def _sanitize_report_value(value: Any) -> Any:
    if isinstance(value, str):
        sanitized = PRIVATE_REPORT_PATH_RE.sub("<private_path>", value)
        sanitized = PRIVATE_PATH_RE.sub("<private_path>", sanitized)
        sanitized = PRIVATE_IP_RE.sub("<private_ip>", sanitized)
        return SECRET_RE.sub("<secret>", sanitized)
    if isinstance(value, dict):
        return {str(_sanitize_report_value(str(key))): _sanitize_report_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize_report_value(item) for item in value]
    return value


def _label_provenance_claims() -> dict[str, bool]:
    return {
        "checkpoint_release": False,
        "adapter_release": False,
        "held_out_generalization_claim": False,
        "production_readiness_claim": False,
        "live_browser_benchmark_claim": False,
        "model_recovery_claim": False,
    }


def _standalone_true_label_mask_status(objective_inspection: dict[str, Any], gaps: list[Any]) -> str:
    status = objective_inspection.get("true_label_mask_status")
    if status in {"inspectable", "fixture_only", "unavailable"}:
        return str(status)
    provenance = objective_inspection.get("label_provenance")
    source_kind = str(provenance.get("source_kind", "")) if isinstance(provenance, dict) else ""
    if source_kind in {"fixture", "fixture_collator", "simulated", "simulated_collator"}:
        return "fixture_only"
    if (
        objective_inspection.get("inspection_status") == "inspectable"
        and objective_inspection.get("label_tensor_available") is True
        and not gaps
        and isinstance(objective_inspection.get("prompt_tokens_masked"), bool)
        and isinstance(objective_inspection.get("assistant_tokens_carry_loss"), bool)
    ):
        return "inspectable"
    return "unavailable"


def write_sft_label_provenance_evidence_pack(
    *,
    objective_inspection: dict[str, Any],
    output_dir: Path,
    prior_artifacts: dict[str, str] | None = None,
    title: str = "Voice2Task SFT label provenance evidence",
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "label_provenance_summary.json"
    markdown_path = output_dir / "label_provenance_summary.md"
    provenance = objective_inspection.get("label_provenance")
    if not isinstance(provenance, dict):
        provenance = {"source_kind": provenance or "unavailable", "real_training_path": False}
    gaps = objective_inspection.get("evidence_gaps")
    if not isinstance(gaps, list):
        gaps = ["real_training_labels_not_inspected", "real_training_label_provenance_missing"]
    true_label_mask_status = _standalone_true_label_mask_status(objective_inspection, gaps)
    summary = {
        "evidence_kind": "sft_label_provenance",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "inspection_status": objective_inspection.get("inspection_status", "unknown"),
        "dependency_unavailable": bool(objective_inspection.get("dependency_unavailable", False)),
        "tokenizer_status": objective_inspection.get("tokenizer_status", "unknown"),
        "tokenizer_template_status": objective_inspection.get("tokenizer_template_status", "unknown"),
        "collator_status": objective_inspection.get("collator_status", "unknown"),
        "label_source": objective_inspection.get("label_source", "unavailable"),
        "label_provenance": _sanitize_report_value(dict(provenance)),
        "label_tensor_available": bool(objective_inspection.get("label_tensor_available", False)),
        "true_label_mask_status": true_label_mask_status,
        "prompt_token_count": objective_inspection.get("prompt_token_count"),
        "assistant_token_count": objective_inspection.get("assistant_token_count"),
        "prompt_tokens_masked": objective_inspection.get("prompt_tokens_masked"),
        "assistant_tokens_carry_loss": objective_inspection.get("assistant_tokens_carry_loss"),
        "evidence_gaps": _sanitize_report_value(list(gaps)),
        "loss_interpretation": _sanitize_report_value(objective_inspection.get("loss_interpretation", {})),
        "prior_artifacts": _sanitize_report_value(prior_artifacts or {}),
        "claims": _label_provenance_claims(),
        "artifact_policy": {
            "raw_rendered_training_text_written": False,
            "raw_prompt_or_target_written": False,
            "checkpoints_or_adapters_copied_to_git": False,
            "remote_or_private_paths_omitted": True,
        },
    }
    write_json(json_path, summary)

    prior = summary["prior_artifacts"]
    lines = [
        f"# {title}",
        "",
        (
            "This evidence pack summarizes SFT label provenance only. "
            "It does not publish raw rendered prompts, checkpoints, adapters, private paths, or raw logs."
        ),
        "",
        "## Boundary",
        "",
        "- This is not a checkpoint release.",
        "- This is not an adapter release.",
        "- This is not held-out generalization evidence.",
        "- This makes no production-readiness claim.",
        "- This is not a live-browser benchmark or benchmark-improvement claim.",
        "",
        "## Summary",
        "",
        f"- Inspection status: `{summary['inspection_status']}`",
        f"- Tokenizer status: `{summary['tokenizer_status']}`",
        f"- Tokenizer template status: `{summary['tokenizer_template_status']}`",
        f"- Collator status: `{summary['collator_status']}`",
        f"- Label source: `{summary['label_source']}`",
        f"- Label tensor available: `{summary['label_tensor_available']}`",
        f"- True label-mask status: `{summary['true_label_mask_status']}`",
        f"- Prompt token count: `{summary['prompt_token_count']}`",
        f"- Assistant token count: `{summary['assistant_token_count']}`",
        f"- Prompt tokens masked: `{summary['prompt_tokens_masked']}`",
        f"- Assistant tokens carry loss: `{summary['assistant_tokens_carry_loss']}`",
        "",
        "## Evidence Gaps",
        "",
    ]
    if summary["evidence_gaps"]:
        for gap in summary["evidence_gaps"]:
            lines.append(f"- `{gap}`")
    else:
        lines.append("- none")
    lines.extend(["", "## Prior Artifacts", ""])
    if prior:
        for name, path in sorted(prior.items()):
            lines.append(f"- `{name}`: `{path}`")
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Loss improvement alone does not prove Browser Task Contract learning.",
            "- Fixture or simulated labels are not real TRL/private-training-path proof.",
            "- True label provenance requires inspected labels from the real tokenizer/collator path.",
            "",
        ]
    )
    markdown_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return {"json": json_path, "markdown": markdown_path}


def write_runtime_label_provenance_prep_evidence_pack(
    *,
    prep_metadata: dict[str, Any],
    output_dir: Path,
    prior_artifacts: dict[str, str] | None = None,
    title: str = "Voice2Task runtime label provenance preparation",
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "runtime_label_provenance_prep.json"
    markdown_path = output_dir / "runtime_label_provenance_prep.md"
    metadata = _sanitize_report_value(dict(prep_metadata))
    metadata_prior = metadata.get("prior_artifacts", {})
    combined_prior = dict(metadata_prior if isinstance(metadata_prior, dict) else {})
    combined_prior.update(prior_artifacts or {})
    combined_prior = _sanitize_report_value(combined_prior)
    metadata_claims = metadata.get("claims", {})
    safe_claims = {
        "runtime_readiness_proves_contract_learning": False,
        "checkpoint_release": False,
        "adapter_release": False,
        "held_out_generalization_claim": False,
        "production_readiness_claim": False,
        "live_browser_benchmark_claim": False,
    }
    metadata_artifact_policy = metadata.get("artifact_policy", {})
    safe_artifact_policy = {
        "raw_rendered_prompts_written": False,
        "raw_logs_copied_to_git": False,
        "checkpoints_or_adapters_copied_to_git": False,
        "private_paths_omitted": True,
    }
    summary = {
        "evidence_kind": "sft_runtime_label_provenance_prep",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "runtime_check_status": metadata.get("runtime_check_status", "unknown"),
        "private_override": metadata.get("private_override", {}),
        "output_root_policy": metadata.get("output_root_policy", {}),
        "dependency_policy": metadata.get("dependency_policy", {}),
        "label_provenance_intent": metadata.get("label_provenance_intent", {}),
        "label_tensor_available": False,
        "true_label_mask_status": "unavailable",
        "inspection_status": metadata.get("inspection_status", "runtime_check_not_executed"),
        "evidence_gaps": metadata.get(
            "evidence_gaps",
            ["runtime_check_not_executed", "real_training_labels_not_inspected"],
        ),
        "prior_artifacts": combined_prior,
        "claims": {
            **(metadata_claims if isinstance(metadata_claims, dict) else {}),
            **safe_claims,
        },
        "artifact_policy": {
            **(metadata_artifact_policy if isinstance(metadata_artifact_policy, dict) else {}),
            **safe_artifact_policy,
        },
    }
    summary = _sanitize_report_value(summary)
    write_json(json_path, summary)

    prior = summary["prior_artifacts"]
    lines = [
        f"# {title}",
        "",
        (
            "This phase did not run private A100 execution, did not load a private adapter, "
            "did not download a model, and did not inspect real tokenizer/collator labels."
        ),
        "",
        "## Boundary",
        "",
        "- Runtime readiness is not true label-mask evidence.",
        "- This is not a checkpoint release.",
        "- This is not an adapter release.",
        "- This is not held-out generalization evidence.",
        "- This makes no production-readiness claim.",
        "- This is not a live-browser benchmark or benchmark-improvement claim.",
        "",
        "## Summary",
        "",
        f"- Runtime check status: `{summary['runtime_check_status']}`",
        f"- Private override status: `{summary['private_override'].get('status', 'unknown')}`",
        f"- Output-root policy status: `{summary['output_root_policy'].get('status', 'unknown')}`",
        f"- Label tensor available: `{summary['label_tensor_available']}`",
        f"- True label-mask status: `{summary['true_label_mask_status']}`",
        "",
        "## Evidence Gaps",
        "",
    ]
    gaps = summary["evidence_gaps"]
    if isinstance(gaps, list) and gaps:
        for gap in gaps:
            lines.append(f"- `{gap}`")
    else:
        lines.append("- none")
    lines.extend(["", "## Prior Artifacts", ""])
    if isinstance(prior, dict) and prior:
        for name, path in sorted(prior.items()):
            lines.append(f"- `{name}`: `{path}`")
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Preparation metadata can make a later private runtime check auditable.",
            "- It cannot prove Browser Task Contract learning or real loss masking.",
            "- Later runtime execution must commit only sanitized public summaries.",
            "",
        ]
    )
    markdown_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return {"json": json_path, "markdown": markdown_path}


def _runtime_label_provenance_check_claims() -> dict[str, bool]:
    return {
        "checkpoint_release": False,
        "adapter_release": False,
        "held_out_generalization_claim": False,
        "production_readiness_claim": False,
        "live_browser_benchmark_claim": False,
        "model_recovery_claim": False,
    }


def _runtime_label_provenance_check_artifact_policy() -> dict[str, bool]:
    return {
        "raw_rendered_prompts_written": False,
        "raw_logs_copied_to_git": False,
        "checkpoints_or_adapters_copied_to_git": False,
        "private_paths_omitted": True,
    }


def _runtime_check_status_from_metadata(metadata: dict[str, Any]) -> str:
    runtime_check_status = str(metadata.get("runtime_check_status", "unknown"))
    if runtime_check_status != "executed_runtime_label_provenance_check":
        if runtime_check_status and runtime_check_status != "unknown":
            return runtime_check_status
        evidence_status = str(metadata.get("evidence_status", "labels_unavailable"))
        return "labels_unavailable" if evidence_status == "labels_inspected" else evidence_status
    runtime_gate = metadata.get("runtime_gate")
    will_run_runtime_check = (
        isinstance(runtime_gate, dict) and runtime_gate.get("will_run_runtime_label_provenance_check") is True
    )
    source_kind = str(metadata.get("label_source_kind", ""))
    provenance = metadata.get("label_provenance")
    real_training_path = False
    if isinstance(provenance, dict):
        source_kind = str(provenance.get("source_kind", source_kind))
        real_training_path = provenance.get("real_training_path") is True
    if metadata.get("true_label_mask_status") == "fixture_only" or source_kind in {
        "fixture",
        "fixture_collator",
        "simulated",
        "simulated_collator",
    }:
        return "fixture_only"
    if (
        metadata.get("inspection_status") == "inspectable"
        and metadata.get("label_tensor_available") is True
        and metadata.get("true_label_mask_status") == "inspectable"
        and real_training_path
        and will_run_runtime_check
    ):
        return "labels_inspected"
    if metadata.get("label_tensor_available") is True:
        return "labels_available_but_not_real_training_proof"
    evidence_status = str(metadata.get("evidence_status", "labels_unavailable"))
    return "labels_unavailable" if evidence_status == "labels_inspected" else evidence_status


def write_runtime_label_provenance_check_evidence_pack(
    *,
    runtime_metadata: dict[str, Any],
    output_dir: Path,
    prior_artifacts: dict[str, str] | None = None,
    leak_scan_result: dict[str, Any] | None = None,
    title: str = "Voice2Task observed runtime label provenance evidence",
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "runtime_label_provenance_check.json"
    markdown_path = output_dir / "runtime_label_provenance_check.md"
    metadata = _sanitize_report_value(dict(runtime_metadata))
    metadata_prior = metadata.get("prior_artifacts", {})
    combined_prior = dict(metadata_prior if isinstance(metadata_prior, dict) else {})
    combined_prior.update(prior_artifacts or {})
    combined_prior = _sanitize_report_value(combined_prior)
    provenance = metadata.get("label_provenance")
    if not isinstance(provenance, dict):
        provenance = {"source_kind": metadata.get("label_source_kind", "unavailable"), "real_training_path": False}
    evidence_status = _runtime_check_status_from_metadata(metadata)
    resolved_leak_scan_status = leak_scan_result or metadata.get(
        "leak_scan_status",
        {"ok": None, "status": "pending_until_leak_scan_runs"},
    )
    summary = {
        "evidence_kind": "sft_runtime_label_provenance_observed",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "evidence_status": evidence_status,
        "runtime_source_kind": "private_a100_runtime",
        "runtime_check_status": metadata.get("runtime_check_status", "unknown"),
        "runtime_gate": _sanitize_report_value(metadata.get("runtime_gate", {})),
        "output_root_policy": _sanitize_report_value(metadata.get("output_root_policy", {})),
        "dataset_manifest_id": metadata.get("dataset_manifest_id", "unknown"),
        "inspection_status": metadata.get("inspection_status", "unknown"),
        "tokenizer_status": metadata.get("tokenizer_status", "unknown"),
        "tokenizer_template_status": metadata.get("tokenizer_template_status", "unknown"),
        "collator_status": metadata.get("collator_status", "unknown"),
        "package_versions": _sanitize_report_value(metadata.get("package_versions", {})),
        "dependency_policy": _sanitize_report_value(metadata.get("dependency_policy", {})),
        "leak_scan_status": _sanitize_report_value(resolved_leak_scan_status),
        "label_source": metadata.get("label_source", "unavailable"),
        "label_source_kind": provenance.get("source_kind", metadata.get("label_source_kind", "unavailable")),
        "label_provenance": _sanitize_report_value(dict(provenance)),
        "label_tensor_available": bool(metadata.get("label_tensor_available", False)),
        "true_label_mask_status": metadata.get("true_label_mask_status", "unavailable"),
        "prompt_token_count": metadata.get("prompt_token_count"),
        "assistant_token_count": metadata.get("assistant_token_count"),
        "prompt_tokens_masked": metadata.get("prompt_tokens_masked"),
        "assistant_tokens_carry_loss": metadata.get("assistant_tokens_carry_loss"),
        "assistant_only_loss_mask_claim": False,
        "evidence_gaps": _sanitize_report_value(metadata.get("evidence_gaps", [])),
        "loss_interpretation": _sanitize_report_value(metadata.get("loss_interpretation", {})),
        "prior_artifacts": combined_prior,
        "release_status": "not_released",
        "claims": _runtime_label_provenance_check_claims(),
        "artifact_policy": _runtime_label_provenance_check_artifact_policy(),
    }
    summary = _sanitize_report_value(summary)
    write_json(json_path, summary)
    leak_scan_status = summary["leak_scan_status"]
    leak_scan_ok = leak_scan_status.get("ok") if isinstance(leak_scan_status, dict) else "unknown"

    lines = [
        f"# {title}",
        "",
        (
            "Runtime label provenance evidence is objective-path evidence only. "
            "It reports whether tokenizer/collator labels were inspectable without publishing private runtime "
            "paths, raw logs, checkpoints, adapters, or private corpus rows."
        ),
        "",
        "## Boundary",
        "",
        "- This is not a checkpoint release.",
        "- This is not an adapter release.",
        "- This is not held-out generalization evidence.",
        "- This makes no production-readiness claim.",
        "- This is not a live-browser benchmark or benchmark-improvement claim.",
        "- This is not model recovery evidence.",
        "",
        "## Summary",
        "",
        f"- Evidence status: `{summary['evidence_status']}`",
        f"- Runtime source kind: `{summary['runtime_source_kind']}`",
        f"- Runtime gate: `{summary['runtime_gate']}`",
        f"- Output-root policy: `{summary['output_root_policy']}`",
        f"- Dataset manifest: `{summary['dataset_manifest_id']}`",
        f"- Label source: `{summary['label_source']}`",
        f"- Label source kind: `{summary['label_source_kind']}`",
        f"- Package versions: `{summary['package_versions']}`",
        f"- Dependency policy: `{summary['dependency_policy']}`",
        f"- Leak scan ok: `{leak_scan_ok}`",
        f"- Label tensor available: `{summary['label_tensor_available']}`",
        f"- True label-mask status: `{summary['true_label_mask_status']}`",
        f"- Prompt tokens masked: `{summary['prompt_tokens_masked']}`",
        f"- Assistant tokens carry loss: `{summary['assistant_tokens_carry_loss']}`",
        f"- Assistant-only loss-mask claim: `{summary['assistant_only_loss_mask_claim']}`",
        "",
        "## Evidence Gaps",
        "",
    ]
    gaps = summary["evidence_gaps"]
    if isinstance(gaps, list) and gaps:
        for gap in gaps:
            lines.append(f"- `{gap}`")
    else:
        lines.append("- none")
    lines.extend(["", "## Prior Artifacts", ""])
    prior = summary["prior_artifacts"]
    if isinstance(prior, dict) and prior:
        for name, path in sorted(prior.items()):
            lines.append(f"- `{name}`: `{path}`")
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Objective Limitations",
            "",
            "- `prompt_tokens_masked=false` means this evidence does not support an assistant-only loss-mask claim.",
            (
                "- `assistant_tokens_carry_loss=true` means assistant target tokens participate in loss, "
                "not that the model has learned the contract task."
            ),
            "",
            "## Interpretation",
            "",
            "- Inspectable real labels can support SFT objective-path interpretation only.",
            "- Fixture or simulated labels remain fixture-only and keep evidence gaps.",
            "- Runtime label evidence does not establish held-out quality, release readiness, or live-browser gains.",
            "",
        ]
    )
    markdown_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return {"json": json_path, "markdown": markdown_path}


def write_source_diagnostics_report(
    diagnostics: dict[str, Any],
    output_dir: Path,
    title: str = "Voice2Task source diagnostics",
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "source_diagnostics.json"
    markdown_path = output_dir / "source_diagnostics.md"
    write_json(json_path, diagnostics)

    summary = diagnostics["summary"]
    target_shape = diagnostics["target_shape"]
    prediction_symptoms = diagnostics["prediction_symptoms"]
    split_coverage = diagnostics["split_coverage"]
    training_coverage = diagnostics["training_coverage"]
    current_prompt_constraints = diagnostics["current_prompt_constraints"]
    prediction_run_prompt_evidence = diagnostics["prediction_run_prompt_evidence"]
    decoding_evidence = diagnostics["decoding_evidence"]
    lines = [
        f"# {title}",
        "",
        (
            "This source diagnostic is evidence-only: invalid predictions remain invalid. "
            "It does not repair, normalize, coerce, or replace predictions."
        ),
        "",
        "## Boundary",
        "",
        "- This is not a checkpoint release.",
        "- This is not an adapter release.",
        "- This makes no production-readiness claim.",
        "- This makes no full-private-corpus claim.",
        "- This is not a live-browser benchmark or benchmark-improvement claim.",
        "",
        "## Summary",
        "",
        f"- Gold rows: `{summary['gold_row_count']}`",
        f"- Predictions: `{summary['prediction_count']}`",
        f"- Missing predictions: `{prediction_symptoms.get('missing_prediction_count', 0)}`",
        f"- Gold path-like route targets: `{target_shape['path_like_route_count']}`",
        f"- Gold list-shaped slots targets: `{target_shape['list_slots_count']}`",
        f"- Prediction path-like routes: `{prediction_symptoms['path_like_route_count']}`",
        f"- Prediction list-shaped slots: `{prediction_symptoms['list_slots_count']}`",
        f"- Schema-invalid predictions: `{prediction_symptoms['schema_invalid_prediction_count']}`",
        f"- Missing `confirmation_required`: `{prediction_symptoms.get('missing_confirmation_required_count', 0)}`",
        "",
        "## Split And Training Coverage",
        "",
        f"- Configured training split: `{split_coverage['configured_training_split']}`",
        f"- Configured prediction split: `{split_coverage['configured_prediction_split']}`",
        f"- Training rows in gold sample: `{split_coverage['training_row_count']}`",
        f"- Prediction-split gold rows: `{split_coverage['prediction_gold_row_count']}`",
        f"- Gold split counts: `{split_coverage['gold_split_counts']}`",
        f"- Training task_type coverage: `{training_coverage['task_type_counts']}`",
        f"- Training route coverage: `{training_coverage['route_counts']}`",
        "",
        "## Current Prompt Constraints",
        "",
        (
            "These describe the current formatter and future rerun preparation. "
            "They are not proof that older prediction artifacts used this strengthened prompt."
        ),
        "",
        f"- task_type enum visible: `{current_prompt_constraints['task_type_enum_visible']}`",
        f"- route enum visible: `{current_prompt_constraints['route_enum_visible']}`",
        f"- route is not a URL/path visible: `{current_prompt_constraints['route_not_url_or_path_visible']}`",
        "- route execution-channel ontology visible: "
        f"`{current_prompt_constraints.get('route_execution_channel_visible', False)}`",
        "- route domain/topic values excluded from route visible: "
        f"`{current_prompt_constraints.get('route_domain_values_not_route_visible', False)}`",
        "- weather-to-search route example visible: "
        f"`{current_prompt_constraints.get('weather_to_search_route_example_visible', False)}`",
        "- confirmation_required boolean visible: "
        f"`{current_prompt_constraints.get('confirmation_required_boolean_visible', False)}`",
        "- weather-to-search confirmation false visible: "
        f"`{current_prompt_constraints.get('weather_to_search_confirmation_false_visible', False)}`",
        f"- slots object-not-array visible: `{current_prompt_constraints['slots_object_not_array_visible']}`",
        "",
        "## Prediction-Run Prompt Evidence",
        "",
        f"- prompt constraints present in metadata: `{prediction_run_prompt_evidence['prompt_constraints_present']}`",
        f"- fields present: `{prediction_run_prompt_evidence['fields_present']}`",
        f"- constraints: `{prediction_run_prompt_evidence['constraints']}`",
        f"- evidence gaps: `{prediction_run_prompt_evidence['evidence_gaps']}`",
        "- current prompt constraints are rerun preparation, not old-run evidence: "
        f"`{prediction_run_prompt_evidence['current_prompt_constraints_are_rerun_preparation_not_old_run_evidence']}`",
        "",
        "## Decoding Evidence",
        "",
        "Evidence gaps are missing evidence, not inferred cause.",
        "",
        f"- decoding_policy present: `{decoding_evidence['decoding_policy_present']}`",
        f"- fields present: `{decoding_evidence['fields_present']}`",
        f"- policy: `{decoding_evidence['policy']}`",
        f"- evidence gaps: `{decoding_evidence['evidence_gaps']}`",
        "",
        "## Symptom Examples",
        "",
    ]
    if prediction_symptoms.get("path_like_route_examples"):
        lines.append("### Path-like Routes")
        lines.append("")
        for example in prediction_symptoms["path_like_route_examples"]:
            lines.append(f"- `{example['row_id']}`: {example['route']}")
        lines.append("")
    if prediction_symptoms.get("list_slots_examples"):
        lines.append("### List-shaped Slots")
        lines.append("")
        for example in prediction_symptoms["list_slots_examples"]:
            lines.append(f"- `{example['row_id']}`: {example['slots']}")
        lines.append("")
    if prediction_symptoms.get("missing_confirmation_required_examples"):
        lines.append("### Missing Confirmation Required")
        lines.append("")
        for example in prediction_symptoms["missing_confirmation_required_examples"]:
            lines.append(f"- `{example['row_id']}`: {example['prediction']}")
        lines.append("")
    if (
        not prediction_symptoms.get("path_like_route_examples")
        and not prediction_symptoms.get("list_slots_examples")
        and not prediction_symptoms.get("missing_confirmation_required_examples")
    ):
        lines.append("- none")
        lines.append("")

    markdown_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    paths = {"json": json_path, "markdown": markdown_path}
    if "sft_target_template_alignment" in diagnostics:
        paths.update(write_sft_target_template_alignment_report(diagnostics, output_dir, title=title))
    return paths


def write_prediction_evidence_pack(
    *,
    output_dir: Path,
    prediction_path: Path,
    prediction_metadata: dict[str, Any],
    metrics_path: Path,
    smoke_result: dict[str, Any],
    leak_scan_result: dict[str, Any],
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "manifest.json"
    report_path = output_dir / "report.md"
    release_status = str(prediction_metadata.get("release_status", "not_released"))
    prediction_source_kind = str(prediction_metadata.get("prediction_source_kind", "unknown"))
    prediction_split = str(prediction_metadata.get("prediction_split", "all"))
    overfit_diagnostic = bool(prediction_metadata.get("overfit_diagnostic", False))
    generalization_claim = bool(prediction_metadata.get("generalization_claim", False))
    diagnostic_evidence = overfit_diagnostic and prediction_split == "train"
    sidecars = prediction_metadata.get("sidecars")
    if not isinstance(sidecars, dict):
        sidecars = {}
    diagnostic_artifacts = prediction_metadata.get("diagnostic_artifacts")
    if not isinstance(diagnostic_artifacts, dict):
        diagnostic_artifacts = {}
    if diagnostic_evidence:
        diagnostic_artifacts = {
            "objective_inspection": (output_dir / "objective_inspection.json").as_posix(),
            "leak_scan": (output_dir / "leak_scan_result.json").as_posix(),
            **diagnostic_artifacts,
        }
    manifest = {
        "evidence_kind": "a100_train_split_overfit_diagnostic"
        if diagnostic_evidence
        else "a100_sft_prediction_eval_smoke",
        "evidence_status": prediction_metadata.get("prediction_status", "unknown"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "base_model": prediction_metadata.get("base_model"),
        "model_source": prediction_metadata.get("model_source", "unknown"),
        "dataset_manifest_id": prediction_metadata.get("dataset_manifest_id"),
        "prediction_artifact_path": prediction_path.as_posix(),
        "prediction_source_kind": prediction_source_kind,
        "prediction_split": prediction_split,
        "overfit_diagnostic": overfit_diagnostic,
        "generalization_claim": generalization_claim,
        "prediction_count": prediction_metadata.get("prediction_count"),
        "metrics_path": metrics_path.as_posix(),
        "sidecars": sidecars,
        "diagnostic_artifacts": diagnostic_artifacts,
        "controlled_smoke_status": smoke_result,
        "leak_scan_result": leak_scan_result,
        "release_status": release_status,
        "claims": {
            "checkpoint_release": False,
            "adapter_release": False,
            "live_browser_benchmark_claim": False,
            "production_readiness_claim": False,
            "generalization_claim": generalization_claim,
            "release_claim": False,
        },
        "artifact_policy": {
            "raw_logs_copied_to_git": False,
            "checkpoints_or_adapters_copied_to_git": False,
            "remote_caches_copied_to_git": False,
            "private_paths_omitted": True,
        },
    }
    write_json(manifest_path, manifest)
    title = (
        "# A100 Train-Split Overfit Diagnostic Evidence"
        if diagnostic_evidence
        else "# A100 SFT Prediction/Eval Smoke Evidence"
    )
    status_line = (
        "Status: train-internal overfit diagnostic evidence. This is not a benchmark, not a release, "
        "and not a live-browser improvement claim."
        if diagnostic_evidence
        else (
            "Status: public-sample prediction/evaluation smoke evidence. "
            "This is not a checkpoint release and not a live-browser benchmark."
        )
    )
    lines = [
        title,
        "",
        status_line,
        "",
        "## Scope",
        "",
        f"- Base model: `{manifest['base_model']}`",
        f"- Model source: `{manifest['model_source']}`",
        f"- Dataset manifest: `{manifest['dataset_manifest_id']}`",
        f"- Prediction source kind: `{prediction_source_kind}`",
        f"- Prediction split: `{prediction_split}`",
        f"- Overfit diagnostic: `{overfit_diagnostic}`",
        f"- Generalization claim: `{generalization_claim}`",
        f"- Release status: `{release_status}`",
        "",
        "## Interpretation",
        "",
        (
            "If `prediction_source_kind` is `public_sample_contract_fixture`, the predictions are deterministic "
            "public-sample contract fixtures used to validate the evidence pipeline. They are not private adapter "
            "model outputs and must not be presented as model-quality evidence."
        ),
        (
            "If `prediction_source_kind` is `private_a100_adapter`, the predictions came from the private A100 "
            "adapter path, but the metrics and controlled smoke results still only describe this bounded public "
            "sample. Failed schema or smoke results must be reported as failures, not hidden behind the existence "
            "of a completed training run."
        ),
        (
            "For a train-internal overfit diagnostic, recovery on `prediction_split=train` can only support "
            "a narrow train-internal sanity check. It does not prove dev/test generalization, production "
            "readiness, checkpoint release, adapter release, or live-browser benchmark improvement. "
            "There is no release claim."
        )
        if diagnostic_evidence
        else "",
        "",
        "## Public Artifacts",
        "",
        f"- Predictions: `{prediction_path.as_posix()}`",
        f"- Metrics: `{metrics_path.as_posix()}`",
        f"- Prompt snapshot: `{sidecars.get('prompt_snapshot', 'not_recorded')}`",
        f"- Raw decoded summary: `{sidecars.get('raw_decoded_summary', 'not_recorded')}`",
        f"- Generation trace: `{sidecars.get('generation_trace', 'not_recorded')}`",
        f"- Objective inspection: `{diagnostic_artifacts.get('objective_inspection', 'not_recorded')}`",
        f"- Leak scan artifact: `{diagnostic_artifacts.get('leak_scan', 'not_recorded')}`",
        f"- Controlled smoke: `{smoke_result.get('notes', 'unknown')}`",
        f"- Leak scan ok: `{bool(leak_scan_result.get('ok'))}`",
        "",
        "## Boundary",
        "",
        (
            "The evidence pack may contain sanitized public-sample contract predictions, aggregate metrics, "
            "controlled smoke status, and leak-scan status. It does not copy raw logs, checkpoints, adapters, "
            "remote caches, private paths, host details, tokens, or private corpus rows into git."
        ),
    ]
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"manifest": manifest_path, "report": report_path}
