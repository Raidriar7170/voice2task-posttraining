from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

import voice2task.contract_compiler_causal_audit as audit_module
from voice2task.contract_compiler_causal_audit import (
    AUDIT_INPUT_WHITELIST,
    DENIED_INPUTS,
    build_contract_compiler_causal_audit,
    render_contract_compiler_causal_audit,
)
from voice2task.contract_core_v2 import ContractCoreV2Error

REPO_ROOT = Path(__file__).resolve().parents[1]
HISTORICAL_CONTEXT_SHA256 = "2ffc67d81be8b3e482555efd23db5b0bf60239eb4ef4d9e24514cae24ea1009f"
HISTORICAL_CONTEXT_SNAPSHOT = (
    "reports/public-sample/contract-compiler-v2-causal-boundary/"
    f"source-snapshots/CONTEXT.{HISTORICAL_CONTEXT_SHA256}.md"
)
HISTORICAL_TRAINING_SHA256 = "978e2df42be7b1e020c5215febaf843a527b0fb96469273c93b66ce20b62db3c"
HISTORICAL_TRAINING_SNAPSHOT = (
    "reports/public-sample/contract-compiler-v2-causal-boundary/"
    f"source-snapshots/training.{HISTORICAL_TRAINING_SHA256}.py"
)
HISTORICAL_MANIFEST_SHA256 = "f866c173795e97953b1dec85611b405867d0a29497910282f99d399f109cda95"
HISTORICAL_MANIFEST_SNAPSHOT = (
    "reports/public-sample/formal-manifest-history/"
    f"manifest_public_sample.{HISTORICAL_MANIFEST_SHA256}.json"
)
HISTORICAL_SPLIT_SUMMARY_SHA256 = "ac10bd0a1c3fefb717433de68ae29d049069b521bae8599234b7f52faec8f598"
HISTORICAL_SPLIT_SUMMARY_SNAPSHOT = (
    "reports/public-sample/split-integrity-audit/source-snapshots/"
    f"summary.{HISTORICAL_SPLIT_SUMMARY_SHA256}.json"
)


def _audit() -> dict[str, object]:
    return build_contract_compiler_causal_audit(REPO_ROOT)


def test_audit_separates_source_linked_observed_and_hypothetical_candidate_graphs() -> None:
    audit = _audit()
    graphs = audit["transformation_graphs"]

    assert set(graphs) == {"observed_current", "candidate_only"}
    assert graphs["observed_current"]["implementation_status"] == "IMPLEMENTED_OBSERVED"
    assert graphs["candidate_only"]["implementation_status"] == "NOT_IMPLEMENTED_HYPOTHETICAL"
    for node in graphs["observed_current"]["nodes"]:
        assert node["source_path"] in AUDIT_INPUT_WHITELIST
        assert node["stable_identity"]
    for edge in graphs["observed_current"]["edges"]:
        assert edge["source_path"] in AUDIT_INPUT_WHITELIST
        assert edge["stable_identity"]
    for node in graphs["candidate_only"]["nodes"]:
        assert node["source_path"] in AUDIT_INPUT_WHITELIST
        assert node["stable_identity"]
        assert node["runtime_wired"] is False
    for edge in graphs["candidate_only"]["edges"]:
        assert edge["source_path"] in AUDIT_INPUT_WHITELIST
        assert edge["stable_identity"]
    assert all(edge["runtime_wired"] is False for edge in graphs["candidate_only"]["edges"])
    observed_nodes = {node["id"]: node for node in graphs["observed_current"]["nodes"]}
    assert observed_nodes["contract_core_v2"]["runtime_wired"] is False
    assert observed_nodes["deterministic_renderer"]["runtime_wired"] is False
    offline_edges = [
        edge
        for edge in graphs["observed_current"]["edges"]
        if edge["to"] in {"contract_core_v2", "deterministic_renderer"}
    ]
    assert offline_edges
    assert all(edge["runtime_wired"] is False for edge in offline_edges)


