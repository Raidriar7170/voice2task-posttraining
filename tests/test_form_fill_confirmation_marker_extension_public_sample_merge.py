import json
from pathlib import Path

import pytest

from voice2task.cli import data as data_cli
from voice2task.dataset import (
    build_public_sample_dataset,
    merge_form_fill_confirmation_marker_extension_candidates_into_public_sample,
)
from voice2task.io import read_json, read_jsonl, write_jsonl
from voice2task.leak_scan import scan_paths
from voice2task.reports import write_form_fill_confirmation_marker_extension_public_sample_merge_report
from voice2task.validation import validate_dataset_artifacts

REPO_ROOT = Path(__file__).resolve().parents[1]
PUBLIC_SAMPLE_DIR = REPO_ROOT / "data" / "public-samples"
FORM_FILL_EXTENSION_CANDIDATE_SEED = (
    PUBLIC_SAMPLE_DIR / "form_fill_confirmation_marker_extension_seed_candidates.jsonl"
)
MERGE_EVIDENCE_DIR = (
    REPO_ROOT / "reports" / "public-sample" / "form-fill-confirmation-marker-extension-merge"
)

EXPECTED_EXTENSION_IDS = {row["id"] for row in read_jsonl(FORM_FILL_EXTENSION_CANDIDATE_SEED)}
PRE_MERGE_COUNTS = {"dpo_pairs": 1938, "seed_rows": 228, "sft_rows": 663}
EXPECTED_COUNTS = {"dpo_pairs": 2046, "seed_rows": 240, "sft_rows": 675}
EXPECTED_SPLITS = {"dev": 207, "test": 207, "train": 261}
HISTORICAL_PRE_MERGE_COUNTS = {"dpo_pairs": 742, "seed_rows": 86, "sft_rows": 240}
HISTORICAL_EXPECTED_COUNTS = {"dpo_pairs": 850, "seed_rows": 98, "sft_rows": 252}
HISTORICAL_EXPECTED_SPLITS = {"dev": 69, "test": 69, "train": 114}
EXPECTED_DPO_DELTAS = {
    "form_confirmation_drift": 12,
    "malformed_schema": 12,
    "missing_confirmation": 12,
    "missing_slot": 12,
    "underspecified_request": 12,
    "unsafe_allowance": 12,
    "wrong_route": 12,
    "wrong_slot": 12,
    "wrong_task_type": 12,
}


def _copy_current_public_sample_without_extension_candidates(tmp_path: Path) -> Path:
    public_dir = tmp_path / "public-samples"
    public_dir.mkdir()
    seed_rows = [
        row
        for row in read_jsonl(PUBLIC_SAMPLE_DIR / "seed_traces.jsonl")
        if row["id"] not in EXPECTED_EXTENSION_IDS
    ]
    write_jsonl(public_dir / "seed_traces.jsonl", seed_rows)
    build_public_sample_dataset(seed_path=public_dir / "seed_traces.jsonl", output_dir=public_dir)
    return public_dir


def _assert_manifest_has_extension_merge_summary(manifest_payload: dict) -> None:
    assert manifest_payload["counts"] == EXPECTED_COUNTS
    assert manifest_payload["split_counts"] == EXPECTED_SPLITS
    source_summary = manifest_payload["source_summary"]
    assert source_summary["form_fill_confirmation_marker_extension_candidate_seed_rows"] == 12
    assert source_summary["form_fill_confirmation_marker_extension_candidate_sft_rows"] == 12
    assert source_summary["form_fill_confirmation_marker_extension_candidates_formal_public_sample"] is True


