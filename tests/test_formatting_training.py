import json
from pathlib import Path

from voice2task.formatting import format_dpo_pair, format_sft_messages
from voice2task.schemas import BrowserTaskContract, DPOPair, SFTDatasetRow
from voice2task.training import run_dpo, run_sft


def _contract() -> BrowserTaskContract:
    return BrowserTaskContract(
        task_type="search",
        route="search_web",
        safety={"allow": True, "reason": "public_readonly"},
        confirmation_required=False,
        slots={"query": "高铁票"},
        normalized_command="搜索高铁票",
    )


def test_sft_formatter_uses_contract_json_only() -> None:
    row = SFTDatasetRow(
        id="sft-1",
        split="train",
        input_text="帮我搜高铁票",
        target_contract=_contract(),
        provenance={"source_id": "seed-1", "public_safe": True},
    )

    messages = format_sft_messages(row)

    assert [message["role"] for message in messages] == ["system", "user", "assistant"]
    assistant = messages[-1]["content"]
    assert assistant.startswith("{")
    assert "我可以" not in assistant
    assert json.loads(assistant)["route"] == "search_web"


def test_dpo_formatter_keeps_same_prompt_with_chosen_and_rejected_contracts() -> None:
    chosen = _contract()
    rejected = BrowserTaskContract(
        task_type="search",
        route="open_url",
        safety={"allow": True, "reason": "wrong_route"},
        confirmation_required=False,
        slots={"query": "高铁票"},
        normalized_command="搜索高铁票",
    )
    pair = DPOPair(
        id="dpo-1",
        split="train",
        input_text="帮我搜高铁票",
        chosen_contract=chosen,
        rejected_contract=rejected,
        rejection_reason="wrong_route",
        provenance={"source_id": "seed-1", "public_safe": True},
    )

    formatted = format_dpo_pair(pair)

    assert formatted["prompt"][-1]["content"] == "帮我搜高铁票"
    assert json.loads(formatted["chosen"])["route"] == "search_web"
    assert json.loads(formatted["rejected"])["route"] == "open_url"
    assert formatted["rejection_reason"] == "wrong_route"


def test_sft_and_dpo_dry_runs_write_honest_adapter_metadata(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps({"manifest_id": "public-sample-1"}), encoding="utf-8")
    sft_config = tmp_path / "sft.json"
    dpo_config = tmp_path / "dpo.json"
    sft_config.write_text(json.dumps({"base_model": "Qwen/Qwen2.5-0.5B-Instruct", "lora": {"r": 8}}), encoding="utf-8")
    dpo_config.write_text(
        json.dumps({"base_model": "Qwen/Qwen2.5-0.5B-Instruct", "sft_model_ref": "adapters/sft-dev", "lora": {"r": 8}}),
        encoding="utf-8",
    )

    sft_meta = run_sft(config_path=sft_config, manifest_path=manifest_path, output_dir=tmp_path / "sft", dry_run=True)
    dpo_meta = run_dpo(config_path=dpo_config, manifest_path=manifest_path, output_dir=tmp_path / "dpo", dry_run=True)

    assert sft_meta["dry_run"] is True
    assert sft_meta["release_status"] == "not_released"
    assert sft_meta["dataset_manifest_id"] == "public-sample-1"
    assert Path(sft_meta["metadata_path"]).exists()
    assert dpo_meta["sft_model_ref"] == "adapters/sft-dev"
    assert dpo_meta["release_status"] == "not_released"
    assert Path(dpo_meta["metadata_path"]).exists()


def test_sft_and_dpo_non_dry_run_report_missing_train_dependencies(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps({"manifest_id": "public-sample-1"}), encoding="utf-8")
    config = tmp_path / "train.json"
    config.write_text(json.dumps({"base_model": "Qwen/Qwen2.5-0.5B-Instruct"}), encoding="utf-8")

    sft_meta = run_sft(config_path=config, manifest_path=manifest_path, output_dir=tmp_path / "sft", dry_run=False)
    dpo_meta = run_dpo(config_path=config, manifest_path=manifest_path, output_dir=tmp_path / "dpo", dry_run=False)

    assert sft_meta["dry_run"] is False
    assert sft_meta["release_status"] in {"not_released", "training_skipped_by_config", "training_unavailable"}
    assert "always disabled" not in sft_meta["notes"]
    assert dpo_meta["dry_run"] is False
    assert dpo_meta["release_status"] in {"not_released", "training_skipped_by_config", "training_unavailable"}
