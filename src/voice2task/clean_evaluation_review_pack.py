from __future__ import annotations

import hashlib
from pathlib import Path, PurePosixPath
from typing import Any

import voice2task.clean_evaluation_boundary as boundary

NOT_SUPPLIED = "NOT_SUPPLIED"
ENVELOPE_VERSION = "clean-evaluation-review-envelope-v1"
SCHEMA_DRAFT = "https://json-schema.org/draft/2020-12/schema"
SCHEMA_ROOT_ID = "https://voice2task.local/schemas/clean-evaluation-review-pack-v1"
TEMPLATE_ENVELOPE_ID = (
    "https://voice2task.local/schemas/clean-evaluation-review-envelope-template-v1"
)
CANDIDATE_ENVELOPE_ID = (
    "https://voice2task.local/schemas/clean-evaluation-review-envelope-v1"
)
REVIEW_INPUT_ROOT = (
    (boundary.CANONICAL_PRIVATE_ROOT / "review-inputs").as_posix() + "/"
)
PUBLIC_REVIEW_PACK_ROOT = boundary.REVIEW_PUBLIC_BUNDLE_ROOT
REVIEW_LINT_UNEXPECTED_FAILURE = "REVIEW_LINT_UNEXPECTED_FAILURE"
REVIEW_DIAGNOSTIC_CODES = frozenset(
    {
        "REVIEW_ENVELOPE_MALFORMED",
        "REVIEW_ENVELOPE_INCOMPLETE",
        "BINDING_INCOMPLETE_OR_PLACEHOLDER",
        "ACQUISITION_SOURCE_UNAVAILABLE_OR_UNVERIFIABLE",
        "POWER_ASSUMPTION_UNSUPPORTED",
        REVIEW_LINT_UNEXPECTED_FAILURE,
    }
)
REVIEW_ENVELOPE_SECTIONS = frozenset(
    {
        "candidate_envelope",
        "binding_draft",
        "source_contract_draft",
        "compiler_card_draft",
        "model_card_draft",
    }
)
REVIEW_MAX_DEPTH = 64
REVIEW_NODE_BUDGET = 10_000
REVIEW_INPUT_MAX_BYTES = 1_048_576
_REVIEW_CANONICAL_DIAGNOSTIC_FIELDS = frozenset(
    {
        "schema_version",
        "document_kind",
        "envelope_schema_id",
        "template_only",
        "execution_input_marker",
        "human_acceptance_marker",
        "binding_draft",
        "source_contract_draft",
        "compiler_card_draft",
        "model_card_draft",
        "schema_id",
        "draft_only",
        "target_schema",
        "proposed_bindings",
        "proposed_fields",
        *boundary.EXECUTION_BINDING_FIELDS,
        *boundary.source_contract_fields(),
        *boundary.compiler_card_fields(),
        *boundary.model_card_fields(),
    }
)


def render_json(value: Any) -> bytes:
    return boundary.canonical_json_bytes(value) + b"\n"


def build_binding_catalog() -> dict[str, Any]:
    entries = [
        {
            "ordinal": ordinal,
            "name": name,
            "responsibility": {
                "provider": "EXTERNAL_PROVIDER_REQUIRED",
                "independent_reviewer": "INDEPENDENT_REVIEWER_REQUIRED",
            },
            "required_evidence": [
                "authority_evidence",
                "derivation_evidence",
                "applicability",
                "zero_access_attestation",
                "independent_review",
            ],
            "human_acceptance_gate": "NOT_RECORDED",
        }
        for ordinal, name in enumerate(boundary.EXECUTION_BINDING_FIELDS, start=1)
    ]
    return {
        "schema_version": "clean-evaluation-binding-catalog-v1",
        "binding_inventory_count": len(entries),
        "entries": entries,
    }


def _draft_specs() -> tuple[tuple[str, str, str, str, tuple[str, ...]], ...]:
    return (
        (
            "binding_draft",
            "clean-evaluation-binding-draft-v1",
            "clean-evaluation-bindings-v1",
            "proposed_bindings",
            tuple(boundary.EXECUTION_BINDING_FIELDS),
        ),
        (
            "source_contract_draft",
            "clean-evaluation-source-contract-draft-v1",
            "clean-source-contract-v1",
            "proposed_fields",
            tuple(sorted(boundary.source_contract_fields())),
        ),
        (
            "compiler_card_draft",
            "clean-evaluation-compiler-card-draft-v1",
            "compiler-power-card-v1",
            "proposed_fields",
            tuple(sorted(boundary.compiler_card_fields())),
        ),
        (
            "model_card_draft",
            "clean-evaluation-model-card-draft-v1",
            "model-power-card-v1",
            "proposed_fields",
            tuple(sorted(boundary.model_card_fields())),
        ),
    )


