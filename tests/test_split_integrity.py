from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from voice2task.cli import data as data_cli
from voice2task.io import write_json, write_jsonl
from voice2task.split_integrity import (
    _digit_template,
    audit_split_integrity,
    render_split_integrity_markdown,
    write_split_integrity_report,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
PUBLIC_SEED = REPO_ROOT / "data/public-samples/seed_traces.jsonl"
PUBLIC_SFT = REPO_ROOT / "data/public-samples/sft_public_sample.jsonl"
PUBLIC_DPO = REPO_ROOT / "data/public-samples/dpo_public_sample.jsonl"
PUBLIC_MANIFEST = REPO_ROOT / "data/public-samples/manifest_public_sample.json"
COMMITTED_SUMMARY = REPO_ROOT / "reports/public-sample/split-integrity-audit/summary.json"
COMMITTED_MARKDOWN = REPO_ROOT / "reports/public-sample/split-integrity-audit/summary.md"


def _contract(query: str) -> dict[str, object]:
    return {
        "task_type": "search",
        "route": "search_web",
        "safety": {"allow": True, "reason": "public_readonly"},
        "confirmation_required": False,
        "slots": {"query": query},
        "normalized_command": f"搜索{query}",
        "language": "zh-CN",
        "contract_version": "v1",
    }


def _seed(row_id: str, split: str, text: str) -> dict[str, object]:
    return {
        "id": row_id,
        "split": split,
        "input_text": text,
        "target_contract": _contract(text),
        "augmentations": [],
    }


def _sft(
    row_id: str,
    split: str,
    text: str,
    *,
    provenance: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "id": row_id,
        "split": split,
        "input_text": text,
        "target_contract": _contract(text),
        "provenance": provenance or {"source_id": row_id, "public_safe": True},
    }


def _dpo(row_id: str, split: str) -> dict[str, object]:
    return {
        "id": row_id,
        "split": split,
        "input_text": f"DPO {row_id}",
        "chosen_contract": _contract(row_id),
        "rejected_contract": _contract(f"wrong-{row_id}"),
        "rejection_reason": "wrong_slot",
        "provenance": {"public_safe": True, "source_id": row_id},
    }


def _valid_seed_rows() -> list[dict[str, object]]:
    return [
        _seed("seed-train", "train", "查北京天气"),
        _seed("seed-dev", "dev", "打开帮助页面"),
        _seed("seed-test", "test", "提取公开标题"),
    ]


def _valid_sft_rows() -> list[dict[str, object]]:
    return [
        _sft("train-row", "train", "查上海天气"),
        _sft("dev-row", "dev", "进入帮助中心"),
        _sft("test-row", "test", "读取公开标题"),
    ]


def _write_fixture(
    root: Path,
    *,
    seed_rows: list[dict[str, object]] | None = None,
    sft_rows: list[dict[str, object]] | None = None,
    dpo_rows: list[dict[str, object]] | None = None,
) -> dict[str, Path]:
    seed = _valid_seed_rows() if seed_rows is None else seed_rows
    sft = _valid_sft_rows() if sft_rows is None else sft_rows
    dpo = dpo_rows or [_dpo(f"dpo-{split}", split) for split in ("train", "dev", "test")]
    paths = {
        "seed": root / "seed.jsonl",
        "sft": root / "sft.jsonl",
        "dpo": root / "dpo.jsonl",
        "manifest": root / "manifest.json",
    }
    write_jsonl(paths["seed"], seed)
    write_jsonl(paths["sft"], sft)
    write_jsonl(paths["dpo"], dpo)
    split_counts = {split: sum(row.get("split") == split for row in sft) for split in ("dev", "test", "train")}
    write_json(
        paths["manifest"],
        {
            "manifest_id": "fixture-manifest",
            "files": {name: path.name for name, path in paths.items()},
            "counts": {"seed_rows": len(seed), "sft_rows": len(sft), "dpo_pairs": len(dpo)},
            "split_counts": split_counts,
        },
    )
    return paths


def _audit(paths: dict[str, Path], repo_root: Path) -> dict[str, Any]:
    return audit_split_integrity(
        seed_path=paths["seed"],
        sft_path=paths["sft"],
        dpo_path=paths["dpo"],
        manifest_path=paths["manifest"],
        repo_root=repo_root,
    )


def _cli_args(paths: dict[str, Path], output_dir: Path, *, require_clean: bool = False) -> list[str]:
    args = [
        "audit-splits",
        "--seed",
        str(paths["seed"]),
        "--sft",
        str(paths["sft"]),
        "--dpo",
        str(paths["dpo"]),
        "--manifest",
        str(paths["manifest"]),
        "--output",
        str(output_dir),
    ]
    if require_clean:
        args.append("--require-clean")
    return args


def test_contaminated_fixture_reports_all_three_zero_gate_violations(tmp_path: Path) -> None:
    paths = _write_fixture(
        tmp_path,
        seed_rows=[
            _seed("seed-train", "train", "搜索城市1"),
            _seed("seed-dev", "dev", "搜索城市2"),
            _seed("seed-test", "test", "提取公开标题"),
        ],
        sft_rows=[
            _sft(
                "train-row",
                "train",
                "完全相同输入",
                provenance={"source_row_ids": ["dev-source"], "source_splits": {"dev": 1}},
            ),
            _sft("dev-source", "dev", "完全相同输入"),
            _sft("test-row", "test", "读取公开标题"),
        ],
    )

    audit = _audit(paths, tmp_path)

    assert audit["input_validation"]["valid"] is True
    assert audit["clean_gate"]["passed"] is False
    assert audit["clean_gate"]["violation_counts"] == {
        "cross_split_digit_template_signatures": 1,
        "heldout_exact_input_rows_overlapping_train": 1,
        "train_rows_with_dev_test_provenance": 1,
    }


def test_clean_family_disjoint_fixture_passes_enforcement(tmp_path: Path) -> None:
    paths = _write_fixture(tmp_path)
    output_dir = tmp_path / "report"

    assert data_cli.main(_cli_args(paths, output_dir, require_clean=True)) == 0
    report = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
    assert report["input_validation"]["valid"] is True
    assert report["clean_gate"]["passed"] is True


@pytest.mark.parametrize("violation_kind", ["exact_input", "digit_template", "heldout_provenance"])
def test_each_strict_zero_violation_fails_clean_gate_independently(
    tmp_path: Path,
    violation_kind: str,
) -> None:
    seed_rows = _valid_seed_rows()
    sft_rows = _valid_sft_rows()
    if violation_kind == "exact_input":
        sft_rows[2] = _sft("test-row", "test", "查上海天气")
    elif violation_kind == "digit_template":
        seed_rows[0] = _seed("seed-train", "train", "模板1")
        seed_rows[2] = _seed("seed-test", "test", "模板2")
    else:
        sft_rows[0] = _sft(
            "train-row",
            "train",
            "查上海天气",
            provenance={"source_row_ids": ["test-row"], "source_splits": {"test": 1}},
        )
    paths = _write_fixture(tmp_path, seed_rows=seed_rows, sft_rows=sft_rows)

    violations = _audit(paths, tmp_path)["clean_gate"]["violation_counts"]

    expected_key = {
        "exact_input": "heldout_exact_input_rows_overlapping_train",
        "digit_template": "cross_split_digit_template_signatures",
        "heldout_provenance": "train_rows_with_dev_test_provenance",
    }[violation_kind]
    assert violations[expected_key] == 1
    assert sum(violations.values()) == 1


def test_require_clean_cli_fails_without_suppressing_contamination_report(tmp_path: Path) -> None:
    sft_rows = _valid_sft_rows()
    sft_rows[2] = _sft("test-row", "test", "查上海天气")
    paths = _write_fixture(tmp_path, sft_rows=sft_rows)
    output_dir = tmp_path / "report"

    assert data_cli.main(_cli_args(paths, output_dir, require_clean=True)) == 1
    assert (output_dir / "summary.json").exists()
    assert (output_dir / "summary.md").exists()


@pytest.mark.parametrize("invalid_kind", ["empty", "missing_split", "unknown_split", "duplicate_id"])
def test_invalid_inputs_fail_closed_and_preserve_report(
    tmp_path: Path,
    invalid_kind: str,
) -> None:
    seed_rows = _valid_seed_rows()
    if invalid_kind == "empty":
        seed_rows = []
    elif invalid_kind == "missing_split":
        seed_rows = seed_rows[:2]
    elif invalid_kind == "unknown_split":
        seed_rows.append(_seed("seed-unknown", "holdout", "未知分片"))
    else:
        seed_rows.append(_seed("seed-train", "test", "重复标识"))
    paths = _write_fixture(tmp_path, seed_rows=seed_rows)
    output_dir = tmp_path / "report"

    assert data_cli.main(_cli_args(paths, output_dir)) == 1
    report = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
    assert report["input_validation"]["valid"] is False
    assert report["clean_gate"]["passed"] is False
    assert report["input_validation"]["errors"]


def test_require_clean_empty_input_exits_nonzero(tmp_path: Path) -> None:
    paths = _write_fixture(tmp_path, seed_rows=[])

    assert data_cli.main(_cli_args(paths, tmp_path / "report", require_clean=True)) == 1


def test_non_ascii_decimal_digits_share_one_template_signature() -> None:
    assert _digit_template("模板١") == "模板<NUM>"
    assert _digit_template("模板٢") == "模板<NUM>"


def test_current_public_split_audit_matches_committed_deterministic_summary(tmp_path: Path) -> None:
    audit = audit_split_integrity(
        seed_path=PUBLIC_SEED,
        sft_path=PUBLIC_SFT,
        dpo_path=PUBLIC_DPO,
        manifest_path=PUBLIC_MANIFEST,
        repo_root=REPO_ROOT,
    )
    paths = write_split_integrity_report(audit, tmp_path)

    assert audit["input_validation"] == {"errors": [], "valid": True}
    assert audit["input_counts"] == {
        "dpo_pairs": 2100,
        "seed_rows": 247,
        "sft_rows": 696,
        "sft_split_counts": {"dev": 207, "test": 207, "train": 282},
    }
    template = audit["diagnostics"]["digit_normalized_seed_templates"]
    assert template["affected_seed_rows"] == 140
    assert template["cross_split_signature_count"] == 8
    assert template["examples"][0]["signature"] == "填写确认边界字段<NUM>,提交前必须先问我"
    assert template["examples"][0]["row_ids"][0] == "scaled-public-sample-overlay-confirmation-boundary-001"
    assert audit["clean_gate"]["violation_counts"] == {
        "cross_split_digit_template_signatures": 8,
        "heldout_exact_input_rows_overlapping_train": 4,
        "train_rows_with_dev_test_provenance": 33,
    }
    assert audit["evidence_status"] == "DEVELOPMENT_ONLY_SPENT"
    assert paths["json"].read_bytes() == COMMITTED_SUMMARY.read_bytes()
    assert paths["markdown"].read_bytes() == COMMITTED_MARKDOWN.read_bytes()
    assert render_split_integrity_markdown(audit) == COMMITTED_MARKDOWN.read_text(encoding="utf-8")
    assert "## Overlap inventory" in render_split_integrity_markdown(audit)


def test_cli_regeneration_is_cwd_independent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    output_dir = tmp_path / "regenerated"
    monkeypatch.chdir(tmp_path)

    result = data_cli.main(
        [
            "audit-splits",
            "--seed",
            str(PUBLIC_SEED),
            "--sft",
            str(PUBLIC_SFT),
            "--dpo",
            str(PUBLIC_DPO),
            "--manifest",
            str(PUBLIC_MANIFEST),
            "--output",
            str(output_dir),
        ]
    )

    assert result == 0
    assert (output_dir / "summary.json").read_bytes() == COMMITTED_SUMMARY.read_bytes()
    assert (output_dir / "summary.md").read_bytes() == COMMITTED_MARKDOWN.read_bytes()
