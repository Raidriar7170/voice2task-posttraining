import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from voice2task.cli import data as data_cli
from voice2task.dataset import check_form_fill_confirmation_marker_extension_candidate_integration_preview
from voice2task.io import read_json, read_jsonl, write_jsonl
from voice2task.leak_scan import scan_paths
from voice2task.reports import write_form_fill_confirmation_marker_extension_candidate_integration_preview_report
from voice2task.validation import validate_dataset_artifacts

REPO_ROOT = Path(__file__).resolve().parents[1]
PUBLIC_SAMPLE_DIR = REPO_ROOT / "data" / "public-samples"
FORMAL_SEED = PUBLIC_SAMPLE_DIR / "seed_traces.jsonl"
FORM_FILL_EXTENSION_CANDIDATE_SEED = (
    PUBLIC_SAMPLE_DIR / "form_fill_confirmation_marker_extension_seed_candidates.jsonl"
)
PUBLIC_SAMPLE_PATHS = [
    FORMAL_SEED,
    PUBLIC_SAMPLE_DIR / "sft_public_sample.jsonl",
    PUBLIC_SAMPLE_DIR / "dpo_public_sample.jsonl",
    PUBLIC_SAMPLE_DIR / "manifest_public_sample.json",
]
COMMITTED_REPORT_DIR = (
    REPO_ROOT
    / "reports"
    / "public-sample"
    / "form-fill-confirmation-marker-extension-candidate-integration-preview"
)
PRE_MERGE_FORMAL_COUNTS = {"dpo_pairs": 1938, "seed_rows": 228, "sft_rows": 663}
CURRENT_FORMAL_COUNTS = {"dpo_pairs": 2046, "seed_rows": 240, "sft_rows": 675}
EXPECTED_PREVIEW_COUNTS = {"dpo_pairs": 2046, "seed_rows": 240, "sft_rows": 675}
EXPECTED_PREVIEW_SPLITS = {"dev": 207, "test": 207, "train": 261}
HISTORICAL_PRE_MERGE_FORMAL_COUNTS = {"dpo_pairs": 742, "seed_rows": 86, "sft_rows": 240}
HISTORICAL_PREVIEW_COUNTS = {"dpo_pairs": 850, "seed_rows": 98, "sft_rows": 252}
EXPECTED_CANDIDATE_IDS = {row["id"] for row in read_jsonl(FORM_FILL_EXTENSION_CANDIDATE_SEED)}


def _sha256_by_path(paths: list[Path]) -> dict[Path, str]:
    return {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}


def _write_pre_merge_formal_seed(tmp_path: Path) -> Path:
    seed_path = tmp_path / "pre_merge_seed_traces.jsonl"
    seed_rows = [
        row for row in read_jsonl(FORMAL_SEED) if row["id"] not in EXPECTED_CANDIDATE_IDS
    ]
    assert len(seed_rows) == PRE_MERGE_FORMAL_COUNTS["seed_rows"]
    write_jsonl(seed_path, seed_rows)
    return seed_path


