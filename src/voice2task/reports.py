from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from voice2task.evaluation import EvaluationResult
from voice2task.io import write_json, write_jsonl
from voice2task.leak_scan import scan_paths
from voice2task.schemas import PRIVATE_IP_RE, PRIVATE_PATH_RE, SECRET_RE

PRIVATE_REPORT_PATH_RE = re.compile(r"(/(?:mnt/data|Users|root|tmp|private)/[^\s\"')]+|data/local-private/[^\s\"')]+)")


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


def write_sft_contract_learning_signal_report(
    diagnostics: dict[str, Any],
    output_dir: Path,
    title: str = "Voice2Task SFT contract learning-signal evidence",
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "sft_contract_learning_signal.json"
    markdown_path = output_dir / "sft_contract_learning_signal.md"
    safe_diagnostics = _sanitize_report_value(diagnostics)
    write_json(json_path, safe_diagnostics)

    summary = safe_diagnostics["summary"]
    pressure = safe_diagnostics["target_pressure"]
    label_mask = safe_diagnostics["label_mask_evidence"]
    prior = safe_diagnostics["prior_repair_evidence"]
    lines = [
        f"# {title}",
        "",
        (
            "This local diagnostic inspects public-sample SFT contract learning signal only. "
            "It does not train, run prediction, download models, load private adapters, or repair outputs."
        ),
        "",
        "## Boundary",
        "",
        "- This is not a model recovery claim.",
        "- This is not a checkpoint release.",
        "- This is not an adapter release.",
        "- This is not held-out or private-corpus generalization evidence.",
        "- This makes no production-readiness claim.",
        "- This is not a live-browser benchmark or benchmark-improvement claim.",
        "",
        "## Summary",
        "",
        f"- Rows inspected: `{summary['row_count']}`",
        f"- Split counts: `{summary['split_counts']}`",
        f"- Task type counts: `{summary['task_type_counts']}`",
        f"- All rows have assistant target span: `{summary['all_rows_have_assistant_target_span']}`",
        f"- True runtime label-mask status: `{summary['true_runtime_label_mask_status']}`",
        "",
        "## Target Pressure",
        "",
        f"- Max training text characters: `{pressure['max_training_text_char_count']}`",
        f"- Max assistant target characters: `{pressure['max_assistant_target_char_count']}`",
        f"- Min assistant target char ratio: `{pressure['min_assistant_target_char_ratio']}`",
        f"- Max assistant target char ratio: `{pressure['max_assistant_target_char_ratio']}`",
        f"- Rows over 2048 chars: `{pressure['rows_over_2048_chars']}`",
        f"- Tokenizer-specific token counts available: `{pressure['tokenizer_specific_token_counts_available']}`",
        "",
        "## Runtime label-mask evidence",
        "",
        f"- Status: `{label_mask['status']}`",
        f"- True label-mask status: `{label_mask['true_label_mask_status']}`",
        f"- Evidence gaps: `{label_mask['evidence_gaps']}`",
        "",
        "## Prior Repair Evidence",
        "",
        f"- Available: `{prior['available']}`",
        f"- Overall interpretation: `{prior['overall_interpretation']}`",
        f"- Split exact match: `{prior['split_exact_match']}`",
        "",
        "## Recommended Next Step",
        "",
        f"- `{safe_diagnostics['recommended_next_step']}`",
        "",
        "## Row Evidence",
        "",
    ]
    for row in safe_diagnostics.get("rows", []):
        lines.extend(
            [
                f"### `{row['row_id']}`",
                "",
                f"- Split: `{row['split']}`",
                f"- Task type: `{row['task_type']}`",
                f"- Route: `{row['route']}`",
                f"- Assistant target span found: `{row['assistant_target_span_found']}`",
                f"- Training text characters: `{row['training_text_char_count']}`",
                f"- Assistant target characters: `{row['assistant_contract_target_char_count']}`",
                f"- Assistant target char ratio: `{row['assistant_target_char_ratio']}`",
                f"- Target fields: `{row['target_top_level_field_count']}`",
                f"- Target slots: `{row['target_slot_count']}`",
                f"- Training text SHA-256: `{row['training_text_sha256']}`",
                f"- Assistant target SHA-256: `{row['assistant_contract_target_sha256']}`",
                "",
            ]
        )

    markdown_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return {"json": json_path, "markdown": markdown_path}


def write_runtime_label_tiny_overfit_diagnostic_report(
    diagnostics: dict[str, Any],
    output_dir: Path,
    title: str = "Voice2Task runtime-label and tiny-overfit diagnostic",
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "runtime_label_tiny_overfit_diagnostic.json"
    markdown_path = output_dir / "runtime_label_tiny_overfit_diagnostic.md"
    safe_diagnostics = _sanitize_report_value(diagnostics)
    write_json(json_path, safe_diagnostics)

    summary = safe_diagnostics["summary"]
    current_manifest = safe_diagnostics["current_manifest"]
    learning = safe_diagnostics["learning_signal_evidence"]
    runtime = safe_diagnostics["runtime_label_evidence"]
    tiny = safe_diagnostics["tiny_overfit_evidence"]
    readiness = safe_diagnostics["tiny_overfit_readiness"]
    prior = safe_diagnostics["prior_repair_evidence"]
    lines = [
        f"# {title}",
        "",
        (
            "This local diagnostic compares public-safe artifacts for the current manifest. "
            "It does not train, run prediction, download models, load private adapters, or repair outputs."
        ),
        "",
        "## Boundary",
        "",
        "- This is not a model recovery claim.",
        "- This is not a checkpoint release.",
        "- This is not an adapter release.",
        "- This is not held-out or private-corpus generalization evidence.",
        "- This makes no production-readiness claim.",
        "- This is not a public full-corpus release claim.",
        "- This is not a live-browser benchmark or benchmark-improvement claim.",
        "- Stale runtime-label or tiny-overfit evidence is prior context only.",
        "",
        "## Summary",
        "",
        f"- Current manifest: `{current_manifest['manifest_id']}`",
        f"- Runtime label status: `{summary['current_runtime_label_status']}`",
        f"- Current true label-mask status: `{summary['current_true_label_mask_status']}`",
        f"- Tiny-overfit evidence status: `{summary['tiny_overfit_status']}`",
        f"- Tiny-overfit readiness: `{summary['tiny_overfit_readiness']}`",
        f"- Recommended next step: `{safe_diagnostics['recommended_next_step']}`",
        "",
        "## Learning Signal Context",
        "",
        f"- Available: `{learning['available']}`",
        f"- Freshness: `{learning['freshness']}`",
        f"- Source manifest: `{learning['source_manifest_id']}`",
        f"- Assistant target spans present: `{learning['all_rows_have_assistant_target_span']}`",
        f"- Learning-signal true label-mask status: `{learning['true_runtime_label_mask_status']}`",
        "",
        "## Prior Repair Evidence",
        "",
        f"- Available: `{prior['available']}`",
        f"- Overall interpretation: `{prior['overall_interpretation']}`",
        f"- Split exact match: `{prior['split_exact_match']}`",
        "",
        "## Runtime Label Evidence",
        "",
        f"- Available: `{runtime['available']}`",
        f"- Freshness: `{runtime['freshness']}`",
        f"- Source manifest: `{runtime['source_manifest_id']}`",
        f"- Current manifest proof: `{runtime['current_manifest_proof']}`",
        f"- Evidence status: `{runtime['evidence_status']}`",
        f"- Runtime check status: `{runtime['runtime_check_status']}`",
        f"- Prior label-mask fields: `{runtime['prior_label_mask_fields']}`",
        f"- Current label-mask fields: `{runtime['current_label_mask_fields']}`",
        f"- Assistant-only loss-mask claim: `{runtime['assistant_only_loss_mask_claim']}`",
        "",
        "## Tiny-Overfit Evidence",
        "",
        f"- Available: `{tiny['available']}`",
        f"- Freshness: `{tiny['freshness']}`",
        f"- Source manifest: `{tiny['source_manifest_id']}`",
        f"- Current manifest proof: `{tiny['current_manifest_proof']}`",
        f"- Overfit diagnostic: `{tiny['overfit_diagnostic']}`",
        f"- Prediction split: `{tiny['prediction_split']}`",
        f"- Training rows used: `{tiny['training_rows_used']}`",
        f"- Assistant-only objective: `{tiny['assistant_only_objective']}`",
        "",
        "## Readiness",
        "",
        f"- Status: `{readiness['status']}`",
        f"- Reason: `{readiness['reason']}`",
        "",
        "## Artifact Policy",
        "",
    ]
    for name, value in sorted(safe_diagnostics["artifact_policy"].items()):
        lines.append(f"- `{name}`: `{value}`")

    markdown_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return {"json": json_path, "markdown": markdown_path}


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


def _runtime_manifest_freshness(metadata: dict[str, Any], expected_manifest_id: str | None) -> str:
    actual_manifest_id = str(metadata.get("dataset_manifest_id", "unknown"))
    if not expected_manifest_id:
        return "expected_manifest_not_supplied"
    if actual_manifest_id == expected_manifest_id:
        return "fresh_current_manifest"
    return "stale_manifest_mismatch"


def _current_manifest_runtime_label_proof(
    *,
    evidence_status: str,
    manifest_freshness: str,
    metadata: dict[str, Any],
) -> bool:
    return (
        evidence_status == "labels_inspected"
        and manifest_freshness == "fresh_current_manifest"
        and metadata.get("inspection_status") == "inspectable"
        and metadata.get("label_tensor_available") is True
        and metadata.get("true_label_mask_status") == "inspectable"
    )


def _assistant_only_loss_mask_observed(*, current_manifest_proof: bool, metadata: dict[str, Any]) -> bool:
    return (
        current_manifest_proof
        and metadata.get("prompt_tokens_masked") is True
        and metadata.get("assistant_tokens_carry_loss") is True
    )


def _runtime_label_recommended_next_step(
    *,
    evidence_status: str,
    manifest_freshness: str,
    current_manifest_proof: bool,
    assistant_only_loss_mask_observed: bool,
) -> str:
    if manifest_freshness == "stale_manifest_mismatch":
        return "run_fresh_current_manifest_runtime_label_check"
    if evidence_status not in {"labels_inspected", "labels_available_but_not_real_training_proof"}:
        return "resolve_runtime_label_check_blocker"
    if not current_manifest_proof:
        return "establish_real_current_manifest_runtime_label_proof"
    if not assistant_only_loss_mask_observed:
        return "fix_runtime_label_masking_before_tiny_overfit"
    return "run_1_to_3_row_current_manifest_tiny_overfit_probe"


def write_runtime_label_provenance_check_evidence_pack(
    *,
    runtime_metadata: dict[str, Any],
    output_dir: Path,
    prior_artifacts: dict[str, str] | None = None,
    leak_scan_result: dict[str, Any] | None = None,
    expected_manifest_id: str | None = None,
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
    manifest_freshness = _runtime_manifest_freshness(metadata, expected_manifest_id)
    if manifest_freshness == "stale_manifest_mismatch":
        evidence_status = "stale_manifest_mismatch"
    current_manifest_proof = _current_manifest_runtime_label_proof(
        evidence_status=evidence_status,
        manifest_freshness=manifest_freshness,
        metadata=metadata,
    )
    assistant_only_loss_mask_observed = _assistant_only_loss_mask_observed(
        current_manifest_proof=current_manifest_proof,
        metadata=metadata,
    )
    recommended_next_step = _runtime_label_recommended_next_step(
        evidence_status=evidence_status,
        manifest_freshness=manifest_freshness,
        current_manifest_proof=current_manifest_proof,
        assistant_only_loss_mask_observed=assistant_only_loss_mask_observed,
    )
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
        "expected_manifest_id": expected_manifest_id or "not_supplied",
        "manifest_freshness": manifest_freshness,
        "current_manifest_runtime_label_proof": current_manifest_proof,
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
        "assistant_only_loss_mask_claim": assistant_only_loss_mask_observed,
        "evidence_gaps": _sanitize_report_value(metadata.get("evidence_gaps", [])),
        "loss_interpretation": _sanitize_report_value(metadata.get("loss_interpretation", {})),
        "prior_artifacts": combined_prior,
        "prior_artifacts_role": "historical_context_only" if combined_prior else "none",
        "recommended_next_step": recommended_next_step,
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
        f"- Expected manifest: `{summary['expected_manifest_id']}`",
        f"- Manifest freshness: `{summary['manifest_freshness']}`",
        f"- Current-manifest runtime label proof: `{summary['current_manifest_runtime_label_proof']}`",
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
        f"- Recommended next step: `{summary['recommended_next_step']}`",
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
        lines.append("- Stale prior artifacts are historical context only.")
        for name, path in sorted(prior.items()):
            lines.append(f"- `{name}`: `{path}`")
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Objective Limitations",
            "",
            "- If `prompt_tokens_masked=false`, this evidence does not support an assistant-only loss-mask claim.",
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


def write_heldout_family_strategy_report(
    diagnostics: dict[str, Any],
    output_dir: Path,
    title: str = "Voice2Task held-out family strategy diagnosis",
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "heldout_family_strategy_diagnosis.json"
    markdown_path = output_dir / "heldout_family_strategy_diagnosis.md"
    safe_diagnostics = _sanitize_report_value(diagnostics)
    write_json(json_path, safe_diagnostics)

    summary = safe_diagnostics["summary"]
    strategy = safe_diagnostics["strategy_recommendation"]
    dpo_signal = safe_diagnostics["dpo_hard_negative_signal"]
    lines = [
        f"# {title}",
        "",
        (
            "This local public-sample diagnosis explains why the current tiny adapter has zero held-out "
            "strict exact match. It is not blind data scaling, not a model recovery claim, and not "
            "held-out generalization evidence."
        ),
        "",
        "## Boundary",
        "",
        "- This does not train, run prediction, generate data, or run DPO.",
        "- This is not a checkpoint release.",
        "- This is not an adapter release.",
        "- This is not a model recovery claim.",
        "- This makes no production-readiness or live-browser benchmark claim.",
        "- Semantic equivalence is not promoted to the primary metric.",
        "",
        "## Summary",
        "",
        f"- Source manifest: `{safe_diagnostics['source_manifest']['manifest_id']}`",
        f"- Held-out strict exact match: `{summary['heldout_contract_exact_match']}`",
        f"- Tiny training subset family count: `{summary['tiny_training_subset_family_count']}`",
        f"- Held-out residual family count: `{summary['heldout_residual_family_count']}`",
        f"- Broad data scaling recommended now: `{summary['broad_data_scaling_recommended']}`",
        f"- Recommended next step: `{summary['recommended_next_step']}`",
        "",
        "## Strategy",
        "",
        f"- Primary: `{strategy['primary']}`",
        f"- Requires user confirmation: `{strategy['requires_user_confirmation']}`",
        "- Interpretation: targeted family coverage should be tested before broad data scaling.",
        "",
        "## Rationale",
        "",
    ]
    for reason in strategy.get("rationale", []):
        lines.append(f"- {reason}")

    lines.extend(["", "## Held-out Residual Families", ""])
    for entry in safe_diagnostics.get("heldout_family_residuals", []):
        lines.extend(
            [
                f"### `{entry['source_family_id']}`",
                "",
                f"- Split: `{entry['split']}`",
                f"- Contract family: `{entry['contract_family_key']}`",
                f"- Rows: `{entry['row_count']}`",
                f"- Train analog family: `{entry['train_analog_family_id']}`",
                f"- Train analog rows: `{entry['train_analog_row_count']}`",
                f"- Tiny subset rows: `{entry['tiny_subset_row_count']}`",
                f"- Schema-invalid predictions: `{entry['schema_invalid_prediction_count']}`",
                f"- Field mismatches: `{entry['field_mismatch_counts']}`",
                f"- DPO hard-negative category: `{entry['dpo_hard_negative_category']}`",
                f"- Strategy bucket: `{entry['strategy_bucket']}`",
                "",
            ]
        )

    lines.extend(
        [
            "## DPO Hard-negative Signal",
            "",
            f"- Categories available: `{dpo_signal['categories_available_for_residual_families']}`",
            f"- Category count: `{dpo_signal['category_count']}`",
            f"- Execute DPO in this phase: `{dpo_signal['execute_dpo_in_this_phase']}`",
            "",
            "## Candidate Next Phases",
            "",
        ]
    )
    for phase in strategy.get("candidate_next_phases", []):
        lines.append(f"- `{phase}`")

    markdown_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return {"json": json_path, "markdown": markdown_path}


def write_targeted_slot_value_residual_report(
    diagnostics: dict[str, Any],
    output_dir: Path,
    title: str = "Voice2Task targeted slot value residual diagnosis",
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "targeted_slot_value_residual_diagnosis.json"
    markdown_path = output_dir / "targeted_slot_value_residual_diagnosis.md"
    manifest_path = output_dir / "manifest.json"
    safe_diagnostics = _sanitize_report_value(diagnostics)
    write_json(json_path, safe_diagnostics)

    manifest = {
        "evidence_kind": safe_diagnostics["evidence_kind"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_targeted_probe": safe_diagnostics["source_targeted_probe"],
        "summary": safe_diagnostics["summary"],
        "aggregates": safe_diagnostics["aggregates"],
        "claims": safe_diagnostics["claims"],
        "artifact_policy": {
            "raw_logs_copied_to_git": False,
            "checkpoints_or_adapters_copied_to_git": False,
            "private_overrides_copied_to_git": False,
            "private_paths_omitted": True,
            "host_details_omitted": True,
            "ssh_details_omitted": True,
            "private_corpus_rows_omitted": True,
            "prediction_repair_or_replacement": False,
            "evaluator_metric_change": False,
        },
        "diagnostic_artifacts": {
            "diagnosis": (
                "reports/public-sample/targeted-slot-value-residual-diagnosis/"
                "targeted_slot_value_residual_diagnosis.json"
            ),
            "markdown": (
                "reports/public-sample/targeted-slot-value-residual-diagnosis/"
                "targeted_slot_value_residual_diagnosis.md"
            ),
            "manifest": "reports/public-sample/targeted-slot-value-residual-diagnosis/manifest.json",
        },
    }
    write_json(manifest_path, manifest)

    summary = safe_diagnostics["summary"]
    aggregates = safe_diagnostics["aggregates"]
    lines = [
        f"# {title}",
        "",
        (
            "This local public-sample diagnosis explains the remaining targeted-family held-out residuals. "
            "It is not broad scaling yet, not DPO, not prediction repair, and not a model recovery claim."
        ),
        "",
        "## Boundary",
        "",
        "- strict `contract_exact_match` remains primary.",
        "- Soft slot F1 and semantic equivalence remain diagnostic-only.",
        "- Predictions are not repaired, replaced, rewritten, or normalized.",
        "- Evaluator rules and metrics are not relaxed.",
        (
            "- This is not a checkpoint release, adapter release, production-readiness claim, "
            "or live-browser benchmark claim."
        ),
        "",
        "## Summary",
        "",
        f"- Strict exact match: `{summary['strict_contract_exact_match']}`",
        f"- Structure metrics already correct: `{summary['json_schema_task_route_safety_confirmation_ok']}`",
        f"- Residual rows: `{summary['residual_row_count']}`",
        f"- Residual fields: `{summary['residual_field_counts']}`",
        f"- Drift buckets: `{summary['residual_drift_bucket_counts']}`",
        f"- Broad scaling recommended now: `{summary['broad_scaling_recommended_now']}`",
        f"- DPO recommended now: `{summary['dpo_recommended_now']}`",
        f"- Recommended next step: `{summary['recommended_next_step']}`",
        "",
        "## Aggregates",
        "",
        f"- By split: `{aggregates['by_split']}`",
        f"- By field path: `{aggregates['by_field_path']}`",
        f"- By source family: `{aggregates['by_source_family']}`",
        f"- By drift bucket: `{aggregates['by_drift_bucket']}`",
        "",
        "## Residual Rows",
        "",
    ]
    for entry in safe_diagnostics.get("residuals", []):
        lines.extend(
            [
                f"### `{entry['split']} / {entry['row_id']}`",
                "",
                f"- Source family: `{entry['source_family_id']}`",
                f"- Field: `{entry['field_path']}`",
                f"- Drift bucket: `{entry['drift_bucket']}`",
                f"- Gold: `{entry['gold_value_summary']}`",
                f"- Prediction: `{entry['predicted_value_summary']}`",
                "",
            ]
        )

    lines.extend(
        [
            "## Recommended Next Step",
            "",
            (
                "Design a bounded slot value generalization/data-design phase before broad scaling or DPO. "
                "The next work should target canonical slot values and command wording, while preserving strict "
                "`contract_exact_match` as the primary metric."
            ),
        ]
    )
    markdown_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return {"json": json_path, "markdown": markdown_path, "manifest": manifest_path}


def write_merged_slot_value_residual_report(
    diagnostics: dict[str, Any],
    output_dir: Path,
    title: str = "Voice2Task merged slot value residual diagnosis",
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "merged_slot_value_residual_diagnosis.json"
    markdown_path = output_dir / "merged_slot_value_residual_diagnosis.md"
    manifest_path = output_dir / "manifest.json"
    safe_diagnostics = _sanitize_report_value(diagnostics)
    write_json(json_path, safe_diagnostics)

    manifest = {
        "evidence_kind": safe_diagnostics["evidence_kind"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_merged_eval": safe_diagnostics["source_merged_eval"],
        "summary": safe_diagnostics["summary"],
        "aggregates": safe_diagnostics["aggregates"],
        "claims": safe_diagnostics["claims"],
        "artifact_policy": {
            "raw_predictions_copied_to_git": False,
            "raw_logs_copied_to_git": False,
            "checkpoints_or_adapters_copied_to_git": False,
            "private_overrides_copied_to_git": False,
            "private_paths_omitted": True,
            "host_details_omitted": True,
            "ssh_details_omitted": True,
            "private_corpus_rows_omitted": True,
            "prediction_repair_or_replacement": False,
            "evaluator_metric_change": False,
            "slot_normalization": False,
        },
        "diagnostic_artifacts": {
            "diagnosis": (
                "reports/public-sample/merged-slot-value-residual-diagnosis/"
                "merged_slot_value_residual_diagnosis.json"
            ),
            "markdown": (
                "reports/public-sample/merged-slot-value-residual-diagnosis/"
                "merged_slot_value_residual_diagnosis.md"
            ),
            "manifest": "reports/public-sample/merged-slot-value-residual-diagnosis/manifest.json",
        },
    }
    write_json(manifest_path, manifest)

    summary = safe_diagnostics["summary"]
    aggregates = safe_diagnostics["aggregates"]
    lines = [
        f"# {title}",
        "",
        (
            "This diagnosis explains the remaining merged slot-value dev/test strict residuals. "
            "It is not training, not prediction rerun, not held-out recovery, and not evaluator relaxation."
        ),
        "",
        "## Boundary",
        "",
        "- strict `contract_exact_match` remains primary.",
        "- Strict `slot_f1` remains authoritative for slot scoring.",
        "- Soft slot F1 is internal diagnostic-only, not semantic-equivalence scoring.",
        "- Predictions are not repaired, replaced, rewritten, normalized, or re-scored.",
        (
            "- This is not a checkpoint release, adapter release, production-readiness claim, "
            "or live-browser benchmark claim."
        ),
        "",
        "## Summary",
        "",
        f"- Strict exact match: `{summary['strict_contract_exact_match']}`",
        f"- Strict slot F1: `{summary['strict_slot_f1']}`",
        f"- Soft slot F1: `{summary['soft_slot_f1']}`",
        f"- Soft slot F1 primary metric: `{summary['soft_slot_f1_primary_metric']}`",
        f"- Residual rows: `{summary['residual_row_count']}`",
        f"- Source count consistency: `{summary['source_count_consistency']}`",
        f"- Residual fields: `{summary['residual_field_counts']}`",
        f"- Residual categories: `{summary['residual_category_counts']}`",
        f"- Recommended next step: `{summary['recommended_next_step']}`",
        "",
        "## Aggregates",
        "",
        f"- By split residual rows: `{aggregates['by_split_residual_rows']}`",
        f"- By split residual fields: `{aggregates['by_split_residual_fields']}`",
        f"- By field path: `{aggregates['by_field_path']}`",
        f"- By category: `{aggregates['by_category']}`",
        f"- By source family: `{aggregates['by_source_family']}`",
        "",
        "## Residual Fields",
        "",
    ]
    for entry in safe_diagnostics.get("residuals", []):
        lines.extend(
            [
                f"### `{entry['split']} / {entry['row_id']} / {entry['field_path']}`",
                "",
                f"- Source family: `{entry['source_family_id']}`",
                f"- Task family: `{entry['task_family']}`",
                f"- Category: `{entry['category']}`",
                f"- Mismatch: `{entry['mismatch_category']}`",
                f"- Gold value: `{entry.get('gold_value')}`",
                f"- Prediction value: `{entry.get('predicted_value')}`",
                f"- Gold: `{entry['gold_value_summary']}`",
                f"- Prediction: `{entry['predicted_value_summary']}`",
                "",
            ]
        )

    lines.extend(
        [
            "## Recommended Next Step",
            "",
            (
                "Review the residual buckets before any data, training, gold-policy, or evaluator change. "
                "If the next action changes those policies, it should be a separate OpenSpec phase."
            ),
        ]
    )
    markdown_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return {"json": json_path, "markdown": markdown_path, "manifest": manifest_path}


def write_formal_heldout_residual_family_report(
    diagnostics: dict[str, Any],
    output_dir: Path,
    title: str = "Voice2Task formal held-out residual family diagnosis",
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "formal_heldout_residual_family_diagnosis.json"
    markdown_path = output_dir / "formal_heldout_residual_family_diagnosis.md"
    manifest_path = output_dir / "manifest.json"
    safe_diagnostics = _sanitize_report_value(diagnostics)
    write_json(json_path, safe_diagnostics)

    manifest = {
        "evidence_kind": safe_diagnostics["evidence_kind"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_formal_heldout_evidence": safe_diagnostics["source_formal_heldout_evidence"],
        "summary": safe_diagnostics["summary"],
        "aggregates": safe_diagnostics["aggregates"],
        "claims": safe_diagnostics["claims"],
        "artifact_policy": {
            "raw_predictions_copied_to_git": False,
            "raw_logs_copied_to_git": False,
            "checkpoints_or_adapters_copied_to_git": False,
            "private_overrides_copied_to_git": False,
            "private_paths_omitted": True,
            "host_details_omitted": True,
            "ssh_details_omitted": True,
            "private_corpus_rows_omitted": True,
            "prediction_repair_or_replacement": False,
            "evaluator_metric_change": False,
            "slot_normalization": False,
            "data_generation": False,
            "training_run": False,
            "dpo_run": False,
        },
        "diagnostic_artifacts": {
            "diagnosis": (
                "reports/public-sample/formal-heldout-residual-family-diagnosis/"
                "formal_heldout_residual_family_diagnosis.json"
            ),
            "markdown": (
                "reports/public-sample/formal-heldout-residual-family-diagnosis/"
                "formal_heldout_residual_family_diagnosis.md"
            ),
            "manifest": "reports/public-sample/formal-heldout-residual-family-diagnosis/manifest.json",
        },
    }
    write_json(manifest_path, manifest)

    summary = safe_diagnostics["summary"]
    aggregates = safe_diagnostics["aggregates"]
    lines = [
        f"# {title}",
        "",
        (
            "This diagnosis groups the current formal public held-out dev/test strict residuals. "
            "It is not training, not a prediction rerun, not held-out recovery, and not evaluator relaxation."
        ),
        "",
        "## Boundary",
        "",
        "- strict `contract_exact_match` remains primary.",
        "- Strict `slot_f1` remains authoritative for slot scoring.",
        "- `slot_f1_soft` is internal diagnostic-only, not semantic-equivalence scoring.",
        "- Predictions are not repaired, replaced, rewritten, normalized, or re-scored.",
        "- No new data, SFT, DPO, A100 job, checkpoint release, or adapter release is performed.",
        "",
        "## Summary",
        "",
        f"- Source evidence: `{safe_diagnostics['source_formal_heldout_evidence']}`",
        f"- Strict exact match: `{summary['strict_contract_exact_match']}`",
        f"- Strict slot F1: `{summary['strict_slot_f1']}`",
        f"- Soft slot F1: `{summary['soft_slot_f1']}`",
        f"- Soft slot F1 primary metric: `{summary['soft_slot_f1_primary_metric']}`",
        f"- Residual rows: `{summary['residual_row_count']}`",
        f"- Source count consistency: `{summary['source_count_consistency']}`",
        f"- Residual fields: `{summary['residual_field_counts']}`",
        f"- Residual categories: `{summary['residual_category_counts']}`",
        f"- Recommended next step: `{summary['recommended_next_step']}`",
        "",
        "## Aggregates",
        "",
        f"- By split residual rows: `{aggregates['by_split_residual_rows']}`",
        f"- By split residual fields: `{aggregates['by_split_residual_fields']}`",
        f"- By field path: `{aggregates['by_field_path']}`",
        f"- By category: `{aggregates['by_category']}`",
        f"- By source family: `{aggregates['by_source_family']}`",
        f"- By task family: `{aggregates['by_task_family']}`",
        "",
        "## Residual Fields",
        "",
    ]
    for entry in safe_diagnostics.get("residuals", []):
        lines.extend(
            [
                f"### `{entry['split']} / {entry['row_id']} / {entry['field_path']}`",
                "",
                f"- Source family: `{entry['source_family_id']}`",
                f"- Task family: `{entry['task_family']}`",
                f"- Category: `{entry['category']}`",
                f"- Mismatch: `{entry['mismatch_category']}`",
                f"- Gold value: `{entry.get('gold_value')}`",
                f"- Prediction value: `{entry.get('predicted_value')}`",
                f"- Gold: `{entry['gold_value_summary']}`",
                f"- Prediction: `{entry['predicted_value_summary']}`",
                "",
            ]
        )

    lines.extend(
        [
            "## Recommended Next Step",
            "",
            (
                "Use this residual grouping to choose one bounded follow-up. Do not add data, train, rerun DPO, "
                "or change evaluator behavior until the target residual family and acceptance boundary are explicit."
            ),
        ]
    )
    markdown_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return {"json": json_path, "markdown": markdown_path, "manifest": manifest_path}


def write_formal_heldout_remediation_target_selection_report(
    selection: dict[str, Any],
    output_dir: Path,
    title: str = "Voice2Task formal held-out remediation target selection",
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "formal_heldout_remediation_target_selection.json"
    markdown_path = output_dir / "formal_heldout_remediation_target_selection.md"
    manifest_path = output_dir / "manifest.json"
    safe_selection = _sanitize_report_value(selection)
    write_json(json_path, safe_selection)

    manifest = {
        "evidence_kind": safe_selection["evidence_kind"],
        "selection_status": safe_selection["selection_status"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_residual_diagnosis": safe_selection["source_residual_diagnosis"],
        "summary": safe_selection["summary"],
        "execution_scope": safe_selection["execution_scope"],
        "claims": safe_selection["claims"],
        "artifact_policy": {
            "raw_predictions_copied_to_git": False,
            "raw_logs_copied_to_git": False,
            "checkpoints_or_adapters_copied_to_git": False,
            "private_overrides_copied_to_git": False,
            "private_paths_omitted": True,
            "host_details_omitted": True,
            "ssh_details_omitted": True,
            "private_corpus_rows_omitted": True,
            "prediction_repair_or_replacement": False,
            "evaluator_metric_change": False,
            "gold_policy_change": False,
            "slot_normalization": False,
            "data_generation": False,
            "training_run": False,
            "dpo_run": False,
            "a100_job": False,
        },
        "diagnostic_artifacts": {
            "selection": (
                "reports/public-sample/formal-heldout-remediation-target-selection/"
                "formal_heldout_remediation_target_selection.json"
            ),
            "markdown": (
                "reports/public-sample/formal-heldout-remediation-target-selection/"
                "formal_heldout_remediation_target_selection.md"
            ),
            "manifest": "reports/public-sample/formal-heldout-remediation-target-selection/manifest.json",
        },
    }
    write_json(manifest_path, manifest)

    summary = safe_selection["summary"]
    selected = safe_selection["selection"]["selected"]
    lines = [
        f"# {title}",
        "",
        (
            "This report selects the first bounded remediation target from the current formal public "
            "held-out residual-family diagnosis. It is not training, not new data generation, not a "
            "prediction rerun, not model recovery, and not evaluator relaxation."
        ),
        "",
        "## Boundary",
        "",
        "- strict `contract_exact_match` remains primary.",
        "- Strict `slot_f1` remains authoritative for slot scoring.",
        "- `slot_f1_soft` remains internal diagnostic-only.",
        "- No raw prediction stream is copied as the planning artifact.",
        "- No A100 job, SFT, DPO, new data, gold rewrite, or metric change is performed.",
        "",
        "## Selected Target",
        "",
        f"- Selected target: `{summary['selected_target']}`",
        f"- Selected task family: `{summary['selected_task_family']}`",
        f"- Residual rows: `{summary['selected_residual_row_count']}`",
        f"- Residual fields: `{summary['selected_residual_field_count']}`",
        f"- Recommended next change: `{summary['recommended_next_change']}`",
        f"- Recommended next step: `{summary['recommended_next_step']}`",
        f"- Source count consistency: `{summary['source_count_consistency']}`",
        "",
        "## Why This Target",
        "",
    ]
    for reason in safe_selection["selection"].get("rationale", []):
        lines.append(f"- {reason}")
    lines.extend(
        [
            "",
            "## Selected Field Distribution",
            "",
            f"- Rows by split: `{selected['residual_rows_by_split']}`",
            f"- Field counts: `{selected['residual_field_counts']}`",
            "",
            "## Deferred Adjacent Targets",
            "",
        ]
    )
    for target in safe_selection["selection"].get("deferred_targets", []):
        lines.append(
            "- "
            f"`{target['short_name']}` / `{target['task_family']}` "
            f"({target['residual_row_count']} rows): {target['reason']}"
        )
    lines.extend(["", "## Ranked Families", ""])
    for item in safe_selection.get("ranked_families", []):
        lines.append(
            "- "
            f"`{item['short_name']}` / `{item['task_family']}`: "
            f"{item['residual_row_count']} rows, {item['residual_field_count']} fields, "
            f"fields `{item['residual_field_counts']}`"
        )
    lines.extend(["", "## Representative Sanitized Examples", ""])
    for example in selected.get("representative_examples", []):
        lines.append(
            "- "
            f"`{example['split']} / {example['row_id']} / {example['field_path']}`: "
            f"gold {example['gold_value_summary']}; prediction {example['predicted_value_summary']}"
        )
    lines.extend(
        [
            "",
            "## Recommended Next Step",
            "",
            (
                "Open a new bounded OpenSpec phase for the selected target. That later phase should decide "
                "whether the fix is prompt/policy clarification, targeted public-safe data design, or a "
                "training rerun. This report alone does not authorize those changes."
            ),
        ]
    )
    markdown_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return {"json": json_path, "markdown": markdown_path, "manifest": manifest_path}


def write_form_fill_remediation_plan_report(
    diagnosis: dict[str, Any],
    output_dir: Path,
    title: str = "Voice2Task form-fill remediation plan diagnosis",
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "form_fill_remediation_plan.json"
    markdown_path = output_dir / "form_fill_remediation_plan.md"
    manifest_path = output_dir / "manifest.json"
    safe_diagnosis = _sanitize_report_value(diagnosis)
    write_json(json_path, safe_diagnosis)

    manifest = {
        "evidence_kind": safe_diagnosis["evidence_kind"],
        "remediation_status": safe_diagnosis["remediation_status"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_target_selection": safe_diagnosis["source_target_selection"],
        "source_residual_diagnosis": safe_diagnosis["source_residual_diagnosis"],
        "summary": safe_diagnosis["summary"],
        "acceptance_boundary": safe_diagnosis["acceptance_boundary"],
        "execution_scope": safe_diagnosis["execution_scope"],
        "claims": safe_diagnosis["claims"],
        "artifact_policy": {
            "raw_predictions_copied_to_git": False,
            "raw_logs_copied_to_git": False,
            "checkpoints_or_adapters_copied_to_git": False,
            "private_overrides_copied_to_git": False,
            "private_paths_omitted": True,
            "host_details_omitted": True,
            "ssh_details_omitted": True,
            "private_corpus_rows_omitted": True,
            "prediction_repair_or_replacement": False,
            "evaluator_metric_change": False,
            "gold_policy_change": False,
            "slot_normalization": False,
            "data_generation": False,
            "training_run": False,
            "dpo_run": False,
            "a100_job": False,
        },
        "diagnostic_artifacts": {
            "diagnosis": "reports/public-sample/form-fill-remediation-plan/form_fill_remediation_plan.json",
            "markdown": "reports/public-sample/form-fill-remediation-plan/form_fill_remediation_plan.md",
            "manifest": "reports/public-sample/form-fill-remediation-plan/manifest.json",
        },
    }
    write_json(manifest_path, manifest)

    summary = safe_diagnosis["summary"]
    lines = [
        f"# {title}",
        "",
        (
            "This report is a plan-only diagnosis for the selected `form_fill` formal held-out residuals. "
            "It does not generate data, change gold labels, launch training, rerun predictions, or relax "
            "evaluator metrics."
        ),
        "",
        "## Boundary",
        "",
        "- strict `contract_exact_match` remains primary.",
        "- Strict `slot_f1` remains authoritative for slot scoring.",
        "- `slot_f1_soft` remains diagnostic-only.",
        "- No current public held-out split is modified.",
        "- Any future data design, training, DPO, or A100 work needs a separate confirmed phase.",
        "",
        "## Summary",
        "",
        f"- Target: `{summary['target']}`",
        f"- Task family: `{summary['target_task_family']}`",
        f"- Residual rows: `{summary['residual_row_count']}`",
        f"- Residual fields: `{summary['residual_field_count']}`",
        f"- Bucket field counts: `{summary['bucket_field_counts']}`",
        f"- Bucket row counts: `{summary['bucket_row_counts']}`",
        f"- Field counts: `{summary['by_field_path']}`",
        f"- Count consistency: `{summary['count_consistency']}`",
        f"- Recommended strategy: `{summary['recommended_strategy']}`",
        f"- Recommended next change: `{summary['recommended_next_change']}`",
        f"- Training recommended now: `{summary['training_recommended_now']}`",
        f"- DPO recommended now: `{summary['dpo_recommended_now']}`",
        f"- Evaluator change recommended now: `{summary['evaluator_change_recommended_now']}`",
        "",
        "## Remediation Buckets",
        "",
    ]
    for bucket in safe_diagnosis.get("remediation_buckets", []):
        lines.extend(
            [
                f"### `{bucket['bucket']}`",
                "",
                f"- Residual rows: `{bucket['residual_row_count']}`",
                f"- Residual fields: `{bucket['residual_field_count']}`",
                f"- By split: `{bucket['by_split']}`",
                f"- By field path: `{bucket['by_field_path']}`",
                f"- By source family: `{bucket['by_source_family']}`",
                "",
                "Representative examples:",
            ]
        )
        for example in bucket.get("representative_examples", []):
            lines.append(
                "- "
                f"`{example['split']} / {example['row_id']} / {example['field_path']}`: "
                f"gold {example['gold_value_summary']}; prediction {example['predicted_value_summary']}"
            )
        lines.append("")
    lines.extend(
        [
            "## Recommended Next Step",
            "",
            (
                "Open a new bounded case-design phase for `form_fill`. That phase can propose reviewed "
                "public-safe examples or prompt/policy wording, but this diagnosis does not authorize "
                "materialization, training, DPO, or evaluator changes."
            ),
        ]
    )
    markdown_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return {"json": json_path, "markdown": markdown_path, "manifest": manifest_path}


def write_form_fill_remediation_case_design_report(
    design: dict[str, Any],
    output_dir: Path,
    title: str = "Voice2Task form-fill remediation case design",
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "form_fill_remediation_case_design.json"
    markdown_path = output_dir / "form_fill_remediation_case_design.md"
    manifest_path = output_dir / "manifest.json"
    safe_design = _sanitize_report_value(design)
    write_json(json_path, safe_design)

    manifest = {
        "evidence_kind": safe_design["evidence_kind"],
        "design_status": safe_design["design_status"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_remediation_plan": safe_design["source_remediation_plan"],
        "summary": safe_design["summary"],
        "acceptance_boundary": safe_design["acceptance_boundary"],
        "execution_scope": safe_design["execution_scope"],
        "claims": safe_design["claims"],
        "artifact_policy": {
            "new_data_generated": False,
            "seed_traces_modified": False,
            "public_sample_modified": False,
            "public_heldout_modified": False,
            "gold_policy_change": False,
            "training_run": False,
            "dpo_run": False,
            "prediction_run": False,
            "a100_job": False,
            "evaluator_metric_change": False,
            "slot_normalization": False,
            "prediction_repair_or_replacement": False,
            "raw_predictions_copied_to_git": False,
            "raw_logs_copied_to_git": False,
            "checkpoints_or_adapters_copied_to_git": False,
            "private_overrides_copied_to_git": False,
            "private_paths_omitted": True,
            "host_details_omitted": True,
            "ssh_details_omitted": True,
            "private_corpus_rows_omitted": True,
        },
        "diagnostic_artifacts": {
            "design": (
                "reports/public-sample/form-fill-remediation-case-design/"
                "form_fill_remediation_case_design.json"
            ),
            "markdown": (
                "reports/public-sample/form-fill-remediation-case-design/"
                "form_fill_remediation_case_design.md"
            ),
            "manifest": "reports/public-sample/form-fill-remediation-case-design/manifest.json",
        },
    }
    write_json(manifest_path, manifest)

    summary = safe_design["summary"]
    lines = [
        f"# {title}",
        "",
        (
            "This is design-only evidence for a later `form_fill` remediation phase. It does not "
            "materialize seed rows, modify public sample splits, change held-out gold labels, launch "
            "training, rerun predictions, or relax evaluator metrics."
        ),
        "",
        "## Boundary",
        "",
        "- strict `contract_exact_match` remains primary.",
        "- Strict `slot_f1` remains authoritative for slot scoring.",
        "- `slot_f1_soft` remains diagnostic-only.",
        "- Candidate cases require user review before materialization.",
        "- Any future dataset, SFT, DPO, prediction, or A100 phase needs separate confirmation.",
        "",
        "## Summary",
        "",
        f"- Target: `{summary['target']}`",
        f"- Source residual rows: `{summary['source_residual_row_count']}`",
        f"- Source residual fields: `{summary['source_residual_field_count']}`",
        f"- Case groups: `{summary['case_group_count']}`",
        f"- Candidate cases: `{summary['candidate_case_count']}`",
        f"- Covered bucket field counts: `{summary['covered_bucket_field_counts']}`",
        f"- Public sample modified: `{summary['public_sample_modified']}`",
        f"- New data generated: `{summary['new_data_generated']}`",
        f"- Recommended next step: `{summary['recommended_next_step']}`",
        "",
        "## Policy Guidance",
        "",
    ]
    for item in safe_design.get("policy_guidance", []):
        lines.extend(
            [
                f"### `{item['guidance_id']}`",
                "",
                f"- Source bucket: `{item['source_bucket']}`",
                f"- Guidance: {item['guidance']}",
                f"- Rationale: {item['review_rationale']}",
                "",
            ]
        )

    lines.extend(["## Candidate Case Groups", ""])
    for group in safe_design.get("case_groups", []):
        lines.extend(
            [
                f"### `{group['case_group_id']}`",
                "",
                f"- Source bucket: `{group['source_bucket']}`",
                f"- Source bucket rows: `{group['source_bucket_row_count']}`",
                f"- Source bucket fields: `{group['source_bucket_field_count']}`",
                f"- Source field paths: `{group['source_field_paths']}`",
                f"- Purpose: {group['case_purpose']}",
                f"- Recommended split role: `{group['recommended_split_role']}`",
                f"- Requires user review before materialization: `{group['materialization_requires_user_review']}`",
                "",
                "Candidate cases:",
            ]
        )
        for case in group.get("candidate_cases", []):
            lines.append(
                "- "
                f"`{case['case_id']}`: {case['input_intent']} -> "
                f"`{case['expected_normalized_command_pattern']}`, slots `{case['expected_slots']}`"
            )
        lines.append("")

    lines.extend(
        [
            "## Recommended Next Step",
            "",
            (
                "Review these case groups. If accepted, open a later bounded OpenSpec change to materialize "
                "the reviewed cases into an independent candidate dataset. Do not merge them into active "
                "held-out splits or start training from this design artifact alone."
            ),
        ]
    )
    markdown_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return {"json": json_path, "markdown": markdown_path, "manifest": manifest_path}


def write_slot_value_generalization_case_design_report(
    diagnostics: dict[str, Any],
    output_dir: Path,
    title: str = "Voice2Task slot value generalization case design",
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "slot_value_generalization_case_design.json"
    markdown_path = output_dir / "slot_value_generalization_case_design.md"
    manifest_path = output_dir / "manifest.json"
    safe_diagnostics = _sanitize_report_value(diagnostics)
    write_json(json_path, safe_diagnostics)

    manifest = {
        "evidence_kind": safe_diagnostics["evidence_kind"],
        "design_status": safe_diagnostics["design_status"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_residual_diagnosis": safe_diagnostics["source_residual_diagnosis"],
        "summary": safe_diagnostics["summary"],
        "execution_scope": safe_diagnostics["execution_scope"],
        "claims": safe_diagnostics["claims"],
        "artifact_policy": {
            "new_data_generated": False,
            "public_sample_modified": False,
            "raw_logs_copied_to_git": False,
            "checkpoints_or_adapters_copied_to_git": False,
            "private_overrides_copied_to_git": False,
            "private_paths_omitted": True,
            "host_details_omitted": True,
            "ssh_details_omitted": True,
            "prediction_repair_or_replacement": False,
            "evaluator_metric_change": False,
        },
        "diagnostic_artifacts": {
            "design": (
                "reports/public-sample/slot-value-generalization-case-design/"
                "slot_value_generalization_case_design.json"
            ),
            "markdown": (
                "reports/public-sample/slot-value-generalization-case-design/"
                "slot_value_generalization_case_design.md"
            ),
            "manifest": "reports/public-sample/slot-value-generalization-case-design/manifest.json",
        },
    }
    write_json(manifest_path, manifest)

    summary = safe_diagnostics["summary"]
    lines = [
        f"# {title}",
        "",
        (
            "This is design-only evidence for a later slot value generalization phase. "
            "It is not materialized into seed_traces.jsonl, not broad scaling, not DPO, "
            "not training evidence, and not a model recovery claim."
        ),
        "",
        "## Boundary",
        "",
        "- Candidate cases are not public sample rows yet.",
        "- No dataset was rebuilt and no training or prediction run was launched.",
        "- strict `contract_exact_match` remains primary.",
        "- Soft slot F1 and semantic equivalence remain diagnostic-only.",
        "- Predictions are not repaired, replaced, rewritten, normalized, or re-scored.",
        "",
        "## Summary",
        "",
        f"- Candidate groups: `{summary['candidate_group_count']}`",
        f"- Covered residual buckets: `{summary['covered_residual_bucket_counts']}`",
        f"- Public sample modified: `{summary['public_sample_modified']}`",
        f"- New data generated: `{summary['new_data_generated']}`",
        f"- Recommended next step: `{summary['recommended_next_step']}`",
        "",
        "## Candidate Case Groups",
        "",
    ]
    for group in safe_diagnostics.get("candidate_case_groups", []):
        lines.extend(
            [
                f"### `{group['case_group_id']}`",
                "",
                f"- Source family: `{group['source_family_id']}`",
                f"- Residual bucket: `{group['residual_bucket']}`",
                f"- Affected fields: `{group['affected_field_paths']}`",
                f"- Residual rows: `{group['residual_row_ids']}`",
                f"- Canonical gold values: `{group['canonical_gold_values']}`",
                f"- Observed wrong values: `{group['observed_wrong_values']}`",
                f"- Purpose: {group['case_purpose']}",
                f"- Recommended split role: `{group['recommended_split_role']}`",
                f"- Requires user review before materialization: `{group['materialization_requires_user_review']}`",
                "",
            ]
        )

    lines.extend(
        [
            "## Recommended Next Step",
            "",
            (
                "Open a later bounded OpenSpec change to materialize reviewed cases into public-safe seed traces "
                "or a separate candidate dataset. That later change should decide split policy explicitly and "
                "still avoid broad scaling, DPO, evaluator relaxation, or release claims unless separately approved."
            ),
        ]
    )
    markdown_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return {"json": json_path, "markdown": markdown_path, "manifest": manifest_path}


def write_slot_value_generalization_materialization_report(
    materialization: dict[str, Any],
    output_dir: Path,
    sft_rows: list[dict[str, Any]],
    title: str = "Voice2Task slot value generalization materialized candidates",
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "slot_value_generalization_materialization.json"
    markdown_path = output_dir / "slot_value_generalization_materialization.md"
    manifest_path = output_dir / "manifest.json"
    sft_path = output_dir / "sft_candidate_rows.jsonl"
    safe_materialization = _sanitize_report_value(materialization)
    safe_sft_rows = _sanitize_report_value(sft_rows)
    write_json(json_path, safe_materialization)
    write_jsonl(sft_path, safe_sft_rows)

    manifest = {
        "evidence_kind": safe_materialization["evidence_kind"],
        "materialization_status": safe_materialization["materialization_status"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_case_design": safe_materialization["source_case_design"],
        "summary": safe_materialization["summary"],
        "execution_scope": safe_materialization["execution_scope"],
        "claims": safe_materialization["claims"],
        "artifact_policy": {
            "candidate_data_only": True,
            "formal_public_sample_files_modified": False,
            "new_candidate_data_generated": True,
            "public_sample_modified": False,
            "dpo_pairs_generated": False,
            "training_run": False,
            "prediction_run": False,
            "raw_logs_copied_to_git": False,
            "checkpoints_or_adapters_copied_to_git": False,
            "private_overrides_copied_to_git": False,
            "private_paths_omitted": True,
            "host_details_omitted": True,
            "ssh_details_omitted": True,
            "prediction_repair_or_replacement": False,
            "evaluator_metric_change": False,
        },
        "diagnostic_artifacts": {
            "candidate_seed": safe_materialization["artifact_files"]["candidate_seed"],
            "candidate_sft": (
                "reports/public-sample/slot-value-generalization-materialized-candidates/"
                "sft_candidate_rows.jsonl"
            ),
            "materialization": (
                "reports/public-sample/slot-value-generalization-materialized-candidates/"
                "slot_value_generalization_materialization.json"
            ),
            "markdown": (
                "reports/public-sample/slot-value-generalization-materialized-candidates/"
                "slot_value_generalization_materialization.md"
            ),
            "manifest": "reports/public-sample/slot-value-generalization-materialized-candidates/manifest.json",
        },
    }
    write_json(manifest_path, manifest)

    summary = safe_materialization["summary"]
    formal_has_candidates = bool(summary.get("formal_public_sample_has_slot_value_candidates"))
    materialization_scope = (
        "This is candidate data only: it materializes reviewed slot value generalization cases into a "
        "standalone public-safe candidate dataset. This command does not rewrite formal public sample files; "
        "the current formal public sample already records a later approved candidate merge."
        if formal_has_candidates
        else "This is candidate data only: it materializes reviewed slot value generalization cases into a "
        "standalone public-safe candidate dataset, not merged into seed_traces.jsonl and not used as "
        "training evidence yet."
    )
    formal_boundary = (
        "- This materialization command does not rewrite formal public sample files; current formal sample "
        "state is reported separately."
        if formal_has_candidates
        else "- Candidate rows are not formal public sample rows yet."
    )
    lines = [
        f"# {title}",
        "",
        materialization_scope,
        "",
        "## Boundary",
        "",
        formal_boundary,
        "- Formal public sample seed, SFT, DPO, and manifest files are not rewritten.",
        "- No DPO pairs, SFT training, prediction run, or A100 execution is performed.",
        "- strict `contract_exact_match` remains primary.",
        "- Soft slot F1 and semantic equivalence remain diagnostic-only.",
        "- This is not a model recovery, held-out recovery, checkpoint, adapter, production, or live-browser claim.",
        "",
        "## Summary",
        "",
        f"- Candidate groups: `{summary['candidate_group_count']}`",
        f"- Candidate seed rows: `{summary['candidate_seed_rows']}`",
        f"- Candidate SFT rows: `{summary['candidate_sft_rows']}`",
        f"- Formal public sample seed rows: `{summary['formal_public_sample_seed_rows']}`",
        f"- Formal public sample SFT rows: `{summary['formal_public_sample_sft_rows']}`",
        f"- Formal public sample DPO pairs: `{summary['formal_public_sample_dpo_pairs']}`",
        f"- Public sample modified: `{summary['public_sample_modified']}`",
        f"- Recommended next step: `{summary['recommended_next_step']}`",
        "",
        "## Candidate Case Groups",
        "",
    ]
    for group in safe_materialization.get("candidate_case_groups", []):
        lines.extend(
            [
                f"### `{group['case_group_id']}`",
                "",
                f"- Candidate seed: `{group['candidate_seed_id']}`",
                f"- Candidate SFT rows: `{group['candidate_sft_row_ids']}`",
                f"- Source family: `{group['source_family_id']}`",
                f"- Residual bucket: `{group['residual_bucket']}`",
                f"- Affected fields: `{group['affected_field_paths']}`",
                f"- Canonical gold values: `{group['canonical_gold_values']}`",
                "",
            ]
        )

    lines.extend(
        [
            "## Recommended Next Step",
            "",
            (
                "Decide in a later bounded OpenSpec phase whether to merge the candidates into the formal public "
                "sample or run a small local/A100 SFT probe. That later phase should keep DPO, evaluator relaxation, "
                "and model-quality claims separate unless explicitly approved."
            ),
        ]
    )
    markdown_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return {"json": json_path, "markdown": markdown_path, "manifest": manifest_path, "sft": sft_path}


def write_family_stratified_generalization_report(
    evidence: dict[str, Any],
    output_dir: Path,
    sft_rows: list[dict[str, Any]],
    title: str = "Voice2Task family-stratified generalization candidates",
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "family_stratified_generalization.json"
    markdown_path = output_dir / "family_stratified_generalization.md"
    manifest_path = output_dir / "manifest.json"
    sft_path = output_dir / "sft_candidate_rows.jsonl"
    safe_evidence = _sanitize_report_value(evidence)
    safe_sft_rows = _sanitize_report_value(sft_rows)
    write_json(json_path, safe_evidence)
    write_jsonl(sft_path, safe_sft_rows)

    summary = safe_evidence["summary"]
    manifest = {
        "evidence_kind": safe_evidence["evidence_kind"],
        "materialization_status": safe_evidence["materialization_status"],
        "generated_at": safe_evidence["generated_at"],
        "summary": summary,
        "execution_scope": safe_evidence["execution_scope"],
        "claims": safe_evidence["claims"],
        "artifact_policy": {
            "candidate_data_only": True,
            "formal_public_sample_files_modified": False,
            "new_candidate_data_generated": True,
            "public_sample_modified": False,
            "dpo_pairs_generated": False,
            "training_run": False,
            "prediction_run": False,
            "a100_execution": False,
            "raw_logs_copied_to_git": False,
            "checkpoints_or_adapters_copied_to_git": False,
            "private_overrides_copied_to_git": False,
            "private_paths_omitted": True,
            "host_details_omitted": True,
            "ssh_details_omitted": True,
            "prediction_repair_or_replacement": False,
            "evaluator_metric_change": False,
        },
        "diagnostic_artifacts": {
            "candidate_seed": safe_evidence["artifact_files"]["candidate_seed"],
            "candidate_sft": (
                "reports/public-sample/family-stratified-generalization-candidates/"
                "sft_candidate_rows.jsonl"
            ),
            "materialization": (
                "reports/public-sample/family-stratified-generalization-candidates/"
                "family_stratified_generalization.json"
            ),
            "markdown": (
                "reports/public-sample/family-stratified-generalization-candidates/"
                "family_stratified_generalization.md"
            ),
            "manifest": "reports/public-sample/family-stratified-generalization-candidates/manifest.json",
        },
    }
    write_json(manifest_path, manifest)

    lines = [
        f"# {title}",
        "",
        (
            "This is candidate data only: it creates a standalone public-safe family-stratified "
            "generalization dataset and does not rewrite formal public sample files."
        ),
        "",
        "## Boundary",
        "",
        "- Formal public sample seed, SFT, DPO, and manifest files are not rewritten.",
        "- No DPO pairs, SFT training, prediction run, or A100 execution is performed.",
        "- strict `contract_exact_match` remains primary.",
        "- Soft slot F1 and semantic equivalence remain diagnostic-only.",
        "- This is not model recovery, held-out recovery, checkpoint, adapter, production, or live-browser evidence.",
        "",
        "## Summary",
        "",
        f"- Families: `{summary['families']}`",
        f"- Candidate seed rows: `{summary['candidate_seed_rows']}`",
        f"- Candidate SFT rows: `{summary['candidate_sft_rows']}`",
        f"- SFT split counts: `{summary['split_counts']}`",
        f"- Formal public sample seed rows: `{summary['formal_public_sample_seed_rows']}`",
        f"- Formal public sample SFT rows: `{summary['formal_public_sample_sft_rows']}`",
        f"- Formal public sample DPO pairs: `{summary['formal_public_sample_dpo_pairs']}`",
        f"- Formal public sample modified: `{summary['formal_public_sample_modified']}`",
        f"- Recommended next step: `{summary['recommended_next_step']}`",
        "",
        "## Family Split Counts",
        "",
        "| family | train seeds | dev seeds | test seeds | train SFT | dev SFT | test SFT |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    family_counts = summary["family_split_counts"]
    for family in summary["families"]:
        seed_counts = family_counts["seed"][family]
        sft_counts = family_counts["sft"][family]
        lines.append(
            f"| `{family}` | {seed_counts['train']} | {seed_counts['dev']} | {seed_counts['test']} | "
            f"{sft_counts['train']} | {sft_counts['dev']} | {sft_counts['test']} |"
        )

    lines.extend(
        [
            "",
            "## Recommended Next Step",
            "",
            (
                "Review this candidate dataset before any merge, DPO generation, or A100 training. A later bounded "
                "OpenSpec phase should decide whether to merge candidates into the formal public sample and how to "
                "evaluate held-out exact match without changing evaluator semantics."
            ),
        ]
    )
    markdown_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return {"json": json_path, "markdown": markdown_path, "manifest": manifest_path, "sft": sft_path}


def write_family_stratified_public_sample_merge_report(
    evidence: dict[str, Any],
    output_dir: Path,
    title: str = "Voice2Task family-stratified public sample merge",
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "family_stratified_public_sample_merge.json"
    markdown_path = output_dir / "family_stratified_public_sample_merge.md"
    manifest_path = output_dir / "manifest.json"
    safe_evidence = _sanitize_report_value(evidence)
    write_json(json_path, safe_evidence)

    manifest = {
        "evidence_kind": safe_evidence["evidence_kind"],
        "merge_status": safe_evidence["merge_status"],
        "generated_at": safe_evidence["generated_at"],
        "formal_public_sample_counts": safe_evidence["formal_public_sample_counts"],
        "formal_public_sample_split_counts": safe_evidence["formal_public_sample_split_counts"],
        "source_summary": safe_evidence["source_summary"],
        "candidate_source": safe_evidence["candidate_source"],
        "execution_scope": safe_evidence["execution_scope"],
        "claims": safe_evidence["claims"],
        "artifact_policy": {
            "public_sample_modified": True,
            "candidate_rows_promoted_to_formal_sample": True,
            "sft_artifacts_rebuilt": True,
            "dpo_artifacts_rebuilt": True,
            "training_run": False,
            "prediction_run": False,
            "a100_execution": False,
            "raw_logs_copied_to_git": False,
            "checkpoints_or_adapters_copied_to_git": False,
            "private_overrides_copied_to_git": False,
            "private_paths_omitted": True,
            "host_details_omitted": True,
            "ssh_details_omitted": True,
            "prediction_repair_or_replacement": False,
            "evaluator_metric_change": False,
        },
        "diagnostic_artifacts": {
            "materialization": "reports/public-sample/family-stratified-public-sample-merge/"
            "family_stratified_public_sample_merge.json",
            "markdown": "reports/public-sample/family-stratified-public-sample-merge/"
            "family_stratified_public_sample_merge.md",
            "manifest": "reports/public-sample/family-stratified-public-sample-merge/manifest.json",
        },
    }
    write_json(manifest_path, manifest)

    counts = safe_evidence["formal_public_sample_counts"]
    splits = safe_evidence["formal_public_sample_split_counts"]
    candidate = safe_evidence["candidate_source"]
    lines = [
        f"# {title}",
        "",
        (
            "This report records a data merge into the formal public sample. "
            "It does not prove held-out recovery, model recovery, adapter release, "
            "checkpoint release, production readiness, or live-browser improvement."
        ),
        "",
        "## Boundary",
        "",
        "- Formal public sample seed, SFT, DPO, and manifest files were rebuilt.",
        "- No SFT/DPO/GRPO training, prediction run, or A100 execution was performed.",
        "- strict `contract_exact_match` remains the future primary evaluation metric.",
        "- Soft slot F1 and semantic equivalence remain diagnostic-only.",
        "",
        "## Summary",
        "",
        f"- Seed rows: `{counts['seed_rows']}`",
        f"- SFT rows: `{counts['sft_rows']}`",
        f"- DPO pairs: `{counts['dpo_pairs']}`",
        f"- SFT split counts: `{splits}`",
        f"- Merged candidate seed rows: `{candidate['candidate_seed_rows']}`",
        f"- Merged candidate SFT rows: `{candidate['candidate_sft_rows']}`",
        f"- Families: `{candidate['families']}`",
        f"- Candidate seed split counts: `{candidate['seed_split_counts']}`",
        "",
        "## Recommended Next Step",
        "",
        (
            "Use the new manifest ID for a later prediction-only eval phase. "
            "Do not compare new results to prior held-out metrics without noting "
            "that the formal public sample boundary changed."
        ),
    ]
    markdown_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return {"json": json_path, "markdown": markdown_path, "manifest": manifest_path}


def write_slot_value_candidate_sft_probe_report(
    *,
    candidate_manifest: dict[str, Any],
    materialization_manifest: dict[str, Any],
    sft_config: dict[str, Any],
    prediction_config: dict[str, Any],
    output_dir: Path,
    candidate_manifest_path: Path,
    materialization_manifest_path: Path,
    sft_config_path: Path,
    prediction_config_path: Path,
    a100_ssh_status: str,
    a100_output_root_status: str,
    a100_idle_gpu_status: str,
    a100_selected_gpu_index: str,
    a100_train_dependencies: list[str],
    a100_missing_dependencies: list[str],
    dry_run_metadata: dict[str, Any] | None = None,
    training_metadata: dict[str, Any] | None = None,
    prediction_metadata: dict[str, Any] | None = None,
    metrics: dict[str, Any] | None = None,
    dry_run_metadata_path: Path | None = None,
    training_metadata_path: Path | None = None,
    prediction_metadata_path: Path | None = None,
    metrics_path: Path | None = None,
    a100_training_status: str | None = None,
    a100_prediction_status: str | None = None,
    remote_workspace_status: str = "not_recorded",
    dependency_env_status: str = "not_recorded",
    sync_status: str = "not_recorded",
    title: str = "Voice2Task slot value candidate SFT probe",
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "slot_value_candidate_sft_probe.json"
    markdown_path = output_dir / "slot_value_candidate_sft_probe.md"
    manifest_path = output_dir / "manifest.json"

    safe_dry_run = _sanitize_report_value(dry_run_metadata or {})
    safe_training = _sanitize_report_value(training_metadata or {})
    safe_prediction = _sanitize_report_value(prediction_metadata or {})
    safe_metrics = _sanitize_report_value(metrics or {})
    safe_candidate_manifest = _sanitize_report_value(candidate_manifest)
    safe_materialization_manifest = _sanitize_report_value(materialization_manifest)
    safe_sft_config = _sanitize_report_value(sft_config)
    safe_prediction_config = _sanitize_report_value(prediction_config)

    counts = safe_candidate_manifest.get("counts", {}) if isinstance(safe_candidate_manifest, dict) else {}
    candidate_sft_rows = int(counts.get("sft_rows", 0))
    selected_rows = int(
        safe_training.get(
            "training_rows_used",
            safe_dry_run.get("training_rows_used", candidate_sft_rows),
        )
    )
    missing_dependencies = list(a100_missing_dependencies)
    if a100_training_status:
        training_status = a100_training_status
    elif missing_dependencies:
        training_status = "blocked_missing_train_dependencies"
    elif isinstance(safe_training, dict) and safe_training.get("training_status"):
        training_status = str(safe_training["training_status"])
    else:
        training_status = "ready_for_private_a100_execution"
    if a100_prediction_status:
        prediction_status = a100_prediction_status
    elif isinstance(safe_prediction, dict) and safe_prediction.get("prediction_status"):
        prediction_status = str(safe_prediction["prediction_status"])
    elif training_status == "training_completed":
        prediction_status = "not_attempted"
    else:
        prediction_status = "skipped_training_not_completed"

    summary = {
        "candidate_sft_rows": candidate_sft_rows,
        "selected_candidate_training_rows": selected_rows,
        "formal_public_sample_modified": bool(safe_candidate_manifest.get("formal_public_sample_modified", False)),
        "a100_training_status": training_status,
        "a100_prediction_status": prediction_status,
        "local_dry_run_status": safe_dry_run.get("training_status", "unknown"),
        "recommended_next_step": "prepare_private_a100_train_environment_then_run_candidate_probe"
        if missing_dependencies
        else (
            "decide_candidate_merge_or_heldout_strategy"
            if prediction_status == "private_adapter_predictions_written"
            else (
                "run_candidate_train_prediction"
                if training_status == "training_completed"
                else "run_private_a100_candidate_probe"
            )
        ),
    }
    a100_preflight = {
        "ssh_status": a100_ssh_status,
        "output_root_status": a100_output_root_status,
        "idle_gpu_status": a100_idle_gpu_status,
        "selected_gpu_index": a100_selected_gpu_index,
        "train_dependencies_available": list(a100_train_dependencies),
        "missing_train_dependencies": missing_dependencies,
        "safe_to_launch_training": not missing_dependencies
        and a100_ssh_status == "ok"
        and a100_output_root_status == "ok"
        and a100_idle_gpu_status == "idle_gpu_available",
    }
    remote_execution = {
        "remote_workspace_status": remote_workspace_status,
        "dependency_env_status": dependency_env_status,
        "sync_status": sync_status,
        "training_status": training_status,
        "prediction_status": prediction_status,
    }
    training_run = training_status == "training_completed"
    training_attempted = training_status in {"training_completed", "training_failed"}
    prediction_run = prediction_status in {"prediction_completed", "completed", "private_adapter_predictions_written"}
    execution_scope = {
        "candidate_only_scope": True,
        "candidate_only_dry_run": bool(safe_dry_run) and not training_run,
        "formal_public_sample_modified": summary["formal_public_sample_modified"],
        "training_run": training_run,
        "prediction_run": prediction_run,
        "dpo_run": False,
        "a100_training_launched": training_attempted,
        "a100_prediction_launched": prediction_run or prediction_status == "prediction_failed",
        "evaluator_metric_change": False,
    }
    claims = {
        "checkpoint_release": False,
        "adapter_release": False,
        "model_recovery_claim": False,
        "held_out_generalization_recovered": False,
        "private_corpus_generalization_claim": False,
        "production_readiness_claim": False,
        "live_browser_benchmark_claim": False,
    }
    artifact_files = {
        "dry_run_metadata": (
            dry_run_metadata_path.as_posix() if dry_run_metadata_path is not None else "not_provided"
        ),
        "training_metadata": (
            training_metadata_path.as_posix() if training_metadata_path is not None else "not_provided"
        ),
        "prediction_metadata": prediction_metadata_path.as_posix()
        if prediction_metadata_path is not None
        else "not_provided",
        "metrics": metrics_path.as_posix() if metrics_path is not None else "not_provided",
        "candidate_manifest": candidate_manifest_path.as_posix(),
        "materialization_manifest": materialization_manifest_path.as_posix(),
        "sft_config": sft_config_path.as_posix(),
        "prediction_config": prediction_config_path.as_posix(),
        "evidence_json": json_path.as_posix(),
        "evidence_markdown": markdown_path.as_posix(),
        "manifest": manifest_path.as_posix(),
    }
    safe_artifact_files = _sanitize_report_value(artifact_files)
    limitations = [
        "formal public sample files remain unchanged",
        "candidate train-split evidence does not prove held-out generalization",
    ]
    if training_run:
        limitations.append(
            "A100 adapters, checkpoints, caches, private overrides, host details, and raw logs remain private"
        )
    else:
        limitations.append("candidate-only dry-run or preflight evidence is not SFT learning evidence")
    if missing_dependencies:
        limitations.append(
            "blocked_missing_train_dependencies means no private A100 training or prediction was launched"
        )
    evidence = {
        "evidence_kind": "slot_value_candidate_sft_probe",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": summary,
        "a100_preflight": a100_preflight,
        "remote_execution": remote_execution,
        "execution_scope": execution_scope,
        "claims": claims,
        "dry_run_metadata": safe_dry_run,
        "training_metadata": safe_training,
        "prediction_metadata": safe_prediction,
        "metrics": safe_metrics,
        "candidate_manifest": safe_candidate_manifest,
        "materialization_manifest": safe_materialization_manifest,
        "sft_config": safe_sft_config,
        "prediction_config": safe_prediction_config,
        "artifact_files": safe_artifact_files,
        "limitations": limitations,
    }
    safe_evidence = _sanitize_report_value(evidence)
    if not isinstance(safe_evidence, dict):
        raise AssertionError("candidate SFT probe evidence must be a mapping")
    write_json(json_path, safe_evidence)

    manifest = {
        "evidence_kind": "slot_value_candidate_sft_probe",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": summary,
        "a100_preflight": a100_preflight,
        "remote_execution": remote_execution,
        "execution_scope": execution_scope,
        "claims": claims,
        "source_candidate_manifest_id": safe_candidate_manifest.get("manifest_id"),
        "source_materialization_evidence_kind": safe_materialization_manifest.get("evidence_kind"),
        "artifact_policy": {
            "candidate_only": True,
            "formal_public_sample_files_modified": False,
            "training_run": training_run,
            "prediction_run": prediction_run,
            "dpo_run": False,
            "raw_logs_copied_to_git": False,
            "checkpoints_or_adapters_copied_to_git": False,
            "private_overrides_copied_to_git": False,
            "private_paths_omitted": True,
            "host_details_omitted": True,
            "ssh_details_omitted": True,
        },
        "diagnostic_artifacts": safe_artifact_files,
    }
    write_json(manifest_path, _sanitize_report_value(manifest))

    lines = [
        f"# {title}",
        "",
        (
            "This is candidate-only evidence for the standalone slot value candidate SFT rows. "
            "It records dry-run, blocked, failed, or observed A100 execution status without publishing adapters "
            "or claiming held-out model recovery."
        ),
        "",
        "## Boundary",
        "",
        "- Formal public sample seed, SFT, DPO, and manifest files are unchanged.",
        "- No DPO training, checkpoint release, or adapter release is claimed.",
        (
            "- A100 SFT/prediction execution is recorded, but adapters, checkpoints, raw logs, caches, host "
            "details, private overrides, and private paths remain outside git."
            if training_run or prediction_run
            else "- No SFT training or prediction run is claimed unless observed metadata is present."
        ),
        "- strict `contract_exact_match` remains primary; no evaluator relaxation is introduced.",
        "- This is not held-out, private-corpus, production-readiness, or live-browser evidence.",
        "",
        "## Summary",
        "",
        f"- Candidate SFT rows: `{summary['candidate_sft_rows']}`",
        f"- Selected candidate training rows: `{summary['selected_candidate_training_rows']}`",
        f"- Formal public sample modified: `{summary['formal_public_sample_modified']}`",
        f"- A100 training status: `{summary['a100_training_status']}`",
        f"- A100 prediction status: `{summary['a100_prediction_status']}`",
        f"- Recommended next step: `{summary['recommended_next_step']}`",
        "",
        "## A100 Preflight",
        "",
        f"- SSH status: `{a100_preflight['ssh_status']}`",
        f"- Output root status: `{a100_preflight['output_root_status']}`",
        f"- Idle GPU status: `{a100_preflight['idle_gpu_status']}`",
        f"- Selected GPU index: `{a100_preflight['selected_gpu_index']}`",
        f"- Available train dependencies: `{a100_preflight['train_dependencies_available']}`",
        f"- Missing train dependencies: `{a100_preflight['missing_train_dependencies']}`",
        f"- Safe to launch training now: `{a100_preflight['safe_to_launch_training']}`",
        "",
        "## Remote Execution",
        "",
        f"- Workspace status: `{remote_execution['remote_workspace_status']}`",
        f"- Dependency environment status: `{remote_execution['dependency_env_status']}`",
        f"- Sync status: `{remote_execution['sync_status']}`",
        f"- Training status: `{remote_execution['training_status']}`",
        f"- Prediction status: `{remote_execution['prediction_status']}`",
        "",
        "## Evidence",
        "",
        f"- Dry-run metadata: `{safe_artifact_files['dry_run_metadata']}`",
        f"- Training metadata: `{safe_artifact_files['training_metadata']}`",
        f"- Prediction metadata: `{safe_artifact_files['prediction_metadata']}`",
        f"- Metrics: `{safe_artifact_files['metrics']}`",
        f"- Candidate manifest: `{safe_artifact_files['candidate_manifest']}`",
        f"- SFT config: `{safe_artifact_files['sft_config']}`",
        f"- Prediction config: `{safe_artifact_files['prediction_config']}`",
    ]
    markdown_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return {"json": json_path, "markdown": markdown_path, "manifest": manifest_path}


def _metric_value(metrics_payload: dict[str, Any], name: str, default: float = 0.0) -> float:
    metrics = metrics_payload.get("metrics")
    if not isinstance(metrics, dict):
        return default
    value = metrics.get(name, default)
    return float(value) if isinstance(value, int | float) else default


def _failure_slice_count(metrics_payload: dict[str, Any], name: str) -> int:
    slices = metrics_payload.get("failure_slices")
    if not isinstance(slices, dict):
        return 0
    entry = slices.get(name)
    if not isinstance(entry, dict):
        return 0
    value = entry.get("count", 0)
    return int(value) if isinstance(value, int) else 0


def _merged_split_result(
    *,
    split: str,
    metrics_payload: dict[str, Any],
    prediction_metadata: dict[str, Any],
    public_manifest: dict[str, Any],
    metrics_path: Path,
    prediction_metadata_path: Path | None,
) -> dict[str, Any]:
    split_counts = public_manifest.get("split_counts", {})
    metadata_manifest_id = prediction_metadata.get("dataset_manifest_id")
    manifest_id = public_manifest.get("manifest_id")
    if metadata_manifest_id is not None and metadata_manifest_id != manifest_id:
        raise ValueError(
            f"prediction metadata manifest mismatch for {split}: {metadata_manifest_id!r} != {manifest_id!r}"
        )
    metadata_split = prediction_metadata.get("prediction_split")
    if metadata_split is not None and metadata_split != split:
        raise ValueError(f"prediction metadata split mismatch for {split}: {metadata_split!r}")
    prediction_count = prediction_metadata.get("prediction_count")
    if not isinstance(prediction_count, int):
        prediction_count = int(split_counts.get(split, 0)) if isinstance(split_counts, dict) else 0
    expected_count = int(split_counts.get(split, 0)) if isinstance(split_counts, dict) else 0
    if expected_count and prediction_count != expected_count:
        raise ValueError(
            f"prediction metadata count mismatch for {split}: {prediction_count!r} != {expected_count!r}"
        )
    exact = _metric_value(metrics_payload, "contract_exact_match")
    residual_rows = max(0, prediction_count - round(prediction_count * exact))
    return {
        "prediction_split": split,
        "prediction_count": prediction_count,
        "contract_exact_match": exact,
        "json_valid_rate": _metric_value(metrics_payload, "json_valid_rate"),
        "slot_f1": _metric_value(metrics_payload, "slot_f1"),
        "slot_f1_soft": _metric_value(metrics_payload, "slot_f1_soft"),
        "task_type_accuracy": _metric_value(metrics_payload, "task_type_accuracy"),
        "route_accuracy": _metric_value(metrics_payload, "route_accuracy"),
        "safety_precision": _metric_value(metrics_payload, "safety_precision"),
        "safety_recall": _metric_value(metrics_payload, "safety_recall"),
        "confirmation_accuracy": _metric_value(metrics_payload, "confirmation_accuracy"),
        "schema_invalid_prediction_count": _failure_slice_count(metrics_payload, "schema"),
        "residual_row_count": residual_rows,
        "failure_slice_counts": {
            name: _failure_slice_count(metrics_payload, name)
            for name in ("schema", "task_type", "route", "safety", "confirmation", "slot", "unknown")
        },
        "artifact_paths": {
            "metrics": metrics_path.as_posix(),
            "prediction_metadata": prediction_metadata_path.as_posix() if prediction_metadata_path else "not_provided",
        },
    }


def _prior_targeted_exact(prior_targeted_manifest: dict[str, Any] | None) -> dict[str, float]:
    if not prior_targeted_manifest:
        return {"train": 0.0, "dev": 0.0, "test": 0.0}
    comparison = prior_targeted_manifest.get("comparison")
    if isinstance(comparison, dict) and isinstance(comparison.get("targeted_family_coverage_exact"), dict):
        return {
            split: float(comparison["targeted_family_coverage_exact"].get(split, 0.0))
            for split in ("train", "dev", "test")
        }
    split_results = prior_targeted_manifest.get("split_results")
    if isinstance(split_results, dict):
        return {
            split: float((split_results.get(split) or {}).get("contract_exact_match", 0.0))
            for split in ("train", "dev", "test")
        }
    return {"train": 0.0, "dev": 0.0, "test": 0.0}


def _merged_slot_value_interpretation(split_results: dict[str, dict[str, Any]], prior_exact: dict[str, float]) -> str:
    heldout_splits = ("dev", "test")
    heldout_exact = {split: float(split_results[split]["contract_exact_match"]) for split in heldout_splits}
    if all(value >= 1.0 for value in heldout_exact.values()):
        return "merged_slot_value_public_heldout_recovered"
    if any(heldout_exact[split] < prior_exact.get(split, 0.0) for split in heldout_splits):
        return "merged_slot_value_heldout_regressed"
    if any(heldout_exact[split] > prior_exact.get(split, 0.0) for split in heldout_splits):
        return "merged_slot_value_heldout_improved_partial"
    return "merged_slot_value_heldout_stayed_partial"


def _public_base_model_from_training_metadata(safe_training: dict[str, Any]) -> str:
    hyperparameters = safe_training.get("hyperparameters")
    if isinstance(hyperparameters, dict):
        public_id = hyperparameters.get("base_model_public_id")
        if isinstance(public_id, str) and public_id:
            return public_id
    public_id = safe_training.get("base_model_public_id")
    if isinstance(public_id, str) and public_id:
        return public_id
    base_model = safe_training.get("base_model")
    if isinstance(base_model, str) and base_model and base_model != "<private_path>":
        return base_model
    return "Qwen/Qwen2.5-7B-Instruct"


def _public_merged_training_metadata(training_metadata: dict[str, Any] | None) -> dict[str, Any]:
    raw_training = dict(training_metadata or {})
    notes = raw_training.get("notes")
    if isinstance(notes, str):
        raw_training["notes"] = notes.replace(
            "SFT training ran locally",
            "SFT training ran in the private A100 runtime",
        )
    safe_training = _sanitize_report_value(raw_training)
    if not isinstance(safe_training, dict):
        return {}
    safe_training["base_model"] = _public_base_model_from_training_metadata(safe_training)
    return safe_training


def write_merged_slot_value_heldout_eval_report(
    *,
    public_manifest: dict[str, Any],
    training_metadata: dict[str, Any] | None,
    metrics_by_split: dict[str, dict[str, Any]],
    prediction_metadata_by_split: dict[str, dict[str, Any] | None],
    output_dir: Path,
    metrics_paths: dict[str, Path],
    prediction_metadata_paths: dict[str, Path | None],
    prior_targeted_manifest: dict[str, Any] | None = None,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "merged_slot_value_heldout_eval.json"
    manifest_path = output_dir / "manifest.json"
    report_path = output_dir / "report.md"
    safe_training = _public_merged_training_metadata(training_metadata)
    safe_prediction_metadata = _sanitize_report_value(prediction_metadata_by_split)
    split_results = {
        split: _merged_split_result(
            split=split,
            metrics_payload=metrics_by_split[split],
            prediction_metadata=prediction_metadata_by_split.get(split) or {},
            public_manifest=public_manifest,
            metrics_path=metrics_paths[split],
            prediction_metadata_path=prediction_metadata_paths.get(split),
        )
        for split in ("train", "dev", "test")
    }
    prior_exact = _prior_targeted_exact(prior_targeted_manifest)
    interpretation = _merged_slot_value_interpretation(split_results, prior_exact)
    dev_test_improved = {
        split: split_results[split]["contract_exact_match"] > prior_exact.get(split, 0.0)
        for split in ("dev", "test")
    }
    heldout_recovered = interpretation == "merged_slot_value_public_heldout_recovered"
    evidence = {
        "evidence_kind": "a100_merged_slot_value_heldout_eval",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "base_model": _public_base_model_from_training_metadata(safe_training),
        "dataset_manifest_id": public_manifest.get("manifest_id"),
        "formal_public_sample_counts": public_manifest.get("counts", {}),
        "formal_public_sample_split_counts": public_manifest.get("split_counts", {}),
        "formal_public_sample_source_summary": public_manifest.get("source_summary", {}),
        "training_status": safe_training.get("training_status", "not_recorded"),
        "training_rows_used": safe_training.get("training_rows_used"),
        "prediction_source_kind": "private_a100_adapter",
        "prediction_splits": ["train", "dev", "test"],
        "primary_evidence_splits": ["dev", "test"],
        "split_results": split_results,
        "comparison": {
            "prior_targeted_family_coverage_exact": prior_exact,
            "merged_slot_value_exact": {
                split: split_results[split]["contract_exact_match"] for split in ("train", "dev", "test")
            },
            "dev_test_improved_from_prior_targeted": dev_test_improved,
        },
        "overall_interpretation": interpretation,
        "claims": {
            "merged_slot_value_candidates": True,
            "held_out_generalization_recovered": heldout_recovered,
            "model_recovery_claim": False,
            "private_corpus_generalization_claim": False,
            "adapter_release": False,
            "checkpoint_release": False,
            "production_readiness_claim": False,
            "live_browser_benchmark_claim": False,
            "semantic_equivalence_primary_metric": False,
            "soft_slot_f1_primary_metric": False,
            "evaluator_relaxation": False,
            "prediction_repair_or_replacement": False,
        },
        "artifact_policy": {
            "raw_logs_copied_to_git": False,
            "checkpoints_or_adapters_copied_to_git": False,
            "remote_caches_copied_to_git": False,
            "private_overrides_copied_to_git": False,
            "private_paths_omitted": True,
            "host_details_omitted": True,
            "ssh_details_omitted": True,
            "private_corpus_rows_omitted": True,
        },
        "training_metadata": safe_training,
        "prediction_metadata_by_split": safe_prediction_metadata,
    }
    safe_evidence = _sanitize_report_value(evidence)
    write_json(json_path, safe_evidence)
    manifest = {
        "evidence_kind": "a100_merged_slot_value_heldout_eval",
        "generated_at": safe_evidence["generated_at"],
        "dataset_manifest_id": safe_evidence["dataset_manifest_id"],
        "formal_public_sample_counts": safe_evidence["formal_public_sample_counts"],
        "prediction_splits": safe_evidence["prediction_splits"],
        "primary_evidence_splits": safe_evidence["primary_evidence_splits"],
        "split_results": safe_evidence["split_results"],
        "comparison": safe_evidence["comparison"],
        "overall_interpretation": safe_evidence["overall_interpretation"],
        "claims": safe_evidence["claims"],
        "artifact_policy": safe_evidence["artifact_policy"],
        "diagnostic_artifacts": {
            "evidence": "reports/public-sample/a100-merged-slot-value-heldout-eval/merged_slot_value_heldout_eval.json",
            "manifest": "reports/public-sample/a100-merged-slot-value-heldout-eval/manifest.json",
            "report": "reports/public-sample/a100-merged-slot-value-heldout-eval/report.md",
        },
    }
    write_json(manifest_path, manifest)

    lines = [
        "# A100 merged slot value held-out evaluation",
        "",
        (
            "Status: merged-candidate public-sample SFT evaluation. Train split is learnability evidence; "
            "dev/test strict exact is the primary held-out signal."
        ),
        "",
        "## Scope",
        "",
        f"- Dataset manifest: `{safe_evidence['dataset_manifest_id']}`",
        f"- Formal public sample counts: `{safe_evidence['formal_public_sample_counts']}`",
        f"- Training status: `{safe_evidence['training_status']}`",
        f"- Overall interpretation: `{safe_evidence['overall_interpretation']}`",
        "",
        "## Split Results",
        "",
        "| split | rows | contract_exact_match | slot_f1 | json_valid_rate | residual rows |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for split in ("train", "dev", "test"):
        result = safe_evidence["split_results"][split]
        lines.append(
            f"| {split} | {result['prediction_count']} | {result['contract_exact_match']:.4f} | "
            f"{result['slot_f1']:.4f} | {result['json_valid_rate']:.4f} | {result['residual_row_count']} |"
        )
    lines.extend(
        [
            "",
            "## Comparison",
            "",
            (
                "- Prior targeted family coverage exact: "
                f"`{safe_evidence['comparison']['prior_targeted_family_coverage_exact']}`"
            ),
            f"- Merged slot value exact: `{safe_evidence['comparison']['merged_slot_value_exact']}`",
            (
                "- Dev/test improved from prior targeted: "
                f"`{safe_evidence['comparison']['dev_test_improved_from_prior_targeted']}`"
            ),
            "",
            "## Boundary",
            "",
            "- strict `contract_exact_match` remains primary.",
            "- Soft slot F1 and semantic equivalence remain diagnostic-only.",
            "- Predictions are not repaired, replaced, normalized, or re-scored.",
            (
                "- This is not a checkpoint release, adapter release, production-readiness claim, "
                "private-corpus generalization claim, public full-corpus release, or live-browser benchmark claim."
            ),
        ]
    )
    report_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return {"json": json_path, "manifest": manifest_path, "report": report_path}


def _formal_public_observed_interpretation(split_results: dict[str, dict[str, Any]]) -> str:
    if not split_results:
        return "formal_public_heldout_prediction_blocked"
    heldout_exact = {split: float(split_results[split]["contract_exact_match"]) for split in ("dev", "test")}
    if all(value >= 1.0 for value in heldout_exact.values()):
        return "formal_public_heldout_strict_exact_recovered"
    if any(value > 0.0 for value in heldout_exact.values()):
        return "formal_public_heldout_partial_signal"
    return "formal_public_heldout_no_strict_exact_recovery"


def write_formal_public_heldout_prediction_report(
    *,
    public_manifest: dict[str, Any],
    output_dir: Path,
    run_status: str,
    blocked_reason: str | None = None,
    metrics_by_split: dict[str, dict[str, Any]] | None = None,
    prediction_metadata_by_split: dict[str, dict[str, Any]] | None = None,
    artifact_paths_by_split: dict[str, dict[str, str]] | None = None,
    leak_scan_result: dict[str, Any] | None = None,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "formal_public_heldout_prediction.json"
    manifest_path = output_dir / "manifest.json"
    report_path = output_dir / "report.md"
    metrics_by_split = metrics_by_split or {}
    prediction_metadata_by_split = prediction_metadata_by_split or {}
    artifact_paths_by_split = artifact_paths_by_split or {}
    if run_status not in {"observed", "blocked"}:
        raise ValueError(f"unsupported formal public heldout prediction run status: {run_status}")
    if run_status == "blocked" and not (blocked_reason or "").strip():
        raise ValueError("blocked formal public heldout prediction requires a blocked_reason")
    if run_status == "observed":
        missing = [
            split
            for split in ("dev", "test")
            if split not in metrics_by_split or split not in prediction_metadata_by_split
        ]
        if missing:
            raise ValueError(f"observed formal public heldout prediction missing splits: {', '.join(missing)}")

    split_results = (
        {
            split: _merged_split_result(
                split=split,
                metrics_payload=metrics_by_split[split],
                prediction_metadata=prediction_metadata_by_split[split],
                public_manifest=public_manifest,
                metrics_path=Path(artifact_paths_by_split.get(split, {}).get("metrics", "not_provided")),
                prediction_metadata_path=Path(
                    artifact_paths_by_split.get(split, {}).get("prediction_metadata", "not_provided")
                ),
            )
            for split in ("dev", "test")
        }
        if run_status == "observed"
        else {}
    )
    interpretation = _formal_public_observed_interpretation(split_results)
    heldout_recovered = interpretation == "formal_public_heldout_strict_exact_recovered"
    evidence = {
        "evidence_kind": "a100_formal_public_heldout_prediction",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run_status": run_status,
        "blocked_reason": blocked_reason if run_status == "blocked" else None,
        "base_model": "Qwen/Qwen2.5-7B-Instruct",
        "source_adapter_runtime": "a100-merged-slot-value-heldout-eval",
        "dataset_manifest_id": public_manifest.get("manifest_id"),
        "formal_public_sample_counts": public_manifest.get("counts", {}),
        "formal_public_sample_split_counts": public_manifest.get("split_counts", {}),
        "formal_public_sample_source_summary": public_manifest.get("source_summary", {}),
        "training_status": "prediction_only_no_training",
        "prediction_splits": ["dev", "test"],
        "primary_evidence_splits": ["dev", "test"],
        "split_results": split_results,
        "overall_interpretation": interpretation,
        "artifact_paths_by_split": artifact_paths_by_split,
        "leak_scan_result": leak_scan_result or {},
        "claims": {
            "prediction_only": True,
            "training_performed": False,
            "data_changed": False,
            "evaluator_relaxation": False,
            "semantic_equivalence_primary_metric": False,
            "soft_slot_f1_primary_metric": False,
            "prediction_repair_or_rescore": False,
            "prediction_repair_or_replacement": False,
            "held_out_generalization_recovered": heldout_recovered,
            "model_recovery_claim": False,
            "private_corpus_generalization_claim": False,
            "adapter_release": False,
            "checkpoint_release": False,
            "production_readiness_claim": False,
            "live_browser_benchmark_claim": False,
            "public_full_corpus_release_claim": False,
        },
        "artifact_policy": {
            "raw_logs_copied_to_git": False,
            "checkpoints_or_adapters_copied_to_git": False,
            "remote_caches_copied_to_git": False,
            "private_overrides_copied_to_git": False,
            "private_paths_omitted": True,
            "host_details_omitted": True,
            "ssh_details_omitted": True,
            "private_corpus_rows_omitted": True,
        },
        "prediction_metadata_by_split": _sanitize_report_value(prediction_metadata_by_split),
    }
    safe_evidence = _sanitize_report_value(evidence)
    write_json(json_path, safe_evidence)
    manifest = {
        "evidence_kind": safe_evidence["evidence_kind"],
        "generated_at": safe_evidence["generated_at"],
        "run_status": safe_evidence["run_status"],
        "blocked_reason": safe_evidence["blocked_reason"],
        "dataset_manifest_id": safe_evidence["dataset_manifest_id"],
        "formal_public_sample_counts": safe_evidence["formal_public_sample_counts"],
        "formal_public_sample_split_counts": safe_evidence["formal_public_sample_split_counts"],
        "source_adapter_runtime": safe_evidence["source_adapter_runtime"],
        "training_status": safe_evidence["training_status"],
        "prediction_splits": safe_evidence["prediction_splits"],
        "primary_evidence_splits": safe_evidence["primary_evidence_splits"],
        "split_results": safe_evidence["split_results"],
        "overall_interpretation": safe_evidence["overall_interpretation"],
        "claims": safe_evidence["claims"],
        "artifact_policy": safe_evidence["artifact_policy"],
        "diagnostic_artifacts": {
            "evidence": _public_report_artifact_path(output_dir, "formal_public_heldout_prediction.json"),
            "manifest": _public_report_artifact_path(output_dir, "manifest.json"),
            "report": _public_report_artifact_path(output_dir, "report.md"),
        },
    }
    write_json(manifest_path, manifest)

    lines = [
        "# A100 formal public held-out prediction",
        "",
        (
            "Status: prediction-only current-manifest held-out evidence. This phase does not train, mutate data, "
            "repair predictions, normalize slots, or change evaluator semantics."
        ),
        "",
        "## Scope",
        "",
        f"- Dataset manifest: `{safe_evidence['dataset_manifest_id']}`",
        f"- Run status: `{safe_evidence['run_status']}`",
        f"- Source adapter runtime: `{safe_evidence['source_adapter_runtime']}`",
        f"- Overall interpretation: `{safe_evidence['overall_interpretation']}`",
    ]
    if run_status == "blocked":
        lines.extend(
            [
                f"- Blocked reason: `{safe_evidence['blocked_reason']}`",
                "",
                "## Blocked Status",
                "",
                (
                    "Blocked before private prediction. No model-quality metrics, held-out recovery claim, "
                    "or adapter release claim is made from this artifact."
                ),
            ]
        )
    else:
        lines.extend(
            [
                "",
                "## Split Results",
                "",
                "| split | rows | contract_exact_match | slot_f1 | slot_f1_soft | json_valid_rate | residual rows |",
                "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        for split in ("dev", "test"):
            result = safe_evidence["split_results"][split]
            lines.append(
                f"| {split} | {result['prediction_count']} | {result['contract_exact_match']:.4f} | "
                f"{result['slot_f1']:.4f} | {result['slot_f1_soft']:.4f} | "
                f"{result['json_valid_rate']:.4f} | {result['residual_row_count']} |"
            )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- Strict `contract_exact_match` remains primary.",
            "- `slot_f1_soft` is diagnostic only.",
            "- Predictions are not repaired, replaced, normalized, or re-scored.",
            (
                "- This is not held-out recovery unless dev/test strict exact both reach `1.0`; it is not a "
                "checkpoint release, adapter release, production-readiness claim, private-corpus generalization "
                "claim, public full-corpus release, or live-browser benchmark claim."
            ),
        ]
    )
    report_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return {"json": json_path, "manifest": manifest_path, "markdown": report_path, "report": report_path}


def _prior_merged_exact(prior_merged_manifest: dict[str, Any]) -> dict[str, float]:
    if prior_merged_manifest.get("evidence_kind") != "a100_merged_slot_value_heldout_eval":
        raise ValueError("prior merged manifest must be a100_merged_slot_value_heldout_eval evidence")
    comparison = prior_merged_manifest.get("comparison")
    if isinstance(comparison, dict) and isinstance(comparison.get("merged_slot_value_exact"), dict):
        exact = comparison["merged_slot_value_exact"]
        missing = [split for split in ("train", "dev", "test") if split not in exact]
        if missing:
            raise ValueError("prior merged manifest missing strict exact values: " + ", ".join(missing))
        return {split: float(exact[split]) for split in ("train", "dev", "test")}
    split_results = prior_merged_manifest.get("split_results")
    if isinstance(split_results, dict):
        missing = [
            split
            for split in ("train", "dev", "test")
            if not isinstance(split_results.get(split), dict)
            or "contract_exact_match" not in split_results[split]
        ]
        if missing:
            raise ValueError("prior merged manifest missing split_results exact values: " + ", ".join(missing))
        return {
            split: float(split_results[split]["contract_exact_match"])
            for split in ("train", "dev", "test")
        }
    raise ValueError("prior merged manifest missing comparison or split_results strict exact values")


def _hardened_prompt_policy_flags(prediction_metadata: dict[str, Any]) -> dict[str, bool]:
    constraints = prediction_metadata.get("prompt_constraints")
    if not isinstance(constraints, dict):
        constraints = {}
    clarify_visible = bool(constraints.get("clarify_ambiguity_canonical_phrase_visible"))
    unsafe_payment_visible = bool(constraints.get("unsafe_payment_canonical_command_visible"))
    return {
        "clarify_ambiguity_canonical_phrase_visible": clarify_visible,
        "unsafe_payment_canonical_command_visible": unsafe_payment_visible,
        "hardened_canonical_policy_visible": clarify_visible and unsafe_payment_visible,
    }


def _hardened_policy_interpretation(
    *,
    rerun_status: str,
    split_results: dict[str, dict[str, Any]],
    prior_exact: dict[str, float],
    prompt_policy_by_split: dict[str, dict[str, bool]],
) -> str:
    if rerun_status == "blocked":
        return "hardened_canonical_policy_rerun_blocked"
    if not all(
        prompt_policy_by_split.get(split, {}).get("hardened_canonical_policy_visible", False)
        for split in ("train", "dev", "test")
    ):
        return "hardened_canonical_policy_prompt_flags_missing"
    heldout_exact = {split: float(split_results[split]["contract_exact_match"]) for split in ("dev", "test")}
    if all(value >= 1.0 for value in heldout_exact.values()):
        return "hardened_canonical_policy_public_heldout_recovered"
    if any(heldout_exact[split] < prior_exact.get(split, 0.0) for split in ("dev", "test")):
        return "hardened_canonical_policy_heldout_regressed"
    if any(heldout_exact[split] > prior_exact.get(split, 0.0) for split in ("dev", "test")):
        return "hardened_canonical_policy_heldout_improved_partial"
    return "hardened_canonical_policy_heldout_unchanged"


def _public_report_artifact_path(output_dir: Path, filename: str) -> str:
    output_posix = output_dir.as_posix().rstrip("/")
    marker = "reports/public-sample/"
    if marker in output_posix:
        output_posix = output_posix[output_posix.index(marker) :]
    elif output_posix in {"", "."}:
        output_posix = "."
    elif not output_dir.is_absolute():
        output_posix = output_posix.removeprefix("./")
    else:
        output_posix = output_dir.name
    return f"{output_posix}/{filename}" if output_posix != "." else filename


def write_hardened_canonical_policy_rerun_report(
    *,
    public_manifest: dict[str, Any],
    prior_merged_manifest: dict[str, Any],
    output_dir: Path,
    rerun_status: str = "observed",
    blocked_reason: str | None = None,
    metrics_by_split: dict[str, dict[str, Any]] | None = None,
    prediction_metadata_by_split: dict[str, dict[str, Any]] | None = None,
    metrics_paths: dict[str, Path | None] | None = None,
    prediction_metadata_paths: dict[str, Path | None] | None = None,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "hardened_canonical_policy_rerun.json"
    manifest_path = output_dir / "manifest.json"
    report_path = output_dir / "report.md"
    metrics_by_split = metrics_by_split or {}
    prediction_metadata_by_split = prediction_metadata_by_split or {}
    metrics_paths = metrics_paths or {}
    prediction_metadata_paths = prediction_metadata_paths or {}
    if rerun_status not in {"observed", "blocked"}:
        raise ValueError(f"unsupported hardened canonical policy rerun status: {rerun_status}")
    if rerun_status == "blocked" and not (blocked_reason or "").strip():
        raise ValueError("blocked hardened canonical policy rerun requires a blocked_reason")
    if rerun_status == "observed":
        missing = [
            split
            for split in ("train", "dev", "test")
            if split not in metrics_by_split or split not in prediction_metadata_by_split
        ]
        if missing:
            raise ValueError(f"observed hardened rerun missing split artifacts: {', '.join(missing)}")

    prior_exact = _prior_merged_exact(prior_merged_manifest)
    split_results = (
        {
            split: _merged_split_result(
                split=split,
                metrics_payload=metrics_by_split[split],
                prediction_metadata=prediction_metadata_by_split[split],
                public_manifest=public_manifest,
                metrics_path=metrics_paths[split] or Path("not_provided"),
                prediction_metadata_path=prediction_metadata_paths.get(split),
            )
            for split in ("train", "dev", "test")
        }
        if rerun_status == "observed"
        else {}
    )
    prompt_policy_by_split = (
        {
            split: _hardened_prompt_policy_flags(prediction_metadata_by_split[split])
            for split in ("train", "dev", "test")
        }
        if rerun_status == "observed"
        else {}
    )
    hardened_exact = (
        {split: split_results[split]["contract_exact_match"] for split in ("train", "dev", "test")}
        if rerun_status == "observed"
        else {}
    )
    exact_delta = (
        {split: hardened_exact[split] - prior_exact.get(split, 0.0) for split in ("train", "dev", "test")}
        if rerun_status == "observed"
        else {}
    )
    prompt_policy_visible = (
        all(prompt_policy_by_split[split]["hardened_canonical_policy_visible"] for split in ("train", "dev", "test"))
        if rerun_status == "observed"
        else False
    )
    public_heldout_recovered = rerun_status == "observed" and prompt_policy_visible and all(
        hardened_exact.get(split, 0.0) >= 1.0 for split in ("dev", "test")
    )
    interpretation = _hardened_policy_interpretation(
        rerun_status=rerun_status,
        split_results=split_results,
        prior_exact=prior_exact,
        prompt_policy_by_split=prompt_policy_by_split,
    )
    safe_prediction_metadata = _sanitize_report_value(prediction_metadata_by_split)
    evidence = {
        "evidence_kind": "a100_hardened_canonical_policy_rerun",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "rerun_status": rerun_status,
        "blocked_reason": blocked_reason if rerun_status == "blocked" else None,
        "base_model": "Qwen/Qwen2.5-7B-Instruct",
        "dataset_manifest_id": public_manifest.get("manifest_id"),
        "formal_public_sample_counts": public_manifest.get("counts", {}),
        "formal_public_sample_split_counts": public_manifest.get("split_counts", {}),
        "source_adapter_runtime": "a100-merged-slot-value-heldout-eval",
        "training_status": "prediction_only_no_training",
        "prediction_splits": ["train", "dev", "test"],
        "primary_evidence_splits": ["dev", "test"],
        "split_results": split_results,
        "prompt_policy_by_split": prompt_policy_by_split,
        "comparison": {
            "prior_merged_slot_value_exact": prior_exact,
            "hardened_canonical_policy_exact": hardened_exact,
            "dev_test_exact_delta": {split: exact_delta[split] for split in ("dev", "test")}
            if exact_delta
            else {},
            "train_exact_delta": exact_delta.get("train") if exact_delta else None,
        },
        "overall_interpretation": interpretation,
        "claims": {
            "prediction_only_rerun": True,
            "training_performed": False,
            "data_changed": False,
            "evaluator_relaxation": False,
            "prediction_repair_or_replacement": False,
            "hardened_prompt_policy_visible": prompt_policy_visible,
            "public_sample_heldout_strict_exact_recovered": public_heldout_recovered,
            "held_out_generalization_recovered": public_heldout_recovered,
            "model_recovery_claim": False,
            "private_corpus_generalization_claim": False,
            "adapter_release": False,
            "checkpoint_release": False,
            "production_readiness_claim": False,
            "live_browser_benchmark_claim": False,
            "semantic_equivalence_primary_metric": False,
            "soft_slot_f1_primary_metric": False,
        },
        "artifact_policy": {
            "raw_logs_copied_to_git": False,
            "checkpoints_or_adapters_copied_to_git": False,
            "remote_caches_copied_to_git": False,
            "private_overrides_copied_to_git": False,
            "private_paths_omitted": True,
            "host_details_omitted": True,
            "ssh_details_omitted": True,
            "private_corpus_rows_omitted": True,
        },
        "prediction_metadata_by_split": safe_prediction_metadata,
    }
    safe_evidence = _sanitize_report_value(evidence)
    write_json(json_path, safe_evidence)
    manifest = {
        "evidence_kind": "a100_hardened_canonical_policy_rerun",
        "generated_at": safe_evidence["generated_at"],
        "rerun_status": safe_evidence["rerun_status"],
        "blocked_reason": safe_evidence["blocked_reason"],
        "dataset_manifest_id": safe_evidence["dataset_manifest_id"],
        "formal_public_sample_counts": safe_evidence["formal_public_sample_counts"],
        "prediction_splits": safe_evidence["prediction_splits"],
        "primary_evidence_splits": safe_evidence["primary_evidence_splits"],
        "split_results": safe_evidence["split_results"],
        "prompt_policy_by_split": safe_evidence["prompt_policy_by_split"],
        "comparison": safe_evidence["comparison"],
        "overall_interpretation": safe_evidence["overall_interpretation"],
        "claims": safe_evidence["claims"],
        "artifact_policy": safe_evidence["artifact_policy"],
        "diagnostic_artifacts": {
            "evidence": _public_report_artifact_path(output_dir, "hardened_canonical_policy_rerun.json"),
            "manifest": _public_report_artifact_path(output_dir, "manifest.json"),
            "report": _public_report_artifact_path(output_dir, "report.md"),
            "prior_merged_manifest": "reports/public-sample/a100-merged-slot-value-heldout-eval/manifest.json",
        },
    }
    write_json(manifest_path, manifest)

    lines = [
        "# A100 hardened canonical policy rerun",
        "",
        (
            "Status: prediction-only hardened prompt rerun. This phase reuses the prior merged slot-value "
            "7B adapter and does not train, repair, normalize, or re-score predictions."
        ),
        "",
        "## Scope",
        "",
        f"- Dataset manifest: `{safe_evidence['dataset_manifest_id']}`",
        f"- Rerun status: `{safe_evidence['rerun_status']}`",
        f"- Source adapter runtime: `{safe_evidence['source_adapter_runtime']}`",
        f"- Overall interpretation: `{safe_evidence['overall_interpretation']}`",
    ]
    if rerun_status == "blocked":
        lines.extend(
            [
                f"- Blocked reason: `{safe_evidence['blocked_reason']}`",
                "",
                "## Blocked Status",
                "",
                (
                    "Blocked before private prediction. No A100 prediction, training, metric comparison, "
                    "or model-quality evidence was produced."
                ),
            ]
        )
    else:
        lines.extend(
            [
                "",
                "## Split Results",
                "",
                (
                    "| split | rows | contract_exact_match | prior exact | delta | slot_f1 | "
                    "json_valid_rate | residual rows | hardened prompt visible |"
                ),
                "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
            ]
        )
        for split in ("train", "dev", "test"):
            result = safe_evidence["split_results"][split]
            policy = safe_evidence["prompt_policy_by_split"][split]
            delta = safe_evidence["comparison"]["hardened_canonical_policy_exact"][split] - safe_evidence["comparison"][
                "prior_merged_slot_value_exact"
            ].get(split, 0.0)
            lines.append(
                f"| {split} | {result['prediction_count']} | {result['contract_exact_match']:.4f} | "
                f"{safe_evidence['comparison']['prior_merged_slot_value_exact'].get(split, 0.0):.4f} | "
                f"{delta:.4f} | {result['slot_f1']:.4f} | {result['json_valid_rate']:.4f} | "
                f"{result['residual_row_count']} | {policy['hardened_canonical_policy_visible']} |"
            )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- strict `contract_exact_match` remains primary.",
            "- Train exact match, JSON-valid rate, and soft slot F1 are not model recovery claims.",
            "- Predictions are not repaired, replaced, normalized, or re-scored.",
            (
                "- This is not new training, checkpoint release, adapter release, production-readiness evidence, "
                "private-corpus generalization evidence, public full-corpus release, or a live-browser benchmark claim."
            ),
        ]
    )
    report_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return {"json": json_path, "manifest": manifest_path, "report": report_path}


def write_a100_merged_slot_value_adapter_restore_report(
    *,
    public_manifest: dict[str, Any],
    prior_merged_manifest: dict[str, Any],
    output_dir: Path,
    restore_status: str,
    acquisition_method: str,
    blocked_reason: str | None = None,
    adapter_checks: dict[str, bool] | None = None,
    training_metadata: dict[str, Any] | None = None,
    dependency_status: str = "not_recorded",
    gpu_status: str = "not_recorded",
) -> dict[str, Path]:
    if prior_merged_manifest.get("evidence_kind") != "a100_merged_slot_value_heldout_eval":
        raise ValueError("prior merged manifest must be a100_merged_slot_value_heldout_eval evidence")
    if restore_status not in {"available", "blocked"}:
        raise ValueError(f"unsupported adapter restore status: {restore_status}")
    if acquisition_method not in {"restored", "regenerated", "not_available"}:
        raise ValueError(f"unsupported adapter acquisition method: {acquisition_method}")
    if restore_status == "available" and acquisition_method not in {"restored", "regenerated"}:
        raise ValueError("available adapter restore requires restored or regenerated acquisition")
    if restore_status == "blocked" and acquisition_method != "not_available":
        raise ValueError("blocked adapter restore requires not_available acquisition")
    if restore_status == "blocked" and not (blocked_reason or "").strip():
        raise ValueError("blocked adapter restore requires a blocked_reason")
    adapter_checks = dict(adapter_checks or {})
    adapter_available = (
        restore_status == "available"
        and bool(adapter_checks.get("adapter_config.json"))
        and bool(
            adapter_checks.get("adapter_model.safetensors")
            or adapter_checks.get("adapter_model.bin")
        )
    )
    if restore_status == "available" and not adapter_available:
        raise ValueError("available adapter restore requires adapter_config.json and adapter model file checks")
    safe_training_metadata = _sanitize_report_value(training_metadata or {})
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "merged_slot_value_adapter_restore.json"
    manifest_path = output_dir / "manifest.json"
    report_path = output_dir / "report.md"
    leak_scan_path = output_dir / "leak_scan_result.json"
    evidence = {
        "evidence_kind": "a100_merged_slot_value_adapter_restore",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "restore_status": restore_status,
        "acquisition_method": acquisition_method,
        "blocked_reason": blocked_reason if restore_status == "blocked" else None,
        "adapter_available": adapter_available,
        "source_adapter_runtime": "a100-merged-slot-value-heldout-eval",
        "target_adapter_path_policy": "<a100_project_root>/runs/a100-merged-slot-value-heldout-eval/adapter",
        "base_model": "Qwen/Qwen2.5-7B-Instruct",
        "dataset_manifest_id": public_manifest.get("manifest_id"),
        "formal_public_sample_counts": public_manifest.get("counts", {}),
        "prior_merged_reference": {
            "evidence_kind": prior_merged_manifest.get("evidence_kind"),
            "manifest": "reports/public-sample/a100-merged-slot-value-heldout-eval/manifest.json",
            "metrics_role": "historical_prior_only_not_this_phase",
        },
        "dependency_status": dependency_status,
        "gpu_status": gpu_status,
        "required_adapter_files": adapter_checks if restore_status == "available" else {},
        "training_metadata": safe_training_metadata,
        "claims": {
            "adapter_prerequisite_available": adapter_available,
            "prediction_metrics_produced": False,
            "hardened_policy_rerun_completed": False,
            "model_recovery_claim": False,
            "adapter_release": False,
            "checkpoint_release": False,
            "private_corpus_generalization_claim": False,
            "production_readiness_claim": False,
            "live_browser_benchmark_claim": False,
            "evaluator_relaxation": False,
            "prediction_repair_or_replacement": False,
        },
        "artifact_policy": {
            "raw_logs_copied_to_git": False,
            "checkpoints_or_adapters_copied_to_git": False,
            "remote_caches_copied_to_git": False,
            "private_overrides_copied_to_git": False,
            "private_paths_omitted": True,
            "host_details_omitted": True,
            "ssh_details_omitted": True,
            "private_corpus_rows_omitted": True,
        },
    }
    safe_evidence = _sanitize_report_value(evidence)
    write_json(json_path, safe_evidence)
    manifest = {
        "evidence_kind": "a100_merged_slot_value_adapter_restore",
        "generated_at": safe_evidence["generated_at"],
        "restore_status": safe_evidence["restore_status"],
        "acquisition_method": safe_evidence["acquisition_method"],
        "blocked_reason": safe_evidence["blocked_reason"],
        "adapter_available": safe_evidence["adapter_available"],
        "dataset_manifest_id": safe_evidence["dataset_manifest_id"],
        "source_adapter_runtime": safe_evidence["source_adapter_runtime"],
        "dependency_status": safe_evidence["dependency_status"],
        "gpu_status": safe_evidence["gpu_status"],
        "required_adapter_files": safe_evidence["required_adapter_files"],
        "claims": safe_evidence["claims"],
        "artifact_policy": safe_evidence["artifact_policy"],
        "diagnostic_artifacts": {
            "evidence": (
                "reports/public-sample/a100-merged-slot-value-adapter-restore/"
                "merged_slot_value_adapter_restore.json"
            ),
            "manifest": "reports/public-sample/a100-merged-slot-value-adapter-restore/manifest.json",
            "report": "reports/public-sample/a100-merged-slot-value-adapter-restore/report.md",
            "leak_scan": "reports/public-sample/a100-merged-slot-value-adapter-restore/leak_scan_result.json",
            "prior_merged_manifest": "reports/public-sample/a100-merged-slot-value-heldout-eval/manifest.json",
        },
    }
    write_json(manifest_path, manifest)
    lines = [
        "# A100 merged slot value adapter restore",
        "",
        (
            "Status: prerequisite adapter evidence. This report records whether the private merged "
            "slot-value adapter is available for later prediction-only evaluation."
        ),
        "",
        "## Scope",
        "",
        f"- Dataset manifest: `{safe_evidence['dataset_manifest_id']}`",
        f"- Restore status: `{safe_evidence['restore_status']}`",
        f"- Acquisition method: `{safe_evidence['acquisition_method']}`",
        f"- Adapter available: `{safe_evidence['adapter_available']}`",
        f"- Dependency status: `{safe_evidence['dependency_status']}`",
        f"- GPU status: `{safe_evidence['gpu_status']}`",
    ]
    if restore_status == "blocked":
        lines.append(f"- Blocked reason: `{safe_evidence['blocked_reason']}`")
    lines.extend(
        [
            "",
            "## Adapter Checks",
            "",
        ]
    )
    if safe_evidence["required_adapter_files"]:
        for name, present in sorted(safe_evidence["required_adapter_files"].items()):
            lines.append(f"- `{name}`: `{present}`")
    else:
        lines.append("- no adapter files accepted")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- This phase produces no train/dev/test prediction metrics.",
            "- This is not a checkpoint release or adapter release.",
            (
                "- This is not model recovery, private-corpus generalization, "
                "production-readiness, or live-browser benchmark evidence."
            ),
            "- Public evidence leak scan is recorded in `leak_scan_result.json`.",
        ]
    )
    report_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    leak_scan_result = scan_paths([json_path, manifest_path, report_path])
    write_json(
        leak_scan_path,
        {
            "evidence_kind": "a100_merged_slot_value_adapter_restore_leak_scan",
            "generated_at": safe_evidence["generated_at"],
            "paths_scanned": [json_path.name, manifest_path.name, report_path.name],
            "ok": leak_scan_result.ok,
            "finding_count": len(leak_scan_result.findings),
            "findings": _sanitize_report_value([finding.__dict__ for finding in leak_scan_result.findings]),
        },
    )
    return {"json": json_path, "manifest": manifest_path, "report": report_path, "leak_scan": leak_scan_path}


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