def _strict_object(
    properties: dict[str, Any],
    *,
    schema_id: str | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }
    if schema_id is not None:
        result["$id"] = schema_id
    return result


def _template_field_schema() -> dict[str, Any]:
    return _strict_object(
        {
            "proposed_value": {"const": NOT_SUPPLIED},
            "evidence": {"const": NOT_SUPPLIED},
            "review": {"const": NOT_SUPPLIED},
        },
        schema_id="https://voice2task.local/schemas/review-draft-field-template-v1",
    )


def _candidate_field_schema() -> dict[str, Any]:
    supplied = {"$ref": f"{SCHEMA_ROOT_ID}#/$defs/safeCandidateJson"}
    return _strict_object(
        {
            "proposed_value": supplied,
            "evidence": supplied,
            "review": supplied,
        },
        schema_id="https://voice2task.local/schemas/review-draft-field-candidate-v1",
    )


def _safe_candidate_json_schema() -> dict[str, Any]:
    forbidden_layouts = [
        {
            "type": "object",
            "patternProperties": {"^.*$": {}},
            "required": sorted(fields),
            "additionalProperties": False,
        }
        for fields in (
            boundary.binding_packet_fields(),
            boundary.binding_dossier_fields(),
            boundary.source_contract_fields(),
            boundary.compiler_card_fields(),
            boundary.model_card_fields(),
        )
    ]
    recursive_ref = {"$ref": f"{SCHEMA_ROOT_ID}#/$defs/safeCandidateJson"}
    return {
        "$id": "https://voice2task.local/schemas/safe-candidate-json-v1",
        "not": {"anyOf": forbidden_layouts},
        "oneOf": [
            {"type": "null"},
            {"type": "boolean"},
            {"type": "integer"},
            {"type": "string", "not": {"const": NOT_SUPPLIED}},
            {"type": "array", "items": recursive_ref},
            {
                "type": "object",
                "patternProperties": {"^.*$": recursive_ref},
                "additionalProperties": False,
            },
        ],
    }


def _draft_schema(
    *,
    version: str,
    target_schema: str,
    proposed_key: str,
    field_names: tuple[str, ...],
    field_definition: str,
    candidate: bool,
) -> dict[str, Any]:
    schema_id = f"https://voice2task.local/schemas/{version}"
    definition_id = f"{schema_id}-candidate" if candidate else schema_id
    proposed_fields = _strict_object(
        {
            name: {
                "$ref": f"{SCHEMA_ROOT_ID}#/$defs/{field_definition}",
            }
            for name in field_names
        }
    )
    return _strict_object(
        {
            "schema_id": {"const": schema_id},
            "schema_version": {"const": version},
            "draft_only": {"const": True},
            "target_schema": {"const": target_schema},
            proposed_key: proposed_fields,
        },
        schema_id=definition_id,
    )


def _envelope_schema(*, candidate: bool) -> dict[str, Any]:
    properties: dict[str, Any] = {
        "schema_version": {"const": ENVELOPE_VERSION},
        "document_kind": {"const": "CANDIDATE" if candidate else "TEMPLATE"},
        "envelope_schema_id": {
            "const": CANDIDATE_ENVELOPE_ID if candidate else TEMPLATE_ENVELOPE_ID
        },
        "template_only": {"const": not candidate},
        "execution_input_marker": {"const": "NOT_AN_EXECUTION_INPUT"},
        "human_acceptance_marker": {"const": "NO_HUMAN_ACCEPTANCE_RECORDED"},
    }
    suffix = "Candidate" if candidate else "Template"
    for section_name, _version, _target, _proposed, _fields in _draft_specs():
        definition_name = section_name.removesuffix("_draft")
        properties[section_name] = {
            "$ref": f"{SCHEMA_ROOT_ID}#/$defs/{definition_name}Draft{suffix}"
        }
    return _strict_object(
        properties,
        schema_id=CANDIDATE_ENVELOPE_ID if candidate else TEMPLATE_ENVELOPE_ID,
    )


