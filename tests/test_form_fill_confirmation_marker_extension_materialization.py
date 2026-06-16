import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

import voice2task.dataset as dataset
from voice2task.cli import data as data_cli
from voice2task.io import read_json, read_jsonl
from voice2task.leak_scan import scan_paths
from voice2task.reports import write_form_fill_confirmation_marker_extension_materialization_report

REPO_ROOT = Path(__file__).resolve().parents[1]
DESIGN_PATH = (
    REPO_ROOT
    / "reports"
    / "public-sample"
    / "form-fill-confirmation-marker-coverage-extension"
    / "form_fill_confirmation_marker_coverage_extension.json"
)
PUBLIC_SAMPLE_PATHS = [
    REPO_ROOT / "data" / "public-samples" / "seed_traces.jsonl",
    REPO_ROOT / "data" / "public-samples" / "sft_public_sample.jsonl",
    REPO_ROOT / "data" / "public-samples" / "dpo_public_sample.jsonl",
    REPO_ROOT / "data" / "public-samples" / "manifest_public_sample.json",
]
COMMITTED_CANDIDATE_SEED = (
    REPO_ROOT / "data" / "public-samples" / "form_fill_confirmation_marker_extension_seed_candidates.jsonl"
)
COMMITTED_REPORT_DIR = (
    REPO_ROOT
    / "reports"
    / "public-sample"
    / "form-fill-confirmation-marker-extension-materialized-candidates"
)
CURRENT_FORMAL_COUNTS = {"dpo_pairs": 742, "seed_rows": 86, "sft_rows": 240}


def _sha256_by_path(paths: list[Path]) -> dict[Path, str]:
    return {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}


def _assert_candidate_contract(row: dict[str, Any], field: str) -> None:
    contract = row["target_contract"]
    assert contract["task_type"] == "form_fill"
    assert contract["route"] == "fill_form"
    assert contract["safety"] == {"allow": True, "reason": "requires_confirmation"}
    assert contract["confirmation_required"] is True
    assert contract["slots"] == {"field": field}
    assert contract["normalized_command"] == f"填写{field}并确认"
    assert contract["language"] == "zh-CN"
    assert contract["contract_version"] == "v1"


