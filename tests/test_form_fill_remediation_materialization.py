import hashlib
import json
from pathlib import Path
from typing import Any

from voice2task.cli import data as data_cli
from voice2task.dataset import materialize_form_fill_remediation_candidates
from voice2task.io import read_json, read_jsonl
from voice2task.leak_scan import scan_paths

REPO_ROOT = Path(__file__).resolve().parents[1]
DESIGN_PATH = (
    REPO_ROOT
    / "reports"
    / "public-sample"
    / "form-fill-remediation-case-design"
    / "form_fill_remediation_case_design.json"
)
PUBLIC_SAMPLE_PATHS = [
    REPO_ROOT / "data" / "public-samples" / "seed_traces.jsonl",
    REPO_ROOT / "data" / "public-samples" / "sft_public_sample.jsonl",
    REPO_ROOT / "data" / "public-samples" / "dpo_public_sample.jsonl",
    REPO_ROOT / "data" / "public-samples" / "manifest_public_sample.json",
]
COMMITTED_CANDIDATE_SEED = REPO_ROOT / "data" / "public-samples" / "form_fill_remediation_seed_candidates.jsonl"
COMMITTED_REPORT_DIR = REPO_ROOT / "reports" / "public-sample" / "form-fill-remediation-materialized-candidates"
CURRENT_FORMAL_COUNTS = {"dpo_pairs": 2046, "seed_rows": 240, "sft_rows": 675}


def _sha256_by_path(paths: list[Path]) -> dict[Path, str]:
    return {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}


def test_materialize_form_fill_remediation_candidates_writes_bounded_candidate_dataset(
    tmp_path: Path,
) -> None:
    public_sample_before = _sha256_by_path(PUBLIC_SAMPLE_PATHS)
    seed_output = tmp_path / "form_fill_remediation_seed_candidates.jsonl"
    output_dir = tmp_path / "form-fill-remediation-materialized-candidates"

    paths = materialize_form_fill_remediation_candidates(
        case_design_path=DESIGN_PATH,
        seed_output_path=seed_output,
        output_dir=output_dir,
    )

    assert paths["seed"] == seed_output
    assert paths["sft"] == output_dir / "sft_candidate_rows.jsonl"
    assert paths["json"] == output_dir / "form_fill_remediation_materialization.json"
    assert paths["markdown"] == output_dir / "form_fill_remediation_materialization.md"
    assert paths["manifest"] == output_dir / "manifest.json"
    assert _sha256_by_path(PUBLIC_SAMPLE_PATHS) == public_sample_before

    seed_rows = read_jsonl(seed_output)
    sft_rows = read_jsonl(paths["sft"])
    materialization = read_json(paths["json"])
    manifest = read_json(paths["manifest"])
    markdown = paths["markdown"].read_text(encoding="utf-8")

    assert materialization["evidence_kind"] == "form_fill_remediation_materialization"
    assert materialization["materialization_status"] == "candidate_dataset_materialized"
    assert materialization["summary"] == {
        "candidate_group_count": 3,
        "candidate_seed_rows": 9,
        "candidate_sft_rows": 9,
        "formal_public_sample_seed_rows": CURRENT_FORMAL_COUNTS["seed_rows"],
        "formal_public_sample_sft_rows": CURRENT_FORMAL_COUNTS["sft_rows"],
        "formal_public_sample_dpo_pairs": CURRENT_FORMAL_COUNTS["dpo_pairs"],
        "public_sample_modified": False,
        "recommended_next_step": "run_local_form_fill_candidate_integration_check",
    }
    assert materialization["execution_scope"]["new_candidate_data_generated"] is True
    assert materialization["execution_scope"]["public_sample_modified"] is False
    assert materialization["execution_scope"]["seed_traces_modified"] is False
    assert materialization["execution_scope"]["training_run"] is False
    assert materialization["execution_scope"]["prediction_run"] is False
    assert materialization["execution_scope"]["dpo_run"] is False
    assert materialization["claims"]["held_out_generalization_recovered"] is False
    assert materialization["claims"]["model_recovery_claim"] is False
    assert materialization["claims"]["soft_slot_f1_primary_metric"] is False
    assert manifest["artifact_policy"]["formal_public_sample_files_modified"] is False
    assert manifest["artifact_policy"]["dpo_pairs_generated"] is False
    assert "candidate data only" in markdown
    assert "not merged into seed_traces.jsonl" in markdown

    assert len(seed_rows) == 9
    assert len(sft_rows) == 9
    assert all(row["split"] == "train" for row in seed_rows)
    assert all(row["split"] == "train" for row in sft_rows)
    assert all(row["provenance"]["source_mode"] == "form_fill_remediation_candidate_seed" for row in seed_rows)
    assert all(row["provenance"]["candidate_status"] == "standalone_not_formal_public_sample" for row in seed_rows)

    seed_by_id = {row["id"]: row for row in seed_rows}
    field_case = seed_by_id["candidate-form-fill-remediation-ff-field-shipping-address"]
    assert field_case["input_text"] == "填写收货地址"
    assert field_case["target_contract"]["slots"] == {"field": "收货地址"}
    assert field_case["target_contract"]["normalized_command"] == "填写收货地址并确认"
    assert field_case["provenance"]["source_expected_normalized_command_pattern"] == "填写收货地址"

    boundary_case = seed_by_id["candidate-form-fill-remediation-ff-boundary-delivery-info"]
    assert boundary_case["input_text"] == "确认前填写配送信息"
    assert boundary_case["target_contract"]["slots"] == {"field": "配送信息"}
    assert boundary_case["target_contract"]["normalized_command"] == "填写配送信息并确认"
    assert boundary_case["target_contract"]["safety"] == {"allow": True, "reason": "requires_confirmation"}
    assert boundary_case["target_contract"]["confirmation_required"] is True

    sft_by_id = {row["id"]: row for row in sft_rows}
    original = sft_by_id["candidate-form-fill-remediation-ff-confirm-phone"]
    assert original["provenance"]["source_mode"] == "form_fill_remediation_candidate"
    assert original["provenance"]["source_case_group_id"] == "form-fill-confirmation-marker-preservation"
    assert original["provenance"]["source_case_id"] == "ff-confirm-phone"
    assert scan_paths([seed_output, output_dir]).ok is True