def build_review_pack_schema() -> dict[str, Any]:
    definitions: dict[str, Any] = {
        "templateDraftField": _template_field_schema(),
        "candidateDraftField": _candidate_field_schema(),
        "safeCandidateJson": _safe_candidate_json_schema(),
    }
    for section_name, version, target, proposed_key, fields in _draft_specs():
        definition_name = section_name.removesuffix("_draft")
        definitions[f"{definition_name}DraftTemplate"] = _draft_schema(
            version=version,
            target_schema=target,
            proposed_key=proposed_key,
            field_names=fields,
            field_definition="templateDraftField",
            candidate=False,
        )
        definitions[f"{definition_name}DraftCandidate"] = _draft_schema(
            version=version,
            target_schema=target,
            proposed_key=proposed_key,
            field_names=fields,
            field_definition="candidateDraftField",
            candidate=True,
        )
    definitions["templateEnvelope"] = _envelope_schema(candidate=False)
    definitions["candidateEnvelope"] = _envelope_schema(candidate=True)
    return {
        "$schema": SCHEMA_DRAFT,
        "$id": SCHEMA_ROOT_ID,
        "oneOf": [
            {"$ref": "#/$defs/templateEnvelope"},
            {"$ref": "#/$defs/candidateEnvelope"},
        ],
        "$defs": definitions,
    }


def _draft_template(
    version: str,
    target_schema: str,
    proposed_key: str,
    field_names: tuple[str, ...],
) -> dict[str, Any]:
    return {
        "schema_id": f"https://voice2task.local/schemas/{version}",
        "schema_version": version,
        "draft_only": True,
        "target_schema": target_schema,
        proposed_key: {
            name: {
                "proposed_value": NOT_SUPPLIED,
                "evidence": NOT_SUPPLIED,
                "review": NOT_SUPPLIED,
            }
            for name in field_names
        },
    }


def build_review_pack_template() -> dict[str, Any]:
    template: dict[str, Any] = {
        "schema_version": ENVELOPE_VERSION,
        "document_kind": "TEMPLATE",
        "envelope_schema_id": TEMPLATE_ENVELOPE_ID,
        "template_only": True,
        "execution_input_marker": "NOT_AN_EXECUTION_INPUT",
        "human_acceptance_marker": "NO_HUMAN_ACCEPTANCE_RECORDED",
    }
    for section_name, version, target, proposed_key, fields in _draft_specs():
        template[section_name] = _draft_template(
            version,
            target,
            proposed_key,
            fields,
        )
    return template


class _ReviewStructureError(Exception):
    def __init__(self, code: str, section: str, field: str | None = None) -> None:
        self.code = code
        self.section = section
        self.field = field
        super().__init__(code)


def _diagnostic(code: str, section: str, field: str | None = None) -> dict[str, str]:
    safe_code = (
        code
        if isinstance(code, str) and code in REVIEW_DIAGNOSTIC_CODES
        else REVIEW_LINT_UNEXPECTED_FAILURE
    )
    safe_section = (
        section
        if isinstance(section, str) and section in REVIEW_ENVELOPE_SECTIONS
        else "candidate_envelope"
    )
    result = {"code": safe_code, "section": safe_section}
    if (
        isinstance(field, str)
        and field in _REVIEW_CANONICAL_DIAGNOSTIC_FIELDS
    ):
        result["field"] = field
    return result


def _supplied_binding_count(envelope: Any) -> int:
    if not isinstance(envelope, dict):
        return 0
    draft = envelope.get("binding_draft")
    if not isinstance(draft, dict):
        return 0
    proposed = draft.get("proposed_bindings")
    if not isinstance(proposed, dict):
        return 0
    count = 0
    for name in boundary.EXECUTION_BINDING_FIELDS:
        record = proposed.get(name)
        if isinstance(record, dict) and record.get("proposed_value", NOT_SUPPLIED) != NOT_SUPPLIED:
            count += 1
    return count