def test_check_form_fill_confirmation_marker_extension_candidate_integration_preview_builds_report_scoped_dataset(
    tmp_path: Path,
) -> None:
    public_sample_before = _sha256_by_path(PUBLIC_SAMPLE_PATHS)
    pre_merge_seed = _write_pre_merge_formal_seed(tmp_path)
    output_dir = tmp_path / "form-fill-confirmation-marker-extension-candidate-integration-preview"

    paths = check_form_fill_confirmation_marker_extension_candidate_integration_preview(
        candidate_seed_path=FORM_FILL_EXTENSION_CANDIDATE_SEED,
        seed_path=pre_merge_seed,
        output_dir=output_dir,
    )

    assert paths["preview_seed"] == output_dir / "public-sample-preview" / "seed_traces.jsonl"
    assert paths["preview_sft"] == output_dir / "public-sample-preview" / "sft_public_sample.jsonl"
    assert paths["preview_dpo"] == output_dir / "public-sample-preview" / "dpo_public_sample.jsonl"
    assert paths["preview_manifest"] == output_dir / "public-sample-preview" / "manifest_public_sample.json"
    assert paths["json"] == output_dir / "form_fill_confirmation_marker_extension_candidate_integration_preview.json"
    assert paths["markdown"] == output_dir / "form_fill_confirmation_marker_extension_candidate_integration_preview.md"
    assert paths["manifest"] == output_dir / "manifest.json"
    assert _sha256_by_path(PUBLIC_SAMPLE_PATHS) == public_sample_before

    preview_seed_rows = read_jsonl(paths["preview_seed"])
    preview_sft_rows = read_jsonl(paths["preview_sft"])
    preview_dpo_rows = read_jsonl(paths["preview_dpo"])
    preview_manifest = read_json(paths["preview_manifest"])
    evidence = read_json(paths["json"])
    manifest = read_json(paths["manifest"])
    markdown = paths["markdown"].read_text(encoding="utf-8")

    assert len(preview_seed_rows) == EXPECTED_PREVIEW_COUNTS["seed_rows"]
    assert len(preview_sft_rows) == EXPECTED_PREVIEW_COUNTS["sft_rows"]
    assert len(preview_dpo_rows) == EXPECTED_PREVIEW_COUNTS["dpo_pairs"]
    assert preview_manifest["counts"] == EXPECTED_PREVIEW_COUNTS
    assert preview_manifest["split_counts"] == EXPECTED_PREVIEW_SPLITS
    assert evidence["evidence_kind"] == "form_fill_confirmation_marker_extension_candidate_integration_preview"
    assert evidence["integration_status"] == "preview_build_validated"
    assert evidence["formal_public_sample_counts_before"] == PRE_MERGE_FORMAL_COUNTS
    assert evidence["preview_counts"] == EXPECTED_PREVIEW_COUNTS
    assert evidence["candidate_source"]["candidate_seed_rows"] == 12
    assert evidence["candidate_source"]["candidate_sft_rows"] == 12
    assert evidence["candidate_source"]["candidate_preview_dpo_pairs"] == 108
    assert evidence["validation"]["ok"] is True
    assert evidence["execution_scope"]["formal_public_sample_modified"] is False
    assert evidence["execution_scope"]["preview_only_not_formal_public_sample"] is True
    assert evidence["execution_scope"]["preview_dpo_pairs_generated"] is True
    assert evidence["execution_scope"]["training_run"] is False
    assert evidence["execution_scope"]["prediction_run"] is False
    assert evidence["execution_scope"]["a100_execution"] is False
    assert evidence["execution_scope"]["evaluator_metric_change"] is False
    assert evidence["claims"]["strict_contract_exact_match_primary_metric"] is True
    assert evidence["claims"]["soft_slot_f1_primary_metric"] is False
    assert evidence["claims"]["held_out_generalization_recovered"] is False
    assert manifest["artifact_policy"]["formal_public_sample_files_modified"] is False
    assert manifest["artifact_policy"]["preview_only_not_formal_public_sample"] is True
    assert manifest["artifact_policy"]["preview_dpo_pairs_generated"] is True
    assert manifest["claims"]["model_recovery_claim"] is False
    assert manifest["claims"]["held_out_generalization_recovered"] is False
    for artifact_ref in manifest["diagnostic_artifacts"].values():
        assert not Path(artifact_ref).is_absolute()
        assert (output_dir / artifact_ref).exists()
    assert "Preview DPO pairs are data-construction evidence only" in markdown
    assert "strict `contract_exact_match` remains primary" in markdown
    assert "Soft slot F1 and semantic equivalence remain diagnostic-only" in markdown
    assert "historical builder-compatibility evidence" in markdown
    assert "Current formal public-sample state must come from the corresponding merge report" in markdown
    assert "decide whether to formally merge" not in markdown

    preview_candidate_rows = [
        row
        for row in preview_seed_rows
        if (row.get("provenance") or {}).get("source_mode")
        == "form_fill_confirmation_marker_extension_preview_public_seed"
    ]
    assert len(preview_candidate_rows) == 12
    assert all(
        row["provenance"]["candidate_status"] == "preview_only_not_formal_public_sample"
        for row in preview_candidate_rows
    )
    assert all(row["provenance"]["public_safe"] is True for row in preview_candidate_rows)

    validation = validate_dataset_artifacts(
        sft_path=paths["preview_sft"],
        dpo_path=paths["preview_dpo"],
        manifest_path=paths["preview_manifest"],
        public=True,
    )
    assert validation.ok is True
    assert scan_paths([output_dir]).ok is True