def test_observed_graph_models_raw_valid_and_conditional_retry_branches() -> None:
    observed = _audit()["transformation_graphs"]["observed_current"]
    nodes = {node["id"]: node for node in observed["nodes"]}
    required_nodes = {
        "json_only_prompt",
        "raw_decode",
        "raw_strict_parse",
        "raw_schema_guard",
        "retry_instruction",
        "retry_prompt_format",
        "retry_decode",
        "retry_strict_parse",
        "retry_schema_guard",
        "validated_output_selection",
        "exported_prediction",
        "strict_evaluation",
    }
    assert required_nodes <= set(nodes)
    assert nodes["raw_strict_parse"]["stable_identity"] == "_extract_strict_json_object"
    assert nodes["retry_instruction"]["stable_identity"] == "_schema_retry_prompt"
    assert nodes["retry_prompt_format"]["stable_identity"] == "format_schema_retry_prompt_text"
    assert nodes["validated_output_selection"]["stable_identity"] == "_build_schema_guard"

    edges = {(edge["from"], edge["to"], edge["branch"]): edge for edge in observed["edges"]}
    direct = edges[("raw_schema_guard", "validated_output_selection", "raw_valid_direct")]
    assert direct["conditional"] is True
    assert direct["condition"] == 'raw_status["schema_valid"]'
    no_retry = edges[("raw_schema_guard", "validated_output_selection", "raw_invalid_no_retry")]
    assert no_retry["conditional"] is True
    assert no_retry["condition"] == (
        'not raw_status["schema_valid"] and not schema_retry_enabled'
    )
    retry_start = edges[("raw_schema_guard", "retry_instruction", "raw_invalid_retry")]
    assert retry_start["conditional"] is True
    assert retry_start["condition"] == 'schema_retry_enabled and not raw_status["schema_valid"]'
    for source, target in (
        ("retry_instruction", "retry_prompt_format"),
        ("retry_prompt_format", "retry_decode"),
        ("retry_decode", "retry_strict_parse"),
        ("retry_strict_parse", "retry_schema_guard"),
        ("retry_schema_guard", "validated_output_selection"),
    ):
        assert edges[(source, target, "raw_invalid_retry")]["conditional"] is True
    retry_selected = edges[
        ("validated_output_selection", "exported_prediction", "retry_valid_selected")
    ]
    assert retry_selected["condition"] == (
        'schema_guard["validated_output_source"] == "retry_attempt"'
    )
    raw_selected = edges[
        ("validated_output_selection", "exported_prediction", "raw_or_invalid_fallback")
    ]
    assert raw_selected["condition"] == (
        'schema_guard["validated_output_source"] != "retry_attempt"'
    )


def test_retry_branch_source_anchor_disappearance_fails_closed(monkeypatch: Any) -> None:
    real_source_text = audit_module._source_text

    def hide_retry_anchor(repo_root: Path, relative_path: str) -> str:
        text = real_source_text(repo_root, relative_path)
        if relative_path == "src/voice2task/training.py":
            return text.replace("def _schema_retry_prompt(", "def removed_retry_anchor(", 1)
        return text

    monkeypatch.setattr(audit_module, "_source_text", hide_retry_anchor)

    with pytest.raises(ValueError, match="source anchor"):
        build_contract_compiler_causal_audit(REPO_ROOT)


