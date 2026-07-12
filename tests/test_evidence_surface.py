from __future__ import annotations

import json
import re
import subprocess
import sys
from copy import deepcopy
from html.parser import HTMLParser
from importlib import util as importlib_util
from pathlib import Path
from types import ModuleType
from urllib.parse import urlsplit

import pytest

from voice2task.leak_scan import scan_paths

REPO_ROOT = Path(__file__).resolve().parents[1]
CHECKER = REPO_ROOT / "scripts/check_current_truth_surface.py"
INDEX_JSON = REPO_ROOT / "reports/public-sample/evidence-index.json"
INDEX_MD = REPO_ROOT / "reports/public-sample/EVIDENCE_INDEX.md"
README = REPO_ROOT / "README.md"
README_EN = REPO_ROOT / "README_en.md"
CONTEXT = REPO_ROOT / "CONTEXT.md"
CURRENT_STATUS = REPO_ROOT / "docs/current-status.md"
CLEAN_BOUNDARY_SUMMARY = (
    REPO_ROOT / "reports/public-sample/clean-compiler-model-evaluation-boundary-v1/summary.json"
)
REVIEW_PACK_ID = "clean-evaluation-acquisition-and-binding-review-pack-v1"
REVIEW_PACK_PHASE = "prepare-clean-evaluation-acquisition-and-binding-review-pack-v1"
RETIRED_REVIEW_PACK_FLAG_ERROR = (
    "--allow-active-review-pack is retired because "
    f"{REVIEW_PACK_PHASE} is archived"
)
REVIEW_PACK_PATH = (
    "reports/public-sample/clean-evaluation-acquisition-and-binding-review-pack-v1/summary.json"
)
REVIEW_PACK_SUMMARY = REPO_ROOT / REVIEW_PACK_PATH
REVIEW_PACK_ARCHIVE_PATH = (
    "openspec/changes/archive/"
    "2026-07-12-prepare-clean-evaluation-acquisition-and-binding-review-pack-v1"
)
REVIEW_PACK_CHANGE_ROOT = REPO_ROOT / REVIEW_PACK_ARCHIVE_PATH
REVIEW_PACK_PROPOSAL = REVIEW_PACK_CHANGE_ROOT / "proposal.md"
REVIEW_PACK_DESIGN = REVIEW_PACK_CHANGE_ROOT / "design.md"
REVIEW_PACK_TASKS = REVIEW_PACK_CHANGE_ROOT / "tasks.md"
REVIEW_PACK_DELTA_SPEC = (
    REVIEW_PACK_CHANGE_ROOT
    / "specs/clean-evaluation-acquisition-and-binding-review-pack/spec.md"
)
REVIEW_PACK_MAIN_SPEC = (
    REPO_ROOT
    / "openspec/specs/clean-evaluation-acquisition-and-binding-review-pack/spec.md"
)
HUMAN_BRIEF = (
    REPO_ROOT
    / "docs/human-briefs/2026-07-11-prepare-clean-evaluation-acquisition-and-binding-review-pack-v1.html"
)
HUMAN_BRIEF_TITLE = "Voice2Task Review Pack Archived · 人类简报"
HUMAN_BRIEF_STATUS = "ARCHIVED · REVIEW PACK READY ONLY · EXECUTION BLOCKED"
HUMAN_BRIEF_H2 = (
    "当前状态",
    "本阶段改变了什么",
    "信任与权限边界",
    "权威来源与关键产物",
    "验证证据",
    "剩余风险与禁止过度声明",
    "建议下一步",
)
HUMAN_BRIEF_TRUTH_TOKENS = (
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
    "task_4_1_status=COMPLETE",
    "task_4_2_status=COMPLETE",
    "task_4_3_status=COMPLETE_WITH_EXPLICIT_LIFECYCLE_AND_BASELINE_LIMITATIONS",
    "task_4_4_status=COMPLETE_AFTER_3_MUST_FIXES_RESOLVED_AND_TWO_INDEPENDENT_REVIEWS_PASS",
    "openspec_progress=20/20",
    "full_pytest_status=1260_PASSED",
    "full_pytest_failure_scope=NONE",
    "full_pytest_failure_reason=NONE",
    "challenge_hash_policy_rows_template_disjoint=PASS",
    "focused_mypy_status=PASS_4_FILES_0_ISSUES",
    "full_mypy_rerun=39_ERRORS_IN_5_FILES_CHECKED_31_SOURCE_FILES",
    "full_mypy_status=RECORDED_BASELINE_PRESERVED",
    "full_mypy_source_coverage=31_CURRENT_VS_28_PRIOR_RECORDED",
    "default_zero_active_truth_status=PASS",
    "active_openspec_changes=0",
    (
        "archive_path=openspec/changes/archive/"
        "2026-07-12-prepare-clean-evaluation-acquisition-and-binding-review-pack-v1"
    ),
    "main_spec_sync=PASS_7_REQUIREMENTS_29_SCENARIOS",
    "task_4_3_independent_gate_reviewer=PASS",
    "task_4_4_must_fixes_resolved=3/3",
    "task_4_4_spec_truth_reviewer=PASS",
    "task_4_4_code_security_reviewer=PASS",
    "final_independent_review_status=PASS_TASK_4_4",
    "task_4_5_archive_status=COMPLETE",
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
    "trusted_exclusive_cooperative_same_euid=true",
    "malicious_same_euid_replacement=ACCOUNT_PROCESS_BOUNDARY_COMPROMISE",
    "no_mutation_exclusion=DESCRIPTOR_READ_ACCESS_TIME_ONLY",
    "recovery_automatic_gc=false",
)
HUMAN_BRIEF_NEXT_STEP_TOKENS = (
    "task_4_1_scope=PUBLICATION_RECOVERY_NO_REPLACE_EXACT_NOOP_CLI_LINT_CURRENT_LEGACY_ACCEPTANCE",
    "task_4_2_scope=TEMP_BUILD_PUBLIC_VALIDATE_PUBLIC_DPO_CHECK_FOCUSED_DATASET_TESTS_PROTECTED_HASH_COMPARISON",
    "task_4_3_scope=FULL_PYTEST_RUFF_FOCUSED_MYPY_RECORDED_FULL_MYPY_BASELINE_OPENSPEC_TRUTH_LEAK_LINK_JSON_MANIFEST_PRIVATE_DIFF",
    "task_4_4_scope=FINAL_INDEPENDENT_SPEC_SECURITY_REVIEW",
    "task_4_5_scope=ARCHIVE_COMPLETE_POST_ARCHIVE_GATES",
)
HUMAN_BRIEF_FORBIDDEN_TAGS = {
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
HUMAN_BRIEF_URL_RESOURCE_ATTRIBUTES = {
    "src",
    "srcset",
    "action",
    "formaction",
    "poster",
    "data",
}
HUMAN_BRIEF_REQUIRED_HREFS = {
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

EXPECTED_REVIEW_PACK_TRUTH = {
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
EXPECTED_REVIEW_PACK_INDEX_ITEM = {
    "id": REVIEW_PACK_ID,
    "status": "DESIGN_ONLY",
    "phase": REVIEW_PACK_PHASE,
    "path": REVIEW_PACK_PATH,
    "manifest_id": None,
    "model_run_id": None,
    "boundary": (
        "PREPARATION_ONLY non-executable operator guidance over the canonical 29-field "
        "inventory; supplied bindings 0/29; authoritatively bound bindings 0; independent "
        "acquisition source UNAVAILABLE."
    ),
    "summary": (
        "DESIGN_ONLY; ACQUISITION_AND_BINDING_REVIEW_PACK_READY_EXECUTION_BLOCKED; review "
        "pack READY_FOR_EXTERNAL_COMPLETION only; candidate pack INCOMPLETE; protocol "
        "NOT_FROZEN; population NOT_MATERIALIZED; human acceptance NOT_RECORDED; "
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
EXPECTED_S0_INDEX_ITEM = {
    "id": "clean-compiler-model-evaluation-boundary-v1",
    "status": "BLOCKED",
    "phase": "materialize-and-freeze-clean-compiler-model-evaluation-boundary-v1",
    "path": (
        "reports/public-sample/clean-compiler-model-evaluation-boundary-v1/summary.json"
    ),
    "manifest_id": None,
    "model_run_id": None,
    "boundary": (
        "Archived S0 source/binding gate over the reviewed 29-field design; no "
        "independent clean acquisition frame or binding packet was supplied."
    ),
    "summary": (
        "BLOCKED; CLEAN_EVALUATION_BOUNDARY_MATERIALIZATION_BLOCKED; DESIGN_ONLY; "
        "0/29 bindings; protocol NOT_FROZEN; population NOT_MATERIALIZED; integrity "
        "NOT_CREATED; execution_readiness=false."
    ),
    "conclusion": (
        "No private registry, membership, seal, clean row, one-look access, "
        "compiler/model arm, training, prediction, A100 execution, experiment, causal "
        "identification, or improvement/readiness claim."
    ),
    "current_claim_allowed": False,
    "superseded_by": None,
}
EXPECTED_S0_MARKDOWN_ROW = (
    "| BLOCKED | materialize-and-freeze-clean-compiler-model-evaluation-boundary-v1 | "
    "archived S0 source/binding gate; no independent clean acquisition frame; 0/29 "
    "reviewed bindings | `CLEAN_EVALUATION_BOUNDARY_MATERIALIZATION_BLOCKED`; state "
    "`DESIGN_ONLY`, protocol `NOT_FROZEN`, population `NOT_MATERIALIZED`, integrity "
    "`NOT_CREATED`; both partitions not materialized and one-look unavailable; no "
    "private artifacts, clean rows, training, prediction, A100, experiment, or claim. | "
    "- | `reports/public-sample/clean-compiler-model-evaluation-boundary-v1/summary.json` |"
)
EXPECTED_REVIEW_PACK_MARKDOWN_ROW = (
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
EXPECTED_CONTEXT_S0_PARAGRAPH = (
    "The archived `materialize-and-freeze-clean-compiler-model-evaluation-boundary-v1` "
    "implementation reached the honest S0 blocked path because no independently "
    "authorized clean acquisition frame or reviewed 29-field binding packet exists. Its "
    "public evidence is `BLOCKED` with decision "
    "`CLEAN_EVALUATION_BOUNDARY_MATERIALIZATION_BLOCKED`, "
    "`current_readiness_state=DESIGN_ONLY`, bindings 0/29, protocol `NOT_FROZEN`, "
    "population `NOT_MATERIALIZED`, and boundary integrity `NOT_CREATED`. Neither "
    "partition was materialized; both one-look states are `NOT_AVAILABLE` with access "
    "count 0 and `consumed=false`. No private registry, membership, seal, clean row, "
    "compiler/model arm, training, prediction, A100 job, or experiment was created or run."
)
EXPECTED_CURRENT_STATUS_S0_BULLET = (
    "- Clean compiler/model evaluation boundary v1: `ARCHIVED` and honestly `BLOCKED` at "
    "`S0_SOURCE_OR_BINDING`; decision "
    "`CLEAN_EVALUATION_BOUNDARY_MATERIALIZATION_BLOCKED`; 0/29 bindings are complete, "
    "protocol is `NOT_FROZEN`, population is `NOT_MATERIALIZED`, integrity is "
    "`NOT_CREATED`, both partitions are `NOT_MATERIALIZED`, both one-look states are "
    "`NOT_AVAILABLE` with access count 0 and `consumed=false`, and "
    "`execution_readiness=false`. No private registry, membership, seal, clean row, "
    "compiler/model arm, training, prediction, A100 execution, or experiment exists."
)
EXPECTED_CURRENT_STATUS_S0_ROW = (
    "| [`reports/public-sample/clean-compiler-model-evaluation-boundary-v1/summary.json`]"
    "(../reports/public-sample/clean-compiler-model-evaluation-boundary-v1/summary.json) | "
    "Honest S0 blocked result: independent acquisition source unavailable and 29/29 "
    "bindings incomplete; no protocol freeze, population materialization, private "
    "membership, clean rows, one-look access, or experiment readiness. |"
)
REVIEW_PACK_NAV_TOKENS = (
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
)
REVIEW_PACK_BOUNDARY_PHRASES = (
    "review-pack readiness only",
    "not a reviewed or accepted candidate",
    "does not bind any input",
    "does not freeze a protocol",
    "does not materialize a population",
    "is not executable",
    "does not supersede the archived S0 blocker",
)


class _HumanBriefParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.start_tags: list[tuple[str, dict[str, str | None]]] = []
        self.headings: list[tuple[int, str]] = []
        self.anchors: list[tuple[str, str]] = []
        self.style_parts: list[str] = []
        self.visible_parts: list[str] = []
        self._heading_level: int | None = None
        self._heading_parts: list[str] = []
        self._anchor_href: str | None = None
        self._anchor_parts: list[str] = []
        self._in_style = False

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        attributes = dict(attrs)
        self.start_tags.append((tag, attributes))
        if re.fullmatch(r"h[1-6]", tag):
            self._heading_level = int(tag[1])
            self._heading_parts = []
        if tag == "a":
            self._anchor_href = attributes.get("href") or ""
            self._anchor_parts = []
        if tag == "style":
            self._in_style = True

    def handle_endtag(self, tag: str) -> None:
        if re.fullmatch(r"h[1-6]", tag) and self._heading_level is not None:
            self.headings.append(
                (self._heading_level, " ".join("".join(self._heading_parts).split()))
            )
            self._heading_level = None
            self._heading_parts = []
        if tag == "a" and self._anchor_href is not None:
            self.anchors.append(
                (self._anchor_href, " ".join("".join(self._anchor_parts).split()))
            )
            self._anchor_href = None
            self._anchor_parts = []
        if tag == "style":
            self._in_style = False

    def handle_data(self, data: str) -> None:
        if self._in_style:
            self.style_parts.append(data)
            return
        if self._heading_level is not None:
            self._heading_parts.append(data)
        if self._anchor_href is not None:
            self._anchor_parts.append(data)
        self.visible_parts.append(data)

    @property
    def css(self) -> str:
        return "".join(self.style_parts)

    @property
    def visible_text(self) -> str:
        return " ".join("".join(self.visible_parts).split())


def _parse_human_brief() -> tuple[str, _HumanBriefParser]:
    assert HUMAN_BRIEF.is_file()
    raw = HUMAN_BRIEF.read_bytes()
    text = raw.decode("utf-8")
    assert text.encode("utf-8") == raw
    parser = _HumanBriefParser()
    parser.feed(text)
    parser.close()
    return text, parser


def _load_checker() -> ModuleType:
    spec = importlib_util.spec_from_file_location("voice2task_current_truth_checker", CHECKER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load checker: {CHECKER}")
    module = importlib_util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


check_current_truth_surface = _load_checker()


def _one_line(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").split())


def test_current_truth_surface_checker_passes_with_no_active_change(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(check_current_truth_surface, "_active_openspec_changes", lambda: [])

    assert check_current_truth_surface.validate() == []


def test_current_truth_surface_checker_legacy_apply_mode_remains_exact(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        check_current_truth_surface,
        "_active_openspec_changes",
        lambda: [check_current_truth_surface.ACTIVE_CLEAN_BOUNDARY_CHANGE],
    )

    assert check_current_truth_surface.validate(allow_active_clean_boundary=True) == []


def test_current_truth_surface_checker_cli_rejects_retired_review_pack_apply_flag() -> None:
    result = subprocess.run(
        [sys.executable, str(CHECKER), "--allow-active-review-pack"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert result.stderr == ""
    assert result.stdout == (
        "current truth surface check failed:\n"
        f"- {RETIRED_REVIEW_PACK_FLAG_ERROR}\n"
    )
    assert check_current_truth_surface.REVIEW_PACK_PHASE == REVIEW_PACK_PHASE
    assert not hasattr(check_current_truth_surface, "ACTIVE_REVIEW_PACK_CHANGE")


@pytest.mark.parametrize(
    ("active_changes", "expected_errors"),
    (
        ([], [RETIRED_REVIEW_PACK_FLAG_ERROR]),
        (
            [REVIEW_PACK_PHASE],
            [
                RETIRED_REVIEW_PACK_FLAG_ERROR,
                (
                    "active OpenSpec changes must be empty after review pack archive, "
                    f"got ['{REVIEW_PACK_PHASE}']"
                ),
            ],
        ),
    ),
)
def test_current_truth_surface_checker_review_pack_mode_is_retired_and_zero_active(
    monkeypatch: pytest.MonkeyPatch,
    active_changes: list[str],
    expected_errors: list[str],
) -> None:
    monkeypatch.setattr(
        check_current_truth_surface,
        "_active_openspec_changes",
        lambda: active_changes,
    )

    assert (
        check_current_truth_surface.validate(allow_active_review_pack=True)
        == expected_errors
    )


def test_current_truth_surface_checker_review_pack_mode_rejects_wrong_change(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        check_current_truth_surface,
        "_active_openspec_changes",
        lambda: ["wrong-review-pack-change"],
    )

    errors = check_current_truth_surface.validate(allow_active_review_pack=True)

    assert errors == [
        RETIRED_REVIEW_PACK_FLAG_ERROR,
        "active OpenSpec changes must be empty after review pack archive, "
        "got ['wrong-review-pack-change']",
    ]


@pytest.mark.parametrize(
    "sibling_kind",
    ("directory", "regular-file", "symlink", "dangling-symlink"),
)
def test_current_truth_checker_blocks_actual_reserved_recovery_without_gc(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    sibling_kind: str,
) -> None:
    public_parent = tmp_path / "reports/public-sample"
    recovery = public_parent / f".review-pack-recovery-{'c' * 32}"
    public_parent.mkdir(parents=True)
    observed_payload_path: Path | None = None
    target: Path | None = None
    if sibling_kind == "directory":
        recovery.mkdir(mode=0o700)
        observed_payload_path = recovery / "marker"
        observed_payload_path.write_bytes(b"recovery-unchanged\n")
    elif sibling_kind == "regular-file":
        recovery.write_bytes(b"recovery-unchanged\n")
        observed_payload_path = recovery
    else:
        target = tmp_path / "recovery-target"
        if sibling_kind == "symlink":
            target.write_bytes(b"target-unchanged\n")
            observed_payload_path = target
        recovery.symlink_to(target)

    def stable_metadata(path: Path) -> tuple[int, ...]:
        observed = path.lstat()
        return (
            observed.st_dev,
            observed.st_ino,
            observed.st_mode,
            observed.st_uid,
            observed.st_gid,
            observed.st_nlink,
            observed.st_size,
            observed.st_mtime_ns,
            observed.st_ctime_ns,
        )

    before = recovery.lstat()
    before_metadata = stable_metadata(recovery)
    before_names = tuple(sorted(path.name for path in public_parent.iterdir()))
    before_payload = (
        observed_payload_path.read_bytes()
        if observed_payload_path is not None
        else None
    )
    before_payload_metadata = (
        stable_metadata(observed_payload_path)
        if observed_payload_path is not None
        else None
    )
    before_link = recovery.readlink() if recovery.is_symlink() else None
    monkeypatch.setattr(
        check_current_truth_surface,
        "REVIEW_PACK_PUBLIC_PARENT_PATH",
        public_parent,
        raising=False,
    )
    monkeypatch.setattr(
        check_current_truth_surface,
        "_active_openspec_changes",
        lambda: [],
    )

    errors = check_current_truth_surface.validate()

    assert errors == [
        "review pack current classification blocked by reserved recovery sibling"
    ]
    assert recovery.lstat().st_ino == before.st_ino
    assert stable_metadata(recovery) == before_metadata
    assert tuple(sorted(path.name for path in public_parent.iterdir())) == before_names
    if observed_payload_path is not None:
        assert observed_payload_path.read_bytes() == before_payload
        assert stable_metadata(observed_payload_path) == before_payload_metadata
    if recovery.is_symlink():
        assert recovery.readlink() == before_link
    if sibling_kind == "dangling-symlink":
        assert target is not None and not target.exists()


@pytest.mark.parametrize(
    "fault",
    (
        PermissionError("private-recovery-gate-canary"),
        OSError("private-recovery-gate-canary"),
    ),
)
def test_current_truth_checker_recovery_gate_fails_closed_when_parent_unreadable(
    monkeypatch: pytest.MonkeyPatch,
    fault: OSError,
) -> None:
    class UnreadableParent:
        def iterdir(self) -> object:
            raise fault

    monkeypatch.setattr(
        check_current_truth_surface,
        "REVIEW_PACK_PUBLIC_PARENT_PATH",
        UnreadableParent(),
    )
    monkeypatch.setattr(
        check_current_truth_surface,
        "_active_openspec_changes",
        lambda: [],
    )

    errors = check_current_truth_surface.validate()

    assert errors == ["review pack recovery gate unavailable"]


def test_review_publication_contract_docs_lock_trust_atime_and_legacy_boundaries() -> None:
    proposal = _one_line(REVIEW_PACK_PROPOSAL)
    design = _one_line(REVIEW_PACK_DESIGN)
    delta_spec = _one_line(REVIEW_PACK_DELTA_SPEC)

    assert "trusted, exclusive, cooperative same-EUID review-writer boundary" in proposal
    for text in (design, delta_spec):
        assert "trusted, exclusive, cooperative same-EUID" in text
        assert "access-time changes caused solely by descriptor reads" in text
    assert "Legacy regression acceptance is limited to its observable signature" in design
    assert "add or strengthen any legacy public-evidence threat/recovery/update guarantee" in (
        delta_spec
    )


def test_review_pack_human_brief_document_contract_and_section_order() -> None:
    text, parser = _parse_human_brief()

    assert text.startswith("<!doctype html>\n")
    assert '<html lang="zh-CN">' in text
    assert '<meta charset="utf-8">' in text
    assert '<meta name="viewport" content="width=device-width, initial-scale=1">' in text
    assert f"<title>{HUMAN_BRIEF_TITLE}</title>" in text
    for tag in ("html", "head", "body", "main"):
        assert text.count(f"</{tag}>") == 1
    assert HUMAN_BRIEF_STATUS in parser.visible_text
    assert [heading for level, heading in parser.headings if level == 1] == [
        "Review pack 已归档，但执行边界仍完全阻断"
    ]
    assert tuple(heading for level, heading in parser.headings if level == 2) == (
        HUMAN_BRIEF_H2
    )


def test_review_pack_human_brief_carries_exact_archive_and_boundary_truth() -> None:
    _text, parser = _parse_human_brief()
    visible = parser.visible_text

    for token in HUMAN_BRIEF_TRUTH_TOKENS:
        assert token in visible
    for token in (
        "template_lint_conforms=false",
        "future_lint_exit_0=CONFORMANCE_ONLY",
        "s0_evidence_status=BLOCKED",
        "s0_decision=CLEAN_EVALUATION_BOUNDARY_MATERIALIZATION_BLOCKED",
        "s0_superseded_by=null",
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
        "full_pytest_status=1260_PASSED",
        "full_pytest_failure_scope=NONE",
        "full_pytest_failure_reason=NONE",
        "challenge_hash_policy_rows_template_disjoint=PASS",
        "default_zero_active_truth_status=PASS",
        "active_openspec_changes=0",
        "main_spec_sync=PASS_7_REQUIREMENTS_29_SCENARIOS",
        "task_4_3_independent_gate_reviewer=PASS",
        "task_4_4_baseexception_tests=7 passed",
        "task_4_4_private_reader_tests=6 passed",
        "task_4_4_adapter_cli_tests=7 passed",
        "task_4_4_clean_chain_tests=4 passed",
        "task_4_4_targeted_tests=24 passed",
        "task_4_4_must_fixes_resolved=3/3",
        "task_4_4_spec_truth_reviewer=PASS",
        "task_4_4_code_security_reviewer=PASS",
        "final_independent_review_status=PASS_TASK_4_4",
        "openspec_strict=15/15",
        "leak_link_diff_status=PASS",
        "publication_initial_create=PASS",
        "publication_second_exact_noop=PASS",
        "recovery_siblings=0",
        "s0_five_hashes=UNCHANGED",
        "canonical_private_root=ABSENT_IGNORED_UNTRACKED",
        "prior_independent_reviews=PASS",
    ):
        assert token in visible
    assert re.search(r"(?<![A-Za-z0-9_])mypy_status=PASS", visible) is None


def test_review_pack_human_brief_separates_authority_after_archive() -> None:
    _text, parser = _parse_human_brief()
    visible = parser.visible_text
    tasks_text = REVIEW_PACK_TASKS.read_text(encoding="utf-8")

    required_boundaries = (
        "READY_FOR_EXTERNAL_COMPLETION means only that template, schema, catalog, and "
        "checklist are externally completable.",
        "not candidate reviewed or accepted",
        "source not acquired",
        "bindings not effective",
        "protocol not frozen",
        "population not materialized",
        "rows not authored",
        "experiment not eligible",
        "no model improvement",
        "trusted, exclusive, cooperative same-EUID writer assumption",
        "account/process-boundary compromise",
        "descriptor-read access-time changes 是 no-mutation contract 唯一排除项",
        "recovery sibling 永不自动 GC",
        "task_4_1_status=COMPLETE",
        "task_4_2_status=COMPLETE",
        "task_4_3_status=COMPLETE_WITH_EXPLICIT_LIFECYCLE_AND_BASELINE_LIMITATIONS",
        "task_4_4_status=COMPLETE_AFTER_3_MUST_FIXES_RESOLVED_AND_TWO_INDEPENDENT_REVIEWS_PASS",
        "openspec_progress=20/20",
        "task_4_5_archive_status=COMPLETE",
        "full_pytest_status=1260_PASSED",
        "full_pytest_failure_scope=NONE",
        "full_pytest_failure_reason=NONE",
        "challenge_hash_policy_rows_template_disjoint=PASS",
        "focused_mypy_status=PASS_4_FILES_0_ISSUES",
        "full_mypy_rerun=39_ERRORS_IN_5_FILES_CHECKED_31_SOURCE_FILES",
        "full_mypy_status=RECORDED_BASELINE_PRESERVED",
        "full_mypy_source_coverage=31_CURRENT_VS_28_PRIOR_RECORDED",
        "default_zero_active_truth_status=PASS",
        "active_openspec_changes=0",
        (
            "archive_path=openspec/changes/archive/"
            "2026-07-12-prepare-clean-evaluation-acquisition-and-binding-review-pack-v1"
        ),
        "main_spec_sync=PASS_7_REQUIREMENTS_29_SCENARIOS",
        "task_4_3_independent_gate_reviewer=PASS",
        "task_4_4_must_fixes_resolved=3/3",
        "task_4_4_spec_truth_reviewer=PASS",
        "task_4_4_code_security_reviewer=PASS",
        "final_independent_review_status=PASS_TASK_4_4",
        *HUMAN_BRIEF_NEXT_STEP_TOKENS,
        (
            "Task 4.1：已完成两组 publication acceptance、CLI/lint、current/recovery "
            "gate 与 legacy observable regression。"
        ),
        (
            "Task 4.2：已在临时目录完成 public build，并通过 validate --public、dpo-check、"
            "focused dataset tests 与 15/15 protected-hash comparison；临时输出已清理。"
        ),
        (
            "Task 4.3：历史检查点为 1241 passed、3 个 active-change archive-guard "
            "失败；Task 4.5 归档后全量结果为 1260 passed，生命周期守卫已关闭，"
            "full-Mypy baseline 保持不变。"
        ),
        "Task 4.4：3 个 Must Fix 已解决，两组独立复核均 PASS。",
        (
            "归档已完成；不自动创建下一 change。任何未来 acquisition/binding 阶段都需要"
            "一个经单独审阅的新 change，以及真实的外部输入与接受记录。"
        ),
    )
    for boundary in required_boundaries:
        assert boundary in visible

    assert "- [x] 4.3 Run full `PYTHONPATH=src pytest -q`" in tasks_text
    assert "- [x] 4.4 Complete independent read-only spec and code/security reviews" in (
        tasks_text
    )
    assert "- [x] 4.5 Archive only after the user separately authorizes archive" in tasks_text

    for forbidden in (
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
        "task_4_2_status=PENDING",
        "task_4_3_status=PENDING",
        "task_4_4_status=PENDING",
        "final_independent_review_status=PENDING_TASK_4_4",
        "openspec_progress=18/20",
        "full_pytest_status=PENDING_TASK_4_3",
        "full_pytest_status=1241_PASSED_3_EXPECTED_ACTIVE_CHANGE_ARCHIVE_GUARD_FAILURES",
        "full_mypy_rerun=PENDING_TASK_4_3",
        "full_pytest_status=PASS",
        "full_mypy_status=PASS",
    ):
        assert forbidden not in visible


def test_review_pack_human_brief_is_accessible_offline_and_repo_linked() -> None:
    _text, parser = _parse_human_brief()
    tags = [tag for tag, _attrs in parser.start_tags]
    ids = {
        element_id
        for _tag, attrs in parser.start_tags
        if (element_id := attrs.get("id")) is not None
    }
    main_tags = [attrs for tag, attrs in parser.start_tags if tag == "main"]
    nav_tags = [attrs for tag, attrs in parser.start_tags if tag == "nav"]

    assert main_tags == [{"id": "brief-main"}]
    assert len(nav_tags) == 1
    assert nav_tags[0].get("aria-label") == "简报目录"
    assert parser.anchors[0] == ("#brief-main", "跳到主要内容")
    assert not HUMAN_BRIEF_FORBIDDEN_TAGS.intersection(tags)
    assert all("style" not in attrs for _tag, attrs in parser.start_tags)
    assert all(
        not any(attribute.lower().startswith("on") for attribute in attrs)
        for _tag, attrs in parser.start_tags
    )
    assert all(
        not HUMAN_BRIEF_URL_RESOURCE_ATTRIBUTES.intersection(attrs)
        for _tag, attrs in parser.start_tags
    )
    assert tags.count("style") == 1

    heading_levels = [level for level, _heading in parser.headings]
    assert heading_levels[0] == 1
    assert all(
        current <= previous + 1
        for previous, current in zip(heading_levels, heading_levels[1:], strict=False)
    )

    hrefs = {href for href, _text in parser.anchors if not href.startswith("#")}
    assert HUMAN_BRIEF_REQUIRED_HREFS.issubset(hrefs)
    for href, anchor_text in parser.anchors:
        assert anchor_text
        assert anchor_text.lower() not in {"here", "click here", "link", "链接"}
        if href.startswith("#"):
            assert href[1:] in ids
            continue
        parts = urlsplit(href)
        assert parts.scheme == ""
        assert parts.netloc == ""
        assert not href.startswith("/")
        target = (HUMAN_BRIEF.parent / parts.path).resolve()
        target.relative_to(REPO_ROOT.resolve())
        assert target.exists()

    css = parser.css
    colors = {color.lower() for color in re.findall(r"#[0-9a-fA-F]{6}", css)}
    assert colors == {"#171717", "#404040", "#a16207", "#ffffff", "#e8ecf0"}
    for fragment in (
        "max-width: 760px",
        "overflow-wrap: anywhere",
        ":focus-visible",
        "text-decoration: underline",
        "@media (max-width: 600px)",
        "@media print",
        "@media (prefers-reduced-motion: reduce)",
        "font-family:",
    ):
        assert fragment in css
    lowered_css = css.lower()
    assert "grid-template-columns" not in lowered_css
    assert re.search(r"\bcolumns\s*:\s*2\b", lowered_css) is None
    for forbidden in (
        "gradient",
        "purple",
        "@import",
        "http://",
        "https://",
        "url(",
        "@font-face",
    ):
        assert forbidden not in lowered_css
    assert scan_paths([HUMAN_BRIEF]).ok is True


def test_current_truth_checker_requires_and_validates_review_pack_human_brief() -> None:
    assert check_current_truth_surface.REVIEW_PACK_HUMAN_BRIEF_PATH == HUMAN_BRIEF
    errors: list[str] = []

    check_current_truth_surface._check_review_pack_human_brief(errors)

    assert errors == []
    text = HUMAN_BRIEF.read_text(encoding="utf-8")
    for original, replacement in (
        ("task_4_1_status=COMPLETE", "task_4_1_status=PENDING"),
        ("task_4_1_group_a_tests=39 passed", "task_4_1_group_a_tests=38 passed"),
        ("recovery_gate_fail_closed=PASS", "recovery_gate_fail_closed=FAIL"),
        (
            "task_4_1_independent_reviewer=PASS",
            "task_4_1_independent_reviewer=PENDING",
        ),
        ("task_4_2_status=COMPLETE", "task_4_2_status=PENDING"),
        ("task_4_2_temp_build=PASS", "task_4_2_temp_build=FAIL"),
        ("public_build_seed_rows=247", "public_build_seed_rows=246"),
        ("public_build_sft_rows=696", "public_build_sft_rows=695"),
        ("public_build_dpo_pairs=2100", "public_build_dpo_pairs=2099"),
        ("public_validate=PASS_0_FAILURES", "public_validate=FAIL_1_FAILURE"),
        ("public_dpo_check_pairs=2100", "public_dpo_check_pairs=2099"),
        ("task_4_2_focused_tests=88 passed", "task_4_2_focused_tests=87 passed"),
        ("protected_hashes_unchanged=15/15", "protected_hashes_unchanged=14/15"),
        ("task_4_2_temp_output=CLEANED", "task_4_2_temp_output=PRESENT"),
        (
            "task_4_2_independent_reviewer=PASS",
            "task_4_2_independent_reviewer=PENDING",
        ),
        (
            "task_4_3_status=COMPLETE_WITH_EXPLICIT_LIFECYCLE_AND_BASELINE_LIMITATIONS",
            "task_4_3_status=PENDING",
        ),
        (
            "task_4_4_status=COMPLETE_AFTER_3_MUST_FIXES_RESOLVED_AND_TWO_INDEPENDENT_REVIEWS_PASS",
            "task_4_4_status=PENDING",
        ),
        ("openspec_progress=20/20", "openspec_progress=19/20"),
        (
            "full_pytest_status=1260_PASSED",
            "full_pytest_status=1257_PASSED_3_EXPECTED_ACTIVE_CHANGE_ARCHIVE_GUARD_FAILURES",
        ),
        (
            "full_pytest_failure_scope=NONE",
            "full_pytest_failure_scope=TEST_RECOVERED_ADAPTER_CHALLENGE_EVALUATION_ONLY",
        ),
        (
            "full_pytest_failure_reason=NONE",
            "full_pytest_failure_reason=ACTIVE_CHANGE_CONFLICTING_ACTIVE_CHANGES",
        ),
        (
            "challenge_hash_policy_rows_template_disjoint=PASS",
            "challenge_hash_policy_rows_template_disjoint=FAIL",
        ),
        (
            "focused_mypy_status=PASS_4_FILES_0_ISSUES",
            "focused_mypy_status=PASS",
        ),
        (
            "full_mypy_rerun=39_ERRORS_IN_5_FILES_CHECKED_31_SOURCE_FILES",
            "full_mypy_rerun=PENDING_TASK_4_3",
        ),
        (
            "full_mypy_status=RECORDED_BASELINE_PRESERVED",
            "full_mypy_status=PASS",
        ),
        (
            "full_mypy_source_coverage=31_CURRENT_VS_28_PRIOR_RECORDED",
            "full_mypy_source_coverage=28_CURRENT_VS_28_PRIOR_RECORDED",
        ),
        (
            "default_zero_active_truth_status=PASS",
            "default_zero_active_truth_status=EXPECTED_RED_UNTIL_SEPARATELY_AUTHORIZED_ARCHIVE",
        ),
        ("active_openspec_changes=0", "active_openspec_changes=1"),
        (
            "main_spec_sync=PASS_7_REQUIREMENTS_29_SCENARIOS",
            "main_spec_sync=PENDING",
        ),
        (
            "task_4_5_archive_status=COMPLETE",
            "task_4_5_archive_status=SEPARATE_AUTHORIZATION_REQUIRED",
        ),
        (
            "task_4_5_scope=ARCHIVE_COMPLETE_POST_ARCHIVE_GATES",
            "task_4_5_scope=ARCHIVE_SEPARATE_AUTHORIZATION_ONLY",
        ),
        (
            "task_4_3_independent_gate_reviewer=PASS",
            "task_4_3_independent_gate_reviewer=PENDING",
        ),
        ("task_4_4_must_fixes_resolved=3/3", "task_4_4_must_fixes_resolved=2/3"),
        (
            "task_4_4_spec_truth_reviewer=PASS",
            "task_4_4_spec_truth_reviewer=PENDING",
        ),
        (
            "task_4_4_code_security_reviewer=PASS",
            "task_4_4_code_security_reviewer=PENDING",
        ),
        (
            "final_independent_review_status=PASS_TASK_4_4",
            "final_independent_review_status=PENDING_TASK_4_4",
        ),
    ):
        drift_errors: list[str] = []
        check_current_truth_surface._check_review_pack_human_brief(
            drift_errors,
            html_text=text.replace(original, replacement),
        )
        assert any(original in error for error in drift_errors), original


@pytest.mark.parametrize(
    ("original", "replacement", "error_fragment"),
    (
        (
            HUMAN_BRIEF_STATUS,
            "ARCHIVED · REVIEW PACK READY ONLY · EXECUTION READY",
            "archived status",
        ),
        (
            "human_acceptance_status=NOT_RECORDED",
            "human_acceptance_status=RECORDED",
            "human_acceptance_status=NOT_RECORDED",
        ),
        (
            'href="../../CONTEXT.md"',
            'href="../../../../outside-review-pack"',
            "link target escapes repository",
        ),
        (
            'href="../../CONTEXT.md"',
            'href="https://example.test/context"',
            "external or absolute link forbidden",
        ),
        (
            'href="#brief-main"',
            'href="#missing-main"',
            "fragment target missing",
        ),
        (
            "</body>",
            '<iframe src="https://example.test/review"></iframe>\n</body>',
            "forbidden element: iframe",
        ),
        (
            "<body>",
            '<body onload="alert(1)">',
            "event handler attribute",
        ),
        (
            "--accent: #A16207;",
            "--accent: #404040;",
            "exact five-color palette",
        ),
        (
            "@media (prefers-reduced-motion: reduce)",
            "@media (min-width: 12345px)",
            "reduced-motion",
        ),
        (
            "</style>",
            "main { grid-template-columns: 1fr 1fr; }\n</style>",
            "must remain single-column",
        ),
        (
            "</html>",
            "",
            "closing skeleton",
        ),
    ),
)
def test_current_truth_checker_rejects_human_brief_drift(
    original: str,
    replacement: str,
    error_fragment: str,
) -> None:
    text, _parser = _parse_human_brief()
    assert original in text
    errors: list[str] = []

    check_current_truth_surface._check_review_pack_human_brief(
        errors,
        html_text=text.replace(original, replacement, 1),
    )

    assert any(error_fragment in error for error in errors)


def test_current_truth_checker_requires_authority_tokens_inside_footer() -> None:
    text, _parser = _parse_human_brief()
    mutated = text.replace("<footer>", "<div>", 1).replace(
        "</footer>",
        "</div>",
        1,
    )
    assert "human_brief_role=NAVIGATION_SUMMARY_ONLY" in mutated
    assert (
        "authoritative_sources=OPENSPEC_RAW_SUMMARY_MANIFEST_TESTS_VALIDATION"
        in mutated
    )
    errors: list[str] = []

    check_current_truth_surface._check_review_pack_human_brief(
        errors,
        html_text=mutated,
    )

    assert any("footer authority drift" in error for error in errors)


def test_current_truth_checker_rejects_unqualified_mypy_pass_marker() -> None:
    text, _parser = _parse_human_brief()
    qualified = text.replace(
        "<code>mypy_status=PASS</code>",
        "<code>focused_mypy_status=PASS</code>",
    )
    assert "focused_mypy_status=PASS" in qualified
    mutated = qualified.replace("focused_mypy_status=PASS", "mypy_status=PASS", 1)
    errors: list[str] = []

    check_current_truth_surface._check_review_pack_human_brief(
        errors,
        html_text=mutated,
    )

    assert any("unqualified mypy pass marker" in error for error in errors)


def test_current_truth_checker_rejects_every_forbidden_resource_surface() -> None:
    text, _parser = _parse_human_brief()

    for tag in sorted(HUMAN_BRIEF_FORBIDDEN_TAGS):
        mutated = text.replace("</body>", f"<{tag}></{tag}>\n</body>", 1)
        errors: list[str] = []
        check_current_truth_surface._check_review_pack_human_brief(
            errors,
            html_text=mutated,
        )
        assert any(f"forbidden element: {tag}" in error for error in errors), tag

    for attribute in sorted(HUMAN_BRIEF_URL_RESOURCE_ATTRIBUTES):
        mutated = text.replace(
            "</body>",
            f'<div {attribute}="https://example.test/resource"></div>\n</body>',
            1,
        )
        errors = []
        check_current_truth_surface._check_review_pack_human_brief(
            errors,
            html_text=mutated,
        )
        assert any(
            f"forbidden URL resource attribute: {attribute}" in error
            for error in errors
        ), attribute


def test_evidence_index_classifies_current_superseded_blocked_and_raw_inputs() -> None:
    payload = json.loads(INDEX_JSON.read_text(encoding="utf-8"))
    assert payload["generated_at"] == "2026-07-11"
    items = payload["items"]
    by_id = {item["id"]: item for item in items}

    assert by_id["internal-contract-v2-core"]["status"] == "CURRENT"
    assert by_id["internal-contract-v2-core"]["path"] == "reports/public-sample/internal-contract-v2-core/summary.json"
    assert by_id["contract-v2-projection-rerun"]["status"] == "CURRENT"
    assert by_id["step-matched-canonical-slot-ablation"]["status"] == "CURRENT"
    assert by_id["contract-v2-projection-blocked"]["status"] == "BLOCKED"
    assert by_id["contract-v2-projection-blocked"]["superseded_by"] == "contract-v2-projection-rerun"
    assert by_id["step-matched-projection-raw-inputs"]["status"] == "RAW_INPUT"
    assert by_id["canonical-slot-paired-sft-ablation"]["status"] == "SUPERSEDED"
    assert by_id["canonical-slot-paired-sft-ablation"]["superseded_by"] == "step-matched-canonical-slot-ablation"
    assert by_id["scaled-clarify-slot-boundary-candidate-design"]["status"] == "DESIGN_ONLY"
    assert by_id["lockbox-v1-final-evaluation"]["status"] == "CURRENT"
    assert by_id["lockbox-v1-final-evaluation"]["path"] == (
        "reports/lockbox-v1/final-evaluation/comparison.json"
    )
    assert by_id["must-fix-phase-3-lockbox-lineage-guard"]["status"] == "SUPERSEDED"
    assert by_id["must-fix-phase-3-lockbox-lineage-guard"]["superseded_by"] == (
        "lockbox-v1-final-evaluation"
    )
    assert by_id["public-split-integrity-audit"]["status"] == "CURRENT"
    assert by_id["clean-compiler-model-evaluation-boundary-v1"]["status"] == "BLOCKED"
    assert by_id["clean-compiler-model-evaluation-boundary-v1"]["path"] == (
        "reports/public-sample/clean-compiler-model-evaluation-boundary-v1/summary.json"
    )
    assert by_id["clean-compiler-model-evaluation-boundary-v1"]["current_claim_allowed"] is False
    assert by_id["clean-matched-causal-evidence-design"]["status"] == "DESIGN_ONLY"
    assert all((REPO_ROOT / item["path"]).exists() for item in items)


def test_review_pack_summary_preserves_exact_preparation_only_truth() -> None:
    summary = json.loads(REVIEW_PACK_SUMMARY.read_text(encoding="utf-8"))

    assert {field: summary[field] for field in EXPECTED_REVIEW_PACK_TRUTH} == (
        EXPECTED_REVIEW_PACK_TRUTH
    )


def test_review_pack_index_item_is_exact_and_follows_unsuperseded_s0() -> None:
    payload = json.loads(INDEX_JSON.read_text(encoding="utf-8"))
    assert payload["generated_at"] == "2026-07-11"
    items = payload["items"]
    by_id = {item["id"]: item for item in items}

    review_item = by_id[REVIEW_PACK_ID]
    assert tuple(review_item) == tuple(EXPECTED_REVIEW_PACK_INDEX_ITEM)
    assert review_item == EXPECTED_REVIEW_PACK_INDEX_ITEM
    assert by_id["clean-compiler-model-evaluation-boundary-v1"] == EXPECTED_S0_INDEX_ITEM

    ids = [item["id"] for item in items]
    s0_index = ids.index("clean-compiler-model-evaluation-boundary-v1")
    assert ids[s0_index : s0_index + 3] == [
        "clean-compiler-model-evaluation-boundary-v1",
        REVIEW_PACK_ID,
        "clean-matched-causal-evidence-design",
    ]


def test_review_pack_markdown_is_first_design_only_row_and_preserves_s0_row() -> None:
    markdown = INDEX_MD.read_text(encoding="utf-8")
    current = markdown.split("## Historical Training Runs", 1)[0]
    blocked = markdown.split("## Blocked Runs", 1)[1].split(
        "## Design-Only Evidence", 1
    )[0]
    design = markdown.split("## Design-Only Evidence", 1)[1].split(
        "## Raw/Reproducibility Inputs", 1
    )[0]
    design_rows = [line for line in design.splitlines() if line.startswith("| DESIGN_ONLY |")]

    assert REVIEW_PACK_PHASE not in current
    assert REVIEW_PACK_PHASE not in blocked
    assert design.count(REVIEW_PACK_PHASE) == 1
    assert design_rows[0] == EXPECTED_REVIEW_PACK_MARKDOWN_ROW
    assert markdown.count(EXPECTED_S0_MARKDOWN_ROW) == 1


def test_review_pack_navigation_is_exact_and_preserves_s0_text() -> None:
    context = CONTEXT.read_text(encoding="utf-8")
    current_status = CURRENT_STATUS.read_text(encoding="utf-8")

    assert context.count(EXPECTED_CONTEXT_S0_PARAGRAPH) == 1
    assert current_status.count(EXPECTED_CURRENT_STATUS_S0_BULLET) == 1
    assert current_status.count(EXPECTED_CURRENT_STATUS_S0_ROW) == 1
    for document in (context, current_status):
        for token in REVIEW_PACK_NAV_TOKENS:
            assert token in document
        for phrase in REVIEW_PACK_BOUNDARY_PHRASES:
            assert phrase in document

    context_target = REVIEW_PACK_PATH
    current_status_target = f"../{REVIEW_PACK_PATH}"
    assert context_target in check_current_truth_surface._markdown_links(context)
    assert current_status_target in check_current_truth_surface._markdown_links(current_status)
    assert (CONTEXT.parent / context_target).resolve() == REVIEW_PACK_SUMMARY.resolve()
    assert (CURRENT_STATUS.parent / current_status_target).resolve() == (
        REVIEW_PACK_SUMMARY.resolve()
    )


def test_markdown_index_moves_lockbox_lineage_history_out_of_blocked_table() -> None:
    markdown = INDEX_MD.read_text(encoding="utf-8")
    current, remainder = markdown.split("## Historical Training Runs", 1)
    superseded, blocked = remainder.split("## Superseded Evidence", 1)[1].split("## Blocked Runs", 1)
    blocked_table = blocked.split("## Design-Only Evidence", 1)[0]

    assert "lockbox-v1-final-evaluation" in current
    assert "must-fix-phase-3-lockbox-lineage-guard" in superseded
    assert "must-fix-phase-3-lockbox-lineage-guard" not in blocked_table
    assert "materialize-and-freeze-clean-compiler-model-evaluation-boundary-v1" in blocked_table


def test_clean_evaluation_boundary_s0_truth_is_guarded() -> None:
    summary = json.loads(CLEAN_BOUNDARY_SUMMARY.read_text(encoding="utf-8"))
    assert summary["evidence_status"] == "BLOCKED"
    assert summary["decision"] == "CLEAN_EVALUATION_BOUNDARY_MATERIALIZATION_BLOCKED"
    assert summary["blocked_stage"] == "S0_SOURCE_OR_BINDING"
    assert summary["current_readiness_state"] == "DESIGN_ONLY"
    assert summary["maximum_state_this_change"] == "DESIGN_ONLY"
    assert summary["binding_counts"] == {"total": 29, "bound": 0, "unbound": 29}
    assert summary["protocol_freeze_status"] == "NOT_FROZEN"
    assert summary["clean_population_status"] == "NOT_MATERIALIZED"
    assert summary["boundary_integrity_status"] == "NOT_CREATED"
    assert summary["execution_readiness"] is False
    assert all(value is False for value in summary["artifacts"].values())
    assert all(value is False for value in summary["mutations"].values())
    assert all(value is False for value in summary["access_and_runs"].values())
    assert all(value is False for value in summary["claims"].values())


def test_clean_evaluation_boundary_guard_rejects_status_drift() -> None:
    items = json.loads(INDEX_JSON.read_text(encoding="utf-8"))["items"]
    summary = json.loads(CLEAN_BOUNDARY_SUMMARY.read_text(encoding="utf-8"))
    drifted = deepcopy(summary)
    drifted["execution_readiness"] = True
    errors: list[str] = []

    check_current_truth_surface._check_clean_evaluation_boundary(
        errors,
        items,
        INDEX_MD.read_text(encoding="utf-8"),
        summary=drifted,
    )

    assert any("execution_readiness" in error for error in errors)


@pytest.mark.parametrize(
    ("surface", "field", "value", "error_fragment"),
    (
        ("review_item", "status", "CURRENT", "index status"),
        (
            "summary",
            "human_acceptance_status",
            "RECORDED",
            "human_acceptance_status",
        ),
        ("summary", "freeze_authorized", True, "freeze_authorized"),
        ("summary", "execution_readiness", True, "execution_readiness"),
        ("s0_item", "superseded_by", REVIEW_PACK_ID, "superseded_by"),
    ),
)
def test_review_pack_guard_rejects_lifecycle_or_s0_drift(
    surface: str,
    field: str,
    value: object,
    error_fragment: str,
) -> None:
    items = deepcopy(json.loads(INDEX_JSON.read_text(encoding="utf-8"))["items"])
    summary = json.loads(REVIEW_PACK_SUMMARY.read_text(encoding="utf-8"))
    if surface == "summary":
        summary[field] = value
    else:
        item_id = (
            REVIEW_PACK_ID
            if surface == "review_item"
            else "clean-compiler-model-evaluation-boundary-v1"
        )
        next(item for item in items if item["id"] == item_id)[field] = value
    errors: list[str] = []

    check_current_truth_surface._check_review_pack_evidence(
        errors,
        items,
        INDEX_MD.read_text(encoding="utf-8"),
        summary=summary,
    )

    assert any(error_fragment in error for error in errors)


@pytest.mark.parametrize(
    ("item_id", "mutation", "expected_error"),
    (
        (REVIEW_PACK_ID, "duplicate", "review pack index id must appear exactly once"),
        (REVIEW_PACK_ID, "missing", "review pack index id must appear exactly once"),
        (
            "clean-compiler-model-evaluation-boundary-v1",
            "duplicate",
            "archived S0 index id must appear exactly once",
        ),
        (
            "clean-compiler-model-evaluation-boundary-v1",
            "missing",
            "archived S0 index id must appear exactly once",
        ),
    ),
)
def test_review_pack_guard_requires_exact_unique_review_and_s0_ids(
    item_id: str,
    mutation: str,
    expected_error: str,
) -> None:
    items = deepcopy(json.loads(INDEX_JSON.read_text(encoding="utf-8"))["items"])
    matching = next(item for item in items if item["id"] == item_id)
    if mutation == "duplicate":
        items.append(deepcopy(matching))
    else:
        items = [item for item in items if item["id"] != item_id]
    errors: list[str] = []

    check_current_truth_surface._check_review_pack_evidence(
        errors,
        items,
        INDEX_MD.read_text(encoding="utf-8"),
    )

    assert expected_error in errors


def test_markdown_links_resolve_relative_to_the_source_document() -> None:
    assert check_current_truth_surface._path_from_markdown_link(
        "evidence-index.json",
        INDEX_MD,
    ) == INDEX_JSON.resolve()
    assert check_current_truth_surface._path_from_markdown_link(
        f"../{REVIEW_PACK_PATH}",
        CURRENT_STATUS,
    ) == REVIEW_PACK_SUMMARY.resolve()
    errors: list[str] = []
    for path in (INDEX_MD, CURRENT_STATUS, CONTEXT):
        check_current_truth_surface._check_doc_links(errors, path)
    assert errors == []


def test_markdown_link_guard_rejects_repo_escape_without_throwing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        check_current_truth_surface,
        "_markdown_links",
        lambda text: ["../../../../outside-review-pack"],
    )
    errors: list[str] = []

    check_current_truth_surface._check_doc_links(errors, INDEX_MD)

    assert errors == [
        "reports/public-sample/EVIDENCE_INDEX.md link target escapes repository: "
        "../../../../outside-review-pack"
    ]


def test_lockbox_index_guard_rejects_raw_artifact_metric_drift() -> None:
    payload = json.loads(INDEX_JSON.read_text(encoding="utf-8"))
    items = payload["items"]
    artifacts = check_current_truth_surface._load_lockbox_artifacts()
    drifted = deepcopy(artifacts)
    drifted["comparison"]["metrics"]["base"]["contract_exact_match"] = 0.5
    errors: list[str] = []

    check_current_truth_surface._check_lockbox_evidence(
        errors,
        items,
        INDEX_MD.read_text(encoding="utf-8"),
        artifacts=drifted,
    )

    assert any("base metrics" in error for error in errors)


def test_lockbox_index_guard_rejects_markdown_aggregate_drift() -> None:
    items = json.loads(INDEX_JSON.read_text(encoding="utf-8"))["items"]
    markdown = INDEX_MD.read_text(encoding="utf-8").replace("0.0083", "0.9999", 1)
    errors: list[str] = []

    check_current_truth_surface._check_lockbox_evidence(errors, items, markdown)

    assert any("Markdown" in error and "aggregate" in error for error in errors)


def test_lockbox_index_guard_rejects_json_boundary_count_and_protocol_drift() -> None:
    items = deepcopy(json.loads(INDEX_JSON.read_text(encoding="utf-8"))["items"])
    final_item = next(item for item in items if item["id"] == "lockbox-v1-final-evaluation")
    final_item["boundary"] = "Frozen 999-row / 120-family lockbox-v1, one-look oracle protocol."
    errors: list[str] = []

    check_current_truth_surface._check_lockbox_evidence(
        errors,
        items,
        INDEX_MD.read_text(encoding="utf-8"),
    )

    assert any("JSON index boundary" in error for error in errors)


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
        "INTERNAL_V2_CORE_READY_RENDERER_PARTIAL",
        "99.77%",
        "5 unsupported",
        "analyze-slot-error-mechanisms-and-design-slot-representation",
        "strict exact remains canonical",
        "DEVELOPMENT_ONLY_SPENT",
        "JSON type-strict",
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
    assert scan_paths(
        [
            README,
            README_EN,
            CONTEXT,
            CURRENT_STATUS,
            INDEX_JSON,
            INDEX_MD,
            REVIEW_PACK_SUMMARY,
        ]
    ).ok is True
