import json
from pathlib import Path
from typing import Any

from voice2task.cli import eval as eval_cli
from voice2task.evaluation import design_slot_value_generalization_cases
from voice2task.io import read_json
from voice2task.leak_scan import scan_paths
from voice2task.reports import write_slot_value_generalization_case_design_report

REPO_ROOT = Path(__file__).resolve().parents[1]
RESIDUAL_DIR = REPO_ROOT / "reports" / "public-sample" / "targeted-slot-value-residual-diagnosis"
DESIGN_DIR = REPO_ROOT / "reports" / "public-sample" / "slot-value-generalization-case-design"


def _current_inputs() -> dict[str, Any]:
    return {
        "residual_diagnosis": read_json(RESIDUAL_DIR / "targeted_slot_value_residual_diagnosis.json"),
        "residual_manifest": read_json(RESIDUAL_DIR / "manifest.json"),
    }


def test_slot_value_generalization_case_design_covers_all_residual_buckets_without_data_mutation() -> None:
    design = design_slot_value_generalization_cases(**_current_inputs())

    assert design["evidence_kind"] == "slot_value_generalization_case_design"
    assert design["design_status"] == "design_only_not_materialized"
    assert design["source_residual_diagnosis"]["evidence_kind"] == "targeted_slot_value_residual_diagnosis"
    assert design["summary"]["candidate_group_count"] == 4
    assert design["summary"]["covered_residual_bucket_counts"] == {
        "normalized_command_paraphrase_drift": 4,
        "slot_value_canonical_phrase_drift": 3,
        "slot_value_language_variant": 3,
    }
    assert design["summary"]["recommended_next_step"] == "materialize_reviewed_cases_in_later_openspec_change"
    assert design["execution_scope"]["new_data_generated"] is False
    assert design["execution_scope"]["public_sample_modified"] is False
    assert design["execution_scope"]["training_run"] is False
    assert design["execution_scope"]["prediction_run"] is False
    assert design["execution_scope"]["evaluator_metric_change"] is False

    groups = {group["case_group_id"]: group for group in design["candidate_case_groups"]}
    assert set(groups) == {
        "clarify-ambiguous-slot-value-canonical-phrase",
        "form-email-slot-value-language-variant",
        "navigate-open-url-normalized-command-paraphrase",
        "blocked-payment-normalized-command-paraphrase",
    }
    assert groups["form-email-slot-value-language-variant"]["canonical_gold_values"] == [
        {"field_path": "slots", "value": {"field": "邮箱"}}
    ]
    assert groups["form-email-slot-value-language-variant"]["observed_wrong_values"] == [
        {"field_path": "slots", "value": {"field": "email"}}
    ]
    assert groups["clarify-ambiguous-slot-value-canonical-phrase"]["case_purpose"] == (
        "teach the canonical ambiguity scope phrase without evaluator-side normalization"
    )
    assert groups["navigate-open-url-normalized-command-paraphrase"]["materialization_requires_user_review"] is True
    assert groups["blocked-payment-normalized-command-paraphrase"]["recommended_split_role"] == (
        "candidate_train_or_validation_design_only"
    )

    assert design["claims"]["held_out_generalization_recovered"] is False
    assert design["claims"]["semantic_equivalence_primary_metric"] is False
    assert design["claims"]["prediction_repair_or_replacement"] is False


def test_slot_value_generalization_case_design_cli_writes_public_safe_report(tmp_path: Path, capsys: Any) -> None:
    output_dir = tmp_path / "slot-value-case-design"

    assert (
        eval_cli.main(
            [
                "design-slot-value-generalization-cases",
                "--residual-diagnosis",
                (RESIDUAL_DIR / "targeted_slot_value_residual_diagnosis.json").as_posix(),
                "--residual-manifest",
                (RESIDUAL_DIR / "manifest.json").as_posix(),
                "--output",
                output_dir.as_posix(),
            ]
        )
        == 0
    )

    cli_output = json.loads(capsys.readouterr().out)
    assert cli_output["ok"] is True
    assert cli_output["paths"]["json"] == (output_dir / "slot_value_generalization_case_design.json").as_posix()
    assert cli_output["paths"]["markdown"] == (
        output_dir / "slot_value_generalization_case_design.md"
    ).as_posix()
    assert cli_output["paths"]["manifest"] == (output_dir / "manifest.json").as_posix()

    design = read_json(output_dir / "slot_value_generalization_case_design.json")
    manifest = read_json(output_dir / "manifest.json")
    markdown = (output_dir / "slot_value_generalization_case_design.md").read_text(encoding="utf-8")
    assert design["summary"]["candidate_group_count"] == 4
    assert manifest["execution_scope"]["public_sample_modified"] is False
    assert manifest["claims"]["model_recovery_claim"] is False
    assert "design-only evidence" in markdown
    assert "not materialized into seed_traces.jsonl" in markdown
    assert scan_paths([output_dir]).ok is True

    direct_paths = write_slot_value_generalization_case_design_report(design, tmp_path / "direct")
    assert direct_paths["json"].exists()
    assert direct_paths["markdown"].exists()
    assert direct_paths["manifest"].exists()


def test_committed_slot_value_generalization_case_design_is_bounded_and_public_safe() -> None:
    manifest = read_json(DESIGN_DIR / "manifest.json")
    design = read_json(DESIGN_DIR / "slot_value_generalization_case_design.json")

    assert manifest["evidence_kind"] == "slot_value_generalization_case_design"
    assert manifest["design_status"] == "design_only_not_materialized"
    assert manifest["summary"]["candidate_group_count"] == 4
    assert manifest["execution_scope"]["new_data_generated"] is False
    assert manifest["execution_scope"]["public_sample_modified"] is False
    assert manifest["execution_scope"]["training_run"] is False
    assert manifest["claims"]["held_out_generalization_recovered"] is False
    assert design["claims"]["checkpoint_release"] is False
    assert design["claims"]["adapter_release"] is False
    assert design["claims"]["production_readiness_claim"] is False
    assert scan_paths([DESIGN_DIR]).ok is True
