import json
from pathlib import Path

from voice2task.layered_evaluation import normalize_slot_key
from voice2task.leak_scan import scan_paths
from voice2task.schemas import BrowserTaskContract, canonical_contract_json


REPO_ROOT = Path(__file__).resolve().parents[1]
POLICY_DIR = REPO_ROOT / "reports" / "public-sample" / "slot-canonicalization-policy"
HUMAN_BRIEF = REPO_ROOT / "docs" / "human-briefs" / "2026-06-18-design-slot-canonicalization-policy.html"


REQUIRED_FILES = {
    "summary.md",
    "summary.json",
    "slot-key-policy.md",
    "slot-value-policy.md",
    "normalized-command-policy.md",
    "model-target-boundary.md",
    "recommended-next-change.md",
}


def _read_policy_file(name: str) -> str:
    return (POLICY_DIR / name).read_text(encoding="utf-8")


def test_slot_key_alias_policy_is_deterministic_and_task_scoped() -> None:
    assert normalize_slot_key(" keyword ") == "query"
    assert normalize_slot_key("search-term") == "query"

    summary = json.loads(_read_policy_file("summary.json"))
    aliases = summary["slot_key_policy"]["aliases"]
    assert aliases["keyword"] == "query"
    assert aliases["search_text"] == "query"
    assert aliases["webpage"] == "url"
    assert aliases["site"] == "url"
    assert aliases["field"] == "field_name"
    assert aliases["form_field"] == "field_name"
    assert aliases["value"] == "field_value"
    assert aliases["input_value"] == "field_value"

    non_equivalent = {item["case_id"] for item in summary["slot_key_policy"]["non_equivalence_cases"]}
    assert {"product_name_vs_query", "location_vs_destination", "action_vs_reason"}.issubset(non_equivalent)
    assert "task_type_boundaries" in summary["slot_key_policy"]


def test_slot_value_policy_keeps_non_equivalent_values_unmerged() -> None:
    summary = json.loads(_read_policy_file("summary.json"))
    cases = {item["case_id"]: item for item in summary["slot_value_policy"]["non_equivalence_cases"]}

    assert cases["date_today_vs_tomorrow"]["merge_allowed"] is False
    assert cases["city_origin_vs_destination"]["merge_allowed"] is False
    assert cases["url_host_change"]["merge_allowed"] is False
    assert cases["product_name_change"]["merge_allowed"] is False

    policy_text = _read_policy_file("slot-value-policy.md")
    assert "does not affect strict exact-match scoring" in policy_text
    assert "Do not merge" in policy_text


def test_normalized_command_policy_preserves_strict_exact_boundary() -> None:
    gold = BrowserTaskContract(
        task_type="search",
        route="search_web",
        safety={"allow": True, "reason": "public_readonly"},
        confirmation_required=False,
        slots={"query": "厦门轮渡时刻表"},
        normalized_command="搜索厦门轮渡时刻表",
    )
    predicted = BrowserTaskContract(
        task_type="search",
        route="search_web",
        safety={"allow": True, "reason": "public_readonly"},
        confirmation_required=False,
        slots={"query": "厦门轮渡时刻表"},
        normalized_command="搜索厦门轮渡时间",
    )

    assert canonical_contract_json(gold) != canonical_contract_json(predicted)

    summary = json.loads(_read_policy_file("summary.json"))
    assert summary["normalized_command_policy"]["strict_exact_impact"] == "none"
    assert summary["claims"]["strict_exact_preserved"] is True
    assert summary["execution_scope"]["evaluator_metric_change"] is False
    assert "outside the core executable-contract pass condition" in _read_policy_file(
        "normalized-command-policy.md"
    )


def test_model_target_boundary_classifies_postprocessor_outputs() -> None:
    boundary = _read_policy_file("model-target-boundary.md")

    assert "model-target" in boundary
    assert "derived-field" in boundary
    assert "allowed_actions" in boundary
    assert "success_criteria" in boundary
    assert "policy_tags" in boundary
    assert "runtime_hints" in boundary
    assert "display_normalized_command" in boundary


def test_required_policy_artifacts_and_human_brief_exist() -> None:
    assert {path.name for path in POLICY_DIR.iterdir() if path.is_file()} >= REQUIRED_FILES
    assert HUMAN_BRIEF.exists()

    summary = json.loads(_read_policy_file("summary.json"))
    assert summary["evidence_kind"] == "slot_canonicalization_policy"
    assert summary["manifest_id"] == "public-sample-20260617T152259Z"
    assert summary["recommended_next_change"]["proposed_change_id"] == (
        "materialize-canonical-slot-boundary-candidates"
    )
    assert (POLICY_DIR / "recommended-next-change.md").exists()


def test_public_policy_artifacts_are_leak_scan_clean() -> None:
    result = scan_paths([POLICY_DIR, HUMAN_BRIEF])
    assert result.ok is True
    assert result.findings == []