def test_field_authority_covers_intermediates_and_v1_leaves_with_three_dimensions() -> None:
    audit = _audit()
    authority = {record["field_path"]: record for record in audit["field_authority"]}
    required = {
        "semantic_core.intent",
        "semantic_core.risk",
        "semantic_core.clarification",
        "semantic_core.slots.query",
        "semantic_core.slots.url",
        "semantic_core.slots.field",
        "semantic_core.slots.value",
        "semantic_core.slots.target",
        "semantic_core.slots.ambiguity",
        "semantic_core.slots.reason",
        "v1.task_type",
        "v1.route",
        "v1.safety.allow",
        "v1.safety.reason",
        "v1.confirmation_required",
        "v1.slots.query",
        "v1.slots.url",
        "v1.slots.field",
        "v1.slots.value",
        "v1.slots.target",
        "v1.slots.ambiguity",
        "v1.slots.reason",
        "v1.normalized_command",
        "v1.language",
        "v1.contract_version",
    }
    assert required <= set(authority)
    for field_path in required:
        record = authority[field_path]
        assert record["value_origin"] in {
            "model_authored",
            "policy_derived",
            "renderer_derived",
            "constant",
            "verifier_derived",
        }
        assert record["constraint_owner"]
        assert record["transform"]
        assert record["source_rule_or_symbol"]
        assert record["source_path"] in AUDIT_INPUT_WHITELIST
        assert set(record["participation"]) == {
            "raw_core_validity",
            "policy_self_consistency",
            "strict_v1_exact",
            "downstream_execution_gate",
        }
        assert set(record["participation"].values()) <= {
            "PARTICIPATES",
            "DOES_NOT_PARTICIPATE",
            "HYPOTHETICAL",
        }
        assert record["authority_status"]
        assert record["constraint_owner_status"]
        assert record["transform_status"]
        assert isinstance(record["mutable_at_candidate_compiler_stage"], bool)
    semantic_records = [
        record for field_path, record in authority.items() if field_path.startswith("semantic_core.")
    ]
    assert all(set(record["participation"].values()) == {"HYPOTHETICAL"} for record in semantic_records)
    assert all(record["authority_status"] == "HYPOTHETICAL_UNSPECIFIED" for record in semantic_records)
    assert all(
        record["constraint_owner_status"] == "HYPOTHETICAL_UNSPECIFIED"
        for record in semantic_records
    )
    assert all(record["transform_status"] == "HYPOTHETICAL_UNSPECIFIED" for record in semantic_records)
    copied_v1_slots = [
        record for field_path, record in authority.items() if field_path.startswith("v1.slots.")
    ]
    assert all(record["transform"] == "copy_from_semantic_core" for record in copied_v1_slots)
    assert all(record["mutable_at_candidate_compiler_stage"] is False for record in copied_v1_slots)
    v1_records = [record for field_path, record in authority.items() if field_path.startswith("v1.")]
    assert all(record["constraint_owner_status"] == "CURRENT_SOURCE_VERIFIED" for record in v1_records)
    assert all(record["transform_status"] == "HYPOTHETICAL" for record in v1_records)
    semantics_owned = (
        "v1.route",
        "v1.safety.allow",
        "v1.safety.reason",
        "v1.confirmation_required",
    )
    assert all(authority[field]["constraint_owner"] == "TASK_TYPE_SEMANTICS" for field in semantics_owned)
    required_slot_fields = (
        "v1.slots.query",
        "v1.slots.url",
        "v1.slots.field",
        "v1.slots.target",
        "v1.slots.ambiguity",
        "v1.slots.reason",
    )
    assert all(
        authority[field]["constraint_owner"] == "TASK_TYPE_SEMANTICS.required_slots"
        for field in required_slot_fields
    )
    assert all(
        authority[field]["participation"]["policy_self_consistency"] == "PARTICIPATES"
        for field in required_slot_fields
    )
    expected_field_anchors = {
        "v1.route": '"route":',
        "v1.safety.allow": '"safety_allow":',
        "v1.safety.reason": '"safety_reason":',
        "v1.confirmation_required": '"confirmation_required":',
        "v1.slots.query": '"required_slots": ("query",)',
        "v1.slots.url": '"required_slots": ("url",)',
        "v1.slots.field": '"required_slots": ("field",)',
        "v1.slots.target": '"required_slots": ("target",)',
        "v1.slots.ambiguity": '"required_slots": ("ambiguity",)',
        "v1.slots.reason": '"required_slots": ("reason",)',
    }
    assert {
        field: authority[field]["source_rule_or_symbol"] for field in expected_field_anchors
    } == expected_field_anchors
    assert authority["v1.task_type"]["constraint_owner"] == "TASK_TYPES"
    assert all(
        record["constraint_owner"] != "BrowserTaskContract.TASK_TYPES"
        for record in authority.values()
    )
    assert authority["v1.slots.value"]["constraint_owner"] == "BrowserTaskContract.slots_object_schema"
    assert "required_slots" not in authority["v1.slots.value"]["constraint_owner"]
    assert authority["v1.slots.value"]["participation"]["policy_self_consistency"] == (
        "DOES_NOT_PARTICIPATE"
    )
    assert authority["v1.normalized_command"]["constraint_owner"] == (
        "BrowserTaskContract.normalized_command_nonempty_string"
    )
    assert "renderer" not in authority["v1.normalized_command"]["constraint_owner"]
    assert authority["v1.language"]["constraint_owner"] == (
        "BrowserTaskContract.language_literal_zh-CN"
    )
    assert authority["v1.contract_version"]["constraint_owner"] == (
        "BrowserTaskContract.contract_version_literal_v1"
    )
    for field in ("v1.normalized_command", "v1.language", "v1.contract_version"):
        assert authority[field]["participation"]["raw_core_validity"] == "DOES_NOT_PARTICIPATE"
        assert authority[field]["participation"]["policy_self_consistency"] == (
            "DOES_NOT_PARTICIPATE"
        )
        assert authority[field]["participation"]["strict_v1_exact"] == "PARTICIPATES"
    current_core_fields = {
        "v1.task_type",
        "v1.route",
        "v1.safety.allow",
        "v1.safety.reason",
        "v1.confirmation_required",
        "v1.slots.query",
        "v1.slots.url",
        "v1.slots.field",
        "v1.slots.value",
        "v1.slots.target",
        "v1.slots.ambiguity",
        "v1.slots.reason",
    }
    assert all(
        authority[field]["participation"]["raw_core_validity"] == "PARTICIPATES"
        for field in current_core_fields
    )


def test_field_authority_source_anchor_disappearance_fails_closed(monkeypatch: Any) -> None:
    real_source_text = audit_module._source_text

    def hide_field_anchor(repo_root: Path, relative_path: str) -> str:
        text = real_source_text(repo_root, relative_path)
        if relative_path == "src/voice2task/schemas.py":
            return text.replace("TASK_TYPES =", "REMOVED_TASK_ENUM =", 1)
        return text

    monkeypatch.setattr(audit_module, "_source_text", hide_field_anchor)

    with pytest.raises(ValueError, match="source anchor"):
        build_contract_compiler_causal_audit(REPO_ROOT)


