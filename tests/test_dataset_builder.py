import json
from pathlib import Path

from voice2task.dataset import build_local_private_corpus, build_public_sample_dataset
from voice2task.validation import validate_dataset_artifacts


def _write_seed(path: Path) -> None:
    rows = [
        {
            "id": "seed-search",
            "split": "train",
            "input_text": "帮我搜索北京明天的天气",
            "target_contract": {
                "task_type": "search",
                "route": "search_web",
                "safety": {"allow": True, "reason": "public_readonly"},
                "confirmation_required": False,
                "contract_version": "v1",
                "language": "zh-CN",
                "slots": {"query": "北京 明天 天气"},
                "normalized_command": "搜索北京明天天气",
            },
            "augmentations": ["查一下北京明天天气", "搜北京明天的天气"],
        },
        {
            "id": "seed-form",
            "split": "dev",
            "input_text": "把邮箱填到这个网页里，提交前问我",
            "target_contract": {
                "task_type": "form_fill",
                "route": "fill_form",
                "safety": {"allow": True, "reason": "requires_confirmation"},
                "confirmation_required": True,
                "contract_version": "v1",
                "language": "zh-CN",
                "slots": {"field": "邮箱"},
                "normalized_command": "填写邮箱并确认",
            },
            "augmentations": ["在网页里填邮箱，提交之前确认"],
        },
    ]
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows), encoding="utf-8")


def test_build_public_sample_dataset_writes_manifest_sft_and_dpo(tmp_path: Path) -> None:
    seed_path = tmp_path / "seed.jsonl"
    output_dir = tmp_path / "public"
    _write_seed(seed_path)

    manifest = build_public_sample_dataset(seed_path=seed_path, output_dir=output_dir)

    assert manifest.mode == "public_sample"
    assert manifest.counts["sft_rows"] >= 3
    assert manifest.counts["dpo_pairs"] >= 6
    expected_categories = {
        "wrong_route",
        "unsafe_allowance",
        "missing_confirmation",
        "wrong_slot",
        "decomposed_search_slots",
        "underspecified_request",
        "malformed_schema",
    }
    assert expected_categories.issubset(set(manifest.dpo_rejection_counts))
    assert (output_dir / "sft_public_sample.jsonl").exists()
    assert (output_dir / "dpo_public_sample.jsonl").exists()
    assert (output_dir / "manifest_public_sample.json").exists()
    sft_rows = [
        json.loads(line)
        for line in (output_dir / "sft_public_sample.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    normalized_by_id = {row["id"]: row["target_contract"]["normalized_command"] for row in sft_rows}
    slots_by_id = {row["id"]: row["target_contract"]["slots"] for row in sft_rows}
    dpo_rows = [
        json.loads(line)
        for line in (output_dir / "dpo_public_sample.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    dpo_by_id = {row["id"]: row for row in dpo_rows}
    assert normalized_by_id["seed-search"] == "搜索北京明天天气"
    assert normalized_by_id["seed-search-aug-1"] == "搜索北京明天天气"
    assert normalized_by_id["seed-search-aug-2"] == "搜索北京明天天气"
    assert slots_by_id["seed-search"] == {"query": "北京明天天气"}
    assert slots_by_id["seed-search-aug-1"] == {"query": "北京明天天气"}
    assert slots_by_id["seed-search-aug-2"] == {"query": "北京明天天气"}
    assert normalized_by_id["seed-form"] == "填写邮箱并确认"
    assert normalized_by_id["seed-form-aug-1"] == "填写邮箱并确认"
    decomposed_pair = dpo_by_id["seed-search-decomposed_search_slots"]
    assert decomposed_pair["chosen_contract"]["slots"] == {"query": "北京明天天气"}
    assert decomposed_pair["rejected_contract"]["slots"] == {"city": "北京", "date": "明天", "topic": ""}
    assert decomposed_pair["rejection_reason"] == "decomposed_search_slots"
    assert "seed-form-decomposed_search_slots" not in dpo_by_id

    result = validate_dataset_artifacts(
        sft_path=output_dir / "sft_public_sample.jsonl",
        dpo_path=output_dir / "dpo_public_sample.jsonl",
        manifest_path=output_dir / "manifest_public_sample.json",
        public=True,
    )
    assert result.ok is True
    assert result.failures == []


def test_build_local_private_corpus_writes_split_files_and_summary(tmp_path: Path) -> None:
    seed_path = tmp_path / "private-seed.jsonl"
    output_dir = tmp_path / "local-private"
    _write_seed(seed_path)

    manifest = build_local_private_corpus(seed_trace_path=seed_path, output_dir=output_dir)

    assert manifest.mode == "local_private"
    assert manifest.source_summary["seed_rows"] == 2
    assert (output_dir / "train.jsonl").exists()
    assert (output_dir / "dev.jsonl").exists()
    assert (output_dir / "test.jsonl").exists()
    assert (output_dir / "dpo_pairs.jsonl").exists()
    assert (output_dir / "manifest_local_private.json").exists()
    private_dpo_rows = [
        json.loads(line)
        for line in (output_dir / "dpo_pairs.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert all(row["rejection_reason"] != "decomposed_search_slots" for row in private_dpo_rows)
