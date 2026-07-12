from __future__ import annotations

import copy
import errno
import hashlib
import inspect
import json
import os
import socket
import stat
import traceback
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import voice2task.clean_evaluation_boundary as boundary
from voice2task.cli import data as data_cli

EXPECTED_BINDINGS = (
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

PARTITIONS = ("compiler_system_evaluation", "model_learning_evaluation")


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _binding(name: str, value: Any) -> dict[str, Any]:
    return {
        "name": name,
        "status": "BOUND",
        "value": value,
        "value_type": "structured" if isinstance(value, (dict, list)) else type(value).__name__,
        "unit": "NOT_APPLICABLE",
        "authority_label": f"reviewed-{name}",
        "authority_sha256": "a" * 64,
        "derivation_method": "DIRECT_REVIEWED_BINDING",
        "derivation_input_sha256": ["b" * 64],
        "applicability": "Applies before clean-family materialization.",
        "access_attestation": {
            "clean_row_access": False,
            "gold_access": False,
            "outcome_access": False,
            "lockbox_row_access": False,
        },
        "review_verdict": "APPROVED",
    }


def _bindings(total: int = 4) -> dict[str, Any]:
    seeds = [11, 17, 23]
    values: dict[str, Any] = {name: f"bound-{name}" for name in EXPECTED_BINDINGS}
    values.update(
        {
            "partition_algorithm": "sha256-partition-by-stratum-v1",
            "partition_seed": "precommitted-seed-v1",
            "strata_definition": ["s1", "s2"],
            "target_total_family_count": total,
            "target_partition_allocation": {
                "s1": {PARTITIONS[0]: 1, PARTITIONS[1]: 1},
                "s2": {PARTITIONS[0]: 1, PARTITIONS[1]: 1},
            },
            "minimum_families_per_partition": 2,
            "compiler_control": {"protocol_id": "compiler-control-v1"},
            "compiler_intervention": {"protocol_id": "compiler-intervention-v1"},
            "model_control": {
                "protocol_id": "model-control-v1",
                "paired_seed_list": seeds,
            },
            "model_training_intervention": {
                "protocol_id": "model-one-intervention-v1",
                "paired_seed_list": seeds,
                "changed_components": ["training_objective"],
            },
            "paired_model_seed_list": seeds,
            "compiler_mde_or_sensitivity_target": "0.05",
            "model_mde_or_sensitivity_target": "0.05",
            "compiler_target_power_or_beta": "0.80",
            "model_target_power_or_beta": "0.80",
            "alpha": "0.05",
        }
    )
    return {
        "schema_version": "clean-evaluation-bindings-v1",
        "bindings": {name: _binding(name, values[name]) for name in EXPECTED_BINDINGS},
    }


def _compiler_card() -> dict[str, Any]:
    return {
        "schema_version": "compiler-power-card-v1",
        "estimand": "compiler_system",
        "planning_mode": "EFFECT_TARGETED",
        "effect_target": "0.05",
        "available_capacity": "NOT_APPLICABLE",
        "paired_record_contrasts": True,
        "family_clustering": True,
        "paired_discordance_sensitivity_grid": ["0.05", "0.10", "0.20"],
        "clean_outcome_used": False,
        "authority_sha256": "c" * 64,
    }


def _model_card() -> dict[str, Any]:
    return {
        "schema_version": "model-power-card-v1",
        "estimand": "model_learning",
        "planning_mode": "CAPACITY_CONSTRAINED",
        "effect_target": "NOT_APPLICABLE",
        "available_capacity": 4,
        "family_by_paired_seed_hierarchy": True,
        "paired_seed_correlation_grid": ["0", "0.25", "0.50"],
        "all_assigned_seed_itt_failure_coding": True,
        "seed_failure_sensitivity_grid": ["0", "0.10"],
        "seed_superpopulation_limitation": "Inference is conditional on the assigned paired seeds.",
        "clean_outcome_used": False,
        "authority_sha256": "d" * 64,
    }


def _records() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for index, stratum in enumerate(("s1", "s1", "s2", "s2"), start=1):
        record = {
            "family_candidate_id": f"family-{index}",
            "source_batch_id": "batch-v1",
            "source_family_key": f"source-key-{index}",
            "stratum": stratum,
            "eligibility": "ELIGIBLE",
            "provenance_class": "independent_blind_frame",
            "ancestry_attestation_sha256": "e" * 64,
        }
        record["unit_hash"] = boundary.frame_unit_hash(record)
        records.append(record)
    return records


def _frame_bytes(records: list[dict[str, Any]]) -> bytes:
    return b"".join(boundary.canonical_json_bytes(record) + b"\n" for record in records)


def _source_contract(frame: bytes) -> dict[str, Any]:
    return {
        "schema_version": "clean-source-contract-v1",
        "authority_label": "independent-source-authority",
        "authority_sha256": "f" * 64,
        "reviewer_label": "independent-source-reviewer",
        "review_sha256": "1" * 64,
        "expected_frame_sha256": _sha(frame),
        "ancestry_attestation_sha256": "e" * 64,
        "permitted_frame_schema": "semantic-family-metadata-frame-v1",
        "allowed_strata": ["s1", "s2"],
        "allowed_provenance_classes": ["independent_blind_frame"],
        "max_frame_bytes": 65536,
        "max_frame_records": 4,
        "natural_asr_claim": False,
        "public_or_lockbox_ancestry_excluded": True,
        "lockbox_attestation_policy": _lockbox_policy(),
    }


def _lockbox_policy() -> dict[str, Any]:
    return {
        "public_lockbox_manifest_sha256": (
            "72471bac59749f3bc9d21d73db47dafe1f160b978f5ac3971434e13527ddedde"
        ),
        "validator_implementation_sha256": "2" * 64,
        "validator_version": "lockbox-lineage-validator-v1",
        "validator_authority_label": "independent-validator",
        "validator_approval_sha256": "3" * 64,
        "reviewer_authority_label": "independent-reviewer",
        "reviewer_approval_sha256": "4" * 64,
    }


def _lockbox_attestation(
    *,
    protocol_sha256: str,
    frame_sha256: str,
    registry_root_sha256: str,
    policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    frozen_policy = policy or _lockbox_policy()
    payload: dict[str, Any] = {
        "schema_version": "sealed-aggregate-lockbox-attestation-v1",
        "attestation_type": "SEALED_AGGREGATE_ATTESTATION_ONLY",
        "protocol_sha256": protocol_sha256,
        "expected_source_frame_sha256": frame_sha256,
        "actual_source_frame_sha256": frame_sha256,
        "family_registry_root_sha256": registry_root_sha256,
        **frozen_policy,
        "comparison_category_counts": {
            "public_train": 0,
            "public_dev": 0,
            "public_test": 0,
            "remediation": 0,
            "challenge": 0,
            "prediction": 0,
            "lockbox_v1": 0,
        },
        "total_overlap_count": 0,
        "row_level_output_count": 0,
    }
    payload["attestation_sha256"] = boundary.attestation_hash(payload)
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_bytes(boundary.canonical_json_bytes(payload) + b"\n")


def _valid_private_inputs(root: Path) -> dict[str, str]:
    root.mkdir(parents=True)
    records = _records()
    frame = _frame_bytes(records)
    bindings = _bindings()
    source_contract = _source_contract(frame)
    compiler = _compiler_card()
    model = _model_card()
    protocol = boundary.freeze_protocol(bindings, source_contract, compiler, model)
    boundary.persist_protocol_manifest(root, protocol)
    parsed = boundary.parse_source_frame(frame, source_contract)
    registry = boundary.build_family_registry(parsed)
    attestation = _lockbox_attestation(
        protocol_sha256=protocol["protocol_sha256"],
        frame_sha256=_sha(frame),
        registry_root_sha256=registry["root_sha256"],
    )
    names = {
        "bindings": "inputs/bindings.json",
        "source_contract": "inputs/source-contract.json",
        "compiler_card": "inputs/compiler-card.json",
        "model_card": "inputs/model-card.json",
        "source_frame": "inputs/source-frame.jsonl",
        "lockbox_attestation": "inputs/lockbox-attestation.json",
        "protocol_sha256": protocol["protocol_sha256"],
    }
    (root / "inputs").mkdir()
    _write_json(root / names["bindings"], bindings)
    _write_json(root / names["source_contract"], source_contract)
    _write_json(root / names["compiler_card"], compiler)
    _write_json(root / names["model_card"], model)
    (root / names["source_frame"]).write_bytes(frame)
    _write_json(root / names["lockbox_attestation"], attestation)
    return names


def _materialize_args(names: dict[str, str]) -> dict[str, str]:
    return {
        "protocol_sha256": names["protocol_sha256"],
        "source_frame": names["source_frame"],
        "lockbox_attestation": names["lockbox_attestation"],
    }


def test_canonical_inventory_and_roots_are_exact() -> None:
    assert boundary.EXECUTION_BINDING_FIELDS == EXPECTED_BINDINGS
    assert boundary.CANONICAL_PRIVATE_ROOT.as_posix() == (
        "data/local-private/clean-compiler-model-evaluation-boundary-v1"
    )
    assert boundary.PUBLIC_REPORT_ROOT.as_posix() == (
        "reports/public-sample/clean-compiler-model-evaluation-boundary-v1"
    )
    assert boundary.PUBLIC_ARTIFACT_FILENAMES == (
        "summary.json",
        "summary.md",
        "protocol-manifest.json",
        "population-seal-attestation.json",
        "lineage-attestation.json",
    )


def test_binding_packet_requires_all_29_typed_reviewed_dossiers() -> None:
    result = boundary.validate_binding_packet(_bindings())
    assert result == {"binding_inventory_count": 29, "bound_binding_count": 29, "unbound_binding_count": 0}


@pytest.mark.parametrize("sentinel", [None, "UNBOUND_BY_DESIGN", "UNBOUND", "TBD", "UNKNOWN", "BLOCKED"])
def test_binding_packet_rejects_missing_alias_unknown_or_placeholder(sentinel: Any) -> None:
    packet = _bindings()
    packet["bindings"]["alpha"]["value"] = sentinel
    with pytest.raises(boundary.BoundaryViolation, match="BINDING_INCOMPLETE_OR_PLACEHOLDER"):
        boundary.validate_binding_packet(packet)


@pytest.mark.parametrize(
    "private_value",
    (
        "/private/source.json",
        "~/private/source.json",
        "C:/private/source.json",
        r"C:\private\source.json",
        "../private/source.json",
        "nested/../../private/source.json",
        "data/local-private/clean/source.json",
    ),
)
def test_binding_packet_recursively_rejects_private_path_values(private_value: str) -> None:
    packet = _bindings()
    packet["bindings"]["acquisition_source"]["value"] = {
        "nested": ["public-label", {"source": private_value}]
    }
    packet["bindings"]["acquisition_source"]["value_type"] = "structured"
    with pytest.raises(boundary.BoundaryViolation, match="BINDING_INCOMPLETE_OR_PLACEHOLDER"):
        boundary.validate_binding_packet(packet)

    packet = _bindings()
    packet["bindings"]["acquisition_source_alias"] = packet["bindings"].pop("acquisition_source")
    with pytest.raises(boundary.BoundaryViolation, match="BINDING_INCOMPLETE_OR_PLACEHOLDER"):
        boundary.validate_binding_packet(packet)


def test_model_arm_requires_one_intervention_and_identical_three_plus_paired_seeds() -> None:
    packet = _bindings()
    packet["bindings"]["model_training_intervention"]["value"]["changed_components"] = ["a", "b"]
    with pytest.raises(boundary.BoundaryViolation, match="BINDING_INCOMPLETE_OR_PLACEHOLDER"):
        boundary.validate_binding_packet(packet)

    packet = _bindings()
    packet["bindings"]["model_control"]["value"]["paired_seed_list"] = [11, 17]
    packet["bindings"]["paired_model_seed_list"]["value"] = [11, 17]
    with pytest.raises(boundary.BoundaryViolation, match="BINDING_INCOMPLETE_OR_PLACEHOLDER"):
        boundary.validate_binding_packet(packet)


@pytest.mark.parametrize(
    "relative_path",
    [
        "",
        "/etc/passwd",
        "../frame.jsonl",
        "inputs/../frame.jsonl",
        r"inputs\frame.jsonl",
        "data/public-samples/frame.jsonl",
        "data/lockbox/lockbox-v1.jsonl",
        "reports/public-sample/frame.jsonl",
        "reports/lockbox-v1/frame.jsonl",
        "adapters/model.bin",
        "checkpoints/model.bin",
        "runs/result.json",
        "logs/private.log",
        ".cache/frame.jsonl",
    ],
)
def test_private_relative_path_policy_rejects_unsafe_or_denied_before_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, relative_path: str
) -> None:
    root = tmp_path / "private"
    root.mkdir()
    reads = 0
    real_read = os.read

    def counted_read(fd: int, size: int) -> bytes:
        nonlocal reads
        reads += 1
        return real_read(fd, size)

    monkeypatch.setattr(os, "read", counted_read)
    with pytest.raises(boundary.BoundaryViolation):
        boundary.verified_read_private_file(root, relative_path, max_bytes=1024)
    assert reads == 0


def test_verified_reader_rejects_final_and_parent_symlinks_and_hardlinks_without_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "private"
    root.mkdir()
    outside = tmp_path / "outside.json"
    outside.write_text("{}", encoding="utf-8")
    (root / "final-link.json").symlink_to(outside)
    (root / "parent-link").symlink_to(tmp_path, target_is_directory=True)
    os.link(outside, root / "hardlink.json")
    reads = 0
    real_read = os.read

    def counted_read(fd: int, size: int) -> bytes:
        nonlocal reads
        reads += 1
        return real_read(fd, size)

    monkeypatch.setattr(os, "read", counted_read)
    for name in ("final-link.json", "parent-link/outside.json", "hardlink.json"):
        with pytest.raises(boundary.BoundaryViolation, match="SOURCE_PATH_UNSAFE_OR_DENIED"):
            boundary.verified_read_private_file(root, name, max_bytes=1024)
    assert reads == 0


def _bind_unix_socket(path: Path) -> socket.socket:
    handle = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    original_directory = Path.cwd()
    try:
        os.chdir(path.parent)
        handle.bind(path.name)
    finally:
        os.chdir(original_directory)
    return handle


@pytest.mark.parametrize("final_kind", ("fifo", "socket"))
def test_verified_reader_rejects_nonregular_final_before_open_or_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    final_kind: str,
) -> None:
    root = tmp_path / "private"
    root.mkdir()
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
                raise AssertionError("nonregular final reached a blocking open")
        return real_open(path, flags, mode, dir_fd=dir_fd)

    def counted_read(fd: int, size: int) -> bytes:
        nonlocal reads
        reads += 1
        return real_read(fd, size)

    monkeypatch.setattr(os, "open", reject_final_open)
    monkeypatch.setattr(os, "read", counted_read)
    try:
        with pytest.raises(boundary.BoundaryViolation) as exc_info:
            boundary.verified_read_private_file(root, final.name, max_bytes=1024)
    finally:
        if socket_handle is not None:
            socket_handle.close()

    assert exc_info.value.code == "SOURCE_PATH_UNSAFE_OR_DENIED"
    assert final_open_attempts == 0
    assert reads == 0
    assert boundary._same_identity(before, final.lstat())


