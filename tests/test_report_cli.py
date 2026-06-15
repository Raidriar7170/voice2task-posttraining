import json
from pathlib import Path

from voice2task.cli import report as report_cli
from voice2task.leak_scan import Finding, ScanResult, scan_paths

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_leak_scan_cli_keeps_positional_paths_compatible(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    public_report = tmp_path / "report.md"
    public_report.write_text("Public sample report with aggregate metrics only.", encoding="utf-8")

    assert report_cli.main(["leak-scan", public_report.as_posix()]) == 0

    output = json.loads(capsys.readouterr().out)
    assert output["ok"] is True
    assert output["findings"] == []


def test_leak_scan_cli_writes_output_with_audit_metadata(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    public_dir = tmp_path / "public"
    public_dir.mkdir()
    (public_dir / "report.md").write_text("Public sample report with aggregate metrics only.", encoding="utf-8")
    output_path = tmp_path / "leak_scan_result.json"

    assert (
        report_cli.main(
            [
                "leak-scan",
                "--paths",
                public_dir.as_posix(),
                "--output",
                output_path.as_posix(),
                "--max-public-jsonl-rows",
                "5",
            ]
        )
        == 0
    )

    assert capsys.readouterr().out == ""
    output = json.loads(output_path.read_text(encoding="utf-8"))
    assert output["ok"] is True
    assert output["findings"] == []
    assert output["scanned_paths"] == ["<private_path>"]
    assert output["max_public_jsonl_rows"] == 5
    assert "generated_at" in output


def test_leak_scan_cli_sanitizes_private_scanned_paths(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    private_path = Path("/mnt/data/" + "minghongsun/voice2task-post-training/evidence/a100-sft-smoke")
    output_path = tmp_path / "leak_scan_result.json"

    assert (
        report_cli.main(
            [
                "leak-scan",
                "--paths",
                private_path.as_posix(),
                "--output",
                output_path.as_posix(),
            ]
        )
        == 1
    )

    assert capsys.readouterr().out == ""
    output = json.loads(output_path.read_text(encoding="utf-8"))
    assert output["scanned_paths"] == ["<private_path>"]
    assert output["findings"] == [
        {"category": "missing_path", "detail": "scan input path does not exist", "line": 0, "path": "<private_path>"}
    ]
    assert private_path.as_posix() not in output_path.read_text(encoding="utf-8")


def test_leak_scan_cli_sanitizes_private_finding_paths(tmp_path: Path, monkeypatch, capsys) -> None:  # type: ignore[no-untyped-def]
    private_path = Path(
        "/mnt/data/" + "minghongsun/voice2task-post-training/runs/run/adapter/adapter_model.safetensors"
    )
    output_path = tmp_path / "leak_scan_result.json"

    monkeypatch.setattr(
        report_cli,
        "scan_paths",
        lambda paths, max_public_jsonl_rows: ScanResult(
            ok=False,
            findings=[Finding(private_path.as_posix(), "model_artifact", 0, "model/checkpoint artifact")],
        ),
    )

    assert (
        report_cli.main(
            [
                "leak-scan",
                "--paths",
                private_path.as_posix(),
                "--output",
                output_path.as_posix(),
            ]
        )
        == 1
    )

    assert capsys.readouterr().out == ""
    output = json.loads(output_path.read_text(encoding="utf-8"))
    assert output["findings"][0]["path"] == "<private_path>"
    assert private_path.as_posix() not in output_path.read_text(encoding="utf-8")


def test_leak_scan_cli_combines_positional_and_flag_paths(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    positional = tmp_path / "positional.md"
    flagged = tmp_path / "flagged.md"
    positional.write_text("Public positional report.", encoding="utf-8")
    flagged.write_text("Public flagged report.", encoding="utf-8")

    assert report_cli.main(["leak-scan", positional.as_posix(), "--paths", flagged.as_posix()]) == 0

    output = json.loads(capsys.readouterr().out)
    assert output["ok"] is True
    assert output["scanned_paths"] == ["<private_path>", "<private_path>"]


def test_runtime_label_provenance_report_cli_writes_public_safe_evidence_pack(
    tmp_path: Path,
    capsys,  # type: ignore[no-untyped-def]
) -> None:
    prep_metadata = tmp_path / "runtime_prep.json"
    prep_metadata.write_text(
        json.dumps(
            {
                "evidence_kind": "sft_runtime_label_provenance_prep",
                "runtime_check_status": "blocked_unresolved_private_override",
                "private_override": {
                    "required": True,
                    "status": "unresolved",
                    "resolved_output_root": "/mnt/data/" + "minghongsun/voice2task-post-training",
                },
                "output_root_policy": {"status": "blocked_unresolved_template"},
                "dependency_policy": {
                    "train_dependencies_imported": False,
                    "model_download_allowed": False,
                    "private_adapter_load_allowed": False,
                },
                "label_provenance_intent": {
                    "private_labels_inspected": False,
                    "later_runtime_path": "/mnt/data/" + "minghongsun/private/runtime",
                },
                "label_tensor_available": False,
                "true_label_mask_status": "unavailable",
                "evidence_gaps": ["runtime_check_not_executed"],
                "claims": {"runtime_readiness_proves_contract_learning": False},
                "prior_artifacts": {
                    "sft_label_provenance": "reports/public-sample/sft-label-provenance/",
                },
            }
        ),
        encoding="utf-8",
    )
    output_dir = tmp_path / "runtime-label-provenance-prep"

    assert (
        report_cli.main(
            [
                "runtime-label-provenance-prep",
                "--prep-metadata",
                prep_metadata.as_posix(),
                "--output-dir",
                output_dir.as_posix(),
                "--prior-artifact",
                "private_runtime=/" + "mnt/data/minghongsun/private/runtime",
            ]
        )
        == 0
    )

    cli_output = json.loads(capsys.readouterr().out)
    assert cli_output["ok"] is True
    summary_path = output_dir / "runtime_label_provenance_prep.json"
    markdown_path = output_dir / "runtime_label_provenance_prep.md"
    assert cli_output["paths"]["json"] == summary_path.as_posix()
    assert cli_output["paths"]["markdown"] == markdown_path.as_posix()

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    markdown = markdown_path.read_text(encoding="utf-8")
    serialized = json.dumps(summary, ensure_ascii=False, sort_keys=True) + markdown

    assert summary["evidence_kind"] == "sft_runtime_label_provenance_prep"
    assert summary["runtime_check_status"] == "blocked_unresolved_private_override"
    assert summary["label_tensor_available"] is False
    assert summary["true_label_mask_status"] == "unavailable"
    assert summary["prior_artifacts"]["sft_label_provenance"] == "reports/public-sample/sft-label-provenance/"
    assert summary["prior_artifacts"]["private_runtime"] == "<private_path>"
    assert "did not run private A100 execution" in markdown
    assert "Runtime readiness is not true label-mask evidence" in markdown
    assert "/mnt/data/" not in serialized
    assert "/Users/" not in serialized


def test_runtime_label_provenance_report_cli_prevents_hostile_claim_and_artifact_policy_overrides(
    tmp_path: Path,
    capsys,  # type: ignore[no-untyped-def]
) -> None:
    prep_metadata = tmp_path / "hostile_runtime_prep.json"
    prep_metadata.write_text(
        json.dumps(
            {
                "evidence_kind": "sft_runtime_label_provenance_prep",
                "runtime_check_status": "blocked_unresolved_private_override",
                "claims": {
                    "runtime_readiness_proves_contract_learning": True,
                    "checkpoint_release": True,
                    "adapter_release": True,
                    "held_out_generalization_claim": True,
                    "production_readiness_claim": True,
                    "live_browser_benchmark_claim": True,
                },
                "artifact_policy": {
                    "raw_rendered_prompts_written": True,
                    "raw_logs_copied_to_git": True,
                    "checkpoints_or_adapters_copied_to_git": True,
                    "private_paths_omitted": False,
                },
            }
        ),
        encoding="utf-8",
    )
    output_dir = tmp_path / "runtime-label-provenance-prep"

    assert (
        report_cli.main(
            [
                "runtime-label-provenance-prep",
                "--prep-metadata",
                prep_metadata.as_posix(),
                "--output-dir",
                output_dir.as_posix(),
            ]
        )
        == 0
    )

    assert json.loads(capsys.readouterr().out)["ok"] is True
    summary = json.loads((output_dir / "runtime_label_provenance_prep.json").read_text(encoding="utf-8"))

    assert summary["claims"] == {
        "runtime_readiness_proves_contract_learning": False,
        "checkpoint_release": False,
        "adapter_release": False,
        "held_out_generalization_claim": False,
        "production_readiness_claim": False,
        "live_browser_benchmark_claim": False,
    }
    assert summary["artifact_policy"] == {
        "raw_rendered_prompts_written": False,
        "raw_logs_copied_to_git": False,
        "checkpoints_or_adapters_copied_to_git": False,
        "private_paths_omitted": True,
    }


def test_runtime_label_provenance_check_report_cli_sanitizes_hostile_metadata_and_forces_safe_boundaries(
    tmp_path: Path,
    capsys,  # type: ignore[no-untyped-def]
) -> None:
    runtime_metadata = tmp_path / "runtime_metadata.json"
    runtime_metadata.write_text(
        json.dumps(
            {
                "evidence_kind": "sft_runtime_label_provenance_observed",
                "evidence_status": "labels_inspected",
                "runtime_source_kind": "private_a100_runtime",
                "runtime_check_status": "executed_runtime_label_provenance_check",
                "runtime_gate": {
                    "cli_requested_runtime_check": True,
                    "config_allow_runtime_label_provenance_check": True,
                    "private_override_resolved": True,
                    "will_run_runtime_label_provenance_check": True,
                },
                "output_root_policy": {"status": "approved_private_root"},
                "dataset_manifest_id": "public-sample-test",
                "label_source": "trl_collator_labels",
                "label_source_kind": "private_training_runtime",
                "label_provenance": {
                    "source_kind": "private_training_runtime",
                    "real_training_path": True,
                    "raw_runtime_path": "<private_path>",
                },
                "label_tensor_available": True,
                "true_label_mask_status": "inspectable",
                "tokenizer_template_status": "template_available",
                "collator_status": "labels_inspected",
                "package_versions": {"python": "3.11.4", "transformers": "4.0.0"},
                "dependency_policy": {
                    "policy": "authorized_runtime_tokenizer_collator_check_no_adapter_load_no_training",
                    "model_download_allowed": False,
                    "private_adapter_load_allowed": False,
                },
                "leak_scan_status": {
                    "ok": True,
                    "result_path": "reports/public-sample/runtime-label-provenance-check/leak_scan_result.json",
                },
                "prompt_tokens_masked": True,
                "assistant_tokens_carry_loss": True,
                "evidence_gaps": ["synthetic_host_and_path_details_omitted"],
                "claims": {
                    "checkpoint_release": True,
                    "adapter_release": True,
                    "held_out_generalization_claim": True,
                    "production_readiness_claim": True,
                    "live_browser_benchmark_claim": True,
                    "model_recovery_claim": True,
                },
                "artifact_policy": {
                    "raw_rendered_prompts_written": True,
                    "raw_logs_copied_to_git": True,
                    "checkpoints_or_adapters_copied_to_git": True,
                    "private_paths_omitted": False,
                },
                "notes": "synthetic secret-bearing details omitted by report writer",
            }
        ),
        encoding="utf-8",
    )
    output_dir = tmp_path / "runtime-label-provenance-check"

    assert (
        report_cli.main(
            [
                "runtime-label-provenance-check",
                "--runtime-metadata",
                runtime_metadata.as_posix(),
                "--output-dir",
                output_dir.as_posix(),
                "--prior-artifact",
                "private_runtime=<private_path>",
            ]
        )
        == 0
    )

    cli_output = json.loads(capsys.readouterr().out)
    summary_path = output_dir / "runtime_label_provenance_check.json"
    markdown_path = output_dir / "runtime_label_provenance_check.md"
    assert cli_output["ok"] is True
    assert cli_output["paths"]["json"] == summary_path.as_posix()
    assert cli_output["paths"]["markdown"] == markdown_path.as_posix()

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    markdown = markdown_path.read_text(encoding="utf-8")
    serialized = json.dumps(summary, ensure_ascii=False, sort_keys=True) + markdown

    assert summary["evidence_kind"] == "sft_runtime_label_provenance_observed"
    assert summary["runtime_source_kind"] == "private_a100_runtime"
    assert summary["dataset_manifest_id"] == "public-sample-test"
    assert summary["label_tensor_available"] is True
    assert summary["runtime_gate"]["will_run_runtime_label_provenance_check"] is True
    assert summary["output_root_policy"]["status"] == "approved_private_root"
    assert summary["package_versions"] == {"python": "3.11.4", "transformers": "4.0.0"}
    assert summary["dependency_policy"]["model_download_allowed"] is False
    assert summary["leak_scan_status"]["ok"] is True
    assert summary["true_label_mask_status"] == "inspectable"
    assert summary["label_source_kind"] == "private_training_runtime"
    assert summary["release_status"] == "not_released"
    assert summary["claims"] == {
        "checkpoint_release": False,
        "adapter_release": False,
        "held_out_generalization_claim": False,
        "production_readiness_claim": False,
        "live_browser_benchmark_claim": False,
        "model_recovery_claim": False,
    }
    assert summary["artifact_policy"] == {
        "raw_rendered_prompts_written": False,
        "raw_logs_copied_to_git": False,
        "checkpoints_or_adapters_copied_to_git": False,
        "private_paths_omitted": True,
    }
    assert summary["prior_artifacts"]["private_runtime"] == "<private_path>"
    assert "Runtime label provenance evidence is objective-path evidence only" in markdown
    assert "not held-out generalization evidence" in markdown
    assert "Leak scan ok: `True`" in markdown
    assert "Dependency policy:" in markdown
    assert "Runtime gate:" in markdown
    assert "Output-root policy:" in markdown
    assert "/mnt/data/" not in serialized
    assert "/Users/" not in serialized
    assert "10" + ".1.2.3" not in serialized
    assert "secret" + "1234" not in serialized
    assert scan_paths([summary_path, markdown_path]).ok is True


def test_runtime_label_provenance_check_report_cli_requires_real_training_path_for_labels_inspected(
    tmp_path: Path,
    capsys,  # type: ignore[no-untyped-def]
) -> None:
    runtime_metadata = tmp_path / "runtime_metadata.json"
    runtime_metadata.write_text(
        json.dumps(
            {
                "evidence_kind": "sft_runtime_label_provenance_observed",
                "evidence_status": "labels_inspected",
                "runtime_check_status": "executed_runtime_label_provenance_check",
                "dataset_manifest_id": "public-sample-test",
                "inspection_status": "inspectable",
                "label_source_kind": "private_training_runtime",
                "label_provenance": {"source_kind": "private_training_runtime", "real_training_path": False},
                "label_tensor_available": True,
                "true_label_mask_status": "inspectable",
            }
        ),
        encoding="utf-8",
    )
    output_dir = tmp_path / "runtime-label-provenance-check"

    assert (
        report_cli.main(
            [
                "runtime-label-provenance-check",
                "--runtime-metadata",
                runtime_metadata.as_posix(),
                "--output-dir",
                output_dir.as_posix(),
            ]
        )
        == 0
    )

    assert json.loads(capsys.readouterr().out)["ok"] is True
    summary = json.loads((output_dir / "runtime_label_provenance_check.json").read_text(encoding="utf-8"))
    assert summary["label_tensor_available"] is True
    assert summary["evidence_status"] == "labels_available_but_not_real_training_proof"


def test_runtime_label_provenance_check_report_cli_does_not_upgrade_blocked_metadata(
    tmp_path: Path,
    capsys,  # type: ignore[no-untyped-def]
) -> None:
    runtime_metadata = tmp_path / "blocked_runtime_metadata.json"
    runtime_metadata.write_text(
        json.dumps(
            {
                "evidence_kind": "sft_runtime_label_provenance_observed",
                "evidence_status": "blocked_output_outside_approved_root",
                "runtime_check_status": "blocked_output_outside_approved_root",
                "runtime_gate": {
                    "cli_requested_runtime_check": True,
                    "config_allow_runtime_label_provenance_check": True,
                    "private_override_resolved": True,
                    "will_run_runtime_label_provenance_check": False,
                },
                "dataset_manifest_id": "public-sample-test",
                "inspection_status": "inspectable",
                "label_source_kind": "private_training_runtime",
                "label_provenance": {"source_kind": "private_training_runtime", "real_training_path": True},
                "label_tensor_available": True,
                "true_label_mask_status": "inspectable",
            }
        ),
        encoding="utf-8",
    )
    output_dir = tmp_path / "runtime-label-provenance-check"

    assert (
        report_cli.main(
            [
                "runtime-label-provenance-check",
                "--runtime-metadata",
                runtime_metadata.as_posix(),
                "--output-dir",
                output_dir.as_posix(),
            ]
        )
        == 0
    )

    assert json.loads(capsys.readouterr().out)["ok"] is True
    summary = json.loads((output_dir / "runtime_label_provenance_check.json").read_text(encoding="utf-8"))
    assert summary["label_tensor_available"] is True
    assert summary["runtime_gate"]["will_run_runtime_label_provenance_check"] is False
    assert summary["evidence_status"] == "blocked_output_outside_approved_root"


def test_runtime_label_provenance_check_report_cli_requires_runtime_gate_for_labels_inspected(
    tmp_path: Path,
    capsys,  # type: ignore[no-untyped-def]
) -> None:
    runtime_metadata = tmp_path / "stale_runtime_metadata.json"
    runtime_metadata.write_text(
        json.dumps(
            {
                "evidence_kind": "sft_runtime_label_provenance_observed",
                "evidence_status": "labels_inspected",
                "runtime_check_status": "executed_runtime_label_provenance_check",
                "runtime_gate": {
                    "cli_requested_runtime_check": True,
                    "config_allow_runtime_label_provenance_check": True,
                    "private_override_resolved": True,
                    "will_run_runtime_label_provenance_check": False,
                },
                "dataset_manifest_id": "public-sample-test",
                "inspection_status": "labels_unavailable",
                "label_source_kind": "private_training_runtime",
                "label_provenance": {"source_kind": "private_training_runtime", "real_training_path": True},
                "label_tensor_available": False,
                "true_label_mask_status": "unavailable",
            }
        ),
        encoding="utf-8",
    )
    output_dir = tmp_path / "runtime-label-provenance-check"

    assert (
        report_cli.main(
            [
                "runtime-label-provenance-check",
                "--runtime-metadata",
                runtime_metadata.as_posix(),
                "--output-dir",
                output_dir.as_posix(),
            ]
        )
        == 0
    )

    assert json.loads(capsys.readouterr().out)["ok"] is True
    summary = json.loads((output_dir / "runtime_label_provenance_check.json").read_text(encoding="utf-8"))
    assert summary["runtime_gate"]["will_run_runtime_label_provenance_check"] is False
    assert summary["evidence_status"] == "labels_unavailable"


def test_runtime_label_provenance_check_report_marks_stale_manifest_as_prior_context_only(
    tmp_path: Path,
    capsys,  # type: ignore[no-untyped-def]
) -> None:
    runtime_metadata = tmp_path / "old_runtime_metadata.json"
    runtime_metadata.write_text(
        json.dumps(
            {
                "evidence_kind": "sft_runtime_label_provenance_observed",
                "runtime_check_status": "executed_runtime_label_provenance_check",
                "runtime_gate": {
                    "cli_requested_runtime_check": True,
                    "config_allow_runtime_label_provenance_check": True,
                    "private_override_resolved": True,
                    "will_run_runtime_label_provenance_check": True,
                },
                "dataset_manifest_id": "public-sample-old",
                "inspection_status": "inspectable",
                "label_source_kind": "private_training_runtime",
                "label_provenance": {"source_kind": "private_training_runtime", "real_training_path": True},
                "label_tensor_available": True,
                "true_label_mask_status": "inspectable",
                "prompt_tokens_masked": True,
                "assistant_tokens_carry_loss": True,
            }
        ),
        encoding="utf-8",
    )
    output_dir = tmp_path / "runtime-label-provenance-check"

    assert (
        report_cli.main(
            [
                "runtime-label-provenance-check",
                "--runtime-metadata",
                runtime_metadata.as_posix(),
                "--output-dir",
                output_dir.as_posix(),
                "--expected-manifest-id",
                "public-sample-current",
                "--prior-artifact",
                "old_runtime=reports/public-sample/runtime-label-provenance-check/",
            ]
        )
        == 0
    )

    assert json.loads(capsys.readouterr().out)["ok"] is True
    summary = json.loads((output_dir / "runtime_label_provenance_check.json").read_text(encoding="utf-8"))
    markdown = (output_dir / "runtime_label_provenance_check.md").read_text(encoding="utf-8")
    assert summary["expected_manifest_id"] == "public-sample-current"
    assert summary["dataset_manifest_id"] == "public-sample-old"
    assert summary["manifest_freshness"] == "stale_manifest_mismatch"
    assert summary["current_manifest_runtime_label_proof"] is False
    assert summary["evidence_status"] == "stale_manifest_mismatch"
    assert summary["prior_artifacts_role"] == "historical_context_only"
    assert summary["recommended_next_step"] == "run_fresh_current_manifest_runtime_label_check"
    assert "Stale prior artifacts are historical context only" in markdown


def test_runtime_label_provenance_check_report_recommends_tiny_probe_only_for_fresh_assistant_only_labels(
    tmp_path: Path,
    capsys,  # type: ignore[no-untyped-def]
) -> None:
    runtime_metadata = tmp_path / "current_runtime_metadata.json"
    runtime_metadata.write_text(
        json.dumps(
            {
                "evidence_kind": "sft_runtime_label_provenance_observed",
                "runtime_check_status": "executed_runtime_label_provenance_check",
                "runtime_gate": {
                    "cli_requested_runtime_check": True,
                    "config_allow_runtime_label_provenance_check": True,
                    "private_override_resolved": True,
                    "will_run_runtime_label_provenance_check": True,
                },
                "dataset_manifest_id": "public-sample-current",
                "inspection_status": "inspectable",
                "label_source_kind": "private_training_runtime",
                "label_provenance": {"source_kind": "private_training_runtime", "real_training_path": True},
                "label_tensor_available": True,
                "true_label_mask_status": "inspectable",
                "prompt_tokens_masked": True,
                "assistant_tokens_carry_loss": True,
                "evidence_gaps": [],
            }
        ),
        encoding="utf-8",
    )
    output_dir = tmp_path / "runtime-label-provenance-check"

    assert (
        report_cli.main(
            [
                "runtime-label-provenance-check",
                "--runtime-metadata",
                runtime_metadata.as_posix(),
                "--output-dir",
                output_dir.as_posix(),
                "--expected-manifest-id",
                "public-sample-current",
            ]
        )
        == 0
    )

    assert json.loads(capsys.readouterr().out)["ok"] is True
    summary = json.loads((output_dir / "runtime_label_provenance_check.json").read_text(encoding="utf-8"))
    markdown = (output_dir / "runtime_label_provenance_check.md").read_text(encoding="utf-8")
    assert summary["manifest_freshness"] == "fresh_current_manifest"
    assert summary["current_manifest_runtime_label_proof"] is True
    assert summary["assistant_only_loss_mask_claim"] is True
    assert summary["recommended_next_step"] == "run_1_to_3_row_current_manifest_tiny_overfit_probe"
    assert "Recommended next step: `run_1_to_3_row_current_manifest_tiny_overfit_probe`" in markdown


def test_public_runtime_label_provenance_check_evidence_is_safe_and_bounded() -> None:
    evidence_dir = REPO_ROOT / "reports" / "public-sample" / "runtime-label-provenance-check"
    summary_path = evidence_dir / "runtime_label_provenance_check.json"
    markdown_path = evidence_dir / "runtime_label_provenance_check.md"
    leak_scan_path = evidence_dir / "leak_scan_result.json"

    assert summary_path.exists()
    assert markdown_path.exists()
    assert leak_scan_path.exists()

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    markdown = markdown_path.read_text(encoding="utf-8")
    leak_scan = json.loads(leak_scan_path.read_text(encoding="utf-8"))

    assert summary["evidence_status"] == "labels_inspected"
    assert summary["label_tensor_available"] is True
    assert summary["prompt_tokens_masked"] is False
    assert summary["assistant_tokens_carry_loss"] is True
    assert summary["claims"] == {
        "checkpoint_release": False,
        "adapter_release": False,
        "held_out_generalization_claim": False,
        "production_readiness_claim": False,
        "live_browser_benchmark_claim": False,
        "model_recovery_claim": False,
    }
    assert summary["dependency_policy"]["model_download_allowed"] is False
    assert summary["leak_scan_status"]["ok"] is True
    assert summary["assistant_only_loss_mask_claim"] is False
    assert "prompt_tokens_masked=false" in markdown
    assert leak_scan["ok"] is True
    assert scan_paths([evidence_dir]).ok is True


def test_current_runtime_label_provenance_check_evidence_is_fresh_and_bounded() -> None:
    evidence_dir = REPO_ROOT / "reports" / "public-sample" / "current-runtime-label-provenance-check"
    manifest = json.loads((evidence_dir / "manifest.json").read_text(encoding="utf-8"))
    summary = json.loads((evidence_dir / "runtime_label_provenance_check.json").read_text(encoding="utf-8"))
    metadata = json.loads((evidence_dir / "runtime_observed_metadata.json").read_text(encoding="utf-8"))
    markdown = (evidence_dir / "runtime_label_provenance_check.md").read_text(encoding="utf-8")
    leak_scan = json.loads((evidence_dir / "leak_scan_result.json").read_text(encoding="utf-8"))
    serialized = json.dumps(manifest, ensure_ascii=False, sort_keys=True)

    assert manifest["dataset_manifest_id"] == "public-sample-20260613T072200Z"
    assert manifest["expected_manifest_id"] == "public-sample-20260613T072200Z"
    assert manifest["manifest_freshness"] == "fresh_current_manifest"
    assert manifest["current_manifest_runtime_label_proof"] is True
    assert manifest["execution_scope"]["tokenizer_collator_label_inspection_only"] is True
    assert manifest["execution_scope"]["sft_training"] is False
    assert manifest["execution_scope"]["prediction_export"] is False
    assert manifest["execution_scope"]["private_adapter_loaded"] is False
    assert manifest["true_label_mask_status"] == "inspectable"
    assert manifest["prompt_tokens_masked"] is True
    assert manifest["assistant_tokens_carry_loss"] is True
    assert manifest["recommended_next_step"] == "run_1_to_3_row_current_manifest_tiny_overfit_probe"
    assert summary["current_manifest_runtime_label_proof"] is True
    assert summary["assistant_only_loss_mask_claim"] is True
    assert metadata["label_source_kind"] == "private_training_runtime"
    assert leak_scan["ok"] is True
    assert "Recommended next step: `run_1_to_3_row_current_manifest_tiny_overfit_probe`" in markdown
    assert "/mnt/data/" not in serialized
    assert "/Users/" not in serialized
    assert scan_paths([evidence_dir]).ok is True


def test_public_runtime_label_provenance_prep_evidence_is_safe_and_links_prior_artifacts() -> None:
    evidence_dir = REPO_ROOT / "reports" / "public-sample" / "runtime-label-provenance-prep"
    summary_path = evidence_dir / "runtime_label_provenance_prep.json"
    markdown_path = evidence_dir / "runtime_label_provenance_prep.md"
    leak_scan_path = evidence_dir / "leak_scan_result.json"

    assert summary_path.exists()
    assert markdown_path.exists()
    assert leak_scan_path.exists()
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    markdown = markdown_path.read_text(encoding="utf-8").lower()

    assert summary["runtime_check_status"] == "blocked_unresolved_private_override"
    assert summary["label_tensor_available"] is False
    assert summary["true_label_mask_status"] == "unavailable"
    assert set(summary["prior_artifacts"]) == {
        "sft_label_provenance",
        "sft_target_template_alignment",
        "a100_train_split_overfit_diagnostic",
    }
    assert summary["claims"]["runtime_readiness_proves_contract_learning"] is False
    assert "did not run private a100 execution" in markdown
    assert "runtime readiness is not true label-mask evidence" in markdown
    assert json.loads(leak_scan_path.read_text(encoding="utf-8"))["ok"] is True
