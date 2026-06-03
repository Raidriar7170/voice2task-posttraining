import json
from pathlib import Path

from voice2task.cli import report as report_cli
from voice2task.leak_scan import Finding, ScanResult

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
    assert output["scanned_paths"] == [public_dir.as_posix()]
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
        == 0
    )

    assert capsys.readouterr().out == ""
    output = json.loads(output_path.read_text(encoding="utf-8"))
    assert output["scanned_paths"] == ["<private_path>"]
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
    assert output["scanned_paths"] == [positional.as_posix(), flagged.as_posix()]


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
                "private_runtime=/mnt/data/minghongsun/private/runtime",
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