def test_verified_reader_regular_final_open_is_nofollow_and_nonblocking(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "private"
    root.mkdir()
    final = root / "candidate.json"
    final.write_bytes(b"{}")
    final_open_flags: list[int] = []
    real_open = os.open

    def record_open(
        path: str | bytes | os.PathLike[str],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        if path == final.name and dir_fd is not None:
            final_open_flags.append(flags)
        return real_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(os, "open", record_open)

    assert boundary.verified_read_private_file(root, final.name, max_bytes=16) == b"{}"
    assert len(final_open_flags) == 1
    assert final_open_flags[0] & os.O_NOFOLLOW
    assert final_open_flags[0] & os.O_NONBLOCK


def test_verified_reader_reads_one_bounded_snapshot_and_detects_identity_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "private"
    root.mkdir()
    source = root / "source.json"
    source.write_bytes(b"{}")
    reads = 0
    real_read = os.read

    def counted_read(fd: int, size: int) -> bytes:
        nonlocal reads
        reads += 1
        return real_read(fd, size)

    monkeypatch.setattr(os, "read", counted_read)
    assert boundary.verified_read_private_file(root, "source.json", max_bytes=16) == b"{}"
    assert reads == 1

    source.write_bytes(b"x" * 17)
    with pytest.raises(boundary.BoundaryViolation, match="SOURCE_LIMIT_EXCEEDED"):
        boundary.verified_read_private_file(root, "source.json", max_bytes=16)


def test_verified_reader_detects_parent_exchange_and_file_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "private"
    inputs = root / "inputs"
    inputs.mkdir(parents=True)
    source = inputs / "source.json"
    source.write_bytes(b"{}")
    real_read = os.read
    exchanged = False

    def exchange_parent(fd: int, size: int) -> bytes:
        nonlocal exchanged
        payload = real_read(fd, size)
        if not exchanged:
            inputs.rename(root / "inputs-old")
            inputs.mkdir()
            exchanged = True
        return payload

    monkeypatch.setattr(os, "read", exchange_parent)
    with pytest.raises(boundary.BoundaryViolation, match="SOURCE_IDENTITY_DRIFT"):
        boundary.verified_read_private_file(root, "inputs/source.json", max_bytes=16)

    monkeypatch.setattr(os, "read", real_read)
    drift_source = root / "drift.json"
    drift_source.write_bytes(b"{}")
    drifted = False

    def mutate_file(fd: int, size: int) -> bytes:
        nonlocal drifted
        payload = real_read(fd, size)
        if not drifted:
            drift_source.write_bytes(b"{ } ")
            drifted = True
        return payload

    monkeypatch.setattr(os, "read", mutate_file)
    with pytest.raises(boundary.BoundaryViolation, match="SOURCE_IDENTITY_DRIFT"):
        boundary.verified_read_private_file(root, "drift.json", max_bytes=16)


@pytest.mark.parametrize(
    "payload",
    [
        b"\xef\xbb\xbf{}",
        b'{"a":1,"a":2}',
        b'{"value":NaN}',
        b'{"value":Infinity}',
        b"\xff",
    ],
)
def test_strict_json_rejects_bom_duplicates_nonfinite_and_invalid_utf8(payload: bytes) -> None:
    with pytest.raises(boundary.BoundaryViolation, match="STRICT_JSON_INVALID"):
        boundary.strict_json_loads(payload)


@pytest.mark.parametrize(
    "payload",
    (
        b"[" * 2000 + b"]" * 2000,
        b'{"value":' + b"9" * 100_000 + b"}",
    ),
)
def test_strict_json_wraps_parser_recursion_and_integer_limit_errors(payload: bytes) -> None:
    with pytest.raises(boundary.BoundaryViolation, match="STRICT_JSON_INVALID"):
        boundary.strict_json_loads(payload)


def test_source_frame_rejects_crlf_even_when_records_are_otherwise_canonical() -> None:
    records = _records()
    frame = _frame_bytes(records).replace(b"\n", b"\r\n")
    with pytest.raises(boundary.BoundaryViolation, match="STRICT_JSON_INVALID"):
        boundary.parse_source_frame(frame, _source_contract(frame))


def test_power_cards_require_one_mode_and_conservative_dependence_contracts() -> None:
    boundary.validate_power_card(_compiler_card(), "compiler")
    boundary.validate_power_card(_model_card(), "model")
    card = _compiler_card()
    card["available_capacity"] = 4
    with pytest.raises(boundary.BoundaryViolation, match="POWER_ASSUMPTION_UNSUPPORTED"):
        boundary.validate_power_card(card, "compiler")
    card = _model_card()
    card["paired_seed_correlation_grid"] = []
    with pytest.raises(boundary.BoundaryViolation, match="POWER_ASSUMPTION_UNSUPPORTED"):
        boundary.validate_power_card(card, "model")


@pytest.mark.parametrize(
    "bad_grid",
    (
        ["TBD"],
        ["UNKNOWN"],
        ["BLOCKED"],
        ["NaN"],
        ["Infinity"],
        ["01.0"],
        ["1..0"],
        [""],
        ["1.5"],
    ),
)
def test_power_cards_reject_sentinels_and_noncanonical_or_nonfinite_grids(
    bad_grid: list[str],
) -> None:
    compiler = _compiler_card()
    compiler["paired_discordance_sensitivity_grid"] = bad_grid
    with pytest.raises(boundary.BoundaryViolation, match="POWER_ASSUMPTION_UNSUPPORTED"):
        boundary.validate_power_card(compiler, "compiler")

    model = _model_card()
    model["paired_seed_correlation_grid"] = bad_grid
    with pytest.raises(boundary.BoundaryViolation, match="POWER_ASSUMPTION_UNSUPPORTED"):
        boundary.validate_power_card(model, "model")

    model = _model_card()
    model["seed_failure_sensitivity_grid"] = ["-0.1"]
    with pytest.raises(boundary.BoundaryViolation, match="POWER_ASSUMPTION_UNSUPPORTED"):
        boundary.validate_power_card(model, "model")


@pytest.mark.parametrize("kind", ("compiler", "model"))
@pytest.mark.parametrize("bad_effect", ("banana", "0.01..0.05", "0", "-0.1", "1.01"))
def test_effect_targeted_power_cards_require_one_positive_bounded_canonical_decimal(
    kind: str, bad_effect: str
) -> None:
    card = _compiler_card() if kind == "compiler" else _model_card()
    card["planning_mode"] = "EFFECT_TARGETED"
    card["effect_target"] = bad_effect
    card["available_capacity"] = "NOT_APPLICABLE"

    with pytest.raises(boundary.BoundaryViolation, match="POWER_ASSUMPTION_UNSUPPORTED"):
        boundary.validate_power_card(card, kind)


def test_protocol_render_is_deterministic_and_does_not_open_frame(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    frame = _frame_bytes(_records())
    source = _source_contract(frame)
    opens = 0

    def forbidden_open(*args: Any, **kwargs: Any) -> bytes:
        nonlocal opens
        opens += 1
        raise AssertionError("frame opened before protocol freeze")

    monkeypatch.setattr(boundary, "verified_read_private_file", forbidden_open)
    first = boundary.freeze_protocol(_bindings(), source, _compiler_card(), _model_card())
    second = boundary.freeze_protocol(_bindings(), source, _compiler_card(), _model_card())
    assert boundary.canonical_json_bytes(first) == boundary.canonical_json_bytes(second)
    assert first["lifecycle_state"] == "PROTOCOL_FROZEN"
    assert len(first["protocol_sha256"]) == 64
    assert opens == 0


def test_pre_freeze_validation_seam_is_pure_and_preserves_blocker_precedence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    frame = _frame_bytes(_records())

    def forbidden_side_effect(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("pre-freeze validation crossed an I/O boundary")

    monkeypatch.setattr(boundary, "verified_read_private_file", forbidden_side_effect)
    monkeypatch.setattr(boundary, "persist_protocol_manifest", forbidden_side_effect)
    valid_inputs = (
        _bindings(),
        _source_contract(frame),
        _compiler_card(),
        _model_card(),
    )
    input_snapshot = copy.deepcopy(valid_inputs)
    assert boundary.validate_pre_freeze_inputs(*valid_inputs) == {
        "binding_inventory_count": 29,
        "bound_binding_count": 29,
        "unbound_binding_count": 0,
    }
    assert valid_inputs == input_snapshot

    invalid_bindings = _bindings()
    invalid_bindings["bindings"]["alpha"]["value"] = "TBD"
    invalid_source = _source_contract(frame)
    invalid_source["authority_label"] = invalid_source["reviewer_label"]
    invalid_compiler = _compiler_card()
    invalid_compiler["planning_mode"] = "UNKNOWN"
    invalid_model = _model_card()
    invalid_model["planning_mode"] = "UNKNOWN"
    with pytest.raises(
        boundary.BoundaryViolation, match="BINDING_INCOMPLETE_OR_PLACEHOLDER"
    ):
        boundary.validate_pre_freeze_inputs(
            invalid_bindings, invalid_source, invalid_compiler, _model_card()
        )
    with pytest.raises(
        boundary.BoundaryViolation,
        match="ACQUISITION_SOURCE_UNAVAILABLE_OR_UNVERIFIABLE",
    ):
        boundary.validate_pre_freeze_inputs(
            _bindings(), invalid_source, invalid_compiler, _model_card()
        )
    with pytest.raises(boundary.BoundaryViolation, match="POWER_ASSUMPTION_UNSUPPORTED"):
        boundary.validate_pre_freeze_inputs(
            _bindings(), _source_contract(frame), invalid_compiler, _model_card()
        )
    with pytest.raises(boundary.BoundaryViolation, match="POWER_ASSUMPTION_UNSUPPORTED"):
        boundary.validate_pre_freeze_inputs(
            _bindings(), _source_contract(frame), _compiler_card(), invalid_model
        )

    mismatched_strata = _source_contract(frame)
    mismatched_strata["allowed_strata"] = ["s2", "s1"]
    with pytest.raises(
        boundary.BoundaryViolation, match="BINDING_INCOMPLETE_OR_PLACEHOLDER"
    ):
        boundary.validate_pre_freeze_inputs(
            _bindings(), mismatched_strata, _compiler_card(), _model_card()
        )

    mismatched_target_count = _source_contract(frame)
    mismatched_target_count["max_frame_records"] = 5
    with pytest.raises(
        boundary.BoundaryViolation, match="BINDING_INCOMPLETE_OR_PLACEHOLDER"
    ):
        boundary.validate_pre_freeze_inputs(
            _bindings(), mismatched_target_count, _compiler_card(), _model_card()
        )


def test_pre_freeze_preserves_historical_empty_structured_binding_acceptance() -> None:
    frame = _frame_bytes(_records())
    bindings = _bindings()
    bindings["bindings"]["compiler_control"]["value"] = {}
    bindings["bindings"]["compiler_control"]["value_type"] = "structured"

    assert boundary.validate_pre_freeze_inputs(
        bindings,
        _source_contract(frame),
        _compiler_card(),
        _model_card(),
    ) == {
        "binding_inventory_count": 29,
        "bound_binding_count": 29,
        "unbound_binding_count": 0,
    }


def test_pre_freeze_seam_preserves_protocol_bytes_hash_and_single_persist(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "private"
    inputs = root / "inputs"
    inputs.mkdir(parents=True)
    frame = _frame_bytes(_records())
    payloads = {
        "bindings.json": _bindings(),
        "source-contract.json": _source_contract(frame),
        "compiler-card.json": _compiler_card(),
        "model-card.json": _model_card(),
    }
    for name, payload in payloads.items():
        _write_json(inputs / name, payload)

    validation_calls = 0
    persist_calls = 0
    real_validate = boundary.validate_pre_freeze_inputs
    real_persist = boundary.persist_protocol_manifest

    def count_validation(*args: Any, **kwargs: Any) -> dict[str, int]:
        nonlocal validation_calls
        validation_calls += 1
        return real_validate(*args, **kwargs)

    def count_persist(*args: Any, **kwargs: Any) -> str:
        nonlocal persist_calls
        persist_calls += 1
        return real_persist(*args, **kwargs)

    monkeypatch.setattr(boundary, "validate_pre_freeze_inputs", count_validation)
    monkeypatch.setattr(boundary, "persist_protocol_manifest", count_persist)
    manifest = boundary.validate_named_inputs(
        root,
        bindings="inputs/bindings.json",
        source_contract="inputs/source-contract.json",
        compiler_card="inputs/compiler-card.json",
        model_card="inputs/model-card.json",
    )
    canonical = boundary.canonical_json_bytes(manifest)
    persisted = canonical + b"\n"
    manifest_path = root / "protocols" / f"{manifest['protocol_sha256']}.json"

    assert validation_calls == 1
    assert persist_calls == 1
    assert manifest["protocol_sha256"] == (
        "d89abe5d15f99aa4a9a91921a50a9379eced306a7cddffeb448fa46bc4f0d653"
    )
    assert _sha(canonical) == "47ef11dc1d8d5c3f86f42dcdb4c6d51f02cbb71492879bc235abfabfdf68fae3"
    assert _sha(persisted) == "3eab88b78084b6d3fe27ad87124014e2eee41ddbe6b810387fcf0f49bc8bfd22"
    assert manifest_path.read_bytes() == persisted
    assert manifest_path.stat().st_mode & 0o777 == 0o600


def test_protocol_verifier_rejects_in_place_drift() -> None:
    frame = _frame_bytes(_records())
    protocol = boundary.freeze_protocol(_bindings(), _source_contract(frame), _compiler_card(), _model_card())
    drifted = json.loads(json.dumps(protocol))
    drifted["protocol"]["partition_algorithm"] = "changed"
    with pytest.raises(boundary.BoundaryViolation, match="PROTOCOL_FREEZE_HASH_DRIFT"):
        boundary.verify_protocol_manifest(drifted)


def test_protocol_manifest_is_persisted_content_addressed_and_reused_immutably(tmp_path: Path) -> None:
    root = tmp_path / "private"
    root.mkdir()
    frame = _frame_bytes(_records())
    protocol = boundary.freeze_protocol(
        _bindings(), _source_contract(frame), _compiler_card(), _model_card()
    )
    first = boundary.persist_protocol_manifest(root, protocol)
    second = boundary.persist_protocol_manifest(root, protocol)
    expected = root / "protocols" / f"{protocol['protocol_sha256']}.json"
    assert first == second == protocol["protocol_sha256"]
    assert expected.read_bytes() == boundary.canonical_json_bytes(protocol) + b"\n"

    expected.write_bytes(expected.read_bytes() + b" ")
    with pytest.raises(boundary.BoundaryViolation, match="PROTOCOL_FREEZE_HASH_DRIFT"):
        boundary.persist_protocol_manifest(root, protocol)


def test_protocol_loader_rejects_symlink_and_hardlink_before_materialization(tmp_path: Path) -> None:
    root = tmp_path / "private"
    names = _valid_private_inputs(root)
    protocol_path = root / "protocols" / f"{names['protocol_sha256']}.json"
    original = protocol_path.read_bytes()
    protocol_path.unlink()
    outside = tmp_path / "outside-protocol.json"
    outside.write_bytes(original)
    protocol_path.symlink_to(outside)
    with pytest.raises(boundary.BoundaryViolation, match="PROTOCOL_FREEZE_HASH_DRIFT"):
        boundary.materialize_boundary(
            root, generation_id="generation-v1", **_materialize_args(names)
        )
    protocol_path.unlink()
    os.link(outside, protocol_path)
    with pytest.raises(boundary.BoundaryViolation, match="PROTOCOL_FREEZE_HASH_DRIFT"):
        boundary.materialize_boundary(
            root, generation_id="generation-v1", **_materialize_args(names)
        )


def test_source_frame_canonical_unit_hash_and_forbidden_content() -> None:
    records = _records()
    frame = _frame_bytes(records)
    parsed = boundary.parse_source_frame(frame, _source_contract(frame))
    assert parsed == records
    duplicate = [records[0], records[0], records[2], records[3]]
    duplicate_frame = _frame_bytes(duplicate)
    with pytest.raises(boundary.BoundaryViolation, match="FAMILY_REGISTRY_INVALID"):
        boundary.parse_source_frame(duplicate_frame, _source_contract(duplicate_frame))
    compromised = dict(records[0])
    compromised["input_text"] = "private row"
    compromised_frame = boundary.canonical_json_bytes(compromised) + b"\n"
    contract = _source_contract(compromised_frame)
    contract["max_frame_records"] = 1
    with pytest.raises(boundary.BoundaryViolation, match="EARLY_ROW_GOLD_OR_OUTCOME_ACCESS"):
        boundary.parse_source_frame(compromised_frame, contract)


def test_registry_and_partition_are_canonical_exact_and_iteration_independent() -> None:
    records = _records()
    first = boundary.build_family_registry(records)
    second = boundary.build_family_registry(list(reversed(records)))
    assert first["root_sha256"] == second["root_sha256"]
    allocation = _bindings()["bindings"]["target_partition_allocation"]["value"]
    one = boundary.assign_partitions(first["records"], allocation, "precommitted-seed-v1")
    two = boundary.assign_partitions(second["records"], allocation, "precommitted-seed-v1")
    assert one == two
    members = [item for records_ in one["memberships"].values() for item in records_]
    assert len(members) == len(set(members)) == 4
    assert set(one["memberships"]) == set(PARTITIONS)
    assert one["overlap_count"] == 0


@pytest.mark.parametrize("record_count", [3, 5])
def test_exact_capacity_rejects_shortfall_and_oversupply(record_count: int) -> None:
    records = _records()
    while len(records) < record_count:
        index = len(records) + 1
        record = dict(records[-1], family_candidate_id=f"family-{index}", source_family_key=f"key-{index}")
        record["unit_hash"] = boundary.frame_unit_hash({k: v for k, v in record.items() if k != "unit_hash"})
        records.append(record)
    registry = boundary.build_family_registry(records[:record_count])
    allocation = _bindings()["bindings"]["target_partition_allocation"]["value"]
    with pytest.raises(boundary.BoundaryViolation, match="INSUFFICIENT_FAMILY_COUNT_OR_STRATA"):
        boundary.assign_partitions(registry["records"], allocation, "precommitted-seed-v1")


def test_lockbox_attestation_is_complete_aggregate_only_and_has_distinct_approvers() -> None:
    frame = _frame_bytes(_records())
    protocol = boundary.freeze_protocol(_bindings(), _source_contract(frame), _compiler_card(), _model_card())
    registry = boundary.build_family_registry(_records())
    attestation = _lockbox_attestation(
        protocol_sha256=protocol["protocol_sha256"],
        frame_sha256=_sha(frame),
        registry_root_sha256=registry["root_sha256"],
    )
    boundary.validate_lockbox_attestation(
        attestation,
        protocol_sha256=protocol["protocol_sha256"],
        frame_sha256=_sha(frame),
        registry_root_sha256=registry["root_sha256"],
        frozen_policy=_lockbox_policy(),
    )
    attestation["row_level_output_count"] = 1
    with pytest.raises(boundary.BoundaryViolation, match="LINEAGE_OR_LOCKBOX_ATTESTATION_FAILED"):
        boundary.validate_lockbox_attestation(
            attestation,
            protocol_sha256=protocol["protocol_sha256"],
            frame_sha256=_sha(frame),
            registry_root_sha256=registry["root_sha256"],
            frozen_policy=_lockbox_policy(),
        )
    boolean_count = _lockbox_attestation(
        protocol_sha256=protocol["protocol_sha256"],
        frame_sha256=_sha(frame),
        registry_root_sha256=registry["root_sha256"],
    )
    boolean_count["total_overlap_count"] = False
    boolean_count["attestation_sha256"] = boundary.attestation_hash(boolean_count)
    with pytest.raises(boundary.BoundaryViolation, match="LINEAGE_OR_LOCKBOX_ATTESTATION_FAILED"):
        boundary.validate_lockbox_attestation(
            boolean_count,
            protocol_sha256=protocol["protocol_sha256"],
            frame_sha256=_sha(frame),
            registry_root_sha256=registry["root_sha256"],
            frozen_policy=_lockbox_policy(),
        )


def test_lockbox_attestation_cannot_self_select_new_trust_anchors() -> None:
    frame = _frame_bytes(_records())
    contract = _source_contract(frame)
    protocol = boundary.freeze_protocol(_bindings(), contract, _compiler_card(), _model_card())
    registry = boundary.build_family_registry(_records())
    attacker_policy = dict(_lockbox_policy())
    attacker_policy["validator_authority_label"] = "attacker-validator"
    attacker_policy["validator_approval_sha256"] = "9" * 64
    attestation = _lockbox_attestation(
        protocol_sha256=protocol["protocol_sha256"],
        frame_sha256=_sha(frame),
        registry_root_sha256=registry["root_sha256"],
        policy=attacker_policy,
    )
    with pytest.raises(boundary.BoundaryViolation, match="LINEAGE_OR_LOCKBOX_ATTESTATION_FAILED"):
        boundary.validate_lockbox_attestation(
            attestation,
            protocol_sha256=protocol["protocol_sha256"],
            frame_sha256=_sha(frame),
            registry_root_sha256=registry["root_sha256"],
            frozen_policy=contract["lockbox_attestation_policy"],
        )


def test_success_materializes_one_immutable_generation_and_stops_at_s3(tmp_path: Path) -> None:
    root = tmp_path / "private"
    names = _valid_private_inputs(root)
    result = boundary.materialize_boundary(
        root, generation_id="generation-v1", **_materialize_args(names)
    )
    assert result["evidence_status"] == "EVALUATION_BOUNDARY_MATERIALIZED"
    assert result["decision"] == "POPULATION_BOUNDARY_READY_ARM_ARTIFACTS_BLOCKED"
    assert result["current_readiness_state"] == "POPULATION_MATERIALIZED_AND_SEALED"
    assert result["execution_readiness"] is False
    assert result["clean_evaluation_rows_status"] == "NOT_CREATED"
    assert result["arm_artifacts_status"] == "NOT_FROZEN"
    assert result["experiment_preregistration_status"] == "NOT_EXECUTABLE"
    assert result["mutations"]["boundary_materialization"] is True
    assert all(
        not value
        for key, value in result["mutations"].items()
        if key != "boundary_materialization" and not key.startswith("private_")
    )
    assert all(partition["one_look_state"] == "SEALED_NOT_ELIGIBLE" for partition in result["partitions"].values())
    assert all(
        partition["access_count"] == 0 and partition["consumed"] is False
        for partition in result["partitions"].values()
    )
    generation = root / "generations" / "generation-v1"
    assert sorted(path.name for path in generation.iterdir()) == [
        "compiler-system-evaluation.membership.jsonl",
        "family-registry.jsonl",
        "model-learning-evaluation.membership.jsonl",
        "population-seal.json",
    ]
    before = {path.name: path.read_bytes() for path in generation.iterdir()}
    with pytest.raises(boundary.BoundaryViolation, match="ATOMIC_PROMOTION_FAILED"):
        boundary.materialize_boundary(
            root, generation_id="generation-v1", **_materialize_args(names)
        )
    assert {path.name: path.read_bytes() for path in generation.iterdir()} == before
    assert not list((root / "generations").glob(".staging-*"))


def test_materializer_consumes_persisted_protocol_before_frame_and_never_recomputes_or_reads_lockbox_rows(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "private"
    names = _valid_private_inputs(root)
    events: list[str] = []
    real_read = boundary.verified_read_private_file

    def observed_read(private_root: Path, relative_path: str, *, max_bytes: int) -> bytes:
        events.append(f"read:{relative_path}")
        return real_read(private_root, relative_path, max_bytes=max_bytes)

    monkeypatch.setattr(boundary, "verified_read_private_file", observed_read)
    monkeypatch.setattr(
        boundary,
        "freeze_protocol",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("protocol recomputed")),
    )
    boundary.materialize_boundary(
        root, generation_id="generation-v1", **_materialize_args(names)
    )
    protocol_read = f"read:protocols/{names['protocol_sha256']}.json"
    assert events.index(protocol_read) < events.index(f"read:{names['source_frame']}")
    assert events.index(f"read:{names['source_frame']}") < events.index(
        f"read:{names['lockbox_attestation']}"
    )
    assert all("lockbox-v1.jsonl" not in event and "row-failures" not in event for event in events)


def test_exclusive_writer_lock_is_not_removed_by_a_competing_attempt(tmp_path: Path) -> None:
    root = tmp_path / "private"
    names = _valid_private_inputs(root)
    generations = root / "generations"
    generations.mkdir()
    lock = generations / ".materialize.lock"
    lock.write_text("other-writer", encoding="utf-8")
    with pytest.raises(boundary.BoundaryViolation, match="ATOMIC_PROMOTION_FAILED"):
        boundary.materialize_boundary(
            root, generation_id="generation-v1", **_materialize_args(names)
        )
    assert lock.read_text(encoding="utf-8") == "other-writer"
    assert not list(generations.glob(".staging-*"))


def test_kernel_no_replace_promotion_rejects_destination_inserted_during_race(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "private"
    names = _valid_private_inputs(root)
    real_rename = boundary._rename_noreplace
    inserted = False

    def race_rename(src_fd: int, source: str, dst_fd: int, destination: str) -> None:
        nonlocal inserted
        if source.startswith(".staging-") and not inserted:
            final = root / "generations" / destination
            final.mkdir()
            (final / "attacker-marker").write_text("keep", encoding="utf-8")
            inserted = True
        real_rename(src_fd, source, dst_fd, destination)

    monkeypatch.setattr(boundary, "_rename_noreplace", race_rename)
    with pytest.raises(boundary.BoundaryViolation, match="ATOMIC_PROMOTION_FAILED"):
        boundary.materialize_boundary(
            root, generation_id="generation-v1", **_materialize_args(names)
        )
    assert (root / "generations/generation-v1/attacker-marker").read_text() == "keep"


def test_exchanged_lock_identity_is_not_unlinked(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "private"
    names = _valid_private_inputs(root)

    def exchange_lock_then_fail(src_fd: int, source: str, dst_fd: int, destination: str) -> None:
        generations = root / "generations"
        lock = generations / ".materialize.lock"
        lock.rename(generations / ".original-lock")
        lock.write_text("replacement-lock", encoding="utf-8")
        raise boundary.BoundaryViolation("ATOMIC_PROMOTION_FAILED")

    monkeypatch.setattr(boundary, "_rename_noreplace", exchange_lock_then_fail)
    with pytest.raises(boundary.BoundaryViolation, match="ATOMIC_PROMOTION_FAILED"):
        boundary.materialize_boundary(
            root, generation_id="generation-v1", **_materialize_args(names)
        )
    assert (root / "generations/.materialize.lock").read_text() == "replacement-lock"


def test_staging_cleanup_never_follows_exchanged_symlink(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "private"
    names = _valid_private_inputs(root)
    outside = tmp_path / "outside"
    outside.mkdir()
    sentinel = outside / "sentinel"
    sentinel.write_text("keep", encoding="utf-8")

    def exchange_staging_then_fail(src_fd: int, source: str, dst_fd: int, destination: str) -> None:
        staging = root / "generations" / source
        staging.rename(root / "generations/.exchanged-staging")
        staging.symlink_to(outside, target_is_directory=True)
        raise boundary.BoundaryViolation("ATOMIC_PROMOTION_FAILED")

    monkeypatch.setattr(boundary, "_rename_noreplace", exchange_staging_then_fail)
    with pytest.raises(boundary.BoundaryViolation, match="ATOMIC_PROMOTION_FAILED"):
        boundary.materialize_boundary(
            root, generation_id="generation-v1", **_materialize_args(names)
        )
    assert sentinel.read_text(encoding="utf-8") == "keep"
    assert (root / "generations/.staging-generation-v1").is_symlink()


def test_staging_stat_to_open_exchange_never_writes_or_cleans_replacement_victim(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "private"
    names = _valid_private_inputs(root)
    real_open = os.open
    exchanged = False
    victim = root / "generations/.staging-generation-v1/victim.txt"

    def exchange_staging_on_open(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        nonlocal exchanged
        if path == ".staging-generation-v1" and dir_fd is not None and not exchanged:
            staging = root / "generations/.staging-generation-v1"
            staging.rename(root / "generations/.attacker-renamed-original")
            staging.mkdir()
            victim.write_text("survive", encoding="utf-8")
            exchanged = True
        return real_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(os, "open", exchange_staging_on_open)
    with pytest.raises(boundary.BoundaryViolation, match="ATOMIC_PROMOTION_FAILED"):
        boundary.materialize_boundary(
            root, generation_id="generation-v1", **_materialize_args(names)
        )
    assert victim.read_text(encoding="utf-8") == "survive"


def test_parent_exchange_inside_noreplace_removes_published_generation_from_both_parents(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "private"
    names = _valid_private_inputs(root)
    real_rename = boundary._rename_noreplace

    def exchange_parent_then_rename(
        src_fd: int, source: str, dst_fd: int, destination: str
    ) -> None:
        generations = root / "generations"
        generations.rename(root / "generations-old")
        generations.mkdir()
        real_rename(src_fd, source, dst_fd, destination)

    monkeypatch.setattr(boundary, "_rename_noreplace", exchange_parent_then_rename)
    with pytest.raises(boundary.BoundaryViolation, match="ATOMIC_PROMOTION_FAILED"):
        boundary.materialize_boundary(
            root, generation_id="generation-v1", **_materialize_args(names)
        )
    assert not (root / "generations/generation-v1").exists()
    assert not (root / "generations-old/generation-v1").exists()


def test_verify_generation_detects_drift_without_opening_membership_as_public_output(tmp_path: Path) -> None:
    root = tmp_path / "private"
    names = _valid_private_inputs(root)
    result = boundary.materialize_boundary(
        root, generation_id="generation-v1", **_materialize_args(names)
    )
    verified = boundary.verify_generation(
        root,
        "generation-v1",
        expected_population_seal_sha256=result["hashes"]["population_seal_sha256"],
    )
    assert verified["ok"] is True
    registry = root / "generations" / "generation-v1" / "family-registry.jsonl"
    registry.write_bytes(registry.read_bytes() + b"\n")
    with pytest.raises(boundary.BoundaryViolation, match="SEALED_ARTIFACT_DRIFT_OR_MEMBERSHIP_LEAK"):
        boundary.verify_generation(
            root,
            "generation-v1",
            expected_population_seal_sha256=result["hashes"]["population_seal_sha256"],
        )


def test_verify_generation_rejects_coordinated_artifact_and_seal_rewrite_via_external_hash(
    tmp_path: Path,
) -> None:
    root = tmp_path / "private"
    names = _valid_private_inputs(root)
    result = boundary.materialize_boundary(
        root, generation_id="generation-v1", **_materialize_args(names)
    )
    generation = root / "generations/generation-v1"
    registry = generation / "family-registry.jsonl"
    registry.write_bytes(registry.read_bytes() + b"\n")
    seal_path = generation / "population-seal.json"
    seal = json.loads(seal_path.read_text(encoding="utf-8"))
    seal["artifact_sha256"]["family-registry.jsonl"] = _sha(registry.read_bytes())
    seal["family_registry_root_sha256"] = "9" * 64
    seal_path.write_bytes(boundary.canonical_json_bytes(seal) + b"\n")
    with pytest.raises(boundary.BoundaryViolation, match="SEALED_ARTIFACT_DRIFT_OR_MEMBERSHIP_LEAK"):
        boundary.verify_generation(
            root,
            "generation-v1",
            expected_population_seal_sha256=result["hashes"]["population_seal_sha256"],
        )


@pytest.mark.parametrize("mutation", ("boolean_access_count", "source_frame_hash_drift"))
def test_verify_generation_rejects_semantically_invalid_rehashed_seal(
    tmp_path: Path, mutation: str
) -> None:
    root = tmp_path / "private"
    names = _valid_private_inputs(root)
    boundary.materialize_boundary(
        root, generation_id="generation-v1", **_materialize_args(names)
    )
    seal_path = root / "generations/generation-v1/population-seal.json"
    seal = json.loads(seal_path.read_text(encoding="utf-8"))
    if mutation == "boolean_access_count":
        seal["partition_states"][PARTITIONS[0]]["access_count"] = False
    else:
        seal["source_frame_sha256"] = "9" * 64
    seal_payload = boundary.canonical_json_bytes(seal) + b"\n"
    seal_path.write_bytes(seal_payload)
    with pytest.raises(boundary.BoundaryViolation, match="SEALED_ARTIFACT_DRIFT_OR_MEMBERSHIP_LEAK"):
        boundary.verify_generation(
            root,
            "generation-v1",
            expected_population_seal_sha256=_sha(seal_payload),
        )


@pytest.mark.parametrize("extra_kind", ("file", "directory", "symlink"))
def test_verify_generation_rejects_any_unsealed_generation_member(
    tmp_path: Path, extra_kind: str
) -> None:
    root = tmp_path / "private"
    names = _valid_private_inputs(root)
    result = boundary.materialize_boundary(
        root, generation_id="generation-v1", **_materialize_args(names)
    )
    generation = root / "generations/generation-v1"
    extra = generation / "unsealed-membership-leak.jsonl"
    if extra_kind == "file":
        extra.write_text("{}\n", encoding="utf-8")
    elif extra_kind == "directory":
        extra.mkdir()
    else:
        outside = tmp_path / "outside-private-membership.jsonl"
        outside.write_text("{}\n", encoding="utf-8")
        extra.symlink_to(outside)

    with pytest.raises(boundary.BoundaryViolation, match="SEALED_ARTIFACT_DRIFT_OR_MEMBERSHIP_LEAK"):
        boundary.verify_generation(
            root,
            "generation-v1",
            expected_population_seal_sha256=result["hashes"]["population_seal_sha256"],
        )


def test_exact_s0_blocked_truth_surface_and_five_public_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert tuple(inspect.signature(boundary.write_public_evidence).parameters) == (
        "summary",
        "trusted_root",
        "relative_output",
    )
    summary = boundary.s0_blocked_summary()
    assert summary["evidence_status"] == "BLOCKED"
    assert summary["decision"] == "CLEAN_EVALUATION_BOUNDARY_MATERIALIZATION_BLOCKED"
    assert summary["current_readiness_state"] == "DESIGN_ONLY"
    assert summary["maximum_state_this_change"] == "DESIGN_ONLY"
    assert summary["binding_counts"] == {"total": 29, "bound": 0, "unbound": 29}
    assert summary["execution_bindings_status"] == "INCOMPLETE"
    assert summary["protocol_freeze_status"] == "NOT_FROZEN"
    assert summary["clean_population_status"] == "NOT_MATERIALIZED"
    assert summary["boundary_integrity_status"] == "NOT_CREATED"
    assert set(summary["blockers"]) >= {
        "ACQUISITION_SOURCE_UNAVAILABLE_OR_UNVERIFIABLE",
        "BINDING_INCOMPLETE_OR_PLACEHOLDER",
    }
    assert set(summary["partitions"]) == set(PARTITIONS)
    for partition in summary["partitions"].values():
        assert partition == {
            "status": "NOT_MATERIALIZED",
            "one_look_state": "NOT_AVAILABLE",
            "access_count": 0,
            "consumed": False,
        }
    assert set(summary["hashes"].values()) == {"NOT_AVAILABLE"}
    assert all(value is False for value in summary["artifacts"].values())
    assert all(value is False for value in summary["mutations"].values())
    assert all(value is False for value in summary["access_and_runs"].values())
    assert all(value is False for value in summary["claims"].values())
    assert summary["compiler_causal_identification_status"] == "CAUSAL_IDENTIFICATION_BLOCKED"
    assert summary["model_causal_identification_status"] == "CAUSAL_IDENTIFICATION_BLOCKED"
    assert summary["protected_input_baseline"] == {
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
    def forbidden_replace(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("legacy writer must not use ordinary replace")

    monkeypatch.setattr(os, "replace", forbidden_replace)
    monkeypatch.setattr(Path, "replace", forbidden_replace)
    paths = boundary.write_public_evidence(summary, tmp_path, Path("public"))
    assert tuple(paths) == boundary.PUBLIC_ARTIFACT_FILENAMES
    assert sorted(path.name for path in (tmp_path / "public").iterdir()) == sorted(
        boundary.PUBLIC_ARTIFACT_FILENAMES
    )
    first = {name: path.read_bytes() for name, path in paths.items()}
    second_paths = boundary.write_public_evidence(summary, tmp_path, Path("public"))
    second = {name: path.read_bytes() for name, path in second_paths.items()}
    assert first == second
    changed = copy.deepcopy(summary)
    changed["blockers"] = ["PUBLIC_EVIDENCE_SCHEMA_VIOLATION"]
    changed_paths = boundary.write_public_evidence(changed, tmp_path, Path("public"))
    assert json.loads(changed_paths["summary.json"].read_bytes())["blockers"] == [
        "PUBLIC_EVIDENCE_SCHEMA_VIOLATION"
    ]
    assert all(path.stat().st_mode & 0o777 == 0o644 for path in changed_paths.values())
    assert all(path.stat().st_nlink == 1 for path in changed_paths.values())
    assert [path.name for path in tmp_path.iterdir()] == ["public"]
    joined = b"\n".join(first.values())
    for forbidden in (b"data/local-private", b"family-1", b"source-key-1", b"/Users/", b"/mnt/"):
        assert forbidden not in joined


def test_legacy_public_evidence_error_is_fixed_and_hides_private_canary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        boundary,
        "_write_all_and_fsync",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            OSError(errno.EIO, "/private/canary-source-frame")
        ),
    )

    with pytest.raises(boundary.BoundaryViolation) as caught:
        boundary.write_public_evidence(
            boundary.s0_blocked_summary(),
            tmp_path,
            Path("public"),
        )

    assert caught.value.code == "PUBLIC_EVIDENCE_SCHEMA_VIOLATION"
    assert str(caught.value) == "PUBLIC_EVIDENCE_SCHEMA_VIOLATION"
    assert "/private/canary" not in repr(caught.value)


def test_generic_public_bundle_is_ordered_atomic_mode_safe_and_never_uses_replace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trusted_root = tmp_path / "repo"
    trusted_root.mkdir()
    payloads = {"second.json": b"second\n", "first.md": b"first\n"}

    def forbidden_replace(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("ordinary replace must never be used")

    monkeypatch.setattr(os, "replace", forbidden_replace)
    monkeypatch.setattr(Path, "replace", forbidden_replace)
    first = boundary.write_public_bundle(payloads, trusted_root, Path("reports/bundle"))
    second = boundary.write_public_bundle(payloads, trusted_root, Path("reports/bundle"))
    changed = dict(payloads, **{"second.json": b"changed\n"})
    third = boundary.write_public_bundle(changed, trusted_root, Path("reports/bundle"))

    assert tuple(first) == tuple(second) == tuple(third) == tuple(payloads)
    assert {name: path.read_bytes() for name, path in first.items()} == changed
    assert all(path.stat().st_mode & 0o777 == 0o644 for path in first.values())
    assert all(path.stat().st_nlink == 1 for path in first.values())
    assert (trusted_root / "reports").stat().st_mode & 0o777 == 0o755
    assert (trusted_root / "reports/bundle").stat().st_mode & 0o777 == 0o755
    assert not [path for path in (trusted_root / "reports").iterdir() if path.name.startswith(".")]


@pytest.mark.parametrize(
    ("payloads", "relative_output"),
    (
        ({}, Path("reports/bundle")),
        ({"../escape": b"x"}, Path("reports/bundle")),
        ({"nested/name": b"x"}, Path("reports/bundle")),
        ({r"nested\name": b"x"}, Path("reports/bundle")),
        ({"/absolute": b"x"}, Path("reports/bundle")),
        ({".hidden": b"x"}, Path("reports/bundle")),
        ({"tmp-member": b"x"}, Path("reports/bundle")),
        ({"bad\x00name": b"x"}, Path("reports/bundle")),
        ({"bad\nname": b"x"}, Path("reports/bundle")),
        ({"bad name": b"x"}, Path("reports/bundle")),
        ({"backup-member": b"x"}, Path("reports/bundle")),
        ({"staging_member": b"x"}, Path("reports/bundle")),
        ({"temp.member": b"x"}, Path("reports/bundle")),
        ({"unicode-文件": b"x"}, Path("reports/bundle")),
        ({"a" * 129: b"x"}, Path("reports/bundle")),
        ({"member.json": "not-bytes"}, Path("reports/bundle")),
        ({"member.json": b"x"}, Path("../escape")),
        ({"member.json": b"x"}, Path(".hidden/bundle")),
        ({"member.json": b"x"}, Path("reports/.hidden")),
        ({"member.json": b"x"}, Path("reports/bad\x00bundle")),
        ({"member.json": b"x"}, Path("reports/bad bundle")),
        ({"member.json": b"x"}, Path("reports/backup-bundle")),
        ({"member.json": b"x"}, Path("reports") / ("b" * 129)),
    ),
)
def test_generic_public_bundle_rejects_inputs_before_mkdir(
    tmp_path: Path,
    payloads: dict[str, Any],
    relative_output: Path,
) -> None:
    trusted_root = tmp_path / "repo"
    trusted_root.mkdir()

    with pytest.raises(boundary.BoundaryViolation, match="PUBLIC_EVIDENCE_SCHEMA_VIOLATION"):
        boundary.write_public_bundle(payloads, trusted_root, relative_output)
    assert list(trusted_root.iterdir()) == []


@pytest.mark.parametrize("member_kind", ("symlink", "directory", "fifo", "hardlink"))
def test_generic_public_bundle_rejects_unsafe_existing_members_without_target_write(
    tmp_path: Path,
    member_kind: str,
) -> None:
    trusted_root = tmp_path / "repo"
    trusted_root.mkdir()
    payloads = {"member.json": b"safe\n"}
    paths = boundary.write_public_bundle(payloads, trusted_root, Path("reports/bundle"))
    member = paths["member.json"]
    member.unlink()
    outside = tmp_path / "outside"
    outside.write_bytes(b"outside-unchanged\n")
    if member_kind == "symlink":
        member.symlink_to(outside)
    elif member_kind == "directory":
        member.mkdir()
    elif member_kind == "fifo":
        os.mkfifo(member)
    else:
        os.link(outside, member)

    with pytest.raises(boundary.BoundaryViolation, match="PUBLIC_EVIDENCE_SCHEMA_VIOLATION"):
        boundary.write_public_bundle({"member.json": b"changed\n"}, trusted_root, Path("reports/bundle"))
    assert outside.read_bytes() == b"outside-unchanged\n"


def test_generic_public_bundle_competing_absent_destination_is_never_overwritten(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trusted_root = tmp_path / "repo"
    trusted_root.mkdir()
    real_noreplace = boundary._rename_noreplace  # noqa: SLF001

    def compete(
        source_fd: int,
        source_name: str,
        destination_fd: int,
        destination_name: str,
    ) -> None:
        os.mkdir(destination_name, 0o755, dir_fd=destination_fd)
        competitor_fd = os.open(
            destination_name,
            os.O_RDONLY | getattr(os, "O_DIRECTORY", 0),
            dir_fd=destination_fd,
        )
        try:
            marker_fd = os.open(
                "competitor.txt",
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                0o644,
                dir_fd=competitor_fd,
            )
            os.close(marker_fd)
        finally:
            os.close(competitor_fd)
        real_noreplace(source_fd, source_name, destination_fd, destination_name)

    monkeypatch.setattr(boundary, "_rename_noreplace", compete)
    with pytest.raises(boundary.BoundaryViolation, match="PUBLIC_EVIDENCE_SCHEMA_VIOLATION"):
        boundary.write_public_bundle(
            {"member.json": b"ours\n"}, trusted_root, Path("reports/bundle")
        )
    assert (trusted_root / "reports/bundle/competitor.txt").is_file()


def test_generic_public_bundle_exchange_unavailable_keeps_complete_old_bundle(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trusted_root = tmp_path / "repo"
    trusted_root.mkdir()
    relative_output = Path("reports/bundle")
    old = {"one.json": b"old-one\n", "two.json": b"old-two\n"}
    paths = boundary.write_public_bundle(old, trusted_root, relative_output)

    def unavailable(*args: Any, **kwargs: Any) -> Any:
        raise OSError(errno.ENOTSUP, "exchange unavailable")

    monkeypatch.setattr(boundary, "_rename_exchange", unavailable)
    with pytest.raises(boundary.BoundaryViolation, match="PUBLIC_EVIDENCE_SCHEMA_VIOLATION"):
        boundary.write_public_bundle(
            {"one.json": b"new-one\n", "two.json": b"new-two\n"},
            trusted_root,
            relative_output,
        )
    assert {name: path.read_bytes() for name, path in paths.items()} == old


@pytest.mark.parametrize("promotion", ("noreplace", "exchange"))
def test_generic_public_bundle_rolls_back_when_kernel_promotion_succeeds_then_wrapper_raises(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    promotion: str,
) -> None:
    trusted_root = tmp_path / "repo"
    trusted_root.mkdir()
    relative_output = Path("reports/bundle")
    old = {"member.json": b"old\n"}
    if promotion == "exchange":
        boundary.write_public_bundle(old, trusted_root, relative_output)
        real = boundary._rename_exchange  # noqa: SLF001
    else:
        real = boundary._rename_noreplace  # noqa: SLF001
    injected = False

    def succeed_then_raise(*args: Any, **kwargs: Any) -> None:
        nonlocal injected
        real(*args, **kwargs)
        if not injected:
            injected = True
            raise OSError(errno.EIO, "post-syscall wrapper fault")

    monkeypatch.setattr(boundary, f"_rename_{promotion}", succeed_then_raise)
    with pytest.raises(boundary.BoundaryViolation, match="PUBLIC_EVIDENCE_SCHEMA_VIOLATION"):
        boundary.write_public_bundle(
            {"member.json": b"new\n"}, trusted_root, relative_output
        )
    final = trusted_root / relative_output
    if promotion == "exchange":
        assert (final / "member.json").read_bytes() == b"old\n"
    else:
        assert not final.exists()
    reports = trusted_root / "reports"
    assert not [path for path in reports.iterdir() if path.name.startswith(".bundle-")]


@pytest.mark.parametrize("timing", ("before", "after"))
def test_generic_public_bundle_exchange_restores_displaced_competitor_on_race(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    timing: str,
) -> None:
    trusted_root = tmp_path / "repo"
    trusted_root.mkdir()
    relative_output = Path("reports/bundle")
    boundary.write_public_bundle(
        {"member.json": b"old\n"}, trusted_root, relative_output
    )
    parent = trusted_root / "reports"
    final = parent / "bundle"
    real_exchange = boundary._rename_exchange  # noqa: SLF001
    injected = False

    def competitor_directory(path: Path) -> None:
        path.mkdir(mode=0o755)
        (path / "member.json").write_bytes(b"competitor\n")

    def race(
        source_fd: int,
        source_name: str,
        destination_fd: int,
        destination_name: str,
    ) -> None:
        nonlocal injected
        if injected:
            real_exchange(source_fd, source_name, destination_fd, destination_name)
        elif timing == "before":
            injected = True
            final.rename(parent / "original-away")
            competitor_directory(final)
            real_exchange(source_fd, source_name, destination_fd, destination_name)
        else:
            injected = True
            real_exchange(source_fd, source_name, destination_fd, destination_name)
            staging = parent / source_name
            staging.rename(parent / "original-away")
            competitor_directory(staging)

    monkeypatch.setattr(boundary, "_rename_exchange", race)
    with pytest.raises(boundary.BoundaryViolation, match="PUBLIC_EVIDENCE_SCHEMA_VIOLATION"):
        boundary.write_public_bundle(
            {"member.json": b"new\n"}, trusted_root, relative_output
        )
    assert (final / "member.json").read_bytes() == b"competitor\n"
    assert not [path for path in parent.iterdir() if path.name.startswith(".bundle-")]


@pytest.mark.parametrize(
    "helper_name",
    ("_create_owned_public_staging", "_create_owned_public_member"),
)
def test_generic_public_bundle_closes_descriptors_when_create_helper_succeeds_then_raises(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    helper_name: str,
) -> None:
    trusted_root = tmp_path / "repo"
    trusted_root.mkdir()
    real_helper = getattr(boundary, helper_name)
    created_fd = -1

    def succeed_then_raise(*args: Any, **kwargs: Any) -> Any:
        nonlocal created_fd
        created_fd, _identity = real_helper(*args, **kwargs)
        raise OSError(errno.EIO, "post-create wrapper fault")

    monkeypatch.setattr(boundary, helper_name, succeed_then_raise)
    with pytest.raises(boundary.BoundaryViolation, match="PUBLIC_EVIDENCE_SCHEMA_VIOLATION"):
        boundary.write_public_bundle(
            {"member.json": b"ours\n"}, trusted_root, Path("reports/bundle")
        )
    assert created_fd >= 0
    with pytest.raises(OSError):
        os.fstat(created_fd)
    reports = trusted_root / "reports"
    if reports.exists():
        assert not [path for path in reports.iterdir() if path.name.startswith(".bundle-")]


def test_generic_public_bundle_recovers_member_when_os_open_succeeds_then_raises(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trusted_root = tmp_path / "repo"
    trusted_root.mkdir()
    real_open = os.open
    injected = False

    def open_then_close_and_raise(*args: Any, **kwargs: Any) -> int:
        nonlocal injected
        descriptor = real_open(*args, **kwargs)
        path = os.fsdecode(args[0])
        flags = args[1]
        if not injected and path == "member.json" and flags & os.O_EXCL:
            injected = True
            os.close(descriptor)
            raise OSError(errno.EIO, "post-open wrapper fault")
        return descriptor

    monkeypatch.setattr(os, "open", open_then_close_and_raise)
    with pytest.raises(boundary.BoundaryViolation, match="PUBLIC_EVIDENCE_SCHEMA_VIOLATION"):
        boundary.write_public_bundle(
            {"member.json": b"ours\n"}, trusted_root, Path("reports/bundle")
        )
    assert injected is True
    reports = trusted_root / "reports"
    assert not [path for path in reports.iterdir() if path.name.startswith(".")]


def test_generic_public_bundle_recovers_member_after_open_wrapper_and_fstat_fault(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trusted_root = tmp_path / "repo"
    trusted_root.mkdir()
    real_open = os.open
    real_fstat = os.fstat
    open_injected = False
    fstat_injected = False
    recovery_fd = -1
    recovery_fds: list[int] = []

    def open_with_post_create_fault(*args: Any, **kwargs: Any) -> int:
        nonlocal open_injected, recovery_fd
        descriptor = real_open(*args, **kwargs)
        path = os.fsdecode(args[0])
        flags = args[1]
        if not open_injected and path == "member.json" and flags & os.O_EXCL:
            open_injected = True
            os.close(descriptor)
            raise OSError(errno.EIO, "post-open wrapper fault")
        if open_injected and path == "member.json" and flags & os.O_ACCMODE == os.O_RDONLY:
            recovery_fd = descriptor
            recovery_fds.append(descriptor)
        return descriptor

    def fstat_with_recovery_fault(fd: int) -> os.stat_result:
        nonlocal fstat_injected
        result = real_fstat(fd)
        if fd == recovery_fd and not fstat_injected:
            fstat_injected = True
            raise OSError(errno.EIO, "post-fstat wrapper fault")
        return result

    monkeypatch.setattr(os, "open", open_with_post_create_fault)
    monkeypatch.setattr(os, "fstat", fstat_with_recovery_fault)
    with pytest.raises(boundary.BoundaryViolation, match="PUBLIC_EVIDENCE_SCHEMA_VIOLATION"):
        boundary.write_public_bundle(
            {"member.json": b"ours\n"}, trusted_root, Path("reports/bundle")
        )
    assert open_injected is True
    assert fstat_injected is True
    assert len(recovery_fds) >= 2
    for descriptor in recovery_fds:
        with pytest.raises(OSError):
            real_fstat(descriptor)
    reports = trusted_root / "reports"
    assert not [path for path in reports.iterdir() if path.name.startswith(".")]


@pytest.mark.parametrize("existing", (False, True))
@pytest.mark.parametrize("verification_call", (3, 4))
def test_generic_public_bundle_never_succeeds_after_late_canonical_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    existing: bool,
    verification_call: int,
) -> None:
    trusted_root = tmp_path / "repo"
    trusted_root.mkdir()
    relative_output = Path("reports/bundle")
    if existing:
        boundary.write_public_bundle(
            {"member.json": b"old\n"}, trusted_root, relative_output
        )
    real_verify = boundary._verify_public_root_link  # noqa: SLF001
    calls = 0

    def mutate_after_root_verification(*args: Any, **kwargs: Any) -> None:
        nonlocal calls
        real_verify(*args, **kwargs)
        calls += 1
        if calls == verification_call:
            member = trusted_root / relative_output / "member.json"
            member.rename(member.with_name(f"owned-away-{verification_call}.json"))
            member.write_bytes(b"attacker\n")

    monkeypatch.setattr(boundary, "_verify_public_root_link", mutate_after_root_verification)
    with pytest.raises(boundary.BoundaryViolation, match="PUBLIC_EVIDENCE_SCHEMA_VIOLATION"):
        boundary.write_public_bundle(
            {"member.json": b"new\n"}, trusted_root, relative_output
        )
    assert (trusted_root / relative_output / "member.json").read_bytes() == b"attacker\n"


def test_generic_public_bundle_cleanup_restores_replaced_member_without_unlinking_it(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trusted_root = tmp_path / "repo"
    trusted_root.mkdir()
    relative_output = Path("reports/bundle")
    boundary.write_public_bundle(
        {"member.json": b"old\n"}, trusted_root, relative_output
    )
    real_noreplace = boundary._rename_noreplace  # noqa: SLF001
    injected = False

    def replace_member_before_quarantine(
        source_fd: int,
        source_name: str,
        destination_fd: int,
        destination_name: str,
    ) -> None:
        nonlocal injected
        if not injected and destination_name.startswith(".cleanup-member-"):
            injected = True
            os.rename(
                source_name,
                "owned-away.json",
                src_dir_fd=source_fd,
                dst_dir_fd=source_fd,
            )
            attacker_fd = os.open(
                source_name,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                0o644,
                dir_fd=source_fd,
            )
            try:
                os.write(attacker_fd, b"attacker\n")
            finally:
                os.close(attacker_fd)
        real_noreplace(source_fd, source_name, destination_fd, destination_name)

    monkeypatch.setattr(boundary, "_rename_noreplace", replace_member_before_quarantine)
    with pytest.raises(boundary.BoundaryViolation, match="PUBLIC_EVIDENCE_SCHEMA_VIOLATION"):
        boundary.write_public_bundle(
            {"member.json": b"new\n"}, trusted_root, relative_output
        )
    assert (trusted_root / relative_output / "member.json").read_bytes() == b"new\n"
    quarantines = [
        path
        for path in (trusted_root / "reports").iterdir()
        if path.name.startswith(".cleanup-bundle-")
    ]
    assert len(quarantines) == 1
    assert (quarantines[0] / "member.json").read_bytes() == b"attacker\n"
    assert (quarantines[0] / "owned-away.json").read_bytes() == b"old\n"


def test_generic_public_bundle_cleanup_restores_owned_member_when_source_reappears(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trusted_root = tmp_path / "repo"
    trusted_root.mkdir()
    relative_output = Path("reports/bundle")
    boundary.write_public_bundle(
        {"member.json": b"old\n"}, trusted_root, relative_output
    )
    real_noreplace = boundary._rename_noreplace  # noqa: SLF001
    injected = False

    def insert_competitor_after_quarantine(
        source_fd: int,
        source_name: str,
        destination_fd: int,
        destination_name: str,
    ) -> None:
        nonlocal injected
        real_noreplace(source_fd, source_name, destination_fd, destination_name)
        if not injected and destination_name.startswith(".cleanup-member-"):
            injected = True
            attacker_fd = os.open(
                source_name,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                0o644,
                dir_fd=source_fd,
            )
            try:
                os.write(attacker_fd, b"attacker\n")
            finally:
                os.close(attacker_fd)

    monkeypatch.setattr(boundary, "_rename_noreplace", insert_competitor_after_quarantine)
    with pytest.raises(boundary.BoundaryViolation, match="PUBLIC_EVIDENCE_SCHEMA_VIOLATION"):
        boundary.write_public_bundle(
            {"member.json": b"new\n"}, trusted_root, relative_output
        )
    quarantine = next(
        path
        for path in (trusted_root / "reports").iterdir()
        if path.name.startswith(".cleanup-bundle-")
    )
    assert (quarantine / "member.json").read_bytes() == b"old\n"
    competitor = next(
        path for path in quarantine.iterdir() if path.name.startswith(".cleanup-member-")
    )
    assert competitor.read_bytes() == b"attacker\n"


@pytest.mark.parametrize("drift", ("content", "mode"))
def test_generic_public_bundle_cleanup_rejects_same_inode_member_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    drift: str,
) -> None:
    trusted_root = tmp_path / "repo"
    trusted_root.mkdir()
    relative_output = Path("reports/bundle")
    boundary.write_public_bundle(
        {"member.json": b"old\n"}, trusted_root, relative_output
    )
    real_noreplace = boundary._rename_noreplace  # noqa: SLF001
    injected = False

    def drift_member_before_quarantine(
        source_fd: int,
        source_name: str,
        destination_fd: int,
        destination_name: str,
    ) -> None:
        nonlocal injected
        if not injected and destination_name.startswith(".cleanup-member-"):
            injected = True
            member_fd = os.open(source_name, os.O_WRONLY, dir_fd=source_fd)
            try:
                if drift == "content":
                    os.ftruncate(member_fd, 0)
                    os.write(member_fd, b"same-inode-drift\n")
                else:
                    os.fchmod(member_fd, 0o600)
            finally:
                os.close(member_fd)
        real_noreplace(source_fd, source_name, destination_fd, destination_name)

    monkeypatch.setattr(boundary, "_rename_noreplace", drift_member_before_quarantine)
    with pytest.raises(boundary.BoundaryViolation, match="PUBLIC_EVIDENCE_SCHEMA_VIOLATION"):
        boundary.write_public_bundle(
            {"member.json": b"new\n"}, trusted_root, relative_output
        )
    quarantine = next(
        path
        for path in (trusted_root / "reports").iterdir()
        if path.name.startswith(".cleanup-bundle-")
    )
    quarantined_member = quarantine / "member.json"
    assert quarantined_member.exists()
    if drift == "content":
        assert quarantined_member.read_bytes() == b"same-inode-drift\n"
    else:
        assert quarantined_member.stat().st_mode & 0o777 == 0o600


def test_generic_public_bundle_cleanup_rejects_same_inode_drift_before_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trusted_root = tmp_path / "repo"
    trusted_root.mkdir()
    relative_output = Path("reports/bundle")
    boundary.write_public_bundle(
        {"member.json": b"old\n"}, trusted_root, relative_output
    )
    real_cleanup = boundary._cleanup_verified_public_bundle  # noqa: SLF001
    injected = False

    def drift_before_cleanup_snapshot(
        parent_fd: int,
        name: str,
        expected_directory: os.stat_result,
        expected_members: dict[str, os.stat_result],
        *,
        allow_owned_state_drift: bool = False,
    ) -> None:
        nonlocal injected
        if not injected:
            injected = True
            directory_fd = os.open(
                name,
                os.O_RDONLY | getattr(os, "O_DIRECTORY", 0),
                dir_fd=parent_fd,
            )
            try:
                member_fd = os.open("member.json", os.O_WRONLY, dir_fd=directory_fd)
                try:
                    os.ftruncate(member_fd, 0)
                    os.write(member_fd, b"pre-snapshot-drift\n")
                finally:
                    os.close(member_fd)
            finally:
                os.close(directory_fd)
        real_cleanup(
            parent_fd,
            name,
            expected_directory,
            expected_members,
            allow_owned_state_drift=allow_owned_state_drift,
        )

    monkeypatch.setattr(
        boundary, "_cleanup_verified_public_bundle", drift_before_cleanup_snapshot
    )
    with pytest.raises(boundary.BoundaryViolation, match="PUBLIC_EVIDENCE_SCHEMA_VIOLATION"):
        boundary.write_public_bundle(
            {"member.json": b"new\n"}, trusted_root, relative_output
        )
    assert (trusted_root / relative_output / "member.json").read_bytes() == b"new\n"
    displaced = next(
        path
        for path in (trusted_root / "reports").iterdir()
        if path.name.startswith(".bundle-")
    )
    assert (displaced / "member.json").read_bytes() == b"pre-snapshot-drift\n"


def test_generic_public_bundle_cleanup_never_rmdirs_replaced_quarantine_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trusted_root = tmp_path / "repo"
    trusted_root.mkdir()
    relative_output = Path("reports/bundle")
    boundary.write_public_bundle(
        {"member.json": b"old\n"}, trusted_root, relative_output
    )
    real_unlink_directory = boundary._unlink_verified_public_directory_at  # noqa: SLF001
    injected = False

    def replace_directory_before_unlink(
        parent_fd: int,
        name: str,
        expected: os.stat_result,
    ) -> None:
        nonlocal injected
        if not injected:
            injected = True
            parent = trusted_root / "reports"
            quarantine = parent / name
            quarantine.rename(parent / ".owned-cleanup-away")
            quarantine.mkdir(mode=0o700)
            (quarantine / "attacker.txt").write_bytes(b"attacker\n")
        real_unlink_directory(parent_fd, name, expected)

    monkeypatch.setattr(
        boundary,
        "_unlink_verified_public_directory_at",
        replace_directory_before_unlink,
    )
    with pytest.raises(boundary.BoundaryViolation, match="PUBLIC_EVIDENCE_SCHEMA_VIOLATION"):
        boundary.write_public_bundle(
            {"member.json": b"new\n"}, trusted_root, relative_output
        )
    parent = trusted_root / "reports"
    attacker_quarantine = next(
        path for path in parent.iterdir() if path.name.startswith(".cleanup-bundle-")
    )
    assert (attacker_quarantine / "attacker.txt").read_bytes() == b"attacker\n"
    assert (trusted_root / relative_output / "member.json").read_bytes() == b"new\n"


@pytest.mark.parametrize(
    ("platform", "expected"),
    (("darwin", 0x80), ("linux", 0x200), ("linux2", 0x200)),
)
def test_public_cleanup_uses_platform_specific_at_removedir(
    monkeypatch: pytest.MonkeyPatch,
    platform: str,
    expected: int,
) -> None:
    monkeypatch.setattr(boundary.sys, "platform", platform)
    assert boundary._public_at_removedir_flag() == expected  # noqa: SLF001


def test_public_cleanup_has_no_at_removedir_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(boundary.sys, "platform", "unsupported")
    with pytest.raises(OSError) as exc_info:
        boundary._public_at_removedir_flag()  # noqa: SLF001
    assert exc_info.value.errno == errno.ENOTSUP


def test_generic_public_bundle_recovers_staging_when_mkdir_succeeds_then_raises(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trusted_root = tmp_path / "repo"
    trusted_root.mkdir()
    real_mkdir = os.mkdir
    injected = False

    def mkdir_then_raise(*args: Any, **kwargs: Any) -> None:
        nonlocal injected
        real_mkdir(*args, **kwargs)
        path = os.fsdecode(args[0])
        if not injected and path.startswith(".bundle-"):
            injected = True
            raise OSError(errno.EIO, "post-mkdir wrapper fault")

    monkeypatch.setattr(os, "mkdir", mkdir_then_raise)
    with pytest.raises(boundary.BoundaryViolation, match="PUBLIC_EVIDENCE_SCHEMA_VIOLATION"):
        boundary.write_public_bundle(
            {"member.json": b"ours\n"}, trusted_root, Path("reports/bundle")
        )
    reports = trusted_root / "reports"
    assert not [path for path in reports.iterdir() if path.name.startswith(".")]


@pytest.mark.parametrize("fault", ("fchmod", "fstat"))
@pytest.mark.parametrize("target", ("child", "staging", "member"))
def test_generic_public_bundle_stage_faults_close_owned_descriptor_and_cleanup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault: str,
    target: str,
) -> None:
    trusted_root = tmp_path / "repo"
    trusted_root.mkdir()
    tracked_fd = -1
    injected = False
    real_open_directory = boundary._open_verified_public_directory  # noqa: SLF001
    real_create_member = boundary._create_owned_public_member  # noqa: SLF001
    real_fchmod = os.fchmod
    real_fstat = os.fstat

    def track_directory(*args: Any, **kwargs: Any) -> tuple[int, os.stat_result]:
        nonlocal tracked_fd
        result = real_open_directory(*args, **kwargs)
        name = args[1]
        if target == "child" and name == "reports":
            tracked_fd = result[0]
        elif target == "staging" and name.startswith(".bundle-"):
            tracked_fd = result[0]
        return result

    def track_member(*args: Any, **kwargs: Any) -> tuple[int, os.stat_result]:
        nonlocal tracked_fd
        result = real_create_member(*args, **kwargs)
        if target == "member":
            tracked_fd = result[0]
        return result

    def fchmod_then_raise(fd: int, mode: int) -> None:
        nonlocal injected
        real_fchmod(fd, mode)
        if fault == "fchmod" and fd == tracked_fd and not injected:
            injected = True
            raise OSError(errno.EIO, "post-fchmod wrapper fault")

    def fstat_then_raise(fd: int) -> os.stat_result:
        nonlocal injected
        result = real_fstat(fd)
        if fault == "fstat" and fd == tracked_fd and not injected:
            injected = True
            raise OSError(errno.EIO, "post-fstat wrapper fault")
        return result

    monkeypatch.setattr(boundary, "_open_verified_public_directory", track_directory)
    monkeypatch.setattr(boundary, "_create_owned_public_member", track_member)
    monkeypatch.setattr(os, "fchmod", fchmod_then_raise)
    monkeypatch.setattr(os, "fstat", fstat_then_raise)
    with pytest.raises(boundary.BoundaryViolation, match="PUBLIC_EVIDENCE_SCHEMA_VIOLATION"):
        boundary.write_public_bundle(
            {"member.json": b"ours\n"}, trusted_root, Path("reports/bundle")
        )
    assert injected is True
    assert tracked_fd >= 0
    with pytest.raises(OSError):
        real_fstat(tracked_fd)
    reports = trusted_root / "reports"
    assert not (reports / "bundle").exists()
    assert not [path for path in reports.iterdir() if path.name.startswith(".")]


@pytest.mark.parametrize("fault", ("write", "short-write", "fsync"))
def test_generic_public_bundle_precommit_faults_leave_no_partial_canonical(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault: str,
) -> None:
    trusted_root = tmp_path / "repo"
    trusted_root.mkdir()
    if fault == "write":
        monkeypatch.setattr(
            boundary,
            "_write_all_and_fsync",
            lambda *args, **kwargs: (_ for _ in ()).throw(OSError("write fault")),
        )
    elif fault == "short-write":
        monkeypatch.setattr(os, "write", lambda *args, **kwargs: 0)
    else:
        monkeypatch.setattr(
            os,
            "fsync",
            lambda *args, **kwargs: (_ for _ in ()).throw(OSError("fsync fault")),
        )

    with pytest.raises(boundary.BoundaryViolation, match="PUBLIC_EVIDENCE_SCHEMA_VIOLATION"):
        boundary.write_public_bundle(
            {"one.json": b"one\n", "two.json": b"two\n"},
            trusted_root,
            Path("reports/bundle"),
        )
    assert not (trusted_root / "reports/bundle").exists()
    reports = trusted_root / "reports"
    if reports.exists():
        assert not [path for path in reports.iterdir() if path.name.startswith(".")]


@pytest.mark.parametrize("final_kind", ("symlink", "file"))
def test_generic_public_bundle_rejects_unsafe_final_bundle_without_outside_write(
    tmp_path: Path,
    final_kind: str,
) -> None:
    trusted_root = tmp_path / "repo"
    reports = trusted_root / "reports"
    reports.mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.write_bytes(b"outside\n")
    final = reports / "bundle"
    if final_kind == "symlink":
        final.symlink_to(tmp_path, target_is_directory=True)
    else:
        final.write_bytes(b"not-a-directory\n")

    with pytest.raises(boundary.BoundaryViolation, match="PUBLIC_EVIDENCE_SCHEMA_VIOLATION"):
        boundary.write_public_bundle(
            {"member.json": b"ours\n"}, trusted_root, Path("reports/bundle")
        )
    assert outside.read_bytes() == b"outside\n"


def test_generic_public_bundle_rejects_symlinked_trusted_root(
    tmp_path: Path,
) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    trusted_root = tmp_path / "repo"
    trusted_root.symlink_to(outside, target_is_directory=True)

    with pytest.raises(boundary.BoundaryViolation, match="PUBLIC_EVIDENCE_SCHEMA_VIOLATION"):
        boundary.write_public_bundle(
            {"member.json": b"ours\n"}, trusted_root, Path("reports/bundle")
        )
    assert list(outside.iterdir()) == []


def test_generic_public_bundle_repairs_missing_members_but_rejects_extras(
    tmp_path: Path,
) -> None:
    trusted_root = tmp_path / "repo"
    trusted_root.mkdir()
    relative_output = Path("reports/bundle")
    payloads = {"one.json": b"one\n", "two.json": b"two\n"}
    paths = boundary.write_public_bundle(payloads, trusted_root, relative_output)
    paths["two.json"].unlink()
    repaired = boundary.write_public_bundle(payloads, trusted_root, relative_output)
    assert {name: path.read_bytes() for name, path in repaired.items()} == payloads

    extra = trusted_root / relative_output / "extra.json"
    extra.write_bytes(b"extra\n")
    with pytest.raises(boundary.BoundaryViolation, match="PUBLIC_EVIDENCE_SCHEMA_VIOLATION"):
        boundary.write_public_bundle(payloads, trusted_root, relative_output)
    assert extra.read_bytes() == b"extra\n"


def test_generic_public_bundle_postcommit_cleanup_fault_keeps_complete_new_canonical(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trusted_root = tmp_path / "repo"
    trusted_root.mkdir()
    relative_output = Path("reports/bundle")
    boundary.write_public_bundle(
        {"one.json": b"old-one\n", "two.json": b"old-two\n"},
        trusted_root,
        relative_output,
    )
    real_unlinkat = boundary._unlinkat_public  # noqa: SLF001
    injected = False

    def cleanup_fault(
        directory_fd: int,
        name: str,
        flags: int = 0,
    ) -> None:
        nonlocal injected
        if not injected and name.startswith(".cleanup-member-") and flags == 0:
            injected = True
            raise OSError(errno.EIO, "cleanup fault")
        real_unlinkat(directory_fd, name, flags)

    monkeypatch.setattr(boundary, "_unlinkat_public", cleanup_fault)
    new = {"one.json": b"new-one\n", "two.json": b"new-two\n"}
    with pytest.raises(boundary.BoundaryViolation, match="PUBLIC_EVIDENCE_SCHEMA_VIOLATION"):
        boundary.write_public_bundle(new, trusted_root, relative_output)
    final = trusted_root / relative_output
    assert {name: (final / name).read_bytes() for name in new} == new
    siblings = [
        path
        for path in final.parent.iterdir()
        if path.name.startswith(".cleanup-bundle-")
    ]
    assert len(siblings) == 1
    assert not [path for path in final.parent.iterdir() if path.name.startswith(".bundle-")]


def test_generic_public_bundle_fsyncs_files_and_directories_before_and_after_promotion(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trusted_root = tmp_path / "repo"
    trusted_root.mkdir()
    events: list[str] = []
    real_write = boundary._write_all_and_fsync  # noqa: SLF001
    real_fsync = os.fsync
    real_promote = boundary._rename_noreplace  # noqa: SLF001

    def record_write(fd: int, payload: bytes) -> None:
        real_write(fd, payload)
        events.append("file-fsynced")

    def record_fsync(fd: int) -> None:
        real_fsync(fd)
        events.append("directory-fsync")

    def record_promote(*args: Any, **kwargs: Any) -> None:
        assert events.count("file-fsynced") == 2
        assert "directory-fsync" in events
        events.append("promotion")
        real_promote(*args, **kwargs)

    monkeypatch.setattr(boundary, "_write_all_and_fsync", record_write)
    monkeypatch.setattr(os, "fsync", record_fsync)
    monkeypatch.setattr(boundary, "_rename_noreplace", record_promote)
    boundary.write_public_bundle(
        {"one.json": b"one\n", "two.json": b"two\n"},
        trusted_root,
        Path("reports/bundle"),
    )
    promotion_index = events.index("promotion")
    assert "directory-fsync" in events[promotion_index + 1 :]


def test_generic_public_bundle_detects_trusted_root_stat_open_exchange(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trusted_root = tmp_path / "repo"
    trusted_root.mkdir()
    real_open = os.open
    exchanged = False

    def exchange_root_on_open(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        nonlocal exchanged
        if not exchanged and dir_fd is None and os.fspath(path) == os.fspath(trusted_root):
            trusted_root.rename(tmp_path / "repo-old")
            trusted_root.mkdir()
            exchanged = True
        return real_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(os, "open", exchange_root_on_open)
    with pytest.raises(boundary.BoundaryViolation, match="PUBLIC_EVIDENCE_SCHEMA_VIOLATION"):
        boundary.write_public_bundle(
            {"member.json": b"ours\n"}, trusted_root, Path("reports/bundle")
        )
    assert list(trusted_root.iterdir()) == []
    assert list((tmp_path / "repo-old").iterdir()) == []


@pytest.mark.parametrize("exchange_target", ("final", "member"))
def test_generic_public_bundle_detects_existing_final_or_member_stat_open_exchange(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    exchange_target: str,
) -> None:
    trusted_root = tmp_path / "repo"
    trusted_root.mkdir()
    relative_output = Path("reports/bundle")
    boundary.write_public_bundle(
        {"member.json": b"old\n"}, trusted_root, relative_output
    )
    final = trusted_root / relative_output
    real_open = os.open
    exchanged = False

    def exchange_on_open(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        nonlocal exchanged
        raw = os.fsdecode(path)
        read_only = flags & os.O_ACCMODE == os.O_RDONLY
        if not exchanged and dir_fd is not None and read_only:
            if exchange_target == "final" and raw == "bundle":
                final.rename(final.parent / "bundle-old")
                final.mkdir()
                (final / "member.json").write_bytes(b"competitor\n")
                exchanged = True
            elif exchange_target == "member" and raw == "member.json":
                member = final / "member.json"
                member.rename(final / "member-old.json")
                member.write_bytes(b"competitor\n")
                exchanged = True
        return real_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(os, "open", exchange_on_open)
    with pytest.raises(boundary.BoundaryViolation, match="PUBLIC_EVIDENCE_SCHEMA_VIOLATION"):
        boundary.write_public_bundle(
            {"member.json": b"new\n"}, trusted_root, relative_output
        )
    assert (final / "member.json").read_bytes() == b"competitor\n"


def test_generic_public_bundle_cleanup_never_deletes_exchanged_attacker_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trusted_root = tmp_path / "repo"
    trusted_root.mkdir()
    real_write = boundary._write_all_and_fsync  # noqa: SLF001
    injected = False
    attacker_name: str | None = None

    def exchange_staging_then_fail(fd: int, payload: bytes) -> None:
        nonlocal injected, attacker_name
        real_write(fd, payload)
        if not injected:
            reports = trusted_root / "reports"
            staging = next(path for path in reports.iterdir() if path.name.startswith(".bundle-"))
            attacker_name = staging.name
            staging.rename(reports / ".owned-away")
            staging.mkdir()
            (staging / "attacker.txt").write_bytes(b"attacker-unchanged\n")
            injected = True
            raise OSError(errno.EIO, "post-exchange write fault")

    monkeypatch.setattr(boundary, "_write_all_and_fsync", exchange_staging_then_fail)
    with pytest.raises(boundary.BoundaryViolation, match="PUBLIC_EVIDENCE_SCHEMA_VIOLATION"):
        boundary.write_public_bundle(
            {"member.json": b"ours\n"}, trusted_root, Path("reports/bundle")
        )
    assert attacker_name is not None
    attacker = trusted_root / "reports" / attacker_name
    assert (attacker / "attacker.txt").read_bytes() == b"attacker-unchanged\n"


@pytest.mark.parametrize("final_kind", ("symlink", "directory"))
def test_public_evidence_writer_rejects_preexisting_symlink_or_nonregular_final_without_target_write(
    tmp_path: Path, final_kind: str
) -> None:
    output = tmp_path / "public"
    output.mkdir()
    outside = tmp_path / "outside"
    outside.write_text("unchanged", encoding="utf-8")
    final = output / "summary.json"
    if final_kind == "symlink":
        final.symlink_to(outside)
    else:
        final.mkdir()
    with pytest.raises(boundary.BoundaryViolation, match="PUBLIC_EVIDENCE_SCHEMA_VIOLATION"):
        boundary.write_public_evidence(boundary.s0_blocked_summary(), tmp_path, Path("public"))
    assert outside.read_text(encoding="utf-8") == "unchanged"


def test_public_evidence_writer_rejects_symlinked_ancestor_without_writing_outside(
    tmp_path: Path,
) -> None:
    trusted_root = tmp_path / "repo"
    trusted_root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (trusted_root / "reports").symlink_to(outside, target_is_directory=True)

    with pytest.raises(boundary.BoundaryViolation, match="PUBLIC_EVIDENCE_SCHEMA_VIOLATION"):
        boundary.write_public_evidence(
            boundary.s0_blocked_summary(),
            trusted_root,
            Path("reports/public-sample/clean-boundary"),
        )
    assert list(outside.iterdir()) == []


def test_public_bundle_rolls_back_absent_promotion_after_parent_exchange(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    trusted_root = tmp_path / "repo"
    trusted_root.mkdir()
    relative_output = Path("reports/public-sample/clean-boundary")
    outside = tmp_path / "outside"
    outside.mkdir()
    sentinel = outside / "sentinel.txt"
    sentinel.write_text("unchanged", encoding="utf-8")
    real_noreplace = boundary._rename_noreplace  # noqa: SLF001
    exchanged = False

    def exchange_parent_before_promotion(
        source_fd: int,
        source_name: str,
        destination_fd: int,
        destination_name: str,
    ) -> None:
        nonlocal exchanged
        if not exchanged:
            reports = trusted_root / "reports"
            reports.rename(trusted_root / "reports-old")
            reports.mkdir()
            exchanged = True
        real_noreplace(source_fd, source_name, destination_fd, destination_name)

    monkeypatch.setattr(boundary, "_rename_noreplace", exchange_parent_before_promotion)
    with pytest.raises(boundary.BoundaryViolation, match="PUBLIC_EVIDENCE_SCHEMA_VIOLATION"):
        boundary.write_public_bundle(
            {"summary.json": b"new\n"}, trusted_root, relative_output
        )

    old_output = trusted_root / "reports-old/public-sample/clean-boundary"
    assert not old_output.exists()
    assert list((trusted_root / "reports").iterdir()) == []
    assert sentinel.read_text(encoding="utf-8") == "unchanged"


REVIEW_BUNDLE_FILENAMES = (
    "binding-catalog.json",
    "review-pack.schema.json",
    "review-pack.template.json",
    "review-checklist.md",
    "summary.json",
    "summary.md",
    "manifest.json",
)


def _review_bundle_payloads() -> dict[str, bytes]:
    return {name: f"payload:{name}\n".encode() for name in REVIEW_BUNDLE_FILENAMES}


def _review_publication_root(tmp_path: Path) -> tuple[Path, Path]:
    trusted_root = tmp_path / "repo"
    fixed_parent = trusted_root / "reports/public-sample"
    fixed_parent.mkdir(parents=True, exist_ok=True)
    for path in (trusted_root, trusted_root / "reports", fixed_parent):
        path.chmod(0o755)
    return trusted_root, fixed_parent


def _review_tree_state(root: Path) -> dict[str, tuple[Any, ...]]:
    state: dict[str, tuple[Any, ...]] = {}
    for path in (root, *sorted(root.rglob("*"))):
        relative = "." if path == root else path.relative_to(root).as_posix()
        observed = path.lstat()
        metadata = (
            observed.st_dev,
            observed.st_ino,
            stat.S_IFMT(observed.st_mode),
            observed.st_mode & 0o7777,
            observed.st_uid,
            observed.st_gid,
            observed.st_nlink,
            observed.st_size,
            observed.st_mtime_ns,
            observed.st_ctime_ns,
        )
        content = path.read_bytes() if stat.S_ISREG(observed.st_mode) else None
        state[relative] = (*metadata, content)
    return state


def _forbid_review_destructive_or_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("review publication used a destructive or fallback path")

    for owner, name in (
        (boundary, "_rename_exchange"),
        (boundary, "_unlinkat_public"),
        (boundary, "_cleanup_verified_public_bundle"),
        (os, "rmdir"),
        (os, "rename"),
        (os, "replace"),
        (Path, "rename"),
        (Path, "replace"),
    ):
        monkeypatch.setattr(owner, name, forbidden)


def _assert_sanitized_publication_error(
    exc: boundary.BoundaryViolation,
    expected_code: str,
    canary: str,
) -> None:
    assert exc.code == expected_code
    assert exc.__context__ is None
    assert exc.__cause__ is None
    rendered = "".join(
        traceback.format_exception(type(exc), exc, exc.__traceback__)
    ) + repr(exc)
    for forbidden in (canary, "/private", "OSError"):
        assert forbidden not in rendered


@pytest.mark.parametrize(
    "unsafe_part",
    (
        "trusted-root-symlink",
        "trusted-root-nonregular",
        "trusted-root-unsafe",
        "ancestor-symlink",
        "ancestor-nonregular",
        "ancestor-unsafe",
        "fixed-parent-symlink",
        "fixed-parent-nonregular",
    ),
)
def test_review_publication_rejects_unsafe_redirected_or_nonregular_namespace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    unsafe_part: str,
) -> None:
    trusted_root = tmp_path / "repo"
    outside = tmp_path / "outside"
    outside.mkdir(mode=0o755)
    (outside / "sentinel").write_bytes(b"outside-unchanged\n")

    if unsafe_part == "trusted-root-symlink":
        real_root = tmp_path / "real-root"
        (real_root / "reports/public-sample").mkdir(parents=True)
        trusted_root.symlink_to(real_root, target_is_directory=True)
    elif unsafe_part == "trusted-root-nonregular":
        trusted_root.write_bytes(b"not-a-directory\n")
    else:
        trusted_root.mkdir(mode=0o755)
        if unsafe_part == "ancestor-symlink":
            (outside / "public-sample").mkdir()
            (trusted_root / "reports").symlink_to(outside, target_is_directory=True)
        elif unsafe_part == "ancestor-nonregular":
            (trusted_root / "reports").write_bytes(b"not-a-directory\n")
        else:
            reports = trusted_root / "reports"
            reports.mkdir(mode=0o755)
            if unsafe_part == "trusted-root-unsafe":
                (reports / "public-sample").mkdir()
                trusted_root.chmod(0o775)
            elif unsafe_part == "ancestor-unsafe":
                (reports / "public-sample").mkdir()
                reports.chmod(0o775)
            elif unsafe_part == "fixed-parent-symlink":
                (reports / "public-sample").symlink_to(
                    outside,
                    target_is_directory=True,
                )
            else:
                (reports / "public-sample").write_bytes(b"not-a-directory\n")

    before = _review_tree_state(tmp_path)
    _forbid_review_destructive_or_fallback(monkeypatch)

    with pytest.raises(
        boundary.BoundaryViolation,
        match="PUBLIC_EVIDENCE_SCHEMA_VIOLATION",
    ):
        boundary.write_review_public_bundle(_review_bundle_payloads(), trusted_root)

    assert _review_tree_state(tmp_path) == before


@pytest.mark.parametrize("final_kind", ("symlink", "nonregular"))
def test_review_publication_rejects_redirected_or_nonregular_final_without_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    final_kind: str,
) -> None:
    trusted_root, fixed_parent = _review_publication_root(tmp_path)
    final = trusted_root / boundary.REVIEW_PUBLIC_BUNDLE_ROOT
    outside = tmp_path / "outside-final"
    outside.mkdir()
    (outside / "sentinel").write_bytes(b"outside-unchanged\n")
    if final_kind == "symlink":
        final.symlink_to(outside, target_is_directory=True)
    else:
        final.write_bytes(b"not-a-directory\n")
    before = _review_tree_state(tmp_path)
    _forbid_review_destructive_or_fallback(monkeypatch)
    monkeypatch.setattr(
        boundary.secrets,
        "token_hex",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("unsafe final must fail before staging")
        ),
    )

    with pytest.raises(
        boundary.BoundaryViolation,
        match="PUBLIC_EVIDENCE_SCHEMA_VIOLATION",
    ):
        boundary.write_review_public_bundle(_review_bundle_payloads(), trusted_root)

    assert _review_tree_state(tmp_path) == before
    assert not [
        path
        for path in fixed_parent.iterdir()
        if path.name.startswith(boundary.REVIEW_PUBLIC_RECOVERY_PREFIX)
    ]


def test_review_publication_rejects_member_identity_exchange_during_bounded_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trusted_root, fixed_parent = _review_publication_root(tmp_path)
    payloads = _review_bundle_payloads()
    paths = boundary.write_review_public_bundle(payloads, trusted_root)
    target_name = REVIEW_BUNDLE_FILENAMES[0]
    target = paths[target_name]
    displaced = tmp_path / "displaced-member"
    real_bounded_read = boundary._review_bounded_read
    real_rename = os.rename
    exchanged = False

    def exchange_then_read(descriptor: int, expected_length: int) -> bytes:
        nonlocal exchanged
        if not exchanged:
            exchanged = True
            real_rename(target, displaced)
            target.write_bytes(payloads[target_name])
            target.chmod(0o644)
        return real_bounded_read(descriptor, expected_length)

    monkeypatch.setattr(boundary, "_review_bounded_read", exchange_then_read)
    _forbid_review_destructive_or_fallback(monkeypatch)
    monkeypatch.setattr(
        boundary.secrets,
        "token_hex",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("identity drift must fail before staging")
        ),
    )

    with pytest.raises(
        boundary.BoundaryViolation,
        match="PUBLIC_EVIDENCE_SCHEMA_VIOLATION",
    ):
        boundary.write_review_public_bundle(payloads, trusted_root)

    assert exchanged is True
    assert displaced.read_bytes() == payloads[target_name]
    assert target.read_bytes() == payloads[target_name]
    assert not [
        path
        for path in fixed_parent.iterdir()
        if path.name.startswith(boundary.REVIEW_PUBLIC_RECOVERY_PREFIX)
    ]


@pytest.mark.parametrize(
    ("platform", "symbol", "expected"),
    (
        ("darwin", "renameatx_np", True),
        ("darwin", "renameat2", False),
        ("linux", "renameat2", True),
        ("linux2", "renameat2", True),
        ("linux", "renameatx_np", False),
        ("freebsd", "renameat2", False),
    ),
)
def test_review_noreplace_preflight_is_platform_and_symbol_specific(
    monkeypatch: pytest.MonkeyPatch,
    platform: str,
    symbol: str,
    expected: bool,
) -> None:
    library = SimpleNamespace(**{symbol: object()})
    monkeypatch.setattr(boundary.sys, "platform", platform)
    monkeypatch.setattr(boundary.ctypes, "CDLL", lambda *args, **kwargs: library)

    assert boundary._review_noreplace_available() is expected


def test_review_noreplace_preflight_rejects_missing_implementation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        boundary.ctypes,
        "CDLL",
        lambda *args, **kwargs: (_ for _ in ()).throw(OSError("unavailable")),
    )

    assert boundary._review_noreplace_available() is False


@pytest.mark.parametrize(
    ("platform", "symbol", "flag"),
    (("darwin", "renameatx_np", 0x00000004), ("linux", "renameat2", 1)),
)
def test_noreplace_dispatch_uses_platform_primitive_and_exact_flag(
    monkeypatch: pytest.MonkeyPatch,
    platform: str,
    symbol: str,
    flag: int,
) -> None:
    class FakeFunction:
        def __init__(self) -> None:
            self.calls: list[tuple[Any, ...]] = []
            self.argtypes: list[Any] = []
            self.restype: Any = None

        def __call__(self, *args: Any) -> int:
            self.calls.append(args)
            return 0

    function = FakeFunction()
    library = SimpleNamespace(**{symbol: function})
    monkeypatch.setattr(boundary.sys, "platform", platform)
    monkeypatch.setattr(boundary.ctypes, "CDLL", lambda *args, **kwargs: library)

    boundary._rename_noreplace(11, "source", 22, "destination")

    assert function.calls == [(11, b"source", 22, b"destination", flag)]


def test_review_file_signature_excludes_only_atime() -> None:
    baseline = {
        "st_dev": 1,
        "st_ino": 2,
        "st_mode": stat.S_IFREG | 0o644,
        "st_uid": 3,
        "st_gid": 4,
        "st_nlink": 1,
        "st_size": 5,
        "st_mtime_ns": 6,
        "st_ctime_ns": 7,
        "st_atime_ns": 8,
    }
    expected = boundary._review_file_signature(SimpleNamespace(**baseline))
    atime_only = dict(baseline, st_atime_ns=999)
    assert boundary._review_file_signature(SimpleNamespace(**atime_only)) == expected
    for field in (
        "st_dev",
        "st_ino",
        "st_mode",
        "st_uid",
        "st_gid",
        "st_nlink",
        "st_size",
        "st_mtime_ns",
        "st_ctime_ns",
    ):
        changed = dict(baseline)
        changed[field] += 1
        assert boundary._review_file_signature(SimpleNamespace(**changed)) != expected


def test_review_publication_requires_preexisting_safe_chain_without_creating_ancestors(
    tmp_path: Path,
) -> None:
    trusted_root = tmp_path / "repo"
    trusted_root.mkdir()

    with pytest.raises(boundary.BoundaryViolation, match="PUBLIC_EVIDENCE_SCHEMA_VIOLATION"):
        boundary.write_review_public_bundle(_review_bundle_payloads(), trusted_root)

    assert list(trusted_root.iterdir()) == []

    _trusted_root, fixed_parent = _review_publication_root(tmp_path)
    fixed_parent.chmod(0o775)
    before = _review_tree_state(trusted_root)
    with pytest.raises(boundary.BoundaryViolation, match="PUBLIC_EVIDENCE_SCHEMA_VIOLATION"):
        boundary.write_review_public_bundle(_review_bundle_payloads(), trusted_root)
    assert _review_tree_state(trusted_root) == before


def test_review_publication_reverifies_ancestor_after_absence_before_first_mkdir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trusted_root, _fixed_parent = _review_publication_root(tmp_path)
    real_stat = os.stat
    real_mkdir = os.mkdir
    exchanged = False
    staging_mkdir_calls = 0

    def exchange_after_final_absence(path: Any, *args: Any, **kwargs: Any) -> os.stat_result:
        nonlocal exchanged
        try:
            return real_stat(path, *args, **kwargs)
        except FileNotFoundError:
            if path == boundary.REVIEW_PUBLIC_BUNDLE_ROOT.name and not exchanged:
                exchanged = True
                (trusted_root / "reports").rename(trusted_root / "reports-old")
                real_mkdir(trusted_root / "reports", 0o755)
                real_mkdir(trusted_root / "reports/public-sample", 0o755)
            raise

    def reject_staging_mkdir(
        name: str | bytes | os.PathLike[str],
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> None:
        nonlocal staging_mkdir_calls
        if isinstance(name, str) and name.startswith(
            boundary.REVIEW_PUBLIC_RECOVERY_PREFIX
        ):
            staging_mkdir_calls += 1
            raise AssertionError("namespace drift must be rejected before staging")
        real_mkdir(name, mode, dir_fd=dir_fd)

    monkeypatch.setattr(os, "stat", exchange_after_final_absence)
    monkeypatch.setattr(os, "mkdir", reject_staging_mkdir)

    with pytest.raises(boundary.BoundaryViolation, match="PUBLIC_EVIDENCE_SCHEMA_VIOLATION"):
        boundary.write_review_public_bundle(_review_bundle_payloads(), trusted_root)

    assert exchanged is True
    assert staging_mkdir_calls == 0
    for parent in (
        trusted_root / "reports-old/public-sample",
        trusted_root / "reports/public-sample",
    ):
        assert not [
            path
            for path in parent.iterdir()
            if path.name.startswith(boundary.REVIEW_PUBLIC_RECOVERY_PREFIX)
        ]


@pytest.mark.parametrize("existing", (False, True))
def test_review_publication_never_returns_after_final_sibling_scan_namespace_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    existing: bool,
) -> None:
    trusted_root, _fixed_parent = _review_publication_root(tmp_path)
    payloads = _review_bundle_payloads()
    if existing:
        boundary.write_review_public_bundle(payloads, trusted_root)
    real_scan = boundary._review_recovery_sibling_present
    real_mkdir = os.mkdir
    scans = 0

    def exchange_during_final_scan(parent_fd: int) -> bool:
        nonlocal scans
        scans += 1
        final_scan = 2 if existing else 3
        if scans == final_scan:
            (trusted_root / "reports").rename(trusted_root / "reports-old")
            real_mkdir(trusted_root / "reports", 0o755)
            real_mkdir(trusted_root / "reports/public-sample", 0o755)
        return real_scan(parent_fd)

    monkeypatch.setattr(
        boundary,
        "_review_recovery_sibling_present",
        exchange_during_final_scan,
    )
    expected_code = (
        "PUBLIC_EVIDENCE_SCHEMA_VIOLATION"
        if existing
        else "REVIEW_PUBLICATION_IDENTITY_UNCERTAIN"
    )

    with pytest.raises(boundary.BoundaryViolation, match=expected_code):
        boundary.write_review_public_bundle(payloads, trusted_root)

    assert not list((trusted_root / "reports/public-sample").iterdir())


def test_review_publication_initial_create_and_exact_second_call_is_observation_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trusted_root, fixed_parent = _review_publication_root(tmp_path)
    payloads = _review_bundle_payloads()
    real_token_hex = boundary.secrets.token_hex
    tokens: list[str] = []

    def token_hex(bits: int) -> str:
        token = real_token_hex(bits)
        tokens.append(token)
        return token

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("destructive or fallback path used by review publication")

    monkeypatch.setattr(boundary.secrets, "token_hex", token_hex)
    _forbid_review_destructive_or_fallback(monkeypatch)

    first = boundary.write_review_public_bundle(payloads, trusted_root)

    assert tuple(first) == REVIEW_BUNDLE_FILENAMES
    assert len(tokens) == 1
    assert len(tokens[0]) == 32 and tokens[0] == tokens[0].lower()
    assert all(character in "0123456789abcdef" for character in tokens[0])
    final = trusted_root / boundary.REVIEW_PUBLIC_BUNDLE_ROOT
    assert final.stat().st_mode & 0o777 == 0o755
    assert {name: path.read_bytes() for name, path in first.items()} == payloads
    assert all(path.stat().st_mode & 0o777 == 0o644 for path in first.values())
    assert all(path.stat().st_nlink == 1 for path in first.values())
    assert not [path for path in fixed_parent.iterdir() if path.name.startswith(boundary.REVIEW_PUBLIC_RECOVERY_PREFIX)]

    before = _review_tree_state(trusted_root)
    reads: list[tuple[int, int, int, int]] = []
    member_read_groups: list[list[tuple[int, int, int, int]]] = []
    active_bounds: dict[int, int] = {}
    real_read = os.read
    real_bounded_read = boundary._review_bounded_read

    def bounded_read(descriptor: int, length: int) -> bytes:
        bound = active_bounds[descriptor]
        assert length <= bound
        payload = real_read(descriptor, length)
        reads.append((descriptor, length, bound, len(payload)))
        return payload

    def record_member_bound(descriptor: int, expected_length: int) -> bytes:
        active_bounds[descriptor] = expected_length + 1
        start = len(reads)
        try:
            return real_bounded_read(descriptor, expected_length)
        finally:
            member_read_groups.append(reads[start:])
            active_bounds.pop(descriptor)

    monkeypatch.setattr(os, "read", bounded_read)
    monkeypatch.setattr(boundary, "_review_bounded_read", record_member_bound)
    monkeypatch.setattr(os, "fchmod", forbidden)
    monkeypatch.setattr(os, "fsync", forbidden)
    monkeypatch.setattr(boundary, "_review_noreplace_available", forbidden)
    monkeypatch.setattr(boundary, "_rename_noreplace", forbidden)
    monkeypatch.setattr(
        boundary.secrets,
        "token_hex",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("exact no-op must not allocate a recovery token")
        ),
    )
    second = boundary.write_review_public_bundle(payloads, trusted_root)

    assert tuple(second) == tuple(first)
    assert _review_tree_state(trusted_root) == before
    assert len(member_read_groups) == 7
    assert sorted(group[0][2] for group in member_read_groups) == sorted(
        len(payload) + 1 for payload in payloads.values()
    )
    for group in member_read_groups:
        assert group
        assert all(requested <= bound for _fd, requested, bound, _read in group)
        assert sum(read_length for _fd, _requested, _bound, read_length in group) <= group[0][2]


@pytest.mark.parametrize(
    "mismatch",
    (
        "changed",
        "missing",
        "extra",
        "directory-mode",
        "member-mode",
        "hardlink",
        "member-symlink",
        "member-nonregular",
    ),
)
def test_review_publication_rejects_nonexact_existing_bundle_without_repair(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mismatch: str,
) -> None:
    trusted_root, _fixed_parent = _review_publication_root(tmp_path)
    payloads = _review_bundle_payloads()
    paths = boundary.write_review_public_bundle(payloads, trusted_root)
    final = trusted_root / boundary.REVIEW_PUBLIC_BUNDLE_ROOT
    if mismatch == "changed":
        paths[REVIEW_BUNDLE_FILENAMES[0]].write_bytes(b"changed\n")
    elif mismatch == "missing":
        paths[REVIEW_BUNDLE_FILENAMES[0]].unlink()
    elif mismatch == "extra":
        (final / "extra.json").write_bytes(b"extra\n")
    elif mismatch == "directory-mode":
        final.chmod(0o700)
    elif mismatch == "member-mode":
        paths[REVIEW_BUNDLE_FILENAMES[0]].chmod(0o600)
    elif mismatch == "hardlink":
        paths[REVIEW_BUNDLE_FILENAMES[0]].unlink()
        os.link(final / REVIEW_BUNDLE_FILENAMES[1], final / REVIEW_BUNDLE_FILENAMES[0])
    elif mismatch == "member-symlink":
        outside = tmp_path / "outside"
        outside.write_bytes(b"outside-unchanged\n")
        paths[REVIEW_BUNDLE_FILENAMES[0]].unlink()
        paths[REVIEW_BUNDLE_FILENAMES[0]].symlink_to(outside)
    else:
        paths[REVIEW_BUNDLE_FILENAMES[0]].unlink()
        paths[REVIEW_BUNDLE_FILENAMES[0]].mkdir()
    before = _review_tree_state(trusted_root)
    monkeypatch.setattr(
        boundary.secrets,
        "token_hex",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("mismatched final must fail before staging")
        ),
    )

    with pytest.raises(boundary.BoundaryViolation, match="PUBLIC_EVIDENCE_SCHEMA_VIOLATION"):
        boundary.write_review_public_bundle(payloads, trusted_root)

    assert _review_tree_state(trusted_root) == before
    if mismatch == "member-symlink":
        assert (tmp_path / "outside").read_bytes() == b"outside-unchanged\n"


def test_review_publication_blocks_reserved_recovery_sibling_without_touching_it(
    tmp_path: Path,
) -> None:
    trusted_root, fixed_parent = _review_publication_root(tmp_path)
    recovery = fixed_parent / f"{boundary.REVIEW_PUBLIC_RECOVERY_PREFIX}{'a' * 32}"
    recovery.mkdir(mode=0o700)
    marker = recovery / "marker"
    marker.write_bytes(b"unchanged\n")
    before = _review_tree_state(trusted_root)

    with pytest.raises(boundary.BoundaryViolation, match="REVIEW_PUBLICATION_RECOVERY_PRESENT"):
        boundary.write_review_public_bundle(_review_bundle_payloads(), trusted_root)

    assert _review_tree_state(trusted_root) == before


def test_review_publication_requires_supported_noreplace_before_staging(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trusted_root, fixed_parent = _review_publication_root(tmp_path)
    monkeypatch.setattr(boundary, "_review_noreplace_available", lambda: False)
    monkeypatch.setattr(
        boundary.secrets,
        "token_hex",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("unsupported no-replace must fail before token allocation")
        ),
    )

    with pytest.raises(
        boundary.BoundaryViolation,
        match="REVIEW_PUBLICATION_NO_REPLACE_UNAVAILABLE",
    ):
        boundary.write_review_public_bundle(_review_bundle_payloads(), trusted_root)

    assert list(fixed_parent.iterdir()) == []


@pytest.mark.parametrize("base_exception_type", (KeyboardInterrupt, SystemExit))
def test_review_publication_propagates_baseexception_before_staging(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    base_exception_type: type[BaseException],
) -> None:
    trusted_root, fixed_parent = _review_publication_root(tmp_path)
    injected = base_exception_type("pre-staging interrupt")

    def interrupt_before_staging() -> bool:
        raise injected

    monkeypatch.setattr(
        boundary,
        "_review_noreplace_available",
        interrupt_before_staging,
    )

    with pytest.raises(base_exception_type) as exc_info:
        boundary.write_review_public_bundle(_review_bundle_payloads(), trusted_root)

    assert exc_info.value is injected
    assert list(fixed_parent.iterdir()) == []


def test_review_publication_keeps_stage_0700_until_all_members_are_fsynced(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trusted_root, _fixed_parent = _review_publication_root(tmp_path)
    payloads = _review_bundle_payloads()
    real_write_member = boundary._review_write_member
    real_fchmod = os.fchmod
    real_fsync = os.fsync
    real_noreplace = boundary._rename_noreplace
    events: list[tuple[str, int, int | None]] = []

    def record_member(
        staging_fd: int,
        name: str,
        payload: bytes,
        trusted_parent_gid: int,
    ) -> None:
        assert os.fstat(staging_fd).st_mode & 0o777 == 0o700
        real_write_member(staging_fd, name, payload, trusted_parent_gid)
        events.append(("member-fsynced", staging_fd, None))

    def record_fchmod(descriptor: int, mode: int) -> None:
        real_fchmod(descriptor, mode)
        events.append(("fchmod", descriptor, mode))

    def record_fsync(descriptor: int) -> None:
        real_fsync(descriptor)
        events.append(("fsync", descriptor, None))

    def record_promotion(
        source_fd: int,
        source_name: str,
        destination_fd: int,
        destination_name: str,
    ) -> None:
        assert sum(event[0] == "member-fsynced" for event in events) == 7
        staging_fd = next(
            event[1] for event in events if event[0] == "member-fsynced"
        )
        assert os.fstat(staging_fd).st_mode & 0o777 == 0o755
        mode_change = max(
            index
            for index, event in enumerate(events)
            if event == ("fchmod", staging_fd, 0o755)
        )
        assert all(
            index < mode_change
            for index, event in enumerate(events)
            if event[0] == "member-fsynced"
        )
        assert ("fsync", staging_fd, None) in events[mode_change + 1 :]
        assert ("fsync", destination_fd, None) in events[mode_change + 1 :]
        real_noreplace(source_fd, source_name, destination_fd, destination_name)

    monkeypatch.setattr(boundary, "_review_write_member", record_member)
    monkeypatch.setattr(os, "fchmod", record_fchmod)
    monkeypatch.setattr(os, "fsync", record_fsync)
    monkeypatch.setattr(boundary, "_rename_noreplace", record_promotion)

    boundary.write_review_public_bundle(payloads, trusted_root)


def test_review_publication_competitor_is_preserved_and_owned_stage_is_retained(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trusted_root, fixed_parent = _review_publication_root(tmp_path)
    payloads = _review_bundle_payloads()
    real_noreplace = boundary._rename_noreplace
    _forbid_review_destructive_or_fallback(monkeypatch)

    def insert_competitor(
        source_fd: int,
        source_name: str,
        destination_fd: int,
        destination_name: str,
    ) -> None:
        os.mkdir(destination_name, 0o755, dir_fd=destination_fd)
        competitor_directory_fd = os.open(
            destination_name,
            os.O_RDONLY | getattr(os, "O_DIRECTORY", 0),
            dir_fd=destination_fd,
        )
        competitor_fd = os.open(
            "competitor.txt",
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o644,
            dir_fd=competitor_directory_fd,
        )
        try:
            os.write(competitor_fd, b"competitor-unchanged\n")
            os.fsync(competitor_fd)
        finally:
            os.close(competitor_fd)
            os.close(competitor_directory_fd)
        real_noreplace(source_fd, source_name, destination_fd, destination_name)

    monkeypatch.setattr(boundary, "_rename_noreplace", insert_competitor)
    with pytest.raises(boundary.BoundaryViolation, match="REVIEW_PUBLICATION_RECOVERY_RETAINED"):
        boundary.write_review_public_bundle(payloads, trusted_root)

    competitor = trusted_root / boundary.REVIEW_PUBLIC_BUNDLE_ROOT / "competitor.txt"
    assert competitor.read_bytes() == b"competitor-unchanged\n"
    recoveries = [
        path
        for path in fixed_parent.iterdir()
        if path.name.startswith(boundary.REVIEW_PUBLIC_RECOVERY_PREFIX)
    ]
    assert len(recoveries) == 1
    assert recoveries[0].stat().st_mode & 0o777 == 0o700
    before = _review_tree_state(trusted_root)
    with pytest.raises(boundary.BoundaryViolation, match="REVIEW_PUBLICATION_RECOVERY_PRESENT"):
        boundary.write_review_public_bundle(payloads, trusted_root)
    assert _review_tree_state(trusted_root) == before


def test_review_publication_retains_owned_stage_after_precommit_fault(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trusted_root, fixed_parent = _review_publication_root(tmp_path)
    real_recovery_owned = boundary._review_recovery_owned
    ownership_observations: list[tuple[int, tuple[int, int, int, int, int], tuple[int, int, int, int, int]]] = []

    def record_recovery_ownership(
        parent_fd: int,
        staging_name: str,
        staging_fd: int,
        expected_identity: os.stat_result,
        trusted_parent_gid: int,
    ) -> bool:
        linked = os.stat(staging_name, dir_fd=parent_fd, follow_symlinks=False)
        ownership_observations.append(
            (
                staging_fd,
                boundary._review_object_signature(expected_identity),
                boundary._review_object_signature(linked),
            )
        )
        return real_recovery_owned(
            parent_fd,
            staging_name,
            staging_fd,
            expected_identity,
            trusted_parent_gid,
        )

    monkeypatch.setattr(boundary, "_review_recovery_owned", record_recovery_ownership)
    monkeypatch.setattr(
        boundary,
        "_write_all_and_fsync",
        lambda *args, **kwargs: (_ for _ in ()).throw(OSError(errno.EIO, "fault")),
    )

    with pytest.raises(boundary.BoundaryViolation, match="REVIEW_PUBLICATION_RECOVERY_RETAINED"):
        boundary.write_review_public_bundle(_review_bundle_payloads(), trusted_root)

    recoveries = [
        path
        for path in fixed_parent.iterdir()
        if path.name.startswith(boundary.REVIEW_PUBLIC_RECOVERY_PREFIX)
    ]
    assert len(recoveries) == 1
    assert recoveries[0].stat().st_mode & 0o777 == 0o700
    assert len(ownership_observations) >= 3
    assert len({observation[0] for observation in ownership_observations}) == 1
    assert all(expected == linked for _fd, expected, linked in ownership_observations)


def test_review_publication_recovery_error_has_no_raw_exception_chain(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trusted_root, _fixed_parent = _review_publication_root(tmp_path)
    canary = "/private/canary-secret-recovery-token"

    def fail_write(*args: Any, **kwargs: Any) -> None:
        raise OSError(canary)

    monkeypatch.setattr(boundary, "_write_all_and_fsync", fail_write)

    with pytest.raises(boundary.BoundaryViolation) as exc_info:
        boundary.write_review_public_bundle(_review_bundle_payloads(), trusted_root)

    _assert_sanitized_publication_error(
        exc_info.value,
        "REVIEW_PUBLICATION_RECOVERY_RETAINED",
        canary,
    )


def test_review_publication_identity_error_has_no_raw_exception_chain(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trusted_root, _fixed_parent = _review_publication_root(tmp_path)
    canary = "/private/canary-secret-identity-token"

    def fail_write(*args: Any, **kwargs: Any) -> None:
        raise OSError(canary)

    monkeypatch.setattr(boundary, "_write_all_and_fsync", fail_write)
    monkeypatch.setattr(boundary, "_review_recovery_owned", lambda *args: False)

    with pytest.raises(boundary.BoundaryViolation) as exc_info:
        boundary.write_review_public_bundle(_review_bundle_payloads(), trusted_root)

    _assert_sanitized_publication_error(
        exc_info.value,
        "REVIEW_PUBLICATION_IDENTITY_UNCERTAIN",
        canary,
    )


def test_review_publication_classifier_baseexception_fails_closed_without_chain(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trusted_root, _fixed_parent = _review_publication_root(tmp_path)
    original_canary = "/private/canary-secret-original-token"
    classifier_canary = "/private/canary-secret-classifier-token"

    def fail_write(*args: Any, **kwargs: Any) -> None:
        raise OSError(original_canary)

    def interrupt_classifier(*args: Any, **kwargs: Any) -> Any:
        raise SystemExit(classifier_canary)

    monkeypatch.setattr(boundary, "_write_all_and_fsync", fail_write)
    monkeypatch.setattr(
        boundary,
        "_review_classify_staged_failure",
        interrupt_classifier,
    )

    with pytest.raises(boundary.BoundaryViolation) as exc_info:
        boundary.write_review_public_bundle(_review_bundle_payloads(), trusted_root)

    _assert_sanitized_publication_error(
        exc_info.value,
        "REVIEW_PUBLICATION_IDENTITY_UNCERTAIN",
        original_canary,
    )
    rendered = "".join(
        traceback.format_exception(
            type(exc_info.value),
            exc_info.value,
            exc_info.value.__traceback__,
        )
    )
    assert classifier_canary not in rendered


def test_review_publication_does_not_claim_or_mutate_name_after_mkdir_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trusted_root, fixed_parent = _review_publication_root(tmp_path)
    real_mkdir = os.mkdir
    real_fchmod = os.fchmod
    injected = False
    fchmod_modes: list[int] = []

    def record_fchmod(descriptor: int, mode: int) -> None:
        fchmod_modes.append(mode)
        real_fchmod(descriptor, mode)

    def mkdir_then_fileexists(
        name: str | bytes,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> None:
        nonlocal injected
        if (
            isinstance(name, str)
            and name.startswith(boundary.REVIEW_PUBLIC_RECOVERY_PREFIX)
            and not injected
        ):
            injected = True
            real_mkdir(name, mode, dir_fd=dir_fd)
            raise FileExistsError(errno.EEXIST, "wrapper lost mkdir result")
        real_mkdir(name, mode, dir_fd=dir_fd)

    monkeypatch.setattr(os, "mkdir", mkdir_then_fileexists)
    monkeypatch.setattr(os, "fchmod", record_fchmod)

    with pytest.raises(boundary.BoundaryViolation, match="REVIEW_PUBLICATION_IDENTITY_UNCERTAIN"):
        boundary.write_review_public_bundle(_review_bundle_payloads(), trusted_root)

    recoveries = [
        path
        for path in fixed_parent.iterdir()
        if path.name.startswith(boundary.REVIEW_PUBLIC_RECOVERY_PREFIX)
    ]
    assert len(recoveries) == 1
    assert recoveries[0].stat().st_mode & 0o777 == 0o700
    assert 0o700 not in fchmod_modes


def test_review_publication_retains_owned_stage_after_filesystem_noreplace_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trusted_root, fixed_parent = _review_publication_root(tmp_path)
    _forbid_review_destructive_or_fallback(monkeypatch)
    monkeypatch.setattr(
        boundary,
        "_rename_noreplace",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            OSError(errno.ENOTSUP, "filesystem declined no-replace")
        ),
    )

    with pytest.raises(boundary.BoundaryViolation, match="REVIEW_PUBLICATION_RECOVERY_RETAINED"):
        boundary.write_review_public_bundle(_review_bundle_payloads(), trusted_root)

    recoveries = [
        path
        for path in fixed_parent.iterdir()
        if path.name.startswith(boundary.REVIEW_PUBLIC_RECOVERY_PREFIX)
    ]
    assert len(recoveries) == 1
    assert recoveries[0].stat().st_mode & 0o777 == 0o700


@pytest.mark.parametrize("base_exception_type", (KeyboardInterrupt, SystemExit))
def test_review_publication_classifies_baseexception_before_promotion(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    base_exception_type: type[BaseException],
) -> None:
    trusted_root, fixed_parent = _review_publication_root(tmp_path)
    payloads = _review_bundle_payloads()
    _forbid_review_destructive_or_fallback(monkeypatch)

    def interrupt_before_promotion(*args: Any, **kwargs: Any) -> None:
        raise base_exception_type("pre-promotion interrupt")

    monkeypatch.setattr(boundary, "_rename_noreplace", interrupt_before_promotion)

    with pytest.raises(boundary.BoundaryViolation) as exc_info:
        boundary.write_review_public_bundle(payloads, trusted_root)

    assert exc_info.value.code == "REVIEW_PUBLICATION_RECOVERY_RETAINED"
    assert not (trusted_root / boundary.REVIEW_PUBLIC_BUNDLE_ROOT).exists()
    recoveries = [
        path
        for path in fixed_parent.iterdir()
        if path.name.startswith(boundary.REVIEW_PUBLIC_RECOVERY_PREFIX)
    ]
    assert len(recoveries) == 1
    assert recoveries[0].stat().st_mode & 0o777 == 0o700
    assert {path.name: path.read_bytes() for path in recoveries[0].iterdir()} == payloads
    assert all(path.stat().st_mode & 0o777 == 0o644 for path in recoveries[0].iterdir())


def test_review_publication_stops_mutating_when_recovery_identity_is_uncertain(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trusted_root, _fixed_parent = _review_publication_root(tmp_path)
    fchmod_modes: list[int] = []
    real_fchmod = os.fchmod

    def record_fchmod(descriptor: int, mode: int) -> None:
        fchmod_modes.append(mode)
        real_fchmod(descriptor, mode)

    monkeypatch.setattr(os, "fchmod", record_fchmod)
    monkeypatch.setattr(boundary, "_review_recovery_owned", lambda *args: False)
    monkeypatch.setattr(
        boundary,
        "_write_all_and_fsync",
        lambda *args, **kwargs: (_ for _ in ()).throw(OSError(errno.EIO, "fault")),
    )

    with pytest.raises(boundary.BoundaryViolation, match="REVIEW_PUBLICATION_IDENTITY_UNCERTAIN"):
        boundary.write_review_public_bundle(_review_bundle_payloads(), trusted_root)

    assert 0o700 not in fchmod_modes


def test_review_publication_identity_uncertainty_forbids_all_later_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trusted_root, fixed_parent = _review_publication_root(tmp_path)
    uncertain = False
    post_uncertainty_calls: list[str] = []

    def uncertain_ownership(*args: Any, **kwargs: Any) -> bool:
        nonlocal uncertain
        uncertain = True
        return False

    def guard(name: str, real: Any) -> Any:
        def guarded(*args: Any, **kwargs: Any) -> Any:
            if uncertain:
                post_uncertainty_calls.append(name)
                raise AssertionError(f"mutation after identity uncertainty: {name}")
            return real(*args, **kwargs)

        return guarded

    monkeypatch.setattr(boundary, "_review_recovery_owned", uncertain_ownership)
    monkeypatch.setattr(
        boundary,
        "_write_all_and_fsync",
        lambda *args, **kwargs: (_ for _ in ()).throw(OSError(errno.EIO, "fault")),
    )
    for owner, name in (
        (os, "write"),
        (os, "mkdir"),
        (os, "fchmod"),
        (os, "ftruncate"),
        (os, "unlink"),
        (os, "remove"),
        (boundary, "_rename_noreplace"),
        (boundary, "_rename_exchange"),
        (boundary, "_unlinkat_public"),
        (boundary, "_cleanup_verified_public_bundle"),
        (os, "rmdir"),
        (os, "rename"),
        (os, "replace"),
        (Path, "unlink"),
        (Path, "replace"),
    ):
        if hasattr(owner, name):
            monkeypatch.setattr(owner, name, guard(name, getattr(owner, name)))

    with pytest.raises(
        boundary.BoundaryViolation,
        match="REVIEW_PUBLICATION_IDENTITY_UNCERTAIN",
    ):
        boundary.write_review_public_bundle(_review_bundle_payloads(), trusted_root)

    assert uncertain is True
    assert post_uncertainty_calls == []
    recoveries = [
        path
        for path in fixed_parent.iterdir()
        if path.name.startswith(boundary.REVIEW_PUBLIC_RECOVERY_PREFIX)
    ]
    assert len(recoveries) == 1
    assert recoveries[0].stat().st_mode & 0o777 == 0o700


def test_review_publication_does_not_reprobe_after_identity_uncertainty(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trusted_root, _fixed_parent = _review_publication_root(tmp_path)
    real_recovery_owned = boundary._review_recovery_owned
    real_fchmod = os.fchmod
    calls = 0
    fchmod_modes: list[int] = []

    def false_once_then_real(*args: Any) -> bool:
        nonlocal calls
        calls += 1
        if calls == 1:
            return False
        return real_recovery_owned(*args)

    def record_fchmod(descriptor: int, mode: int) -> None:
        fchmod_modes.append(mode)
        real_fchmod(descriptor, mode)

    monkeypatch.setattr(boundary, "_review_recovery_owned", false_once_then_real)
    monkeypatch.setattr(os, "fchmod", record_fchmod)

    with pytest.raises(boundary.BoundaryViolation, match="REVIEW_PUBLICATION_IDENTITY_UNCERTAIN"):
        boundary.write_review_public_bundle(_review_bundle_payloads(), trusted_root)

    assert calls == 1
    assert 0o700 not in fchmod_modes


def test_review_publication_namespace_identity_failure_is_sticky(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trusted_root, _fixed_parent = _review_publication_root(tmp_path)
    real_verify_namespace = boundary._review_verify_namespace
    real_fchmod = os.fchmod
    calls = 0
    fchmod_modes: list[int] = []

    def fail_first_post_staging_check(*args: Any, **kwargs: Any) -> None:
        nonlocal calls
        calls += 1
        if calls == 4:
            raise boundary.BoundaryViolation("PUBLIC_EVIDENCE_SCHEMA_VIOLATION")
        real_verify_namespace(*args, **kwargs)

    def record_fchmod(descriptor: int, mode: int) -> None:
        fchmod_modes.append(mode)
        real_fchmod(descriptor, mode)

    monkeypatch.setattr(
        boundary,
        "_review_verify_namespace",
        fail_first_post_staging_check,
    )
    monkeypatch.setattr(os, "fchmod", record_fchmod)

    with pytest.raises(boundary.BoundaryViolation, match="REVIEW_PUBLICATION_IDENTITY_UNCERTAIN"):
        boundary.write_review_public_bundle(_review_bundle_payloads(), trusted_root)

    assert calls == 4
    assert 0o700 not in fchmod_modes


def test_review_publication_namespace_drift_stops_before_recovery_mode_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trusted_root, _fixed_parent = _review_publication_root(tmp_path)
    fchmod_modes: list[int] = []
    real_fchmod = os.fchmod
    real_write_member = boundary._review_write_member
    injected = False

    def record_fchmod(descriptor: int, mode: int) -> None:
        fchmod_modes.append(mode)
        real_fchmod(descriptor, mode)

    def exchange_namespace_then_fail(
        staging_fd: int,
        name: str,
        payload: bytes,
        trusted_parent_gid: int,
    ) -> None:
        nonlocal injected
        real_write_member(staging_fd, name, payload, trusted_parent_gid)
        if not injected:
            injected = True
            (trusted_root / "reports").rename(trusted_root / "reports-old")
            (trusted_root / "reports/public-sample").mkdir(parents=True)
            raise OSError(errno.EIO, "namespace exchanged")

    monkeypatch.setattr(os, "fchmod", record_fchmod)
    monkeypatch.setattr(boundary, "_review_write_member", exchange_namespace_then_fail)

    with pytest.raises(boundary.BoundaryViolation, match="REVIEW_PUBLICATION_IDENTITY_UNCERTAIN"):
        boundary.write_review_public_bundle(_review_bundle_payloads(), trusted_root)

    assert 0o700 not in fchmod_modes
    recoveries = [
        path
        for path in (trusted_root / "reports-old/public-sample").iterdir()
        if path.name.startswith(boundary.REVIEW_PUBLIC_RECOVERY_PREFIX)
    ]
    assert len(recoveries) == 1


def test_review_publication_classifies_success_then_wrapper_error_without_downgrade(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trusted_root, fixed_parent = _review_publication_root(tmp_path)
    payloads = _review_bundle_payloads()
    real_noreplace = boundary._rename_noreplace
    canary = "/private/canary-secret-post-syscall-token"

    def promote_then_raise(
        source_fd: int,
        source_name: str,
        destination_fd: int,
        destination_name: str,
    ) -> None:
        real_noreplace(source_fd, source_name, destination_fd, destination_name)
        raise OSError(errno.EIO, canary)

    monkeypatch.setattr(boundary, "_rename_noreplace", promote_then_raise)
    with pytest.raises(boundary.BoundaryViolation) as exc_info:
        boundary.write_review_public_bundle(payloads, trusted_root)

    _assert_sanitized_publication_error(
        exc_info.value,
        "REVIEW_PUBLICATION_POST_SYSCALL_FAILURE",
        canary,
    )

    final = trusted_root / boundary.REVIEW_PUBLIC_BUNDLE_ROOT
    assert final.stat().st_mode & 0o777 == 0o755
    assert {name: (final / name).read_bytes() for name in payloads} == payloads
    assert not [path for path in fixed_parent.iterdir() if path.name.startswith(boundary.REVIEW_PUBLIC_RECOVERY_PREFIX)]

    monkeypatch.setattr(boundary, "_rename_noreplace", real_noreplace)
    assert tuple(boundary.write_review_public_bundle(payloads, trusted_root)) == tuple(payloads)


@pytest.mark.parametrize("base_exception_type", (KeyboardInterrupt, SystemExit))
def test_review_publication_classifies_promoted_baseexception_without_downgrade(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    base_exception_type: type[BaseException],
) -> None:
    trusted_root, fixed_parent = _review_publication_root(tmp_path)
    payloads = _review_bundle_payloads()
    real_noreplace = boundary._rename_noreplace
    _forbid_review_destructive_or_fallback(monkeypatch)

    def promote_then_interrupt(
        source_fd: int,
        source_name: str,
        destination_fd: int,
        destination_name: str,
    ) -> None:
        real_noreplace(source_fd, source_name, destination_fd, destination_name)
        raise base_exception_type("post-promotion interrupt")

    monkeypatch.setattr(boundary, "_rename_noreplace", promote_then_interrupt)

    with pytest.raises(boundary.BoundaryViolation) as exc_info:
        boundary.write_review_public_bundle(payloads, trusted_root)

    assert exc_info.value.code == "REVIEW_PUBLICATION_POST_SYSCALL_FAILURE"
    final = trusted_root / boundary.REVIEW_PUBLIC_BUNDLE_ROOT
    assert final.stat().st_mode & 0o777 == 0o755
    assert {name: (final / name).read_bytes() for name in payloads} == payloads
    assert not [
        path
        for path in fixed_parent.iterdir()
        if path.name.startswith(boundary.REVIEW_PUBLIC_RECOVERY_PREFIX)
    ]


def test_s1_s2_and_compromised_truth_matrices_are_monotonic() -> None:
    s1 = boundary.blocked_summary_for(
        boundary.BoundaryViolation("PROTOCOL_FREEZE_HASH_DRIFT"),
        last_state="EXPERIMENT_BINDINGS_COMPLETE",
    )
    assert s1["blocked_stage"] == "S1_PROTOCOL_FREEZE"
    assert s1["maximum_state_this_change"] == "EXPERIMENT_BINDINGS_COMPLETE"
    assert s1["execution_bindings_status"] == "COMPLETE"
    assert s1["protocol_freeze_status"] == "NOT_FROZEN"
    assert s1["new_protocol_version_required"] is True
    assert s1["clean_population_status"] == "NOT_MATERIALIZED"

    s2 = boundary.blocked_summary_for(
        boundary.BoundaryViolation("LINEAGE_OR_LOCKBOX_ATTESTATION_FAILED"),
        last_state="PROTOCOL_FROZEN",
    )
    assert s2["blocked_stage"] == "S2_MATERIALIZATION_OR_SEAL"
    assert s2["maximum_state_this_change"] == "PROTOCOL_FROZEN"
    assert s2["protocol_freeze_status"] == "FROZEN"
    assert s2["boundary_integrity_status"] == "INTACT_BLOCKED"
    assert s2["new_protocol_and_acquisition_required"] is True
    assert all(value is False for value in s2["artifacts"].values())

    compromised = boundary.blocked_summary_for(
        boundary.BoundaryViolation("SEALED_ARTIFACT_DRIFT_OR_MEMBERSHIP_LEAK"),
        last_state="POPULATION_MATERIALIZED_AND_SEALED",
    )
    assert compromised["boundary_integrity_status"] == "COMPROMISED"
    assert compromised["clean_population_status"] == "MATERIALIZED_AND_SEALED"
    assert compromised["protocol_freeze_status"] == "FROZEN"
    assert all(value is True for value in compromised["artifacts"].values())
    assert compromised["new_protocol_and_acquisition_required"] is True
    assert compromised["boundary_reuse_allowed"] is False
    assert compromised["execution_readiness"] is False
    assert all(value is False for value in compromised["claims"].values())


def test_cli_missing_inputs_returns_nonzero_and_public_safe_stdout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(data_cli, "REPO_ROOT", tmp_path)
    rc = data_cli.main(
        [
            "clean-boundary-validate",
            "--bindings",
            "missing-bindings.json",
            "--source-contract",
            "missing-source.json",
            "--compiler-card",
            "missing-compiler.json",
            "--model-card",
            "missing-model.json",
        ]
    )
    assert rc != 0
    output = capsys.readouterr().out
    payload = json.loads(output)
    assert payload["ok"] is False
    assert payload["decision"] == "CLEAN_EVALUATION_BOUNDARY_MATERIALIZATION_BLOCKED"
    assert "missing-bindings" not in output
    assert str(tmp_path) not in output


@pytest.mark.parametrize(
    "manifest_case",
    ("missing_root", "invalid_hash", "missing_manifest", "symlink", "corrupt"),
)
def test_cli_materialize_manifest_load_failures_remain_conservative_s0(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    manifest_case: str,
) -> None:
    monkeypatch.setattr(data_cli, "REPO_ROOT", tmp_path)
    root = tmp_path / boundary.CANONICAL_PRIVATE_ROOT
    protocol_sha256 = "a" * 64
    if manifest_case != "missing_root":
        protocols = root / "protocols"
        protocols.mkdir(parents=True)
        if manifest_case == "invalid_hash":
            protocol_sha256 = "not-a-sha256"
        elif manifest_case == "symlink":
            outside = tmp_path / "outside-manifest.json"
            outside.write_text("{}\n", encoding="utf-8")
            (protocols / f"{protocol_sha256}.json").symlink_to(outside)
        elif manifest_case == "corrupt":
            (protocols / f"{protocol_sha256}.json").write_bytes(b"{broken\n")

    rc = data_cli.main(
        [
            "clean-boundary-materialize",
            "--protocol-sha256",
            protocol_sha256,
            "--source-frame",
            "inputs/source-frame.jsonl",
            "--lockbox-attestation",
            "inputs/lockbox-attestation.json",
            "--generation-id",
            "generation-v1",
        ]
    )
    assert rc != 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["current_readiness_state"] == "DESIGN_ONLY"
    assert payload["execution_bindings_status"] == "INCOMPLETE"
    assert payload["protocol_freeze_status"] == "NOT_FROZEN"
    assert payload["artifacts"]["protocol_manifest_frozen"] is False
    assert payload["boundary_integrity_status"] == "NOT_CREATED"


def test_cli_materialize_failure_after_verified_manifest_reports_s2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(data_cli, "REPO_ROOT", tmp_path)
    root = tmp_path / boundary.CANONICAL_PRIVATE_ROOT
    names = _valid_private_inputs(root)
    (root / names["source_frame"]).unlink()

    rc = data_cli.main(
        [
            "clean-boundary-materialize",
            "--protocol-sha256",
            names["protocol_sha256"],
            "--source-frame",
            names["source_frame"],
            "--lockbox-attestation",
            names["lockbox_attestation"],
            "--generation-id",
            "generation-v1",
        ]
    )
    assert rc != 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["current_readiness_state"] == "PROTOCOL_FROZEN"
    assert payload["execution_bindings_status"] == "COMPLETE"
    assert payload["protocol_freeze_status"] == "FROZEN"
    assert payload["boundary_integrity_status"] == "INTACT_BLOCKED"


def test_cli_validate_persists_frozen_protocol_before_materialization(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(data_cli, "REPO_ROOT", tmp_path)
    root = tmp_path / boundary.CANONICAL_PRIVATE_ROOT
    names = _valid_private_inputs(root)
    protocol_dir = root / "protocols"
    for path in protocol_dir.iterdir():
        path.unlink()
    protocol_dir.rmdir()
    rc = data_cli.main(
        [
            "clean-boundary-validate",
            "--bindings",
            names["bindings"],
            "--source-contract",
            names["source_contract"],
            "--compiler-card",
            names["compiler_card"],
            "--model-card",
            names["model_card"],
        ]
    )
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["protocol_sha256"] == names["protocol_sha256"]
    assert (root / "protocols" / f"{names['protocol_sha256']}.json").is_file()


def test_cli_verify_missing_generation_reports_not_created_without_private_details(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(data_cli, "REPO_ROOT", tmp_path)
    rc = data_cli.main(
        [
            "clean-boundary-verify",
            "--generation-id",
            "missing-generation",
            "--population-seal-sha256",
            "0" * 64,
        ]
    )
    assert rc != 0
    output = capsys.readouterr().out
    payload = json.loads(output)
    assert payload["boundary_integrity_status"] == "NOT_CREATED"
    assert str(tmp_path) not in output


def test_cli_materialize_and_verify_success_with_named_inputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(data_cli, "REPO_ROOT", tmp_path)
    root = tmp_path / boundary.CANONICAL_PRIVATE_ROOT
    names = _valid_private_inputs(root)
    rc = data_cli.main(
        [
            "clean-boundary-materialize",
            "--protocol-sha256",
            names["protocol_sha256"],
            "--source-frame",
            names["source_frame"],
            "--lockbox-attestation",
            names["lockbox_attestation"],
            "--generation-id",
            "generation-v1",
        ]
    )
    assert rc == 0
    materialized = json.loads(capsys.readouterr().out)
    assert materialized["ok"] is True
    assert materialized["current_readiness_state"] == "POPULATION_MATERIALIZED_AND_SEALED"
    rc = data_cli.main(
        [
            "clean-boundary-verify",
            "--generation-id",
            "generation-v1",
            "--population-seal-sha256",
            materialized["hashes"]["population_seal_sha256"],
        ]
    )
    assert rc == 0
    verified = json.loads(capsys.readouterr().out)
    assert verified == {"ok": True, "boundary_integrity_status": "INTACT_SEALED"}
