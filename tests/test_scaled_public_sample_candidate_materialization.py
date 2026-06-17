import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

import pytest

from voice2task import dataset as dataset_module
from voice2task.cli import data as data_cli
from voice2task.io import read_json, read_jsonl
from voice2task.leak_scan import scan_paths

REPO_ROOT = Path(__file__).resolve().parents[1]
PUBLIC_SAMPLE_PATHS = [
    REPO_ROOT / "data" / "public-samples" / "seed_traces.jsonl",
    REPO_ROOT / "data" / "public-samples" / "sft_public_sample.jsonl",
    REPO_ROOT / "data" / "public-samples" / "dpo_public_sample.jsonl",
    REPO_ROOT / "data" / "public-samples" / "manifest_public_sample.json",
]
CORE_DELTAS = {
    "blocked_payment": 20,
    "clarify": 33,
    "extract": 25,
    "form_fill": 3,
    "navigation": 17,
    "search": 20,
}


def _materializer() -> Any:
    assert hasattr(dataset_module, "materialize_scaled_public_sample_candidates")
    return dataset_module.materialize_scaled_public_sample_candidates


def _sha256_by_path(paths: list[Path]) -> dict[Path, str]:
    return {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}


def _assert_scaled_candidate_payload(seed_rows: list[dict[str, Any]], sft_rows: list[dict[str, Any]]) -> None:
    assert len(seed_rows) == 138
    assert len(sft_rows) == 414
    assert {row["split"] for row in seed_rows} == {"train", "dev", "test"}
    assert {row["split"] for row in sft_rows} == {"train", "dev", "test"}

    seed_ids = [row["id"] for row in seed_rows]
    sft_ids = [row["id"] for row in sft_rows]
    assert len(seed_ids) == len(set(seed_ids))
    assert len(sft_ids) == len(set(sft_ids))

    assert all(row["provenance"]["candidate_status"] == "standalone_not_formal_public_sample" for row in seed_rows)
    assert all(row["provenance"]["source_mode"] == "scaled_public_sample_candidate_seed" for row in seed_rows)
    assert all(row["provenance"]["public_safe"] is True for row in seed_rows)

    core_rows = [
        row
        for row in seed_rows
        if row["provenance"]["scaled_candidate_group"] == "core_family_delta"
    ]
    overlay_rows = [
        row
        for row in seed_rows
        if row["provenance"]["scaled_candidate_group"] == "confirmation_boundary_overlay"
    ]
    assert len(core_rows) == 118
    assert len(overlay_rows) == 20
    assert Counter(row["provenance"]["family_id"] for row in core_rows) == CORE_DELTAS
    assert Counter(row["provenance"]["overlay_family_id"] for row in overlay_rows) == {
        "confirmation_boundary": 20
    }
    extract_rows = [row for row in core_rows if row["provenance"]["family_id"] == "extract"]
    assert extract_rows
    for row in extract_rows:
        target = row["target_contract"]["slots"]["target"]
        assert target.startswith("字段")
        assert row["target_contract"]["normalized_command"] == f"提取页面{target}"
        assert "页面页面" not in row["target_contract"]["normalized_command"]

    sft_by_source = Counter(row["provenance"]["source_id"] for row in sft_rows)
    assert set(sft_by_source) == set(seed_ids)
    assert set(sft_by_source.values()) == {3}