def test_decoding_inventory_distinguishes_prompt_and_post_generation_guards_from_constraints() -> None:
    audit = _audit()
    controls = {record["control"]: record for record in audit["decoding_inventory"]}

    expected_present = {
        "json_only_prompting": True,
        "greedy_decoding": True,
        "do_sample_false": True,
        "markdown_fence_suppression": True,
        "post_generation_strict_parse_schema_guard": True,
        "schema_retry_max_one": True,
        "token_level_grammar_json_schema_constrained_decoding": False,
    }
    assert {name: controls[name]["present"] for name in expected_present} == expected_present
    for record in controls.values():
        assert record["source_path"] in AUDIT_INPUT_WHITELIST
        assert len(record["source_sha256"]) == 64
        assert record["stable_identity"]
    assert controls["token_level_grammar_json_schema_constrained_decoding"]["classification"] == "ABSENT"
    absent = controls["token_level_grammar_json_schema_constrained_decoding"]
    assert absent["stable_identity"] == "_decode_prediction_attempt"
    assert absent["inspected_callsite"] == "model.generate(**generation_kwargs)"
    assert set(absent["absence_terms"]) == {
        "prefix_allowed_tokens_fn",
        "constraints",
        "force_words_ids",
        "grammar",
        "json_schema",
    }


def test_renderer_audit_fixes_full_itt_population_and_keeps_support_separate_from_exact() -> None:
    renderer = _audit()["renderer_audit"]

    assert renderer["population"] == {
        "observation_unit": "one_formal_seed_row",
        "source_path": "data/public-samples/seed_traces.jsonl",
        "manifest_path": "data/public-samples/manifest_public_sample.json",
        "fixed_itt_denominator": 247,
        "deduplicated": False,
        "selected_or_tuned_on_public_dev_test": False,
        "classification": "DESCRIPTIVE_ONLY",
    }
    assert renderer["counts"] == {
        "parse_valid": 247,
        "parse_invalid": 0,
        "supported": 246,
        "unsupported": 1,
        "supported_and_deterministic": 246,
        "repeated_outcome_stable": 247,
        "legacy_exact": 98,
        "legacy_mismatch": 148,
        "policy_self_consistent": 246,
    }
    assert renderer["itt"]["denominator"] == 247
    assert renderer["itt"]["legacy_exact"]["numerator"] == 98
    assert renderer["itt"]["legacy_exact"]["rate"] == 0.396761
    assert renderer["itt"]["policy_self_consistent"]["rate"] == 0.995951
    assert renderer["supported_only_secondary"]["denominator"] == 246
    assert renderer["supported_only_secondary"]["legacy_exact"]["rate"] == 0.398374
    assert renderer["supported_only_secondary"]["policy_self_consistent"]["rate"] == 1.0
    assert renderer["invalid_and_unsupported_count_as_itt_failures"] is True
    assert renderer["historical_support_interpretation"]["rate"] == 0.9977116704805492
    assert renderer["historical_support_interpretation"]["canonical_exact_compatibility"] is False
    assert "support" in renderer["historical_support_interpretation"]["warning"].lower()


def test_renderer_failure_does_not_reclassify_a_schema_valid_seed_as_parse_invalid(
    monkeypatch: Any,
) -> None:
    real_renderer = audit_module.deterministic_normalized_command_renderer
    failed_once = False

    def fail_first_renderer(core: dict[str, Any]) -> dict[str, Any]:
        nonlocal failed_once
        if not failed_once:
            failed_once = True
            raise ContractCoreV2Error("injected renderer failure")
        return real_renderer(core)

    monkeypatch.setattr(audit_module, "deterministic_normalized_command_renderer", fail_first_renderer)
    renderer = build_contract_compiler_causal_audit(REPO_ROOT)["renderer_audit"]

    assert renderer["counts"]["parse_valid"] == 247
    assert renderer["counts"]["parse_invalid"] == 0


def test_policy_self_consistency_requires_semantic_validation(monkeypatch: Any) -> None:
    real_validate = audit_module.validate_contract_status
    invalidated_once = False

    def invalidate_one_supported_contract(value: Any) -> dict[str, Any]:
        nonlocal invalidated_once
        status = real_validate(value)
        if status["semantic_valid"] and not invalidated_once:
            invalidated_once = True
            status = {**status, "semantic_valid": False}
        return status

    monkeypatch.setattr(audit_module, "validate_contract_status", invalidate_one_supported_contract)
    renderer = build_contract_compiler_causal_audit(REPO_ROOT)["renderer_audit"]

    assert invalidated_once is True
    assert renderer["counts"]["policy_self_consistent"] == 245


