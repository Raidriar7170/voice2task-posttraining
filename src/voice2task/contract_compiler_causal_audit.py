from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Any

from voice2task.contract_core_v2 import (
    ContractCoreV2Error,
    build_v1_compatible_envelope,
    project_v1_to_core_v2,
)
from voice2task.contract_v2_projection import deterministic_normalized_command_renderer
from voice2task.schemas import ValidationError, as_contract, validate_contract_status

AUDIT_INPUT_WHITELIST = (
    "src/voice2task/formatting.py",
    "src/voice2task/training.py",
    "src/voice2task/schemas.py",
    "src/voice2task/evaluation.py",
    "src/voice2task/contract_core_v2.py",
    "src/voice2task/contract_v2_projection.py",
    "data/public-samples/seed_traces.jsonl",
    "data/public-samples/manifest_public_sample.json",
    "reports/public-sample/split-integrity-audit/summary.json",
    "reports/public-sample/internal-contract-v2-core/summary.json",
    "CONTEXT.md",
    "data/lockbox/lockbox-v1.manifest.json",
    "reports/lockbox-v1/final-evaluation/run-card.json",
    "reports/lockbox-v1/final-evaluation/base/metrics.json",
    "reports/lockbox-v1/final-evaluation/final-sft/metrics.json",
    "reports/lockbox-v1/final-evaluation/comparison.json",
)

EXPECTED_SOURCE_SHA256 = {
    "src/voice2task/formatting.py": "a5933b89f9f9b43358619b15264047bc449a83dacadfc3e49db88d38d434a8f0",
    "src/voice2task/training.py": "978e2df42be7b1e020c5215febaf843a527b0fb96469273c93b66ce20b62db3c",
    "src/voice2task/schemas.py": "e5897b622dbcac398c28b14d264b99fb98ae749cf278cda1cdd9e83a4300d74f",
    "src/voice2task/evaluation.py": "568f4f41d2d6b0b5d45e68c53e14c5c6b70ebb37227c988a0b4b5aff8017e228",
    "src/voice2task/contract_core_v2.py": "ed77d5a21af3a868c3b9ff0fa81c62da29bfe939070c39fb3c8a0076f8c29098",
    "src/voice2task/contract_v2_projection.py": (
        "b35c2b47ea73d96a484b96f3c6d4d38e510a58c5c2fb0ebf389e6da36e3a59b9"
    ),
    "data/public-samples/seed_traces.jsonl": (
        "8fe5e75e9e0891b6824d7c142cbe15547267377420f8b3240414436265d15801"
    ),
    "data/public-samples/manifest_public_sample.json": (
        "f866c173795e97953b1dec85611b405867d0a29497910282f99d399f109cda95"
    ),
    "reports/public-sample/split-integrity-audit/summary.json": (
        "ac10bd0a1c3fefb717433de68ae29d049069b521bae8599234b7f52faec8f598"
    ),
    "reports/public-sample/internal-contract-v2-core/summary.json": (
        "b4cbee7220cb8d9564c4a90a1b0469b27b0eb666b5aed572ff58749994d67d20"
    ),
    "CONTEXT.md": "2ffc67d81be8b3e482555efd23db5b0bf60239eb4ef4d9e24514cae24ea1009f",
    "data/lockbox/lockbox-v1.manifest.json": (
        "72471bac59749f3bc9d21d73db47dafe1f160b978f5ac3971434e13527ddedde"
    ),
    "reports/lockbox-v1/final-evaluation/run-card.json": (
        "39e59cd6e16baa7adadb6b3c474e7fce8bfe8223e5980a1288a1c50432acec66"
    ),
    "reports/lockbox-v1/final-evaluation/base/metrics.json": (
        "400fa753e6e8bde611af4e4f9623155ceff6664454bfea0f57748043243cd02f"
    ),
    "reports/lockbox-v1/final-evaluation/final-sft/metrics.json": (
        "aaecc8dcdad90e70c0f8a7c59a21d2e65d8d42bae3e304e4dce9b049390bc829"
    ),
    "reports/lockbox-v1/final-evaluation/comparison.json": (
        "48fae0e85e016c1872477881939716076d96998d0c63f83adf1e9be42d9ed544"
    ),
}

HISTORICAL_SOURCE_SNAPSHOT_OVERRIDES = {
    "src/voice2task/training.py": (
        "reports/public-sample/contract-compiler-v2-causal-boundary/source-snapshots/"
        "training.978e2df42be7b1e020c5215febaf843a527b0fb96469273c93b66ce20b62db3c.py"
    ),
    "CONTEXT.md": (
        "reports/public-sample/contract-compiler-v2-causal-boundary/source-snapshots/"
        "CONTEXT.2ffc67d81be8b3e482555efd23db5b0bf60239eb4ef4d9e24514cae24ea1009f.md"
    )
}

