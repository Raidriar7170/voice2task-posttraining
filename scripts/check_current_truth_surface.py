#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import math
import re
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, cast
from urllib.parse import urlsplit

REPO_ROOT = Path(__file__).resolve().parents[1]
SUMMARY_PATH = REPO_ROOT / "reports/public-sample/contract-v2-projection/rerun-with-recovered-inputs/summary.json"
INTERNAL_SUMMARY_PATH = REPO_ROOT / "reports/public-sample/internal-contract-v2-core/summary.json"
MANIFEST_PATH = REPO_ROOT / "data/public-samples/manifest_public_sample.json"
INDEX_JSON_PATH = REPO_ROOT / "reports/public-sample/evidence-index.json"
INDEX_MD_PATH = REPO_ROOT / "reports/public-sample/EVIDENCE_INDEX.md"
README_PATH = REPO_ROOT / "README.md"
README_EN_PATH = REPO_ROOT / "README_en.md"
CONTEXT_PATH = REPO_ROOT / "CONTEXT.md"
CURRENT_STATUS_PATH = REPO_ROOT / "docs/current-status.md"
LOCKBOX_MANIFEST_PATH = REPO_ROOT / "data/lockbox/lockbox-v1.manifest.json"
LOCKBOX_RUN_CARD_PATH = REPO_ROOT / "reports/lockbox-v1/final-evaluation/run-card.json"
LOCKBOX_BASE_METRICS_PATH = REPO_ROOT / "reports/lockbox-v1/final-evaluation/base/metrics.json"
LOCKBOX_FINAL_METRICS_PATH = REPO_ROOT / "reports/lockbox-v1/final-evaluation/final-sft/metrics.json"
LOCKBOX_COMPARISON_PATH = REPO_ROOT / "reports/lockbox-v1/final-evaluation/comparison.json"
SPLIT_AUDIT_JSON_PATH = REPO_ROOT / "reports/public-sample/split-integrity-audit/summary.json"
SPLIT_AUDIT_MD_PATH = REPO_ROOT / "reports/public-sample/split-integrity-audit/summary.md"
PUBLIC_SEED_PATH = REPO_ROOT / "data/public-samples/seed_traces.jsonl"
PUBLIC_SFT_PATH = REPO_ROOT / "data/public-samples/sft_public_sample.jsonl"
PUBLIC_DPO_PATH = REPO_ROOT / "data/public-samples/dpo_public_sample.jsonl"
CLEAN_BOUNDARY_REPORT_DIR = (
    REPO_ROOT / "reports/public-sample/clean-compiler-model-evaluation-boundary-v1"
)
CLEAN_BOUNDARY_SUMMARY_PATH = CLEAN_BOUNDARY_REPORT_DIR / "summary.json"
CLEAN_BOUNDARY_PUBLIC_FILES = {
    "summary.json",
    "summary.md",
    "protocol-manifest.json",
    "population-seal-attestation.json",
    "lineage-attestation.json",
}
ACTIVE_CLEAN_BOUNDARY_CHANGE = "materialize-and-freeze-clean-compiler-model-evaluation-boundary-v1"
REVIEW_PACK_SUMMARY_PATH = (
    REPO_ROOT
    / "reports/public-sample/clean-evaluation-acquisition-and-binding-review-pack-v1/summary.json"
)
REVIEW_PACK_PUBLIC_PARENT_PATH = REVIEW_PACK_SUMMARY_PATH.parent.parent
REVIEW_PACK_RECOVERY_PREFIX = ".review-pack-recovery-"
REVIEW_PACK_ID = "clean-evaluation-acquisition-and-binding-review-pack-v1"
REVIEW_PACK_PHASE = "prepare-clean-evaluation-acquisition-and-binding-review-pack-v1"
RETIRED_REVIEW_PACK_FLAG_ERROR = (
    "--allow-active-review-pack is retired because "
    f"{REVIEW_PACK_PHASE} is archived"
)
REVIEW_PACK_HUMAN_BRIEF_PATH = (
    REPO_ROOT
    / "docs/human-briefs/2026-07-11-prepare-clean-evaluation-acquisition-and-binding-review-pack-v1.html"
)
REVIEW_PACK_HUMAN_BRIEF_STATUS = (
    "ARCHIVED · REVIEW PACK READY ONLY · EXECUTION BLOCKED"
)
REVIEW_PACK_HUMAN_BRIEF_H2 = (
    "当前状态",
    "本阶段改变了什么",
    "信任与权限边界",
    "权威来源与关键产物",
    "验证证据",
    "剩余风险与禁止过度声明",
    "建议下一步",
)
REVIEW_PACK_HUMAN_BRIEF_TRUTH = {
    "change_status=ARCHIVED",
    "evidence_status=DESIGN_ONLY",
    "phase_status=PREPARATION_ONLY",
    "decision=ACQUISITION_AND_BINDING_REVIEW_PACK_READY_EXECUTION_BLOCKED",
    "review_pack_status=READY_FOR_EXTERNAL_COMPLETION",
    "candidate_pack_status=INCOMPLETE",
    "binding_inventory_count=29",
    "supplied_binding_count=0",
    "authoritatively_bound_binding_count=0",
    "acquisition_source_status=UNAVAILABLE",
    "current_readiness_state=DESIGN_ONLY",
    "execution_bindings_status=INCOMPLETE",
    "protocol_freeze_status=NOT_FROZEN",
    "clean_population_status=NOT_MATERIALIZED",
    "boundary_integrity_status=NOT_CREATED",
    "human_acceptance_status=NOT_RECORDED",
    "freeze_authorized=false",
    "next_phase_eligible=false",
    "execution_readiness=false",
    "seven_member_bundle=true",
    "manifest_hashed_payload_count=6",
    "manifest_self_hash=false",
    "human_brief_role=NAVIGATION_SUMMARY_ONLY",
    "authoritative_sources=OPENSPEC_RAW_SUMMARY_MANIFEST_TESTS_VALIDATION",
    "browser_viewport_qa_status=NOT_RUN_FILE_URL_BLOCKED",
    "trusted_exclusive_cooperative_same_euid=true",
    "malicious_same_euid_replacement=ACCOUNT_PROCESS_BOUNDARY_COMPROMISE",
    "no_mutation_exclusion=DESCRIPTOR_READ_ACCESS_TIME_ONLY",
    "recovery_automatic_gc=false",
    "template_lint_conforms=false",
    "future_lint_exit_0=CONFORMANCE_ONLY",
    "s0_evidence_status=BLOCKED",
    "s0_decision=CLEAN_EVALUATION_BOUNDARY_MATERIALIZATION_BLOCKED",
    "s0_superseded_by=null",
    "task_4_1_status=COMPLETE",
    "task_4_2_status=COMPLETE",
    "task_4_3_status=COMPLETE_WITH_EXPLICIT_LIFECYCLE_AND_BASELINE_LIMITATIONS",
    "task_4_4_status=COMPLETE_AFTER_3_MUST_FIXES_RESOLVED_AND_TWO_INDEPENDENT_REVIEWS_PASS",
    "openspec_progress=20/20",
    "full_pytest_status=1260_PASSED",
    "full_pytest_failure_scope=NONE",
    "full_pytest_failure_reason=NONE",
    "challenge_hash_policy_rows_template_disjoint=PASS",
    "default_zero_active_truth_status=PASS",
    "active_openspec_changes=0",
    (
        "archive_path=openspec/changes/archive/"
        "2026-07-12-prepare-clean-evaluation-acquisition-and-binding-review-pack-v1"
    ),
    "main_spec_sync=PASS_7_REQUIREMENTS_29_SCENARIOS",
    "task_4_4_must_fixes_resolved=3/3",
    "task_4_4_spec_truth_reviewer=PASS",
    "task_4_4_code_security_reviewer=PASS",
    "final_independent_review_status=PASS_TASK_4_4",
    "task_4_5_archive_status=COMPLETE",
    "task_4_1_group_a_tests=39 passed",
    "task_4_1_group_b_tests=25 passed",
    "cli_lint_tests=193 passed",
    "evidence_surface_tests=55 passed",
    "review_boundary_tests=434 passed",
    "boundary_review_evidence_tests=489 passed",
    "recovery_gate_fail_closed=PASS",
    "task_4_1_reviewer_focused_tests=8 passed",
    "task_4_1_independent_reviewer=PASS",
    "task_4_2_temp_build=PASS",
    "public_build_seed_rows=247",
    "public_build_sft_rows=696",
    "public_build_dpo_pairs=2100",
    "public_validate=PASS_0_FAILURES",
    "public_dpo_check_pairs=2100",
    "task_4_2_focused_tests=88 passed",
    "protected_hashes_unchanged=15/15",
    "task_4_2_temp_output=CLEANED",
    "task_4_2_independent_reviewer=PASS",
    "checker_status=PASS",
    "ruff_status=PASS",
    "focused_mypy_status=PASS_4_FILES_0_ISSUES",
    "recorded_full_mypy_baseline=39_ERRORS_IN_5_FILES",
    "full_mypy_rerun=39_ERRORS_IN_5_FILES_CHECKED_31_SOURCE_FILES",
    "full_mypy_status=RECORDED_BASELINE_PRESERVED",
    "full_mypy_source_coverage=31_CURRENT_VS_28_PRIOR_RECORDED",
    "task_4_3_independent_gate_reviewer=PASS",
    "task_4_4_baseexception_tests=7 passed",
    "task_4_4_private_reader_tests=6 passed",
    "task_4_4_adapter_cli_tests=7 passed",
    "task_4_4_clean_chain_tests=4 passed",
    "task_4_4_targeted_tests=24 passed",
    "openspec_strict=15/15",
    "leak_link_diff_status=PASS",
    "publication_initial_create=PASS",
    "publication_second_exact_noop=PASS",
    "recovery_siblings=0",
    "s0_five_hashes=UNCHANGED",
    "canonical_private_root=ABSENT_IGNORED_UNTRACKED",
    "prior_independent_reviews=PASS",
    "task_4_1_scope=PUBLICATION_RECOVERY_NO_REPLACE_EXACT_NOOP_CLI_LINT_CURRENT_LEGACY_ACCEPTANCE",
    "task_4_2_scope=TEMP_BUILD_PUBLIC_VALIDATE_PUBLIC_DPO_CHECK_FOCUSED_DATASET_TESTS_PROTECTED_HASH_COMPARISON",
    "task_4_3_scope=FULL_PYTEST_RUFF_FOCUSED_MYPY_RECORDED_FULL_MYPY_BASELINE_OPENSPEC_TRUTH_LEAK_LINK_JSON_MANIFEST_PRIVATE_DIFF",
    "task_4_4_scope=FINAL_INDEPENDENT_SPEC_SECURITY_REVIEW",
    "task_4_5_scope=ARCHIVE_COMPLETE_POST_ARCHIVE_GATES",
}
REVIEW_PACK_HUMAN_BRIEF_FORBIDDEN = {
    "ACTIVE APPLY",
    "change_status=APPLYING",
    "openspec_progress=19/20",
    "task_4_5_archive_status=SEPARATE_AUTHORIZATION_REQUIRED",
    "task_4_5_scope=ARCHIVE_SEPARATE_AUTHORIZATION_ONLY",
    "full_pytest_status=1257_PASSED_3_EXPECTED_ACTIVE_CHANGE_ARCHIVE_GUARD_FAILURES",
    "full_pytest_failure_scope=TEST_RECOVERED_ADAPTER_CHALLENGE_EVALUATION_ONLY",
    "full_pytest_failure_reason=ACTIVE_CHANGE_CONFLICTING_ACTIVE_CHANGES",
    "default_zero_active_truth_status=EXPECTED_RED_UNTIL_SEPARATELY_AUTHORIZED_ARCHIVE",
    "HUMAN_ACCEPTANCE_RECORDED",
    "READY_FOR_FREEZE",
    "EXPERIMENT_BINDINGS_COMPLETE",
    "PROTOCOL_FROZEN",
    "POPULATION_MATERIALIZED_AND_SEALED",
    "freeze_authorized=true",
    "next_phase_eligible=true",
    "execution_readiness=true",
    "viewport_qa_status=PASS",
    "task_4_1_status=PENDING",
    "task_4_1_independent_reviewer=PENDING",
    "task_4_2_status=PENDING",
    "task_4_2_temp_build=FAIL",
    "task_4_2_temp_output=PRESENT",
    "task_4_2_independent_reviewer=PENDING",
    "task_4_3_status=PENDING",
    "task_4_4_status=PENDING",
    "final_independent_review_status=PENDING_TASK_4_4",
    "openspec_progress=18/20",
    "full_pytest_status=PENDING_TASK_4_3",
    "full_pytest_status=1241_PASSED_3_EXPECTED_ACTIVE_CHANGE_ARCHIVE_GUARD_FAILURES",
    "full_pytest_status=PASS",
    "full_mypy_rerun=PENDING_TASK_4_3",
    "full_mypy_status=PASS",
    "protected_hashes_unchanged=14/15",
    "recovery_gate_fail_closed=FAIL",
    "evidence_surface_tests=48 passed",
    "review_boundary_tests=388 passed",
}
REVIEW_PACK_HUMAN_BRIEF_REQUIRED_LINKS = {
    "../../openspec/changes/archive/2026-07-12-prepare-clean-evaluation-acquisition-and-binding-review-pack-v1/proposal.md",
    "../../openspec/changes/archive/2026-07-12-prepare-clean-evaluation-acquisition-and-binding-review-pack-v1/design.md",
    "../../openspec/changes/archive/2026-07-12-prepare-clean-evaluation-acquisition-and-binding-review-pack-v1/specs/clean-evaluation-acquisition-and-binding-review-pack/spec.md",
    "../../openspec/changes/archive/2026-07-12-prepare-clean-evaluation-acquisition-and-binding-review-pack-v1/tasks.md",
    "../../openspec/specs/clean-evaluation-acquisition-and-binding-review-pack/spec.md",
    "../../reports/public-sample/clean-evaluation-acquisition-and-binding-review-pack-v1/summary.json",
    "../../reports/public-sample/clean-evaluation-acquisition-and-binding-review-pack-v1/summary.md",
    "../../reports/public-sample/clean-evaluation-acquisition-and-binding-review-pack-v1/manifest.json",
    "../../reports/public-sample/clean-evaluation-acquisition-and-binding-review-pack-v1/binding-catalog.json",
    "../../reports/public-sample/clean-evaluation-acquisition-and-binding-review-pack-v1/review-pack.schema.json",
    "../../reports/public-sample/clean-evaluation-acquisition-and-binding-review-pack-v1/review-pack.template.json",
    "../../reports/public-sample/clean-evaluation-acquisition-and-binding-review-pack-v1/review-checklist.md",
    "../../reports/public-sample/clean-compiler-model-evaluation-boundary-v1/summary.json",
    "../../src/voice2task/clean_evaluation_review_pack.py",
    "../../src/voice2task/clean_evaluation_boundary.py",
    "../../src/voice2task/cli/data.py",
    "../../tests/test_clean_evaluation_review_pack.py",
    "../../tests/test_clean_evaluation_boundary.py",
    "../../tests/test_evidence_surface.py",
    "../../reports/public-sample/EVIDENCE_INDEX.md",
    "../current-status.md",
    "../../CONTEXT.md",
    "../../scripts/check_current_truth_surface.py",
}
REVIEW_PACK_HUMAN_BRIEF_FORBIDDEN_ELEMENTS = {
    "script",
    "iframe",
    "object",
    "embed",
    "img",
    "picture",
    "source",
    "audio",
    "video",
    "base",
    "form",
    "link",
}
REVIEW_PACK_HUMAN_BRIEF_URL_RESOURCE_ATTRIBUTES = {
    "src",
    "srcset",
    "action",
    "formaction",
    "poster",
    "data",
}
REVIEW_PACK_HUMAN_BRIEF_COLORS = {
    "#171717",
    "#404040",
    "#a16207",
    "#ffffff",
    "#e8ecf0",
}
REVIEW_PACK_HUMAN_BRIEF_REQUIRED_CSS = {
    "max-width: 760px": "bounded width",
    "overflow-wrap: anywhere": "overflow wrapping",
    ":focus-visible": "focus-visible",
    "text-decoration: underline": "underlined links",
    "@media (max-width: 600px)": "mobile media query",
    "@media print": "print media query",
    "@media (prefers-reduced-motion: reduce)": "reduced-motion",
    "font-family:": "font stack",
}
REVIEW_PACK_HUMAN_BRIEF_FORBIDDEN_CSS = {
    "gradient",
    "purple",
    "@import",
    "http://",
    "https://",
    "url(",
    "@font-face",
}

