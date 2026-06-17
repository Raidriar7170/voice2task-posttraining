import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from voice2task.cli import data as data_cli
from voice2task.dataset import materialize_family_stratified_generalization_candidates
from voice2task.io import read_json, read_jsonl
from voice2task.leak_scan import scan_paths

REPO_ROOT = Path(__file__).resolve().parents[1]
PUBLIC_SAMPLE_PATHS = [
    REPO_ROOT / "data" / "public-samples" / "seed_traces.jsonl",
    REPO_ROOT / "data" / "public-samples" / "sft_public_sample.jsonl",
    REPO_ROOT / "data" / "public-samples" / "dpo_public_sample.jsonl",
    REPO_ROOT / "data" / "public-samples" / "manifest_public_sample.json",
]
COMMITTED_SEED = REPO_ROOT / "data" / "public-samples" / "family_stratified_generalization_seed_candidates.jsonl"
COMMITTED_REPORT_DIR = REPO_ROOT / "reports" / "public-sample" / "family-stratified-generalization-candidates"
EXPECTED_FAMILIES = {
    "blocked_payment",
    "clarify",
    "confirmation",
    "extract",
    "form_fill",
    "navigation",
    "search",
}
CURRENT_FORMAL_COUNTS = {"dpo_pairs": 2046, "seed_rows": 240, "sft_rows": 675}
CURRENT_FORMAL_SPLITS = {"dev": 207, "test": 207, "train": 261}


def _sha256_by_path(paths: list[Path]) -> dict[Path, str]:
    return {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}


def _slot_signature(row: dict[str, Any]) -> str:
    contract = row["target_contract"]
    return json.dumps(contract["slots"], ensure_ascii=False, sort_keys=True)


def _assert_family_stratified_payload(seed_rows: list[dict[str, Any]], sft_rows: list[dict[str, Any]]) -> None:
    assert len(seed_rows) == 63
    assert len(sft_rows) == 189
    assert {row["split"] for row in seed_rows} == {"train", "dev", "test"}
    assert {row["split"] for row in sft_rows} == {"train", "dev", "test"}

    seed_ids = [row["id"] for row in seed_rows]
    assert len(seed_ids) == len(set(seed_ids))
    assert all(row["provenance"]["candidate_status"] == "standalone_not_formal_public_sample" for row in seed_rows)
    assert all(
        row["provenance"]["source_mode"] == "family_stratified_generalization_candidate_seed" for row in seed_rows
    )
    assert all(row["provenance"]["family_stratification"] is True for row in seed_rows)
    assert all(row["provenance"]["public_safe"] is True for row in seed_rows)

    seed_counts: dict[tuple[str, str], int] = defaultdict(int)
    sft_counts: dict[tuple[str, str], int] = defaultdict(int)
    slot_signatures: dict[tuple[str, str], set[str]] = defaultdict(set)
    source_splits: dict[str, set[str]] = defaultdict(set)
    for row in seed_rows:
        family = row["provenance"]["family_id"]
        split = row["split"]
        seed_counts[(family, split)] += 1
        slot_signatures[(family, split)].add(_slot_signature(row))
        source_splits[row["id"]].add(split)
    for row in sft_rows:
        family = row["provenance"]["family_id"]
        sft_counts[(family, row["split"])] += 1

    assert {family for family, _split in seed_counts} == EXPECTED_FAMILIES
    for family in EXPECTED_FAMILIES:
        split_signature_sets = []
        for split in ("train", "dev", "test"):
            assert seed_counts[(family, split)] == 3
            assert sft_counts[(family, split)] == 9
            split_signature_sets.append(slot_signatures[(family, split)])
        assert split_signature_sets[0].isdisjoint(split_signature_sets[1])
        assert split_signature_sets[0].isdisjoint(split_signature_sets[2])
        assert split_signature_sets[1].isdisjoint(split_signature_sets[2])

    assert all(len(splits) == 1 for splits in source_splits.values())


