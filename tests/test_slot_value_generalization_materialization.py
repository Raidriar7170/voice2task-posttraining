import hashlib
import json
from pathlib import Path
from typing import Any

from voice2task.cli import data as data_cli
from voice2task.dataset import materialize_slot_value_generalization_candidates
from voice2task.io import read_json, read_jsonl
from voice2task.leak_scan import scan_paths

REPO_ROOT = Path(__file__).resolve().parents[1]
DESIGN_DIR = REPO_ROOT / "reports" / "public-sample" / "slot-value-generalization-case-design"
DESIGN_PATH = DESIGN_DIR / "slot_value_generalization_case_design.json"
PUBLIC_SAMPLE_PATHS = [
    REPO_ROOT / "data" / "public-samples" / "seed_traces.jsonl",
    REPO_ROOT / "data" / "public-samples" / "sft_public_sample.jsonl",
    REPO_ROOT / "data" / "public-samples" / "dpo_public_sample.jsonl",
    REPO_ROOT / "data" / "public-samples" / "manifest_public_sample.json",
]
COMMITTED_CANDIDATE_SEED = REPO_ROOT / "data" / "public-samples" / "slot_value_generalization_seed_candidates.jsonl"
COMMITTED_REPORT_DIR = REPO_ROOT / "reports" / "public-sample" / "slot-value-generalization-materialized-candidates"
CURRENT_FORMAL_COUNTS = {"dpo_pairs": 2046, "seed_rows": 240, "sft_rows": 675}
CURRENT_FORMAL_SPLITS = {"dev": 207, "test": 207, "train": 261}


def _sha256_by_path(paths: list[Path]) -> dict[Path, str]:
    return {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}


def test_materialize_slot_value_generalization_candidates_writes_bounded_candidate_dataset(
    tmp_path: Path,
) -> None:
    public_sample_before = _sha256_by_path(PUBLIC_SAMPLE_PATHS)
    seed_output = tmp_path / "slot_value_generalization_seed_candidates.jsonl"
    output_dir = tmp_path / "materialized-candidates"

    paths = materialize_slot_value_generalization_candidates(
        case_design_path=DESIGN_PATH,
        seed_output_path=seed_output,
        output_dir=output_dir,
    )

    assert paths["seed"] == seed_output
    assert paths["sft"] == output_dir / "sft_candidate_rows.jsonl"
    assert paths["json"] == output_dir / "slot_value_generalization_materialization.json"
    assert paths["markdown"] == output_dir / "slot_value_generalization_materialization.md"
    assert paths["manifest"] == output_dir / "manifest.json"
    assert _sha256_by_path(PUBLIC_SAMPLE_PATHS) == public_sample_before

    seed_rows = read_jsonl(seed_output)
    sft_rows = read_jsonl(paths["sft"])
    materialization = read_json(paths["json"])
    manifest = read_json(paths["manifest"])
    markdown = paths["markdown"].read_text(encoding="utf-8")

    assert materialization["evidence_kind"] == "slot_value_generalization_materialization"
    assert materialization["materialization_status"] == "candidate_dataset_materialized"
    assert materialization["summary"] == {
        "candidate_group_count": 4,
        "candidate_seed_rows": 4,
        "candidate_sft_rows": 12,
        "formal_public_sample_seed_rows": CURRENT_FORMAL_COUNTS["seed_rows"],
        "formal_public_sample_sft_rows": CURRENT_FORMAL_COUNTS["sft_rows"],
        "formal_public_sample_dpo_pairs": CURRENT_FORMAL_COUNTS["dpo_pairs"],
        "formal_public_sample_has_slot_value_candidates": True,
        "public_sample_modified": False,
        "recommended_next_step": "decide_candidate_merge_or_local_sft_probe",
    }
    assert materialization["execution_scope"]["new_candidate_data_generated"] is True
    assert materialization["execution_scope"]["public_sample_modified"] is False
    assert materialization["execution_scope"]["training_run"] is False
    assert materialization["execution_scope"]["prediction_run"] is False
    assert materialization["execution_scope"]["dpo_run"] is False
    assert materialization["claims"]["held_out_generalization_recovered"] is False
    assert materialization["claims"]["model_recovery_claim"] is False
    assert materialization["claims"]["soft_slot_f1_primary_metric"] is False
    assert manifest["artifact_policy"]["formal_public_sample_files_modified"] is False
    assert manifest["artifact_policy"]["dpo_pairs_generated"] is False
    assert "candidate data only" in markdown
    assert "does not rewrite formal public sample files" in markdown

    assert {row["id"] for row in seed_rows} == {
        "candidate-blocked-payment-canonical-command",
        "candidate-clarify-ambiguous-canonical-scope",
        "candidate-form-email-canonical-field",
        "candidate-navigate-open-url-canonical-command",
    }
    assert len(seed_rows) == 4
    assert len(sft_rows) == 12
    assert all(row["split"] == "train" for row in seed_rows)
    assert all(row["split"] == "train" for row in sft_rows)

    seed_by_id = {row["id"]: row for row in seed_rows}
    assert seed_by_id["candidate-form-email-canonical-field"]["target_contract"]["slots"] == {"field": "邮箱"}
    assert seed_by_id["candidate-form-email-canonical-field"]["target_contract"]["normalized_command"] == (
        "填写邮箱并确认"
    )
    assert seed_by_id["candidate-clarify-ambiguous-canonical-scope"]["target_contract"]["slots"] == {
        "ambiguity": "目标不明确，未指定具体网站或页面"
    }
    assert seed_by_id["candidate-navigate-open-url-canonical-command"]["target_contract"]["slots"] == {
        "url": "https://example.com"
    }
    assert seed_by_id["candidate-navigate-open-url-canonical-command"]["target_contract"]["normalized_command"] == (
        "打开示例网站"
    )
    assert seed_by_id["candidate-blocked-payment-canonical-command"]["target_contract"]["safety"] == {
        "allow": False,
        "reason": "unsafe_payment",
    }
    assert seed_by_id["candidate-blocked-payment-canonical-command"]["target_contract"]["normalized_command"] == (
        "拒绝代替用户付款"
    )

    sft_by_id = {row["id"]: row for row in sft_rows}
    original = sft_by_id["candidate-form-email-canonical-field"]
    augmentation = sft_by_id["candidate-form-email-canonical-field-aug-1"]
    assert original["provenance"]["source_mode"] == "slot_value_generalization_candidate"
    assert original["provenance"]["source_case_group_id"] == "form-email-slot-value-language-variant"
    assert augmentation["provenance"]["source_mode"] == "schema_preserving_augmentation"
    assert augmentation["provenance"]["source_case_group_id"] == "form-email-slot-value-language-variant"
    assert augmentation["target_contract"] == original["target_contract"]
    assert scan_paths([seed_output, output_dir]).ok is True