def test_materialize_confirmation_marker_extension_candidates_writes_standalone_dataset(
    tmp_path: Path,
) -> None:
    public_sample_before = _sha256_by_path(PUBLIC_SAMPLE_PATHS)
    seed_output = tmp_path / "form_fill_confirmation_marker_extension_seed_candidates.jsonl"
    output_dir = tmp_path / "confirmation-marker-extension-materialized-candidates"

    paths = dataset.materialize_form_fill_confirmation_marker_extension_candidates(
        extension_design_path=DESIGN_PATH,
        seed_output_path=seed_output,
        output_dir=output_dir,
    )

    assert paths["seed"] == seed_output
    assert paths["sft"] == output_dir / "sft_candidate_rows.jsonl"
    assert paths["json"] == output_dir / "form_fill_confirmation_marker_extension_materialization.json"
    assert paths["markdown"] == output_dir / "form_fill_confirmation_marker_extension_materialization.md"
    assert paths["manifest"] == output_dir / "manifest.json"
    assert _sha256_by_path(PUBLIC_SAMPLE_PATHS) == public_sample_before

    seed_rows = read_jsonl(seed_output)
    sft_rows = read_jsonl(paths["sft"])
    materialization = read_json(paths["json"])
    manifest = read_json(paths["manifest"])
    markdown = paths["markdown"].read_text(encoding="utf-8")

    assert len(seed_rows) == 12
    assert len(sft_rows) == 12
    assert all(row["split"] == "train" for row in seed_rows)
    assert all(row["split"] == "train" for row in sft_rows)
    assert materialization["evidence_kind"] == "form_fill_confirmation_marker_extension_materialization"
    assert materialization["materialization_status"] == "candidate_dataset_materialized"
    assert materialization["source_extension_design"]["evidence_kind"] == (
        "form_fill_confirmation_marker_coverage_extension_design"
    )
    assert materialization["summary"] == {
        "candidate_case_count": 12,
        "candidate_seed_rows": 12,
        "candidate_sft_rows": 12,
        "derived_field_label_rows": 3,
        "family_level_candidate_label_rows": 9,
        "formal_public_sample_seed_rows": 86,
        "formal_public_sample_sft_rows": 240,
        "formal_public_sample_dpo_pairs": 742,
        "formal_public_sample_modified": False,
        "seed_traces_modified": False,
        "recommended_next_step": "review_candidate_extension_before_any_formal_public_sample_merge",
    }
    assert materialization["metric_authority"]["contract_exact_match"] == "authoritative_strict_metric"
    assert materialization["metric_authority"]["slot_f1"] == "authoritative_strict_metric"
    assert materialization["metric_authority"]["slot_f1_soft"] == "diagnostic_only_not_primary"
    assert materialization["execution_scope"]["new_candidate_data_generated"] is True
    assert materialization["execution_scope"]["formal_public_sample_modified"] is False
    assert materialization["execution_scope"]["seed_traces_modified"] is False
    assert materialization["execution_scope"]["training_run"] is False
    assert materialization["execution_scope"]["prediction_run"] is False
    assert materialization["execution_scope"]["dpo_run"] is False
    assert materialization["execution_scope"]["a100_execution"] is False
    assert materialization["claims"]["held_out_recovery_claim"] is False
    assert materialization["claims"]["model_recovery_claim"] is False
    assert materialization["claims"]["soft_slot_f1_primary_metric"] is False
    assert manifest["artifact_policy"]["candidate_data_only"] is True
    assert manifest["artifact_policy"]["formal_public_sample_files_modified"] is False
    assert manifest["artifact_policy"]["dpo_pairs_generated"] is False
    assert "candidate data only" in markdown
    assert "not recovered gold text" in markdown
    assert "slot_f1_soft` is diagnostic-only" in markdown

    seed_by_case = {row["provenance"]["source_case_id"]: row for row in seed_rows}
    derived = seed_by_case["ff-confirm-marker-extension-family-form_fill-dev-1"]
    assert derived["input_text"] == "填写手机号并确认"
    _assert_candidate_contract(derived, "手机号")
    assert derived["provenance"]["field_label_derivation_status"] == "derived_from_committed_coverage_examples"
    assert derived["provenance"]["field_label_provenance"] == "derived_from_committed_public_artifacts"

    non_derivable = seed_by_case["ff-confirm-marker-extension-family-confirmation-dev-1"]
    family_label = "公开候选字段-family-confirmation-dev-1"
    assert non_derivable["input_text"] == f"填写{family_label}并确认"
    _assert_candidate_contract(non_derivable, family_label)
    assert non_derivable["provenance"]["field_label_derivation_status"] == (
        "not_derivable_from_committed_coverage_policy_artifacts"
    )
    assert non_derivable["provenance"]["field_label_provenance"] == (
        "public_safe_family_level_candidate_label_not_recovered_gold_text"
    )
    assert non_derivable["provenance"]["candidate_status"] == "standalone_not_formal_public_sample"

    assert all(
        row["provenance"]["source_mode"] == "form_fill_confirmation_marker_extension_candidate_seed"
        for row in seed_rows
    )
    assert all(row["provenance"]["candidate_status"] == "standalone_not_formal_public_sample" for row in seed_rows)
    assert all(
        row["provenance"]["source_mode"] == "form_fill_confirmation_marker_extension_candidate" for row in sft_rows
    )
    assert scan_paths([seed_output, output_dir]).ok is True


