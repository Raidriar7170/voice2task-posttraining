from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from voice2task.dataset import build_public_sample_dataset
from voice2task.io import read_json, read_jsonl, write_json, write_jsonl
from voice2task.validation import validate_dataset_artifacts

REPO_ROOT = Path(__file__).resolve().parents[1]
FORMAL_PUBLIC_DIR = REPO_ROOT / "data/public-samples"
FORMAL_TRAIN_SHA256 = "262096626e808ac42f20900e0ff85230f43d68df58910a60a316dfc468fd779f"


def _contract(query: str) -> dict[str, object]:
    return {
        "task_type": "search",
        "route": "search_web",
        "safety": {"allow": True, "reason": "public_readonly"},
        "confirmation_required": False,
        "contract_version": "v1",
        "language": "zh-CN",
        "slots": {"query": query},
        "normalized_command": f"搜索{query}",
    }


def _write_seed(path: Path) -> None:
    rows = [
        {
            "id": "seed-train",
            "split": "train",
            "input_text": "搜索训练样本",
            "target_contract": _contract("训练样本"),
            "augmentations": ["查训练样本", "检索训练样本"],
        },
        {
            "id": "seed-dev",
            "split": "dev",
            "input_text": "搜索开发样本",
            "target_contract": _contract("开发样本"),
            "augmentations": [],
        },
    ]
    write_jsonl(path, rows)


def _built_dataset(tmp_path: Path) -> dict[str, Path]:
    seed_path = tmp_path / "seed.jsonl"
    output_dir = tmp_path / "public"
    _write_seed(seed_path)
    build_public_sample_dataset(seed_path=seed_path, output_dir=output_dir)
    paths = {
        "sft": output_dir / "sft_public_sample.jsonl",
        "dpo": output_dir / "dpo_public_sample.jsonl",
        "manifest": output_dir / "manifest_public_sample.json",
        "sft_train": output_dir / "sft_train_public_sample.jsonl",
    }
    if not paths["sft_train"].exists():
        write_jsonl(
            paths["sft_train"],
            [row for row in read_jsonl(paths["sft"]) if row["split"] == "train"],
        )
    return paths


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_binding(paths: dict[str, Path], *, relative_path: str | None = None) -> dict[str, Any]:
    manifest = read_json(paths["manifest"])
    manifest["files"]["sft_train"] = relative_path or paths["sft_train"].name
    train_rows = read_jsonl(paths["sft_train"])
    manifest["source_summary"]["sft_train_artifact"] = {
        "sha256": _sha256(paths["sft_train"]),
        "row_count": len(train_rows),
        "split": "train",
        "canonical_jsonl": True,
    }
    write_json(paths["manifest"], manifest)
    return manifest


def _validate(paths: dict[str, Path], *, public: bool = False):  # type: ignore[no-untyped-def]
    return validate_dataset_artifacts(
        sft_path=paths["sft"],
        dpo_path=paths["dpo"],
        manifest_path=paths["manifest"],
        public=public,
    )


def _refresh_binding(paths: dict[str, Path], *, row_count: int | None = None) -> None:
    manifest = read_json(paths["manifest"])
    binding = manifest["source_summary"]["sft_train_artifact"]
    binding["sha256"] = _sha256(paths["sft_train"])
    if row_count is not None:
        binding["row_count"] = row_count
    write_json(paths["manifest"], manifest)


def test_train_only_validation_accepts_exact_bound_ordered_subsequence(tmp_path: Path) -> None:
    paths = _built_dataset(tmp_path)
    _write_binding(paths)

    result = _validate(paths)

    assert result.ok is True
    assert result.failures == []
    assert result.counts["sft_train_rows"] == 3


@pytest.mark.parametrize("public", [False, True], ids=["local", "public"])
@pytest.mark.parametrize("binding_half", ["path", "metadata"])
def test_train_only_validation_rejects_partial_binding(
    tmp_path: Path,
    binding_half: str,
    public: bool,
) -> None:
    paths = _built_dataset(tmp_path)
    manifest = read_json(paths["manifest"])
    if binding_half == "path":
        manifest["source_summary"].pop("sft_train_artifact")
        manifest["files"]["sft_train"] = paths["sft_train"].name
    else:
        manifest["files"].pop("sft_train")
        manifest["source_summary"]["sft_train_artifact"] = {
            "sha256": _sha256(paths["sft_train"]),
            "row_count": 3,
            "split": "train",
            "canonical_jsonl": True,
        }
    write_json(paths["manifest"], manifest)

    result = _validate(paths, public=public)

    assert result.ok is False
    assert any(failure["category"] == "train_only_artifact_invalid" for failure in result.failures)


@pytest.mark.parametrize(
    "unsafe_path",
    [
        pytest.param("/data/sft_train.jsonl", id="absolute"),
        pytest.param("../outside.jsonl", id="traversal"),
        pytest.param("nested/../../outside.jsonl", id="outside"),
        pytest.param(r"nested\sft_train.jsonl", id="backslash"),
    ],
)
def test_train_only_validation_rejects_unsafe_paths(tmp_path: Path, unsafe_path: str) -> None:
    paths = _built_dataset(tmp_path)
    _write_binding(paths, relative_path=unsafe_path)

    result = _validate(paths)

    assert result.ok is False
    assert any(failure["category"] == "train_only_artifact_invalid" for failure in result.failures)


def test_train_only_validation_rejects_symlink_path_component(tmp_path: Path) -> None:
    paths = _built_dataset(tmp_path)
    symlink_path = paths["manifest"].parent / "linked_train.jsonl"
    symlink_path.symlink_to(paths["sft_train"])
    _write_binding(paths, relative_path=symlink_path.name)

    result = _validate(paths)

    assert result.ok is False
    assert any(failure["category"] == "train_only_artifact_invalid" for failure in result.failures)