def test_causal_estimands_fail_closed_with_required_controls_and_one_bounded_next_phase() -> None:
    audit = _audit()
    estimands = audit["causal_estimands"]

    assert set(estimands) == {"system_compiler", "model_learning"}
    assert estimands["system_compiler"]["status"] == "CAUSAL_IDENTIFICATION_BLOCKED"
    assert estimands["model_learning"]["status"] == "CAUSAL_IDENTIFICATION_BLOCKED"
    for estimand in estimands.values():
        for key in (
            "observation_unit",
            "eligible_population",
            "intervention",
            "control",
            "outcomes",
            "denominators",
            "invalid_or_unsupported_handling",
            "matched_arm_requirements",
            "invariants",
            "confounders",
            "negative_controls",
            "status_reasons",
        ):
            assert estimand[key]
    assert audit["evidence_classification"]["renderer_mechanics"] == "DESCRIPTIVE_ONLY"
    assert audit["evidence_classification"]["full_compiler_causal_identification"] == (
        "CAUSAL_IDENTIFICATION_BLOCKED"
    )
    assert audit["evidence_classification"]["model_learning_causal_identification"] == (
        "CAUSAL_IDENTIFICATION_BLOCKED"
    )
    status_reasons = audit["evidence_status_reasons"]
    assert status_reasons["renderer_mechanics"]["status"] == "DESCRIPTIVE_ONLY"
    assert status_reasons["full_compiler_causal_identification"]["status"] == (
        "CAUSAL_IDENTIFICATION_BLOCKED"
    )
    assert status_reasons["model_learning_causal_identification"]["status"] == (
        "CAUSAL_IDENTIFICATION_BLOCKED"
    )
    assert all(record["reasons"] for record in status_reasons.values())
    compiler_invariants = set(estimands["system_compiler"]["invariants"])
    model_invariants = set(estimands["model_learning"]["invariants"])
    assert "raw_core_identity" in compiler_invariants
    assert "raw_core_identity" not in model_invariants
    assert {
        "matched_data_boundary_identity",
        "eligible_evaluation_identity",
        "row_and_order_identity",
        "prompt_and_decoding_identity",
        "compiler_policy_identity",
        "evaluator_identity",
        "optimization_budget_identity",
        "no_prediction_repair",
    } <= model_invariants
    model_requirements = set(estimands["model_learning"]["matched_arm_requirements"])
    assert "same_eligible_evaluation_set" in model_requirements
    assert "same_evaluator_version" in model_requirements
    assert len(audit["next_phase_recommendations"]) == 1
    recommendation = audit["next_phase_recommendations"][0]
    assert recommendation["phase"] == "preregister-clean-matched-compiler-and-model-evidence-design"
    assert recommendation["executed"] is False
    assert "preregistration" in recommendation["requires"]


def test_whitelist_denylist_and_false_scope_flags_are_fail_closed() -> None:
    audit = _audit()
    source_paths = {record["path"] for record in audit["source_manifest"]}

    assert source_paths == set(AUDIT_INPUT_WHITELIST)
    assert all(len(record["sha256"]) == 64 for record in audit["source_manifest"])
    assert "data/public-samples/sft_public_sample.jsonl" not in source_paths
    assert "data/public-samples/dpo_public_sample.jsonl" not in source_paths
    assert "data/lockbox/lockbox-v1.jsonl" in DENIED_INPUTS
    assert "data/lockbox/lockbox-v1.draft.jsonl" in DENIED_INPUTS
    assert audit["input_policy"]["wide_directory_glob_used"] is False
    assert audit["input_policy"]["denied_input_read"] is False
    assert audit["input_policy"]["renderer_source_paths"] == [
        "data/public-samples/seed_traces.jsonl",
        "data/public-samples/manifest_public_sample.json",
    ]
    assert audit["execution_and_claim_flags"]
    assert set(audit["execution_and_claim_flags"].values()) == {False}


@pytest.mark.parametrize(
    "forbidden_path",
    (
        "data/lockbox/lockbox-v1.jsonl",
        "data/lockbox/lockbox-v1.jsonl/child",
        "private-corpora/forbidden.jsonl",
        "adapters/x",
        "../outside.json",
        "/absolute/outside.json",
        "C:outside.json",
        "C:/outside.json",
    ),
)
def test_forbidden_whitelist_path_fails_before_any_hash_or_read(
    monkeypatch: Any,
    forbidden_path: str,
) -> None:
    monkeypatch.setattr(
        audit_module,
        "AUDIT_INPUT_WHITELIST",
        (*AUDIT_INPUT_WHITELIST, forbidden_path),
    )
    accesses: list[tuple[str, str]] = []

    def forbidden_hash(_repo_root: Path, relative_path: str) -> str:
        accesses.append(("hash", relative_path))
        raise AssertionError("hash must not run before whitelist path validation")

    def forbidden_read(_repo_root: Path, relative_path: str) -> str:
        accesses.append(("read", relative_path))
        raise AssertionError("read must not run before whitelist path validation")

    monkeypatch.setattr(audit_module, "_sha256", forbidden_hash)
    monkeypatch.setattr(audit_module, "_source_text", forbidden_read)

    with pytest.raises(ValueError, match="audit input path"):
        build_contract_compiler_causal_audit(REPO_ROOT)
    assert accesses == []