def _incomplete_lint_truth(
    supplied_binding_count: int,
    diagnostic: dict[str, str],
) -> dict[str, Any]:
    return {
        "evidence_status": "DESIGN_ONLY",
        "phase_status": "PREPARATION_ONLY",
        "decision": "ACQUISITION_AND_BINDING_REVIEW_PACK_READY_EXECUTION_BLOCKED",
        "review_pack_status": "READY_FOR_EXTERNAL_COMPLETION",
        "candidate_pack_status": "INCOMPLETE",
        "binding_inventory_count": len(boundary.EXECUTION_BINDING_FIELDS),
        "supplied_binding_count": supplied_binding_count,
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
        "diagnostics": [diagnostic],
    }


def _complete_lint_truth() -> dict[str, Any]:
    return {
        "evidence_status": "DESIGN_ONLY",
        "phase_status": "PREPARATION_ONLY",
        "decision": "CANDIDATE_PACK_STRUCTURALLY_COMPLETE_REVIEW_REQUIRED",
        "review_pack_status": "READY_FOR_EXTERNAL_COMPLETION",
        "candidate_pack_status": "STRUCTURALLY_COMPLETE_REVIEW_REQUIRED",
        "binding_inventory_count": len(boundary.EXECUTION_BINDING_FIELDS),
        "supplied_binding_count": len(boundary.EXECUTION_BINDING_FIELDS),
        "authoritatively_bound_binding_count": 0,
        "acquisition_source_status": "CANDIDATE_DECLARED_REVIEW_REQUIRED",
        "current_readiness_state": "DESIGN_ONLY",
        "execution_bindings_status": "INCOMPLETE",
        "protocol_freeze_status": "NOT_FROZEN",
        "clean_population_status": "NOT_MATERIALIZED",
        "boundary_integrity_status": "NOT_CREATED",
        "human_acceptance_status": "NOT_RECORDED",
        "freeze_authorized": False,
        "next_phase_eligible": False,
        "execution_readiness": False,
        "lint_conforms": True,
        "diagnostics": [],
    }


def review_command_failure_truth() -> dict[str, Any]:
    return _incomplete_lint_truth(
        0,
        _diagnostic(REVIEW_LINT_UNEXPECTED_FAILURE, "candidate_envelope"),
    )


def review_lint_success_truth() -> dict[str, Any]:
    return _complete_lint_truth()


