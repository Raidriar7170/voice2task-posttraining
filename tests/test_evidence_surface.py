from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from voice2task.leak_scan import scan_paths

REPO_ROOT = Path(__file__).resolve().parents[1]
CHECKER = REPO_ROOT / "scripts/check_current_truth_surface.py"
INDEX_JSON = REPO_ROOT / "reports/public-sample/evidence-index.json"
INDEX_MD = REPO_ROOT / "reports/public-sample/EVIDENCE_INDEX.md"
README = REPO_ROOT / "README.md"
README_EN = REPO_ROOT / "README_en.md"
CONTEXT = REPO_ROOT / "CONTEXT.md"


def _one_line(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").split())


def test_current_truth_surface_checker_passes() -> None:
    result = subprocess.run(
        [sys.executable, str(CHECKER)],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr


def test_evidence_index_classifies_current_superseded_blocked_and_raw_inputs() -> None:
    items = json.loads(INDEX_JSON.read_text(encoding="utf-8"))["items"]
    by_id = {item["id"]: item for item in items}

    assert by_id["contract-v2-projection-rerun"]["status"] == "CURRENT"
    assert by_id["step-matched-canonical-slot-ablation"]["status"] == "CURRENT"
    assert by_id["contract-v2-projection-blocked"]["status"] == "BLOCKED"
    assert by_id["contract-v2-projection-blocked"]["superseded_by"] == "contract-v2-projection-rerun"
    assert by_id["step-matched-projection-raw-inputs"]["status"] == "RAW_INPUT"
    assert by_id["canonical-slot-paired-sft-ablation"]["status"] == "SUPERSEDED"
    assert by_id["canonical-slot-paired-sft-ablation"]["superseded_by"] == "step-matched-canonical-slot-ablation"
    assert by_id["scaled-clarify-slot-boundary-candidate-design"]["status"] == "DESIGN_ONLY"
    assert all((REPO_ROOT / item["path"]).exists() for item in items)


def test_public_current_docs_are_compact_and_no_overclaim() -> None:
    readme = _one_line(README)
    readme_en = _one_line(README_EN)
    context = _one_line(CONTEXT)
    combined = f"{readme} {readme_en} {context}"

    required_fragments = [
        "public-sample-20260619T090925Z",
        "247 seeds",
        "696 SFT rows",
        "2100 DPO pairs",
        "PARTIAL_SCHEMA_BENEFIT",
        "14.65%",
        "metadata-only",
        "0%",
        "99.88%",
        "1.0",
        "68.79%",
        "decide-contract-v2-core-implementation-scope",
        "strict exact remains canonical",
    ]
    for fragment in required_fragments:
        assert fragment in combined

    forbidden_current_claims = [
        "model improvement",
        "executable quality improvement",
        "production readiness",
        "safety readiness",
        "held-out recovery",
        "live-browser benchmark gain",
        "checkpoint release",
        "adapter release",
        "DPO justification",
        "another canonical-candidate loop",
    ]
    for claim in forbidden_current_claims:
        assert f"cannot claim {claim}" in combined or f"no {claim}" in combined

    assert "Evidence Index" in INDEX_MD.read_text(encoding="utf-8")
    assert "reports/public-sample/EVIDENCE_INDEX.md" in context
    assert scan_paths([README, README_EN, CONTEXT, INDEX_JSON, INDEX_MD]).ok is True