@pytest.mark.parametrize(
    "safe_path",
    (
        "data/lockbox/lockbox-v1.jsonl.bak",
        "raw/private-predictions-safe/public-summary.json",
    ),
)
def test_denylist_near_names_remain_allowed(safe_path: str) -> None:
    assert audit_module._validate_audit_input_path(safe_path) == safe_path


def test_source_manifest_and_candidate_graph_use_durable_context_not_active_change_paths() -> None:
    audit = _audit()
    source_paths = {record["path"] for record in audit["source_manifest"]}
    candidate = audit["transformation_graphs"]["candidate_only"]

    assert "CONTEXT.md" in source_paths
    assert not any(path.startswith("openspec/changes/") for path in source_paths)
    assert {node["source_path"] for node in candidate["nodes"]} == {"CONTEXT.md"}
    assert {edge["source_path"] for edge in candidate["edges"]} == {"CONTEXT.md"}


def test_source_anchor_validation_fails_closed_when_present_symbol_disappears(monkeypatch: Any) -> None:
    real_source_text = audit_module._source_text

    def hide_decode_anchor(repo_root: Path, relative_path: str) -> str:
        text = real_source_text(repo_root, relative_path)
        if relative_path == "src/voice2task/training.py":
            return text.replace("def _decode_prediction_attempt(", "def removed_decode_anchor(", 1)
        return text

    monkeypatch.setattr(audit_module, "_source_text", hide_decode_anchor)

    with pytest.raises(ValueError, match="source anchor"):
        build_contract_compiler_causal_audit(REPO_ROOT)


def test_source_manifest_rejects_one_byte_hash_drift(monkeypatch: Any) -> None:
    real_sha256 = audit_module._sha256

    def one_byte_drift(repo_root: Path, relative_path: str) -> str:
        if relative_path == "src/voice2task/formatting.py":
            content = (repo_root / relative_path).read_bytes() + b"x"
            return hashlib.sha256(content).hexdigest()
        return real_sha256(repo_root, relative_path)

    monkeypatch.setattr(audit_module, "_sha256", one_byte_drift)

    with pytest.raises(ValueError, match="hash drift"):
        build_contract_compiler_causal_audit(REPO_ROOT)


def test_reports_are_byte_deterministic_and_public_safe(tmp_path: Path) -> None:
    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"

    first = render_contract_compiler_causal_audit(REPO_ROOT, first_dir)
    second = render_contract_compiler_causal_audit(REPO_ROOT, second_dir)

    assert first == second
    for name in ("summary.json", "summary.md"):
        assert (first_dir / name).read_bytes() == (second_dir / name).read_bytes()
    parsed = json.loads((first_dir / "summary.json").read_text(encoding="utf-8"))
    assert parsed == _audit()
    assert parsed["audit_status"] == "ARCHIVED"
    markdown = (first_dir / "summary.md").read_text(encoding="utf-8")
    assert "99.77% support is not legacy canonical exact compatibility" in markdown
    assert "CAUSAL_IDENTIFICATION_BLOCKED" in markdown
    assert "NOT_IMPLEMENTED_HYPOTHETICAL" in markdown
    assert str(REPO_ROOT) not in markdown


def test_summary_markdown_uses_audit_denominators_instead_of_fixed_literals() -> None:
    audit = _audit()
    renderer = audit["renderer_audit"]
    renderer["counts"].update(
        {
            "parse_valid": 9,
            "supported_and_deterministic": 8,
            "repeated_outcome_stable": 10,
            "legacy_exact": 3,
            "policy_self_consistent": 7,
        }
    )
    renderer["itt"]["denominator"] = 10
    renderer["supported_only_secondary"]["denominator"] = 8

    markdown = audit_module._summary_markdown(audit)

    for expected in ("`9/10`", "`8/10`", "`10/10`", "`3/10`", "`3/8`", "`7/10`"):
        assert expected in markdown
    assert "/247`" not in markdown
    assert "/246`" not in markdown


def test_historical_context_snapshot_is_exact_and_live_context_has_advanced() -> None:
    overrides = getattr(audit_module, "HISTORICAL_SOURCE_SNAPSHOT_OVERRIDES", None)
    resolver = getattr(audit_module, "_resolve_audit_source_path", None)

    assert overrides == {
        "src/voice2task/training.py": HISTORICAL_TRAINING_SNAPSHOT,
        "CONTEXT.md": HISTORICAL_CONTEXT_SNAPSHOT,
        "data/public-samples/manifest_public_sample.json": HISTORICAL_MANIFEST_SNAPSHOT,
        "reports/public-sample/split-integrity-audit/summary.json": (
            HISTORICAL_SPLIT_SUMMARY_SNAPSHOT
        ),
    }
    assert callable(resolver)
    snapshot = resolver(REPO_ROOT, "CONTEXT.md")
    assert snapshot == REPO_ROOT / HISTORICAL_CONTEXT_SNAPSHOT
    snapshot_bytes = snapshot.read_bytes()
    assert len(snapshot_bytes) == 16_755
    assert hashlib.sha256(snapshot_bytes).hexdigest() == HISTORICAL_CONTEXT_SHA256
    assert hashlib.sha256((REPO_ROOT / "CONTEXT.md").read_bytes()).hexdigest() != (
        HISTORICAL_CONTEXT_SHA256
    )


