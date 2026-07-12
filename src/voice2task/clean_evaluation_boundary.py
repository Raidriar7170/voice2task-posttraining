from __future__ import annotations

import ctypes
import errno
import hashlib
import json
import os
import re
import secrets
import stat
import sys
from collections.abc import Mapping
from decimal import Decimal, InvalidOperation
from pathlib import Path, PurePosixPath
from typing import Any, NoReturn, cast

CANONICAL_PRIVATE_ROOT = Path("data/local-private/clean-compiler-model-evaluation-boundary-v1")
PUBLIC_REPORT_ROOT = Path("reports/public-sample/clean-compiler-model-evaluation-boundary-v1")
PUBLIC_ARTIFACT_FILENAMES = (
    "summary.json",
    "summary.md",
    "protocol-manifest.json",
    "population-seal-attestation.json",
    "lineage-attestation.json",
)
REVIEW_PUBLIC_BUNDLE_ROOT = Path(
    "reports/public-sample/clean-evaluation-acquisition-and-binding-review-pack-v1"
)
REVIEW_PUBLIC_ARTIFACT_FILENAMES = (
    "binding-catalog.json",
    "review-pack.schema.json",
    "review-pack.template.json",
    "review-checklist.md",
    "summary.json",
    "summary.md",
    "manifest.json",
)
REVIEW_PUBLIC_RECOVERY_PREFIX = ".review-pack-recovery-"
_PUBLIC_COMPONENT_PATTERN = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")
_PUBLIC_RESERVED_PREFIX_PATTERN = re.compile(
    r"\A(?:tmp|temp|backup|staging)(?:[._-]|\Z)", re.IGNORECASE
)
PROTECTED_INPUT_BASELINE = {
    "prior_design_evidence_status": "DESIGN_ONLY",
    "prior_design_binding_inventory_count": 29,
    "prior_design_report_sha256": {
        "json": "d547922a423a3f26413bae1a732586c6afca57199a7491ac9b22051689e45d4e",
        "markdown": "5f9b05bc8e7f242afcbed50078538818e9e10a26cb7d4f10922a2463cbf84c7f",
    },
    "archived_design_sha256": "3c1b70656203f5bee556c398c130731bba7c932cfbe6dd9644acda0530314c2e",
    "main_design_spec_sha256": "11c2201d6bf82fe0decce9ff7d32ae0ad0fbb6d73dac6daada6cc990b3bcaeff",
    "public_dataset_sha256": {
        "seed": "8fe5e75e9e0891b6824d7c142cbe15547267377420f8b3240414436265d15801",
        "sft": "4b677420f766555c04199f15f69f41f3b3ad36ad3cd5c33d2b40b0e3f8573587",
        "dpo": "b673dff3c1f598a250c8ed463be320fd2126b61a07e7672b83fbca4bae266ea8",
        "manifest": "f866c173795e97953b1dec85611b405867d0a29497910282f99d399f109cda95",
    },
    "lockbox_aggregate_sha256": {
        "manifest": "72471bac59749f3bc9d21d73db47dafe1f160b978f5ac3971434e13527ddedde",
        "run_card": "39e59cd6e16baa7adadb6b3c474e7fce8bfe8223e5980a1288a1c50432acec66",
        "base_metrics": "400fa753e6e8bde611af4e4f9623155ceff6664454bfea0f57748043243cd02f",
        "final_sft_metrics": "aaecc8dcdad90e70c0f8a7c59a21d2e65d8d42bae3e304e4dce9b049390bc829",
        "comparison": "48fae0e85e016c1872477881939716076d96998d0c63f83adf1e9be42d9ed544",
    },
    "canonical_registry_preexisting": False,
    "canonical_membership_preexisting": False,
    "canonical_seal_preexisting": False,
    "forbidden_source_classes": [
        "PUBLIC_SAMPLE",
        "REMEDIATION",
        "CHALLENGE",
        "PREDICTION",
        "LOCKBOX_V1_ROWS",
        "MODEL_ADAPTER_CHECKPOINT_CACHE_RUN_LOG",
    ],
}
PROTECTED_LOCKBOX_MANIFEST_SHA256 = (
    "72471bac59749f3bc9d21d73db47dafe1f160b978f5ac3971434e13527ddedde"
)

EXECUTION_BINDING_FIELDS = (
    "acquisition_source",
    "acquisition_frame_version",
    "semantic_family_key",
    "partition_algorithm",
    "partition_seed",
    "strata_definition",
    "target_total_family_count",
    "target_partition_allocation",
    "minimum_families_per_partition",
    "compiler_control",
    "compiler_intervention",
    "model_control",
    "model_training_intervention",
    "paired_model_seed_list",
    "compiler_effect_scale",
    "model_effect_scale",
    "compiler_mde_or_sensitivity_target",
    "model_mde_or_sensitivity_target",
    "compiler_target_power_or_beta",
    "model_target_power_or_beta",
    "alpha",
    "compiler_family_variance_or_icc_assumption",
    "model_family_variance_or_icc_assumption",
    "paired_seed_correlation_assumption",
    "seed_failure_or_attrition_assumption",
    "compiler_interval_and_multiplicity_method",
    "model_interval_and_multiplicity_method",
    "guardrail_margins",
    "stop_rules",
)

PARTITION_IDS = ("compiler_system_evaluation", "model_learning_evaluation")
BLOCKED_SENTINELS = frozenset(
    {
        "UNBOUND_BY_DESIGN",
        "UNBOUND",
        "TBD",
        "UNKNOWN",
        "BLOCKED",
        "NOT_AVAILABLE",
        "NOT_SUPPLIED",
    }
)
DENIED_PATH_PREFIXES = (
    "data/public-samples",
    "data/lockbox",
    "reports/public-sample",
    "reports/lockbox-v1",
    "raw/private-predictions",
    "private-corpora",
    ".cache",
    "adapters",
    "checkpoints",
    "runs",
    "run",
    "logs",
    "secrets",
    ".env",
    ".ssh",
)
FRAME_FIELDS = frozenset(
    {
        "family_candidate_id",
        "source_batch_id",
        "source_family_key",
        "stratum",
        "eligibility",
        "provenance_class",
        "ancestry_attestation_sha256",
        "unit_hash",
    }
)
FORBIDDEN_FRAME_FIELDS = frozenset(
    {
        "input",
        "input_text",
        "text",
        "audio",
        "transcript",
        "annotation",
        "gold",
        "target_contract",
        "prediction",
        "metric",
        "outcome",
        "notes",
        "path",
        "private_path",
    }
)
_HASH_RE = re.compile(r"^[0-9a-f]{64}$")
_OPAQUE_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
_GENERATION_RE = re.compile(r"^[A-Za-z0-9._-]{1,96}$")
_BINDING_PACKET_FIELDS = frozenset({"schema_version", "bindings"})
_BINDING_FIELDS = frozenset(
    {
        "name",
        "status",
        "value",
        "value_type",
        "unit",
        "authority_label",
        "authority_sha256",
        "derivation_method",
        "derivation_input_sha256",
        "applicability",
        "access_attestation",
        "review_verdict",
    }
)
_ACCESS_ATTESTATION_FIELDS = frozenset(
    {"clean_row_access", "gold_access", "outcome_access", "lockbox_row_access"}
)
_SOURCE_CONTRACT_FIELDS = frozenset(
    {
        "schema_version",
        "authority_label",
        "authority_sha256",
        "reviewer_label",
        "review_sha256",
        "expected_frame_sha256",
        "ancestry_attestation_sha256",
        "permitted_frame_schema",
        "allowed_strata",
        "allowed_provenance_classes",
        "max_frame_bytes",
        "max_frame_records",
        "natural_asr_claim",
        "public_or_lockbox_ancestry_excluded",
        "lockbox_attestation_policy",
    }
)
_LOCKBOX_POLICY_FIELDS = frozenset(
    {
        "public_lockbox_manifest_sha256",
        "validator_implementation_sha256",
        "validator_version",
        "validator_authority_label",
        "validator_approval_sha256",
        "reviewer_authority_label",
        "reviewer_approval_sha256",
    }
)
_COMPILER_CARD_FIELDS = frozenset(
    {
        "schema_version",
        "estimand",
        "planning_mode",
        "effect_target",
        "available_capacity",
        "paired_record_contrasts",
        "family_clustering",
        "paired_discordance_sensitivity_grid",
        "clean_outcome_used",
        "authority_sha256",
    }
)
_MODEL_CARD_FIELDS = frozenset(
    {
        "schema_version",
        "estimand",
        "planning_mode",
        "effect_target",
        "available_capacity",
        "family_by_paired_seed_hierarchy",
        "paired_seed_correlation_grid",
        "all_assigned_seed_itt_failure_coding",
        "seed_failure_sensitivity_grid",
        "seed_superpopulation_limitation",
        "clean_outcome_used",
        "authority_sha256",
    }
)
_LOCKBOX_ATTESTATION_FIELDS = frozenset(
    {
        "schema_version",
        "attestation_type",
        "protocol_sha256",
        "expected_source_frame_sha256",
        "actual_source_frame_sha256",
        "family_registry_root_sha256",
        "public_lockbox_manifest_sha256",
        "validator_implementation_sha256",
        "validator_version",
        "validator_authority_label",
        "validator_approval_sha256",
        "reviewer_authority_label",
        "reviewer_approval_sha256",
        "comparison_category_counts",
        "total_overlap_count",
        "row_level_output_count",
        "attestation_sha256",
    }
)
_COMPARISON_CATEGORIES = frozenset(
    {"public_train", "public_dev", "public_test", "remediation", "challenge", "prediction", "lockbox_v1"}
)
_PRIVATE_SEAL_FIELDS = frozenset(
    {
        "schema_version",
        "protocol_sha256",
        "source_frame_sha256",
        "family_registry_root_sha256",
        "membership_root_sha256",
        "family_count",
        "partition_counts",
        "overlap_count",
        "artifact_sha256",
        "artifact_references",
        "partition_states",
        "maximum_state",
    }
)
_REGISTRY_ENTRY_FIELDS = frozenset(
    {
        "family_id",
        "source_unit_hash",
        "semantic_family_key",
        "stratum",
        "provenance_class",
        "ancestry_attestation_sha256",
        "registry_entry_hash",
    }
)


def binding_packet_fields() -> frozenset[str]:
    return _BINDING_PACKET_FIELDS


def binding_dossier_fields() -> frozenset[str]:
    return _BINDING_FIELDS


def source_contract_fields() -> frozenset[str]:
    return _SOURCE_CONTRACT_FIELDS


def compiler_card_fields() -> frozenset[str]:
    return _COMPILER_CARD_FIELDS


def model_card_fields() -> frozenset[str]:
    return _MODEL_CARD_FIELDS


def contains_blocked_sentinel(value: Any) -> bool:
    return _contains_blocked_sentinel(value)


def contains_private_path_value(value: Any) -> bool:
    return _contains_private_path_value(value)


class BoundaryViolation(ValueError):
    """A public-safe fail-closed boundary error identified only by code."""

    def __init__(self, code: str, *, last_verified_state: str = "DESIGN_ONLY") -> None:
        self.code = code
        self.last_verified_state = last_verified_state
        super().__init__(code)


def _fail(code: str) -> NoReturn:
    raise BoundaryViolation(code)


def _reject_float(value: Any) -> None:
    if isinstance(value, float):
        _fail("STRICT_JSON_INVALID")
    if isinstance(value, dict):
        if not all(isinstance(key, str) for key in value):
            _fail("STRICT_JSON_INVALID")
        for nested in value.values():
            _reject_float(nested)
    elif isinstance(value, list):
        for nested in value:
            _reject_float(nested)


def canonical_json_bytes(value: Any) -> bytes:
    _reject_float(value)
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise BoundaryViolation("STRICT_JSON_INVALID") from exc


def _reject_constant(_value: str) -> NoReturn:
    _fail("STRICT_JSON_INVALID")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            _fail("STRICT_JSON_INVALID")
        result[key] = value
    return result


def strict_json_loads(payload: bytes) -> Any:
    if payload.startswith(b"\xef\xbb\xbf"):
        _fail("STRICT_JSON_INVALID")
    try:
        text = payload.decode("utf-8", errors="strict")
        value = json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except BoundaryViolation:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError, ValueError) as exc:
        raise BoundaryViolation("STRICT_JSON_INVALID") from exc
    _reject_float(value)
    return value


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def domain_hash(domain: str, chunks: list[bytes]) -> str:
    digest = hashlib.sha256()
    for chunk in [domain.encode("ascii"), *chunks]:
        digest.update(len(chunk).to_bytes(8, "big"))
        digest.update(chunk)
    return digest.hexdigest()


def _valid_hash(value: Any) -> bool:
    return isinstance(value, str) and _HASH_RE.fullmatch(value) is not None


def _public_label(value: Any) -> bool:
    return (
        isinstance(value, str)
        and 1 <= len(value) <= 160
        and not value.startswith(("/", "~"))
        and "\\" not in value
        and ".." not in value
    )