def test_materialize_family_stratified_generalization_candidates_writes_independent_dataset(tmp_path: Path) -> None:
    public_sample_before = _sha256_by_path(PUBLIC_SAMPLE_PATHS)
    seed_output = tmp_path / "family_stratified_generalization_seed_candidates.jsonl"
    output_dir = tmp_path / "family-stratified-generalization-candidates"

    paths = materialize_family_stratified_generalization_candidates(
        seed_output_path=seed_output,
        output_dir=output_dir,
    )

    assert paths["seed"] == seed_output
    assert paths["sft"] == output_dir / "sft_candidate_rows.jsonl"
    assert paths["json"] == output_dir / "family_stratified_generalization.json"
    assert paths["markdown"] == output_dir / "family_stratified_generalization.md"
    assert paths["manifest"] == output_dir / "manifest.json"
    assert _sha256_by_path(PUBLIC_SAMPLE_PATHS) == public_sample_before

    seed_rows = read_jsonl(seed_output)
    sft_rows = read_jsonl(paths["sft"])
    evidence = read_json(paths["json"])
    manifest = read_json(paths["manifest"])
    markdown = paths["markdown"].read_text(encoding="utf-8")

    _assert_family_stratified_payload(seed_rows, sft_rows)
    assert evidence["evidence_kind"] == "family_stratified_generalization_candidates"
    assert evidence["materialization_status"] == "candidate_dataset_materialized"
    assert evidence["summary"]["candidate_seed_rows"] == 63
    assert evidence["summary"]["candidate_sft_rows"] == 189
    assert evidence["summary"]["split_counts"] == {"dev": 63, "test": 63, "train": 63}
    assert evidence["summary"]["families"] == sorted(EXPECTED_FAMILIES)
    assert evidence["execution_scope"]["formal_public_sample_modified"] is False
    assert evidence["execution_scope"]["dpo_run"] is False
    assert evidence["execution_scope"]["a100_execution"] is False
    assert evidence["claims"]["held_out_generalization_recovered"] is False
    assert evidence["claims"]["contract_exact_match_primary_metric"] is True
    assert manifest["artifact_policy"]["candidate_data_only"] is True
    assert manifest["artifact_policy"]["formal_public_sample_files_modified"] is False
    assert "candidate data only" in markdown
    assert "does not rewrite formal public sample files" in markdown
    assert scan_paths([seed_output, output_dir]).ok is True


def test_materialize_family_stratified_generalization_candidates_cli(tmp_path: Path, capsys: Any) -> None:
    seed_output = tmp_path / "family_stratified_generalization_seed_candidates.jsonl"
    output_dir = tmp_path / "family-stratified-generalization-candidates"

    assert (
        data_cli.main(
            [
                "materialize-family-stratified-candidates",
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
    assert payload["summary"]["candidate_seed_rows"] == 63
    assert payload["summary"]["candidate_sft_rows"] == 189
    assert payload["summary"]["split_counts"] == {"dev": 63, "test": 63, "train": 63}
    assert payload["execution_scope"]["formal_public_sample_modified"] is False
    assert payload["paths"]["seed"] == seed_output.as_posix()
    assert payload["paths"]["manifest"] == (output_dir / "manifest.json").as_posix()
    assert scan_paths([seed_output, output_dir]).ok is True


def test_committed_family_stratified_generalization_candidates_are_public_safe() -> None:
    public_manifest = read_json(REPO_ROOT / "data" / "public-samples" / "manifest_public_sample.json")
    evidence = read_json(COMMITTED_REPORT_DIR / "family_stratified_generalization.json")
    manifest = read_json(COMMITTED_REPORT_DIR / "manifest.json")
    seed_rows = read_jsonl(COMMITTED_SEED)
    sft_rows = read_jsonl(COMMITTED_REPORT_DIR / "sft_candidate_rows.jsonl")

    assert public_manifest["counts"] == CURRENT_FORMAL_COUNTS
    assert public_manifest["split_counts"] == CURRENT_FORMAL_SPLITS
    assert public_manifest["source_summary"]["family_stratified_candidates_formal_public_sample"] is True
    _assert_family_stratified_payload(seed_rows, sft_rows)
    assert evidence["summary"]["formal_public_sample_seed_rows"] == 77
    assert evidence["summary"]["formal_public_sample_sft_rows"] == 231
    assert evidence["summary"]["formal_public_sample_dpo_pairs"] == 661
    assert manifest["claims"]["held_out_generalization_recovered"] is False
    assert manifest["execution_scope"]["training_run"] is False
    assert manifest["execution_scope"]["prediction_run"] is False
    assert scan_paths([COMMITTED_SEED, COMMITTED_REPORT_DIR]).ok is True