DENIED_INPUTS = (
    "data/lockbox/lockbox-v1.jsonl",
    "data/lockbox/lockbox-v1.draft.jsonl",
    "reports/lockbox-v1/final-evaluation/row-failures.jsonl",
    "raw/private-predictions/",
    "private-corpora/",
    ".cache/",
    "adapters/",
    "checkpoints/",
)


def _validate_audit_input_path(relative_path: str) -> str:
    raw_path = str(relative_path)
    if not raw_path or "\\" in raw_path:
        raise ValueError(f"audit input path must be a non-empty repo-relative POSIX path: {raw_path!r}")
    path = PurePosixPath(raw_path)
    is_windows_drive_path = len(raw_path) >= 2 and raw_path[0].isalpha() and raw_path[1] == ":"
    if path.is_absolute() or is_windows_drive_path:
        raise ValueError(f"audit input path must be repo-relative: {raw_path}")
    if ".." in path.parts:
        raise ValueError(f"audit input path traversal is forbidden: {raw_path}")
    normalized = path.as_posix()
    if normalized in {"", "."}:
        raise ValueError(f"audit input path must name a file: {raw_path!r}")
    for denied in DENIED_INPUTS:
        denied_boundary = denied.rstrip("/")
        if normalized == denied_boundary or normalized.startswith(f"{denied_boundary}/"):
            raise ValueError(f"audit input path is denylisted: {normalized}")
    return normalized


def _validated_whitelist_paths() -> tuple[str, ...]:
    paths = tuple(_validate_audit_input_path(path) for path in AUDIT_INPUT_WHITELIST)
    if len(set(paths)) != len(paths):
        raise ValueError("audit input path whitelist contains duplicates after normalization")
    return paths


def _resolve_audit_source_path(repo_root: Path, logical_path: str) -> Path:
    logical_path = _validate_audit_input_path(logical_path)
    if logical_path not in _validated_whitelist_paths():
        raise ValueError(f"audit source logical path is not in the exact whitelist: {logical_path}")
    physical_path = HISTORICAL_SOURCE_SNAPSHOT_OVERRIDES.get(logical_path, logical_path)
    physical_path = _validate_audit_input_path(physical_path)
    try:
        resolved_root = repo_root.resolve(strict=True)
    except (FileNotFoundError, RuntimeError) as exc:
        raise ValueError(f"required audit source root missing: {repo_root}") from exc
    expected_path = resolved_root / physical_path
    try:
        resolved_path = expected_path.resolve(strict=True)
    except (FileNotFoundError, RuntimeError) as exc:
        raise ValueError(f"required audit source missing: {logical_path}") from exc
    if resolved_path != expected_path:
        raise ValueError(
            f"audit source symlink or alternate logical location is forbidden: {logical_path}"
        )
    try:
        resolved_path.relative_to(resolved_root)
    except ValueError as exc:
        raise ValueError(f"audit source resolves outside repository: {logical_path}") from exc
    if not resolved_path.is_file():
        raise ValueError(f"required audit source is not a regular file: {logical_path}")
    return resolved_path


def _validated_audit_source_paths(repo_root: Path) -> tuple[Path, ...]:
    return tuple(
        _resolve_audit_source_path(repo_root, logical_path)
        for logical_path in _validated_whitelist_paths()
    )


def _audit_source_bytes(repo_root: Path, logical_path: str) -> bytes:
    return _resolve_audit_source_path(repo_root, logical_path).read_bytes()


def _sha256(repo_root: Path, relative_path: str) -> str:
    relative_path = _validate_audit_input_path(relative_path)
    return hashlib.sha256(_audit_source_bytes(repo_root, relative_path)).hexdigest()


def _source_text(repo_root: Path, relative_path: str) -> str:
    relative_path = _validate_audit_input_path(relative_path)
    return _audit_source_bytes(repo_root, relative_path).decode("utf-8")


def _decoding_inventory(repo_root: Path) -> list[dict[str, Any]]:
    controls = (
        ("json_only_prompting", True, "src/voice2task/formatting.py", "PREDICTION_SYSTEM_PROMPT"),
        ("greedy_decoding", True, "src/voice2task/training.py", "_decode_prediction_attempt"),
        ("do_sample_false", True, "src/voice2task/training.py", '"do_sample": False'),
        (
            "markdown_fence_suppression",
            True,
            "src/voice2task/training.py",
            "_markdown_fence_bad_words_ids",
        ),
        (
            "post_generation_strict_parse_schema_guard",
            True,
            "src/voice2task/training.py",
            "_schema_guard_status",
        ),
        ("schema_retry_max_one", True, "src/voice2task/training.py", "schema_retry_max_attempts"),
        (
            "token_level_grammar_json_schema_constrained_decoding",
            False,
            "src/voice2task/training.py",
            "_decode_prediction_attempt",
        ),
    )
    records = [
        {
            "control": name,
            "present": present,
            "classification": "PRESENT" if present else "ABSENT",
            "source_path": path,
            "source_sha256": _sha256(repo_root, path),
            "stable_identity": identity,
        }
        for name, present, path, identity in controls
    ]
    records[-1].update(
        {
            "inspected_callsite": "model.generate(**generation_kwargs)",
            "absence_terms": [
                "prefix_allowed_tokens_fn",
                "constraints",
                "force_words_ids",
                "grammar",
                "json_schema",
            ],
        }
    )
    return records