def _assert_extension_rows_are_formal(seed_rows: list[dict], sft_rows: list[dict], dpo_rows: list[dict]) -> None:
    seed_by_id = {row["id"]: row for row in seed_rows}
    sft_by_id = {row["id"]: row for row in sft_rows}
    dpo_by_id = {row["id"]: row for row in dpo_rows}
    candidate_rows = read_jsonl(FORM_FILL_EXTENSION_CANDIDATE_SEED)

    assert EXPECTED_EXTENSION_IDS.issubset(seed_by_id)
    for candidate in candidate_rows:
        seed = seed_by_id[candidate["id"]]
        provenance = seed["provenance"]
        assert seed["split"] == "train"
        assert provenance["candidate_status"] == "formal_public_sample"
        assert provenance["source_mode"] == "form_fill_confirmation_marker_extension_formal_public_seed"
        assert provenance["merged_from_candidate_seed"] == (
            "data/public-samples/form_fill_confirmation_marker_extension_seed_candidates.jsonl"
        )
        assert provenance["source_family_id"] == candidate["provenance"]["source_family_id"]

        original = sft_by_id[candidate["id"]]
        assert original["split"] == "train"
        assert original["provenance"]["candidate_status"] == "formal_public_sample"
        assert original["provenance"]["source_mode"] == "form_fill_confirmation_marker_extension_formal_public_seed"
        for rejection_reason in EXPECTED_DPO_DELTAS:
            assert f"{candidate['id']}-{rejection_reason}" in dpo_by_id


def test_merge_form_fill_confirmation_marker_extension_candidates_rebuilds_formal_public_sample(
    tmp_path: Path,
) -> None:
    public_dir = _copy_current_public_sample_without_extension_candidates(tmp_path)

    manifest = merge_form_fill_confirmation_marker_extension_candidates_into_public_sample(
        candidate_seed_path=FORM_FILL_EXTENSION_CANDIDATE_SEED,
        seed_path=public_dir / "seed_traces.jsonl",
        output_dir=public_dir,
    )

    seed_rows = read_jsonl(public_dir / "seed_traces.jsonl")
    sft_rows = read_jsonl(public_dir / "sft_public_sample.jsonl")
    dpo_rows = read_jsonl(public_dir / "dpo_public_sample.jsonl")
    manifest_payload = read_json(public_dir / "manifest_public_sample.json")

    assert manifest.counts == EXPECTED_COUNTS
    assert manifest.split_counts == EXPECTED_SPLITS
    _assert_manifest_has_extension_merge_summary(manifest_payload)
    assert len(seed_rows) == EXPECTED_COUNTS["seed_rows"]
    assert len(sft_rows) == EXPECTED_COUNTS["sft_rows"]
    assert len(dpo_rows) == EXPECTED_COUNTS["dpo_pairs"]
    _assert_extension_rows_are_formal(seed_rows, sft_rows, dpo_rows)

    validation = validate_dataset_artifacts(
        sft_path=public_dir / "sft_public_sample.jsonl",
        dpo_path=public_dir / "dpo_public_sample.jsonl",
        manifest_path=public_dir / "manifest_public_sample.json",
        public=True,
    )
    assert validation.ok is True
    assert scan_paths([public_dir]).ok is True