def test_check_form_fill_confirmation_marker_extension_candidate_integration_preview_cli(
    tmp_path: Path,
    capsys: Any,
) -> None:
    pre_merge_seed = _write_pre_merge_formal_seed(tmp_path)
    output_dir = tmp_path / "integration-preview"

    assert (
        data_cli.main(
            [
                "check-form-fill-confirmation-marker-extension-candidate-integration",
                "--candidate-seed",
                FORM_FILL_EXTENSION_CANDIDATE_SEED.as_posix(),
                "--seed",
                pre_merge_seed.as_posix(),
                "--output",
                output_dir.as_posix(),
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["preview_counts"] == EXPECTED_PREVIEW_COUNTS
    assert payload["preview_split_counts"] == EXPECTED_PREVIEW_SPLITS
    assert payload["candidate_source"]["candidate_preview_dpo_pairs"] == 108
    assert payload["validation"]["ok"] is True
    assert payload["execution_scope"]["formal_public_sample_modified"] is False
    assert payload["execution_scope"]["preview_only_not_formal_public_sample"] is True
    assert payload["paths"]["manifest"] == (output_dir / "manifest.json").as_posix()
    assert scan_paths([output_dir]).ok is True


def test_check_form_fill_confirmation_marker_extension_candidate_integration_preview_rejects_unreviewed_rows(
    tmp_path: Path,
) -> None:
    pre_merge_seed = _write_pre_merge_formal_seed(tmp_path)
    candidate_rows = read_jsonl(FORM_FILL_EXTENSION_CANDIDATE_SEED)
    unreviewed = dict(candidate_rows[0])
    unreviewed["id"] = "candidate-form-fill-confirmation-marker-extension-extra"
    candidate_path = tmp_path / "candidate_seed_with_extra.jsonl"
    write_jsonl(candidate_path, [*candidate_rows, unreviewed])

    with pytest.raises(
        ValueError,
        match="expected reviewed form-fill confirmation-marker extension candidate seed IDs",
    ):
        check_form_fill_confirmation_marker_extension_candidate_integration_preview(
            candidate_seed_path=candidate_path,
            seed_path=pre_merge_seed,
            output_dir=tmp_path / "preview",
        )


def test_check_form_fill_confirmation_marker_extension_candidate_integration_preview_rejects_already_formal_ids(
    tmp_path: Path,
) -> None:
    pre_merge_seed = _write_pre_merge_formal_seed(tmp_path)
    candidate_rows = read_jsonl(FORM_FILL_EXTENSION_CANDIDATE_SEED)
    formal_rows = read_jsonl(pre_merge_seed)
    formal_path = tmp_path / "seed_traces.jsonl"
    write_jsonl(formal_path, [*formal_rows, candidate_rows[0]])

    with pytest.raises(ValueError, match="candidate IDs already exist"):
        check_form_fill_confirmation_marker_extension_candidate_integration_preview(
            candidate_seed_path=FORM_FILL_EXTENSION_CANDIDATE_SEED,
            seed_path=formal_path,
            output_dir=tmp_path / "preview",
        )


def test_form_fill_confirmation_marker_extension_candidate_integration_report_writer_rejects_contradictory_scope(
    tmp_path: Path,
) -> None:
    pre_merge_seed = _write_pre_merge_formal_seed(tmp_path)
    paths = check_form_fill_confirmation_marker_extension_candidate_integration_preview(
        candidate_seed_path=FORM_FILL_EXTENSION_CANDIDATE_SEED,
        seed_path=pre_merge_seed,
        output_dir=tmp_path / "source-preview",
    )
    evidence = read_json(paths["json"])
    evidence["execution_scope"]["training_run"] = True

    with pytest.raises(ValueError, match="preview integration report cannot claim"):
        write_form_fill_confirmation_marker_extension_candidate_integration_preview_report(
            evidence,
            output_dir=tmp_path / "bad-report",
        )


def test_form_fill_confirmation_marker_extension_candidate_integration_report_writer_rejects_prediction_repair_claim(
    tmp_path: Path,
) -> None:
    pre_merge_seed = _write_pre_merge_formal_seed(tmp_path)
    paths = check_form_fill_confirmation_marker_extension_candidate_integration_preview(
        candidate_seed_path=FORM_FILL_EXTENSION_CANDIDATE_SEED,
        seed_path=pre_merge_seed,
        output_dir=tmp_path / "source-preview",
    )
    evidence = read_json(paths["json"])
    evidence["execution_scope"]["prediction_repair_or_replacement"] = True

    with pytest.raises(ValueError, match="preview integration report cannot claim"):
        write_form_fill_confirmation_marker_extension_candidate_integration_preview_report(
            evidence,
            output_dir=tmp_path / "bad-report",
        )


def test_committed_form_fill_confirmation_marker_extension_candidate_integration_preview_is_public_safe() -> None:
    public_manifest = read_json(PUBLIC_SAMPLE_DIR / "manifest_public_sample.json")
    evidence = read_json(
        COMMITTED_REPORT_DIR / "form_fill_confirmation_marker_extension_candidate_integration_preview.json"
    )
    manifest = read_json(COMMITTED_REPORT_DIR / "manifest.json")
    preview_manifest = read_json(COMMITTED_REPORT_DIR / "public-sample-preview" / "manifest_public_sample.json")

    assert public_manifest["counts"] == CURRENT_FORMAL_COUNTS
    assert evidence["formal_public_sample_counts_before"] == HISTORICAL_PRE_MERGE_FORMAL_COUNTS
    assert evidence["preview_counts"] == HISTORICAL_PREVIEW_COUNTS
    assert evidence["candidate_source"]["candidate_seed_rows"] == 12
    assert evidence["candidate_source"]["candidate_preview_dpo_pairs"] == 108
    assert evidence["execution_scope"]["formal_public_sample_modified"] is False
    assert evidence["execution_scope"]["preview_only_not_formal_public_sample"] is True
    assert evidence["execution_scope"]["training_run"] is False
    assert evidence["execution_scope"]["prediction_run"] is False
    assert manifest["artifact_policy"]["formal_public_sample_files_modified"] is False
    assert manifest["artifact_policy"]["preview_only_not_formal_public_sample"] is True
    assert manifest["claims"]["model_recovery_claim"] is False
    assert manifest["claims"]["held_out_generalization_recovered"] is False
    assert preview_manifest["counts"] == HISTORICAL_PREVIEW_COUNTS
    markdown = (
        COMMITTED_REPORT_DIR / "form_fill_confirmation_marker_extension_candidate_integration_preview.md"
    ).read_text(encoding="utf-8")
    assert "Current formal public-sample state must come from the corresponding merge report" in markdown
    assert "decide whether to formally merge" not in markdown
    assert scan_paths([COMMITTED_REPORT_DIR]).ok is True
