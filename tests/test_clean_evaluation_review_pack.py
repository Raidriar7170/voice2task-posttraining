from __future__ import annotations

import copy
import hashlib
import inspect
import json
import os
import socket
import stat
from pathlib import Path
from typing import Any, cast

import pytest
import test_clean_evaluation_boundary as boundary_fixtures

import voice2task.clean_evaluation_boundary as boundary
import voice2task.clean_evaluation_review_pack as review_pack
from voice2task.cli import data as data_cli


def _candidate_envelope() -> dict[str, Any]:
    candidate = copy.deepcopy(review_pack.build_review_pack_template())
    candidate.update(
        {
            "document_kind": "CANDIDATE",
            "envelope_schema_id": review_pack.CANDIDATE_ENVELOPE_ID,
            "template_only": False,
        }
    )
    for section_name, proposed_key in (
        ("binding_draft", "proposed_bindings"),
        ("source_contract_draft", "proposed_fields"),
        ("compiler_card_draft", "proposed_fields"),
        ("model_card_draft", "proposed_fields"),
    ):
        section = cast(dict[str, Any], candidate[section_name])
        proposed = cast(dict[str, dict[str, Any]], section[proposed_key])
        for record in proposed.values():
            record.update(
                {
                    "proposed_value": "candidate-scalar",
                    "evidence": {"kind": "candidate-evidence"},
                    "review": ["candidate-review"],
                }
            )
    first = candidate["binding_draft"]["proposed_bindings"]["acquisition_source"]
    first["proposed_value"] = {"safe": ["scalar", 1, True, None]}
    first["evidence"] = ["evidence", {"source": "public-label"}]
    first["review"] = {"status": "PENDING"}
    return candidate


def _semantic_candidate_envelope() -> dict[str, Any]:
    frame = boundary_fixtures._frame_bytes(boundary_fixtures._records())  # noqa: SLF001
    components = {
        "binding_draft": boundary_fixtures._bindings(),  # noqa: SLF001
        "source_contract_draft": boundary_fixtures._source_contract(frame),  # noqa: SLF001
        "compiler_card_draft": boundary_fixtures._compiler_card(),  # noqa: SLF001
        "model_card_draft": boundary_fixtures._model_card(),  # noqa: SLF001
    }
    candidate = _candidate_envelope()
    binding_packet = components["binding_draft"]
    binding_records = candidate["binding_draft"]["proposed_bindings"]
    for name in boundary.EXECUTION_BINDING_FIELDS:
        dossier = binding_packet["bindings"][name]
        binding_records[name] = {
            "proposed_value": copy.deepcopy(dossier["value"]),
            "evidence": {
                key: copy.deepcopy(value)
                for key, value in dossier.items()
                if key not in {"name", "status", "value", "review_verdict"}
            },
            "review": {
                "binding_status": dossier["status"],
                "review_verdict": dossier["review_verdict"],
            },
        }
    for section_name, proposed_key in (
        ("source_contract_draft", "proposed_fields"),
        ("compiler_card_draft", "proposed_fields"),
        ("model_card_draft", "proposed_fields"),
    ):
        records = candidate[section_name][proposed_key]
        for name, value in components[section_name].items():
            records[name] = {
                "proposed_value": copy.deepcopy(value),
                "evidence": "external-evidence-declared",
                "review": "independent-review-declared",
            }
    return candidate


def _raw_layout(fields: frozenset[str]) -> dict[str, Any]:
    return {name: f"raw-{index}" for index, name in enumerate(sorted(fields), start=1)}


RAW_LAYOUT_CASES = (
    pytest.param(
        {"schema_version": "raw", "bindings": {}},
        id="binding-packet",
    ),
    pytest.param(_raw_layout(boundary.binding_dossier_fields()), id="binding-dossier"),
    pytest.param(_raw_layout(boundary.source_contract_fields()), id="source-contract"),
    pytest.param(_raw_layout(boundary.compiler_card_fields()), id="compiler-card"),
    pytest.param(_raw_layout(boundary.model_card_fields()), id="model-card"),
)

NESTING_CASES = (
    pytest.param(lambda value: value, id="direct"),
    pytest.param(lambda value: {"nested": value}, id="nested-object"),
    pytest.param(lambda value: ["safe", {"nested": [value]}], id="nested-array"),
)


def _walk(value: Any) -> list[Any]:
    observed = [value]
    if isinstance(value, dict):
        for nested in value.values():
            observed.extend(_walk(nested))
    elif isinstance(value, list):
        for nested in value:
            observed.extend(_walk(nested))
    return observed