EXPECTED_CURRENT_BOUNDARY_HASHES = {
    "seed": "8fe5e75e9e0891b6824d7c142cbe15547267377420f8b3240414436265d15801",
    "sft": "4b677420f766555c04199f15f69f41f3b3ad36ad3cd5c33d2b40b0e3f8573587",
    "dpo": "b673dff3c1f598a250c8ed463be320fd2126b61a07e7672b83fbca4bae266ea8",
    "manifest": "f866c173795e97953b1dec85611b405867d0a29497910282f99d399f109cda95",
}

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
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def _one_line(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").split())


def _format_percent(value: float) -> str:
    if value == 0:
        return "0%"
    return f"{value * 100:.2f}%"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _markdown_links(text: str) -> list[str]:
    return [target.strip() for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", text)]


class _HumanBriefParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.anchors: list[tuple[str, str]] = []
        self.declarations: list[str] = []
        self.end_tags: list[str] = []
        self.events: list[tuple[str, str]] = []
        self.headings: list[tuple[int, str]] = []
        self.style_parts: list[str] = []
        self.tags: list[tuple[str, dict[str, str | None]]] = []
        self.visible_parts: list[str] = []
        self.footer_parts: list[str] = []
        self._anchor_href: str | None = None
        self._anchor_parts: list[str] = []
        self._footer_depth = 0
        self._heading_level: int | None = None
        self._heading_parts: list[str] = []
        self._hidden_depth = 0

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        attributes = dict(attrs)
        self.tags.append((tag, attributes))
        self.events.append(("start", tag))
        if tag == "footer":
            self._footer_depth += 1
        if tag in {"style", "script"}:
            self._hidden_depth += 1
        if tag == "a":
            self._anchor_href = attributes.get("href") or ""
            self._anchor_parts = []
        if re.fullmatch(r"h[1-6]", tag):
            self._heading_level = int(tag[1])
            self._heading_parts = []

    def handle_endtag(self, tag: str) -> None:
        self.end_tags.append(tag)
        self.events.append(("end", tag))
        if tag == "a" and self._anchor_href is not None:
            self.anchors.append(
                (self._anchor_href, " ".join("".join(self._anchor_parts).split()))
            )
            self._anchor_href = None
            self._anchor_parts = []
        if re.fullmatch(r"h[1-6]", tag) and self._heading_level is not None:
            self.headings.append(
                (
                    self._heading_level,
                    " ".join("".join(self._heading_parts).split()),
                )
            )
            self._heading_level = None
            self._heading_parts = []
        if tag in {"style", "script"}:
            self._hidden_depth = max(0, self._hidden_depth - 1)
        if tag == "footer":
            self._footer_depth = max(0, self._footer_depth - 1)

    def handle_decl(self, decl: str) -> None:
        self.declarations.append(decl)

    def handle_data(self, data: str) -> None:
        if self._hidden_depth:
            if self.tags and self.tags[-1][0] == "style":
                self.style_parts.append(data)
            return
        self.visible_parts.append(data)
        if self._footer_depth:
            self.footer_parts.append(data)
        if self._anchor_href is not None:
            self._anchor_parts.append(data)
        if self._heading_level is not None:
            self._heading_parts.append(data)

    @property
    def visible_text(self) -> str:
        return " ".join("".join(self.visible_parts).split())

    @property
    def css(self) -> str:
        return "".join(self.style_parts)

    @property
    def footer_text(self) -> str:
        return " ".join("".join(self.footer_parts).split())


def _is_repo_relative_link(target: str) -> bool:
    if target.startswith(("http://", "https://", "mailto:", "#")):
        return False
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1]
    return not target.startswith("/")


def _path_from_markdown_link(target: str, source_path: Path) -> Path:
    clean = target.strip()
    if clean.startswith("<") and clean.endswith(">"):
        clean = clean[1:-1]
    clean = clean.split("#", 1)[0]
    linked = (source_path.parent / clean).resolve()
    linked.relative_to(REPO_ROOT.resolve())
    return linked


def _active_openspec_changes() -> list[str]:
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
    changes = payload.get("changes", [])
    if not isinstance(changes, list):
        raise RuntimeError("openspec list changes must be a list")
    return sorted(str(change.get("name")) for change in changes if isinstance(change, dict))


def _check_doc_links(errors: list[str], path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    for target in _markdown_links(text):
        if not _is_repo_relative_link(target):
            continue
        try:
            linked = _path_from_markdown_link(target, path)
        except ValueError:
            errors.append(f"{path.relative_to(REPO_ROOT)} link target escapes repository: {target}")
            continue
        if not linked.exists():
            errors.append(f"{path.relative_to(REPO_ROOT)} link target missing: {target}")


def _check_review_pack_human_brief(
    errors: list[str],
    *,
    html_text: str | None = None,
) -> None:
    try:
        text = (
            REVIEW_PACK_HUMAN_BRIEF_PATH.read_text(encoding="utf-8")
            if html_text is None
            else html_text
        )
    except (OSError, UnicodeError) as exc:
        errors.append(f"review pack Human Brief unreadable: {type(exc).__name__}")
        return

    parser = _HumanBriefParser()
    try:
        parser.feed(text)
        parser.close()
    except Exception as exc:  # pragma: no cover - surfaced as validation failure
        errors.append(f"review pack Human Brief parse failed: {type(exc).__name__}")
        return

    visible = parser.visible_text
    if REVIEW_PACK_HUMAN_BRIEF_STATUS not in visible:
        errors.append("review pack Human Brief archived status drift")

    if text.startswith("<!doctype html>\n") is False or parser.declarations != [
        "doctype html"
    ]:
        errors.append("review pack Human Brief doctype drift")

    html_tags = [attrs for tag, attrs in parser.tags if tag == "html"]
    if html_tags != [{"lang": "zh-CN"}]:
        errors.append("review pack Human Brief language drift")

    skeleton_events = [
        event
        for event in parser.events
        if event[1] in {"html", "head", "body", "main"}
    ]
    expected_skeleton_events = [
        ("start", "html"),
        ("start", "head"),
        ("end", "head"),
        ("start", "body"),
        ("start", "main"),
        ("end", "main"),
        ("end", "body"),
        ("end", "html"),
    ]
    main_tags = [attrs for tag, attrs in parser.tags if tag == "main"]
    if (
        skeleton_events != expected_skeleton_events
        or main_tags != [{"id": "brief-main"}]
        or not text.rstrip().endswith("</html>")
    ):
        errors.append("review pack Human Brief closing skeleton drift")

    h1 = [heading for level, heading in parser.headings if level == 1]
    if h1 != ["Review pack 已归档，但执行边界仍完全阻断"]:
        errors.append("review pack Human Brief h1 drift")
    h2 = tuple(heading for level, heading in parser.headings if level == 2)
    if h2 != REVIEW_PACK_HUMAN_BRIEF_H2:
        errors.append("review pack Human Brief section order drift")

    for token in sorted(REVIEW_PACK_HUMAN_BRIEF_TRUTH):
        if token not in visible:
            errors.append(f"review pack Human Brief missing truth token: {token}")
    for token in sorted(REVIEW_PACK_HUMAN_BRIEF_FORBIDDEN):
        if token in visible:
            errors.append(f"review pack Human Brief forbidden truth token: {token}")
    if re.search(r"(?<![A-Za-z0-9_])mypy_status=PASS", text):
        errors.append("review pack Human Brief unqualified mypy pass marker")

    tags = [tag for tag, _attrs in parser.tags]
    for tag in sorted(REVIEW_PACK_HUMAN_BRIEF_FORBIDDEN_ELEMENTS.intersection(tags)):
        errors.append(f"review pack Human Brief forbidden element: {tag}")
    for _tag, attrs in parser.tags:
        for attribute in sorted(attrs):
            lowered_attribute = attribute.lower()
            if lowered_attribute.startswith("on"):
                errors.append(
                    "review pack Human Brief event handler attribute: "
                    f"{lowered_attribute}"
                )
            if lowered_attribute in REVIEW_PACK_HUMAN_BRIEF_URL_RESOURCE_ATTRIBUTES:
                errors.append(
                    "review pack Human Brief forbidden URL resource attribute: "
                    f"{lowered_attribute}"
                )
    if any("style" in attrs for _tag, attrs in parser.tags):
        errors.append("review pack Human Brief must not use inline style attributes")

    style_count = tags.count("style")
    if style_count != 1:
        errors.append("review pack Human Brief must contain exactly one style element")
    css = parser.css
    lowered_css = css.lower()
    colors = {color.lower() for color in re.findall(r"#[0-9a-fA-F]{6}", css)}
    if colors != REVIEW_PACK_HUMAN_BRIEF_COLORS:
        errors.append("review pack Human Brief exact five-color palette drift")
    for fragment, label in sorted(REVIEW_PACK_HUMAN_BRIEF_REQUIRED_CSS.items()):
        if fragment not in css:
            errors.append(f"review pack Human Brief missing {label} CSS")
    if "grid-template-columns" in lowered_css or re.search(
        r"\bcolumns\s*:", lowered_css
    ):
        errors.append("review pack Human Brief must remain single-column")
    for fragment in sorted(REVIEW_PACK_HUMAN_BRIEF_FORBIDDEN_CSS):
        if fragment in lowered_css:
            errors.append(f"review pack Human Brief forbidden CSS token: {fragment}")

    for token in (
        "human_brief_role=NAVIGATION_SUMMARY_ONLY",
        "authoritative_sources=OPENSPEC_RAW_SUMMARY_MANIFEST_TESTS_VALIDATION",
    ):
        if token not in parser.footer_text:
            errors.append(f"review pack Human Brief footer authority drift: {token}")

    hrefs = {href for href, _anchor_text in parser.anchors if not href.startswith("#")}
    for required in sorted(REVIEW_PACK_HUMAN_BRIEF_REQUIRED_LINKS - hrefs):
        errors.append(f"review pack Human Brief missing required link: {required}")

    for target, anchor_text in parser.anchors:
        if not anchor_text:
            errors.append(f"review pack Human Brief empty link text: {target}")
        if target.startswith("#"):
            ids = {
                element_id
                for _tag, attrs in parser.tags
                if (element_id := attrs.get("id")) is not None
            }
            if not target[1:] or target[1:] not in ids:
                errors.append(
                    "review pack Human Brief fragment target missing: "
                    f"{target}"
                )
            continue
        parts = urlsplit(target)
        if parts.scheme or parts.netloc or target.startswith("/"):
            errors.append(f"review pack Human Brief external or absolute link forbidden: {target}")
            continue
        try:
            linked = (REVIEW_PACK_HUMAN_BRIEF_PATH.parent / parts.path).resolve()
            linked.relative_to(REPO_ROOT.resolve())
        except ValueError:
            errors.append(
                "review pack Human Brief link target escapes repository: "
                f"{target}"
            )
            continue
        if not linked.exists():
            errors.append(f"review pack Human Brief link target missing: {target}")


def _check_index(errors: list[str]) -> list[dict[str, Any]]:
    payload = _load_json(INDEX_JSON_PATH)
    if payload.get("generated_at") != "2026-07-11":
        errors.append("evidence-index generated_at must be 2026-07-11")
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


def _load_lockbox_artifacts() -> dict[str, dict[str, Any]]:
    return {
        "manifest": _load_json(LOCKBOX_MANIFEST_PATH),
        "run_card": _load_json(LOCKBOX_RUN_CARD_PATH),
        "base_metrics": _load_json(LOCKBOX_BASE_METRICS_PATH),
        "final_metrics": _load_json(LOCKBOX_FINAL_METRICS_PATH),
        "comparison": _load_json(LOCKBOX_COMPARISON_PATH),
    }


def _check_lockbox_evidence(
    errors: list[str],
    items: list[dict[str, Any]],
    markdown: str,
    *,
    artifacts: dict[str, dict[str, Any]] | None = None,
) -> None:
    by_id = {str(item.get("id")): item for item in items}
    final_item = by_id.get("lockbox-v1-final-evaluation")
    history_item = by_id.get("must-fix-phase-3-lockbox-lineage-guard")
    if final_item is None:
        errors.append("evidence-index missing lockbox-v1-final-evaluation")
    else:
        if final_item.get("status") != "CURRENT":
            errors.append("lockbox-v1-final-evaluation must be CURRENT")
        if final_item.get("path") != "reports/lockbox-v1/final-evaluation/comparison.json":
            errors.append("lockbox-v1-final-evaluation must point to final comparison")
        if final_item.get("current_claim_allowed") is not True:
            errors.append("lockbox-v1-final-evaluation must allow its bounded current claim")
    if history_item is None:
        errors.append("evidence-index missing must-fix-phase-3-lockbox-lineage-guard history")
    else:
        if history_item.get("status") != "SUPERSEDED":
            errors.append("must-fix-phase-3-lockbox-lineage-guard must be SUPERSEDED")
        if history_item.get("superseded_by") != "lockbox-v1-final-evaluation":
            errors.append("lockbox lineage history must be superseded by final evaluation")

    current_section = markdown.split("## Historical Training Runs", 1)[0]
    superseded_and_after = markdown.split("## Superseded Evidence", 1)
    blocked_and_after = markdown.split("## Blocked Runs", 1)
    if "lockbox-v1-final-evaluation" not in current_section:
        errors.append("Markdown current table missing lockbox-v1-final-evaluation")
    if len(superseded_and_after) != 2 or "must-fix-phase-3-lockbox-lineage-guard" not in (
        superseded_and_after[1].split("## Blocked Runs", 1)[0]
    ):
        errors.append("Markdown superseded table missing lockbox lineage history")
    if len(blocked_and_after) == 2 and "must-fix-phase-3-lockbox-lineage-guard" in (
        blocked_and_after[1].split("## Design-Only Evidence", 1)[0]
    ):
        errors.append("Markdown blocked table retains superseded lockbox lineage history")

    loaded = artifacts or _load_lockbox_artifacts()
    manifest = loaded["manifest"]
    run_card = loaded["run_card"]
    base_metrics = loaded["base_metrics"]
    final_metrics = loaded["final_metrics"]
    comparison = loaded["comparison"]
    if manifest.get("row_count") != 120 or manifest.get("family_count") != 120:
        errors.append("lockbox manifest must remain 120 rows / 120 families")
    if manifest.get("frozen") is not True:
        errors.append("lockbox manifest must remain frozen")

    run_lockbox = run_card.get("lockbox", {})
    for field in ("manifest_id", "lockbox_hash", "row_count", "family_count", "frozen"):
        if run_lockbox.get(field) != manifest.get(field):
            errors.append(f"lockbox run card {field} disagrees with frozen manifest")
    if run_card.get("one_look_rule", {}).get("final_lockbox_evaluation_run_once") is not True:
        errors.append("lockbox run card must preserve one-look completion")
    if run_card.get("prompt_policy") != "unified_gold_free_v1":
        errors.append("lockbox run card prompt policy drift")

    for arm_name, metrics_artifact in (("base", base_metrics), ("final_sft", final_metrics)):
        if metrics_artifact.get("row_count") != manifest.get("row_count"):
            errors.append(f"lockbox {arm_name} metrics row count disagrees with manifest")
        if metrics_artifact.get("prompt_policy") != run_card.get("prompt_policy"):
            errors.append(f"lockbox {arm_name} metrics prompt policy drift")
        if metrics_artifact.get("public_report_policy", {}).get("aggregate_metrics_only") is not True:
            errors.append(f"lockbox {arm_name} metrics must remain aggregate-only")

    if comparison.get("row_count") != manifest.get("row_count"):
        errors.append("lockbox comparison row count disagrees with manifest")
    if comparison.get("prompt_policy") != run_card.get("prompt_policy"):
        errors.append("lockbox comparison prompt policy drift")
    if comparison.get("public_report_policy", {}).get("aggregate_metrics_only") is not True:
        errors.append("lockbox comparison must remain aggregate-only")
    if comparison.get("metrics", {}).get("base") != base_metrics.get("metrics"):
        errors.append("lockbox comparison base metrics disagree with authoritative base metrics")
    if comparison.get("metrics", {}).get("final_sft") != final_metrics.get("metrics"):
        errors.append("lockbox comparison final metrics disagree with authoritative final metrics")

    base_values = base_metrics.get("metrics", {})
    final_values = final_metrics.get("metrics", {})
    deltas = comparison.get("delta", {})
    for metric_name in sorted(set(base_values).intersection(final_values)):
        base_value = base_values[metric_name]
        final_value = final_values[metric_name]
        delta_value = deltas.get(metric_name)
        if all(isinstance(value, (int, float)) for value in (base_value, final_value, delta_value)):
            if not math.isclose(
                float(delta_value), float(final_value) - float(base_value), rel_tol=0.0, abs_tol=1e-15
            ):
                errors.append(f"lockbox comparison delta drift: {metric_name}")

    if final_item is not None:
        if final_item.get("manifest_id") != manifest.get("manifest_id"):
            errors.append("lockbox final index manifest identity drift")
        if final_item.get("model_run_id") != run_card.get("run_id"):
            errors.append("lockbox final index run identity drift")
        summary = str(final_item.get("summary", ""))
        base_exact = float(base_values.get("contract_exact_match", 0.0))
        final_exact = float(final_values.get("contract_exact_match", 0.0))
        exact_delta = float(deltas.get("contract_exact_match", 0.0))
        expected_summary_phrase = (
            f"Final SFT contract_exact_match {final_exact:.4f} versus base {base_exact:.4f}, "
            f"delta {exact_delta:.4f}"
        )
        if expected_summary_phrase not in summary:
            errors.append("lockbox final index summary disagrees with strict exact aggregate")
        boundary = str(final_item.get("boundary", ""))
        boundary_tokens = (
            f"{manifest.get('row_count')}-row",
            f"{manifest.get('family_count')}-family",
            str(run_card.get("prompt_policy")),
            "aggregate-only",
        )
        if any(token not in boundary for token in boundary_tokens):
            errors.append("lockbox JSON index boundary disagrees with raw count or protocol")

        markdown_rows = [
            line
            for line in current_section.splitlines()
            if "lockbox-v1-final-evaluation" in line
        ]
        expected_markdown_tokens = (
            f"{manifest.get('row_count')}-row",
            f"{manifest.get('family_count')}-family",
            str(run_card.get("prompt_policy")),
        )
        expected_aggregate_phrase = (
            f"Final SFT strict exact {final_exact:.4f} versus base {base_exact:.4f} "
            f"(delta {exact_delta:.4f})"
        )
        if len(markdown_rows) != 1 or any(
            token not in markdown_rows[0] for token in expected_markdown_tokens
        ) or expected_aggregate_phrase not in markdown_rows[0]:
            errors.append("lockbox Markdown current row aggregate or protocol drift")


def _check_split_integrity_evidence(errors: list[str], items: list[dict[str, Any]]) -> None:
    audit = _load_json(SPLIT_AUDIT_JSON_PATH)
    manifest = _load_json(MANIFEST_PATH)
    by_id = {str(item.get("id")): item for item in items}
    index_item = by_id.get("public-split-integrity-audit")
    if index_item is None or index_item.get("status") != "CURRENT":
        errors.append("public split integrity audit must be a CURRENT index item")
    elif index_item.get("path") != "reports/public-sample/split-integrity-audit/summary.json":
        errors.append("public split integrity audit index path drift")

    expected_sources = {
        "seed": ("data/public-samples/seed_traces.jsonl", PUBLIC_SEED_PATH),
        "sft": ("data/public-samples/sft_public_sample.jsonl", PUBLIC_SFT_PATH),
        "dpo": ("data/public-samples/dpo_public_sample.jsonl", PUBLIC_DPO_PATH),
        "manifest": ("data/public-samples/manifest_public_sample.json", MANIFEST_PATH),
    }
    for source_name, (expected_path, source_path) in expected_sources.items():
        actual_hash = _sha256(source_path)
        if actual_hash != EXPECTED_CURRENT_BOUNDARY_HASHES[source_name]:
            errors.append(f"immutable current-boundary hash drift: {source_name}")
        source = audit.get("sources", {}).get(source_name, {})
        if source.get("path") != expected_path:
            errors.append(f"split integrity {source_name} source path drift")
        if source.get("sha256") != actual_hash:
            errors.append(f"split integrity {source_name} source hash drift")

    try:
        sys.path.insert(0, str(REPO_ROOT / "src"))
        from voice2task.split_integrity import (
            audit_split_integrity,
            render_split_integrity_markdown,
        )

        recomputed = audit_split_integrity(
            seed_path=PUBLIC_SEED_PATH,
            sft_path=PUBLIC_SFT_PATH,
            dpo_path=PUBLIC_DPO_PATH,
            manifest_path=MANIFEST_PATH,
            repo_root=REPO_ROOT,
        )
        rendered = render_split_integrity_markdown(recomputed)
    except Exception as exc:  # pragma: no cover - surfaced as validation failure
        errors.append(f"split integrity full recomputation failed: {exc}")
        return

    if audit != recomputed:
        errors.append("split integrity JSON does not exactly match full raw recomputation")
    if SPLIT_AUDIT_MD_PATH.read_text(encoding="utf-8") != rendered:
        errors.append("split integrity Markdown does not exactly match full raw recomputation")
    if manifest.get("manifest_id") != "public-sample-20260619T090925Z":
        errors.append("current public manifest identity drift")


def _check_clean_evaluation_boundary(
    errors: list[str],
    items: list[dict[str, Any]],
    markdown: str,
    *,
    summary: dict[str, Any] | None = None,
) -> None:
    by_id = {str(item.get("id")): item for item in items}
    index_item = by_id.get("clean-compiler-model-evaluation-boundary-v1")
    if index_item is None:
        errors.append("evidence-index missing clean compiler/model evaluation boundary")
    else:
        if index_item.get("status") != "BLOCKED":
            errors.append("clean compiler/model evaluation boundary index status must be BLOCKED")
        if index_item.get("path") != (
            "reports/public-sample/clean-compiler-model-evaluation-boundary-v1/summary.json"
        ):
            errors.append("clean compiler/model evaluation boundary index path drift")
        if index_item.get("current_claim_allowed") is not False:
            errors.append("clean compiler/model evaluation boundary must not allow a current claim")
        if index_item.get("superseded_by") is not None:
            errors.append("clean compiler/model evaluation boundary superseded_by must remain null")
    design_item = by_id.get("clean-matched-causal-evidence-design")
    if design_item is None or design_item.get("status") != "DESIGN_ONLY":
        errors.append("clean matched design must remain DESIGN_ONLY")
    blocked_section = markdown.split("## Blocked Runs", 1)
    blocked_table = (
        blocked_section[1].split("## Design-Only Evidence", 1)[0]
        if len(blocked_section) == 2
        else ""
    )
    if ACTIVE_CLEAN_BOUNDARY_CHANGE not in blocked_table:
        errors.append("Markdown blocked table missing clean compiler/model evaluation boundary")

    observed = summary if summary is not None else _load_json(CLEAN_BOUNDARY_SUMMARY_PATH)
    expected_scalars = {
        "evidence_status": "BLOCKED",
        "decision": "CLEAN_EVALUATION_BOUNDARY_MATERIALIZATION_BLOCKED",
        "blocked_stage": "S0_SOURCE_OR_BINDING",
        "current_readiness_state": "DESIGN_ONLY",
        "maximum_state_this_change": "DESIGN_ONLY",
        "execution_bindings_status": "INCOMPLETE",
        "protocol_freeze_status": "NOT_FROZEN",
        "clean_population_status": "NOT_MATERIALIZED",
        "population_unit": "NOT_CREATED",
        "clean_evaluation_rows_status": "NOT_CREATED",
        "boundary_integrity_status": "NOT_CREATED",
        "arm_artifacts_status": "NOT_FROZEN",
        "experiment_preregistration_status": "NOT_EXECUTABLE",
        "execution_readiness": False,
        "compiler_causal_identification_status": "CAUSAL_IDENTIFICATION_BLOCKED",
        "model_causal_identification_status": "CAUSAL_IDENTIFICATION_BLOCKED",
    }
    for field, expected in expected_scalars.items():
        if observed.get(field) != expected:
            errors.append(f"clean evaluation boundary {field} drift")
    if observed.get("binding_counts") != {"total": 29, "bound": 0, "unbound": 29}:
        errors.append("clean evaluation boundary binding counts must remain 29/0/29")
    expected_blockers = {
        "ACQUISITION_SOURCE_UNAVAILABLE_OR_UNVERIFIABLE",
        "BINDING_INCOMPLETE_OR_PLACEHOLDER",
    }
    if set(observed.get("blockers", [])) != expected_blockers:
        errors.append("clean evaluation boundary blocker set drift")
    expected_partition = {
        "status": "NOT_MATERIALIZED",
        "one_look_state": "NOT_AVAILABLE",
        "access_count": 0,
        "consumed": False,
    }
    partitions = observed.get("partitions", {})
    if set(partitions) != {"compiler_system_evaluation", "model_learning_evaluation"} or any(
        partition != expected_partition for partition in partitions.values()
    ):
        errors.append("clean evaluation boundary partition/one-look truth drift")
    hashes = observed.get("hashes", {})
    if not isinstance(hashes, dict) or not hashes or set(hashes.values()) != {"NOT_AVAILABLE"}:
        errors.append("clean evaluation boundary unavailable hashes must remain NOT_AVAILABLE")
    for group in ("artifacts", "mutations", "access_and_runs", "claims"):
        values = observed.get(group, {})
        if not isinstance(values, dict) or not values or any(value is not False for value in values.values()):
            errors.append(f"clean evaluation boundary {group} flags must all remain false")

    if summary is None:
        actual_files = {path.name for path in CLEAN_BOUNDARY_REPORT_DIR.iterdir() if path.is_file()}
        if actual_files != CLEAN_BOUNDARY_PUBLIC_FILES:
            errors.append("clean evaluation boundary public artifact set must contain exactly five files")
        baseline = observed.get("protected_input_baseline", {})
        protected_paths = {
            ("prior_design_report_sha256", "json"): (
                REPO_ROOT / "reports/public-sample/clean-matched-causal-evidence-design/summary.json"
            ),
            ("prior_design_report_sha256", "markdown"): (
                REPO_ROOT / "reports/public-sample/clean-matched-causal-evidence-design/summary.md"
            ),
            ("public_dataset_sha256", "seed"): PUBLIC_SEED_PATH,
            ("public_dataset_sha256", "sft"): PUBLIC_SFT_PATH,
            ("public_dataset_sha256", "dpo"): PUBLIC_DPO_PATH,
            ("public_dataset_sha256", "manifest"): MANIFEST_PATH,
            ("lockbox_aggregate_sha256", "manifest"): LOCKBOX_MANIFEST_PATH,
            ("lockbox_aggregate_sha256", "run_card"): LOCKBOX_RUN_CARD_PATH,
            ("lockbox_aggregate_sha256", "base_metrics"): LOCKBOX_BASE_METRICS_PATH,
            ("lockbox_aggregate_sha256", "final_sft_metrics"): LOCKBOX_FINAL_METRICS_PATH,
            ("lockbox_aggregate_sha256", "comparison"): LOCKBOX_COMPARISON_PATH,
        }
        for (group, name), path in protected_paths.items():
            if not isinstance(baseline, dict) or baseline.get(group, {}).get(name) != _sha256(path):
                errors.append(f"clean evaluation boundary protected hash drift: {group}.{name}")


def _check_review_pack_evidence(
    errors: list[str],
    items: list[dict[str, Any]],
    markdown: str,
    *,
    summary: dict[str, Any] | None = None,
) -> None:
    expected_path = (
        "reports/public-sample/clean-evaluation-acquisition-and-binding-review-pack-v1/summary.json"
    )
    expected_item = {
        "id": REVIEW_PACK_ID,
        "status": "DESIGN_ONLY",
        "phase": REVIEW_PACK_PHASE,
        "path": expected_path,
        "manifest_id": None,
        "model_run_id": None,
        "boundary": (
            "PREPARATION_ONLY non-executable operator guidance over the canonical 29-field "
            "inventory; supplied bindings 0/29; authoritatively bound bindings 0; "
            "independent acquisition source UNAVAILABLE."
        ),
        "summary": (
            "DESIGN_ONLY; ACQUISITION_AND_BINDING_REVIEW_PACK_READY_EXECUTION_BLOCKED; "
            "review pack READY_FOR_EXTERNAL_COMPLETION only; candidate pack INCOMPLETE; "
            "protocol NOT_FROZEN; population NOT_MATERIALIZED; human acceptance "
            "NOT_RECORDED; "
            "freeze_authorized=false; next_phase_eligible=false; execution_readiness=false."
        ),
        "conclusion": (
            "READY_FOR_EXTERNAL_COMPLETION means only that the public template, schema, and "
            "checklist are ready for external completion. This is not an acquisition source, "
            "reviewed binding packet, frozen protocol, clean population, or executable "
            "experiment; it records no human acceptance or lifecycle authorization and does "
            "not supersede the archived S0 BLOCKED result."
        ),
        "current_claim_allowed": False,
        "superseded_by": None,
    }
    s0_id = "clean-compiler-model-evaluation-boundary-v1"
    ids = [str(item.get("id")) for item in items]
    review_count = ids.count(REVIEW_PACK_ID)
    s0_count = ids.count(s0_id)
    if review_count != 1:
        errors.append("review pack index id must appear exactly once")
    if s0_count != 1:
        errors.append("archived S0 index id must appear exactly once")

    if review_count == 1 and s0_count == 1:
        by_id = {str(item.get("id")): item for item in items}
        index_item = by_id[REVIEW_PACK_ID]
        if tuple(index_item) != tuple(expected_item):
            errors.append("review pack index exact 11-key surface drift")
        for field, expected in expected_item.items():
            if index_item.get(field) != expected:
                errors.append(f"review pack index {field} drift")

        s0_item = by_id[s0_id]
        if s0_item.get("superseded_by") is not None:
            errors.append("archived S0 superseded_by must remain null")

        expected_order = [
            s0_id,
            REVIEW_PACK_ID,
            "clean-matched-causal-evidence-design",
        ]
        s0_position = ids.index(s0_id)
        if ids[s0_position : s0_position + 3] != expected_order:
            errors.append("review pack index ordering must be S0, review pack, prior design")

    expected_markdown_row = (
        "| DESIGN_ONLY | prepare-clean-evaluation-acquisition-and-binding-review-pack-v1 | "
        "`PREPARATION_ONLY` non-executable operator guidance; canonical 29-item inventory; "
        "supplied bindings 0/29; authoritatively bound 0; independent acquisition source "
        "`UNAVAILABLE` | "
        "`ACQUISITION_AND_BINDING_REVIEW_PACK_READY_EXECUTION_BLOCKED`; review pack "
        "`READY_FOR_EXTERNAL_COMPLETION` only, candidate pack `INCOMPLETE`; protocol "
        "`NOT_FROZEN`, population `NOT_MATERIALIZED`, human acceptance `NOT_RECORDED`, "
        "`freeze_authorized=false`, `next_phase_eligible=false`, "
        "`execution_readiness=false`; not a source, reviewed binding packet, frozen protocol, "
        "clean population, or executable experiment; archived S0 remains blocked and "
        "unsuperseded. | - | "
        "`reports/public-sample/clean-evaluation-acquisition-and-binding-review-pack-v1/summary.json` |"
    )
    current_section = markdown.split("## Historical Training Runs", 1)[0]
    blocked_parts = markdown.split("## Blocked Runs", 1)
    blocked_section = (
        blocked_parts[1].split("## Design-Only Evidence", 1)[0]
        if len(blocked_parts) == 2
        else ""
    )
    design_parts = markdown.split("## Design-Only Evidence", 1)
    design_section = (
        design_parts[1].split("## Raw/Reproducibility Inputs", 1)[0]
        if len(design_parts) == 2
        else ""
    )
    design_rows = [
        line for line in design_section.splitlines() if line.startswith("| DESIGN_ONLY |")
    ]
    if REVIEW_PACK_PHASE in current_section:
        errors.append("review pack must not appear in Markdown current evidence")
    if REVIEW_PACK_PHASE in blocked_section:
        errors.append("review pack must not appear in Markdown blocked evidence")
    if design_section.count(REVIEW_PACK_PHASE) != 1:
        errors.append("review pack must appear exactly once in Markdown design-only evidence")
    if not design_rows or design_rows[0] != expected_markdown_row:
        errors.append("review pack must be the exact first Markdown design-only row")

    observed = summary if summary is not None else _load_json(REVIEW_PACK_SUMMARY_PATH)
    expected_truth = {
        "evidence_status": "DESIGN_ONLY",
        "phase_status": "PREPARATION_ONLY",
        "decision": "ACQUISITION_AND_BINDING_REVIEW_PACK_READY_EXECUTION_BLOCKED",
        "review_pack_status": "READY_FOR_EXTERNAL_COMPLETION",
        "candidate_pack_status": "INCOMPLETE",
        "binding_inventory_count": 29,
        "supplied_binding_count": 0,
        "authoritatively_bound_binding_count": 0,
        "acquisition_source_status": "UNAVAILABLE",
        "protocol_freeze_status": "NOT_FROZEN",
        "clean_population_status": "NOT_MATERIALIZED",
        "human_acceptance_status": "NOT_RECORDED",
        "freeze_authorized": False,
        "next_phase_eligible": False,
        "execution_readiness": False,
    }
    for field, expected_truth_value in expected_truth.items():
        if observed.get(field) != expected_truth_value:
            errors.append(f"review pack summary {field} drift")

    required_tokens = {
        "DESIGN_ONLY",
        "PREPARATION_ONLY",
        "ACQUISITION_AND_BINDING_REVIEW_PACK_READY_EXECUTION_BLOCKED",
        "review_pack_status=READY_FOR_EXTERNAL_COMPLETION",
        "candidate_pack_status=INCOMPLETE",
        "binding_inventory_count=29",
        "supplied_binding_count=0",
        "authoritatively_bound_binding_count=0",
        "acquisition_source_status=UNAVAILABLE",
        "protocol_freeze_status=NOT_FROZEN",
        "clean_population_status=NOT_MATERIALIZED",
        "human_acceptance_status=NOT_RECORDED",
        "freeze_authorized=false",
        "next_phase_eligible=false",
        "execution_readiness=false",
    }
    required_boundaries = {
        "review-pack readiness only",
        "not a reviewed or accepted candidate",
        "does not bind any input",
        "does not freeze a protocol",
        "does not materialize a population",
        "is not executable",
        "does not supersede the archived S0 blocker",
    }
    navigation = {
        CONTEXT_PATH: expected_path,
        CURRENT_STATUS_PATH: f"../{expected_path}",
    }
    for path, expected_link in navigation.items():
        text = path.read_text(encoding="utf-8")
        for token in sorted(required_tokens):
            if token not in text:
                errors.append(f"{path.relative_to(REPO_ROOT)} missing review pack truth: {token}")
        for phrase in sorted(required_boundaries):
            if phrase not in text:
                errors.append(f"{path.relative_to(REPO_ROOT)} missing review boundary: {phrase}")
        if expected_link not in _markdown_links(text):
            errors.append(f"{path.relative_to(REPO_ROOT)} missing review pack summary link")


def _check_review_pack_recovery_gate(errors: list[str]) -> None:
    try:
        recovery_present = any(
            path.name.startswith(REVIEW_PACK_RECOVERY_PREFIX)
            for path in REVIEW_PACK_PUBLIC_PARENT_PATH.iterdir()
        )
    except OSError:
        errors.append("review pack recovery gate unavailable")
        return
    if recovery_present:
        errors.append(
            "review pack current classification blocked by reserved recovery sibling"
        )


def _check_current_docs(errors: list[str]) -> None:
    summary = _load_json(SUMMARY_PATH)
    internal_summary = _load_json(INTERNAL_SUMMARY_PATH)
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
        internal_summary["decision_label"],
        _format_percent(internal_summary["derive_display_supported_rate"]),
        f"{internal_summary['derive_display_unsupported_count']} unsupported",
        internal_summary["recommended_next_change"],
        internal_summary["default_external_schema"],
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
        if "DEVELOPMENT_ONLY_SPENT" not in text:
            errors.append(f"{doc_name} missing spent public dev/test boundary")
        if "JSON type-strict" not in text:
            errors.append(f"{doc_name} missing future exact-match type boundary")


def validate(
    *,
    allow_active_clean_boundary: bool = False,
    allow_active_review_pack: bool = False,
) -> list[str]:
    errors: list[str] = []
    required_paths = [
        SUMMARY_PATH,
        INTERNAL_SUMMARY_PATH,
        MANIFEST_PATH,
        INDEX_JSON_PATH,
        INDEX_MD_PATH,
        README_PATH,
        README_EN_PATH,
        CONTEXT_PATH,
        CURRENT_STATUS_PATH,
        LOCKBOX_MANIFEST_PATH,
        LOCKBOX_RUN_CARD_PATH,
        LOCKBOX_BASE_METRICS_PATH,
        LOCKBOX_FINAL_METRICS_PATH,
        LOCKBOX_COMPARISON_PATH,
        SPLIT_AUDIT_JSON_PATH,
        SPLIT_AUDIT_MD_PATH,
        PUBLIC_SEED_PATH,
        PUBLIC_SFT_PATH,
        PUBLIC_DPO_PATH,
        CLEAN_BOUNDARY_SUMMARY_PATH,
        REVIEW_PACK_SUMMARY_PATH,
        REVIEW_PACK_HUMAN_BRIEF_PATH,
        *(CLEAN_BOUNDARY_REPORT_DIR / name for name in sorted(CLEAN_BOUNDARY_PUBLIC_FILES)),
    ]
    for required_path in required_paths:
        if not required_path.exists():
            errors.append(f"missing required path: {required_path.relative_to(REPO_ROOT)}")
    if errors:
        return errors
    if allow_active_review_pack:
        errors.append(RETIRED_REVIEW_PACK_FLAG_ERROR)

    items = _check_index(errors)
    _check_lockbox_evidence(errors, items, INDEX_MD_PATH.read_text(encoding="utf-8"))
    _check_split_integrity_evidence(errors, items)
    _check_clean_evaluation_boundary(errors, items, INDEX_MD_PATH.read_text(encoding="utf-8"))
    _check_review_pack_evidence(errors, items, INDEX_MD_PATH.read_text(encoding="utf-8"))
    _check_review_pack_recovery_gate(errors)
    _check_review_pack_human_brief(errors)
    _check_current_docs(errors)
    _check_doc_links(errors, README_PATH)
    _check_doc_links(errors, README_EN_PATH)
    _check_doc_links(errors, CONTEXT_PATH)
    _check_doc_links(errors, CURRENT_STATUS_PATH)
    _check_doc_links(errors, INDEX_MD_PATH)
    if "reports/public-sample/EVIDENCE_INDEX.md" not in CONTEXT_PATH.read_text(encoding="utf-8"):
        errors.append("CONTEXT.md must link to reports/public-sample/EVIDENCE_INDEX.md")

    try:
        active_changes = _active_openspec_changes()
    except RuntimeError as exc:
        errors.append(f"openspec active count unavailable: {exc}")
    else:
        if allow_active_clean_boundary and allow_active_review_pack:
            errors.append("active OpenSpec allow flags are mutually exclusive")
            allowed_active: list[str] = []
        elif allow_active_clean_boundary:
            allowed_active = [ACTIVE_CLEAN_BOUNDARY_CHANGE]
        else:
            allowed_active = []
        if active_changes not in ([], allowed_active):
            errors.append(
                "active OpenSpec changes must be empty after review pack archive, "
                f"got {active_changes}"
            )

    try:
        sys.path.insert(0, str(REPO_ROOT / "src"))
        from voice2task.leak_scan import scan_paths

        scan_result = scan_paths(
            [
                README_PATH,
                README_EN_PATH,
                CONTEXT_PATH,
                CURRENT_STATUS_PATH,
                INDEX_MD_PATH,
                INDEX_JSON_PATH,
                REVIEW_PACK_SUMMARY_PATH,
                REVIEW_PACK_HUMAN_BRIEF_PATH,
                SPLIT_AUDIT_JSON_PATH,
                SPLIT_AUDIT_MD_PATH,
                *(CLEAN_BOUNDARY_REPORT_DIR / name for name in sorted(CLEAN_BOUNDARY_PUBLIC_FILES)),
            ]
        )
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
    allow_active_clean_boundary = "--allow-active-clean-boundary" in sys.argv[1:]
    allow_active_review_pack = "--allow-active-review-pack" in sys.argv[1:]
    known = {"--allow-active-clean-boundary", "--allow-active-review-pack"}
    unknown = [argument for argument in sys.argv[1:] if argument not in known]
    if unknown:
        print(f"unknown arguments: {' '.join(unknown)}")
        return 2
    errors = validate(
        allow_active_clean_boundary=allow_active_clean_boundary,
        allow_active_review_pack=allow_active_review_pack,
    )
    if errors:
        print("current truth surface check failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("current truth surface check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