def test_historical_training_snapshot_is_exact_and_live_training_has_advanced() -> None:
    snapshot = audit_module._resolve_audit_source_path(REPO_ROOT, "src/voice2task/training.py")

    assert snapshot == REPO_ROOT / HISTORICAL_TRAINING_SNAPSHOT
    snapshot_bytes = snapshot.read_bytes()
    assert len(snapshot_bytes) == 112_979
    assert hashlib.sha256(snapshot_bytes).hexdigest() == HISTORICAL_TRAINING_SHA256
    assert hashlib.sha256(
        (REPO_ROOT / "src/voice2task/training.py").read_bytes()
    ).hexdigest() != HISTORICAL_TRAINING_SHA256


def test_historical_manifest_snapshot_is_exact_and_live_manifest_has_advanced() -> None:
    snapshot = audit_module._resolve_audit_source_path(
        REPO_ROOT, "data/public-samples/manifest_public_sample.json"
    )

    assert snapshot == REPO_ROOT / HISTORICAL_MANIFEST_SNAPSHOT
    assert hashlib.sha256(snapshot.read_bytes()).hexdigest() == HISTORICAL_MANIFEST_SHA256
    assert hashlib.sha256(
        (REPO_ROOT / "data/public-samples/manifest_public_sample.json").read_bytes()
    ).hexdigest() != HISTORICAL_MANIFEST_SHA256


def test_historical_split_summary_snapshot_is_exact_and_current_report_has_advanced() -> None:
    snapshot = audit_module._resolve_audit_source_path(
        REPO_ROOT, "reports/public-sample/split-integrity-audit/summary.json"
    )

    assert snapshot == REPO_ROOT / HISTORICAL_SPLIT_SUMMARY_SNAPSHOT
    assert hashlib.sha256(snapshot.read_bytes()).hexdigest() == HISTORICAL_SPLIT_SUMMARY_SHA256
    assert hashlib.sha256(
        (REPO_ROOT / "reports/public-sample/split-integrity-audit/summary.json").read_bytes()
    ).hexdigest() != HISTORICAL_SPLIT_SUMMARY_SHA256


def test_historical_builder_emits_logical_context_path_and_phase_time_hash() -> None:
    audit = _audit()
    context_records = [
        record for record in audit["source_manifest"] if record["path"] == "CONTEXT.md"
    ]

    assert context_records == [
        {"path": "CONTEXT.md", "sha256": HISTORICAL_CONTEXT_SHA256}
    ]
    candidate = audit["transformation_graphs"]["candidate_only"]
    assert {node["source_path"] for node in candidate["nodes"]} == {"CONTEXT.md"}
    assert {edge["source_path"] for edge in candidate["edges"]} == {"CONTEXT.md"}


def test_historical_context_snapshot_missing_fails_closed(monkeypatch: Any) -> None:
    overrides = getattr(audit_module, "HISTORICAL_SOURCE_SNAPSHOT_OVERRIDES", None)
    assert isinstance(overrides, dict)
    monkeypatch.setitem(
        overrides,
        "CONTEXT.md",
        "reports/public-sample/contract-compiler-v2-causal-boundary/"
        "source-snapshots/CONTEXT.missing.md",
    )

    with pytest.raises(ValueError, match="missing"):
        build_contract_compiler_causal_audit(REPO_ROOT)


def test_historical_context_snapshot_drift_fails_closed(monkeypatch: Any) -> None:
    source_bytes = getattr(audit_module, "_audit_source_bytes", None)
    assert callable(source_bytes)

    def drifted_source_bytes(repo_root: Path, logical_path: str) -> bytes:
        content = source_bytes(repo_root, logical_path)
        return content + b"x" if logical_path == "CONTEXT.md" else content

    monkeypatch.setattr(audit_module, "_audit_source_bytes", drifted_source_bytes)
    with pytest.raises(ValueError, match="hash drift"):
        build_contract_compiler_causal_audit(REPO_ROOT)


def test_historical_render_replays_archived_report_bytes(tmp_path: Path) -> None:
    output_dir = tmp_path / "historical-replay"
    render_contract_compiler_causal_audit(REPO_ROOT, output_dir)
    committed_dir = REPO_ROOT / "reports/public-sample/contract-compiler-v2-causal-boundary"

    for name in ("summary.json", "summary.md"):
        assert (output_dir / name).read_bytes() == (committed_dir / name).read_bytes()