def _expect_exact_keys(
    value: Any,
    expected: tuple[str, ...],
    section: str,
    field: str | None = None,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise _ReviewStructureError("REVIEW_ENVELOPE_MALFORMED", section, field)
    missing = [name for name in expected if name not in value]
    if missing:
        raise _ReviewStructureError("REVIEW_ENVELOPE_MALFORMED", section, missing[0])
    if set(value) != set(expected):
        raise _ReviewStructureError("REVIEW_ENVELOPE_MALFORMED", section, field)
    return value


def _candidate_value_issue(value: Any) -> str | None:
    stack: list[tuple[Any, int, bool]] = [(value, 0, False)]
    active: set[int] = set()
    observed_nodes = 0
    raw_layouts = (
        boundary.binding_packet_fields(),
        boundary.binding_dossier_fields(),
        boundary.source_contract_fields(),
        boundary.compiler_card_fields(),
        boundary.model_card_fields(),
    )
    while stack:
        current, depth, exiting = stack.pop()
        if exiting:
            active.discard(id(current))
            continue
        observed_nodes += 1
        if observed_nodes > REVIEW_NODE_BUDGET:
            return "REVIEW_ENVELOPE_MALFORMED"
        if isinstance(current, (dict, list)):
            if not current:
                return "REVIEW_ENVELOPE_INCOMPLETE"
            if depth >= REVIEW_MAX_DEPTH:
                return "REVIEW_ENVELOPE_MALFORMED"
            identity = id(current)
            if identity in active:
                return "REVIEW_ENVELOPE_MALFORMED"
            active.add(identity)
            stack.append((current, depth, True))
            if isinstance(current, dict):
                if not all(isinstance(key, str) for key in current):
                    return "REVIEW_ENVELOPE_MALFORMED"
                if any(fields <= set(current) for fields in raw_layouts):
                    return "REVIEW_ENVELOPE_MALFORMED"
                nested_values = list(current.values())
            else:
                nested_values = list(current)
            stack.extend((nested, depth + 1, False) for nested in reversed(nested_values))
            continue
        if boundary.contains_blocked_sentinel(current):
            return "REVIEW_ENVELOPE_INCOMPLETE"
        if isinstance(current, str) and boundary.contains_private_path_value(current):
            return "REVIEW_ENVELOPE_MALFORMED"
        if isinstance(current, float):
            return "REVIEW_ENVELOPE_MALFORMED"
        if current is None or isinstance(current, (str, bool, int)):
            continue
        return "REVIEW_ENVELOPE_MALFORMED"
    return None


def _validate_review_envelope_structure(envelope: Any) -> bool:
    root_fields = (
        "schema_version",
        "document_kind",
        "envelope_schema_id",
        "template_only",
        "execution_input_marker",
        "human_acceptance_marker",
        "binding_draft",
        "source_contract_draft",
        "compiler_card_draft",
        "model_card_draft",
    )
    root = _expect_exact_keys(envelope, root_fields, "candidate_envelope")
    if root["schema_version"] != ENVELOPE_VERSION:
        raise _ReviewStructureError(
            "REVIEW_ENVELOPE_MALFORMED", "candidate_envelope", "schema_version"
        )
    if root["execution_input_marker"] != "NOT_AN_EXECUTION_INPUT":
        raise _ReviewStructureError(
            "REVIEW_ENVELOPE_MALFORMED", "candidate_envelope", "execution_input_marker"
        )
    if root["human_acceptance_marker"] != "NO_HUMAN_ACCEPTANCE_RECORDED":
        raise _ReviewStructureError(
            "REVIEW_ENVELOPE_MALFORMED", "candidate_envelope", "human_acceptance_marker"
        )
    template_only = root["template_only"]
    if template_only is True:
        if (
            root["document_kind"] != "TEMPLATE"
            or root["envelope_schema_id"] != TEMPLATE_ENVELOPE_ID
        ):
            raise _ReviewStructureError("REVIEW_ENVELOPE_MALFORMED", "candidate_envelope")
    elif template_only is False:
        if (
            root["document_kind"] != "CANDIDATE"
            or root["envelope_schema_id"] != CANDIDATE_ENVELOPE_ID
        ):
            raise _ReviewStructureError("REVIEW_ENVELOPE_MALFORMED", "candidate_envelope")
    else:
        raise _ReviewStructureError(
            "REVIEW_ENVELOPE_MALFORMED", "candidate_envelope", "template_only"
        )

    for section_name, version, target, proposed_key, field_names in _draft_specs():
        draft_fields = (
            "schema_id",
            "schema_version",
            "draft_only",
            "target_schema",
            proposed_key,
        )
        draft = _expect_exact_keys(root[section_name], draft_fields, section_name)
        if (
            draft["schema_id"] != f"https://voice2task.local/schemas/{version}"
            or draft["schema_version"] != version
            or draft["draft_only"] is not True
            or draft["target_schema"] != target
        ):
            raise _ReviewStructureError("REVIEW_ENVELOPE_MALFORMED", section_name)
        proposed = _expect_exact_keys(
            draft[proposed_key], field_names, section_name
        )
        for name in field_names:
            record = _expect_exact_keys(
                proposed[name],
                ("proposed_value", "evidence", "review"),
                section_name,
                name,
            )
            if template_only:
                if any(record[key] != NOT_SUPPLIED for key in record):
                    raise _ReviewStructureError(
                        "REVIEW_ENVELOPE_MALFORMED", section_name, name
                    )
            else:
                for value in record.values():
                    issue = _candidate_value_issue(value)
                    if issue is not None:
                        raise _ReviewStructureError(issue, section_name, name)
    return bool(template_only)


def _boundary_diagnostic(code: str) -> dict[str, str]:
    section = {
        "BINDING_INCOMPLETE_OR_PLACEHOLDER": "binding_draft",
        "ACQUISITION_SOURCE_UNAVAILABLE_OR_UNVERIFIABLE": "source_contract_draft",
        "POWER_ASSUMPTION_UNSUPPORTED": "candidate_envelope",
    }.get(code, "candidate_envelope")
    return _diagnostic(code, section)


def lint_review_envelope(envelope: Any) -> dict[str, Any]:
    supplied_count = 0
    binding_packet: dict[str, Any] | None = None
    source_contract: dict[str, Any] | None = None
    compiler_card: dict[str, Any] | None = None
    model_card: dict[str, Any] | None = None
    try:
        supplied_count = _supplied_binding_count(envelope)
        template_only = _validate_review_envelope_structure(envelope)
        if template_only:
            return _incomplete_lint_truth(
                0,
                _diagnostic("REVIEW_ENVELOPE_INCOMPLETE", "binding_draft"),
            )

        candidate = envelope
        binding_records = candidate["binding_draft"]["proposed_bindings"]
        binding_evidence_fields = boundary.binding_dossier_fields() - {
            "name",
            "status",
            "value",
            "review_verdict",
        }
        binding_packet = {
            "schema_version": "clean-evaluation-bindings-v1",
            "bindings": {},
        }
        for name in boundary.EXECUTION_BINDING_FIELDS:
            record = binding_records[name]
            evidence = _expect_exact_keys(
                record["evidence"],
                tuple(sorted(binding_evidence_fields)),
                "binding_draft",
                name,
            )
            review = _expect_exact_keys(
                record["review"],
                ("binding_status", "review_verdict"),
                "binding_draft",
                name,
            )
            binding_packet["bindings"][name] = {
                "name": name,
                "status": review["binding_status"],
                "value": record["proposed_value"],
                **evidence,
                "review_verdict": review["review_verdict"],
            }
        source_contract = {
            name: candidate["source_contract_draft"]["proposed_fields"][name][
                "proposed_value"
            ]
            for name in boundary.source_contract_fields()
        }
        compiler_card = {
            name: candidate["compiler_card_draft"]["proposed_fields"][name][
                "proposed_value"
            ]
            for name in boundary.compiler_card_fields()
        }
        model_card = {
            name: candidate["model_card_draft"]["proposed_fields"][name]["proposed_value"]
            for name in boundary.model_card_fields()
        }
        boundary.validate_pre_freeze_inputs(
            binding_packet,
            source_contract,
            compiler_card,
            model_card,
        )
        return _complete_lint_truth()
    except _ReviewStructureError as exc:
        return _incomplete_lint_truth(
            supplied_count,
            _diagnostic(exc.code, exc.section, exc.field),
        )
    except boundary.BoundaryViolation as exc:
        return _incomplete_lint_truth(
            supplied_count,
            _boundary_diagnostic(exc.code),
        )
    except Exception:
        return _incomplete_lint_truth(
            supplied_count,
            _diagnostic(REVIEW_LINT_UNEXPECTED_FAILURE, "candidate_envelope"),
        )
    finally:
        binding_packet = None
        source_contract = None
        compiler_card = None
        model_card = None


def _safe_review_input_name(name: str) -> bool:
    if type(name) is not str or not name or "\\" in name or name.startswith("~"):
        return False
    path = PurePosixPath(name)
    components = name.split("/")
    return bool(
        not path.is_absolute()
        and all(component not in {"", ".", ".."} for component in components)
        and "\x00" not in name
    )


def lint_review_envelope_file(
    review_input_root: Path,
    review_pack_name: str,
) -> dict[str, Any]:
    if not _safe_review_input_name(review_pack_name):
        return review_command_failure_truth()
    try:
        payload = boundary.verified_read_private_file(
            review_input_root,
            review_pack_name,
            max_bytes=REVIEW_INPUT_MAX_BYTES,
        )
        envelope = boundary.strict_json_loads(payload)
        return lint_review_envelope(envelope)
    except Exception:
        return review_command_failure_truth()


def _responsibility_row(
    scope: str,
    name: str,
    envelope_section: str,
) -> dict[str, str]:
    return {
        "row_id": f"{scope}:{name}",
        "scope": scope,
        "name": name,
        "envelope_section": envelope_section,
        "provider": NOT_SUPPLIED,
        "independent_reviewer": NOT_SUPPLIED,
        "required_evidence": NOT_SUPPLIED,
        "applicability": NOT_SUPPLIED,
        "zero_access_attestation": NOT_SUPPLIED,
        "human_acceptance_gate": "NOT_RECORDED",
        "preapproval_status": "NOT_RECORDED",
    }


def build_responsibility_matrix() -> dict[str, Any]:
    rows = [
        _responsibility_row("component", name, section)
        for name, section in (
            ("binding_packet", "binding_draft"),
            ("source_contract", "source_contract_draft"),
            ("compiler_card", "compiler_card_draft"),
            ("model_card", "model_card_draft"),
        )
    ]
    rows.extend(
        _responsibility_row("binding", name, "binding_draft")
        for name in boundary.EXECUTION_BINDING_FIELDS
    )
    return {
        "schema_version": "clean-evaluation-review-responsibility-matrix-v1",
        "row_count": len(rows),
        "rows": rows,
    }


def build_review_checklist() -> str:
    matrix = build_responsibility_matrix()
    lines = [
        "# Clean Evaluation Acquisition and Binding Review Checklist",
        "",
        "This is preparation-only operator guidance. It is not an execution input and records no human acceptance.",
        "",
        "- Independence: source provider must differ from source reviewer.",
        "- Independence: lockbox validator must differ from lockbox reviewer.",
        "- Ancestry exclusions: public train/dev/test, remediation, challenge, prediction, and lockbox-v1 row content.",
        "- Every proposed binding requires derivation evidence, applicability, and a zero-access attestation.",
        "- Compiler and model power assumptions require independent statistical review.",
        "- Human acceptance is a separate future gate and is not recorded by this pack.",
        f"- The operator alone may manually copy a completed envelope to `{REVIEW_INPUT_ROOT}`.",
        "- The tool never creates or modifies this root.",
        "",
        "## Responsibility matrix (33 rows; no preapproval)",
        "",
        "| row_id | scope | name | envelope section | provider | independent reviewer | "
        "required evidence | applicability | zero-access attestation | human acceptance gate | "
        "preapproval status |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in matrix["rows"]:
        lines.append(
            "| {row_id} | {scope} | {name} | {envelope_section} | {provider} | "
            "{independent_reviewer} | {required_evidence} | {applicability} | "
            "{zero_access_attestation} | {human_acceptance_gate} | "
            "{preapproval_status} |".format(**row)
        )
    return "\n".join(lines) + "\n"


def build_review_pack_artifacts() -> dict[str, bytes]:
    return {
        "binding-catalog.json": render_json(build_binding_catalog()),
        "review-pack.schema.json": render_json(build_review_pack_schema()),
        "review-pack.template.json": render_json(build_review_pack_template()),
        "review-checklist.md": build_review_checklist().encode("utf-8"),
    }


def build_review_pack_summary() -> dict[str, Any]:
    return {
        "schema_version": "clean-evaluation-review-pack-summary-v1",
        **lint_review_envelope(build_review_pack_template()),
    }


def build_review_pack_summary_markdown() -> str:
    summary = build_review_pack_summary()
    return f"""# Clean Evaluation Acquisition and Binding Review Pack

- Evidence status: `{summary['evidence_status']}`
- Phase status: `{summary['phase_status']}`
- Decision: `{summary['decision']}`
- Candidate pack: `{summary['candidate_pack_status']}`
- Supplied bindings: `{summary['supplied_binding_count']}/{summary['binding_inventory_count']}`
- Authoritatively bound bindings: `{summary['authoritatively_bound_binding_count']}`
- Acquisition source: `{summary['acquisition_source_status']}`
- Human acceptance: `{summary['human_acceptance_status']}`
- Protocol freeze: `{summary['protocol_freeze_status']}`
- Clean population: `{summary['clean_population_status']}`
- Freeze authorized: `{str(summary['freeze_authorized']).lower()}`
- Next phase eligible: `{str(summary['next_phase_eligible']).lower()}`
- Execution readiness: `{str(summary['execution_readiness']).lower()}`
"""


def build_review_pack_bundle() -> dict[str, bytes]:
    bundle = dict(build_review_pack_artifacts())
    bundle["summary.json"] = render_json(build_review_pack_summary())
    bundle["summary.md"] = build_review_pack_summary_markdown().encode("utf-8")
    artifacts = [
        {
            "name": name,
            "sha256": hashlib.sha256(payload).hexdigest(),
            "bytes": len(payload),
        }
        for name, payload in bundle.items()
    ]
    manifest = {
        "schema_version": "clean-evaluation-review-pack-manifest-v1",
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
    }
    bundle["manifest.json"] = render_json(manifest)
    return bundle


def write_review_pack_bundle(trusted_root: Path) -> dict[str, Path]:
    return boundary.write_review_public_bundle(
        build_review_pack_bundle(),
        trusted_root,
    )
