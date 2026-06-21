#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SUMMARY_PATH = REPO_ROOT / "reports/public-sample/contract-v2-projection/rerun-with-recovered-inputs/summary.json"
MANIFEST_PATH = REPO_ROOT / "data/public-samples/manifest_public_sample.json"
INDEX_JSON_PATH = REPO_ROOT / "reports/public-sample/evidence-index.json"
INDEX_MD_PATH = REPO_ROOT / "reports/public-sample/EVIDENCE_INDEX.md"
README_PATH = REPO_ROOT / "README.md"
README_EN_PATH = REPO_ROOT / "README_en.md"
CONTEXT_PATH = REPO_ROOT / "CONTEXT.md"

ALLOWED_STATUSES = {
    "CURRENT",
    "HISTORICAL",
    "SUPERSEDED",
    "BLOCKED",
    "DESIGN_ONLY",
    "RAW_INPUT",
    "ARCHIVED",
}

EXPECTED_CANNOT_CLAIM = {
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
}


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _one_line(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").split())


def _format_percent(value: float) -> str:
    if value == 0:
        return "0%"
    return f"{value * 100:.2f}%"


def _markdown_links(text: str) -> list[str]:
    return [target.strip() for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", text)]


def _is_repo_relative_link(target: str) -> bool:
    if target.startswith(("http://", "https://", "mailto:", "#")):
        return False
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1]
    return not target.startswith("/")


def _path_from_markdown_link(target: str) -> Path:
    clean = target.strip()
    if clean.startswith("<") and clean.endswith(">"):
        clean = clean[1:-1]
    clean = clean.split("#", 1)[0]
    return REPO_ROOT / clean


def _active_openspec_count() -> int:
    result = subprocess.run(
        ["openspec", "list", "--json"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr or result.stdout)
    output = result.stdout
    json_start = output.find("{")
    if json_start < 0:
        raise RuntimeError(f"openspec list did not return JSON: {output}")
    payload = json.loads(output[json_start:])
    return len(payload.get("changes", []))


def _check_doc_links(errors: list[str], path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    for target in _markdown_links(text):
        if not _is_repo_relative_link(target):
            continue
        linked = _path_from_markdown_link(target)
        if not linked.exists():
            errors.append(f"{path.relative_to(REPO_ROOT)} link target missing: {target}")


def _check_index(errors: list[str]) -> list[dict[str, Any]]:
    payload = _load_json(INDEX_JSON_PATH)
    statuses = set(payload.get("allowed_statuses", []))
    if statuses != ALLOWED_STATUSES:
        errors.append(f"evidence-index allowed_statuses mismatch: {sorted(statuses)}")

    items = payload.get("items", [])
    if not isinstance(items, list) or not items:
        errors.append("evidence-index items must be a non-empty list")
        return []

    seen_current_ids: set[str] = set()
    seen_superseded_ids: set[str] = set()
    for item in items:
        item_id = str(item.get("id", "<missing-id>"))
        status = item.get("status")
        path = item.get("path")
        summary = str(item.get("summary", ""))
        conclusion = str(item.get("conclusion", ""))
        text = f"{summary} {conclusion}".lower()

        if status not in ALLOWED_STATUSES:
            errors.append(f"{item_id}: invalid status {status!r}")
        if not path or not isinstance(path, str):
            errors.append(f"{item_id}: missing repo-relative path")
        elif Path(path).is_absolute():
            errors.append(f"{item_id}: path must be repo-relative")
        elif not (REPO_ROOT / path).exists():
            errors.append(f"{item_id}: path does not exist: {path}")

        if status == "CURRENT":
            seen_current_ids.add(item_id)
            if "blocked" in str(path).lower() or "blocked-only" in text:
                errors.append(f"{item_id}: CURRENT item points to blocked-only evidence")
            if item.get("current_claim_allowed") is not True:
                errors.append(f"{item_id}: CURRENT item must set current_claim_allowed=true")

        if status == "SUPERSEDED":
            seen_superseded_ids.add(item_id)
            if not item.get("superseded_by") and not item.get("supersession_explanation"):
                errors.append(f"{item_id}: SUPERSEDED item needs superseded_by or supersession_explanation")

        if status == "BLOCKED":
            if item.get("current_claim_allowed") is not False:
                errors.append(f"{item_id}: BLOCKED item must set current_claim_allowed=false")
            mentions_current_metrics = "current model metric" in text or "current model metrics" in text
            if mentions_current_metrics and "no current model metric" not in text:
                errors.append(f"{item_id}: BLOCKED item appears to declare current model metrics")

        if status == "DESIGN_ONLY":
            if item.get("current_claim_allowed") is not False:
                errors.append(f"{item_id}: DESIGN_ONLY item must set current_claim_allowed=false")
            if "model improvement claim" not in text and "model improvement" in text:
                errors.append(f"{item_id}: DESIGN_ONLY item appears to declare model improvement")

    overlap = seen_current_ids.intersection(seen_superseded_ids)
    if overlap:
        errors.append(f"items cannot be both CURRENT and SUPERSEDED: {sorted(overlap)}")
    return items


def _check_current_docs(errors: list[str]) -> None:
    summary = _load_json(SUMMARY_PATH)
    manifest = _load_json(MANIFEST_PATH)
    required_questions = summary["required_questions"]
    contribution = summary["failure_contribution_overall"]
    renderer = summary["renderer"]

    docs = {
        "README.md": _one_line(README_PATH),
        "README_en.md": _one_line(README_EN_PATH),
        "CONTEXT.md": _one_line(CONTEXT_PATH),
    }
    combined = " ".join(docs.values())

    counts = manifest["counts"]
    split_counts = manifest["split_counts"]
    required_fragments = {
        manifest["manifest_id"],
        f"{counts['seed_rows']} seeds",
        f"{counts['sft_rows']} SFT rows",
        f"{counts['dpo_pairs']} DPO pairs",
        f"train/dev/test = {split_counts['train']}/{split_counts['dev']}/{split_counts['test']}",
        summary["decision_label"],
        _format_percent(required_questions["normalized_command_only_share"]),
        _format_percent(required_questions["metadata_only_share"]),
        _format_percent(contribution["category_proportions"]["CORE_SLOT_FAILURE"]),
        _format_percent(renderer["supported_rate"]),
        str(required_questions["deterministic_roundtrip_rate"]),
        required_questions["recommended_next_change"],
        "strict exact remains canonical",
        "reports/public-sample/EVIDENCE_INDEX.md",
    }
    for fragment in sorted(required_fragments):
        if fragment not in combined:
            errors.append(f"current docs missing required fragment: {fragment}")

    expected_improvements = {
        "+0.0193",
        "+0.0386",
        "+0.0290",
        "+0.0242",
    }
    for fragment in expected_improvements:
        if fragment not in combined:
            errors.append(f"current docs missing V2 core exact delta: {fragment}")

    for claim in EXPECTED_CANNOT_CLAIM:
        if f"cannot claim {claim}" not in combined and f"no {claim}" not in combined:
            errors.append(f"current docs missing cannot-claim boundary: {claim}")

    for doc_name, text in docs.items():
        if "PARTIAL_SCHEMA_BENEFIT" not in text:
            errors.append(f"{doc_name} missing Contract V2 projection decision")
        if "14.65%" not in text:
            errors.append(f"{doc_name} missing derived-field-only share")
        if "68.79%" not in text:
            errors.append(f"{doc_name} missing slot bottleneck share")


def validate() -> list[str]:
    errors: list[str] = []
    required_paths = [
        SUMMARY_PATH,
        MANIFEST_PATH,
        INDEX_JSON_PATH,
        INDEX_MD_PATH,
        README_PATH,
        README_EN_PATH,
        CONTEXT_PATH,
    ]
    for required_path in required_paths:
        if not required_path.exists():
            errors.append(f"missing required path: {required_path.relative_to(REPO_ROOT)}")
    if errors:
        return errors

    _check_index(errors)
    _check_current_docs(errors)
    _check_doc_links(errors, README_PATH)
    _check_doc_links(errors, README_EN_PATH)
    if "reports/public-sample/EVIDENCE_INDEX.md" not in CONTEXT_PATH.read_text(encoding="utf-8"):
        errors.append("CONTEXT.md must link to reports/public-sample/EVIDENCE_INDEX.md")

    try:
        active_count = _active_openspec_count()
    except RuntimeError as exc:
        errors.append(f"openspec active count unavailable: {exc}")
    else:
        if active_count != 0:
            errors.append(f"active OpenSpec change count must be 0 after cleanup archive, got {active_count}")

    try:
        sys.path.insert(0, str(REPO_ROOT / "src"))
        from voice2task.leak_scan import scan_paths

        scan_result = scan_paths([README_PATH, README_EN_PATH, CONTEXT_PATH, INDEX_MD_PATH, INDEX_JSON_PATH])
    except Exception as exc:  # pragma: no cover - surfaced as validation failure
        errors.append(f"public leak scan failed to run: {exc}")
    else:
        if not scan_result.ok:
            details = "; ".join(
                f"{finding.path}:{finding.line}:{finding.category}" for finding in scan_result.findings[:10]
            )
            errors.append(f"public leak scan failed: {details}")

    return errors


def main() -> int:
    errors = validate()
    if errors:
        print("current truth surface check failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("current truth surface check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