def _contains_blocked_sentinel(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip().upper() in BLOCKED_SENTINELS or not value.strip()
    if isinstance(value, dict):
        return any(_contains_blocked_sentinel(item) for item in value.values())
    if isinstance(value, list):
        return not value or any(_contains_blocked_sentinel(item) for item in value)
    return False


def _contains_private_path_value(value: Any) -> bool:
    if isinstance(value, str):
        normalized = value.strip()
        windows_absolute = re.match(r"^[A-Za-z]:[\\/]", normalized) is not None
        parts = re.split(r"[\\/]", normalized)
        return (
            normalized.startswith(("/", "~"))
            or windows_absolute
            or ".." in parts
            or normalized == "data/local-private"
            or normalized.startswith("data/local-private/")
        )
    if isinstance(value, dict):
        return any(_contains_private_path_value(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_private_path_value(item) for item in value)
    return False


def _binding_value_type(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return "structured"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, str):
        return "str"
    return "unsupported"


def _validate_allocation(bindings: dict[str, Any]) -> None:
    total = bindings["target_total_family_count"]["value"]
    allocation = bindings["target_partition_allocation"]["value"]
    strata = bindings["strata_definition"]["value"]
    minimum = bindings["minimum_families_per_partition"]["value"]
    if not isinstance(total, int) or isinstance(total, bool) or total <= 0:
        _fail("BINDING_INCOMPLETE_OR_PLACEHOLDER")
    if not isinstance(minimum, int) or isinstance(minimum, bool) or minimum <= 0:
        _fail("BINDING_INCOMPLETE_OR_PLACEHOLDER")
    if not isinstance(strata, list) or not strata or len(set(strata)) != len(strata):
        _fail("BINDING_INCOMPLETE_OR_PLACEHOLDER")
    if not all(isinstance(item, str) and _OPAQUE_ID_RE.fullmatch(item) for item in strata):
        _fail("BINDING_INCOMPLETE_OR_PLACEHOLDER")
    if not isinstance(allocation, dict) or set(allocation) != set(strata):
        _fail("BINDING_INCOMPLETE_OR_PLACEHOLDER")
    partition_totals = {partition: 0 for partition in PARTITION_IDS}
    observed_total = 0
    for stratum in strata:
        row = allocation[stratum]
        if not isinstance(row, dict) or set(row) != set(PARTITION_IDS):
            _fail("BINDING_INCOMPLETE_OR_PLACEHOLDER")
        for partition in PARTITION_IDS:
            count = row[partition]
            if not isinstance(count, int) or isinstance(count, bool) or count < 0:
                _fail("BINDING_INCOMPLETE_OR_PLACEHOLDER")
            observed_total += count
            partition_totals[partition] += count
    if observed_total != total or any(count < minimum for count in partition_totals.values()):
        _fail("BINDING_INCOMPLETE_OR_PLACEHOLDER")


def validate_binding_packet(packet: dict[str, Any]) -> dict[str, int]:
    if set(packet) != _BINDING_PACKET_FIELDS:
        _fail("BINDING_INCOMPLETE_OR_PLACEHOLDER")
    if packet.get("schema_version") != "clean-evaluation-bindings-v1":
        _fail("BINDING_INCOMPLETE_OR_PLACEHOLDER")
    bindings = packet.get("bindings")
    if not isinstance(bindings, dict) or set(bindings) != set(EXECUTION_BINDING_FIELDS):
        _fail("BINDING_INCOMPLETE_OR_PLACEHOLDER")
    for name in EXECUTION_BINDING_FIELDS:
        dossier = bindings[name]
        if not isinstance(dossier, dict) or set(dossier) != _BINDING_FIELDS:
            _fail("BINDING_INCOMPLETE_OR_PLACEHOLDER")
        if dossier["name"] != name or dossier["status"] != "BOUND":
            _fail("BINDING_INCOMPLETE_OR_PLACEHOLDER")
        if _contains_blocked_sentinel(dossier["value"]):
            _fail("BINDING_INCOMPLETE_OR_PLACEHOLDER")
        if _contains_private_path_value(dossier["value"]):
            _fail("BINDING_INCOMPLETE_OR_PLACEHOLDER")
        if dossier["value_type"] != _binding_value_type(dossier["value"]):
            _fail("BINDING_INCOMPLETE_OR_PLACEHOLDER")
        if not isinstance(dossier["unit"], str) or not dossier["unit"]:
            _fail("BINDING_INCOMPLETE_OR_PLACEHOLDER")
        if not _public_label(dossier["authority_label"]) or not _valid_hash(dossier["authority_sha256"]):
            _fail("BINDING_INCOMPLETE_OR_PLACEHOLDER")
        if not isinstance(dossier["derivation_method"], str) or not dossier["derivation_method"]:
            _fail("BINDING_INCOMPLETE_OR_PLACEHOLDER")
        derivation_hashes = dossier["derivation_input_sha256"]
        if not isinstance(derivation_hashes, list) or not derivation_hashes or not all(
            _valid_hash(item) for item in derivation_hashes
        ):
            _fail("BINDING_INCOMPLETE_OR_PLACEHOLDER")
        if not isinstance(dossier["applicability"], str) or not dossier["applicability"].strip():
            _fail("BINDING_INCOMPLETE_OR_PLACEHOLDER")
        access = dossier["access_attestation"]
        if not isinstance(access, dict) or set(access) != _ACCESS_ATTESTATION_FIELDS:
            _fail("BINDING_INCOMPLETE_OR_PLACEHOLDER")
        if any(value is not False for value in access.values()):
            _fail("BINDING_INCOMPLETE_OR_PLACEHOLDER")
        if dossier["review_verdict"] != "APPROVED":
            _fail("BINDING_INCOMPLETE_OR_PLACEHOLDER")

    seeds = bindings["paired_model_seed_list"]["value"]
    model_control = bindings["model_control"]["value"]
    intervention = bindings["model_training_intervention"]["value"]
    if (
        not isinstance(seeds, list)
        or len(seeds) < 3
        or len(seeds) != len(set(seeds))
        or not all(isinstance(seed, int) and not isinstance(seed, bool) for seed in seeds)
        or not isinstance(model_control, dict)
        or not isinstance(intervention, dict)
        or model_control.get("paired_seed_list") != seeds
        or intervention.get("paired_seed_list") != seeds
        or not isinstance(intervention.get("changed_components"), list)
        or len(intervention["changed_components"]) != 1
    ):
        _fail("BINDING_INCOMPLETE_OR_PLACEHOLDER")
    if bindings["partition_algorithm"]["value"] != "sha256-partition-by-stratum-v1":
        _fail("BINDING_INCOMPLETE_OR_PLACEHOLDER")
    _validate_allocation(cast(dict[str, Any], bindings))
    return {"binding_inventory_count": 29, "bound_binding_count": 29, "unbound_binding_count": 0}


def _validate_source_contract(contract: dict[str, Any]) -> None:
    if set(contract) != _SOURCE_CONTRACT_FIELDS:
        _fail("ACQUISITION_SOURCE_UNAVAILABLE_OR_UNVERIFIABLE")
    if contract.get("schema_version") != "clean-source-contract-v1":
        _fail("ACQUISITION_SOURCE_UNAVAILABLE_OR_UNVERIFIABLE")
    if not _public_label(contract.get("authority_label")) or not _public_label(contract.get("reviewer_label")):
        _fail("ACQUISITION_SOURCE_UNAVAILABLE_OR_UNVERIFIABLE")
    if contract["authority_label"] == contract["reviewer_label"]:
        _fail("ACQUISITION_SOURCE_UNAVAILABLE_OR_UNVERIFIABLE")
    for key in (
        "authority_sha256",
        "review_sha256",
        "expected_frame_sha256",
        "ancestry_attestation_sha256",
    ):
        if not _valid_hash(contract.get(key)):
            _fail("ACQUISITION_SOURCE_UNAVAILABLE_OR_UNVERIFIABLE")
    if contract.get("permitted_frame_schema") != "semantic-family-metadata-frame-v1":
        _fail("ACQUISITION_SOURCE_UNAVAILABLE_OR_UNVERIFIABLE")
    for key in ("allowed_strata", "allowed_provenance_classes"):
        values = contract.get(key)
        if not isinstance(values, list) or not values or len(values) != len(set(values)):
            _fail("ACQUISITION_SOURCE_UNAVAILABLE_OR_UNVERIFIABLE")
        if not all(isinstance(item, str) and _OPAQUE_ID_RE.fullmatch(item) for item in values):
            _fail("ACQUISITION_SOURCE_UNAVAILABLE_OR_UNVERIFIABLE")
    max_bytes = contract.get("max_frame_bytes")
    max_records = contract.get("max_frame_records")
    if not isinstance(max_bytes, int) or isinstance(max_bytes, bool) or not 1 <= max_bytes <= 16 * 1024 * 1024:
        _fail("ACQUISITION_SOURCE_UNAVAILABLE_OR_UNVERIFIABLE")
    if not isinstance(max_records, int) or isinstance(max_records, bool) or not 1 <= max_records <= 100_000:
        _fail("ACQUISITION_SOURCE_UNAVAILABLE_OR_UNVERIFIABLE")
    if (
        contract.get("natural_asr_claim") is not False
        or contract.get("public_or_lockbox_ancestry_excluded") is not True
    ):
        _fail("ACQUISITION_SOURCE_UNAVAILABLE_OR_UNVERIFIABLE")
    _validate_lockbox_policy(contract.get("lockbox_attestation_policy"))


def _validate_lockbox_policy(value: Any) -> None:
    if not isinstance(value, dict) or set(value) != _LOCKBOX_POLICY_FIELDS:
        _fail("ACQUISITION_SOURCE_UNAVAILABLE_OR_UNVERIFIABLE")
    if value.get("public_lockbox_manifest_sha256") != PROTECTED_LOCKBOX_MANIFEST_SHA256:
        _fail("ACQUISITION_SOURCE_UNAVAILABLE_OR_UNVERIFIABLE")
    for field in (
        "validator_implementation_sha256",
        "validator_approval_sha256",
        "reviewer_approval_sha256",
    ):
        if not _valid_hash(value.get(field)):
            _fail("ACQUISITION_SOURCE_UNAVAILABLE_OR_UNVERIFIABLE")
    for field in ("validator_version", "validator_authority_label", "reviewer_authority_label"):
        if not _public_label(value.get(field)):
            _fail("ACQUISITION_SOURCE_UNAVAILABLE_OR_UNVERIFIABLE")
    if value["validator_authority_label"] == value["reviewer_authority_label"]:
        _fail("ACQUISITION_SOURCE_UNAVAILABLE_OR_UNVERIFIABLE")


_CANONICAL_DECIMAL_RE = re.compile(r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$")


def _canonical_decimal_or_range(value: Any) -> bool:
    if not isinstance(value, str) or not value:
        return False
    pieces = value.split("..")
    if len(pieces) not in {1, 2} or any(_CANONICAL_DECIMAL_RE.fullmatch(piece) is None for piece in pieces):
        return False
    try:
        decimals = [Decimal(piece) for piece in pieces]
    except InvalidOperation:
        return False
    if any(not item.is_finite() for item in decimals):
        return False
    return len(decimals) == 1 or decimals[0] <= decimals[1]


def _canonical_effect_target(value: Any) -> bool:
    if not isinstance(value, str) or _CANONICAL_DECIMAL_RE.fullmatch(value) is None:
        return False
    try:
        effect = Decimal(value)
    except InvalidOperation:
        return False
    return effect.is_finite() and Decimal("0") < effect <= Decimal("1")


def _grid_within(values: Any, lower: Decimal, upper: Decimal) -> bool:
    if not isinstance(values, list) or not values:
        return False
    for value in values:
        if not _canonical_decimal_or_range(value):
            return False
        endpoints = [Decimal(piece) for piece in cast(str, value).split("..")]
        if any(endpoint < lower or endpoint > upper for endpoint in endpoints):
            return False
    return True


def _mode_is_valid(card: dict[str, Any]) -> bool:
    mode = card.get("planning_mode")
    effect = card.get("effect_target")
    capacity = card.get("available_capacity")
    if mode == "EFFECT_TARGETED":
        return _canonical_effect_target(effect) and capacity == "NOT_APPLICABLE"
    if mode == "CAPACITY_CONSTRAINED":
        return (
            effect == "NOT_APPLICABLE"
            and isinstance(capacity, int)
            and not isinstance(capacity, bool)
            and capacity > 0
        )
    return False


def validate_power_card(card: dict[str, Any], kind: str) -> None:
    fields = _COMPILER_CARD_FIELDS if kind == "compiler" else _MODEL_CARD_FIELDS if kind == "model" else frozenset()
    if (
        not fields
        or set(card) != fields
        or not _mode_is_valid(card)
        or _contains_blocked_sentinel(card)
        or _contains_private_path_value(card)
    ):
        _fail("POWER_ASSUMPTION_UNSUPPORTED")
    if card.get("clean_outcome_used") is not False or not _valid_hash(card.get("authority_sha256")):
        _fail("POWER_ASSUMPTION_UNSUPPORTED")
    if kind == "compiler":
        if (
            card.get("schema_version") != "compiler-power-card-v1"
            or card.get("estimand") != "compiler_system"
            or card.get("paired_record_contrasts") is not True
            or card.get("family_clustering") is not True
            or not _grid_within(
                card.get("paired_discordance_sensitivity_grid"), Decimal("0"), Decimal("1")
            )
        ):
            _fail("POWER_ASSUMPTION_UNSUPPORTED")
    else:
        if (
            card.get("schema_version") != "model-power-card-v1"
            or card.get("estimand") != "model_learning"
            or card.get("family_by_paired_seed_hierarchy") is not True
            or card.get("all_assigned_seed_itt_failure_coding") is not True
            or not isinstance(card.get("paired_seed_correlation_grid"), list)
            or not card["paired_seed_correlation_grid"]
            or not isinstance(card.get("seed_failure_sensitivity_grid"), list)
            or not card["seed_failure_sensitivity_grid"]
            or not isinstance(card.get("seed_superpopulation_limitation"), str)
            or not card["seed_superpopulation_limitation"].strip()
        ):
            _fail("POWER_ASSUMPTION_UNSUPPORTED")
        if not _grid_within(card["paired_seed_correlation_grid"], Decimal("-1"), Decimal("1")):
            _fail("POWER_ASSUMPTION_UNSUPPORTED")
        if not _grid_within(card["seed_failure_sensitivity_grid"], Decimal("0"), Decimal("1")):
            _fail("POWER_ASSUMPTION_UNSUPPORTED")


def validate_pre_freeze_inputs(
    bindings: dict[str, Any],
    source_contract: dict[str, Any],
    compiler_card: dict[str, Any],
    model_card: dict[str, Any],
) -> dict[str, int]:
    binding_facts = validate_binding_packet(bindings)
    _validate_source_contract(source_contract)
    validate_power_card(compiler_card, "compiler")
    validate_power_card(model_card, "model")
    binding_values = {name: bindings["bindings"][name]["value"] for name in EXECUTION_BINDING_FIELDS}
    if binding_values["strata_definition"] != source_contract["allowed_strata"]:
        _fail("BINDING_INCOMPLETE_OR_PLACEHOLDER")
    if binding_values["target_total_family_count"] != source_contract["max_frame_records"]:
        _fail("BINDING_INCOMPLETE_OR_PLACEHOLDER")
    return binding_facts


def freeze_protocol(
    bindings: dict[str, Any],
    source_contract: dict[str, Any],
    compiler_card: dict[str, Any],
    model_card: dict[str, Any],
) -> dict[str, Any]:
    validate_pre_freeze_inputs(bindings, source_contract, compiler_card, model_card)
    protocol = {
        "schema_version": "clean-evaluation-protocol-v1",
        "binding_packet": bindings,
        "source_contract": source_contract,
        "partition_algorithm": "sha256-partition-by-stratum-v1",
        "compiler_card": compiler_card,
        "model_card": model_card,
        "frame_schema": "semantic-family-metadata-frame-v1",
        "lifecycle_version": "clean-evaluation-boundary-lifecycle-v1",
        "row_level_disjointness": {
            "exact": "PENDING_ROW_AUTHORING_GATE",
            "normalized": "PENDING_ROW_AUTHORING_GATE",
            "template": "PENDING_ROW_AUTHORING_GATE",
        },
        "privacy_policy": "AGGREGATE_ROOTS_AND_COUNTS_ONLY",
        "hard_stop": "POPULATION_MATERIALIZED_AND_SEALED",
    }
    protocol_sha256 = _sha256(canonical_json_bytes(protocol))
    return {
        "schema_version": "clean-evaluation-protocol-manifest-v1",
        "lifecycle_state": "PROTOCOL_FROZEN",
        "protocol_sha256": protocol_sha256,
        "protocol": protocol,
    }


def verify_protocol_manifest(manifest: dict[str, Any]) -> None:
    if set(manifest) != {"schema_version", "lifecycle_state", "protocol_sha256", "protocol"}:
        _fail("PROTOCOL_FREEZE_HASH_DRIFT")
    if manifest.get("schema_version") != "clean-evaluation-protocol-manifest-v1":
        _fail("PROTOCOL_FREEZE_HASH_DRIFT")
    if manifest.get("lifecycle_state") != "PROTOCOL_FROZEN":
        _fail("PROTOCOL_FREEZE_HASH_DRIFT")
    if _sha256(canonical_json_bytes(manifest.get("protocol"))) != manifest.get("protocol_sha256"):
        _fail("PROTOCOL_FREEZE_HASH_DRIFT")


def _rename_noreplace(
    source_directory_fd: int,
    source_name: str,
    destination_directory_fd: int,
    destination_name: str,
) -> None:
    libc = ctypes.CDLL(None, use_errno=True)
    source = os.fsencode(source_name)
    destination = os.fsencode(destination_name)
    if sys.platform == "darwin" and hasattr(libc, "renameatx_np"):
        function = libc.renameatx_np
        function.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
        function.restype = ctypes.c_int
        result = function(
            source_directory_fd,
            source,
            destination_directory_fd,
            destination,
            0x00000004,
        )
    elif sys.platform.startswith("linux") and hasattr(libc, "renameat2"):
        function = libc.renameat2
        function.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
        function.restype = ctypes.c_int
        result = function(
            source_directory_fd,
            source,
            destination_directory_fd,
            destination,
            1,
        )
    else:
        raise OSError(errno.ENOTSUP, "atomic no-replace rename is unavailable")
    if result != 0:
        error_number = ctypes.get_errno()
        raise OSError(error_number, os.strerror(error_number))


def _rename_exchange(
    source_directory_fd: int,
    source_name: str,
    destination_directory_fd: int,
    destination_name: str,
) -> None:
    libc = ctypes.CDLL(None, use_errno=True)
    source = os.fsencode(source_name)
    destination = os.fsencode(destination_name)
    if sys.platform == "darwin" and hasattr(libc, "renameatx_np"):
        function = libc.renameatx_np
        function.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
        function.restype = ctypes.c_int
        result = function(
            source_directory_fd,
            source,
            destination_directory_fd,
            destination,
            0x00000002,
        )
    elif sys.platform.startswith("linux") and hasattr(libc, "renameat2"):
        function = libc.renameat2
        function.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
        function.restype = ctypes.c_int
        result = function(
            source_directory_fd,
            source,
            destination_directory_fd,
            destination,
            2,
        )
    else:
        raise OSError(errno.ENOTSUP, "atomic directory exchange is unavailable")
    if result != 0:
        error_number = ctypes.get_errno()
        raise OSError(error_number, os.strerror(error_number))


def _write_all_and_fsync(file_descriptor: int, payload: bytes) -> None:
    view = memoryview(payload)
    while view:
        written = os.write(file_descriptor, view)
        if written <= 0:
            raise OSError(errno.EIO, "short write")
        view = view[written:]
    os.fsync(file_descriptor)


def _safe_unlink_owned(directory_fd: int, name: str, expected: os.stat_result) -> None:
    try:
        observed = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
    except FileNotFoundError:
        return
    if _same_identity(expected, observed) and stat.S_ISREG(observed.st_mode):
        os.unlink(name, dir_fd=directory_fd)


def persist_protocol_manifest(private_root: Path, manifest: dict[str, Any]) -> str:
    verify_protocol_manifest(manifest)
    protocol_sha256 = manifest.get("protocol_sha256")
    if not _valid_hash(protocol_sha256):
        _fail("PROTOCOL_FREEZE_HASH_DRIFT")
    payload = canonical_json_bytes(manifest) + b"\n"
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    directory = getattr(os, "O_DIRECTORY", 0)
    root_fd = protocols_fd = temporary_fd = -1
    temporary_name = f".tmp-protocol-{secrets.token_hex(16)}"
    temporary_identity: os.stat_result | None = None
    final_name = f"{protocol_sha256}.json"
    try:
        root_fd = os.open(private_root, os.O_RDONLY | directory | nofollow)
        try:
            os.mkdir("protocols", 0o700, dir_fd=root_fd)
        except FileExistsError:
            pass
        protocols_fd = os.open("protocols", os.O_RDONLY | directory | nofollow, dir_fd=root_fd)
        os.fsync(root_fd)
        try:
            existing_fd = os.open(final_name, os.O_RDONLY | nofollow, dir_fd=protocols_fd)
        except FileNotFoundError:
            existing_fd = -1
        if existing_fd >= 0:
            try:
                identity = os.fstat(existing_fd)
                if not stat.S_ISREG(identity.st_mode) or identity.st_nlink != 1 or identity.st_size != len(payload):
                    _fail("PROTOCOL_FREEZE_HASH_DRIFT")
                if os.read(existing_fd, len(payload) + 1) != payload:
                    _fail("PROTOCOL_FREEZE_HASH_DRIFT")
                return cast(str, protocol_sha256)
            finally:
                os.close(existing_fd)
        temporary_fd = os.open(
            temporary_name,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | nofollow,
            0o600,
            dir_fd=protocols_fd,
        )
        try:
            _write_all_and_fsync(temporary_fd, payload)
        finally:
            temporary_identity = os.fstat(temporary_fd)
            os.close(temporary_fd)
            temporary_fd = -1
        try:
            _rename_noreplace(protocols_fd, temporary_name, protocols_fd, final_name)
        except OSError as exc:
            if exc.errno != errno.EEXIST:
                raise
            existing_fd = os.open(final_name, os.O_RDONLY | nofollow, dir_fd=protocols_fd)
            try:
                identity = os.fstat(existing_fd)
                if not stat.S_ISREG(identity.st_mode) or identity.st_nlink != 1 or identity.st_size != len(payload):
                    _fail("PROTOCOL_FREEZE_HASH_DRIFT")
                if os.read(existing_fd, len(payload) + 1) != payload:
                    _fail("PROTOCOL_FREEZE_HASH_DRIFT")
            finally:
                os.close(existing_fd)
        os.fsync(protocols_fd)
        return cast(str, protocol_sha256)
    except BoundaryViolation:
        raise
    except OSError as exc:
        raise BoundaryViolation("PROTOCOL_FREEZE_HASH_DRIFT") from exc
    finally:
        if temporary_fd >= 0:
            os.close(temporary_fd)
        if protocols_fd >= 0 and temporary_identity is not None:
            try:
                _safe_unlink_owned(protocols_fd, temporary_name, temporary_identity)
            except OSError:
                pass
        if protocols_fd >= 0:
            os.close(protocols_fd)
        if root_fd >= 0:
            os.close(root_fd)


def _validate_private_relative_path(relative_path: str) -> tuple[str, ...]:
    raw = str(relative_path)
    if not raw or "\\" in raw:
        _fail("SOURCE_PATH_UNSAFE_OR_DENIED")
    path = PurePosixPath(raw)
    if path.is_absolute() or raw.startswith("~") or ".." in path.parts:
        _fail("SOURCE_PATH_UNSAFE_OR_DENIED")
    normalized = path.as_posix()
    if normalized in {"", "."}:
        _fail("SOURCE_PATH_UNSAFE_OR_DENIED")
    for denied in DENIED_PATH_PREFIXES:
        if normalized == denied or normalized.startswith(f"{denied}/"):
            _fail("SOURCE_PATH_UNSAFE_OR_DENIED")
    if any(part in {"", "."} for part in path.parts):
        _fail("SOURCE_PATH_UNSAFE_OR_DENIED")
    return path.parts


def _same_identity(left: os.stat_result, right: os.stat_result) -> bool:
    return (
        left.st_dev,
        left.st_ino,
        left.st_mode,
        left.st_nlink,
        left.st_size,
        left.st_mtime_ns,
        left.st_ctime_ns,
    ) == (
        right.st_dev,
        right.st_ino,
        right.st_mode,
        right.st_nlink,
        right.st_size,
        right.st_mtime_ns,
        right.st_ctime_ns,
    )


def _same_inode(left: os.stat_result, right: os.stat_result) -> bool:
    return (left.st_dev, left.st_ino, left.st_mode) == (right.st_dev, right.st_ino, right.st_mode)


def verified_read_private_file(private_root: Path, relative_path: str, *, max_bytes: int) -> bytes:
    parts = _validate_private_relative_path(relative_path)
    if not isinstance(max_bytes, int) or isinstance(max_bytes, bool) or max_bytes <= 0:
        _fail("SOURCE_LIMIT_EXCEEDED")
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    nonblock = getattr(os, "O_NONBLOCK", 0)
    directory = getattr(os, "O_DIRECTORY", 0)
    if not nofollow or not nonblock:
        _fail("SOURCE_PATH_UNSAFE_OR_DENIED")
    descriptors: list[int] = []
    directory_links: list[tuple[int, str, os.stat_result]] = []
    try:
        root_fd = os.open(private_root, os.O_RDONLY | directory | nofollow)
        descriptors.append(root_fd)
        root_stat = os.fstat(root_fd)
        if not stat.S_ISDIR(root_stat.st_mode):
            _fail("SOURCE_PATH_UNSAFE_OR_DENIED")
        parent_fd = root_fd
        for component in parts[:-1]:
            child_fd = os.open(component, os.O_RDONLY | directory | nofollow, dir_fd=parent_fd)
            descriptors.append(child_fd)
            child_stat = os.fstat(child_fd)
            if not stat.S_ISDIR(child_stat.st_mode):
                _fail("SOURCE_PATH_UNSAFE_OR_DENIED")
            directory_links.append((parent_fd, component, child_stat))
            parent_fd = child_fd
        linked = os.stat(parts[-1], dir_fd=parent_fd, follow_symlinks=False)
        if not stat.S_ISREG(linked.st_mode) or linked.st_nlink != 1:
            _fail("SOURCE_PATH_UNSAFE_OR_DENIED")
        file_fd = os.open(
            parts[-1],
            os.O_RDONLY | nofollow | nonblock,
            dir_fd=parent_fd,
        )
        descriptors.append(file_fd)
        before = os.fstat(file_fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            _fail("SOURCE_PATH_UNSAFE_OR_DENIED")
        if not _same_identity(linked, before):
            _fail("SOURCE_IDENTITY_DRIFT")
        if before.st_size > max_bytes:
            _fail("SOURCE_LIMIT_EXCEEDED")
        snapshot = os.read(file_fd, max_bytes + 1)
        if len(snapshot) > max_bytes or len(snapshot) != before.st_size:
            _fail("SOURCE_LIMIT_EXCEEDED")
        after = os.fstat(file_fd)
        relinked = os.stat(parts[-1], dir_fd=parent_fd, follow_symlinks=False)
        if not (
            _same_identity(linked, before)
            and _same_identity(before, after)
            and _same_identity(after, relinked)
        ):
            _fail("SOURCE_IDENTITY_DRIFT")
        for link_parent_fd, component, expected in directory_links:
            observed = os.stat(component, dir_fd=link_parent_fd, follow_symlinks=False)
            if not _same_identity(expected, observed):
                _fail("SOURCE_IDENTITY_DRIFT")
        root_observed = os.stat(private_root, follow_symlinks=False)
        if not _same_identity(root_stat, root_observed):
            _fail("SOURCE_IDENTITY_DRIFT")
        return snapshot
    except BoundaryViolation:
        raise
    except (FileNotFoundError, NotADirectoryError, PermissionError, OSError) as exc:
        raise BoundaryViolation("SOURCE_PATH_UNSAFE_OR_DENIED") from exc
    finally:
        for fd in reversed(descriptors):
            try:
                os.close(fd)
            except OSError:
                pass


def frame_unit_hash(record: dict[str, Any]) -> str:
    payload = {key: value for key, value in record.items() if key != "unit_hash"}
    return domain_hash("clean-source-frame-unit-v1", [canonical_json_bytes(payload)])


def parse_source_frame(payload: bytes, source_contract: dict[str, Any]) -> list[dict[str, Any]]:
    _validate_source_contract(source_contract)
    if len(payload) > source_contract["max_frame_bytes"]:
        _fail("SOURCE_LIMIT_EXCEEDED")
    if _sha256(payload) != source_contract["expected_frame_sha256"]:
        _fail("SOURCE_FRAME_HASH_DRIFT")
    if (
        not payload
        or not payload.endswith(b"\n")
        or payload.startswith(b"\xef\xbb\xbf")
        or b"\r" in payload
    ):
        _fail("STRICT_JSON_INVALID")
    raw_lines = payload.splitlines()
    if len(raw_lines) > source_contract["max_frame_records"] or not raw_lines:
        _fail("SOURCE_LIMIT_EXCEEDED")
    records: list[dict[str, Any]] = []
    ids: set[str] = set()
    keys: set[str] = set()
    for raw_line in raw_lines:
        value = strict_json_loads(raw_line)
        if not isinstance(value, dict):
            _fail("FAMILY_REGISTRY_INVALID")
        if set(value) & FORBIDDEN_FRAME_FIELDS:
            _fail("EARLY_ROW_GOLD_OR_OUTCOME_ACCESS")
        if set(value) != FRAME_FIELDS:
            _fail("FAMILY_REGISTRY_INVALID")
        record = cast(dict[str, Any], value)
        if canonical_json_bytes(record) != raw_line:
            _fail("STRICT_JSON_INVALID")
        for key in ("family_candidate_id", "source_batch_id", "source_family_key"):
            if not isinstance(record[key], str) or _OPAQUE_ID_RE.fullmatch(record[key]) is None:
                _fail("FAMILY_REGISTRY_INVALID")
        if record["family_candidate_id"] in ids or record["source_family_key"] in keys:
            _fail("FAMILY_REGISTRY_INVALID")
        ids.add(record["family_candidate_id"])
        keys.add(record["source_family_key"])
        if record["stratum"] not in source_contract["allowed_strata"]:
            _fail("FAMILY_REGISTRY_INVALID")
        if record["provenance_class"] not in source_contract["allowed_provenance_classes"]:
            _fail("FAMILY_REGISTRY_INVALID")
        if record["eligibility"] != "ELIGIBLE":
            _fail("FAMILY_REGISTRY_INVALID")
        if record["ancestry_attestation_sha256"] != source_contract["ancestry_attestation_sha256"]:
            _fail("LINEAGE_OR_LOCKBOX_ATTESTATION_FAILED")
        if record["unit_hash"] != frame_unit_hash(record):
            _fail("FAMILY_REGISTRY_INVALID")
        records.append(record)
    return records


def build_family_registry(records: list[dict[str, Any]]) -> dict[str, Any]:
    registry: list[dict[str, Any]] = []
    for source in sorted(records, key=lambda item: cast(str, item["family_candidate_id"])):
        entry = {
            "family_id": source["family_candidate_id"],
            "source_unit_hash": source["unit_hash"],
            "semantic_family_key": source["source_family_key"],
            "stratum": source["stratum"],
            "provenance_class": source["provenance_class"],
            "ancestry_attestation_sha256": source["ancestry_attestation_sha256"],
        }
        entry["registry_entry_hash"] = domain_hash(
            "clean-family-registry-entry-v1", [canonical_json_bytes(entry)]
        )
        registry.append(entry)
    ids = [item["family_id"] for item in registry]
    family_keys = [item["semantic_family_key"] for item in registry]
    if len(ids) != len(set(ids)) or len(family_keys) != len(set(family_keys)):
        _fail("FAMILY_REGISTRY_INVALID")
    root = domain_hash(
        "clean-family-registry-root-v1",
        [canonical_json_bytes(item) for item in registry],
    )
    return {"records": registry, "root_sha256": root, "family_count": len(registry)}


def _partition_score(seed: str, stratum: str, family_id: str) -> str:
    return domain_hash(
        "sha256-partition-by-stratum-v1",
        [seed.encode("utf-8"), stratum.encode("utf-8"), family_id.encode("utf-8")],
    )


def assign_partitions(
    registry: list[dict[str, Any]], allocation: dict[str, dict[str, int]], seed: str
) -> dict[str, Any]:
    if not isinstance(seed, str) or not seed or not isinstance(allocation, dict):
        _fail("PARTITION_NONDETERMINISM_OR_OVERLAP")
    if not all(isinstance(row, dict) and set(row) == set(PARTITION_IDS) for row in allocation.values()):
        _fail("INSUFFICIENT_FAMILY_COUNT_OR_STRATA")
    target = sum(sum(row.values()) for row in allocation.values())
    if len(registry) != target:
        _fail("INSUFFICIENT_FAMILY_COUNT_OR_STRATA")
    by_stratum: dict[str, list[dict[str, Any]]] = {stratum: [] for stratum in allocation}
    for record in registry:
        stratum = record.get("stratum")
        if stratum not in by_stratum:
            _fail("INSUFFICIENT_FAMILY_COUNT_OR_STRATA")
        by_stratum[cast(str, stratum)].append(record)
    memberships: dict[str, list[str]] = {partition: [] for partition in PARTITION_IDS}
    stratum_counts: dict[str, dict[str, int]] = {}
    for stratum in sorted(allocation):
        row = allocation[stratum]
        if any(not isinstance(count, int) or isinstance(count, bool) or count < 0 for count in row.values()):
            _fail("INSUFFICIENT_FAMILY_COUNT_OR_STRATA")
        records = by_stratum[stratum]
        if len(records) != sum(row.values()):
            _fail("INSUFFICIENT_FAMILY_COUNT_OR_STRATA")
        ordered = sorted(
            records,
            key=lambda item: (
                _partition_score(seed, stratum, cast(str, item["family_id"])),
                cast(str, item["family_id"]),
            ),
        )
        split = row[PARTITION_IDS[0]]
        first = [cast(str, item["family_id"]) for item in ordered[:split]]
        second = [cast(str, item["family_id"]) for item in ordered[split:]]
        memberships[PARTITION_IDS[0]].extend(first)
        memberships[PARTITION_IDS[1]].extend(second)
        stratum_counts[stratum] = {PARTITION_IDS[0]: len(first), PARTITION_IDS[1]: len(second)}
    all_members = [member for partition in PARTITION_IDS for member in memberships[partition]]
    overlap = set(memberships[PARTITION_IDS[0]]) & set(memberships[PARTITION_IDS[1]])
    if len(all_members) != len(set(all_members)) or overlap or len(all_members) != len(registry):
        _fail("PARTITION_NONDETERMINISM_OR_OVERLAP")
    for partition in PARTITION_IDS:
        memberships[partition].sort()
    roots = {
        partition: domain_hash(
            f"clean-partition-membership-root-v1:{partition}",
            [member.encode("utf-8") for member in memberships[partition]],
        )
        for partition in PARTITION_IDS
    }
    return {
        "memberships": memberships,
        "membership_root_sha256": roots,
        "partition_counts": {partition: len(memberships[partition]) for partition in PARTITION_IDS},
        "stratum_counts": stratum_counts,
        "overlap_count": len(overlap),
    }


def attestation_hash(attestation: dict[str, Any]) -> str:
    payload = {key: value for key, value in attestation.items() if key != "attestation_sha256"}
    return domain_hash("sealed-aggregate-lockbox-attestation-v1", [canonical_json_bytes(payload)])


def validate_lockbox_attestation(
    attestation: dict[str, Any],
    *,
    protocol_sha256: str,
    frame_sha256: str,
    registry_root_sha256: str,
    frozen_policy: dict[str, Any],
) -> None:
    _validate_lockbox_policy(frozen_policy)
    if set(attestation) != _LOCKBOX_ATTESTATION_FIELDS:
        _fail("LINEAGE_OR_LOCKBOX_ATTESTATION_FAILED")
    expected = {
        "schema_version": "sealed-aggregate-lockbox-attestation-v1",
        "attestation_type": "SEALED_AGGREGATE_ATTESTATION_ONLY",
        "protocol_sha256": protocol_sha256,
        "expected_source_frame_sha256": frame_sha256,
        "actual_source_frame_sha256": frame_sha256,
        "family_registry_root_sha256": registry_root_sha256,
    }
    if any(attestation.get(key) != value for key, value in expected.items()):
        _fail("LINEAGE_OR_LOCKBOX_ATTESTATION_FAILED")
    for field in _LOCKBOX_POLICY_FIELDS:
        if attestation.get(field) != frozen_policy.get(field):
            _fail("LINEAGE_OR_LOCKBOX_ATTESTATION_FAILED")
    for key in (
        "public_lockbox_manifest_sha256",
        "validator_implementation_sha256",
        "validator_approval_sha256",
        "reviewer_approval_sha256",
    ):
        if not _valid_hash(attestation.get(key)):
            _fail("LINEAGE_OR_LOCKBOX_ATTESTATION_FAILED")
    if not _public_label(attestation.get("validator_version")):
        _fail("LINEAGE_OR_LOCKBOX_ATTESTATION_FAILED")
    if not _public_label(attestation.get("validator_authority_label")) or not _public_label(
        attestation.get("reviewer_authority_label")
    ):
        _fail("LINEAGE_OR_LOCKBOX_ATTESTATION_FAILED")
    if attestation["validator_authority_label"] == attestation["reviewer_authority_label"]:
        _fail("LINEAGE_OR_LOCKBOX_ATTESTATION_FAILED")
    counts = attestation.get("comparison_category_counts")
    if not isinstance(counts, dict) or set(counts) != _COMPARISON_CATEGORIES:
        _fail("LINEAGE_OR_LOCKBOX_ATTESTATION_FAILED")
    if any(not isinstance(value, int) or isinstance(value, bool) or value != 0 for value in counts.values()):
        _fail("LINEAGE_OR_LOCKBOX_ATTESTATION_FAILED")
    total_overlap = attestation.get("total_overlap_count")
    row_outputs = attestation.get("row_level_output_count")
    if (
        not isinstance(total_overlap, int)
        or isinstance(total_overlap, bool)
        or total_overlap != 0
        or not isinstance(row_outputs, int)
        or isinstance(row_outputs, bool)
        or row_outputs != 0
    ):
        _fail("LINEAGE_OR_LOCKBOX_ATTESTATION_FAILED")
    if attestation.get("attestation_sha256") != attestation_hash(attestation):
        _fail("LINEAGE_OR_LOCKBOX_ATTESTATION_FAILED")


def _read_json_input(private_root: Path, relative_path: str, *, max_bytes: int = 1_048_576) -> dict[str, Any]:
    payload = verified_read_private_file(private_root, relative_path, max_bytes=max_bytes)
    value = strict_json_loads(payload)
    if not isinstance(value, dict):
        _fail("STRICT_JSON_INVALID")
    return cast(dict[str, Any], value)


def load_protocol_manifest(private_root: Path, protocol_sha256: str) -> dict[str, Any]:
    if not _valid_hash(protocol_sha256):
        _fail("PROTOCOL_FREEZE_HASH_DRIFT")
    try:
        payload = verified_read_private_file(
            private_root,
            f"protocols/{protocol_sha256}.json",
            max_bytes=4 * 1024 * 1024,
        )
    except BoundaryViolation as exc:
        raise BoundaryViolation("PROTOCOL_FREEZE_HASH_DRIFT") from exc
    value = strict_json_loads(payload)
    if not isinstance(value, dict) or canonical_json_bytes(value) + b"\n" != payload:
        _fail("PROTOCOL_FREEZE_HASH_DRIFT")
    manifest = cast(dict[str, Any], value)
    verify_protocol_manifest(manifest)
    if manifest.get("protocol_sha256") != protocol_sha256:
        _fail("PROTOCOL_FREEZE_HASH_DRIFT")
    return manifest


def validate_named_inputs(
    private_root: Path,
    *,
    bindings: str,
    source_contract: str,
    compiler_card: str,
    model_card: str,
) -> dict[str, Any]:
    binding_payload = _read_json_input(private_root, bindings)
    source_payload = _read_json_input(private_root, source_contract)
    compiler_payload = _read_json_input(private_root, compiler_card)
    model_payload = _read_json_input(private_root, model_card)
    protocol = freeze_protocol(binding_payload, source_payload, compiler_payload, model_payload)
    persist_protocol_manifest(private_root, protocol)
    return protocol


def _private_jsonl(records: list[dict[str, Any]]) -> bytes:
    return b"".join(canonical_json_bytes(record) + b"\n" for record in records)


def _write_generation_file(directory_fd: int, name: str, payload: bytes) -> str:
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | nofollow, 0o600, dir_fd=directory_fd)
    try:
        view = memoryview(payload)
        while view:
            written = os.write(fd, view)
            if written <= 0:
                _fail("ATOMIC_PROMOTION_FAILED")
            view = view[written:]
        os.fsync(fd)
    finally:
        os.close(fd)
    return _sha256(payload)


def _stage_and_promote_generation(
    private_root: Path,
    generation_id: str,
    *,
    protocol: dict[str, Any],
    frame_sha256: str,
    registry: dict[str, Any],
    assignment: dict[str, Any],
) -> str:
    if _GENERATION_RE.fullmatch(generation_id) is None:
        _fail("ATOMIC_PROMOTION_FAILED")
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    directory = getattr(os, "O_DIRECTORY", 0)
    root_fd = parent_fd = lock_fd = staging_fd = -1
    lock_identity: os.stat_result | None = None
    staging_identity: os.stat_result | None = None
    staging_fd_owned = False
    parent_link_identity: os.stat_result | None = None
    lock_name = ".materialize.lock"
    staging_name = f".staging-{generation_id}"
    published = False
    promotion_committed = False
    try:
        root_fd = os.open(private_root, os.O_RDONLY | directory | nofollow)
        try:
            os.mkdir("generations", 0o700, dir_fd=root_fd)
        except FileExistsError:
            pass
        parent_link_identity = os.stat("generations", dir_fd=root_fd, follow_symlinks=False)
        parent_fd = os.open("generations", os.O_RDONLY | directory | nofollow, dir_fd=root_fd)
        parent_identity = os.fstat(parent_fd)
        if (
            not stat.S_ISDIR(parent_link_identity.st_mode)
            or not stat.S_ISDIR(parent_identity.st_mode)
            or not _same_inode(parent_link_identity, parent_identity)
        ):
            _fail("ATOMIC_PROMOTION_FAILED")
        os.fsync(root_fd)
        lock_fd = os.open(
            lock_name,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | nofollow,
            0o600,
            dir_fd=parent_fd,
        )
        lock_identity = os.fstat(lock_fd)
        os.mkdir(staging_name, 0o700, dir_fd=parent_fd)
        staging_identity = os.stat(staging_name, dir_fd=parent_fd, follow_symlinks=False)
        if parent_identity.st_dev != staging_identity.st_dev or not stat.S_ISDIR(staging_identity.st_mode):
            _fail("ATOMIC_PROMOTION_FAILED")
        staging_fd = os.open(staging_name, os.O_RDONLY | directory | nofollow, dir_fd=parent_fd)
        opened_staging_identity = os.fstat(staging_fd)
        if (
            not stat.S_ISDIR(opened_staging_identity.st_mode)
            or not _same_inode(staging_identity, opened_staging_identity)
        ):
            _fail("ATOMIC_PROMOTION_FAILED")
        staging_fd_owned = True
        registry_payload = _private_jsonl(cast(list[dict[str, Any]], registry["records"]))
        compiler_payload = _private_jsonl(
            [{"family_id": family_id} for family_id in assignment["memberships"][PARTITION_IDS[0]]]
        )
        model_payload = _private_jsonl(
            [{"family_id": family_id} for family_id in assignment["memberships"][PARTITION_IDS[1]]]
        )
        artifact_hashes = {
            "family-registry.jsonl": _write_generation_file(staging_fd, "family-registry.jsonl", registry_payload),
            "compiler-system-evaluation.membership.jsonl": _write_generation_file(
                staging_fd, "compiler-system-evaluation.membership.jsonl", compiler_payload
            ),
            "model-learning-evaluation.membership.jsonl": _write_generation_file(
                staging_fd, "model-learning-evaluation.membership.jsonl", model_payload
            ),
        }
        seal = {
            "schema_version": "private-population-seal-v1",
            "protocol_sha256": protocol["protocol_sha256"],
            "source_frame_sha256": frame_sha256,
            "family_registry_root_sha256": registry["root_sha256"],
            "membership_root_sha256": assignment["membership_root_sha256"],
            "family_count": registry["family_count"],
            "partition_counts": assignment["partition_counts"],
            "overlap_count": assignment["overlap_count"],
            "artifact_sha256": artifact_hashes,
            "artifact_references": sorted(artifact_hashes),
            "partition_states": {
                partition: {"one_look_state": "SEALED_NOT_ELIGIBLE", "access_count": 0, "consumed": False}
                for partition in PARTITION_IDS
            },
            "maximum_state": "POPULATION_MATERIALIZED_AND_SEALED",
        }
        seal_payload = canonical_json_bytes(seal) + b"\n"
        seal_sha256 = _write_generation_file(staging_fd, "population-seal.json", seal_payload)
        os.fsync(staging_fd)
        os.fsync(parent_fd)
        before_promotion = os.stat("generations", dir_fd=root_fd, follow_symlinks=False)
        if not _same_inode(parent_link_identity, before_promotion):
            _fail("ATOMIC_PROMOTION_FAILED")
        _rename_noreplace(parent_fd, staging_name, parent_fd, generation_id)
        published = True
        published_identity = os.stat(generation_id, dir_fd=parent_fd, follow_symlinks=False)
        if not _same_inode(staging_identity, published_identity):
            _fail("ATOMIC_PROMOTION_FAILED")
        os.fsync(parent_fd)
        after_promotion = os.stat("generations", dir_fd=root_fd, follow_symlinks=False)
        if not _same_inode(parent_link_identity, after_promotion):
            _fail("ATOMIC_PROMOTION_FAILED")
        promotion_committed = True
        return seal_sha256
    except BoundaryViolation:
        raise
    except OSError as exc:
        raise BoundaryViolation("ATOMIC_PROMOTION_FAILED") from exc
    finally:
        if lock_fd >= 0:
            os.close(lock_fd)
        if (
            parent_fd >= 0
            and not promotion_committed
            and staging_identity is not None
            and staging_fd_owned
            and staging_fd >= 0
        ):
            try:
                cleanup_name = generation_id if published else staging_name
                if not _same_inode(staging_identity, os.fstat(staging_fd)):
                    raise OSError(errno.EPERM, "unowned staging directory")
                for child_name in os.listdir(staging_fd):
                    child = os.stat(child_name, dir_fd=staging_fd, follow_symlinks=False)
                    if not stat.S_ISREG(child.st_mode) or child.st_nlink != 1:
                        raise OSError(errno.EPERM, "unsafe staging child")
                    os.unlink(child_name, dir_fd=staging_fd)
                os.fsync(staging_fd)
                observed = os.stat(cleanup_name, dir_fd=parent_fd, follow_symlinks=False)
                if _same_inode(staging_identity, observed) and stat.S_ISDIR(observed.st_mode):
                    os.rmdir(cleanup_name, dir_fd=parent_fd)
            except (FileNotFoundError, OSError):
                pass
        if staging_fd >= 0:
            os.close(staging_fd)
        if parent_fd >= 0 and lock_identity is not None:
            try:
                _safe_unlink_owned(parent_fd, lock_name, lock_identity)
            except OSError:
                pass
        if parent_fd >= 0:
            os.close(parent_fd)
        if root_fd >= 0:
            os.close(root_fd)


def _false_mutations() -> dict[str, bool]:
    return {
        "boundary_materialization": False,
        "private_family_registry_created": False,
        "private_partition_membership_created": False,
        "public_data_mutation": False,
        "formal_training_data_mutation": False,
        "lockbox_mutation": False,
        "clean_evaluation_row_creation": False,
    }


def _false_access_and_runs() -> dict[str, bool]:
    return {
        "gold_access": False,
        "outcome_access": False,
        "training_run": False,
        "prediction_run": False,
        "a100_execution": False,
        "experiment_execution": False,
        "one_look_access": False,
    }


def _false_claims() -> dict[str, bool]:
    return {
        "clean_independent_evidence_claim": False,
        "row_clean_claim": False,
        "evaluated_benchmark_claim": False,
        "compiler_causal_effect_claim": False,
        "model_learning_causal_effect_claim": False,
        "model_improvement_claim": False,
        "executable_improvement_claim": False,
        "natural_asr_generalization_claim": False,
        "checkpoint_release_claim": False,
        "adapter_release_claim": False,
        "production_readiness_claim": False,
        "safety_readiness_claim": False,
        "live_browser_benchmark_claim": False,
    }


def _unavailable_hashes() -> dict[str, str]:
    return {
        "protocol_sha256": "NOT_AVAILABLE",
        "source_frame_sha256": "NOT_AVAILABLE",
        "family_registry_root_sha256": "NOT_AVAILABLE",
        "compiler_membership_root_sha256": "NOT_AVAILABLE",
        "model_membership_root_sha256": "NOT_AVAILABLE",
        "population_seal_sha256": "NOT_AVAILABLE",
    }


def _not_materialized_partitions() -> dict[str, dict[str, Any]]:
    return {
        partition: {
            "status": "NOT_MATERIALIZED",
            "one_look_state": "NOT_AVAILABLE",
            "access_count": 0,
            "consumed": False,
        }
        for partition in PARTITION_IDS
    }


def s0_blocked_summary() -> dict[str, Any]:
    return {
        "schema_version": "clean-evaluation-boundary-summary-v1",
        "evidence_status": "BLOCKED",
        "decision": "CLEAN_EVALUATION_BOUNDARY_MATERIALIZATION_BLOCKED",
        "blocked_stage": "S0_SOURCE_OR_BINDING",
        "current_readiness_state": "DESIGN_ONLY",
        "maximum_state_this_change": "DESIGN_ONLY",
        "binding_counts": {"total": 29, "bound": 0, "unbound": 29},
        "execution_bindings_status": "INCOMPLETE",
        "protocol_freeze_status": "NOT_FROZEN",
        "clean_population_status": "NOT_MATERIALIZED",
        "population_unit": "NOT_CREATED",
        "clean_evaluation_rows_status": "NOT_CREATED",
        "boundary_integrity_status": "NOT_CREATED",
        "boundary_reuse_allowed": False,
        "new_protocol_version_required": False,
        "new_protocol_and_acquisition_required": False,
        "arm_artifacts_status": "NOT_FROZEN",
        "experiment_preregistration_status": "NOT_EXECUTABLE",
        "execution_readiness": False,
        "compiler_causal_identification_status": "CAUSAL_IDENTIFICATION_BLOCKED",
        "model_causal_identification_status": "CAUSAL_IDENTIFICATION_BLOCKED",
        "blockers": [
            "ACQUISITION_SOURCE_UNAVAILABLE_OR_UNVERIFIABLE",
            "BINDING_INCOMPLETE_OR_PLACEHOLDER",
        ],
        "protected_input_baseline": PROTECTED_INPUT_BASELINE,
        "partitions": _not_materialized_partitions(),
        "hashes": _unavailable_hashes(),
        "artifacts": {
            "canonical_family_registry_created": False,
            "canonical_partition_membership_created": False,
            "canonical_population_seal_created": False,
            "protocol_manifest_frozen": False,
        },
        "mutations": _false_mutations(),
        "access_and_runs": _false_access_and_runs(),
        "claims": _false_claims(),
        "lineage": {
            "source_ancestry": "NOT_EVALUATED_SOURCE_BLOCKED",
            "semantic_family_overlap": "NOT_EVALUATED_SOURCE_BLOCKED",
            "exact_row_disjointness": "PENDING_ROW_AUTHORING_GATE",
            "normalized_row_disjointness": "PENDING_ROW_AUTHORING_GATE",
            "template_row_disjointness": "PENDING_ROW_AUTHORING_GATE",
        },
    }


def _success_summary(
    *,
    protocol_sha256: str,
    frame_sha256: str,
    registry: dict[str, Any],
    assignment: dict[str, Any],
    seal_sha256: str,
) -> dict[str, Any]:
    mutations = _false_mutations()
    mutations.update(
        {
            "boundary_materialization": True,
            "private_family_registry_created": True,
            "private_partition_membership_created": True,
        }
    )
    partitions = {
        partition: {
            "status": "MATERIALIZED_AND_SEALED",
            "one_look_state": "SEALED_NOT_ELIGIBLE",
            "access_count": 0,
            "consumed": False,
            "family_count": assignment["partition_counts"][partition],
        }
        for partition in PARTITION_IDS
    }
    return {
        "schema_version": "clean-evaluation-boundary-summary-v1",
        "evidence_status": "EVALUATION_BOUNDARY_MATERIALIZED",
        "decision": "POPULATION_BOUNDARY_READY_ARM_ARTIFACTS_BLOCKED",
        "blocked_stage": "NOT_APPLICABLE",
        "current_readiness_state": "POPULATION_MATERIALIZED_AND_SEALED",
        "maximum_state_this_change": "POPULATION_MATERIALIZED_AND_SEALED",
        "binding_counts": {"total": 29, "bound": 29, "unbound": 0},
        "execution_bindings_status": "COMPLETE",
        "protocol_freeze_status": "FROZEN",
        "clean_population_status": "MATERIALIZED_AND_SEALED",
        "population_unit": "SEMANTIC_FAMILY_METADATA_ONLY",
        "clean_evaluation_rows_status": "NOT_CREATED",
        "boundary_integrity_status": "INTACT_SEALED",
        "boundary_reuse_allowed": False,
        "arm_artifacts_status": "NOT_FROZEN",
        "experiment_preregistration_status": "NOT_EXECUTABLE",
        "execution_readiness": False,
        "compiler_causal_identification_status": "CAUSAL_IDENTIFICATION_BLOCKED",
        "model_causal_identification_status": "CAUSAL_IDENTIFICATION_BLOCKED",
        "blockers": ["ARM_ARTIFACTS_NOT_FROZEN", "EXPERIMENT_PREREGISTRATION_NOT_EXECUTABLE"],
        "partitions": partitions,
        "hashes": {
            "protocol_sha256": protocol_sha256,
            "source_frame_sha256": frame_sha256,
            "family_registry_root_sha256": registry["root_sha256"],
            "compiler_membership_root_sha256": assignment["membership_root_sha256"][PARTITION_IDS[0]],
            "model_membership_root_sha256": assignment["membership_root_sha256"][PARTITION_IDS[1]],
            "population_seal_sha256": seal_sha256,
        },
        "artifacts": {
            "canonical_family_registry_created": True,
            "canonical_partition_membership_created": True,
            "canonical_population_seal_created": True,
            "protocol_manifest_frozen": True,
        },
        "mutations": mutations,
        "access_and_runs": _false_access_and_runs(),
        "claims": _false_claims(),
        "aggregate_counts": {
            "total_families": registry["family_count"],
            "partition_counts": assignment["partition_counts"],
            "stratum_counts": assignment["stratum_counts"],
            "cross_partition_overlap": 0,
        },
        "lineage": {
            "source_ancestry": "AGGREGATE_ATTESTATION_PASSED",
            "semantic_family_overlap": "PASSED_ZERO_OVERLAP",
            "exact_row_disjointness": "PENDING_ROW_AUTHORING_GATE",
            "normalized_row_disjointness": "PENDING_ROW_AUTHORING_GATE",
            "template_row_disjointness": "PENDING_ROW_AUTHORING_GATE",
        },
    }


def materialize_boundary(
    private_root: Path,
    *,
    protocol_sha256: str,
    source_frame: str,
    lockbox_attestation: str,
    generation_id: str,
) -> dict[str, Any]:
    protocol = load_protocol_manifest(private_root, protocol_sha256)
    try:
        return _materialize_with_verified_protocol(
            private_root,
            protocol=protocol,
            source_frame=source_frame,
            lockbox_attestation=lockbox_attestation,
            generation_id=generation_id,
        )
    except BoundaryViolation as exc:
        exc.last_verified_state = "PROTOCOL_FROZEN"
        raise


def _materialize_with_verified_protocol(
    private_root: Path,
    *,
    protocol: dict[str, Any],
    source_frame: str,
    lockbox_attestation: str,
    generation_id: str,
) -> dict[str, Any]:
    protocol_payload = cast(dict[str, Any], protocol["protocol"])
    source_payload = cast(dict[str, Any], protocol_payload["source_contract"])
    binding_payload = cast(dict[str, Any], protocol_payload["binding_packet"])
    frame = verified_read_private_file(
        private_root,
        source_frame,
        max_bytes=cast(int, source_payload["max_frame_bytes"]),
    )
    frame_sha256 = _sha256(frame)
    records = parse_source_frame(frame, source_payload)
    registry = build_family_registry(records)
    attestation = _read_json_input(private_root, lockbox_attestation)
    validate_lockbox_attestation(
        attestation,
        protocol_sha256=cast(str, protocol["protocol_sha256"]),
        frame_sha256=frame_sha256,
        registry_root_sha256=cast(str, registry["root_sha256"]),
        frozen_policy=cast(dict[str, Any], source_payload["lockbox_attestation_policy"]),
    )
    binding_values = binding_payload["bindings"]
    assignment = assign_partitions(
        cast(list[dict[str, Any]], registry["records"]),
        cast(dict[str, dict[str, int]], binding_values["target_partition_allocation"]["value"]),
        cast(str, binding_values["partition_seed"]["value"]),
    )
    minimum = cast(int, binding_values["minimum_families_per_partition"]["value"])
    if any(count < minimum for count in assignment["partition_counts"].values()):
        _fail("INSUFFICIENT_FAMILY_COUNT_OR_STRATA")
    seal_sha256 = _stage_and_promote_generation(
        private_root,
        generation_id,
        protocol=protocol,
        frame_sha256=frame_sha256,
        registry=registry,
        assignment=assignment,
    )
    return _success_summary(
        protocol_sha256=cast(str, protocol["protocol_sha256"]),
        frame_sha256=frame_sha256,
        registry=registry,
        assignment=assignment,
        seal_sha256=seal_sha256,
    )


def _strict_private_jsonl(payload: bytes, fields: frozenset[str]) -> list[dict[str, Any]]:
    if not payload or not payload.endswith(b"\n") or b"\r" in payload:
        _fail("SEALED_ARTIFACT_DRIFT_OR_MEMBERSHIP_LEAK")
    records: list[dict[str, Any]] = []
    for line in payload.splitlines():
        value = strict_json_loads(line)
        if not isinstance(value, dict) or set(value) != fields or canonical_json_bytes(value) != line:
            _fail("SEALED_ARTIFACT_DRIFT_OR_MEMBERSHIP_LEAK")
        records.append(cast(dict[str, Any], value))
    return records


def _read_sealed_file_at(directory_fd: int, name: str, *, max_bytes: int) -> bytes:
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    file_fd = -1
    try:
        file_fd = os.open(name, os.O_RDONLY | nofollow, dir_fd=directory_fd)
        initial = os.fstat(file_fd)
        linked = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        if (
            not stat.S_ISREG(initial.st_mode)
            or initial.st_nlink != 1
            or initial.st_size > max_bytes
            or not _same_identity(initial, linked)
        ):
            _fail("SEALED_ARTIFACT_DRIFT_OR_MEMBERSHIP_LEAK")
        chunks: list[bytes] = []
        remaining = max_bytes + 1
        while remaining > 0:
            chunk = os.read(file_fd, remaining)
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        payload = b"".join(chunks)
        final = os.fstat(file_fd)
        relinked = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        if (
            len(payload) > max_bytes
            or len(payload) != initial.st_size
            or not _same_identity(initial, final)
            or not _same_identity(initial, relinked)
        ):
            _fail("SEALED_ARTIFACT_DRIFT_OR_MEMBERSHIP_LEAK")
        return payload
    except BoundaryViolation:
        raise
    except OSError as exc:
        raise BoundaryViolation("SEALED_ARTIFACT_DRIFT_OR_MEMBERSHIP_LEAK") from exc
    finally:
        if file_fd >= 0:
            os.close(file_fd)


def _read_exact_sealed_generation(private_root: Path, generation_id: str) -> dict[str, bytes]:
    expected_names = {
        "population-seal.json",
        "family-registry.jsonl",
        "compiler-system-evaluation.membership.jsonl",
        "model-learning-evaluation.membership.jsonl",
    }
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    directory = getattr(os, "O_DIRECTORY", 0)
    root_fd = generations_fd = generation_fd = -1
    try:
        try:
            root_fd = os.open(private_root, os.O_RDONLY | directory | nofollow)
        except FileNotFoundError as exc:
            raise BoundaryViolation("GENERATION_NOT_FOUND") from exc
        try:
            generations_link = os.stat("generations", dir_fd=root_fd, follow_symlinks=False)
            generations_fd = os.open(
                "generations", os.O_RDONLY | directory | nofollow, dir_fd=root_fd
            )
        except FileNotFoundError as exc:
            raise BoundaryViolation("GENERATION_NOT_FOUND") from exc
        generations_identity = os.fstat(generations_fd)
        if (
            not stat.S_ISDIR(generations_link.st_mode)
            or not _same_inode(generations_link, generations_identity)
        ):
            _fail("SEALED_ARTIFACT_DRIFT_OR_MEMBERSHIP_LEAK")
        try:
            generation_link = os.stat(
                generation_id, dir_fd=generations_fd, follow_symlinks=False
            )
            generation_fd = os.open(
                generation_id,
                os.O_RDONLY | directory | nofollow,
                dir_fd=generations_fd,
            )
        except FileNotFoundError as exc:
            raise BoundaryViolation("GENERATION_NOT_FOUND") from exc
        generation_identity = os.fstat(generation_fd)
        if (
            not stat.S_ISDIR(generation_link.st_mode)
            or not _same_inode(generation_link, generation_identity)
            or set(os.listdir(generation_fd)) != expected_names
        ):
            _fail("SEALED_ARTIFACT_DRIFT_OR_MEMBERSHIP_LEAK")
        payloads = {
            name: _read_sealed_file_at(
                generation_fd,
                name,
                max_bytes=1_048_576 if name == "population-seal.json" else 16 * 1024 * 1024,
            )
            for name in sorted(expected_names)
        }
        current_generation_link = os.stat(
            generation_id, dir_fd=generations_fd, follow_symlinks=False
        )
        current_generations_link = os.stat(
            "generations", dir_fd=root_fd, follow_symlinks=False
        )
        if (
            set(os.listdir(generation_fd)) != expected_names
            or not _same_inode(generation_identity, current_generation_link)
            or not _same_inode(generations_identity, current_generations_link)
        ):
            _fail("SEALED_ARTIFACT_DRIFT_OR_MEMBERSHIP_LEAK")
        return payloads
    except BoundaryViolation:
        raise
    except OSError as exc:
        raise BoundaryViolation("SEALED_ARTIFACT_DRIFT_OR_MEMBERSHIP_LEAK") from exc
    finally:
        if generation_fd >= 0:
            os.close(generation_fd)
        if generations_fd >= 0:
            os.close(generations_fd)
        if root_fd >= 0:
            os.close(root_fd)


def verify_generation(
    private_root: Path,
    generation_id: str,
    *,
    expected_population_seal_sha256: str,
) -> dict[str, Any]:
    if _GENERATION_RE.fullmatch(generation_id) is None or not _valid_hash(expected_population_seal_sha256):
        _fail("SEALED_ARTIFACT_DRIFT_OR_MEMBERSHIP_LEAK")
    generation_payloads = _read_exact_sealed_generation(private_root, generation_id)
    seal_payload = generation_payloads["population-seal.json"]
    if _sha256(seal_payload) != expected_population_seal_sha256:
        _fail("SEALED_ARTIFACT_DRIFT_OR_MEMBERSHIP_LEAK")
    seal_value = strict_json_loads(seal_payload)
    if (
        not isinstance(seal_value, dict)
        or set(seal_value) != _PRIVATE_SEAL_FIELDS
        or canonical_json_bytes(seal_value) + b"\n" != seal_payload
    ):
        _fail("SEALED_ARTIFACT_DRIFT_OR_MEMBERSHIP_LEAK")
    seal = cast(dict[str, Any], seal_value)
    protocol_sha256 = seal.get("protocol_sha256")
    if not isinstance(protocol_sha256, str):
        _fail("SEALED_ARTIFACT_DRIFT_OR_MEMBERSHIP_LEAK")
    try:
        protocol_manifest = load_protocol_manifest(private_root, protocol_sha256)
    except BoundaryViolation as exc:
        raise BoundaryViolation("SEALED_ARTIFACT_DRIFT_OR_MEMBERSHIP_LEAK") from exc
    protocol_payload = cast(dict[str, Any], protocol_manifest["protocol"])
    source_contract = cast(dict[str, Any], protocol_payload["source_contract"])
    if seal.get("source_frame_sha256") != source_contract.get("expected_frame_sha256"):
        _fail("SEALED_ARTIFACT_DRIFT_OR_MEMBERSHIP_LEAK")
    references = seal.get("artifact_references")
    hashes = seal.get("artifact_sha256")
    allowed = {
        "family-registry.jsonl",
        "compiler-system-evaluation.membership.jsonl",
        "model-learning-evaluation.membership.jsonl",
    }
    if (
        not isinstance(references, list)
        or not isinstance(hashes, dict)
        or set(references) != allowed
        or set(hashes) != allowed
        or references != sorted(allowed)
        or not all(_valid_hash(value) for value in hashes.values())
    ):
        _fail("SEALED_ARTIFACT_DRIFT_OR_MEMBERSHIP_LEAK")
    artifact_payloads: dict[str, bytes] = {}
    for name in sorted(allowed):
        payload = generation_payloads[name]
        if _sha256(payload) != hashes[name]:
            _fail("SEALED_ARTIFACT_DRIFT_OR_MEMBERSHIP_LEAK")
        artifact_payloads[name] = payload

    registry = _strict_private_jsonl(artifact_payloads["family-registry.jsonl"], _REGISTRY_ENTRY_FIELDS)
    registry.sort(key=lambda item: cast(str, item["family_id"]))
    if len({item["family_id"] for item in registry}) != len(registry):
        _fail("SEALED_ARTIFACT_DRIFT_OR_MEMBERSHIP_LEAK")
    for entry in registry:
        without_hash = {key: value for key, value in entry.items() if key != "registry_entry_hash"}
        if entry["registry_entry_hash"] != domain_hash(
            "clean-family-registry-entry-v1", [canonical_json_bytes(without_hash)]
        ):
            _fail("SEALED_ARTIFACT_DRIFT_OR_MEMBERSHIP_LEAK")
    registry_root = domain_hash(
        "clean-family-registry-root-v1", [canonical_json_bytes(item) for item in registry]
    )
    if registry_root != seal.get("family_registry_root_sha256"):
        _fail("SEALED_ARTIFACT_DRIFT_OR_MEMBERSHIP_LEAK")

    membership_files = {
        PARTITION_IDS[0]: "compiler-system-evaluation.membership.jsonl",
        PARTITION_IDS[1]: "model-learning-evaluation.membership.jsonl",
    }
    memberships: dict[str, list[str]] = {}
    for partition, name in membership_files.items():
        rows = _strict_private_jsonl(artifact_payloads[name], frozenset({"family_id"}))
        members = [cast(str, row["family_id"]) for row in rows]
        if members != sorted(members) or len(members) != len(set(members)):
            _fail("SEALED_ARTIFACT_DRIFT_OR_MEMBERSHIP_LEAK")
        memberships[partition] = members
        expected_root = domain_hash(
            f"clean-partition-membership-root-v1:{partition}",
            [member.encode("utf-8") for member in members],
        )
        if seal.get("membership_root_sha256", {}).get(partition) != expected_root:
            _fail("SEALED_ARTIFACT_DRIFT_OR_MEMBERSHIP_LEAK")
    combined = memberships[PARTITION_IDS[0]] + memberships[PARTITION_IDS[1]]
    overlap = set(memberships[PARTITION_IDS[0]]) & set(memberships[PARTITION_IDS[1]])
    partition_counts = {partition: len(memberships[partition]) for partition in PARTITION_IDS}
    binding_packet = cast(dict[str, Any], protocol_payload["binding_packet"])
    binding_values = cast(dict[str, Any], binding_packet["bindings"])
    target_count = binding_values["target_total_family_count"]["value"]
    minimum_count = binding_values["minimum_families_per_partition"]["value"]
    allocation = cast(
        dict[str, dict[str, int]],
        binding_values["target_partition_allocation"]["value"],
    )
    registry_by_id = {cast(str, item["family_id"]): item for item in registry}
    actual_allocation = {
        stratum: {
            partition: sum(
                1
                for family_id in memberships[partition]
                if registry_by_id[family_id]["stratum"] == stratum
            )
            for partition in PARTITION_IDS
        }
        for stratum in allocation
    }
    seal_family_count = seal.get("family_count")
    seal_overlap_count = seal.get("overlap_count")
    seal_partition_counts = seal.get("partition_counts")
    if (
        len(combined) != len(registry)
        or set(combined) != {cast(str, item["family_id"]) for item in registry}
        or overlap
        or not isinstance(seal_family_count, int)
        or isinstance(seal_family_count, bool)
        or seal_family_count != len(registry)
        or not isinstance(seal_partition_counts, dict)
        or any(
            not isinstance(value, int) or isinstance(value, bool)
            for value in seal_partition_counts.values()
        )
        or seal_partition_counts != partition_counts
        or not isinstance(seal_overlap_count, int)
        or isinstance(seal_overlap_count, bool)
        or seal_overlap_count != 0
        or target_count != len(registry)
        or actual_allocation != allocation
        or any(count < minimum_count for count in partition_counts.values())
    ):
        _fail("SEALED_ARTIFACT_DRIFT_OR_MEMBERSHIP_LEAK")
    states = seal.get("partition_states")
    if not isinstance(states, dict) or set(states) != set(PARTITION_IDS):
        _fail("SEALED_ARTIFACT_DRIFT_OR_MEMBERSHIP_LEAK")
    for partition in PARTITION_IDS:
        state = states[partition]
        if (
            not isinstance(state, dict)
            or set(state) != {"one_look_state", "access_count", "consumed"}
            or state.get("one_look_state") != "SEALED_NOT_ELIGIBLE"
            or not isinstance(state.get("access_count"), int)
            or isinstance(state.get("access_count"), bool)
            or state.get("access_count") != 0
            or state.get("consumed") is not False
        ):
            _fail("SEALED_ARTIFACT_DRIFT_OR_MEMBERSHIP_LEAK")
    if (
        seal.get("schema_version") != "private-population-seal-v1"
        or seal.get("maximum_state") != "POPULATION_MATERIALIZED_AND_SEALED"
        or not _valid_hash(seal.get("source_frame_sha256"))
    ):
        _fail("SEALED_ARTIFACT_DRIFT_OR_MEMBERSHIP_LEAK")
    return {"ok": True, "boundary_integrity_status": "INTACT_SEALED"}


def blocked_summary_for(error: BoundaryViolation, *, last_state: str = "DESIGN_ONLY") -> dict[str, Any]:
    if last_state == "DESIGN_ONLY":
        summary = s0_blocked_summary()
        if error.code not in summary["blockers"]:
            summary["blockers"] = sorted({*summary["blockers"], error.code})
        return summary
    summary = s0_blocked_summary()
    compromised = error.code in {
        "EARLY_ROW_GOLD_OR_OUTCOME_ACCESS",
        "ONE_LOOK_OR_EXPERIMENT_SCOPE_BREACH",
        "SEALED_ARTIFACT_DRIFT_OR_MEMBERSHIP_LEAK",
    }
    if last_state == "EXPERIMENT_BINDINGS_COMPLETE":
        summary["blocked_stage"] = "S1_PROTOCOL_FREEZE"
        summary["new_protocol_version_required"] = True
        summary["maximum_state_this_change"] = "EXPERIMENT_BINDINGS_COMPLETE"
    else:
        summary["blocked_stage"] = "COMPROMISED_BOUNDARY" if compromised else "S2_MATERIALIZATION_OR_SEAL"
        summary["new_protocol_and_acquisition_required"] = True
        summary["maximum_state_this_change"] = last_state
    summary["current_readiness_state"] = last_state
    summary["execution_bindings_status"] = "COMPLETE"
    summary["binding_counts"] = {"total": 29, "bound": 29, "unbound": 0}
    summary["protocol_freeze_status"] = (
        "NOT_FROZEN" if last_state == "EXPERIMENT_BINDINGS_COMPLETE" else "FROZEN"
    )
    summary["boundary_integrity_status"] = (
        "COMPROMISED"
        if compromised
        else "INTACT_BLOCKED" if last_state == "PROTOCOL_FROZEN" else "NOT_CREATED"
    )
    if last_state == "POPULATION_MATERIALIZED_AND_SEALED":
        summary["clean_population_status"] = "MATERIALIZED_AND_SEALED"
        summary["population_unit"] = "SEMANTIC_FAMILY_METADATA_ONLY"
        summary["artifacts"] = {key: True for key in summary["artifacts"]}
        mutations = _false_mutations()
        mutations.update(
            {
                "boundary_materialization": True,
                "private_family_registry_created": True,
                "private_partition_membership_created": True,
            }
        )
        summary["mutations"] = mutations
        summary["partitions"] = {
            partition: {
                "status": "MATERIALIZED_AND_SEALED",
                "one_look_state": "SEALED_NOT_ELIGIBLE",
                "access_count": 0,
                "consumed": False,
            }
            for partition in PARTITION_IDS
        }
    summary["blockers"] = [error.code]
    return summary


def _summary_markdown(summary: dict[str, Any]) -> str:
    blockers = ", ".join(cast(list[str], summary["blockers"]))
    return "\n".join(
        [
            "# Clean compiler/model evaluation boundary v1",
            "",
            f"- Evidence status: `{summary['evidence_status']}`",
            f"- Decision: `{summary['decision']}`",
            f"- Current readiness state: `{summary['current_readiness_state']}`",
            f"- Bindings: `{summary['binding_counts']['bound']}/{summary['binding_counts']['total']}` bound",
            f"- Protocol: `{summary['protocol_freeze_status']}`",
            f"- Clean population: `{summary['clean_population_status']}`",
            f"- Clean evaluation rows: `{summary['clean_evaluation_rows_status']}`",
            f"- Experiment preregistration: `{summary['experiment_preregistration_status']}`",
            f"- Execution readiness: `{str(summary['execution_readiness']).lower()}`",
            f"- Blockers: `{blockers}`",
            "",
            "This evidence is aggregate-only. It creates no clean evaluation rows, opens no one-look partition, "
            "and does not establish compiler or model improvement.",
            "",
        ]
    )


def _public_protocol_manifest(summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "public-clean-evaluation-protocol-manifest-v1",
        "evidence_status": summary["evidence_status"],
        "protocol_freeze_status": summary["protocol_freeze_status"],
        "protocol_sha256": summary["hashes"]["protocol_sha256"],
        "binding_counts": summary["binding_counts"],
        "partition_algorithm": (
            "sha256-partition-by-stratum-v1" if summary["protocol_freeze_status"] == "FROZEN" else "NOT_AVAILABLE"
        ),
        "execution_readiness": False,
    }


def _public_population_seal(summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "public-population-seal-attestation-v1",
        "evidence_status": summary["evidence_status"],
        "clean_population_status": summary["clean_population_status"],
        "boundary_integrity_status": summary["boundary_integrity_status"],
        "hashes": summary["hashes"],
        "partitions": summary["partitions"],
        "artifacts": summary["artifacts"],
        "execution_readiness": False,
    }


def _public_lineage_attestation(summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "public-clean-lineage-attestation-v1",
        "evidence_status": summary["evidence_status"],
        "lineage": summary["lineage"],
        "blockers": summary["blockers"],
        "lockbox_interface": "SEALED_AGGREGATE_ATTESTATION_ONLY",
        "lockbox_row_access": False,
        "clean_evaluation_rows_status": "NOT_CREATED",
        "claims": summary["claims"],
    }


def _public_relative_parts(relative_output: Path) -> tuple[str, ...]:
    if not isinstance(relative_output, Path):
        _fail("PUBLIC_EVIDENCE_SCHEMA_VIOLATION")
    raw = relative_output.as_posix()
    path = PurePosixPath(raw)
    if (
        not raw
        or raw.startswith("~")
        or "\\" in raw
        or path.is_absolute()
        or ".." in path.parts
        or any(part in {"", "."} for part in path.parts)
        or any(not _valid_public_component(part) for part in path.parts)
    ):
        _fail("PUBLIC_EVIDENCE_SCHEMA_VIOLATION")
    return path.parts


def _valid_public_component(name: str) -> bool:
    return bool(
        _PUBLIC_COMPONENT_PATTERN.fullmatch(name)
        and not _PUBLIC_RESERVED_PREFIX_PATTERN.match(name)
    )


def _verify_public_directory_chain(
    links: list[tuple[int, str, os.stat_result]],
) -> None:
    for parent_fd, name, expected in links:
        observed = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        if not stat.S_ISDIR(observed.st_mode) or not _same_inode(expected, observed):
            _fail("PUBLIC_EVIDENCE_SCHEMA_VIOLATION")


def _validate_public_bundle_payloads(
    payloads: Mapping[str, bytes],
) -> list[tuple[str, bytes]]:
    if not isinstance(payloads, Mapping) or not payloads:
        _fail("PUBLIC_EVIDENCE_SCHEMA_VIOLATION")
    items = list(payloads.items())
    for name, payload in items:
        if (
            not isinstance(name, str)
            or not _valid_public_component(name)
            or type(payload) is not bytes
        ):
            _fail("PUBLIC_EVIDENCE_SCHEMA_VIOLATION")
    return items


def _open_verified_public_root(trusted_root: Path) -> tuple[int, os.stat_result]:
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    directory = getattr(os, "O_DIRECTORY", 0)
    descriptor = -1
    try:
        linked = os.stat(trusted_root, follow_symlinks=False)
        descriptor = os.open(trusted_root, os.O_RDONLY | directory | nofollow)
        opened = os.fstat(descriptor)
        restated = os.stat(trusted_root, follow_symlinks=False)
        if (
            not stat.S_ISDIR(linked.st_mode)
            or not stat.S_ISDIR(opened.st_mode)
            or not _same_identity(linked, opened)
            or not _same_identity(opened, restated)
        ):
            _fail("PUBLIC_EVIDENCE_SCHEMA_VIOLATION")
        return descriptor, opened
    except Exception:
        if descriptor >= 0:
            os.close(descriptor)
        raise


def _open_verified_public_directory(
    parent_fd: int,
    name: str,
) -> tuple[int, os.stat_result]:
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    directory = getattr(os, "O_DIRECTORY", 0)
    descriptor = -1
    try:
        linked = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        descriptor = os.open(
            name, os.O_RDONLY | directory | nofollow, dir_fd=parent_fd
        )
        opened = os.fstat(descriptor)
        restated = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        if (
            not stat.S_ISDIR(linked.st_mode)
            or not stat.S_ISDIR(opened.st_mode)
            or not _same_identity(linked, opened)
            or not _same_identity(opened, restated)
        ):
            _fail("PUBLIC_EVIDENCE_SCHEMA_VIOLATION")
        return descriptor, opened
    except Exception:
        if descriptor >= 0:
            os.close(descriptor)
        raise


def _close_tracked_public_descriptor(descriptors: set[int], descriptor: int) -> None:
    if descriptor in descriptors:
        descriptors.remove(descriptor)
        os.close(descriptor)


def _create_owned_public_staging(
    parent_fd: int,
    name: str,
    descriptors: set[int],
    ownership: dict[str, os.stat_result],
) -> tuple[int, os.stat_result]:
    try:
        os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        pass
    else:
        _fail("PUBLIC_EVIDENCE_SCHEMA_VIOLATION")
    mkdir_error: OSError | None = None
    try:
        os.mkdir(name, 0o700, dir_fd=parent_fd)
    except FileExistsError:
        raise
    except OSError as exc:
        # A wrapper may report failure after mkdir(2) succeeded. The random name
        # was proven absent above; recover only a stable, owned, empty 0700 dir.
        mkdir_error = exc
    try:
        descriptor, identity = _open_verified_public_directory(parent_fd, name)
    except Exception as exc:
        try:
            descriptor, identity = _open_verified_public_directory(parent_fd, name)
        except Exception:
            if mkdir_error is not None:
                raise mkdir_error from exc
            raise
        descriptors.add(descriptor)
        ownership["directory"] = identity
        if mkdir_error is not None:
            raise mkdir_error from exc
        raise
    descriptors.add(descriptor)
    ownership["directory"] = identity
    if (
        identity.st_uid != os.geteuid()
        or identity.st_mode & 0o777 != 0o700
        or tuple(os.listdir(descriptor))
    ):
        _fail("PUBLIC_EVIDENCE_SCHEMA_VIOLATION")
    os.fchmod(descriptor, 0o700)
    updated = os.fstat(descriptor)
    restated = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    if (
        not stat.S_ISDIR(updated.st_mode)
        or updated.st_mode & 0o777 != 0o700
        or updated.st_uid != os.geteuid()
        or not _same_identity(updated, restated)
    ):
        _fail("PUBLIC_EVIDENCE_SCHEMA_VIOLATION")
    ownership["directory"] = updated
    if mkdir_error is not None:
        raise mkdir_error
    return descriptor, updated


def _create_owned_public_member(
    directory_fd: int,
    name: str,
    descriptors: set[int],
    ownership: dict[str, os.stat_result],
) -> tuple[int, os.stat_result]:
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(
            name,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | nofollow,
            0o600,
            dir_fd=directory_fd,
        )
    except FileExistsError:
        raise
    except OSError:
        # A wrapper can lose the returned descriptor after successful O_EXCL
        # creation. Recover only the exact empty 0600 member inside the owned
        # random 0700 staging directory; the caller will quarantine it.
        for _attempt in range(2):
            recovered_descriptor = -1
            try:
                recovered_descriptor, recovered = _open_verified_public_file_at(
                    directory_fd, name
                )
                if (
                    recovered.st_mode & 0o777 == 0o600
                    and recovered.st_size == 0
                    and recovered.st_uid == os.geteuid()
                ):
                    descriptors.add(recovered_descriptor)
                    ownership[name] = recovered
                    recovered_descriptor = -1
                    break
            except (BoundaryViolation, OSError):
                pass
            finally:
                if recovered_descriptor >= 0:
                    os.close(recovered_descriptor)
        raise
    descriptors.add(descriptor)
    try:
        linked = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        if (
            not stat.S_ISREG(linked.st_mode)
            or linked.st_nlink != 1
            or linked.st_uid != os.geteuid()
        ):
            _fail("PUBLIC_EVIDENCE_SCHEMA_VIOLATION")
        ownership[name] = linked
        opened = os.fstat(descriptor)
        restated = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        if (
            not stat.S_ISREG(opened.st_mode)
            or opened.st_nlink != 1
            or not _same_identity(linked, opened)
            or not _same_identity(opened, restated)
        ):
            _fail("PUBLIC_EVIDENCE_SCHEMA_VIOLATION")
        ownership[name] = opened
        return descriptor, opened
    except Exception:
        if name not in ownership:
            try:
                recovered = os.fstat(descriptor)
                relinked = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
                if (
                    stat.S_ISREG(recovered.st_mode)
                    and recovered.st_nlink == 1
                    and recovered.st_uid == os.geteuid()
                    and _same_identity(recovered, relinked)
                ):
                    ownership[name] = recovered
            except (OSError, ValueError):
                pass
        raise


def _verify_public_root_link(trusted_root: Path, expected: os.stat_result) -> None:
    observed = os.stat(trusted_root, follow_symlinks=False)
    if not stat.S_ISDIR(observed.st_mode) or not _same_inode(expected, observed):
        _fail("PUBLIC_EVIDENCE_SCHEMA_VIOLATION")


def _snapshot_public_bundle(
    parent_fd: int,
    name: str,
    expected_names: tuple[str, ...],
    *,
    allow_missing: bool,
) -> tuple[os.stat_result, dict[str, os.stat_result]] | None:
    try:
        linked = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        return None
    if not stat.S_ISDIR(linked.st_mode):
        _fail("PUBLIC_EVIDENCE_SCHEMA_VIOLATION")
    descriptor, opened = _open_verified_public_directory(parent_fd, name)
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    try:
        names = tuple(os.listdir(descriptor))
        if set(names) - set(expected_names) or (
            not allow_missing and set(names) != set(expected_names)
        ):
            _fail("PUBLIC_EVIDENCE_SCHEMA_VIOLATION")
        members: dict[str, os.stat_result] = {}
        for member_name in names:
            before = os.stat(member_name, dir_fd=descriptor, follow_symlinks=False)
            if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
                _fail("PUBLIC_EVIDENCE_SCHEMA_VIOLATION")
            member_fd = os.open(member_name, os.O_RDONLY | nofollow, dir_fd=descriptor)
            try:
                member_opened = os.fstat(member_fd)
                after = os.stat(member_name, dir_fd=descriptor, follow_symlinks=False)
                if (
                    not stat.S_ISREG(member_opened.st_mode)
                    or member_opened.st_nlink != 1
                    or not _same_identity(before, member_opened)
                    or not _same_identity(member_opened, after)
                ):
                    _fail("PUBLIC_EVIDENCE_SCHEMA_VIOLATION")
                members[member_name] = member_opened
            finally:
                os.close(member_fd)
        restated = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        if not _same_inode(opened, restated):
            _fail("PUBLIC_EVIDENCE_SCHEMA_VIOLATION")
        return opened, members
    finally:
        os.close(descriptor)


def _public_bundle_matches(
    parent_fd: int,
    name: str,
    expected_directory: os.stat_result,
    expected_members: dict[str, os.stat_result],
) -> bool:
    try:
        snapshot = _snapshot_public_bundle(
            parent_fd,
            name,
            tuple(expected_members),
            allow_missing=False,
        )
    except (BoundaryViolation, OSError):
        return False
    if snapshot is None or not _same_inode(expected_directory, snapshot[0]):
        return False
    return all(
        member_name in snapshot[1]
        and _same_identity(expected, snapshot[1][member_name])
        for member_name, expected in expected_members.items()
    )


def _same_public_owned_file(
    expected: os.stat_result, observed: os.stat_result
) -> bool:
    return (
        _same_public_file_ownership(expected, observed)
        and expected.st_mode == observed.st_mode
        and expected.st_nlink == observed.st_nlink
        and expected.st_size == observed.st_size
        and expected.st_mtime_ns == observed.st_mtime_ns
    )


def _same_public_owned_directory(
    expected: os.stat_result, observed: os.stat_result
) -> bool:
    return (
        _same_public_directory_ownership(expected, observed)
        and expected.st_mode == observed.st_mode
        and expected.st_nlink == observed.st_nlink
        and expected.st_size == observed.st_size
        and expected.st_mtime_ns == observed.st_mtime_ns
    )


def _same_public_object_id(
    expected: os.stat_result, observed: os.stat_result
) -> bool:
    return (expected.st_dev, expected.st_ino) == (observed.st_dev, observed.st_ino)


def _same_public_file_ownership(
    expected: os.stat_result, observed: os.stat_result
) -> bool:
    return (
        _same_public_object_id(expected, observed)
        and stat.S_ISREG(observed.st_mode)
        and observed.st_nlink == 1
        and expected.st_uid == observed.st_uid == os.geteuid()
        and expected.st_gid == observed.st_gid
    )


def _same_public_directory_ownership(
    expected: os.stat_result, observed: os.stat_result
) -> bool:
    return (
        _same_public_object_id(expected, observed)
        and stat.S_ISDIR(observed.st_mode)
        and expected.st_uid == observed.st_uid == os.geteuid()
        and expected.st_gid == observed.st_gid
    )


def _open_verified_public_file_at(
    directory_fd: int,
    name: str,
) -> tuple[int, os.stat_result]:
    descriptor = -1
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    try:
        linked = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        if not stat.S_ISREG(linked.st_mode) or linked.st_nlink != 1:
            _fail("PUBLIC_EVIDENCE_SCHEMA_VIOLATION")
        descriptor = os.open(name, os.O_RDONLY | nofollow, dir_fd=directory_fd)
        opened = os.fstat(descriptor)
        restated = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        if (
            not stat.S_ISREG(opened.st_mode)
            or opened.st_nlink != 1
            or not _same_identity(linked, opened)
            or not _same_identity(opened, restated)
        ):
            _fail("PUBLIC_EVIDENCE_SCHEMA_VIOLATION")
        return descriptor, opened
    except Exception:
        if descriptor >= 0:
            os.close(descriptor)
        raise


def _unlinkat_public(directory_fd: int, name: str, flags: int = 0) -> None:
    if sys.platform != "darwin" and not sys.platform.startswith("linux"):
        raise OSError(errno.ENOTSUP, "unlinkat is unavailable")
    libc = ctypes.CDLL(None, use_errno=True)
    if not hasattr(libc, "unlinkat"):
        raise OSError(errno.ENOTSUP, "unlinkat is unavailable")
    function = libc.unlinkat
    function.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int]
    function.restype = ctypes.c_int
    result = function(directory_fd, os.fsencode(name), flags)
    if result != 0:
        error_number = ctypes.get_errno()
        raise OSError(error_number, os.strerror(error_number))


def _public_at_removedir_flag() -> int:
    if sys.platform == "darwin":
        return 0x80
    if sys.platform.startswith("linux"):
        return 0x200
    raise OSError(errno.ENOTSUP, "AT_REMOVEDIR is unavailable")


def _restore_public_quarantine_name(
    directory_fd: int,
    quarantine_name: str,
    source_name: str,
) -> None:
    try:
        os.stat(source_name, dir_fd=directory_fd, follow_symlinks=False)
    except FileNotFoundError:
        try:
            _rename_noreplace(
                directory_fd,
                quarantine_name,
                directory_fd,
                source_name,
            )
        except OSError:
            return


def _verified_public_name_identity(
    directory_fd: int,
    name: str,
    *,
    is_directory: bool,
) -> os.stat_result:
    if is_directory:
        descriptor, identity = _open_verified_public_directory(directory_fd, name)
    else:
        descriptor, identity = _open_verified_public_file_at(directory_fd, name)
    try:
        return identity
    finally:
        os.close(descriptor)


def _quarantine_verified_public_name(
    directory_fd: int,
    source_name: str,
    quarantine_name: str,
    expected: os.stat_result,
    *,
    is_directory: bool,
) -> tuple[os.stat_result, OSError | None]:
    try:
        os.stat(quarantine_name, dir_fd=directory_fd, follow_symlinks=False)
    except FileNotFoundError:
        pass
    else:
        _fail("PUBLIC_EVIDENCE_SCHEMA_VIOLATION")
    rename_error: OSError | None = None
    try:
        _rename_noreplace(
            directory_fd,
            source_name,
            directory_fd,
            quarantine_name,
        )
    except OSError as exc:
        # Inspect the destination because a wrapper may raise after rename(2).
        rename_error = exc
    descriptor = -1
    try:
        if is_directory:
            descriptor, moved = _open_verified_public_directory(
                directory_fd, quarantine_name
            )
            identity_matches = _same_public_owned_directory(expected, moved)
        else:
            descriptor, moved = _open_verified_public_file_at(
                directory_fd, quarantine_name
            )
            identity_matches = _same_public_owned_file(expected, moved)
    except (BoundaryViolation, OSError) as exc:
        if rename_error is not None:
            raise rename_error from exc
        raise
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    if not identity_matches:
        _restore_public_quarantine_name(
            directory_fd, quarantine_name, source_name
        )
        _fail("PUBLIC_EVIDENCE_SCHEMA_VIOLATION")
    try:
        source_replacement = _verified_public_name_identity(
            directory_fd,
            source_name,
            is_directory=is_directory,
        )
    except FileNotFoundError:
        pass
    else:
        # Restore the moved owned object with an atomic exchange while moving
        # the replacement into quarantine. If exchange is unavailable or its
        # wrapper faults, inspect only; every branch preserves both objects.
        try:
            _rename_exchange(
                directory_fd,
                quarantine_name,
                directory_fd,
                source_name,
            )
        except OSError:
            pass
        try:
            restored = _verified_public_name_identity(
                directory_fd,
                source_name,
                is_directory=is_directory,
            )
            isolated_replacement = _verified_public_name_identity(
                directory_fd,
                quarantine_name,
                is_directory=is_directory,
            )
        except (BoundaryViolation, OSError):
            _fail("PUBLIC_EVIDENCE_SCHEMA_VIOLATION")
        if is_directory:
            restoration_matches = _same_public_owned_directory(expected, restored)
            replacement_matches = _same_public_owned_directory(
                source_replacement, isolated_replacement
            )
        else:
            restoration_matches = _same_public_owned_file(expected, restored)
            replacement_matches = _same_public_owned_file(
                source_replacement, isolated_replacement
            )
        if not restoration_matches or not replacement_matches:
            _fail("PUBLIC_EVIDENCE_SCHEMA_VIOLATION")
        _fail("PUBLIC_EVIDENCE_SCHEMA_VIOLATION")
    return moved, rename_error


def _unlink_verified_public_file_at(
    directory_fd: int,
    name: str,
    expected: os.stat_result,
) -> None:
    descriptor, opened = _open_verified_public_file_at(directory_fd, name)
    try:
        if not _same_identity(expected, opened):
            _fail("PUBLIC_EVIDENCE_SCHEMA_VIOLATION")
        _unlinkat_public(directory_fd, name)
        unlinked = os.fstat(descriptor)
        if (
            not _same_public_object_id(opened, unlinked)
            or not stat.S_ISREG(unlinked.st_mode)
            or unlinked.st_nlink != 0
        ):
            _fail("PUBLIC_EVIDENCE_SCHEMA_VIOLATION")
        try:
            os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            _fail("PUBLIC_EVIDENCE_SCHEMA_VIOLATION")
    finally:
        os.close(descriptor)


def _unlink_verified_public_directory_at(
    parent_fd: int,
    name: str,
    expected: os.stat_result,
) -> None:
    descriptor, opened = _open_verified_public_directory(parent_fd, name)
    try:
        if (
            not _same_public_owned_directory(expected, opened)
            or tuple(os.listdir(descriptor))
        ):
            _fail("PUBLIC_EVIDENCE_SCHEMA_VIOLATION")
        linked = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        if not _same_identity(opened, linked):
            _fail("PUBLIC_EVIDENCE_SCHEMA_VIOLATION")
        _unlinkat_public(parent_fd, name, _public_at_removedir_flag())
        unlinked = os.fstat(descriptor)
        if not _same_public_object_id(opened, unlinked) or not stat.S_ISDIR(
            unlinked.st_mode
        ):
            _fail("PUBLIC_EVIDENCE_SCHEMA_VIOLATION")
        try:
            os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            _fail("PUBLIC_EVIDENCE_SCHEMA_VIOLATION")
    finally:
        os.close(descriptor)


def _cleanup_verified_public_bundle(
    parent_fd: int,
    name: str,
    expected_directory: os.stat_result,
    expected_members: dict[str, os.stat_result],
    *,
    allow_owned_state_drift: bool = False,
) -> None:
    parent_identity = os.fstat(parent_fd)
    snapshot = _snapshot_public_bundle(
        parent_fd,
        name,
        tuple(expected_members),
        allow_missing=True,
    )
    if snapshot is None:
        return
    directory_matches = (
        _same_public_directory_ownership(expected_directory, snapshot[0])
        if allow_owned_state_drift
        else _same_public_owned_directory(expected_directory, snapshot[0])
    )
    members_match = all(
        member_name in expected_members
        and (
            _same_public_file_ownership(expected_members[member_name], observed)
            if allow_owned_state_drift
            else _same_identity(expected_members[member_name], observed)
        )
        for member_name, observed in snapshot[1].items()
    )
    if not directory_matches or not members_match:
        _fail("PUBLIC_EVIDENCE_SCHEMA_VIOLATION")
    quarantine_name = f".cleanup-bundle-{secrets.token_hex(16)}"
    moved_directory, cleanup_error = _quarantine_verified_public_name(
        parent_fd,
        name,
        quarantine_name,
        snapshot[0],
        is_directory=True,
    )
    descriptor, opened = _open_verified_public_directory(parent_fd, quarantine_name)
    try:
        if not _same_public_owned_directory(moved_directory, opened):
            _fail("PUBLIC_EVIDENCE_SCHEMA_VIOLATION")
        os.fchmod(descriptor, 0o700)
        quarantine_identity = os.fstat(descriptor)
        linked = os.stat(quarantine_name, dir_fd=parent_fd, follow_symlinks=False)
        if (
            quarantine_identity.st_mode & 0o777 != 0o700
            or not _same_identity(quarantine_identity, linked)
            or not _same_public_directory_ownership(parent_identity, os.fstat(parent_fd))
        ):
            _fail("PUBLIC_EVIDENCE_SCHEMA_VIOLATION")
        for member_name in tuple(os.listdir(descriptor)):
            expected = expected_members.get(member_name)
            if expected is None:
                _fail("PUBLIC_EVIDENCE_SCHEMA_VIOLATION")
            member_quarantine_name = f".cleanup-member-{secrets.token_hex(16)}"
            moved_member, member_error = _quarantine_verified_public_name(
                descriptor,
                member_name,
                member_quarantine_name,
                snapshot[1][member_name],
                is_directory=False,
            )
            cleanup_error = cleanup_error or member_error
            _unlink_verified_public_file_at(
                descriptor, member_quarantine_name, moved_member
            )
        os.fsync(descriptor)
        if tuple(os.listdir(descriptor)):
            _fail("PUBLIC_EVIDENCE_SCHEMA_VIOLATION")
        quarantine_identity = os.fstat(descriptor)
        linked = os.stat(quarantine_name, dir_fd=parent_fd, follow_symlinks=False)
        if not _same_identity(quarantine_identity, linked):
            _fail("PUBLIC_EVIDENCE_SCHEMA_VIOLATION")
    finally:
        os.close(descriptor)
    _unlink_verified_public_directory_at(
        parent_fd, quarantine_name, quarantine_identity
    )
    os.fsync(parent_fd)
    if not _same_public_directory_ownership(parent_identity, os.fstat(parent_fd)):
        _fail("PUBLIC_EVIDENCE_SCHEMA_VIOLATION")
    if cleanup_error is not None:
        raise cleanup_error


def _verified_public_directory_identity(
    parent_fd: int,
    name: str,
) -> os.stat_result | None:
    try:
        descriptor, identity = _open_verified_public_directory(parent_fd, name)
    except FileNotFoundError:
        return None
    try:
        return identity
    finally:
        os.close(descriptor)


def _rollback_public_bundle_promotion(
    parent_fd: int,
    final_name: str,
    staging_name: str,
    staging_identity: os.stat_result,
    staging_members: dict[str, os.stat_result],
    original: tuple[os.stat_result, dict[str, os.stat_result]] | None,
) -> None:
    if original is None:
        if not _public_bundle_matches(
            parent_fd, final_name, staging_identity, staging_members
        ):
            return
        try:
            os.stat(staging_name, dir_fd=parent_fd, follow_symlinks=False)
        except FileNotFoundError:
            _rename_noreplace(parent_fd, final_name, parent_fd, staging_name)
        else:
            return
    else:
        if not _public_bundle_matches(
            parent_fd, final_name, staging_identity, staging_members
        ):
            return
        displaced_identity = _verified_public_directory_identity(
            parent_fd, staging_name
        )
        if displaced_identity is None:
            return
        _rename_exchange(parent_fd, final_name, parent_fd, staging_name)
        restored = _verified_public_directory_identity(parent_fd, final_name)
        if (
            restored is None
            or not _same_inode(displaced_identity, restored)
            or not _public_bundle_matches(
                parent_fd, staging_name, staging_identity, staging_members
            )
        ):
            return
    if _public_bundle_matches(
        parent_fd, staging_name, staging_identity, staging_members
    ):
        _cleanup_verified_public_bundle(
            parent_fd,
            staging_name,
            staging_identity,
            staging_members,
        )


def _review_object_signature(value: os.stat_result) -> tuple[int, int, int, int, int]:
    return (
        value.st_dev,
        value.st_ino,
        stat.S_IFMT(value.st_mode),
        value.st_uid,
        value.st_gid,
    )


def _review_directory_signature(
    value: os.stat_result,
) -> tuple[int, int, int, int, int, int]:
    return (*_review_object_signature(value), value.st_mode)


def _review_file_signature(
    value: os.stat_result,
) -> tuple[int, int, int, int, int, int, int, int, int, int]:
    return (
        *_review_object_signature(value),
        value.st_mode,
        value.st_nlink,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )


def _review_require_safe_directory(value: os.stat_result) -> None:
    if (
        not stat.S_ISDIR(value.st_mode)
        or value.st_uid != os.geteuid()
        or value.st_mode & 0o022
    ):
        _fail("PUBLIC_EVIDENCE_SCHEMA_VIOLATION")


def _review_open_root(trusted_root: Path) -> tuple[int, os.stat_result]:
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    directory = getattr(os, "O_DIRECTORY", 0)
    if not nofollow or not directory:
        _fail("PUBLIC_EVIDENCE_SCHEMA_VIOLATION")
    descriptor = -1
    try:
        linked = os.stat(trusted_root, follow_symlinks=False)
        descriptor = os.open(trusted_root, os.O_RDONLY | directory | nofollow)
        opened = os.fstat(descriptor)
        relinked = os.stat(trusted_root, follow_symlinks=False)
        if not (
            _review_directory_signature(linked)
            == _review_directory_signature(opened)
            == _review_directory_signature(relinked)
        ):
            _fail("PUBLIC_EVIDENCE_SCHEMA_VIOLATION")
        _review_require_safe_directory(opened)
        return descriptor, opened
    except Exception:
        if descriptor >= 0:
            os.close(descriptor)
        raise


def _review_open_directory_at(
    parent_fd: int,
    name: str,
) -> tuple[int, os.stat_result]:
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    directory = getattr(os, "O_DIRECTORY", 0)
    if not nofollow or not directory:
        _fail("PUBLIC_EVIDENCE_SCHEMA_VIOLATION")
    descriptor = -1
    try:
        linked = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        descriptor = os.open(
            name,
            os.O_RDONLY | directory | nofollow,
            dir_fd=parent_fd,
        )
        opened = os.fstat(descriptor)
        relinked = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        if not (
            _review_directory_signature(linked)
            == _review_directory_signature(opened)
            == _review_directory_signature(relinked)
        ):
            _fail("PUBLIC_EVIDENCE_SCHEMA_VIOLATION")
        return descriptor, opened
    except Exception:
        if descriptor >= 0:
            os.close(descriptor)
        raise


def _review_verify_namespace(
    trusted_root: Path,
    root_fd: int,
    root_identity: os.stat_result,
    links: list[tuple[int, str, int, os.stat_result]],
) -> None:
    root_opened = os.fstat(root_fd)
    root_relinked = os.stat(trusted_root, follow_symlinks=False)
    expected_root = _review_directory_signature(root_identity)
    if not (
        _review_directory_signature(root_opened)
        == expected_root
        == _review_directory_signature(root_relinked)
    ):
        _fail("PUBLIC_EVIDENCE_SCHEMA_VIOLATION")
    _review_require_safe_directory(root_opened)
    for parent_fd, name, descriptor, expected in links:
        opened = os.fstat(descriptor)
        relinked = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        expected_signature = _review_directory_signature(expected)
        if not (
            _review_directory_signature(opened)
            == expected_signature
            == _review_directory_signature(relinked)
        ):
            _fail("PUBLIC_EVIDENCE_SCHEMA_VIOLATION")
        _review_require_safe_directory(opened)


def _review_require_stable_staged_namespace(
    trusted_root: Path,
    root_fd: int,
    root_identity: os.stat_result,
    links: list[tuple[int, str, int, os.stat_result]],
) -> None:
    try:
        _review_verify_namespace(
            trusted_root,
            root_fd,
            root_identity,
            links,
        )
    except (BoundaryViolation, OSError, ValueError):
        _fail("REVIEW_PUBLICATION_IDENTITY_UNCERTAIN")


def _review_open_fixed_parent(
    trusted_root: Path,
) -> tuple[
    list[int],
    int,
    os.stat_result,
    list[tuple[int, str, int, os.stat_result]],
    os.stat_result,
]:
    descriptors: list[int] = []
    links: list[tuple[int, str, int, os.stat_result]] = []
    try:
        root_fd, root_identity = _review_open_root(trusted_root)
        descriptors.append(root_fd)
        parent_fd = root_fd
        parent_identity = root_identity
        for name in REVIEW_PUBLIC_BUNDLE_ROOT.parts[:-1]:
            child_fd, child_identity = _review_open_directory_at(parent_fd, name)
            descriptors.append(child_fd)
            _review_require_safe_directory(child_identity)
            links.append((parent_fd, name, child_fd, child_identity))
            parent_fd = child_fd
            parent_identity = child_identity
        _review_verify_namespace(
            trusted_root,
            root_fd,
            root_identity,
            links,
        )
        return descriptors, root_fd, root_identity, links, parent_identity
    except Exception:
        for descriptor in reversed(descriptors):
            os.close(descriptor)
        raise


def _review_recovery_sibling_present(parent_fd: int) -> bool:
    return any(
        name.startswith(REVIEW_PUBLIC_RECOVERY_PREFIX)
        for name in os.listdir(parent_fd)
    )


def _review_noreplace_available() -> bool:
    try:
        libc = ctypes.CDLL(None, use_errno=True)
    except OSError:
        return False
    if sys.platform == "darwin":
        return hasattr(libc, "renameatx_np")
    if sys.platform.startswith("linux"):
        return hasattr(libc, "renameat2")
    return False


def _review_bounded_read(descriptor: int, expected_length: int) -> bytes:
    limit = expected_length + 1
    chunks: list[bytes] = []
    consumed = 0
    while consumed < limit:
        chunk = os.read(descriptor, limit - consumed)
        if not chunk:
            break
        chunks.append(chunk)
        consumed += len(chunk)
    return b"".join(chunks)


def _review_exact_final(
    parent_fd: int,
    items: list[tuple[str, bytes]],
    trusted_parent_gid: int,
) -> os.stat_result | None:
    final_name = REVIEW_PUBLIC_BUNDLE_ROOT.name
    try:
        linked = os.stat(final_name, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        return None
    if not stat.S_ISDIR(linked.st_mode):
        _fail("PUBLIC_EVIDENCE_SCHEMA_VIOLATION")
    final_fd, opened = _review_open_directory_at(parent_fd, final_name)
    try:
        if (
            stat.S_IMODE(opened.st_mode) != 0o755
            or opened.st_uid != os.geteuid()
            or opened.st_gid != trusted_parent_gid
            or opened.st_mode & 0o022
        ):
            _fail("PUBLIC_EVIDENCE_SCHEMA_VIOLATION")
        expected_names = tuple(name for name, _payload in items)
        observed_names = tuple(os.listdir(final_fd))
        if len(observed_names) != len(expected_names) or set(observed_names) != set(
            expected_names
        ):
            _fail("PUBLIC_EVIDENCE_SCHEMA_VIOLATION")
        nofollow = getattr(os, "O_NOFOLLOW", 0)
        if not nofollow:
            _fail("PUBLIC_EVIDENCE_SCHEMA_VIOLATION")
        for name, expected_payload in items:
            member_fd = -1
            try:
                member_linked = os.stat(
                    name,
                    dir_fd=final_fd,
                    follow_symlinks=False,
                )
                if (
                    not stat.S_ISREG(member_linked.st_mode)
                    or stat.S_IMODE(member_linked.st_mode) != 0o644
                    or member_linked.st_nlink != 1
                    or member_linked.st_uid != os.geteuid()
                    or member_linked.st_gid != trusted_parent_gid
                ):
                    _fail("PUBLIC_EVIDENCE_SCHEMA_VIOLATION")
                member_fd = os.open(
                    name,
                    os.O_RDONLY | nofollow,
                    dir_fd=final_fd,
                )
                before_read = os.fstat(member_fd)
                if _review_file_signature(member_linked) != _review_file_signature(
                    before_read
                ):
                    _fail("PUBLIC_EVIDENCE_SCHEMA_VIOLATION")
                observed_payload = _review_bounded_read(
                    member_fd,
                    len(expected_payload),
                )
                after_read = os.fstat(member_fd)
                member_relinked = os.stat(
                    name,
                    dir_fd=final_fd,
                    follow_symlinks=False,
                )
                expected_signature = _review_file_signature(member_linked)
                if not (
                    _review_file_signature(before_read)
                    == expected_signature
                    == _review_file_signature(after_read)
                    == _review_file_signature(member_relinked)
                ):
                    _fail("PUBLIC_EVIDENCE_SCHEMA_VIOLATION")
                if observed_payload != expected_payload:
                    _fail("PUBLIC_EVIDENCE_SCHEMA_VIOLATION")
            finally:
                if member_fd >= 0:
                    os.close(member_fd)
        final_opened = os.fstat(final_fd)
        final_relinked = os.stat(
            final_name,
            dir_fd=parent_fd,
            follow_symlinks=False,
        )
        expected_directory = _review_directory_signature(opened)
        if not (
            _review_directory_signature(final_opened)
            == expected_directory
            == _review_directory_signature(final_relinked)
        ):
            _fail("PUBLIC_EVIDENCE_SCHEMA_VIOLATION")
        return final_opened
    finally:
        os.close(final_fd)


def _review_recovery_owned(
    parent_fd: int,
    staging_name: str,
    staging_fd: int,
    expected_identity: os.stat_result,
    trusted_parent_gid: int,
) -> bool:
    try:
        opened = os.fstat(staging_fd)
        relinked = os.stat(
            staging_name,
            dir_fd=parent_fd,
            follow_symlinks=False,
        )
    except (OSError, ValueError):
        return False
    expected = _review_object_signature(expected_identity)
    return (
        stat.S_ISDIR(opened.st_mode)
        and stat.S_ISDIR(relinked.st_mode)
        and _review_object_signature(opened)
        == expected
        == _review_object_signature(relinked)
        and opened.st_uid == os.geteuid()
        and opened.st_gid == trusted_parent_gid
    )


def _review_retain_owned_recovery(
    parent_fd: int,
    staging_name: str,
    staging_fd: int,
    expected_identity: os.stat_result,
    trusted_parent_gid: int,
) -> str:
    if not _review_recovery_owned(
        parent_fd,
        staging_name,
        staging_fd,
        expected_identity,
        trusted_parent_gid,
    ):
        return "REVIEW_PUBLICATION_IDENTITY_UNCERTAIN"
    try:
        os.fchmod(staging_fd, 0o700)
    except OSError:
        pass
    if not _review_recovery_owned(
        parent_fd,
        staging_name,
        staging_fd,
        expected_identity,
        trusted_parent_gid,
    ):
        return "REVIEW_PUBLICATION_IDENTITY_UNCERTAIN"
    try:
        opened = os.fstat(staging_fd)
        relinked = os.stat(
            staging_name,
            dir_fd=parent_fd,
            follow_symlinks=False,
        )
    except (OSError, ValueError):
        return "REVIEW_PUBLICATION_IDENTITY_UNCERTAIN"
    if not (
        stat.S_IMODE(opened.st_mode) == 0o700
        and _review_directory_signature(opened)
        == _review_directory_signature(relinked)
    ):
        return "REVIEW_PUBLICATION_IDENTITY_UNCERTAIN"
    return "REVIEW_PUBLICATION_RECOVERY_RETAINED"


def _review_stage_name_absent(parent_fd: int, staging_name: str) -> bool:
    try:
        os.stat(staging_name, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        return True
    except OSError:
        return False
    return False


def _review_final_is_promoted(
    parent_fd: int,
    staging_name: str,
    staging_identity: os.stat_result,
    items: list[tuple[str, bytes]],
    trusted_parent_gid: int,
) -> bool:
    try:
        final_identity = _review_exact_final(
            parent_fd,
            items,
            trusted_parent_gid,
        )
    except (BoundaryViolation, OSError, ValueError):
        return False
    return (
        final_identity is not None
        and _review_object_signature(final_identity)
        == _review_object_signature(staging_identity)
        and _review_stage_name_absent(parent_fd, staging_name)
    )


def _review_classify_staged_failure(
    trusted_root: Path,
    root_fd: int,
    root_identity: os.stat_result,
    links: list[tuple[int, str, int, os.stat_result]],
    parent_fd: int,
    staging_name: str,
    staging_fd: int,
    staging_identity: os.stat_result,
    trusted_parent_gid: int,
    items: list[tuple[str, bytes]],
    *,
    promotion_attempted: bool,
) -> str:
    try:
        _review_verify_namespace(
            trusted_root,
            root_fd,
            root_identity,
            links,
        )
    except (BoundaryViolation, OSError, ValueError):
        return "REVIEW_PUBLICATION_IDENTITY_UNCERTAIN"
    if promotion_attempted and _review_final_is_promoted(
        parent_fd,
        staging_name,
        staging_identity,
        items,
        trusted_parent_gid,
    ):
        return "REVIEW_PUBLICATION_POST_SYSCALL_FAILURE"
    if not _review_recovery_owned(
        parent_fd,
        staging_name,
        staging_fd,
        staging_identity,
        trusted_parent_gid,
    ):
        return "REVIEW_PUBLICATION_IDENTITY_UNCERTAIN"
    return _review_retain_owned_recovery(
        parent_fd,
        staging_name,
        staging_fd,
        staging_identity,
        trusted_parent_gid,
    )


def _review_write_member(
    staging_fd: int,
    name: str,
    payload: bytes,
    trusted_parent_gid: int,
) -> None:
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    if not nofollow:
        _fail("PUBLIC_EVIDENCE_SCHEMA_VIOLATION")
    descriptor = -1
    try:
        descriptor = os.open(
            name,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | nofollow,
            0o600,
            dir_fd=staging_fd,
        )
        created = os.fstat(descriptor)
        linked = os.stat(name, dir_fd=staging_fd, follow_symlinks=False)
        if (
            not stat.S_ISREG(created.st_mode)
            or created.st_nlink != 1
            or created.st_uid != os.geteuid()
            or created.st_gid != trusted_parent_gid
            or _review_file_signature(created) != _review_file_signature(linked)
        ):
            _fail("PUBLIC_EVIDENCE_SCHEMA_VIOLATION")
        os.fchmod(descriptor, 0o644)
        _write_all_and_fsync(descriptor, payload)
        completed = os.fstat(descriptor)
        relinked = os.stat(name, dir_fd=staging_fd, follow_symlinks=False)
        if (
            not stat.S_ISREG(completed.st_mode)
            or stat.S_IMODE(completed.st_mode) != 0o644
            or completed.st_nlink != 1
            or completed.st_uid != os.geteuid()
            or completed.st_gid != trusted_parent_gid
            or completed.st_size != len(payload)
            or _review_file_signature(completed) != _review_file_signature(relinked)
        ):
            _fail("PUBLIC_EVIDENCE_SCHEMA_VIOLATION")
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def write_review_public_bundle(
    payloads: Mapping[str, bytes],
    trusted_root: Path,
) -> dict[str, Path]:
    items = _validate_public_bundle_payloads(payloads)
    if tuple(name for name, _payload in items) != REVIEW_PUBLIC_ARTIFACT_FILENAMES:
        _fail("PUBLIC_EVIDENCE_SCHEMA_VIOLATION")
    descriptors: list[int] = []
    parent_fd = -1
    root_fd = -1
    root_identity: os.stat_result | None = None
    links: list[tuple[int, str, int, os.stat_result]] = []
    trusted_parent_gid = -1
    staging_fd = -1
    staging_name = ""
    staging_identity: os.stat_result | None = None
    staging_namespace_attempted = False
    promotion_attempted = False
    canonical_proven = False
    failure_code: str | None = None
    output_dir = trusted_root / REVIEW_PUBLIC_BUNDLE_ROOT
    try:
        (
            descriptors,
            root_fd,
            root_identity,
            links,
            parent_identity,
        ) = _review_open_fixed_parent(trusted_root)
        parent_fd = descriptors[-1]
        trusted_parent_gid = parent_identity.st_gid
        recovery_present = _review_recovery_sibling_present(parent_fd)
        _review_verify_namespace(
            trusted_root,
            root_fd,
            root_identity,
            links,
        )
        if recovery_present:
            _fail("REVIEW_PUBLICATION_RECOVERY_PRESENT")
        existing = _review_exact_final(parent_fd, items, trusted_parent_gid)
        if existing is not None:
            recovery_present = _review_recovery_sibling_present(parent_fd)
            _review_verify_namespace(
                trusted_root,
                root_fd,
                root_identity,
                links,
            )
            if recovery_present:
                _fail("REVIEW_PUBLICATION_RECOVERY_PRESENT")
            return {name: output_dir / name for name, _payload in items}
        try:
            noreplace_available = _review_noreplace_available()
        except Exception:
            noreplace_available = False
        if not noreplace_available:
            _fail("REVIEW_PUBLICATION_NO_REPLACE_UNAVAILABLE")
        token = secrets.token_hex(16)
        if not re.fullmatch(r"[0-9a-f]{32}", token):
            _fail("PUBLIC_EVIDENCE_SCHEMA_VIOLATION")
        staging_name = f"{REVIEW_PUBLIC_RECOVERY_PREFIX}{token}"
        try:
            os.stat(staging_name, dir_fd=parent_fd, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            _fail("REVIEW_PUBLICATION_IDENTITY_UNCERTAIN")
        recovery_present = _review_recovery_sibling_present(parent_fd)
        _review_verify_namespace(
            trusted_root,
            root_fd,
            root_identity,
            links,
        )
        if recovery_present:
            _fail("REVIEW_PUBLICATION_RECOVERY_PRESENT")
        staging_namespace_attempted = True
        mkdir_error: OSError | None = None
        try:
            os.mkdir(staging_name, 0o700, dir_fd=parent_fd)
        except OSError as exc:
            mkdir_error = exc
        staging_fd, staging_identity = _review_open_directory_at(
            parent_fd,
            staging_name,
        )
        descriptors.append(staging_fd)
        if (
            staging_identity.st_uid != os.geteuid()
            or staging_identity.st_gid != trusted_parent_gid
        ):
            _fail("REVIEW_PUBLICATION_IDENTITY_UNCERTAIN")
        staging_entries = tuple(os.listdir(staging_fd))
        if mkdir_error is not None:
            _fail("REVIEW_PUBLICATION_IDENTITY_UNCERTAIN")
        if (
            stat.S_IMODE(staging_identity.st_mode) != 0o700
            or staging_entries
        ):
            raise OSError(errno.EIO, "staging post-create state is not recoverable")
        for name, payload in items:
            _review_write_member(staging_fd, name, payload, trusted_parent_gid)
        os.fsync(staging_fd)
        _review_require_stable_staged_namespace(
            trusted_root,
            root_fd,
            root_identity,
            links,
        )
        if not _review_recovery_owned(
            parent_fd,
            staging_name,
            staging_fd,
            staging_identity,
            trusted_parent_gid,
        ):
            _fail("REVIEW_PUBLICATION_IDENTITY_UNCERTAIN")
        staged_before_mode_change = os.fstat(staging_fd)
        staging_before_mode_relink = os.stat(
            staging_name,
            dir_fd=parent_fd,
            follow_symlinks=False,
        )
        if not (
            _review_object_signature(staged_before_mode_change)
            == _review_object_signature(staging_identity)
            == _review_object_signature(staging_before_mode_relink)
            and _review_directory_signature(staged_before_mode_change)
            == _review_directory_signature(staging_before_mode_relink)
        ):
            _fail("REVIEW_PUBLICATION_IDENTITY_UNCERTAIN")
        if stat.S_IMODE(staged_before_mode_change.st_mode) != 0o700:
            raise OSError(errno.EIO, "staging mode drifted before promotion")
        os.fchmod(staging_fd, 0o755)
        staged_opened = os.fstat(staging_fd)
        staged_relinked = os.stat(
            staging_name,
            dir_fd=parent_fd,
            follow_symlinks=False,
        )
        if not (
            _review_object_signature(staged_opened)
            == _review_object_signature(staging_identity)
            == _review_object_signature(staged_relinked)
            and _review_directory_signature(staged_opened)
            == _review_directory_signature(staged_relinked)
            and staged_opened.st_uid == os.geteuid()
            and staged_opened.st_gid == trusted_parent_gid
        ):
            _fail("REVIEW_PUBLICATION_IDENTITY_UNCERTAIN")
        if (
            stat.S_IMODE(staged_opened.st_mode) != 0o755
            or staged_opened.st_mode & 0o022
        ):
            raise OSError(errno.EIO, "staging mode transition was not proven")
        os.fsync(staging_fd)
        os.fsync(parent_fd)
        _review_require_stable_staged_namespace(
            trusted_root,
            root_fd,
            root_identity,
            links,
        )
        promotion_attempted = True
        _rename_noreplace(
            parent_fd,
            staging_name,
            parent_fd,
            REVIEW_PUBLIC_BUNDLE_ROOT.name,
        )
        try:
            final_identity = _review_exact_final(
                parent_fd,
                items,
                trusted_parent_gid,
            )
        except (BoundaryViolation, OSError, ValueError):
            _fail("REVIEW_PUBLICATION_IDENTITY_UNCERTAIN")
        if (
            final_identity is None
            or _review_object_signature(final_identity)
            != _review_object_signature(staging_identity)
            or not _review_stage_name_absent(parent_fd, staging_name)
        ):
            _fail("REVIEW_PUBLICATION_IDENTITY_UNCERTAIN")
        canonical_proven = True
        os.fsync(parent_fd)
        recovery_present = _review_recovery_sibling_present(parent_fd)
        _review_require_stable_staged_namespace(
            trusted_root,
            root_fd,
            root_identity,
            links,
        )
        if recovery_present:
            _fail("REVIEW_PUBLICATION_RECOVERY_PRESENT")
    except BaseException as exc:
        if (
            canonical_proven
            and isinstance(exc, BoundaryViolation)
            and exc.code == "REVIEW_PUBLICATION_RECOVERY_PRESENT"
        ):
            failure_code = exc.code
        elif (
            isinstance(exc, BoundaryViolation)
            and exc.code == "REVIEW_PUBLICATION_IDENTITY_UNCERTAIN"
        ):
            failure_code = exc.code
        elif staging_fd >= 0 and staging_identity is not None:
            if root_identity is None:
                failure_code = "REVIEW_PUBLICATION_IDENTITY_UNCERTAIN"
            else:
                try:
                    failure_code = _review_classify_staged_failure(
                        trusted_root,
                        root_fd,
                        root_identity,
                        links,
                        parent_fd,
                        staging_name,
                        staging_fd,
                        staging_identity,
                        trusted_parent_gid,
                        items,
                        promotion_attempted=promotion_attempted,
                    )
                except BaseException:
                    failure_code = "REVIEW_PUBLICATION_IDENTITY_UNCERTAIN"
        elif staging_namespace_attempted:
            failure_code = "REVIEW_PUBLICATION_IDENTITY_UNCERTAIN"
        elif not isinstance(exc, Exception):
            raise
        elif isinstance(exc, BoundaryViolation):
            failure_code = exc.code
        else:
            failure_code = "PUBLIC_EVIDENCE_SCHEMA_VIOLATION"
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)
    if failure_code is not None:
        raise BoundaryViolation(failure_code) from None
    return {name: output_dir / name for name, _payload in items}


def write_public_bundle(
    payloads: Mapping[str, bytes],
    trusted_root: Path,
    relative_output: Path,
) -> dict[str, Path]:
    items = _validate_public_bundle_payloads(payloads)
    relative_parts = _public_relative_parts(relative_output)
    parent_parts = relative_parts[:-1]
    final_name = relative_parts[-1]
    output_dir = trusted_root.joinpath(*relative_parts)
    descriptors: set[int] = set()
    links: list[tuple[int, str, os.stat_result]] = []
    parent_fd = -1
    staging_fd = -1
    staging_name = f".bundle-{final_name}-{secrets.token_hex(16)}"
    staging_ownership: dict[str, os.stat_result] = {}
    staging_identity: os.stat_result | None = None
    staging_members: dict[str, os.stat_result] = {}
    original: tuple[os.stat_result, dict[str, os.stat_result]] | None = None
    promotion_performed = False
    canonical_committed = False
    transaction_complete = False
    try:
        root_fd, root_identity = _open_verified_public_root(trusted_root)
        descriptors.add(root_fd)
        parent_fd = root_fd
        for part in parent_parts:
            created = False
            try:
                os.mkdir(part, 0o755, dir_fd=parent_fd)
                os.fsync(parent_fd)
                created = True
            except FileExistsError:
                pass
            child_fd, child_identity = _open_verified_public_directory(parent_fd, part)
            descriptors.add(child_fd)
            if created:
                os.fchmod(child_fd, 0o755)
                child_identity = os.fstat(child_fd)
            links.append((parent_fd, part, child_identity))
            parent_fd = child_fd
        _verify_public_directory_chain(links)
        _verify_public_root_link(trusted_root, root_identity)
        original = _snapshot_public_bundle(
            parent_fd,
            final_name,
            tuple(name for name, _payload in items),
            allow_missing=True,
        )
        staging_fd, staging_identity = _create_owned_public_staging(
            parent_fd,
            staging_name,
            descriptors,
            staging_ownership,
        )
        for member_name, payload in items:
            member_fd, created_identity = _create_owned_public_member(
                staging_fd,
                member_name,
                descriptors,
                staging_members,
            )
            try:
                os.fchmod(member_fd, 0o644)
                _write_all_and_fsync(member_fd, payload)
            finally:
                try:
                    recovered = os.fstat(member_fd)
                    if _same_public_object_id(created_identity, recovered):
                        staging_members[member_name] = recovered
                finally:
                    _close_tracked_public_descriptor(descriptors, member_fd)
            observed = os.stat(member_name, dir_fd=staging_fd, follow_symlinks=False)
            if (
                not stat.S_ISREG(observed.st_mode)
                or observed.st_nlink != 1
                or not _same_identity(staging_members[member_name], observed)
            ):
                _fail("PUBLIC_EVIDENCE_SCHEMA_VIOLATION")
        os.fchmod(staging_fd, 0o755)
        staging_identity = os.fstat(staging_fd)
        staging_ownership["directory"] = staging_identity
        staging_link = os.stat(
            staging_name, dir_fd=parent_fd, follow_symlinks=False
        )
        if (
            staging_identity.st_mode & 0o777 != 0o755
            or not _same_identity(staging_identity, staging_link)
        ):
            _fail("PUBLIC_EVIDENCE_SCHEMA_VIOLATION")
        os.fsync(staging_fd)
        staged = _snapshot_public_bundle(
            parent_fd,
            staging_name,
            tuple(name for name, _payload in items),
            allow_missing=False,
        )
        if staged is None or not _same_inode(staging_identity, staged[0]):
            _fail("PUBLIC_EVIDENCE_SCHEMA_VIOLATION")
        if not all(
            name in staged[1] and _same_identity(identity, staged[1][name])
            for name, identity in staging_members.items()
        ):
            _fail("PUBLIC_EVIDENCE_SCHEMA_VIOLATION")
        staging_identity = staged[0]
        staging_members = staged[1]
        os.fsync(parent_fd)
        _verify_public_directory_chain(links)
        _verify_public_root_link(trusted_root, root_identity)
        if original is None:
            _rename_noreplace(parent_fd, staging_name, parent_fd, final_name)
        else:
            current = _snapshot_public_bundle(
                parent_fd,
                final_name,
                tuple(name for name, _payload in items),
                allow_missing=True,
            )
            if (
                current is None
                or not _same_inode(original[0], current[0])
                or set(current[1]) != set(original[1])
                or any(
                    not _same_identity(identity, current[1][name])
                    for name, identity in original[1].items()
                )
            ):
                _fail("PUBLIC_EVIDENCE_SCHEMA_VIOLATION")
            _rename_exchange(parent_fd, staging_name, parent_fd, final_name)
        promotion_performed = True
        if original is not None and not _public_bundle_matches(
            parent_fd,
            staging_name,
            original[0],
            original[1],
        ):
            _fail("PUBLIC_EVIDENCE_SCHEMA_VIOLATION")
        if not _public_bundle_matches(
            parent_fd,
            final_name,
            staging_identity,
            staging_members,
        ):
            _fail("PUBLIC_EVIDENCE_SCHEMA_VIOLATION")
        os.fsync(parent_fd)
        _verify_public_directory_chain(links)
        _verify_public_root_link(trusted_root, root_identity)
        if not _public_bundle_matches(
            parent_fd,
            final_name,
            staging_identity,
            staging_members,
        ):
            _fail("PUBLIC_EVIDENCE_SCHEMA_VIOLATION")
        canonical_committed = True
        if original is not None:
            _cleanup_verified_public_bundle(
                parent_fd,
                staging_name,
                original[0],
                original[1],
            )
        os.fsync(parent_fd)
        _verify_public_directory_chain(links)
        _verify_public_root_link(trusted_root, root_identity)
        if not _public_bundle_matches(
            parent_fd,
            final_name,
            staging_identity,
            staging_members,
        ):
            _fail("PUBLIC_EVIDENCE_SCHEMA_VIOLATION")
        transaction_complete = True
    except BoundaryViolation:
        owned_staging_identity = staging_identity or staging_ownership.get("directory")
        if (
            parent_fd >= 0
            and owned_staging_identity is not None
            and not canonical_committed
        ):
            try:
                promotion_observed = promotion_performed or _public_bundle_matches(
                    parent_fd,
                    final_name,
                    owned_staging_identity,
                    staging_members,
                )
                if promotion_observed:
                    _rollback_public_bundle_promotion(
                        parent_fd,
                        final_name,
                        staging_name,
                        owned_staging_identity,
                        staging_members,
                        original,
                    )
                else:
                    _cleanup_verified_public_bundle(
                        parent_fd,
                        staging_name,
                        owned_staging_identity,
                        staging_members,
                        allow_owned_state_drift=True,
                    )
            except (BoundaryViolation, OSError):
                pass
        raise
    except OSError as exc:
        owned_staging_identity = staging_identity or staging_ownership.get("directory")
        if (
            parent_fd >= 0
            and owned_staging_identity is not None
            and not canonical_committed
        ):
            try:
                promotion_observed = promotion_performed or _public_bundle_matches(
                    parent_fd,
                    final_name,
                    owned_staging_identity,
                    staging_members,
                )
                if promotion_observed:
                    _rollback_public_bundle_promotion(
                        parent_fd,
                        final_name,
                        staging_name,
                        owned_staging_identity,
                        staging_members,
                        original,
                    )
                else:
                    _cleanup_verified_public_bundle(
                        parent_fd,
                        staging_name,
                        owned_staging_identity,
                        staging_members,
                        allow_owned_state_drift=True,
                    )
            except (BoundaryViolation, OSError):
                pass
        raise BoundaryViolation("PUBLIC_EVIDENCE_SCHEMA_VIOLATION") from exc
    finally:
        for descriptor in sorted(descriptors, reverse=True):
            os.close(descriptor)
    if not transaction_complete:
        _fail("PUBLIC_EVIDENCE_SCHEMA_VIOLATION")
    return {name: output_dir / name for name, _payload in items}


def write_public_evidence(
    summary: dict[str, Any], trusted_root: Path, relative_output: Path
) -> dict[str, Path]:
    payloads = {
        "summary.json": canonical_json_bytes(summary) + b"\n",
        "summary.md": _summary_markdown(summary).encode("utf-8"),
        "protocol-manifest.json": canonical_json_bytes(_public_protocol_manifest(summary)) + b"\n",
        "population-seal-attestation.json": canonical_json_bytes(_public_population_seal(summary)) + b"\n",
        "lineage-attestation.json": canonical_json_bytes(_public_lineage_attestation(summary)) + b"\n",
    }
    return write_public_bundle(payloads, trusted_root, relative_output)
