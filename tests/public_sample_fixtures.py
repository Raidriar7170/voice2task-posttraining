from pathlib import Path

from voice2task.dataset import build_public_sample_dataset
from voice2task.io import read_json, read_jsonl, write_json, write_jsonl

REPO_ROOT = Path(__file__).resolve().parents[1]
PUBLIC_SAMPLE_DIR = REPO_ROOT / "data" / "public-samples"
PRE_SCALED_PUBLIC_SAMPLE_MANIFEST_ID = "public-sample-20260617T045941Z"
PRE_SCALED_PUBLIC_SAMPLE_COUNTS = {"seed_rows": 102, "sft_rows": 261, "dpo_pairs": 881}
PRE_SCALED_PUBLIC_SAMPLE_SPLITS = {"train": 123, "dev": 69, "test": 69}
SCALED_PUBLIC_SAMPLE_COUNTS = {"seed_rows": 240, "sft_rows": 675, "dpo_pairs": 2046}
SCALED_PUBLIC_SAMPLE_SPLITS = {"train": 261, "dev": 207, "test": 207}


def write_pre_scaled_public_sample_fixture(tmp_path: Path) -> Path:
    """Reconstruct the formal boundary immediately before the scaled merge."""

    public_dir = tmp_path / "pre-scaled-public-samples"
    public_dir.mkdir()
    seed_rows = [
        row
        for row in read_jsonl(PUBLIC_SAMPLE_DIR / "seed_traces.jsonl")
        if (row.get("provenance") or {}).get("source_mode") != "scaled_public_sample_formal_public_seed"
    ]
    write_jsonl(public_dir / "seed_traces.jsonl", seed_rows)
    manifest = build_public_sample_dataset(seed_path=public_dir / "seed_traces.jsonl", output_dir=public_dir)
    if manifest.counts != PRE_SCALED_PUBLIC_SAMPLE_COUNTS:
        raise AssertionError(f"unexpected pre-scaled counts: {manifest.counts}")
    if manifest.split_counts != PRE_SCALED_PUBLIC_SAMPLE_SPLITS:
        raise AssertionError(f"unexpected pre-scaled splits: {manifest.split_counts}")

    manifest_path = public_dir / "manifest_public_sample.json"
    payload = read_json(manifest_path)
    payload["manifest_id"] = PRE_SCALED_PUBLIC_SAMPLE_MANIFEST_ID
    write_json(manifest_path, payload)
    return manifest_path