def test_catalog_is_exactly_derived_ordered_and_value_free(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    catalog = review_pack.build_binding_catalog()
    entries = catalog["entries"]

    assert catalog["binding_inventory_count"] == 29
    assert tuple(entry["name"] for entry in entries) == boundary.EXECUTION_BINDING_FIELDS
    assert [entry["ordinal"] for entry in entries] == list(range(1, 30))
    assert all("alias" not in key.lower() and "value" not in key.lower() for entry in entries for key in entry)
    assert review_pack.render_json(catalog) == review_pack.render_json(
        review_pack.build_binding_catalog()
    )

    monkeypatch.setattr(boundary, "EXECUTION_BINDING_FIELDS", ("runtime-derived-field",))
    derived = review_pack.build_binding_catalog()
    assert derived["binding_inventory_count"] == 1
    assert [entry["name"] for entry in derived["entries"]] == ["runtime-derived-field"]


def test_boundary_exposes_immutable_authoritative_field_inventories() -> None:
    assert boundary.binding_packet_fields() == frozenset({"schema_version", "bindings"})
    assert boundary.binding_dossier_fields() == boundary._BINDING_FIELDS  # noqa: SLF001
    assert boundary.source_contract_fields() == boundary._SOURCE_CONTRACT_FIELDS  # noqa: SLF001
    assert boundary.compiler_card_fields() == boundary._COMPILER_CARD_FIELDS  # noqa: SLF001
    assert boundary.model_card_fields() == boundary._MODEL_CARD_FIELDS  # noqa: SLF001
    assert all(
        isinstance(fields, frozenset)
        for fields in (
            boundary.binding_packet_fields(),
            boundary.binding_dossier_fields(),
            boundary.source_contract_fields(),
            boundary.compiler_card_fields(),
            boundary.model_card_fields(),
        )
    )
    assert boundary.contains_blocked_sentinel(None) is True
    assert boundary.contains_blocked_sentinel({}) is False
    assert boundary.contains_blocked_sentinel("TBD") is True
    assert boundary.contains_private_path_value("C:\\private\\canary") is True
    assert boundary.contains_private_path_value("data/local-private/canary") is True


def test_schema_and_template_are_strict_distinct_and_non_executable() -> None:
    schema = review_pack.build_review_pack_schema()
    template = review_pack.build_review_pack_template()
    schema_ids = {
        item["$id"]
        for item in _walk(schema)
        if isinstance(item, dict) and isinstance(item.get("$id"), str)
    }

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    prefix = "https://voice2task.local/schemas/"
    assert schema_ids == {
        f"{prefix}clean-evaluation-review-pack-v1",
        f"{prefix}clean-evaluation-review-envelope-template-v1",
        f"{prefix}clean-evaluation-review-envelope-v1",
        f"{prefix}review-draft-field-template-v1",
        f"{prefix}review-draft-field-candidate-v1",
        f"{prefix}safe-candidate-json-v1",
        *(
            f"{prefix}clean-evaluation-{draft_name}-draft-v1{suffix}"
            for draft_name in ("binding", "source-contract", "compiler-card", "model-card")
            for suffix in ("", "-candidate")
        ),
    }
    for item in _walk(schema):
        if isinstance(item, dict) and item.get("type") == "object":
            assert item.get("additionalProperties") is False

    assert template["schema_version"] == "clean-evaluation-review-envelope-v1"
    assert template["template_only"] is True
    assert template["execution_input_marker"] == "NOT_AN_EXECUTION_INPUT"
    assert template["human_acceptance_marker"] == "NO_HUMAN_ACCEPTANCE_RECORDED"
    for section_name, target_schema, proposed_key in (
        ("binding_draft", "clean-evaluation-bindings-v1", "proposed_bindings"),
        ("source_contract_draft", "clean-source-contract-v1", "proposed_fields"),
        ("compiler_card_draft", "compiler-power-card-v1", "proposed_fields"),
        ("model_card_draft", "model-power-card-v1", "proposed_fields"),
    ):
        draft = cast(dict[str, Any], template[section_name])
        assert draft["schema_version"].endswith("-draft-v1")
        assert draft["draft_only"] is True
        assert draft["target_schema"] == target_schema
        proposed = cast(dict[str, dict[str, Any]], draft[proposed_key])
        assert proposed
        assert all(
            record
            == {
                "proposed_value": "NOT_SUPPLIED",
                "evidence": "NOT_SUPPLIED",
                "review": "NOT_SUPPLIED",
            }
            for record in proposed.values()
        )

    draft_field_keys = {"proposed_value", "evidence", "review"}
    raw_layouts = (
        boundary._BINDING_FIELDS,  # noqa: SLF001
        boundary._SOURCE_CONTRACT_FIELDS,  # noqa: SLF001
        boundary._COMPILER_CARD_FIELDS,  # noqa: SLF001
        boundary._MODEL_CARD_FIELDS,  # noqa: SLF001
    )
    for item in _walk(template):
        if isinstance(item, dict) and set(item) in raw_layouts:
            assert all(
                isinstance(value, dict) and set(value) == draft_field_keys
                for value in item.values()
            )

    serialized = review_pack.render_json(template).decode("utf-8")
    assert "NOT_AN_EXECUTION_INPUT" in serialized
    assert "NO_HUMAN_ACCEPTANCE_RECORDED" in serialized
    assert "NOT_SUPPLIED" in serialized
    assert not any(
        isinstance(item, str) and boundary._valid_hash(item)  # noqa: SLF001
        for item in _walk(template)
    )
    assert not hasattr(review_pack, "export_execution_components")
    assert not hasattr(review_pack, "write_review_pack")


def test_template_optionally_conforms_to_published_schema() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema = review_pack.build_review_pack_schema()
    jsonschema.Draft202012Validator.check_schema(schema)
    validator = jsonschema.Draft202012Validator(schema)
    validator.validate(review_pack.build_review_pack_template())
    validator.validate(_candidate_envelope())
    validator.validate(_semantic_candidate_envelope())


@pytest.mark.parametrize("raw_layout", RAW_LAYOUT_CASES)
@pytest.mark.parametrize("field_name", ("proposed_value", "evidence", "review"))
@pytest.mark.parametrize("nest", NESTING_CASES)
def test_candidate_schema_recursively_rejects_raw_execution_layouts(
    raw_layout: dict[str, Any],
    field_name: str,
    nest: Any,
) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    candidate = _candidate_envelope()
    record = candidate["binding_draft"]["proposed_bindings"]["acquisition_source"]
    record[field_name] = nest(copy.deepcopy(raw_layout))

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(
            review_pack.build_review_pack_schema()
        ).validate(candidate)


def test_candidate_schema_recursively_rejects_not_supplied() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    candidate = _candidate_envelope()
    record = candidate["binding_draft"]["proposed_bindings"]["acquisition_source"]
    record["evidence"] = {"nested": ["NOT_SUPPLIED"]}

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(
            review_pack.build_review_pack_schema()
        ).validate(candidate)


def test_responsibility_matrix_has_exact_unapproved_component_and_binding_rows() -> None:
    matrix = review_pack.build_responsibility_matrix()
    rows = matrix["rows"]
    expected_ids = {
        "component:binding_packet",
        "component:source_contract",
        "component:compiler_card",
        "component:model_card",
        *(f"binding:{name}" for name in boundary.EXECUTION_BINDING_FIELDS),
    }

    assert matrix["row_count"] == len(rows) == 33
    assert {row["row_id"] for row in rows} == expected_ids
    assert len({row["row_id"] for row in rows}) == 33
    for row in rows:
        assert set(row) == {
            "row_id",
            "scope",
            "name",
            "envelope_section",
            "provider",
            "independent_reviewer",
            "required_evidence",
            "applicability",
            "zero_access_attestation",
            "human_acceptance_gate",
            "preapproval_status",
        }
        assert all(
            row[field] == "NOT_SUPPLIED"
            for field in (
                "provider",
                "independent_reviewer",
                "required_evidence",
                "applicability",
                "zero_access_attestation",
            )
        )
        assert row["human_acceptance_gate"] == "NOT_RECORDED"
        assert row["preapproval_status"] == "NOT_RECORDED"
    assert {
        row["name"]: row["envelope_section"]
        for row in rows
        if row["scope"] == "component"
    } == {
        "binding_packet": "binding_draft",
        "source_contract": "source_contract_draft",
        "compiler_card": "compiler_card_draft",
        "model_card": "model_card_draft",
    }
    assert all(
        row["envelope_section"] == "binding_draft"
        for row in rows
        if row["scope"] == "binding"
    )

    catalog = review_pack.build_binding_catalog()
    assert all(entry["human_acceptance_gate"] == "NOT_RECORDED" for entry in catalog["entries"])
    for item in _walk(catalog):
        if isinstance(item, dict):
            assert all("alias" not in key.lower() and "value" not in key.lower() for key in item)

    checklist = review_pack.build_review_checklist()
    assert all(row_id in checklist for row_id in expected_ids)
    assert "APPROVED" not in checklist


def test_review_input_root_is_derived_from_boundary_root() -> None:
    assert review_pack.REVIEW_INPUT_ROOT == (
        boundary.CANONICAL_PRIVATE_ROOT / "review-inputs"
    ).as_posix() + "/"


EXPECTED_EMPTY_LINT_TRUTH = {
    "evidence_status": "DESIGN_ONLY",
    "phase_status": "PREPARATION_ONLY",
    "decision": "ACQUISITION_AND_BINDING_REVIEW_PACK_READY_EXECUTION_BLOCKED",
    "review_pack_status": "READY_FOR_EXTERNAL_COMPLETION",
    "candidate_pack_status": "INCOMPLETE",
    "binding_inventory_count": 29,
    "supplied_binding_count": 0,
    "authoritatively_bound_binding_count": 0,
    "acquisition_source_status": "UNAVAILABLE",
    "current_readiness_state": "DESIGN_ONLY",
    "execution_bindings_status": "INCOMPLETE",
    "protocol_freeze_status": "NOT_FROZEN",
    "clean_population_status": "NOT_MATERIALIZED",
    "boundary_integrity_status": "NOT_CREATED",
    "human_acceptance_status": "NOT_RECORDED",
    "freeze_authorized": False,
    "next_phase_eligible": False,
    "execution_readiness": False,
    "lint_conforms": False,
}


def test_lint_empty_template_has_exact_preparation_truth_and_no_generic_ok() -> None:
    result = review_pack.lint_review_envelope(review_pack.build_review_pack_template())

    assert {key: result[key] for key in EXPECTED_EMPTY_LINT_TRUTH} == EXPECTED_EMPTY_LINT_TRUTH
    assert set(result) == {*EXPECTED_EMPTY_LINT_TRUTH, "diagnostics"}
    assert result["diagnostics"] == [
        {"code": "REVIEW_ENVELOPE_INCOMPLETE", "section": "binding_draft"}
    ]
    assert "ok" not in result
    assert "protocol_sha256" not in result
    assert "protocol" not in result


def test_lint_complete_candidate_is_pure_uses_shared_seam_and_caps_truth(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = _semantic_candidate_envelope()
    snapshot = copy.deepcopy(candidate)
    calls = 0
    forbidden_calls = {
        "verified_read_private_file": 0,
        "freeze_protocol": 0,
        "validate_named_inputs": 0,
        "persist_protocol_manifest": 0,
        "materialize_boundary": 0,
    }
    real_validate = boundary.validate_pre_freeze_inputs

    def count_validate(*args: Any, **kwargs: Any) -> dict[str, int]:
        nonlocal calls
        calls += 1
        return real_validate(*args, **kwargs)

    def forbidden(name: str) -> Any:
        def record(*args: Any, **kwargs: Any) -> Any:
            forbidden_calls[name] += 1
            raise AssertionError("review lint crossed an execution or I/O boundary")

        return record

    monkeypatch.setattr(boundary, "validate_pre_freeze_inputs", count_validate)
    for name in forbidden_calls:
        monkeypatch.setattr(boundary, name, forbidden(name))
    result = review_pack.lint_review_envelope(candidate)

    assert calls == 1
    assert forbidden_calls == {name: 0 for name in forbidden_calls}
    assert candidate == snapshot
    assert result["evidence_status"] == "DESIGN_ONLY"
    assert result["phase_status"] == "PREPARATION_ONLY"
    assert result["decision"] == "CANDIDATE_PACK_STRUCTURALLY_COMPLETE_REVIEW_REQUIRED"
    assert result["review_pack_status"] == "READY_FOR_EXTERNAL_COMPLETION"
    assert result["candidate_pack_status"] == "STRUCTURALLY_COMPLETE_REVIEW_REQUIRED"
    assert result["binding_inventory_count"] == result["supplied_binding_count"] == 29
    assert result["authoritatively_bound_binding_count"] == 0
    assert result["acquisition_source_status"] == "CANDIDATE_DECLARED_REVIEW_REQUIRED"
    assert result["human_acceptance_status"] == "NOT_RECORDED"
    assert result["freeze_authorized"] is False
    assert result["next_phase_eligible"] is False
    assert result["execution_readiness"] is False
    assert result["lint_conforms"] is True
    assert set(result) == {*EXPECTED_EMPTY_LINT_TRUTH, "diagnostics"}
    assert result["diagnostics"] == []
    assert "ok" not in result
    assert "protocol_sha256" not in result
    assert "protocol" not in result
    assert "components" not in result
    assert "bindings" not in result
    assert list(inspect.signature(review_pack.lint_review_envelope).parameters) == ["envelope"]
    assert not hasattr(review_pack, "convert_review_envelope")
    assert not hasattr(review_pack, "export_execution_components")
    serialized = review_pack.render_json(result).decode("utf-8")
    assert "reviewed-acquisition_source" not in serialized
    assert "APPROVED" not in serialized


@pytest.mark.parametrize(
    ("mutate", "expected_code", "canary"),
    (
        pytest.param(lambda value: [value], "REVIEW_ENVELOPE_MALFORMED", None, id="malformed"),
        pytest.param(
            lambda value: (value.pop("model_card_draft"), value)[1],
            "REVIEW_ENVELOPE_MALFORMED",
            None,
            id="missing-section",
        ),
        pytest.param(
            lambda value: (value.update({"model_card_alias": value["model_card_draft"]}), value)[1],
            "REVIEW_ENVELOPE_MALFORMED",
            "model_card_alias",
            id="unknown-alias",
        ),
        pytest.param(
            lambda value: (
                value["binding_draft"]["proposed_bindings"]["alpha"].update(
                    {"proposed_value": "NOT_SUPPLIED"}
                ),
                value,
            )[1],
            "REVIEW_ENVELOPE_INCOMPLETE",
            None,
            id="not-supplied",
        ),
        pytest.param(
            lambda value: (
                value["binding_draft"]["proposed_bindings"]["acquisition_source"].update(
                    {"proposed_value": "/private/canary"}
                ),
                value,
            )[1],
            "REVIEW_ENVELOPE_MALFORMED",
            "/private/canary",
            id="private-path",
        ),
        pytest.param(
            lambda value: (
                value["binding_draft"]["proposed_bindings"]["alpha"]["evidence"].update(
                    {"authority_sha256": "invalid-hash-canary"}
                ),
                value,
            )[1],
            "BINDING_INCOMPLETE_OR_PLACEHOLDER",
            "invalid-hash-canary",
            id="invalid-hash",
        ),
        pytest.param(
            lambda value: (
                value["source_contract_draft"]["proposed_fields"]["reviewer_label"].update(
                    {"proposed_value": "independent-source-authority"}
                ),
                value,
            )[1],
            "ACQUISITION_SOURCE_UNAVAILABLE_OR_UNVERIFIABLE",
            "independent-source-authority",
            id="provider-reviewer-independence",
        ),
        pytest.param(
            lambda value: (
                value["compiler_card_draft"]["proposed_fields"]["planning_mode"].update(
                    {"proposed_value": "unsupported-power-canary"}
                ),
                value,
            )[1],
            "POWER_ASSUMPTION_UNSUPPORTED",
            "unsupported-power-canary",
            id="power",
        ),
        pytest.param(
            lambda value: (
                value["source_contract_draft"]["proposed_fields"]["allowed_strata"].update(
                    {"proposed_value": ["s2", "s1"]}
                ),
                value,
            )[1],
            "BINDING_INCOMPLETE_OR_PLACEHOLDER",
            None,
            id="cross-component",
        ),
    ),
)
def test_lint_invalid_candidates_fail_closed_with_sanitized_diagnostics(
    mutate: Any,
    expected_code: str,
    canary: str | None,
) -> None:
    candidate = mutate(_semantic_candidate_envelope())
    result = review_pack.lint_review_envelope(candidate)
    rendered = json.dumps(result, sort_keys=True)

    assert result["lint_conforms"] is False
    assert expected_code in {item["code"] for item in result["diagnostics"]}
    assert result["authoritatively_bound_binding_count"] == 0
    assert result["human_acceptance_status"] == "NOT_RECORDED"
    assert result["freeze_authorized"] is False
    assert result["next_phase_eligible"] is False
    assert result["execution_readiness"] is False
    assert "ok" not in result
    assert "protocol_sha256" not in result
    if canary is not None:
        assert canary not in rendered


def test_self_reported_approval_never_advances_authority_or_readiness() -> None:
    candidate = _semantic_candidate_envelope()
    candidate["binding_draft"]["proposed_bindings"]["alpha"]["review"].update(
        {"review_verdict": "APPROVED"}
    )
    result = review_pack.lint_review_envelope(candidate)

    assert result["lint_conforms"] is True
    assert result["authoritatively_bound_binding_count"] == 0
    assert result["human_acceptance_status"] == "NOT_RECORDED"
    assert result["freeze_authorized"] is False
    assert result["next_phase_eligible"] is False
    assert result["execution_readiness"] is False


def _candidate_objects() -> list[dict[str, Any]]:
    candidate = _semantic_candidate_envelope()
    objects = [item for item in _walk(candidate) if isinstance(item, dict)]
    unique: list[dict[str, Any]] = []
    seen: set[int] = set()
    for item in objects:
        if id(item) not in seen:
            unique.append(item)
            seen.add(id(item))
    return unique


def test_every_unchanged_candidate_object_fails_execution_validators_and_named_freeze(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    objects = _candidate_objects()
    persisted = 0

    def forbidden_persist(*args: Any, **kwargs: Any) -> Any:
        nonlocal persisted
        persisted += 1
        raise AssertionError("protocol persistence reached")

    monkeypatch.setattr(boundary, "persist_protocol_manifest", forbidden_persist)
    for surface in objects:
        with pytest.raises(boundary.BoundaryViolation):
            boundary.validate_binding_packet(surface)
        with pytest.raises(boundary.BoundaryViolation):
            boundary._validate_source_contract(surface)  # noqa: SLF001
        with pytest.raises(boundary.BoundaryViolation):
            boundary.validate_power_card(surface, "compiler")
        with pytest.raises(boundary.BoundaryViolation):
            boundary.validate_power_card(surface, "model")
        with pytest.raises(boundary.BoundaryViolation):
            boundary.freeze_protocol(surface, surface, surface, surface)

        monkeypatch.setattr(boundary, "_read_json_input", lambda *args, _surface=surface: _surface)
        with pytest.raises(boundary.BoundaryViolation):
            boundary.validate_named_inputs(
                tmp_path,
                bindings="candidate",
                source_contract="candidate",
                compiler_card="candidate",
                model_card="candidate",
            )
    assert persisted == 0
    assert not (tmp_path / "protocols").exists()


def test_candidate_envelope_drafts_maps_and_nested_objects_fail_existing_cli(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    for surface in _candidate_objects():
        monkeypatch.setattr(
            data_cli,
            "validate_named_inputs",
            lambda *args, _surface=surface, **kwargs: boundary.freeze_protocol(
                _surface, _surface, _surface, _surface
            ),
        )
        rc = data_cli.main(
            [
                "clean-boundary-validate",
                "--bindings",
                "candidate",
                "--source-contract",
                "candidate",
                "--compiler-card",
                "candidate",
                "--model-card",
                "candidate",
            ]
        )
        assert rc != 0
        output = capsys.readouterr().out
        assert "protocol_sha256" not in output


def _set_discarded_or_nonsemantic_surface(
    candidate: dict[str, Any],
    location: str,
    value: Any,
) -> None:
    if location == "source-evidence":
        candidate["source_contract_draft"]["proposed_fields"]["authority_label"][
            "evidence"
        ] = value
    elif location == "source-review":
        candidate["source_contract_draft"]["proposed_fields"]["authority_label"][
            "review"
        ] = value
    elif location == "compiler-evidence":
        candidate["compiler_card_draft"]["proposed_fields"]["estimand"]["evidence"] = value
    elif location == "model-review":
        candidate["model_card_draft"]["proposed_fields"]["estimand"]["review"] = value
    else:
        candidate["binding_draft"]["proposed_bindings"]["alpha"]["evidence"][
            "applicability"
        ] = value


@pytest.mark.parametrize(
    "location",
    (
        "source-evidence",
        "source-review",
        "compiler-evidence",
        "model-review",
        "binding-applicability",
    ),
)
@pytest.mark.parametrize(
    ("bad_value", "expected_code"),
    (
        (None, "REVIEW_ENVELOPE_INCOMPLETE"),
        ("", "REVIEW_ENVELOPE_INCOMPLETE"),
        ("   ", "REVIEW_ENVELOPE_INCOMPLETE"),
        ([], "REVIEW_ENVELOPE_INCOMPLETE"),
        ({}, "REVIEW_ENVELOPE_INCOMPLETE"),
        ("TBD", "REVIEW_ENVELOPE_INCOMPLETE"),
        ("NOT_AVAILABLE", "REVIEW_ENVELOPE_INCOMPLETE"),
        ("/private/canary", "REVIEW_ENVELOPE_MALFORMED"),
        ("../private-canary", "REVIEW_ENVELOPE_MALFORMED"),
        (r"C:\private\canary", "REVIEW_ENVELOPE_MALFORMED"),
        ("data/local-private/canary", "REVIEW_ENVELOPE_MALFORMED"),
    ),
)
def test_all_recursive_candidate_surfaces_reject_placeholders_and_private_paths(
    location: str,
    bad_value: Any,
    expected_code: str,
) -> None:
    candidate = _semantic_candidate_envelope()
    _set_discarded_or_nonsemantic_surface(candidate, location, bad_value)

    result = review_pack.lint_review_envelope(candidate)
    rendered = json.dumps(result, sort_keys=True)

    assert result["lint_conforms"] is False
    assert {item["code"] for item in result["diagnostics"]} == {expected_code}
    assert all(item["section"] in review_pack.REVIEW_ENVELOPE_SECTIONS for item in result["diagnostics"])
    if isinstance(bad_value, str) and bad_value.strip() and bad_value not in {"TBD", "NOT_AVAILABLE"}:
        assert bad_value not in rendered


@pytest.mark.parametrize("shape", ("cycle", "depth", "budget"))
def test_lint_is_total_for_cycles_depth_and_node_budget(shape: str) -> None:
    candidate = _semantic_candidate_envelope()
    if shape == "cycle":
        hostile: list[Any] = []
        hostile.append(hostile)
    elif shape == "depth":
        hostile = []
        cursor = hostile
        for _ in range(1200):
            nested: list[Any] = []
            cursor.append(nested)
            cursor = nested
        cursor.append("leaf")
    else:
        hostile = [0] * (review_pack.REVIEW_NODE_BUDGET + 1)
    candidate["source_contract_draft"]["proposed_fields"]["authority_label"][
        "evidence"
    ] = hostile

    result = review_pack.lint_review_envelope(candidate)

    assert result["lint_conforms"] is False
    assert {item["code"] for item in result["diagnostics"]} == {
        "REVIEW_ENVELOPE_MALFORMED"
    }


@pytest.mark.parametrize(
    "error",
    (
        TypeError("type-canary /private/type"),
        ValueError("value-canary deadbeef"),
        RuntimeError("runtime-canary data/local-private/runtime"),
        OSError("oserror-path-canary /private/oserror"),
        KeyError("f" * 64),
        AttributeError("attribute-canary data/local-private/attribute"),
    ),
)
def test_unexpected_semantic_errors_are_sanitized_to_fixed_generic_code(
    error: Exception,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(*args: Any, **kwargs: Any) -> Any:
        raise error

    monkeypatch.setattr(boundary, "validate_pre_freeze_inputs", fail)
    result = review_pack.lint_review_envelope(_semantic_candidate_envelope())
    rendered = json.dumps(result, sort_keys=True)

    assert result["lint_conforms"] is False
    assert result["diagnostics"] == [
        {
            "code": review_pack.REVIEW_LINT_UNEXPECTED_FAILURE,
            "section": "candidate_envelope",
        }
    ]
    assert str(error) not in rendered
    assert "canary" not in rendered


@pytest.mark.parametrize(
    "error",
    (
        BaseException("base-exception-canary"),
        SystemExit("system-exit-canary"),
        KeyboardInterrupt("keyboard-interrupt-canary"),
    ),
)
def test_lint_does_not_swallow_base_exceptions(
    error: BaseException,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(*args: Any, **kwargs: Any) -> Any:
        raise error

    monkeypatch.setattr(boundary, "validate_pre_freeze_inputs", fail)
    with pytest.raises(type(error), match="canary"):
        review_pack.lint_review_envelope(_semantic_candidate_envelope())


def test_unknown_boundary_code_and_unhashable_semantics_are_generic_and_sanitized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unknown(*args: Any, **kwargs: Any) -> Any:
        raise boundary.BoundaryViolation("UNKNOWN_CODE_PATH_CANARY")

    monkeypatch.setattr(boundary, "validate_pre_freeze_inputs", unknown)
    unknown_result = review_pack.lint_review_envelope(_semantic_candidate_envelope())
    assert unknown_result["diagnostics"][0]["code"] == review_pack.REVIEW_LINT_UNEXPECTED_FAILURE
    assert "UNKNOWN_CODE_PATH_CANARY" not in json.dumps(unknown_result)

    monkeypatch.undo()
    unhashable = _semantic_candidate_envelope()
    unhashable["source_contract_draft"]["proposed_fields"]["allowed_strata"][
        "proposed_value"
    ] = [{"unhashable-canary": "hidden"}]
    unhashable_result = review_pack.lint_review_envelope(unhashable)
    assert unhashable_result["diagnostics"][0]["code"] == review_pack.REVIEW_LINT_UNEXPECTED_FAILURE
    assert "unhashable-canary" not in json.dumps(unhashable_result)


def test_diagnostic_allowlist_is_exact_and_all_results_conform() -> None:
    assert review_pack.REVIEW_DIAGNOSTIC_CODES == frozenset(
        {
            "REVIEW_ENVELOPE_MALFORMED",
            "REVIEW_ENVELOPE_INCOMPLETE",
            "BINDING_INCOMPLETE_OR_PLACEHOLDER",
            "ACQUISITION_SOURCE_UNAVAILABLE_OR_UNVERIFIABLE",
            "POWER_ASSUMPTION_UNSUPPORTED",
            review_pack.REVIEW_LINT_UNEXPECTED_FAILURE,
        }
    )
    candidates = [review_pack.build_review_pack_template(), _semantic_candidate_envelope(), []]
    assert all(
        item["code"] in review_pack.REVIEW_DIAGNOSTIC_CODES
        for candidate in candidates
        for item in review_pack.lint_review_envelope(candidate)["diagnostics"]
    )


def test_float_schema_and_runtime_reject_while_null_is_incomplete() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    validator = jsonschema.Draft202012Validator(review_pack.build_review_pack_schema())
    float_candidate = _semantic_candidate_envelope()
    float_candidate["source_contract_draft"]["proposed_fields"]["max_frame_bytes"][
        "evidence"
    ] = 1.5
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(float_candidate)
    assert review_pack.lint_review_envelope(float_candidate)["diagnostics"][0]["code"] == (
        "REVIEW_ENVELOPE_MALFORMED"
    )

    null_candidate = _semantic_candidate_envelope()
    null_candidate["model_card_draft"]["proposed_fields"]["estimand"]["review"] = None
    validator.validate(null_candidate)
    assert review_pack.lint_review_envelope(null_candidate)["diagnostics"][0]["code"] == (
        "REVIEW_ENVELOPE_INCOMPLETE"
    )


def test_real_existing_clean_boundary_cli_rejects_candidate_file_before_persist(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(data_cli, "REPO_ROOT", tmp_path)
    private_root = tmp_path / boundary.CANONICAL_PRIVATE_ROOT
    inputs = private_root / "inputs"
    inputs.mkdir(parents=True)
    payload = boundary.canonical_json_bytes(_semantic_candidate_envelope()) + b"\n"
    for name in ("bindings", "source", "compiler", "model"):
        (inputs / f"{name}.json").write_bytes(payload)

    def forbidden_persist(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("candidate reached protocol persistence")

    monkeypatch.setattr(boundary, "persist_protocol_manifest", forbidden_persist)
    rc = data_cli.main(
        [
            "clean-boundary-validate",
            "--bindings",
            "inputs/bindings.json",
            "--source-contract",
            "inputs/source.json",
            "--compiler-card",
            "inputs/compiler.json",
            "--model-card",
            "inputs/model.json",
        ]
    )
    output = capsys.readouterr().out

    assert rc != 0
    assert "protocol_sha256" not in output
    assert not (private_root / "protocols").exists()


def test_checklist_and_all_b1_artifacts_are_deterministic_and_complete() -> None:
    checklist = review_pack.build_review_checklist()
    required_phrases = (
        "source provider must differ from source reviewer",
        "lockbox validator must differ from lockbox reviewer",
        "public train/dev/test",
        "remediation",
        "challenge",
        "prediction",
        "lockbox-v1 row content",
        "derivation evidence",
        "applicability",
        "zero-access attestation",
        "statistical review",
        "human acceptance",
        "operator alone may manually copy",
        "data/local-private/clean-compiler-model-evaluation-boundary-v1/review-inputs/",
        "tool never creates or modifies this root",
    )
    lowered = checklist.lower()
    assert all(phrase in lowered for phrase in required_phrases)

    first = review_pack.build_review_pack_artifacts()
    second = review_pack.build_review_pack_artifacts()
    assert first == second
    assert tuple(first) == (
        "binding-catalog.json",
        "review-pack.schema.json",
        "review-pack.template.json",
        "review-checklist.md",
    )
    assert all(isinstance(payload, bytes) and payload.endswith(b"\n") for payload in first.values())
    assert "jsonschema" not in inspect.getsource(review_pack)


def test_review_pack_bundle_has_seven_deterministic_non_self_referential_members() -> None:
    base = review_pack.build_review_pack_artifacts()
    first = review_pack.build_review_pack_bundle()
    second = review_pack.build_review_pack_bundle()

    assert first == second
    assert tuple(first) == (
        *base,
        "summary.json",
        "summary.md",
        "manifest.json",
    )
    assert len(first) == 7
    assert {name: first[name] for name in base} == base
    summary = json.loads(first["summary.json"])
    assert summary["phase_status"] == "PREPARATION_ONLY"
    assert summary["supplied_binding_count"] == 0
    assert summary["authoritatively_bound_binding_count"] == 0
    assert summary["human_acceptance_status"] == "NOT_RECORDED"
    assert summary["freeze_authorized"] is False
    assert summary["next_phase_eligible"] is False
    assert summary["execution_readiness"] is False
    assert first["summary.md"] == review_pack.build_review_pack_summary_markdown().encode(
        "utf-8"
    )

    manifest = json.loads(first["manifest.json"])
    expected_names = tuple(first)[:6]
    assert manifest["artifact_count"] == 6
    assert tuple(item["name"] for item in manifest["artifacts"]) == expected_names
    assert "manifest.json" not in {item["name"] for item in manifest["artifacts"]}
    for item in manifest["artifacts"]:
        payload = first[item["name"]]
        assert item["sha256"] == hashlib.sha256(payload).hexdigest()
        assert item["bytes"] == len(payload)
    manifest_text = first["manifest.json"].decode("utf-8")
    for forbidden in ("generated_at", "timestamp", "nonce", "data/local-private", "/private"):
        assert forbidden not in manifest_text


def test_review_pack_writer_uses_fixed_public_root_and_no_execution_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixed_parent = tmp_path / "reports/public-sample"
    fixed_parent.mkdir(parents=True)
    for path in (tmp_path, tmp_path / "reports", fixed_parent):
        path.chmod(0o755)
    forbidden_calls = {
        "verified_read_private_file": 0,
        "freeze_protocol": 0,
        "persist_protocol_manifest": 0,
        "materialize_boundary": 0,
    }

    def forbidden(name: str) -> Any:
        def record(*args: Any, **kwargs: Any) -> Any:
            forbidden_calls[name] += 1
            raise AssertionError("review bundle crossed an execution boundary")

        return record

    for name in forbidden_calls:
        monkeypatch.setattr(boundary, name, forbidden(name))
    monkeypatch.setattr(
        boundary,
        "write_public_bundle",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("review pack must not use the update-capable legacy writer")
        ),
    )
    paths = review_pack.write_review_pack_bundle(tmp_path)

    assert tuple(paths) == tuple(review_pack.build_review_pack_bundle())
    assert all(
        path.parent == tmp_path / review_pack.PUBLIC_REVIEW_PACK_ROOT
        for path in paths.values()
    )
    assert forbidden_calls == {name: 0 for name in forbidden_calls}


def _review_input_root(repo_root: Path) -> Path:
    return repo_root / boundary.CANONICAL_PRIVATE_ROOT / "review-inputs"


def _bind_unix_socket(path: Path) -> socket.socket:
    handle = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    original_directory = Path.cwd()
    try:
        os.chdir(path.parent)
        handle.bind(path.name)
    finally:
        os.chdir(original_directory)
    return handle


def _write_review_envelope(root: Path, name: str, envelope: Any) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    path = root / name
    path.write_bytes(boundary.canonical_json_bytes(envelope) + b"\n")
    return path


def _assert_conservative_cli_truth(payload: dict[str, Any]) -> None:
    assert payload["evidence_status"] == "DESIGN_ONLY"
    assert payload["phase_status"] == "PREPARATION_ONLY"
    assert payload["current_readiness_state"] == "DESIGN_ONLY"
    assert payload["human_acceptance_status"] == "NOT_RECORDED"
    assert payload["freeze_authorized"] is False
    assert payload["next_phase_eligible"] is False
    assert payload["execution_readiness"] is False
    assert "ok" not in payload
    assert "protocol_sha256" not in payload


def _forbid_review_execution_paths(monkeypatch: pytest.MonkeyPatch) -> dict[str, int]:
    calls = {
        "freeze_protocol": 0,
        "validate_named_inputs": 0,
        "persist_protocol_manifest": 0,
        "materialize_boundary": 0,
        "verify_generation": 0,
        "write_public_evidence": 0,
    }

    def forbidden(name: str) -> Any:
        def record(*args: Any, **kwargs: Any) -> Any:
            calls[name] += 1
            raise AssertionError(f"review CLI crossed {name}")

        return record

    monkeypatch.setattr(boundary, "freeze_protocol", forbidden("freeze_protocol"))
    monkeypatch.setattr(
        boundary,
        "validate_named_inputs",
        forbidden("validate_named_inputs"),
    )
    monkeypatch.setattr(
        boundary,
        "persist_protocol_manifest",
        forbidden("persist_protocol_manifest"),
    )
    monkeypatch.setattr(
        data_cli,
        "validate_named_inputs",
        forbidden("validate_named_inputs"),
    )
    monkeypatch.setattr(
        data_cli,
        "materialize_boundary",
        forbidden("materialize_boundary"),
    )
    monkeypatch.setattr(
        data_cli,
        "verify_generation",
        forbidden("verify_generation"),
    )
    monkeypatch.setattr(
        data_cli,
        "write_public_evidence",
        forbidden("write_public_evidence"),
    )
    return calls


def test_review_envelope_file_adapter_reads_one_bounded_named_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "review-inputs"
    candidate = _semantic_candidate_envelope()
    _write_review_envelope(root, "candidate.json", candidate)
    real_reader = boundary.verified_read_private_file
    reads: list[tuple[Path, str, int]] = []

    def record_read(private_root: Path, name: str, *, max_bytes: int) -> bytes:
        reads.append((private_root, name, max_bytes))
        return real_reader(private_root, name, max_bytes=max_bytes)

    monkeypatch.setattr(boundary, "verified_read_private_file", record_read)

    result = review_pack.lint_review_envelope_file(root, "candidate.json")

    assert result == review_pack.lint_review_envelope(candidate)
    assert result["lint_conforms"] is True
    assert reads == [(root, "candidate.json", review_pack.REVIEW_INPUT_MAX_BYTES)]
    serialized = json.dumps(result, ensure_ascii=False)
    assert "proposed_value" not in serialized
    assert "protocol_sha256" not in serialized


@pytest.mark.parametrize(
    "unsafe_name",
    (
        "/private/canary.json",
        "../canary.json",
        "~/canary.json",
        r"nested\canary.json",
        "",
    ),
)
def test_review_envelope_file_adapter_rejects_unsafe_name_before_reader(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    unsafe_name: str,
) -> None:
    calls = 0

    def forbidden_reader(*args: Any, **kwargs: Any) -> bytes:
        nonlocal calls
        calls += 1
        raise AssertionError("unsafe name reached the private reader")

    monkeypatch.setattr(boundary, "verified_read_private_file", forbidden_reader)
    result = review_pack.lint_review_envelope_file(tmp_path, unsafe_name)

    assert calls == 0
    assert result["lint_conforms"] is False
    _assert_conservative_cli_truth(result)
    assert result["diagnostics"] == [
        {
            "code": review_pack.REVIEW_LINT_UNEXPECTED_FAILURE,
            "section": "candidate_envelope",
        }
    ]


@pytest.mark.parametrize(
    "payload",
    (
        b'\xef\xbb\xbf{"schema_version":"canary"}',
        b'{"schema_version":"\xff"}',
        b'{"schema_version":"first","schema_version":"second"}',
        b"[" * 2_000 + b"0" + b"]" * 2_000,
    ),
)
def test_review_envelope_file_adapter_sanitizes_strict_json_failures(
    tmp_path: Path,
    payload: bytes,
) -> None:
    root = tmp_path / "review-inputs"
    root.mkdir()
    (root / "candidate.json").write_bytes(payload)

    result = review_pack.lint_review_envelope_file(root, "candidate.json")

    assert result["lint_conforms"] is False
    _assert_conservative_cli_truth(result)
    serialized = json.dumps(result, ensure_ascii=False)
    for forbidden in ("first", "second", "canary", "private", "candidate.json"):
        assert forbidden not in serialized


def test_review_envelope_file_adapter_rejects_oversized_input(
    tmp_path: Path,
) -> None:
    root = tmp_path / "review-inputs"
    root.mkdir()
    (root / "candidate.json").write_bytes(
        b"x" * (review_pack.REVIEW_INPUT_MAX_BYTES + 1)
    )

    result = review_pack.lint_review_envelope_file(root, "candidate.json")

    assert result["lint_conforms"] is False
    _assert_conservative_cli_truth(result)


@pytest.mark.parametrize("root_kind", ("missing", "symlink", "exchange"))
def test_review_envelope_file_adapter_rejects_missing_redirected_or_exchanged_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    root_kind: str,
) -> None:
    root = tmp_path / "review-inputs"
    if root_kind == "missing":
        pass
    elif root_kind == "symlink":
        outside = tmp_path / "outside"
        _write_review_envelope(outside, "candidate.json", _semantic_candidate_envelope())
        root.symlink_to(outside, target_is_directory=True)
    else:
        _write_review_envelope(root, "candidate.json", _semantic_candidate_envelope())
        real_read = os.read
        exchanged = False

        def exchange_root(descriptor: int, length: int) -> bytes:
            nonlocal exchanged
            payload = real_read(descriptor, length)
            if not exchanged:
                exchanged = True
                root.rename(tmp_path / "review-inputs-old")
                root.mkdir()
            return payload

        monkeypatch.setattr(os, "read", exchange_root)

    result = review_pack.lint_review_envelope_file(root, "candidate.json")

    assert result["lint_conforms"] is False
    _assert_conservative_cli_truth(result)
    if root_kind == "missing":
        assert not root.exists()
    elif root_kind == "exchange":
        assert list(root.iterdir()) == []


@pytest.mark.parametrize(
    "final_kind",
    ("symlink", "hardlink", "nonregular", "fifo", "socket"),
)
def test_review_envelope_file_adapter_rejects_unsafe_final_object(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    final_kind: str,
) -> None:
    root = tmp_path / "review-inputs"
    root.mkdir()
    final = root / "candidate.json"
    outside = tmp_path / "outside.json"
    outside.write_bytes(b"outside-canary-unchanged\n")
    socket_handle: socket.socket | None = None
    if final_kind == "symlink":
        final.symlink_to(outside)
    elif final_kind == "hardlink":
        os.link(outside, final)
    elif final_kind == "nonregular":
        final.mkdir()
    elif final_kind == "fifo":
        os.mkfifo(final)
    else:
        socket_handle = _bind_unix_socket(final)
    before = final.lstat()
    final_open_attempts = 0
    reads = 0
    real_open = os.open
    real_read = os.read

    def reject_final_open(
        path: str | bytes | os.PathLike[str],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        nonlocal final_open_attempts
        if path == final.name and dir_fd is not None:
            final_open_attempts += 1
            if not flags & getattr(os, "O_NONBLOCK", 0):
                raise AssertionError("unsafe final reached a blocking open")
        return real_open(path, flags, mode, dir_fd=dir_fd)

    def counted_read(fd: int, size: int) -> bytes:
        nonlocal reads
        reads += 1
        return real_read(fd, size)

    monkeypatch.setattr(os, "open", reject_final_open)
    monkeypatch.setattr(os, "read", counted_read)

    try:
        result = review_pack.lint_review_envelope_file(root, "candidate.json")
    finally:
        if socket_handle is not None:
            socket_handle.close()

    assert final_open_attempts == 0
    assert reads == 0
    assert boundary._same_identity(before, final.lstat())
    assert result["lint_conforms"] is False
    _assert_conservative_cli_truth(result)
    assert outside.read_bytes() == b"outside-canary-unchanged\n"
    assert "outside" not in json.dumps(result, ensure_ascii=False)


@pytest.mark.parametrize("final_kind", ("fifo", "socket"))
def test_review_lint_cli_rejects_nonregular_final_without_open_read_or_leak(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    final_kind: str,
) -> None:
    monkeypatch.setattr(data_cli, "REPO_ROOT", tmp_path)
    root = _review_input_root(tmp_path)
    root.mkdir(parents=True)
    final = root / "candidate.json"
    socket_handle: socket.socket | None = None
    if final_kind == "fifo":
        os.mkfifo(final)
    else:
        socket_handle = _bind_unix_socket(final)
    before = final.lstat()
    final_open_attempts = 0
    reads = 0
    real_open = os.open
    real_read = os.read

    def reject_final_open(
        path: str | bytes | os.PathLike[str],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        nonlocal final_open_attempts
        if path == final.name and dir_fd is not None:
            final_open_attempts += 1
            if not flags & getattr(os, "O_NONBLOCK", 0):
                raise AssertionError("unsafe final reached a blocking open")
        return real_open(path, flags, mode, dir_fd=dir_fd)

    def counted_read(fd: int, size: int) -> bytes:
        nonlocal reads
        reads += 1
        return real_read(fd, size)

    monkeypatch.setattr(os, "open", reject_final_open)
    monkeypatch.setattr(os, "read", counted_read)

    try:
        rc = data_cli.main(
            ["clean-boundary-review-lint", "--review-pack", final.name]
        )
        captured = capsys.readouterr()
    finally:
        if socket_handle is not None:
            socket_handle.close()

    result = json.loads(captured.out)
    assert rc != 0
    assert captured.err == ""
    assert result == review_pack.review_command_failure_truth()
    assert final_open_attempts == 0
    assert reads == 0
    assert boundary._same_identity(before, final.lstat())
    serialized = captured.out.lower()
    for forbidden in ("candidate.json", "/private", "fifo", "socket", "canary"):
        assert forbidden not in serialized


@pytest.mark.parametrize(
    "fault",
    (
        PermissionError("private-permission-canary"),
        OSError("private-oserror-canary"),
    ),
)
def test_review_envelope_file_adapter_sanitizes_ordinary_read_faults(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault: OSError,
) -> None:
    monkeypatch.setattr(
        boundary,
        "verified_read_private_file",
        lambda *args, **kwargs: (_ for _ in ()).throw(fault),
    )

    result = review_pack.lint_review_envelope_file(tmp_path, "candidate.json")

    assert result["lint_conforms"] is False
    serialized = json.dumps(result, ensure_ascii=False)
    assert "canary" not in serialized
    assert type(fault).__name__ not in serialized


def test_review_envelope_file_adapter_does_not_swallow_baseexception(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        boundary,
        "verified_read_private_file",
        lambda *args, **kwargs: (_ for _ in ()).throw(KeyboardInterrupt()),
    )

    with pytest.raises(KeyboardInterrupt):
        review_pack.lint_review_envelope_file(tmp_path, "candidate.json")


@pytest.mark.parametrize(
    "failure_case",
    (
        "missing",
        "permission",
        "oversize",
        "invalid-utf8",
        "duplicate-keys",
        "deep-json",
        "unexpected-oserror",
    ),
)
def test_review_lint_cli_capture_layer_sanitizes_input_failure_matrix(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    failure_case: str,
) -> None:
    monkeypatch.setattr(data_cli, "REPO_ROOT", tmp_path)
    root = _review_input_root(tmp_path)
    name = "candidate.json"
    candidate: Path | None = None
    before_bytes: bytes | None = None
    before_stat: os.stat_result | None = None

    if failure_case == "permission":
        monkeypatch.setattr(
            boundary,
            "verified_read_private_file",
            lambda *args, **kwargs: (_ for _ in ()).throw(
                PermissionError("/private/permission-canary")
            ),
        )
    elif failure_case == "unexpected-oserror":
        monkeypatch.setattr(
            boundary,
            "verified_read_private_file",
            lambda *args, **kwargs: (_ for _ in ()).throw(
                OSError("/private/oserror-canary")
            ),
        )
    elif failure_case != "missing":
        payloads = {
            "oversize": b"x" * (review_pack.REVIEW_INPUT_MAX_BYTES + 1),
            "invalid-utf8": b'{"schema_version":"\xff-private-canary"}',
            "duplicate-keys": b'{"canary":1,"canary":2}',
            "deep-json": b"[" * 2_000 + b"0" + b"]" * 2_000,
        }
        root.mkdir(parents=True)
        candidate = root / name
        candidate.write_bytes(payloads[failure_case])
        before_bytes = candidate.read_bytes()
        before_stat = candidate.stat()

    rc = data_cli.main(["clean-boundary-review-lint", "--review-pack", name])
    captured = capsys.readouterr()
    result = json.loads(captured.out)

    assert rc != 0
    assert captured.err == ""
    assert result == review_pack.review_command_failure_truth()
    assert result["lint_conforms"] is False
    _assert_conservative_cli_truth(result)
    serialized = captured.out.lower()
    assert '"path"' not in serialized
    for forbidden in (
        "candidate.json",
        "/private",
        "canary",
        "permissionerror",
        "oserror",
        "unicodedecodeerror",
        "jsondecodeerror",
        "recursionerror",
        "filenotfounderror",
    ):
        assert forbidden not in serialized
    if candidate is None:
        assert not root.exists()
    else:
        assert before_bytes is not None and before_stat is not None
        after = candidate.stat()
        assert candidate.read_bytes() == before_bytes
        assert (
            after.st_dev,
            after.st_ino,
            after.st_mode,
            after.st_nlink,
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
        ) == (
            before_stat.st_dev,
            before_stat.st_ino,
            before_stat.st_mode,
            before_stat.st_nlink,
            before_stat.st_size,
            before_stat.st_mtime_ns,
            before_stat.st_ctime_ns,
        )


def test_review_lint_cli_complete_candidate_has_strict_success_truth_and_zero_lifecycle_calls(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(data_cli, "REPO_ROOT", tmp_path)
    candidate = _semantic_candidate_envelope()
    candidate_path = _write_review_envelope(
        _review_input_root(tmp_path),
        "candidate.json",
        candidate,
    )
    before = candidate_path.stat()
    before_bytes = candidate_path.read_bytes()
    before_names = tuple(path.name for path in candidate_path.parent.iterdir())
    forbidden_calls = _forbid_review_execution_paths(monkeypatch)

    rc = data_cli.main(
        ["clean-boundary-review-lint", "--review-pack", "candidate.json"]
    )
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert rc == 0
    assert captured.err == ""
    assert payload == review_pack.lint_review_envelope(candidate)
    assert payload["lint_conforms"] is True
    assert payload["decision"] == "CANDIDATE_PACK_STRUCTURALLY_COMPLETE_REVIEW_REQUIRED"
    assert payload["candidate_pack_status"] == "STRUCTURALLY_COMPLETE_REVIEW_REQUIRED"
    _assert_conservative_cli_truth(payload)
    assert forbidden_calls == {name: 0 for name in forbidden_calls}
    after = candidate_path.stat()
    assert candidate_path.read_bytes() == before_bytes
    assert tuple(path.name for path in candidate_path.parent.iterdir()) == before_names
    assert (
        after.st_dev,
        after.st_ino,
        after.st_mode,
        after.st_nlink,
        after.st_size,
        after.st_mtime_ns,
        after.st_ctime_ns,
    ) == (
        before.st_dev,
        before.st_ino,
        before.st_mode,
        before.st_nlink,
        before.st_size,
        before.st_mtime_ns,
        before.st_ctime_ns,
    )
    serialized = json.dumps(payload, ensure_ascii=False)
    for forbidden in ("proposed_value", "data/local-private", "candidate.json", "/private"):
        assert forbidden not in serialized


@pytest.mark.parametrize(
    ("name", "payload"),
    (
        pytest.param(
            "template.json",
            lambda: boundary.canonical_json_bytes(review_pack.build_review_pack_template()) + b"\n",
            id="template-incomplete",
        ),
        pytest.param("malformed.json", lambda: b"{not-json-private-canary", id="malformed"),
        pytest.param(
            "semantic-invalid.json",
            lambda: boundary.canonical_json_bytes(_candidate_envelope()) + b"\n",
            id="semantic-invalid",
        ),
    ),
)
def test_review_lint_cli_rejects_incomplete_malformed_and_semantic_invalid_inputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    name: str,
    payload: Any,
) -> None:
    monkeypatch.setattr(data_cli, "REPO_ROOT", tmp_path)
    root = _review_input_root(tmp_path)
    root.mkdir(parents=True)
    (root / name).write_bytes(payload())

    rc = data_cli.main(["clean-boundary-review-lint", "--review-pack", name])
    captured = capsys.readouterr()
    result = json.loads(captured.out)

    assert rc != 0
    assert captured.err == ""
    assert result["lint_conforms"] is False
    _assert_conservative_cli_truth(result)
    serialized = json.dumps(result, ensure_ascii=False)
    assert name not in serialized
    assert "private-canary" not in serialized


def test_review_lint_cli_missing_root_stays_absent_and_unexpected_fault_is_sanitized(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(data_cli, "REPO_ROOT", tmp_path)
    root = _review_input_root(tmp_path)

    rc = data_cli.main(
        ["clean-boundary-review-lint", "--review-pack", "missing-private-canary.json"]
    )
    first = capsys.readouterr()
    first_payload = json.loads(first.out)

    assert rc != 0
    assert first.err == ""
    assert not root.exists()
    assert "missing-private-canary" not in json.dumps(first_payload, ensure_ascii=False)

    monkeypatch.setattr(
        boundary,
        "verified_read_private_file",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            OSError("unexpected-private-oserror-canary")
        ),
    )
    rc = data_cli.main(
        ["clean-boundary-review-lint", "--review-pack", "safe-name.json"]
    )
    second = capsys.readouterr()
    second_payload = json.loads(second.out)
    assert rc != 0
    assert second.err == ""
    assert "canary" not in json.dumps(second_payload, ensure_ascii=False)


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("freeze_authorized", True),
        ("evidence_status", "EXECUTABLE"),
        ("phase_status", "EXECUTION"),
        ("protocol_freeze_status", "FROZEN"),
        ("authoritatively_bound_binding_count", 29),
        ("ok", True),
        ("protocol_sha256", "a" * 64),
        ("private_path", "/private/canary"),
    ),
)
def test_review_lint_cli_normalizes_any_nonexact_positive_truth_to_fixed_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    field: str,
    value: Any,
) -> None:
    monkeypatch.setattr(data_cli, "REPO_ROOT", tmp_path)
    inconsistent = review_pack.lint_review_envelope(_semantic_candidate_envelope())
    inconsistent[field] = value
    monkeypatch.setattr(
        review_pack,
        "lint_review_envelope_file",
        lambda *args, **kwargs: inconsistent,
    )

    rc = data_cli.main(
        ["clean-boundary-review-lint", "--review-pack", "safe-name.json"]
    )
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert rc != 0
    assert captured.err == ""
    assert payload["lint_conforms"] is False
    _assert_conservative_cli_truth(payload)
    serialized = json.dumps(payload, ensure_ascii=False)
    assert "canary" not in serialized
    assert "protocol_sha256" not in serialized
    assert "EXECUTABLE" not in serialized


def test_validate_lockbox_help_preserves_existing_parser_payload_behavior(
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc = data_cli.main(["validate-lockbox", "--help"])
    captured = capsys.readouterr()

    assert rc == 0
    assert captured.err == ""
    assert "usage: voice2task-data validate-lockbox" in captured.out
    assert '"category": "ArgumentParserError"' in captured.out
    assert '"message": ""' in captured.out


@pytest.mark.parametrize(
    "argv",
    (
        ["clean-boundary-review-lint"],
        ["clean-boundary-review-lint", "--review-pack"],
        ["clean-boundary-review-lint", "--review-pack", "safe.json", "extra-canary"],
        ["clean-boundary-review-lint", "--bindings", "/private/canary"],
        ["clean-boundary-review-lint", "--source-contract", "/private/canary"],
        ["clean-boundary-review-lint", "--compiler-card", "/private/canary"],
        ["clean-boundary-review-lint", "--model-card", "/private/canary"],
        ["clean-boundary-review-pack", "extra-private-canary"],
    ),
)
def test_review_cli_parser_errors_are_fixed_safe_and_never_call_reader_or_writer(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    argv: list[str],
) -> None:
    reader_calls = 0
    writer_calls = 0

    def forbidden_reader(*args: Any, **kwargs: Any) -> bytes:
        nonlocal reader_calls
        reader_calls += 1
        raise AssertionError("parser error reached private reader")

    def forbidden_writer(*args: Any, **kwargs: Any) -> dict[str, Path]:
        nonlocal writer_calls
        writer_calls += 1
        raise AssertionError("parser error reached review writer")

    monkeypatch.setattr(boundary, "verified_read_private_file", forbidden_reader)
    monkeypatch.setattr(review_pack, "write_review_pack_bundle", forbidden_writer)

    rc = data_cli.main(argv)
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert rc != 0
    assert captured.err == ""
    assert reader_calls == 0
    assert writer_calls == 0
    assert payload["lint_conforms"] is False
    _assert_conservative_cli_truth(payload)
    serialized = json.dumps(payload, ensure_ascii=False)
    for forbidden in ("canary", "/private", "--bindings", "--source-contract"):
        assert forbidden not in serialized


def test_review_pack_cli_calls_fixed_writer_once_and_prints_no_paths_or_execution_claims(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(data_cli, "REPO_ROOT", tmp_path)
    calls: list[Path] = []

    def record_writer(trusted_root: Path) -> dict[str, Path]:
        calls.append(trusted_root)
        return {
            "manifest.json": trusted_root
            / review_pack.PUBLIC_REVIEW_PACK_ROOT
            / "private-path-canary.json"
        }

    monkeypatch.setattr(review_pack, "write_review_pack_bundle", record_writer)
    monkeypatch.setattr(
        boundary,
        "verified_read_private_file",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("pack command read private input")
        ),
    )
    forbidden_calls = _forbid_review_execution_paths(monkeypatch)

    rc = data_cli.main(["clean-boundary-review-pack"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert rc == 0
    assert captured.err == ""
    assert calls == [tmp_path]
    assert not _review_input_root(tmp_path).exists()
    _assert_conservative_cli_truth(payload)
    assert payload["decision"] == "ACQUISITION_AND_BINDING_REVIEW_PACK_READY_EXECUTION_BLOCKED"
    assert forbidden_calls == {name: 0 for name in forbidden_calls}
    serialized = json.dumps(payload, ensure_ascii=False)
    for forbidden in ("path", "canary", "protocol_sha256", "PUBLISHED"):
        assert forbidden not in serialized


@pytest.mark.parametrize(
    "fault",
    (
        boundary.BoundaryViolation("PRIVATE_BOUNDARY_CANARY"),
        RuntimeError("private-runtime-canary"),
    ),
)
def test_review_pack_cli_sanitizes_boundary_and_ordinary_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    fault: Exception,
) -> None:
    monkeypatch.setattr(data_cli, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(
        review_pack,
        "write_review_pack_bundle",
        lambda *args, **kwargs: (_ for _ in ()).throw(fault),
    )

    rc = data_cli.main(["clean-boundary-review-pack"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert rc != 0
    assert captured.err == ""
    assert payload["lint_conforms"] is False
    _assert_conservative_cli_truth(payload)
    serialized = json.dumps(payload, ensure_ascii=False)
    assert "canary" not in serialized.lower()
    assert type(fault).__name__ not in serialized


def test_committed_review_pack_matches_builder_and_all_template_objects_fail_freeze(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = data_cli.REPO_ROOT / review_pack.PUBLIC_REVIEW_PACK_ROOT
    private_root = data_cli.REPO_ROOT / boundary.CANONICAL_PRIVATE_ROOT
    trusted_parent_gid = target.parent.stat().st_gid
    assert not private_root.exists()
    assert target.is_dir()

    target_metadata = target.lstat()
    assert stat.S_ISDIR(target_metadata.st_mode)
    assert stat.S_IMODE(target_metadata.st_mode) == 0o755
    assert target_metadata.st_uid == os.geteuid()
    assert target_metadata.st_gid == trusted_parent_gid

    expected = review_pack.build_review_pack_bundle()
    assert set(path.name for path in target.iterdir()) == set(expected)
    for name in expected:
        member_metadata = (target / name).lstat()
        assert stat.S_ISREG(member_metadata.st_mode)
        assert stat.S_IMODE(member_metadata.st_mode) == 0o644
        assert member_metadata.st_uid == os.geteuid()
        assert member_metadata.st_gid == trusted_parent_gid
        assert member_metadata.st_nlink == 1
    observed = {name: (target / name).read_bytes() for name in expected}
    assert observed == expected

    manifest = boundary.strict_json_loads(observed["manifest.json"])
    expected_manifest_names = tuple(expected)[:6]
    assert manifest["artifact_count"] == 6
    assert tuple(item["name"] for item in manifest["artifacts"]) == (
        expected_manifest_names
    )
    assert "manifest.json" not in {
        item["name"] for item in manifest["artifacts"]
    }
    for item in manifest["artifacts"]:
        payload = observed[item["name"]]
        assert item["sha256"] == hashlib.sha256(payload).hexdigest()
        assert item["bytes"] == len(payload)

    template = boundary.strict_json_loads(observed["review-pack.template.json"])
    surfaces = [item for item in _walk(template) if isinstance(item, dict)]
    persisted = 0

    def forbidden_persist(*args: Any, **kwargs: Any) -> Any:
        nonlocal persisted
        persisted += 1
        raise AssertionError("committed template reached protocol persistence")

    monkeypatch.setattr(boundary, "persist_protocol_manifest", forbidden_persist)
    for surface in surfaces:
        before = copy.deepcopy(surface)
        with pytest.raises(boundary.BoundaryViolation):
            boundary.freeze_protocol(surface, surface, surface, surface)
        assert surface == before

    assert persisted == 0
    assert not private_root.exists()
    assert not tuple(
        target.parent.glob(f"{boundary.REVIEW_PUBLIC_RECOVERY_PREFIX}*")
    )

    expected_s0_hashes = {
        "summary.json": (
            "24658fb7ca9143564133fa8521bed81b97f89b5cd94430560577def71ae85a13"
        ),
        "summary.md": (
            "9426602fe6fc768d569e1d7ceff78a2f5261a14fe4ca7c2e27391e19d7a08e25"
        ),
        "protocol-manifest.json": (
            "84c775907f585a79d8d577077c4484e9648721b3a6d0619d01f912e092c0e8cc"
        ),
        "population-seal-attestation.json": (
            "19ea3d3b944faa3a1ef732db83d50e9affc59d4f4e0e231f5c6d980a81ade849"
        ),
        "lineage-attestation.json": (
            "e7b6dae68ba5dda941238d803e7387377e48bcdcc4d1e9f7786e118f5e68f0dc"
        ),
    }
    s0_root = data_cli.REPO_ROOT / boundary.PUBLIC_REPORT_ROOT
    observed_s0_hashes = {
        name: hashlib.sha256((s0_root / name).read_bytes()).hexdigest()
        for name in expected_s0_hashes
    }
    assert observed_s0_hashes == expected_s0_hashes