def test_merge_form_fill_confirmation_marker_extension_candidates_cli_writes_evidence(
    tmp_path: Path,
    capsys,
) -> None:
    public_dir = _copy_current_public_sample_without_extension_candidates(tmp_path)
    evidence_dir = tmp_path / "merge-evidence"

    assert (
        data_cli.main(
            [
                "merge-form-fill-confirmation-marker-extension-candidates",
                "--candidate-seed",
                FORM_FILL_EXTENSION_CANDIDATE_SEED.as_posix(),
                "--seed",
                (public_dir / "seed_traces.jsonl").as_posix(),
                "--output",
                public_dir.as_posix(),
                "--evidence-output",
                evidence_dir.as_posix(),
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["counts"] == EXPECTED_COUNTS
    assert payload["split_counts"] == EXPECTED_SPLITS
    assert payload["source_summary"]["form_fill_confirmation_marker_extension_candidate_seed_rows"] == 12
    assert payload["evidence_paths"]["manifest"] == (evidence_dir / "manifest.json").as_posix()

    evidence = read_json(evidence_dir / "form_fill_confirmation_marker_extension_public_sample_merge.json")
    evidence_manifest = read_json(evidence_dir / "manifest.json")
    markdown = (evidence_dir / "form_fill_confirmation_marker_extension_public_sample_merge.md").read_text(
        encoding="utf-8"
    )
    assert evidence["evidence_kind"] == "form_fill_confirmation_marker_extension_public_sample_merge"
    assert evidence["pre_merge_public_sample_counts"] == PRE_MERGE_COUNTS
    assert evidence["candidate_source"]["candidate_dpo_pairs"] == 108
    assert evidence["candidate_source"]["dpo_rejection_deltas"] == EXPECTED_DPO_DELTAS
    assert evidence_manifest["formal_public_sample_counts"] == EXPECTED_COUNTS
    assert evidence_manifest["claims"]["held_out_generalization_recovered"] is False
    assert "does not prove held-out recovery" in markdown
    assert scan_paths([evidence_dir]).ok is True


def test_merge_form_fill_confirmation_marker_extension_candidates_cli_surfaces_validation_failure(
    tmp_path: Path,
    capsys,
    monkeypatch,
) -> None:
    public_dir = _copy_current_public_sample_without_extension_candidates(tmp_path)
    evidence_dir = tmp_path / "merge-evidence"
    real_evidence_builder = data_cli.form_fill_confirmation_marker_extension_public_sample_merge_evidence

    def fake_failed_evidence(*args, **kwargs):
        evidence = real_evidence_builder(*args, **kwargs)
        evidence["merge_status"] = "formal_public_sample_validation_failed"
        evidence["validation"] = {
            **evidence["validation"],
            "ok": False,
            "failures": ["forced validation failure"],
        }
        return evidence

    monkeypatch.setattr(
        data_cli,
        "form_fill_confirmation_marker_extension_public_sample_merge_evidence",
        fake_failed_evidence,
    )

    assert (
        data_cli.main(
            [
                "merge-form-fill-confirmation-marker-extension-candidates",
                "--candidate-seed",
                FORM_FILL_EXTENSION_CANDIDATE_SEED.as_posix(),
                "--seed",
                (public_dir / "seed_traces.jsonl").as_posix(),
                "--output",
                public_dir.as_posix(),
                "--evidence-output",
                evidence_dir.as_posix(),
            ]
        )
        == 1
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    evidence = read_json(evidence_dir / "form_fill_confirmation_marker_extension_public_sample_merge.json")
    assert evidence["validation"]["ok"] is False


def test_merge_form_fill_confirmation_marker_extension_candidates_rejects_unreviewed_rows(
    tmp_path: Path,
) -> None:
    public_dir = _copy_current_public_sample_without_extension_candidates(tmp_path)
    candidate_rows = read_jsonl(FORM_FILL_EXTENSION_CANDIDATE_SEED)
    unreviewed = dict(candidate_rows[0])
    unreviewed["id"] = "candidate-form-fill-confirmation-marker-extension-unreviewed-extra"
    write_jsonl(tmp_path / "candidate_seed_with_extra.jsonl", [*candidate_rows, unreviewed])

    with pytest.raises(
        ValueError,
        match="expected reviewed form-fill confirmation-marker extension candidate seed IDs",
    ):
        merge_form_fill_confirmation_marker_extension_candidates_into_public_sample(
            candidate_seed_path=tmp_path / "candidate_seed_with_extra.jsonl",
            seed_path=public_dir / "seed_traces.jsonl",
            output_dir=public_dir,
        )


def test_merge_form_fill_confirmation_marker_extension_candidates_rejects_already_formal_rows(
    tmp_path: Path,
) -> None:
    public_dir = _copy_current_public_sample_without_extension_candidates(tmp_path)
    candidate_rows = read_jsonl(FORM_FILL_EXTENSION_CANDIDATE_SEED)
    seed_path = public_dir / "seed_traces.jsonl"
    write_jsonl(seed_path, [*read_jsonl(seed_path), candidate_rows[0]])

    with pytest.raises(ValueError, match="confirmation-marker extension candidate seed IDs already exist"):
        merge_form_fill_confirmation_marker_extension_candidates_into_public_sample(
            candidate_seed_path=FORM_FILL_EXTENSION_CANDIDATE_SEED,
            seed_path=seed_path,
            output_dir=public_dir,
        )


def test_confirmation_marker_extension_merge_report_writer_rejects_contradictory_claim(
    tmp_path: Path,
) -> None:
    public_dir = _copy_current_public_sample_without_extension_candidates(tmp_path)
    manifest = merge_form_fill_confirmation_marker_extension_candidates_into_public_sample(
        candidate_seed_path=FORM_FILL_EXTENSION_CANDIDATE_SEED,
        seed_path=public_dir / "seed_traces.jsonl",
        output_dir=public_dir,
    )
    from voice2task.dataset import form_fill_confirmation_marker_extension_public_sample_merge_evidence

    evidence = form_fill_confirmation_marker_extension_public_sample_merge_evidence(
        manifest=manifest,
        candidate_seed_path=FORM_FILL_EXTENSION_CANDIDATE_SEED,
        pre_merge_counts=PRE_MERGE_COUNTS,
    )
    evidence["execution_scope"]["training_run"] = True

    with pytest.raises(ValueError, match="public-sample merge report cannot claim"):
        write_form_fill_confirmation_marker_extension_public_sample_merge_report(
            evidence,
            output_dir=tmp_path / "bad-report",
        )


def test_committed_formal_public_sample_contains_confirmation_marker_extension_candidates() -> None:
    manifest = read_json(PUBLIC_SAMPLE_DIR / "manifest_public_sample.json")
    seed_rows = read_jsonl(PUBLIC_SAMPLE_DIR / "seed_traces.jsonl")
    sft_rows = read_jsonl(PUBLIC_SAMPLE_DIR / "sft_public_sample.jsonl")
    dpo_rows = read_jsonl(PUBLIC_SAMPLE_DIR / "dpo_public_sample.jsonl")

    _assert_manifest_has_extension_merge_summary(manifest)
    _assert_extension_rows_are_formal(seed_rows, sft_rows, dpo_rows)
    assert scan_paths([PUBLIC_SAMPLE_DIR]).ok is True


def test_committed_form_fill_confirmation_marker_extension_merge_evidence_is_public_safe() -> None:
    evidence = read_json(MERGE_EVIDENCE_DIR / "form_fill_confirmation_marker_extension_public_sample_merge.json")
    evidence_manifest = read_json(MERGE_EVIDENCE_DIR / "manifest.json")

    assert evidence["evidence_kind"] == "form_fill_confirmation_marker_extension_public_sample_merge"
    assert evidence["pre_merge_public_sample_counts"] == HISTORICAL_PRE_MERGE_COUNTS
    assert evidence["execution_scope"]["training_run"] is False
    assert evidence["execution_scope"]["prediction_run"] is False
    assert evidence["execution_scope"]["a100_execution"] is False
    assert evidence["candidate_source"]["candidate_dpo_pairs"] == 108
    assert evidence_manifest["formal_public_sample_counts"] == HISTORICAL_EXPECTED_COUNTS
    assert evidence_manifest["formal_public_sample_split_counts"] == HISTORICAL_EXPECTED_SPLITS
    assert evidence_manifest["claims"]["held_out_generalization_recovered"] is False
    assert evidence_manifest["claims"]["model_recovery_claim"] is False
    assert evidence_manifest["claims"]["adapter_release"] is False
    assert evidence_manifest["claims"]["checkpoint_release"] is False
    assert evidence_manifest["claims"]["production_readiness_claim"] is False
    assert scan_paths([MERGE_EVIDENCE_DIR]).ok is True