@pytest.mark.parametrize("invalid_kind", ["missing", "hash_drift", "noncanonical"])
def test_train_only_validation_rejects_file_identity_drift(tmp_path: Path, invalid_kind: str) -> None:
    paths = _built_dataset(tmp_path)
    _write_binding(paths)
    if invalid_kind == "missing":
        paths["sft_train"].unlink()
    elif invalid_kind == "hash_drift":
        manifest = read_json(paths["manifest"])
        manifest["source_summary"]["sft_train_artifact"]["sha256"] = "0" * 64
        write_json(paths["manifest"], manifest)
    else:
        rows = read_jsonl(paths["sft_train"])
        paths["sft_train"].write_text(
            "\n".join(json.dumps(row, ensure_ascii=False) for row in rows),
            encoding="utf-8",
        )
        _refresh_binding(paths)

    result = _validate(paths)

    assert result.ok is False
    assert any(failure["category"] == "train_only_artifact_invalid" for failure in result.failures)


@pytest.mark.parametrize(
    "invalid_kind",
    [
        "non_train",
        "duplicate_id",
        "blank_id",
        "count_drift",
        "reorder",
        "row_drift",
        "provenance_drift",
    ],
)
def test_train_only_validation_rejects_content_drift(tmp_path: Path, invalid_kind: str) -> None:
    paths = _built_dataset(tmp_path)
    _write_binding(paths)
    rows = read_jsonl(paths["sft_train"])
    expected_count = len(rows)
    if invalid_kind == "non_train":
        rows[0]["split"] = "dev"
    elif invalid_kind == "duplicate_id":
        rows[1]["id"] = rows[0]["id"]
    elif invalid_kind == "blank_id":
        rows[0]["id"] = " "
    elif invalid_kind == "count_drift":
        pass
    elif invalid_kind == "reorder":
        rows = list(reversed(rows))
    elif invalid_kind == "row_drift":
        rows[0]["input_text"] = "漂移后的训练样本"
    else:
        rows[0]["provenance"] = copy.deepcopy(rows[0]["provenance"])
        rows[0]["provenance"]["source_id"] = "drifted-source"
    write_jsonl(paths["sft_train"], rows)
    _refresh_binding(
        paths,
        row_count=expected_count + 1 if invalid_kind == "count_drift" else expected_count,
    )

    result = _validate(paths)

    assert result.ok is False
    assert any(failure["category"] == "train_only_artifact_invalid" for failure in result.failures)


def test_train_only_validation_keeps_unbound_historical_manifest_compatible(tmp_path: Path) -> None:
    paths = _built_dataset(tmp_path)
    manifest = read_json(paths["manifest"])
    manifest["files"].pop("sft_train", None)
    manifest["source_summary"].pop("sft_train_artifact", None)
    write_json(paths["manifest"], manifest)

    result = _validate(paths)

    assert result.ok is True
    assert result.counts["sft_train_rows"] == 0


def test_train_only_validation_requires_complete_binding_for_public_dataset(tmp_path: Path) -> None:
    paths = _built_dataset(tmp_path)
    manifest = read_json(paths["manifest"])
    manifest["files"].pop("sft_train")
    manifest["source_summary"].pop("sft_train_artifact")
    write_json(paths["manifest"], manifest)

    result = _validate(paths, public=True)

    assert result.ok is False
    assert any(failure["category"] == "train_only_artifact_invalid" for failure in result.failures)


def test_formal_train_only_artifact_is_exact_bound_canonical_subsequence() -> None:
    manifest_path = FORMAL_PUBLIC_DIR / "manifest_public_sample.json"
    manifest = read_json(manifest_path)
    assert manifest["files"]["sft_train"] == "data/public-samples/sft_train_public_sample.jsonl"
    train_path = REPO_ROOT / manifest["files"]["sft_train"]
    payload = train_path.read_bytes()
    train_rows = read_jsonl(train_path)
    mixed_rows = read_jsonl(FORMAL_PUBLIC_DIR / "sft_public_sample.jsonl")
    binding = manifest["source_summary"]["sft_train_artifact"]
    canonical = "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in train_rows
    ).encode("utf-8")

    assert manifest["manifest_id"] == "public-sample-20260619T090925Z"
    assert manifest["generated_at"] == "2026-06-19T09:09:25.032006+00:00"
    assert manifest["counts"] == {"dpo_pairs": 2100, "seed_rows": 247, "sft_rows": 696}
    assert manifest["split_counts"] == {"dev": 207, "test": 207, "train": 282}
    assert len(train_rows) == 282
    assert all(row["split"] == "train" for row in train_rows)
    assert all(isinstance(row["id"], str) and row["id"].strip() for row in train_rows)
    assert len({row["id"] for row in train_rows}) == 282
    assert train_rows == [row for row in mixed_rows if row["split"] == "train"]
    assert payload == canonical
    assert hashlib.sha256(payload).hexdigest() == FORMAL_TRAIN_SHA256
    assert binding == {
        "canonical_jsonl": True,
        "row_count": 282,
        "sha256": FORMAL_TRAIN_SHA256,
        "split": "train",
    }

    result = validate_dataset_artifacts(
        sft_path=FORMAL_PUBLIC_DIR / "sft_public_sample.jsonl",
        dpo_path=FORMAL_PUBLIC_DIR / "dpo_public_sample.jsonl",
        manifest_path=manifest_path,
        public=True,
    )
    assert result.ok is True
    assert result.failures == []
    assert result.counts == {"sft_rows": 696, "sft_train_rows": 282, "dpo_pairs": 2100}