def test_materialize_scaled_public_sample_candidates_writes_standalone_artifacts(tmp_path: Path) -> None:
    public_sample_before = _sha256_by_path(PUBLIC_SAMPLE_PATHS)
    seed_output = tmp_path / "scaled_public_sample_seed_candidates.jsonl"
    output_dir = tmp_path / "scaled-public-sample-candidate-materialization"

    paths = _materializer()(
        seed_output_path=seed_output,
        output_dir=output_dir,
    )

    assert paths["seed"] == seed_output
    assert paths["sft"] == output_dir / "sft_candidate_rows.jsonl"
    assert paths["json"] == output_dir / "scaled_public_sample_candidate_materialization.json"
    assert paths["markdown"] == output_dir / "scaled_public_sample_candidate_materialization.md"
    assert paths["manifest"] == output_dir / "manifest.json"
    assert _sha256_by_path(PUBLIC_SAMPLE_PATHS) == public_sample_before

    seed_rows = read_jsonl(seed_output)
    sft_rows = read_jsonl(paths["sft"])
    evidence = read_json(paths["json"])
    manifest = read_json(paths["manifest"])
    markdown = paths["markdown"].read_text(encoding="utf-8")

    _assert_scaled_candidate_payload(seed_rows, sft_rows)
    assert evidence["evidence_kind"] == "scaled_public_sample_candidate_materialization"
    assert evidence["materialization_status"] == "candidate_dataset_materialized"
    assert evidence["summary"]["current_formal_public_sample_counts"] == {
        "dpo_pairs": 2046,
        "seed_rows": 240,
        "sft_rows": 675,
    }
    assert evidence["summary"]["current_formal_public_sample_seed_split_counts"] == {
        "dev": 69,
        "test": 69,
        "train": 102,
    }
    assert evidence["summary"]["current_formal_public_sample_sft_split_counts"] == {
        "dev": 207,
        "test": 207,
        "train": 261,
    }
    assert evidence["summary"]["target_counts"] == {
        "core_seed_rows": 220,
        "confirmation_boundary_overlay_seed_rows": 20,
        "total_seed_rows_after_later_merge": 240,
    }
    assert evidence["summary"]["candidate_core_seed_rows"] == 118
    assert evidence["summary"]["candidate_overlay_seed_rows"] == 20
    assert evidence["summary"]["candidate_seed_rows"] == 138
    assert evidence["summary"]["candidate_sft_rows"] == 414
    assert evidence["summary"]["core_family_candidate_counts"] == CORE_DELTAS
    assert evidence["execution_scope"]["formal_public_sample_modified"] is False
    assert evidence["execution_scope"]["dpo_run"] is False
    assert evidence["execution_scope"]["training_run"] is False
    assert evidence["claims"]["held_out_generalization_recovered"] is False
    assert manifest["artifact_policy"]["candidate_data_only"] is True
    assert manifest["artifact_policy"]["formal_public_sample_files_modified"] is False
    assert "candidate data only" in markdown
    assert "does not merge the formal public sample" in markdown
    assert scan_paths([seed_output, output_dir]).ok is True


def test_materialize_scaled_public_sample_candidates_cli(tmp_path: Path, capsys: Any) -> None:
    seed_output = tmp_path / "scaled_public_sample_seed_candidates.jsonl"
    output_dir = tmp_path / "scaled-public-sample-candidate-materialization"

    assert (
        data_cli.main(
            [
                "materialize-scaled-public-sample-candidates",
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
    assert payload["summary"]["candidate_seed_rows"] == 138
    assert payload["summary"]["candidate_core_seed_rows"] == 118
    assert payload["summary"]["candidate_overlay_seed_rows"] == 20
    assert payload["summary"]["candidate_sft_rows"] == 414
    assert payload["execution_scope"]["formal_public_sample_modified"] is False
    assert payload["paths"]["seed"] == seed_output.as_posix()
    assert payload["paths"]["manifest"] == (output_dir / "manifest.json").as_posix()


@pytest.mark.parametrize(
    "protected_path",
    [
        dataset_module.FORMAL_PUBLIC_SEED_PATH,
        dataset_module.FORMAL_PUBLIC_SFT_PATH,
        dataset_module.FORMAL_PUBLIC_DPO_PATH,
        dataset_module.FORMAL_PUBLIC_MANIFEST_PATH,
    ],
)
def test_materialize_scaled_public_sample_candidates_rejects_formal_public_sample_outputs(
    tmp_path: Path,
    protected_path: Path,
) -> None:
    with pytest.raises(ValueError, match="formal public sample files"):
        _materializer()(
            seed_output_path=protected_path,
            output_dir=tmp_path / "scaled-public-sample-candidate-materialization",
        )

    with pytest.raises(ValueError, match="formal public sample files"):
        _materializer()(
            seed_output_path=tmp_path / "scaled_public_sample_seed_candidates.jsonl",
            output_dir=protected_path,
        )