def _rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 6) if denominator else 0.0


def _renderer_audit(repo_root: Path) -> dict[str, Any]:
    seed_path = repo_root / "data/public-samples/seed_traces.jsonl"
    rows = [json.loads(line) for line in seed_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(rows) != 247:
        raise ValueError(f"formal seed population drifted: expected 247 rows, found {len(rows)}")

    parse_valid = supported = deterministic = stable = legacy_exact = policy_consistent = 0
    for row in rows:
        try:
            contract = as_contract(row["target_contract"])
        except (KeyError, TypeError, ValidationError):
            continue
        parse_valid += 1
        try:
            core = project_v1_to_core_v2(contract)
            first = deterministic_normalized_command_renderer(core.to_dict())
            second = deterministic_normalized_command_renderer(core.to_dict())
        except (TypeError, ValidationError, ContractCoreV2Error):
            continue
        stable += int(first == second)
        if not first["supported"]:
            continue
        supported += 1
        deterministic += int(first == second)
        legacy_exact += int(first["normalized_command"] == contract.normalized_command)
        rebuilt = build_v1_compatible_envelope(core, mode="derive_display")
        policy_consistent += int(validate_contract_status(rebuilt)["semantic_valid"])

    legacy_mismatch = supported - legacy_exact
    historical = json.loads(
        (repo_root / "reports/public-sample/internal-contract-v2-core/summary.json").read_text(
            encoding="utf-8"
        )
    )
    historical_rate = float(historical["derive_display_supported_rate"])
    historical_unsupported = int(historical["derive_display_unsupported_count"])
    historical_denominator = round(historical_unsupported / (1.0 - historical_rate))
    return {
        "population": {
            "observation_unit": "one_formal_seed_row",
            "source_path": "data/public-samples/seed_traces.jsonl",
            "manifest_path": "data/public-samples/manifest_public_sample.json",
            "fixed_itt_denominator": 247,
            "deduplicated": False,
            "selected_or_tuned_on_public_dev_test": False,
            "classification": "DESCRIPTIVE_ONLY",
        },
        "counts": {
            "parse_valid": parse_valid,
            "parse_invalid": 247 - parse_valid,
            "supported": supported,
            "unsupported": parse_valid - supported,
            "supported_and_deterministic": deterministic,
            "repeated_outcome_stable": stable,
            "legacy_exact": legacy_exact,
            "legacy_mismatch": legacy_mismatch,
            "policy_self_consistent": policy_consistent,
        },
        "itt": {
            "denominator": 247,
            "legacy_exact": {"numerator": legacy_exact, "rate": _rate(legacy_exact, 247)},
            "policy_self_consistent": {
                "numerator": policy_consistent,
                "rate": _rate(policy_consistent, 247),
            },
        },
        "supported_only_secondary": {
            "denominator": supported,
            "legacy_exact": {"numerator": legacy_exact, "rate": _rate(legacy_exact, supported)},
            "policy_self_consistent": {
                "numerator": policy_consistent,
                "rate": _rate(policy_consistent, supported),
            },
        },
        "invalid_and_unsupported_count_as_itt_failures": True,
        "historical_support_interpretation": {
            "numerator": historical_denominator - historical_unsupported,
            "denominator": historical_denominator,
            "rate": historical_rate,
            "canonical_exact_compatibility": False,
            "warning": "99.77% support is not legacy canonical exact compatibility.",
        },
    }


def _field_authority() -> list[dict[str, Any]]:
    semantic_fields = (
        "intent",
        "risk",
        "clarification",
        "slots.query",
        "slots.url",
        "slots.field",
        "slots.value",
        "slots.target",
        "slots.ambiguity",
        "slots.reason",
    )
    v1_fields = (
        "task_type",
        "route",
        "safety.allow",
        "safety.reason",
        "confirmation_required",
        "slots.query",
        "slots.url",
        "slots.field",
        "slots.value",
        "slots.target",
        "slots.ambiguity",
        "slots.reason",
        "normalized_command",
        "language",
        "contract_version",
    )
    participation = (
        "raw_core_validity",
        "policy_self_consistency",
        "strict_v1_exact",
        "downstream_execution_gate",
    )
    records = [
        {
            "field_path": f"semantic_core.{field}",
            "value_origin": "model_authored",
            "authority_status": "HYPOTHETICAL_UNSPECIFIED",
            "constraint_owner": "candidate_semantic_core_schema_unspecified",
            "constraint_owner_status": "HYPOTHETICAL_UNSPECIFIED",
            "transform": "candidate_model_output_transform_unspecified",
            "transform_status": "HYPOTHETICAL_UNSPECIFIED",
            "source_path": "CONTEXT.md",
            "source_rule_or_symbol": "candidate_semantic_core",
            "source_anchor": "candidate_semantic_core",
            "participation": {key: "HYPOTHETICAL" for key in participation},
            "mutable_at_candidate_compiler_stage": False,
        }
        for field in semantic_fields
    ]
    for field in v1_fields:
        if field == "normalized_command":
            origin, transform = "renderer_derived", "deterministic_renderer"
            constraint_owner = "BrowserTaskContract.normalized_command_nonempty_string"
            source_rule = '_require_nonempty_string(self.normalized_command, "normalized_command")'
            field_participation = {
                "raw_core_validity": "DOES_NOT_PARTICIPATE",
                "policy_self_consistency": "DOES_NOT_PARTICIPATE",
                "strict_v1_exact": "PARTICIPATES",
                "downstream_execution_gate": "DOES_NOT_PARTICIPATE",
            }
        elif field == "language":
            origin, transform = "constant", "constant_assignment"
            constraint_owner = "BrowserTaskContract.language_literal_zh-CN"
            source_rule = 'if self.language != "zh-CN":'
            field_participation = {
                "raw_core_validity": "DOES_NOT_PARTICIPATE",
                "policy_self_consistency": "DOES_NOT_PARTICIPATE",
                "strict_v1_exact": "PARTICIPATES",
                "downstream_execution_gate": "DOES_NOT_PARTICIPATE",
            }
        elif field == "contract_version":
            origin, transform = "constant", "constant_assignment"
            constraint_owner = "BrowserTaskContract.contract_version_literal_v1"
            source_rule = 'if self.contract_version != "v1":'
            field_participation = {
                "raw_core_validity": "DOES_NOT_PARTICIPATE",
                "policy_self_consistency": "DOES_NOT_PARTICIPATE",
                "strict_v1_exact": "PARTICIPATES",
                "downstream_execution_gate": "DOES_NOT_PARTICIPATE",
            }
        elif field == "slots.value":
            origin, transform = "model_authored", "copy_from_semantic_core"
            constraint_owner = "BrowserTaskContract.slots_object_schema"
            source_rule = 'raise ValidationError("slots must be an object")'
            field_participation = {key: "PARTICIPATES" for key in participation}
            field_participation["policy_self_consistency"] = "DOES_NOT_PARTICIPATE"
        elif field.startswith("slots."):
            origin, transform = "model_authored", "copy_from_semantic_core"
            constraint_owner = "TASK_TYPE_SEMANTICS.required_slots"
            slot_name = field.removeprefix("slots.")
            source_rule = f'"required_slots": ("{slot_name}",)'
            field_participation = {key: "PARTICIPATES" for key in participation}
        elif field == "task_type":
            origin, transform = "policy_derived", "candidate_policy_table"
            constraint_owner = "TASK_TYPES"
            source_rule = "TASK_TYPES ="
            field_participation = {key: "PARTICIPATES" for key in participation}
        else:
            origin, transform = "policy_derived", "candidate_policy_table"
            constraint_owner = "TASK_TYPE_SEMANTICS"
            source_rule = {
                "route": '"route":',
                "safety.allow": '"safety_allow":',
                "safety.reason": '"safety_reason":',
                "confirmation_required": '"confirmation_required":',
            }[field]
            field_participation = {key: "PARTICIPATES" for key in participation}
        records.append(
            {
                "field_path": f"v1.{field}",
                "value_origin": origin,
                "authority_status": "HYPOTHETICAL",
                "constraint_owner": constraint_owner,
                "constraint_owner_status": "CURRENT_SOURCE_VERIFIED",
                "transform": transform,
                "transform_status": "HYPOTHETICAL",
                "source_path": "src/voice2task/schemas.py",
                "source_rule_or_symbol": source_rule,
                "source_anchor": source_rule,
                "participation": field_participation,
                "mutable_at_candidate_compiler_stage": not field.startswith("slots."),
            }
        )
    return records


def _causal_estimands() -> dict[str, dict[str, Any]]:
    compiler_invariants = [
        "raw_core_identity",
        "row_and_order_identity",
        "source_hash_identity",
        "prompt_and_decoding_identity",
        "evaluator_identity",
        "no_prediction_repair",
    ]
    model_invariants = [
        "matched_data_boundary_identity",
        "eligible_evaluation_identity",
        "row_and_order_identity",
        "prompt_and_decoding_identity",
        "compiler_policy_identity",
        "evaluator_identity",
        "optimization_budget_identity",
        "no_prediction_repair",
    ]
    confounders = [
        "spent_public_dev_test_reuse",
        "cross_split_template_or_provenance_contamination",
        "single_seed_or_unmatched_training",
        "renderer_policy_mismatch",
        "compiler_filled_metrics",
        "prompt_or_decoding_change",
        "evaluator_version_change",
        "post_hoc_selection",
    ]
    return {
        "system_compiler": {
            "status": "CAUSAL_IDENTIFICATION_BLOCKED",
            "observation_unit": "one_frozen_raw_core_record",
            "eligible_population": "future_preregistered_clean_fixed_evaluation_population",
            "intervention": "candidate_compiler_over_identical_frozen_raw_core",
            "control": "identity_or_preserve_legacy_over_identical_frozen_raw_core",
            "outcomes": ["compiled_v1_strict_exact_itt", "safety_and_slot_guardrails"],
            "denominators": {"primary": "full_fixed_itt", "secondary": "supported_only_diagnostic"},
            "invalid_or_unsupported_handling": "count_as_primary_itt_failure",
            "matched_arm_requirements": [
                "same_model_output",
                "same_data",
                "same_prompt_and_decoding",
                "same_evaluator_version",
            ],
            "invariants": compiler_invariants,
            "confounders": confounders,
            "negative_controls": ["constant_only", "field_copy_only", "policy_default_only", "plumbing_only"],
            "status_reasons": ["no_preregistered_clean_matched_compiler_comparison"],
            "effect_label_if_future_identified": "system_compiler_transformation_effect",
        },
        "model_learning": {
            "status": "CAUSAL_IDENTIFICATION_BLOCKED",
            "observation_unit": "one_preregistered_evaluation_family",
            "eligible_population": "future_clean_family_level_evaluation_set",
            "intervention": "matched_training_arm_with_predeclared_multi_seed_aggregation",
            "control": "matched_training_control_arm",
            "outcomes": ["family_level_model_authored_field_quality", "uncertainty_and_guardrails"],
            "denominators": {"primary": "all_preregistered_eligible_families"},
            "invalid_or_unsupported_handling": "retain_as_failure_without_compiler_attribution",
            "matched_arm_requirements": [
                "same_data_boundary",
                "same_prompt_and_decoding",
                "same_optimization_budget",
                "same_compiler_policy",
                "same_evaluator_version",
                "same_eligible_evaluation_set",
            ],
            "invariants": model_invariants,
            "confounders": confounders,
            "negative_controls": ["compiler_filled_fields", "constant_fields", "field_copying", "evaluation_plumbing"],
            "status_reasons": [
                "public_dev_test_spent",
                "one_look_lockbox_consumed",
                "no_clean_matched_multi_seed_training_arms",
            ],
        },
    }


def _source_manifest(repo_root: Path) -> list[dict[str, str]]:
    whitelist_paths = _validated_whitelist_paths()
    if set(EXPECTED_SOURCE_SHA256) != set(whitelist_paths):
        raise ValueError("expected-hash manifest contains an extra or missing whitelist input")
    manifest = []
    for path in whitelist_paths:
        try:
            actual_hash = _sha256(repo_root, path)
        except FileNotFoundError as exc:
            raise ValueError(f"required audit input missing: {path}") from exc
        if actual_hash != EXPECTED_SOURCE_SHA256[path]:
            raise ValueError(f"required audit input hash drift: {path}")
        manifest.append({"path": path, "sha256": actual_hash})
    return manifest


def _validate_source_anchors(
    repo_root: Path,
    decoding_inventory: list[dict[str, Any]],
    transformation_graphs: dict[str, Any],
    field_authority: list[dict[str, Any]],
) -> dict[str, Any]:
    graph_records = [
        record
        for graph in transformation_graphs.values()
        for group in ("nodes", "edges")
        for record in graph[group]
    ]
    checked = 0
    for record in [*decoding_inventory, *graph_records, *field_authority]:
        source_path = str(record["source_path"])
        anchor_value = record.get("source_anchor")
        if anchor_value is None:
            anchor_value = record.get("stable_identity")
        if not anchor_value:
            raise ValueError(f"source anchor missing from audit record: {source_path}")
        anchor = str(anchor_value)
        if source_path not in AUDIT_INPUT_WHITELIST:
            raise ValueError(f"source anchor path is not whitelisted: {source_path}")
        if anchor not in _source_text(repo_root, source_path):
            raise ValueError(f"source anchor missing: {source_path}::{anchor}")
        checked += 1

    absent = next(
        record
        for record in decoding_inventory
        if record["control"] == "token_level_grammar_json_schema_constrained_decoding"
    )
    training_source = _source_text(repo_root, str(absent["source_path"]))
    start = training_source.find("def _decode_prediction_attempt(")
    end = training_source.find("\ndef ", start + 1)
    callsite_body = training_source[start : len(training_source) if end == -1 else end]
    if start == -1 or str(absent["inspected_callsite"]) not in callsite_body:
        raise ValueError("source anchor missing: inspected decoding callsite")
    contradicted = [term for term in absent["absence_terms"] if term in callsite_body]
    if contradicted:
        raise ValueError(f"absent decoding control contradicted by source: {contradicted}")
    return {
        "passed": True,
        "source_anchor_records_checked": checked,
        "absent_generation_controls_checked": 1,
    }


def _graph_source_anchor(source_path: str, stable_identity: str) -> str:
    if source_path == "CONTEXT.md" or stable_identity.startswith("final_prediction"):
        return stable_identity
    return f"def {stable_identity}("


def build_contract_compiler_causal_audit(repo_root: Path) -> dict[str, Any]:
    _validated_audit_source_paths(repo_root)
    observed_nodes = [
        ("json_only_prompt", "src/voice2task/formatting.py", "format_sft_prediction_prompt", True),
        ("raw_decode", "src/voice2task/training.py", "_decode_prediction_attempt", True),
        ("raw_strict_parse", "src/voice2task/training.py", "_extract_strict_json_object", True),
        ("raw_schema_guard", "src/voice2task/training.py", "_schema_guard_status", True),
        ("retry_instruction", "src/voice2task/training.py", "_schema_retry_prompt", True),
        (
            "retry_prompt_format",
            "src/voice2task/formatting.py",
            "format_schema_retry_prompt_text",
            True,
        ),
        ("retry_decode", "src/voice2task/training.py", "_decode_prediction_attempt", True),
        ("retry_strict_parse", "src/voice2task/training.py", "_extract_strict_json_object", True),
        ("retry_schema_guard", "src/voice2task/training.py", "_schema_guard_status", True),
        ("validated_output_selection", "src/voice2task/training.py", "_build_schema_guard", True),
        ("exported_prediction", "src/voice2task/training.py", "final_prediction = (", True),
        ("strict_evaluation", "src/voice2task/evaluation.py", "evaluate_predictions", True),
        (
            "contract_core_v2",
            "src/voice2task/contract_core_v2.py",
            "project_v1_to_core_v2",
            False,
        ),
        (
            "deterministic_renderer",
            "src/voice2task/contract_v2_projection.py",
            "deterministic_normalized_command_renderer",
            False,
        ),
    ]
    observed_edges = [
        (
            "json_only_prompt",
            "raw_decode",
            "src/voice2task/training.py",
            "_decode_prediction_attempt",
            True,
            "raw_attempt",
            False,
            "always",
        ),
        (
            "raw_decode",
            "raw_strict_parse",
            "src/voice2task/training.py",
            "_extract_strict_json_object",
            True,
            "raw_attempt",
            False,
            "always",
        ),
        (
            "raw_strict_parse",
            "raw_schema_guard",
            "src/voice2task/training.py",
            "_schema_guard_status",
            True,
            "raw_attempt",
            False,
            "always",
        ),
        (
            "raw_schema_guard",
            "validated_output_selection",
            "src/voice2task/training.py",
            "_build_schema_guard",
            True,
            "raw_valid_direct",
            True,
            'raw_status["schema_valid"]',
        ),
        (
            "raw_schema_guard",
            "validated_output_selection",
            "src/voice2task/training.py",
            "_build_schema_guard",
            True,
            "raw_invalid_no_retry",
            True,
            'not raw_status["schema_valid"] and not schema_retry_enabled',
        ),
        (
            "raw_schema_guard",
            "retry_instruction",
            "src/voice2task/training.py",
            "_schema_retry_prompt",
            True,
            "raw_invalid_retry",
            True,
            'schema_retry_enabled and not raw_status["schema_valid"]',
        ),
        (
            "retry_instruction",
            "retry_prompt_format",
            "src/voice2task/formatting.py",
            "format_schema_retry_prompt_text",
            True,
            "raw_invalid_retry",
            True,
            "retry_attempted",
        ),
        (
            "retry_prompt_format",
            "retry_decode",
            "src/voice2task/training.py",
            "_decode_prediction_attempt",
            True,
            "raw_invalid_retry",
            True,
            "retry_attempted",
        ),
        (
            "retry_decode",
            "retry_strict_parse",
            "src/voice2task/training.py",
            "_extract_strict_json_object",
            True,
            "raw_invalid_retry",
            True,
            "retry_attempted",
        ),
        (
            "retry_strict_parse",
            "retry_schema_guard",
            "src/voice2task/training.py",
            "_schema_guard_status",
            True,
            "raw_invalid_retry",
            True,
            "retry_attempted",
        ),
        (
            "retry_schema_guard",
            "validated_output_selection",
            "src/voice2task/training.py",
            "_build_schema_guard",
            True,
            "raw_invalid_retry",
            True,
            "retry_status is not None",
        ),
        (
            "validated_output_selection",
            "exported_prediction",
            "src/voice2task/training.py",
            "final_prediction = (",
            True,
            "retry_valid_selected",
            True,
            'schema_guard["validated_output_source"] == "retry_attempt"',
        ),
        (
            "validated_output_selection",
            "exported_prediction",
            "src/voice2task/training.py",
            "final_prediction = (",
            True,
            "raw_or_invalid_fallback",
            True,
            'schema_guard["validated_output_source"] != "retry_attempt"',
        ),
        (
            "exported_prediction",
            "strict_evaluation",
            "src/voice2task/evaluation.py",
            "evaluate_predictions",
            True,
            "evaluation",
            False,
            "always",
        ),
        (
            "exported_prediction",
            "contract_core_v2",
            "src/voice2task/contract_core_v2.py",
            "project_v1_to_core_v2",
            False,
            "offline_core_projection",
            False,
            "offline_audit_only",
        ),
        (
            "contract_core_v2",
            "deterministic_renderer",
            "src/voice2task/contract_v2_projection.py",
            "deterministic_normalized_command_renderer",
            False,
            "offline_renderer",
            False,
            "offline_audit_only",
        ),
    ]
    candidate_source = "CONTEXT.md"
    transformation_graphs = {
        "observed_current": {
            "implementation_status": "IMPLEMENTED_OBSERVED",
            "nodes": [
                {
                    "id": node_id,
                    "source_path": path,
                    "stable_identity": identity,
                    "source_anchor": _graph_source_anchor(path, identity),
                    "runtime_wired": runtime_wired,
                }
                for node_id, path, identity, runtime_wired in observed_nodes
            ],
            "edges": [
                {
                    "from": source,
                    "to": target,
                    "source_path": path,
                    "stable_identity": identity,
                    "source_anchor": _graph_source_anchor(path, identity),
                    "runtime_wired": runtime_wired,
                    "branch": branch,
                    "conditional": conditional,
                    "condition": condition,
                }
                for (
                    source,
                    target,
                    path,
                    identity,
                    runtime_wired,
                    branch,
                    conditional,
                    condition,
                ) in observed_edges
            ],
        },
        "candidate_only": {
            "implementation_status": "NOT_IMPLEMENTED_HYPOTHETICAL",
            "nodes": [
                {
                    "id": "candidate_semantic_core",
                    "source_path": candidate_source,
                    "stable_identity": "candidate_semantic_core",
                    "source_anchor": "candidate_semantic_core",
                    "runtime_wired": False,
                },
                {
                    "id": "candidate_v1_compiler",
                    "source_path": candidate_source,
                    "stable_identity": "candidate_v1_compiler",
                    "source_anchor": "candidate_v1_compiler",
                    "runtime_wired": False,
                },
            ],
            "edges": [
                {
                    "from": "candidate_semantic_core",
                    "to": "candidate_v1_compiler",
                    "source_path": candidate_source,
                    "stable_identity": "candidate_semantic_core_to_v1_compiler",
                    "source_anchor": "candidate_semantic_core_to_v1_compiler",
                    "runtime_wired": False,
                }
            ],
        },
    }
    field_authority = _field_authority()
    decoding_inventory = _decoding_inventory(repo_root)
    source_manifest = _source_manifest(repo_root)
    source_anchor_validation = _validate_source_anchors(
        repo_root, decoding_inventory, transformation_graphs, field_authority
    )
    renderer_audit = _renderer_audit(repo_root)
    return {
        "audit_status": "ARCHIVED",
        "causal_estimands": _causal_estimands(),
        "decoding_inventory": decoding_inventory,
        "evidence_classification": {
            "renderer_mechanics": "DESCRIPTIVE_ONLY",
            "full_compiler_causal_identification": "CAUSAL_IDENTIFICATION_BLOCKED",
            "model_learning_causal_identification": "CAUSAL_IDENTIFICATION_BLOCKED",
        },
        "evidence_status_reasons": {
            "renderer_mechanics": {
                "status": "DESCRIPTIVE_ONLY",
                "reasons": [
                    "fixed_seed_population_includes_development_only_spent_public_dev_test",
                    "renderer_support_and_self_consistency_do_not_supply_intervention_control_arms",
                    "policy_self_consistency_is_not_external_semantic_correctness",
                ],
            },
            "full_compiler_causal_identification": {
                "status": "CAUSAL_IDENTIFICATION_BLOCKED",
                "reasons": [
                    "candidate_compiler_not_implemented_or_runtime_wired",
                    "no_preregistered_clean_matched_compiler_control_and_intervention",
                    "public_dev_test_are_development_only_spent",
                    "lockbox_v1_one_look_evidence_already_consumed",
                ],
            },
            "model_learning_causal_identification": {
                "status": "CAUSAL_IDENTIFICATION_BLOCKED",
                "reasons": [
                    "no_clean_eligible_evaluation_set",
                    "no_matched_multi_seed_training_arms_or_predeclared_uncertainty",
                    "public_dev_test_are_development_only_spent",
                    "lockbox_v1_one_look_evidence_already_consumed",
                ],
            },
        },
        "execution_and_claim_flags": {
            "training_run": False,
            "prediction_run": False,
            "a100_execution": False,
            "data_mutation": False,
            "prompt_change": False,
            "evaluator_default_change": False,
            "compiler_implementation": False,
            "decoder_implementation": False,
            "historical_metrics_rescored": False,
            "lockbox_row_level_read": False,
            "clean_evaluation_run": False,
            "public_dev_test_selection": False,
            "model_improvement_claim": False,
            "heldout_recovery_claim": False,
            "natural_asr_generalization_claim": False,
            "checkpoint_release": False,
            "adapter_release": False,
            "production_readiness_claim": False,
            "safety_readiness_claim": False,
            "live_browser_benchmark_improvement_claim": False,
        },
        "field_authority": field_authority,
        "input_policy": {
            "wide_directory_glob_used": False,
            "denied_input_read": False,
            "renderer_source_paths": [
                "data/public-samples/seed_traces.jsonl",
                "data/public-samples/manifest_public_sample.json",
            ],
            "whitelist_enforced": True,
        },
        "methodology_version": "contract-compiler-v2-causal-audit.v1",
        "next_phase_recommendations": [
            {
                "phase": "preregister-clean-matched-compiler-and-model-evidence-design",
                "requires": [
                    "preregistration",
                    "clean_evaluation_population",
                    "matched_control_and_intervention_arms",
                    "multiple_training_seeds_and_predeclared_uncertainty",
                    "machine_checked_invariants",
                ],
                "executed": False,
            }
        ],
        "renderer_audit": renderer_audit,
        "source_anchor_validation": source_anchor_validation,
        "source_manifest": source_manifest,
        "transformation_graphs": transformation_graphs,
    }


def _summary_markdown(audit: dict[str, Any]) -> str:
    renderer = audit["renderer_audit"]
    counts = renderer["counts"]
    itt_denominator = renderer["itt"]["denominator"]
    supported_denominator = renderer["supported_only_secondary"]["denominator"]
    flags = audit["execution_and_claim_flags"]
    sources = audit["source_manifest"]
    lines = [
        "# Contract Compiler V2 causal boundary audit",
        "",
        "Status: `ARCHIVED`.",
        "",
        "## Conclusion",
        "",
        "Both compiler and model-learning causal estimands are `CAUSAL_IDENTIFICATION_BLOCKED`; "
        "renderer and transformation mechanics are `DESCRIPTIVE_ONLY`.",
        "",
        "**99.77% support is not legacy canonical exact compatibility.** Historical `2180/2185` "
        "measures renderer support, not equality with legacy canonical targets.",
        "",
        f"## Fixed {itt_denominator}-row renderer population",
        "",
        f"- Parse valid: `{counts['parse_valid']}/{itt_denominator}`",
        f"- Supported and deterministic: "
        f"`{counts['supported_and_deterministic']}/{itt_denominator}`",
        f"- Repeated outcome stable: `{counts['repeated_outcome_stable']}/{itt_denominator}`",
        f"- Legacy exact: `{counts['legacy_exact']}/{itt_denominator}` "
        f"(`{renderer['itt']['legacy_exact']['rate']}`)",
        f"- Legacy mismatch among supported rows: `{counts['legacy_mismatch']}`",
        f"- Supported-only legacy exact (secondary): "
        f"`{counts['legacy_exact']}/{supported_denominator}` "
        f"(`{renderer['supported_only_secondary']['legacy_exact']['rate']}`)",
        f"- Policy self-consistent ITT: "
        f"`{counts['policy_self_consistent']}/{itt_denominator}` "
        f"(`{renderer['itt']['policy_self_consistent']['rate']}`)",
        "",
        "## Architecture boundary",
        "",
        "Observed paths are `IMPLEMENTED_OBSERVED`; the candidate compiler graph is "
        "`NOT_IMPLEMENTED_HYPOTHETICAL` with `runtime_wired=false`.",
        "",
        "## Audit-only scope",
        "",
        *[f"- `{name}=false`" for name, value in sorted(flags.items()) if value is False],
        "",
        "## Bound sources",
        "",
        *[f"- `{record['path']}` — `{record['sha256']}`" for record in sources],
        "",
    ]
    return "\n".join(lines)


def render_contract_compiler_causal_audit(repo_root: Path, output_dir: Path) -> dict[str, Any]:
    audit = build_contract_compiler_causal_audit(repo_root)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "summary.json").write_text(
        json.dumps(audit, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output_dir / "summary.md").write_text(_summary_markdown(audit), encoding="utf-8")
    return audit
