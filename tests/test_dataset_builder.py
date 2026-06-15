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
        "wrong_task_type",
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
    wrong_task_type_pair = dpo_by_id["seed-search-wrong_task_type"]
    assert wrong_task_type_pair["chosen_contract"]["task_type"] == "search"
    assert wrong_task_type_pair["rejected_contract"]["task_type"] != "search"
    assert wrong_task_type_pair["rejection_reason"] == "wrong_task_type"
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


def test_build_public_sample_dataset_adds_extract_price_hard_negatives(tmp_path: Path) -> None:
    seed_path = tmp_path / "extract-seed.jsonl"
    output_dir = tmp_path / "public"
    rows = [
        {
            "id": "seed-extract-price",
            "split": "train",
            "input_text": "帮我看看这个东西现在卖多少钱",
            "target_contract": {
                "task_type": "extract",
                "route": "extract_page",
                "safety": {"allow": True, "reason": "public_readonly"},
                "confirmation_required": False,
                "contract_version": "v1",
                "language": "zh-CN",
                "slots": {"target": "商品价格"},
                "normalized_command": "提取页面商品价格",
            },
            "augmentations": ["把页面上标价找出来"],
        }
    ]
    seed_path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows), encoding="utf-8")

    manifest = build_public_sample_dataset(seed_path=seed_path, output_dir=output_dir)

    dpo_rows = [
        json.loads(line)
        for line in (output_dir / "dpo_public_sample.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    dpo_by_id = {row["id"]: row for row in dpo_rows}
    assert manifest.dpo_rejection_counts["extract_search_fallback"] == 1
    assert manifest.dpo_rejection_counts["extract_query_slot"] == 1
    assert manifest.dpo_rejection_counts["extract_generic_price_wording"] == 1
    assert manifest.dpo_rejection_counts["extract_listed_price_wording"] == 1
    assert manifest.dpo_rejection_counts["extract_extra_particle_wording"] == 1

    search_fallback = dpo_by_id["seed-extract-price-extract_search_fallback"]
    assert search_fallback["chosen_contract"]["task_type"] == "extract"
    assert search_fallback["chosen_contract"]["route"] == "extract_page"
    assert search_fallback["chosen_contract"]["slots"] == {"target": "商品价格"}
    assert search_fallback["rejected_contract"]["task_type"] == "search"
    assert search_fallback["rejected_contract"]["route"] == "search_web"
    assert search_fallback["rejected_contract"]["slots"] == {"query": "商品价格"}

    query_slot = dpo_by_id["seed-extract-price-extract_query_slot"]
    assert query_slot["chosen_contract"]["slots"] == {"target": "商品价格"}
    assert query_slot["rejected_contract"]["task_type"] == "extract"
    assert query_slot["rejected_contract"]["route"] == "extract_page"
    assert query_slot["rejected_contract"]["slots"] == {"query": "商品价格", "page_url": ""}
    assert "seed-extract-price-aug-1-extract_search_fallback" not in dpo_by_id

    generic_wording = dpo_by_id["seed-extract-price-extract_generic_price_wording"]
    assert generic_wording["chosen_contract"]["slots"] == {"target": "商品价格"}
    assert generic_wording["chosen_contract"]["normalized_command"] == "提取页面商品价格"
    assert generic_wording["rejected_contract"]["slots"] == {"target": "价格"}
    assert generic_wording["rejected_contract"]["normalized_command"] == "页面价格"

    listed_wording = dpo_by_id["seed-extract-price-extract_listed_price_wording"]
    assert listed_wording["chosen_contract"]["slots"] == {"target": "商品价格"}
    assert listed_wording["rejected_contract"]["slots"] == {"target": "标价"}
    assert listed_wording["rejected_contract"]["normalized_command"] == "提取页面标价"

    extra_particle = dpo_by_id["seed-extract-price-extract_extra_particle_wording"]
    assert extra_particle["chosen_contract"]["slots"] == {"target": "商品价格"}
    assert extra_particle["rejected_contract"]["slots"] == {"target": "商品价格"}
    assert extra_particle["rejected_contract"]["normalized_command"] == "提取页面上的商品价格"
    assert "seed-extract-price-aug-1-extract_generic_price_wording" not in dpo_by_id


def test_build_public_sample_dataset_adds_train_only_heldout_repair_exemplars(tmp_path: Path) -> None:
    seed_path = Path("data/public-samples/seed_traces.jsonl")
    output_dir = tmp_path / "public"

    manifest = build_public_sample_dataset(seed_path=seed_path, output_dir=output_dir)

    sft_rows = [
        json.loads(line)
        for line in (output_dir / "sft_public_sample.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    rows_by_id = {row["id"]: row for row in sft_rows}
    dpo_rows = [
        json.loads(line)
        for line in (output_dir / "dpo_public_sample.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    dpo_by_id = {row["id"]: row for row in dpo_rows}

    assert rows_by_id["seed-open-help"]["split"] == "train"
    assert rows_by_id["seed-open-help"]["target_contract"]["slots"] == {"url": "https://help.example.com"}
    assert rows_by_id["seed-open-help"]["target_contract"]["normalized_command"] == "打开帮助中心"
    assert rows_by_id["seed-clarify-target"]["split"] == "train"
    assert rows_by_id["seed-clarify-target"]["target_contract"]["task_type"] == "clarify"
    assert rows_by_id["seed-form-nickname"]["split"] == "train"
    assert rows_by_id["seed-form-nickname"]["target_contract"]["slots"] == {"field": "昵称"}
    assert rows_by_id["seed-block-transfer"]["split"] == "train"
    assert rows_by_id["seed-block-transfer"]["target_contract"]["safety"] == {
        "allow": False,
        "reason": "unsafe_payment",
    }
    assert rows_by_id["seed-open-example"]["split"] == "dev"
    assert rows_by_id["seed-clarify-ambiguous"]["split"] == "dev"
    assert rows_by_id["seed-form-email"]["split"] == "test"
    assert rows_by_id["seed-block-purchase"]["split"] == "test"
    assert manifest.split_counts["dev"] == 69
    assert manifest.split_counts["test"] == 69
    assert manifest.split_counts["train"] == 93

    expected_repair_categories = {
        "clarify_action_drift",
        "blocked_payment_action_drift",
        "form_confirmation_drift",
        "navigate_canonical_url_drift",
    }
    assert expected_repair_categories.issubset(set(manifest.dpo_rejection_counts))
    assert expected_repair_categories.issubset(
        {row["rejection_reason"] for row in dpo_rows if row["id"].startswith("seed-")}
    )
    navigate_drift = dpo_by_id["seed-open-help-navigate_canonical_url_drift"]
    assert navigate_drift["chosen_contract"]["slots"] == {"url": "https://help.example.com"}
    assert navigate_drift["rejected_contract"]["slots"] == {"url": "help.example.com"}
    assert dpo_by_id["seed-open-example-navigate_canonical_url_drift"]["split"] == "dev"


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
