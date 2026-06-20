from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from voice2task import training


def test_manifest_file_resolution_prefers_manifest_snapshot_dir(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    snapshot = tmp_path / "snapshot" / "data" / "public-samples"
    workspace_public = workspace / "data" / "public-samples"
    snapshot.mkdir(parents=True)
    workspace_public.mkdir(parents=True)
    (snapshot / "sft_public_sample.jsonl").write_text('{"id":"snapshot"}\n', encoding="utf-8")
    (workspace_public / "sft_public_sample.jsonl").write_text('{"id":"workspace"}\n', encoding="utf-8")
    manifest_path = snapshot / "manifest_public_sample.json"
    manifest_path.write_text("{}", encoding="utf-8")

    monkeypatch.chdir(workspace)

    resolved = training._resolve_manifest_file(manifest_path, "data/public-samples/sft_public_sample.jsonl")

    assert resolved == snapshot / "sft_public_sample.jsonl"


def test_sft_training_arguments_include_paired_ablation_invariants(monkeypatch):
    captured: dict[str, object] = {}

    class FakeTrainingArguments:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setitem(
        __import__("sys").modules,
        "transformers",
        SimpleNamespace(TrainingArguments=FakeTrainingArguments),
    )

    config = {
        "num_train_epochs": 3,
        "max_steps": 120,
        "per_device_train_batch_size": 2,
        "gradient_accumulation_steps": 4,
        "learning_rate": 0.0002,
        "warmup_ratio": 0.1,
        "logging_steps": 5,
        "save_strategy": "no",
        "seed": 7170,
    }

    training._training_arguments(config, Path("out"))

    assert captured["num_train_epochs"] == 3.0
    assert captured["max_steps"] == 120
    assert captured["per_device_train_batch_size"] == 2
    assert captured["gradient_accumulation_steps"] == 4
    assert captured["learning_rate"] == 0.0002
    assert captured["warmup_ratio"] == 0.1
    assert captured["logging_steps"] == 5
    assert captured["save_strategy"] == "no"
    assert captured["seed"] == 7170
    assert captured["report_to"] == []


def test_runtime_base_model_can_use_private_path_without_changing_public_id():
    config = {
        "base_model": "Qwen/Qwen2.5-7B-Instruct",
        "base_model_runtime_path": "<a100_project_root>/models/qwen2.5-7b-instruct",
    }

    assert training._public_base_model(config) == "Qwen/Qwen2.5-7B-Instruct"
    assert training._runtime_base_model(config) == "<a100_project_root>/models/qwen2.5-7b-instruct"
