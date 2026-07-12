import json
import re
from pathlib import Path

from voice2task.leak_scan import scan_paths

REPO_ROOT = Path(__file__).resolve().parents[1]
README_PATH = REPO_ROOT / "README.md"
STRICT_STRING_POLICY_PATH = (
    REPO_ROOT
    / "reports/public-sample/confirmation-rerun-normalized-command-string-mismatch-diagnosis/"
    / "strict_string_mismatch_policy.md"
)
MANIFEST_PATH = (
    REPO_ROOT
    / "reports/public-sample/confirmation-rerun-normalized-command-string-mismatch-diagnosis/"
    / "manifest.json"
)
CANONICAL_POLICY_PATH = (
    REPO_ROOT
    / "reports/public-sample/normalized-command-canonicalization-policy/"
    / "normalized_command_canonicalization_policy.md"
)
CANONICAL_POLICY_MANIFEST_PATH = (
    REPO_ROOT / "reports/public-sample/normalized-command-canonicalization-policy/manifest.json"
)
MOBILE_HUMAN_BRIEF_PATHS = (
    REPO_ROOT / "docs/human-briefs/2026-07-10-audit-contract-compiler-v2-causal-boundary.html",
    REPO_ROOT
    / "docs/human-briefs/2026-07-10-preregister-clean-matched-compiler-and-model-evidence-design.html",
    REPO_ROOT
    / "docs/human-briefs/2026-07-11-materialize-and-freeze-clean-compiler-model-evaluation-boundary-v1.html",
)


def _one_line(text: str) -> str:
    return " ".join(text.split())


def test_public_surfaces_clarify_strict_normalized_command_mismatch_policy() -> None:
    readme = README_PATH.read_text(encoding="utf-8")
    policy = STRICT_STRING_POLICY_PATH.read_text(encoding="utf-8")
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    canonical_policy = CANONICAL_POLICY_PATH.read_text(encoding="utf-8")
    canonical_policy_manifest = json.loads(CANONICAL_POLICY_MANIFEST_PATH.read_text(encoding="utf-8"))
    combined = f"{readme}\n{policy}"
    normalized_readme = _one_line(readme)

    assert "Metric Interpretation Boundaries" in readme
    assert "`contract_exact_match` is a hard full-contract exact-match metric" in normalized_readme
    assert "JSON type-strict" in normalized_readme
    assert "object key order and serialization whitespace" in normalized_readme
    assert (
        "`normalized_command` string-mismatch diagnostics are explanatory row-level evidence only"
        in normalized_readme
    )
    assert "do not relax" in normalized_readme
    assert "semantically score" in normalized_readme
    assert "re-score predictions" in normalized_readme
    assert "`搜索/查询`" in readme
    assert "`明天的天气/明天天气`" in readme

    assert "not a new metric or a rerun result" in policy
    assert "Any future semantic-equivalence or normalized-string metric" in policy
    assert "separately scoped OpenSpec change" in policy
    assert "No A100 execution was performed" in policy
    assert "No training, prediction rerun, prompt change" in policy
    assert "evaluator metric change" in policy
    assert (
        "This note does not claim checkpoint release, adapter release, held-out generalization, "
        "production readiness, public full-corpus release, model-quality improvement, or "
        "live-browser benchmark improvement."
    ) in policy

    clarification = manifest["strict_string_policy_clarification"]
    assert clarification["artifact_role"] == "later_reader_facing_interpretation_note"
    assert clarification["change_name"] == "clarify-strict-string-mismatch-policy"
    assert clarification["not_rerun_or_metric_artifact"] is True
    assert manifest["claims"]["a100_execution_performed"] is False
    assert manifest["claims"]["training_or_prediction_rerun_performed"] is False
    assert manifest["claims"]["semantic_equivalence_scoring_performed"] is False
    assert manifest["claims"]["checkpoint_release"] is False
    assert manifest["claims"]["adapter_release"] is False
    assert manifest["claims"]["held_out_generalization_claim"] is False
    assert manifest["claims"]["production_readiness_claim"] is False
    assert manifest["claims"]["public_full_corpus_release_claim"] is False
    assert manifest["claims"]["model_quality_improvement_claim"] is False
    assert manifest["claims"]["live_browser_benchmark_improvement_claim"] is False
    assert "automatically mark Chinese phrase differences" in combined
    assert "Normalized Command Target Policy" in readme
    assert "canonical Chinese intent phrases, not verbatim" in _one_line(readme)
    assert "`搜索北京明天天气`" in readme
    assert "`打开示例网站`" in readme
    assert "`填写邮箱并确认`" in readme
    assert "`拒绝代替用户付款`" in readme
    assert "not evaluator-side normalization" in _one_line(readme)
    assert "semantic-equivalence scoring" in readme
    assert "canonical Chinese intent phrases, not verbatim transcripts or ASR text" in canonical_policy
    assert "Search/information targets prefer `搜索` plus a concise query phrase" in canonical_policy
    assert "does not normalize predictions" in canonical_policy
    assert "mark `搜索/查询` or `明天的天气/明天天气` equivalent" in canonical_policy
    assert canonical_policy_manifest["artifact_role"] == "normalized_command_target_writing_policy"
    assert canonical_policy_manifest["evidence_kind"] == "local_policy_clarification"
    assert canonical_policy_manifest["claims"]["evaluator_metric_changed"] is False
    assert canonical_policy_manifest["claims"]["semantic_equivalence_scoring_performed"] is False
    assert canonical_policy_manifest["claims"]["training_performed"] is False
    assert canonical_policy_manifest["claims"]["prediction_rerun_performed"] is False
    assert canonical_policy_manifest["claims"]["a100_execution_performed"] is False
    assert scan_paths(
        [README_PATH, STRICT_STRING_POLICY_PATH, MANIFEST_PATH, CANONICAL_POLICY_PATH, CANONICAL_POLICY_MANIFEST_PATH]
    ).ok is True


def test_human_briefs_keep_long_content_within_mobile_viewport() -> None:
    for brief_path in MOBILE_HUMAN_BRIEF_PATHS:
        brief = brief_path.read_text(encoding="utf-8")
        compact_brief = "".join(brief.split())

        assert '<metaname="viewport"content="width=device-width,initial-scale=1">' in compact_brief
        assert re.search(r"body\s*\{[^}]*overflow-wrap\s*:\s*anywhere\s*;", brief)