def test_materialize_confirmation_marker_extension_candidates_cli(tmp_path: Path, capsys: Any) -> None:
    seed_output = tmp_path / "form_fill_confirmation_marker_extension_seed_candidates.jsonl"
    output_dir = tmp_path / "materialized-candidates"

    assert (
        data_cli.main(
            [
                "materialize-form-fill-confirmation-marker-extension-candidates",
                "--extension-design",
                DESIGN_PATH.as_posix(),
                "--seed-output",
                seed_output.as_posix(),
                "--output",
                output_dir.as_posix(),
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["summary"]["candidate_case_count"] == 12
    assert payload["summary"]["candidate_sft_rows"] == 12
    assert payload["execution_scope"]["formal_public_sample_modified"] is False
    assert payload["execution_scope"]["dpo_run"] is False
    assert payload["paths"]["seed"] == seed_output.as_posix()
    assert payload["paths"]["manifest"] == (output_dir / "manifest.json").as_posix()
    assert scan_paths([seed_output, output_dir]).ok is True


@pytest.mark.parametrize("protected_path", PUBLIC_SAMPLE_PATHS)
def test_materialize_confirmation_marker_extension_candidates_rejects_formal_public_output_path(
    tmp_path: Path,
    protected_path: Path,
) -> None:
    before_hash = hashlib.sha256(protected_path.read_bytes()).hexdigest()

    with pytest.raises(ValueError, match="must not overwrite formal public sample files"):
        dataset.materialize_form_fill_confirmation_marker_extension_candidates(
            extension_design_path=DESIGN_PATH,
            seed_output_path=protected_path,
            output_dir=tmp_path / "materialized-candidates",
        )

    assert hashlib.sha256(protected_path.read_bytes()).hexdigest() == before_hash


def test_committed_confirmation_marker_extension_materialized_candidates_are_public_safe() -> None:
    public_manifest = read_json(REPO_ROOT / "data" / "public-samples" / "manifest_public_sample.json")
    materialization = read_json(
        COMMITTED_REPORT_DIR / "form_fill_confirmation_marker_extension_materialization.json"
    )
    manifest = read_json(COMMITTED_REPORT_DIR / "manifest.json")
    seed_rows = read_jsonl(COMMITTED_CANDIDATE_SEED)
    sft_rows = read_jsonl(COMMITTED_REPORT_DIR / "sft_candidate_rows.jsonl")

    assert public_manifest["counts"] == CURRENT_FORMAL_COUNTS
    assert materialization["summary"]["candidate_case_count"] == 12
    assert materialization["summary"]["candidate_seed_rows"] == 12
    assert materialization["summary"]["candidate_sft_rows"] == 12
    assert materialization["summary"]["formal_public_sample_modified"] is False
    assert materialization["metric_authority"]["slot_f1_soft"] == "diagnostic_only_not_primary"
    assert manifest["artifact_policy"]["formal_public_sample_files_modified"] is False
    assert manifest["artifact_policy"]["dpo_pairs_generated"] is False
    assert manifest["execution_scope"]["training_run"] is False
    assert manifest["execution_scope"]["prediction_run"] is False
    assert manifest["execution_scope"]["dpo_run"] is False
    assert len(seed_rows) == 12
    assert len(sft_rows) == 12
    assert scan_paths([COMMITTED_CANDIDATE_SEED, COMMITTED_REPORT_DIR]).ok is True


def test_confirmation_marker_extension_report_writer_rejects_contradictory_scope(
    tmp_path: Path,
) -> None:
    materialization = read_json(
        COMMITTED_REPORT_DIR / "form_fill_confirmation_marker_extension_materialization.json"
    )
    sft_rows = read_jsonl(COMMITTED_REPORT_DIR / "sft_candidate_rows.jsonl")
    materialization["execution_scope"]["training_run"] = True

    with pytest.raises(ValueError, match="candidate-only report cannot claim"):
        write_form_fill_confirmation_marker_extension_materialization_report(
            materialization,
            output_dir=tmp_path / "bad-report",
            sft_rows=sft_rows,
        )