def _materialize_audit_sources(destination_root: Path) -> None:
    overrides = audit_module.HISTORICAL_SOURCE_SNAPSHOT_OVERRIDES
    for logical_path in AUDIT_INPUT_WHITELIST:
        physical_path = overrides.get(logical_path, logical_path)
        destination = destination_root / physical_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(
            audit_module._resolve_audit_source_path(REPO_ROOT, logical_path).read_bytes()
        )


def _replace_audit_source_with_external_symlink(
    repo_root: Path,
    logical_path: str,
    outside_root: Path,
    link_kind: str,
) -> None:
    physical_path = audit_module.HISTORICAL_SOURCE_SNAPSHOT_OVERRIDES.get(
        logical_path, logical_path
    )
    source = repo_root / physical_path
    if link_kind == "final":
        outside_target = outside_root / f"{source.name}.outside"
        source.rename(outside_target)
        source.symlink_to(outside_target)
        return
    outside_parent = outside_root / f"{source.parent.name}.outside"
    source.parent.rename(outside_parent)
    source.parent.symlink_to(outside_parent, target_is_directory=True)


def _assert_audit_source_operations_reject_before_read(
    repo_root: Path,
    logical_path: str,
    monkeypatch: Any,
    error_pattern: str,
) -> None:
    reads: list[Path] = []
    real_read_bytes = Path.read_bytes

    def read_spy(path: Path) -> bytes:
        reads.append(path)
        return real_read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", read_spy)
    operations = (
        (audit_module._resolve_audit_source_path, (repo_root, logical_path)),
        (audit_module._audit_source_bytes, (repo_root, logical_path)),
        (audit_module._sha256, (repo_root, logical_path)),
        (audit_module._source_text, (repo_root, logical_path)),
        (build_contract_compiler_causal_audit, (repo_root,)),
    )
    for operation, arguments in operations:
        reads.clear()
        with pytest.raises(ValueError, match=error_pattern):
            operation(*arguments)
        assert reads == []


def test_historical_resolver_rejects_non_whitelisted_logical_path_before_read(
    monkeypatch: Any,
) -> None:
    reads: list[Path] = []

    def forbidden_read(path: Path) -> bytes:
        reads.append(path)
        raise AssertionError("non-whitelisted audit source must not be read")

    monkeypatch.setattr(Path, "read_bytes", forbidden_read)
    for operation in (
        audit_module._resolve_audit_source_path,
        audit_module._audit_source_bytes,
        audit_module._sha256,
        audit_module._source_text,
    ):
        with pytest.raises(ValueError, match="whitelist"):
            operation(REPO_ROOT, "README.md")
    assert reads == []


@pytest.mark.parametrize("link_kind", ("final", "parent"))
def test_historical_resolver_rejects_external_symlink_for_regular_source_before_read(
    tmp_path: Path,
    monkeypatch: Any,
    link_kind: str,
) -> None:
    repo_root = tmp_path / "repo"
    outside_root = tmp_path / "outside"
    repo_root.mkdir()
    outside_root.mkdir()
    _materialize_audit_sources(repo_root)
    logical_path = "src/voice2task/formatting.py"
    _replace_audit_source_with_external_symlink(
        repo_root, logical_path, outside_root, link_kind
    )

    _assert_audit_source_operations_reject_before_read(
        repo_root,
        logical_path,
        monkeypatch,
        "symlink|logical location|outside",
    )


@pytest.mark.parametrize("link_kind", ("final", "parent"))
def test_historical_resolver_rejects_external_snapshot_symlink_before_read(
    tmp_path: Path,
    monkeypatch: Any,
    link_kind: str,
) -> None:
    repo_root = tmp_path / "repo"
    outside_root = tmp_path / "outside"
    repo_root.mkdir()
    outside_root.mkdir()
    _materialize_audit_sources(repo_root)
    _replace_audit_source_with_external_symlink(
        repo_root, "CONTEXT.md", outside_root, link_kind
    )

    _assert_audit_source_operations_reject_before_read(
        repo_root,
        "CONTEXT.md",
        monkeypatch,
        "symlink|logical location|outside",
    )


@pytest.mark.parametrize("source_state", ("missing", "non_regular"))
def test_historical_resolver_rejects_missing_or_non_regular_source_before_read(
    tmp_path: Path,
    monkeypatch: Any,
    source_state: str,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _materialize_audit_sources(repo_root)
    logical_path = "src/voice2task/formatting.py"
    source = repo_root / logical_path
    source.unlink()
    if source_state == "non_regular":
        source.mkdir()

    _assert_audit_source_operations_reject_before_read(
        repo_root,
        logical_path,
        monkeypatch,
        "missing|regular file",
    )