def test_materialize_form_fill_remediation_candidates_cli(tmp_path: Path, capsys: Any) -> None:
    seed_output = tmp_path / "form_fill_remediation_seed_candidates.jsonl"
    output_dir = tmp_path / "materialized-candidates"

    assert (
        data_cli.main(
            [
                "materialize-form-fill-remediation-candidates",
                "--case-design",
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
    assert payload["summary"]["candidate_group_count"] == 3
    assert payload["summary"]["candidate_sft_rows"] == 9
    assert payload["execution_scope"]["public_sample_modified"] is False
    assert payload["paths"]["seed"] == seed_output.as_posix()
    assert payload["paths"]["manifest"] == (output_dir / "manifest.json").as_posix()
    assert scan_paths([seed_output, output_dir]).ok is True


def test_committed_form_fill_remediation_materialized_candidates_are_public_safe() -> None:
    public_manifest = read_json(REPO_ROOT / "data" / "public-samples" / "manifest_public_sample.json")
    materialization = read_json(COMMITTED_REPORT_DIR / "form_fill_remediation_materialization.json")
    manifest = read_json(COMMITTED_REPORT_DIR / "manifest.json")
    seed_rows = read_jsonl(COMMITTED_CANDIDATE_SEED)
    sft_rows = read_jsonl(COMMITTED_REPORT_DIR / "sft_candidate_rows.jsonl")

    assert public_manifest["counts"] == CURRENT_FORMAL_COUNTS
    assert materialization["summary"]["candidate_group_count"] == 3
    assert materialization["summary"]["candidate_seed_rows"] == 9
    assert materialization["summary"]["candidate_sft_rows"] == 9
    assert materialization["summary"]["public_sample_modified"] is False
    assert manifest["execution_scope"]["training_run"] is False
    assert manifest["execution_scope"]["prediction_run"] is False
    assert manifest["execution_scope"]["dpo_run"] is False
    assert len(seed_rows) == 9
    assert len(sft_rows) == 9
    assert scan_paths([COMMITTED_CANDIDATE_SEED, COMMITTED_REPORT_DIR]).ok is True
