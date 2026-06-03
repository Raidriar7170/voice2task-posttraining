import json
from pathlib import Path
from typing import Any

import pytest

from voice2task import training
from voice2task.cli import train as train_cli
from voice2task.leak_scan import scan_paths
from voice2task.training import run_sft

REPO_ROOT = Path(__file__).resolve().parents[1]
A100_PROJECT_DIR = "/mnt/data/" + "minghongsun/voice2task-post-training"
A100_PROJECT_ROOT_POLICY = "must_resolve_to_approved_private_a100_project_root"


def _write_manifest(tmp_path: Path) -> Path:
    manifest = tmp_path / "manifest.json"
    rows = tmp_path / "sft_public_sample.jsonl"
    rows.write_text(
        json.dumps(
            {
                "id": "sft-1",
                "split": "train",
                "input_text": "搜索天气",
                "target_contract": {
                    "task_type": "search",
                    "route": "search_web",
                    "safety": {"allow": True, "reason": "public_readonly"},
                    "confirmation_required": False,
                    "slots": {"query": "天气"},
                    "normalized_command": "搜索天气",
                    "language": "zh-CN",
                    "contract_version": "v1",
                },
                "provenance": {"source_id": "seed-1", "public_safe": True},
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    manifest.write_text(
        json.dumps(
            {
                "manifest_id": "public-sample-test",
                "files": {"sft": rows.name},
                "counts": {"sft_rows": 1},
            }
        ),
        encoding="utf-8",
    )
    return manifest


def _write_config(tmp_path: Path, allow_heavy_training: bool, output_root: str = A100_PROJECT_DIR) -> Path:
    suffix = "allow" if allow_heavy_training else "block"
    config = tmp_path / f"sft-{suffix}.json"
    config.write_text(
        json.dumps(
            {
                "base_model": "Qwen/Qwen2.5-0.5B-Instruct",
                "allow_heavy_training": allow_heavy_training,
                "dataset_split": "train",
                "gpu_selection_policy": "select_idle_gpu_only_no_process_interruption",
                "output_root": output_root,
                "lora": {"r": 8, "alpha": 16, "dropout": 0.05, "target_modules": ["q_proj", "v_proj"]},
            }
        ),
        encoding="utf-8",
    )
    return config


def _write_runtime_label_provenance_config(
    tmp_path: Path,
    *,
    allow_runtime_check: bool = False,
    output_root: str = "<a100_project_root>",
    adapter_path: str = "<a100_project_root>/runs/a100-train-split-overfit-diagnostic/adapter",
    evidence_output_dir: str | None = None,
    runtime_check_output_dir: str | None = None,
) -> Path:
    resolved_evidence_output_dir = evidence_output_dir or f"{output_root}/evidence/runtime-label-provenance-prep"
    resolved_runtime_check_output_dir = (
        runtime_check_output_dir or f"{output_root}/evidence/runtime-label-provenance-prep"
    )
    config = tmp_path / "runtime-label-provenance-prep.json"
    config.write_text(
        json.dumps(
            {
                "base_model": "Qwen/Qwen2.5-0.5B-Instruct",
                "allow_runtime_label_provenance_check": allow_runtime_check,
                "private_override_required": True,
                "private_override_requirements": [
                    "Create a private override outside git before runtime execution.",
                    "Resolve <a100_project_root> to the approved private A100 project root.",
                ],
                "output_root": output_root,
                "evidence_output_dir": resolved_evidence_output_dir,
                "runtime_check_output_dir": resolved_runtime_check_output_dir,
                "adapter_path": adapter_path,
                "dependency_policy": "prep_only_no_train_dependency_import_no_model_download",
                "label_provenance_intent": "inspect_real_tokenizer_collator_labels_later",
                "prior_artifacts": {
                    "sft_label_provenance": "reports/public-sample/sft-label-provenance/",
                    "sft_target_template_alignment": "reports/public-sample/sft-target-template-alignment/",
                    "a100_train_split_overfit_diagnostic": (
                        "reports/public-sample/a100-train-split-overfit-diagnostic/"
                    ),
                },
            }
        ),
        encoding="utf-8",
    )
    return config


def test_public_sample_a100_sft_smoke_config_is_bounded_and_opt_in() -> None:
    config_path = REPO_ROOT / "configs" / "sft-a100-public-smoke.json"

    assert config_path.exists()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    assert config["allow_heavy_training"] is True
    assert config["base_model"] == "Qwen/Qwen2.5-0.5B-Instruct"
    assert config["public_sample_manifest"] == "data/public-samples/manifest_public_sample.json"
    assert config["output_root"] == "<a100_project_root>"
    assert config["output_dir"] == "<a100_project_root>/runs/a100-sft-public-smoke"
    assert config["adapter_output_dir"] == "<a100_project_root>/runs/a100-sft-public-smoke/adapter"
    assert config["a100_project_root_policy"] == A100_PROJECT_ROOT_POLICY
    assert config["gpu_selection_policy"] == "select_idle_gpu_only_no_process_interruption"
    assert scan_paths([config_path]).ok is True


def test_runtime_label_provenance_config_template_is_public_safe_and_requires_private_override() -> None:
    config_path = REPO_ROOT / "configs" / "sft-runtime-label-provenance-prep.json"

    assert config_path.exists()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    serialized = json.dumps(config, ensure_ascii=False, sort_keys=True)

    assert config["private_override_required"] is True
    assert config["allow_runtime_label_provenance_check"] is False
    assert config["true_label_mask_status"] == "unavailable"
    assert config["label_tensor_available"] is False
    assert config["output_root"] == "<a100_project_root>"
    assert "<a100_project_root>" in serialized
    assert "private override" in " ".join(config["private_override_requirements"]).lower()
    assert "prep_only_no_train_dependency_import_no_model_download" == config["dependency_policy"]
    assert set(config["prior_artifacts"]) == {
        "sft_label_provenance",
        "sft_target_template_alignment",
        "a100_train_split_overfit_diagnostic",
    }
    assert "/mnt/data/" not in serialized
    assert "/Users/" not in serialized
    assert scan_paths([config_path]).ok is True


def test_runtime_label_provenance_prep_blocks_unresolved_private_override_and_keeps_true_labels_unavailable(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    manifest = _write_manifest(tmp_path)
    config = _write_runtime_label_provenance_config(tmp_path, allow_runtime_check=True)

    def fail_if_train_dependencies_checked() -> bool:
        raise AssertionError("runtime prep must not inspect train dependencies")

    monkeypatch.setattr(training, "_train_dependencies_available", fail_if_train_dependencies_checked)

    metadata = training.prepare_sft_runtime_label_provenance(config, manifest)
    serialized = json.dumps(metadata, ensure_ascii=False, sort_keys=True)

    assert metadata["evidence_kind"] == "sft_runtime_label_provenance_prep"
    assert metadata["runtime_check_status"] == "blocked_unresolved_private_override"
    assert metadata["runtime_gate"] == {
        "cli_requested_runtime_check": False,
        "config_allow_runtime_label_provenance_check": True,
        "private_override_resolved": False,
        "will_run_runtime_label_provenance_check": False,
    }
    assert metadata["private_override"]["required"] is True
    assert metadata["private_override"]["status"] == "unresolved"
    assert set(metadata["private_override"]["unresolved_fields"]) == {
        "adapter_path",
        "evidence_output_dir",
        "output_root",
        "runtime_check_output_dir",
    }
    assert metadata["dependency_policy"]["train_dependencies_imported"] is False
    assert metadata["dependency_policy"]["model_download_allowed"] is False
    assert metadata["dependency_policy"]["private_adapter_load_allowed"] is False
    assert metadata["label_provenance_intent"]["private_labels_inspected"] is False
    assert metadata["label_tensor_available"] is False
    assert metadata["true_label_mask_status"] == "unavailable"
    assert "runtime_check_not_executed" in metadata["evidence_gaps"]
    assert "/mnt/data/" not in serialized
    assert "/Users/" not in serialized


def test_runtime_label_provenance_prep_defaults_to_non_heavy_skipped_status(tmp_path: Path) -> None:
    manifest = _write_manifest(tmp_path)
    resolved_root = tmp_path / "private-a100-root"
    config = _write_runtime_label_provenance_config(
        tmp_path,
        allow_runtime_check=False,
        output_root=resolved_root.as_posix(),
        adapter_path=(resolved_root / "runs" / "adapter").as_posix(),
    )

    metadata = training.prepare_sft_runtime_label_provenance(config, manifest)

    assert metadata["runtime_check_status"] == "skipped_no_runtime_opt_in"
    assert metadata["runtime_gate"] == {
        "cli_requested_runtime_check": False,
        "config_allow_runtime_label_provenance_check": False,
        "private_override_resolved": True,
        "will_run_runtime_label_provenance_check": False,
    }
    assert metadata["output_root_policy"]["status"] == "resolved_private_override_not_run"
    assert metadata["label_tensor_available"] is False
    assert metadata["true_label_mask_status"] == "unavailable"
    assert metadata["claims"]["runtime_readiness_proves_contract_learning"] is False


def test_runtime_label_provenance_prep_blocks_partial_override_with_unresolved_evidence_output_dir(
    tmp_path: Path,
) -> None:
    manifest = _write_manifest(tmp_path)
    resolved_root = tmp_path / "private-a100-root"
    config = _write_runtime_label_provenance_config(
        tmp_path,
        allow_runtime_check=True,
        output_root=resolved_root.as_posix(),
        adapter_path=(resolved_root / "runs" / "adapter").as_posix(),
        runtime_check_output_dir=(resolved_root / "evidence" / "runtime-label-provenance-prep").as_posix(),
        evidence_output_dir="<a100_project_root>/evidence/runtime-label-provenance-prep",
    )

    metadata = training.prepare_sft_runtime_label_provenance(config, manifest)

    assert metadata["runtime_check_status"] == "blocked_unresolved_private_override"
    assert metadata["runtime_gate"]["private_override_resolved"] is False
    assert metadata["private_override"]["status"] == "unresolved"
    assert metadata["private_override"]["unresolved_fields"] == ["evidence_output_dir"]


def test_runtime_label_provenance_train_cli_writes_prep_metadata_without_stdout(
    tmp_path: Path,
    capsys: Any,
) -> None:
    manifest = _write_manifest(tmp_path)
    config = _write_runtime_label_provenance_config(tmp_path, allow_runtime_check=True)
    output = tmp_path / "runtime_prep.json"

    assert (
        train_cli.main(
            [
                "sft-prepare-runtime-label-provenance",
                "--config",
                config.as_posix(),
                "--manifest",
                manifest.as_posix(),
                "--output",
                output.as_posix(),
            ]
        )
        == 0
    )

    assert capsys.readouterr().out == ""
    metadata = json.loads(output.read_text(encoding="utf-8"))
    assert metadata["runtime_check_status"] == "blocked_unresolved_private_override"
    assert metadata["metadata_path"] == output.as_posix()


def test_sft_heavy_training_requires_cli_and_config_opt_ins(monkeypatch: Any, tmp_path: Path) -> None:
    manifest = _write_manifest(tmp_path)
    calls: list[Path] = []

    monkeypatch.setattr(training, "_train_dependencies_available", lambda: True)
    monkeypatch.setattr(
        training,
        "_run_real_sft",
        lambda metadata, config, manifest_path, output_dir: calls.append(output_dir),
    )

    allowed_root = tmp_path / "remote-root"
    config_allows = _write_config(tmp_path, allow_heavy_training=True, output_root=allowed_root.as_posix())
    dry_run_meta = run_sft(
        config_path=config_allows,
        manifest_path=manifest,
        output_dir=tmp_path / "dry-run",
        dry_run=True,
    )
    assert calls == []
    assert dry_run_meta["heavy_training_gate"] == {
        "cli_run_training": False,
        "config_allow_heavy_training": True,
        "will_run_heavy_training": False,
    }
    assert dry_run_meta["command_summary"]["mode"] == "dry_run"

    config_blocks = _write_config(tmp_path, allow_heavy_training=False)
    blocked_meta = run_sft(
        config_path=config_blocks,
        manifest_path=manifest,
        output_dir=tmp_path / "blocked",
        dry_run=False,
    )
    assert calls == []
    assert blocked_meta["release_status"] == "not_released"
    assert blocked_meta["training_status"] == "training_skipped_by_config"
    assert blocked_meta["heavy_training_gate"] == {
        "cli_run_training": True,
        "config_allow_heavy_training": False,
        "will_run_heavy_training": False,
    }

    run_meta = run_sft(
        config_path=config_allows,
        manifest_path=manifest,
        output_dir=allowed_root / "runs" / "run",
        dry_run=False,
    )
    assert calls == [allowed_root / "runs" / "run"]
    assert run_meta["release_status"] == "not_released"
    assert run_meta["heavy_training_gate"]["will_run_heavy_training"] is True
    assert run_meta["command_summary"]["mode"] == "run_training"


def test_sft_a100_run_training_blocks_output_outside_configured_root(monkeypatch: Any, tmp_path: Path) -> None:
    manifest = _write_manifest(tmp_path)
    allowed_root = tmp_path / "allowed-root"
    config = _write_config(tmp_path, allow_heavy_training=True, output_root=allowed_root.as_posix())
    calls: list[Path] = []
    monkeypatch.setattr(training, "_train_dependencies_available", lambda: True)
    monkeypatch.setattr(
        training,
        "_run_real_sft",
        lambda metadata, config, manifest_path, output_dir: calls.append(output_dir),
    )

    metadata = run_sft(
        config_path=config,
        manifest_path=manifest,
        output_dir=tmp_path / "outside-root",
        dry_run=False,
    )

    assert calls == []
    assert metadata["release_status"] == "not_released"
    assert metadata["training_status"] == "training_blocked_by_output_policy"
    assert metadata["heavy_training_gate"]["will_run_heavy_training"] is False
    assert "outside configured output_root" in metadata["notes"]


def test_sft_a100_run_training_blocks_unresolved_public_template_output_root(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    manifest = _write_manifest(tmp_path)
    config = _write_config(tmp_path, allow_heavy_training=True, output_root="<a100_project_root>")
    calls: list[Path] = []
    monkeypatch.setattr(training, "_train_dependencies_available", lambda: True)
    monkeypatch.setattr(
        training,
        "_run_real_sft",
        lambda metadata, config, manifest_path, output_dir: calls.append(output_dir),
    )

    metadata = run_sft(
        config_path=config,
        manifest_path=manifest,
        output_dir=Path("<a100_project_root>") / "runs" / "run",
        dry_run=False,
    )

    assert calls == []
    assert metadata["release_status"] == "not_released"
    assert metadata["training_status"] == "training_blocked_by_output_policy"
    assert metadata["heavy_training_gate"]["will_run_heavy_training"] is False
    assert "unresolved output_root template" in metadata["notes"]


def test_sft_metadata_contains_public_safe_a100_smoke_fields(monkeypatch: Any, tmp_path: Path) -> None:
    manifest = _write_manifest(tmp_path)
    allowed_root = tmp_path / "remote-root"
    config = _write_config(tmp_path, allow_heavy_training=True, output_root=allowed_root.as_posix())
    output_dir = allowed_root / "runs" / "run"
    monkeypatch.setattr(training, "_train_dependencies_available", lambda: True)
    monkeypatch.setattr(training, "_run_real_sft", lambda metadata, config, manifest_path, output_dir: None)

    metadata = run_sft(config_path=config, manifest_path=manifest, output_dir=output_dir, dry_run=False)

    assert metadata["release_status"] == "not_released"
    assert metadata["dataset_manifest_id"] == "public-sample-test"
    assert metadata["gpu_selection_policy"]["policy"] == "select_idle_gpu_only_no_process_interruption"
    assert metadata["gpu_selection_policy"]["identifier_policy"] == "policy_only_no_host_ip_or_gpu_uuid"
    assert metadata["output_paths"]["run_output_dir"] == output_dir.as_posix()
    assert metadata["output_paths"]["adapter_path"] == (output_dir / "adapter").as_posix()
    assert metadata["output_paths"]["metadata_path"] == (output_dir / "adapter_metadata.json").as_posix()
    assert metadata["output_paths"]["configured_output_root"] == allowed_root.as_posix()
    assert metadata["command_summary"]["entrypoint"] == "voice2task-train sft"
    assert metadata["command_summary"]["requires_cli_run_training"] is True
    assert metadata["command_summary"]["requires_config_allow_heavy_training"] is True
    assert metadata["command_summary"]["mode"] == "run_training"
    assert set(metadata["package_versions"]).issuperset(
        {"python", "accelerate", "datasets", "peft", "transformers", "trl"}
    )
    assert all("/" not in str(version) for version in metadata["package_versions"].values())


def test_sft_training_failure_writes_sanitized_metadata(monkeypatch: Any, tmp_path: Path) -> None:
    manifest = _write_manifest(tmp_path)
    allowed_root = tmp_path / "remote-root"
    config = _write_config(tmp_path, allow_heavy_training=True, output_root=allowed_root.as_posix())
    output_dir = allowed_root / "runs" / "run"
    monkeypatch.setattr(training, "_train_dependencies_available", lambda: True)

    def fail_training(metadata: dict[str, Any], config: dict[str, Any], manifest_path: Path, output_dir: Path) -> None:
        raise RuntimeError("Network is unreachable while reading /" + "Users/person/token.txt")

    monkeypatch.setattr(training, "_run_real_sft", fail_training)

    with pytest.raises(RuntimeError):
        run_sft(config_path=config, manifest_path=manifest, output_dir=output_dir, dry_run=False)

    metadata = json.loads((output_dir / "adapter_metadata.json").read_text(encoding="utf-8"))
    assert metadata["release_status"] == "not_released"
    assert metadata["training_status"] == "training_failed"
    assert metadata["error_category"] == "model_download_unavailable"
    assert metadata["error_summary"] == "Training failed before completion; raw logs remain private."
    assert "Users" not in json.dumps(metadata)


def test_public_a100_smoke_evidence_sample_is_safe_and_honest() -> None:
    evidence_dir = REPO_ROOT / "reports" / "public-sample" / "a100-sft-smoke"
    manifest_path = evidence_dir / "manifest.json"
    report_path = evidence_dir / "report.md"

    assert manifest_path.exists()
    assert report_path.exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    report = report_path.read_text(encoding="utf-8").lower()

    assert manifest["release_status"] == "not_released"
    assert manifest["claims"]["checkpoint_release"] is False
    assert manifest["claims"]["live_browser_benchmark_claim"] is False
    assert manifest["artifact_policy"]["raw_logs_copied_to_git"] is False
    assert manifest["artifact_policy"]["checkpoints_or_adapters_copied_to_git"] is False
    assert "not a checkpoint release" in report
    assert "no live-browser benchmark improvement claim" in report
    assert scan_paths([evidence_dir]).ok is True


def test_public_a100_smoke_evidence_omits_exact_remote_run_paths() -> None:
    evidence_dir = REPO_ROOT / "reports" / "public-sample" / "a100-sft-smoke"
    human_brief = REPO_ROOT / "docs" / "human-briefs" / "2026-06-02-a100-sft-smoke-run.html"
    runbook = REPO_ROOT / "README.md"
    smoke_config = REPO_ROOT / "configs" / "sft-a100-public-smoke.json"
    exact_private_paths = [
        A100_PROJECT_DIR + "/runs/a100-sft-public-smoke",
        A100_PROJECT_DIR + "/runs/a100-sft-public-smoke-modelscope",
        A100_PROJECT_DIR + "/models/Qwen2.5-0.5B-Instruct-modelscope",
    ]

    public_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in [*sorted(evidence_dir.glob("*")), human_brief, runbook, smoke_config]
        if path.is_file()
    )

    for private_path in exact_private_paths:
        assert private_path not in public_text


def test_evidence_leak_scan_rejects_ssh_details_private_rows_and_oversized_corpora(tmp_path: Path) -> None:
    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir()
    bad_report = evidence_dir / "report.md"
    bad_report.write_text(
        "\n".join(
            [
                "api_" + "key=abcd1234efgh",
                "ssh " + "operator@10" + ".1.2.3",
                "/" + "Users/person/private.jsonl",
            ]
        ),
        encoding="utf-8",
    )
    (evidence_dir / "raw-private.jsonl").write_text(
        '{"provenance":{"public_safe":false}}\n',
        encoding="utf-8",
    )
    (evidence_dir / "generated.jsonl").write_text("{}\n" * 6, encoding="utf-8")

    result = scan_paths([evidence_dir], max_public_jsonl_rows=5)

    assert {
        "private_path",
        "secret",
        "private_ip",
        "ssh_detail",
        "raw_private_row",
        "oversized_public_corpus",
    }.issubset({finding.category for finding in result.findings})