def test_materialize_slot_value_generalization_candidates_cli(tmp_path: Path, capsys: Any) -> None:
    seed_output = tmp_path / "slot_value_generalization_seed_candidates.jsonl"
    output_dir = tmp_path / "materialized-candidates"

    assert (
        data_cli.main(
            [
                "materialize-slot-value-candidates",
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
    assert payload["summary"]["candidate_group_count"] == 4
    assert payload["summary"]["candidate_sft_rows"] == 12
    assert payload["execution_scope"]["public_sample_modified"] is False
    assert payload["paths"]["seed"] == seed_output.as_posix()
    assert payload["paths"]["manifest"] == (output_dir / "manifest.json").as_posix()
    assert scan_paths([seed_output, output_dir]).ok is True


def test_committed_slot_value_generalization_materialized_candidates_are_public_safe() -> None:
    public_manifest = read_json(REPO_ROOT / "data" / "public-samples" / "manifest_public_sample.json")
    materialization = read_json(COMMITTED_REPORT_DIR / "slot_value_generalization_materialization.json")
    manifest = read_json(COMMITTED_REPORT_DIR / "manifest.json")
    seed_rows = read_jsonl(COMMITTED_CANDIDATE_SEED)
    sft_rows = read_jsonl(COMMITTED_REPORT_DIR / "sft_candidate_rows.jsonl")

    assert public_manifest["counts"] == CURRENT_FORMAL_COUNTS
    assert public_manifest["split_counts"] == CURRENT_FORMAL_SPLITS
    assert public_manifest["source_summary"]["slot_value_candidates_formal_public_sample"] is True
    assert materialization["summary"]["candidate_group_count"] == 4
    assert materialization["summary"]["candidate_seed_rows"] == 4
    assert materialization["summary"]["candidate_sft_rows"] == 12
    assert materialization["summary"]["public_sample_modified"] is False
    assert manifest["execution_scope"]["training_run"] is False
    assert manifest["execution_scope"]["prediction_run"] is False
    assert manifest["execution_scope"]["dpo_run"] is False
    assert len(seed_rows) == 4
    assert len(sft_rows) == 12
    assert scan_paths([COMMITTED_CANDIDATE_SEED, COMMITTED_REPORT_DIR]).ok is True
