from __future__ import annotations

import hashlib
import unicodedata
from dataclasses import asdict, dataclass
from typing import Any, Literal

VERIFIED_EXACT_UNIQUE = "VERIFIED_EXACT_UNIQUE"
VERIFIED_NORMALIZED_UNIQUE = "VERIFIED_NORMALIZED_UNIQUE"
AMBIGUOUS_MULTIPLE_MATCHES = "AMBIGUOUS_MULTIPLE_MATCHES"
AMBIGUOUS_NORMALIZATION_COLLISION = "AMBIGUOUS_NORMALIZATION_COLLISION"
NOT_FOUND = "NOT_FOUND"
UNSUPPORTED_VALUE_TYPE = "UNSUPPORTED_VALUE_TYPE"
OUT_OF_SCOPE = "OUT_OF_SCOPE"
INVALID_INPUT = "INVALID_INPUT"

STATUS_VALUES = (
    VERIFIED_EXACT_UNIQUE,
    VERIFIED_NORMALIZED_UNIQUE,
    AMBIGUOUS_MULTIPLE_MATCHES,
    AMBIGUOUS_NORMALIZATION_COLLISION,
    NOT_FOUND,
    UNSUPPORTED_VALUE_TYPE,
    OUT_OF_SCOPE,
    INVALID_INPUT,
)
VERIFIED_STATUS_VALUES = {VERIFIED_EXACT_UNIQUE, VERIFIED_NORMALIZED_UNIQUE}

MatchKind = Literal["exact", "normalized", "none"]
Provenance = Literal["system_verified_source", "unresolved"]
NORMALIZATION_COLLISION_RULE = "nfkc_casefold_strip_space_punct_symbol"


@dataclass(frozen=True)
class CopyBackedScope:
    task_type: str
    route: str
    slot_path: str
    enabled: bool
    policy_version: str = "copy-backed-slot-verification-slice-v1"
    evidence_reference: str | None = None
    exclusion_reason: str | None = None

    @property
    def key(self) -> str:
        return f"{self.task_type}:{self.route}:{self.slot_path}"


@dataclass(frozen=True)
class SourceSpan:
    start: int
    end: int
    text: str
    source_text_hash: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CopyBackedVerificationResult:
    scope: CopyBackedScope
    status: str
    match_kind: MatchKind
    provenance: Provenance
    source_span: SourceSpan | None
    candidate_span_count: int
    normalization_rule: str | None
    fail_closed: bool
    reason: str

    @property
    def verified(self) -> bool:
        return self.status in VERIFIED_STATUS_VALUES

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["scope_key"] = self.scope.key
        return value


@dataclass(frozen=True)
class NormalizedEquivalentCollisionAudit:
    status: str
    raw_exact_span_count: int
    normalized_equivalent_span_count: int
    normalization_rule: str | None
    source_attested_exact: bool
    fail_closed: bool
    ambiguous_mapping: bool
    raw_exact_spans: list[dict[str, int | str]]
    normalized_equivalent_spans: list[dict[str, int | str]]
    source_text_hash: str | None
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def source_text_hash(source_text: str) -> str:
    return hashlib.sha256(source_text.encode("utf-8")).hexdigest()


def verify_source_span(source_text: str, span: SourceSpan) -> bool:
    if span.start < 0 or span.end < span.start or span.end > len(source_text):
        return False
    return source_text[span.start : span.end] == span.text and span.source_text_hash == source_text_hash(source_text)


def normalize_copy_text(value: str) -> str:
    pieces: list[str] = []
    for char in value:
        normalized = unicodedata.normalize("NFKC", char).casefold()
        for normalized_char in normalized:
            if _is_omitted_separator(normalized_char):
                continue
            pieces.append(normalized_char)
    return "".join(pieces)


def normalize_source_with_mapping(source_text: str) -> tuple[str, list[int]]:
    normalized_chars: list[str] = []
    source_index_by_normalized_index: list[int] = []
    for source_index, char in enumerate(source_text):
        normalized = unicodedata.normalize("NFKC", char).casefold()
        for normalized_char in normalized:
            if _is_omitted_separator(normalized_char):
                continue
            normalized_chars.append(normalized_char)
            source_index_by_normalized_index.append(source_index)
    return "".join(normalized_chars), source_index_by_normalized_index


def verify_copy_backed_value(
    value: Any,
    source_text: Any,
    scope: CopyBackedScope,
) -> CopyBackedVerificationResult:
    if not scope.enabled:
        return _result(scope, OUT_OF_SCOPE, "none", None, 0, None, "scope_not_enabled")
    if not isinstance(source_text, str) or not source_text:
        return _result(scope, INVALID_INPUT, "none", None, 0, None, "source_text_missing_or_not_string")
    if not isinstance(value, str):
        return _result(scope, UNSUPPORTED_VALUE_TYPE, "none", None, 0, None, "value_is_not_string")
    if not value:
        return _result(scope, NOT_FOUND, "none", None, 0, None, "empty_value_not_verifiable")

    exact_spans = _find_exact_spans(value, source_text)
    if len(exact_spans) == 1:
        start, end = exact_spans[0]
        span = SourceSpan(
            start=start,
            end=end,
            text=source_text[start:end],
            source_text_hash=source_text_hash(source_text),
        )
        return _result(scope, VERIFIED_EXACT_UNIQUE, "exact", span, 1, None, "exact_unique_source_span")
    if len(exact_spans) > 1:
        return _result(
            scope,
            AMBIGUOUS_MULTIPLE_MATCHES,
            "none",
            None,
            len(exact_spans),
            None,
            "multiple_exact_source_spans",
        )

    normalized_value = normalize_copy_text(value)
    if not normalized_value:
        return _result(scope, NOT_FOUND, "none", None, 0, "nfkc_casefold_strip_space_punct", "empty_normalized_value")

    normalized_source, source_mapping = normalize_source_with_mapping(source_text)
    normalized_matches = _find_normalized_spans(normalized_value, normalized_source, source_mapping, source_text)
    if len(normalized_matches) == 1:
        start, end = normalized_matches[0]
        span = SourceSpan(
            start=start,
            end=end,
            text=source_text[start:end],
            source_text_hash=source_text_hash(source_text),
        )
        return _result(
            scope,
            VERIFIED_NORMALIZED_UNIQUE,
            "normalized",
            span,
            1,
            "nfkc_casefold_strip_space_punct",
            "normalized_unique_source_span",
        )
    if len(normalized_matches) > 1:
        return _result(
            scope,
            AMBIGUOUS_MULTIPLE_MATCHES,
            "none",
            None,
            len(normalized_matches),
            "nfkc_casefold_strip_space_punct",
            "multiple_normalized_source_spans",
        )
    return _result(
        scope,
        NOT_FOUND,
        "none",
        None,
        0,
        "nfkc_casefold_strip_space_punct",
        "source_span_not_found",
    )


def audit_normalized_equivalent_collision(value: Any, source_text: Any) -> NormalizedEquivalentCollisionAudit:
    rule = NORMALIZATION_COLLISION_RULE
    if not isinstance(source_text, str) or not source_text:
        return _collision_audit(INVALID_INPUT, 0, [], [], None, None, "source_text_missing_or_not_string")
    if not isinstance(value, str) or not value:
        return _collision_audit(UNSUPPORTED_VALUE_TYPE, 0, [], [], rule, source_text, "value_missing_or_not_string")

    raw_exact_spans = _find_exact_spans(value, source_text)
    normalized_value = _normalize_collision_text(value)
    if not normalized_value:
        return _collision_audit(
            NOT_FOUND,
            len(raw_exact_spans),
            raw_exact_spans,
            [],
            rule,
            source_text,
            "empty_normalized_value",
        )

    normalized_source, source_mapping = _normalize_collision_source_with_mapping(source_text)
    normalized_spans = _find_collision_normalized_spans(
        normalized_value,
        normalized_source,
        source_mapping,
        source_text,
    )
    normalized_equivalent_spans = _dedupe_spans([*raw_exact_spans, *normalized_spans])

    ambiguous_mapping = (
        len(raw_exact_spans) == 1
        and len(normalized_equivalent_spans) > 1
        and any(span != raw_exact_spans[0] for span in normalized_equivalent_spans)
    )
    if ambiguous_mapping:
        return _collision_audit(
            AMBIGUOUS_NORMALIZATION_COLLISION,
            len(raw_exact_spans),
            raw_exact_spans,
            normalized_equivalent_spans,
            rule,
            source_text,
            "raw_exact_unique_but_normalized_equivalent_ambiguous",
        )
    if len(raw_exact_spans) == 1:
        return _collision_audit(
            VERIFIED_EXACT_UNIQUE,
            1,
            raw_exact_spans,
            normalized_equivalent_spans,
            rule,
            source_text,
            "raw_exact_unique_no_normalized_collision",
        )
    if len(raw_exact_spans) > 1 or len(normalized_equivalent_spans) > 1:
        return _collision_audit(
            AMBIGUOUS_MULTIPLE_MATCHES,
            len(raw_exact_spans),
            raw_exact_spans,
            normalized_equivalent_spans,
            rule,
            source_text,
            "multiple_raw_or_normalized_spans",
        )
    return _collision_audit(NOT_FOUND, 0, [], normalized_equivalent_spans, rule, source_text, "source_span_not_found")


def _is_omitted_separator(char: str) -> bool:
    category = unicodedata.category(char)
    return char.isspace() or category.startswith("P") or category.startswith("Z")


def _is_collision_omitted_separator(char: str) -> bool:
    category = unicodedata.category(char)
    return _is_omitted_separator(char) or category.startswith("S")


def _normalize_collision_text(value: str) -> str:
    pieces: list[str] = []
    for char in value:
        normalized = unicodedata.normalize("NFKC", char).casefold()
        for normalized_char in normalized:
            if _is_collision_omitted_separator(normalized_char):
                continue
            pieces.append(normalized_char)
    return "".join(pieces)


def _normalize_collision_source_with_mapping(source_text: str) -> tuple[str, list[int]]:
    normalized_chars: list[str] = []
    source_index_by_normalized_index: list[int] = []
    for source_index, char in enumerate(source_text):
        normalized = unicodedata.normalize("NFKC", char).casefold()
        for normalized_char in normalized:
            if _is_collision_omitted_separator(normalized_char):
                continue
            normalized_chars.append(normalized_char)
            source_index_by_normalized_index.append(source_index)
    return "".join(normalized_chars), source_index_by_normalized_index


def _find_exact_spans(value: str, source_text: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    start = 0
    while True:
        index = source_text.find(value, start)
        if index == -1:
            break
        spans.append((index, index + len(value)))
        start = index + 1
    return _dedupe_spans(spans)


def _find_normalized_spans(
    normalized_value: str,
    normalized_source: str,
    source_mapping: list[int],
    source_text: str,
) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    start = 0
    while True:
        index = normalized_source.find(normalized_value, start)
        if index == -1:
            break
        source_start = source_mapping[index]
        source_end = source_mapping[index + len(normalized_value) - 1] + 1
        if normalize_copy_text(source_text[source_start:source_end]) == normalized_value:
            spans.append((source_start, source_end))
        start = index + 1
    return _dedupe_spans(spans)


def _find_collision_normalized_spans(
    normalized_value: str,
    normalized_source: str,
    source_mapping: list[int],
    source_text: str,
) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    start = 0
    while True:
        index = normalized_source.find(normalized_value, start)
        if index == -1:
            break
        source_start = source_mapping[index]
        source_end = source_mapping[index + len(normalized_value) - 1] + 1
        if _normalize_collision_text(source_text[source_start:source_end]) == normalized_value:
            spans.append((source_start, source_end))
        start = index + 1
    return _dedupe_spans(spans)


def _dedupe_spans(spans: list[tuple[int, int]]) -> list[tuple[int, int]]:
    return sorted(set(spans))


def _span_dicts(spans: list[tuple[int, int]], source_text: str) -> list[dict[str, int | str]]:
    return [
        {
            "start": start,
            "end": end,
            "text_hash": hashlib.sha256(source_text[start:end].encode("utf-8")).hexdigest(),
        }
        for start, end in spans
    ]


def _collision_audit(
    status: str,
    raw_exact_span_count: int,
    raw_exact_spans: list[tuple[int, int]],
    normalized_equivalent_spans: list[tuple[int, int]],
    normalization_rule: str | None,
    source_text: str | None,
    reason: str,
) -> NormalizedEquivalentCollisionAudit:
    source_hash = source_text_hash(source_text) if source_text is not None else None
    fail_closed = status != VERIFIED_EXACT_UNIQUE
    ambiguous_mapping = status == AMBIGUOUS_NORMALIZATION_COLLISION
    normalized_span_dicts = _span_dicts(normalized_equivalent_spans, source_text) if source_text is not None else []
    return NormalizedEquivalentCollisionAudit(
        status=status,
        raw_exact_span_count=raw_exact_span_count,
        normalized_equivalent_span_count=len(normalized_equivalent_spans),
        normalization_rule=normalization_rule,
        source_attested_exact=status == VERIFIED_EXACT_UNIQUE,
        fail_closed=fail_closed,
        ambiguous_mapping=ambiguous_mapping,
        raw_exact_spans=_span_dicts(raw_exact_spans, source_text) if source_text is not None else [],
        normalized_equivalent_spans=normalized_span_dicts,
        source_text_hash=source_hash,
        reason=reason,
    )


def _result(
    scope: CopyBackedScope,
    status: str,
    match_kind: MatchKind,
    source_span: SourceSpan | None,
    candidate_span_count: int,
    normalization_rule: str | None,
    reason: str,
) -> CopyBackedVerificationResult:
    provenance: Provenance = "system_verified_source" if status in VERIFIED_STATUS_VALUES else "unresolved"
    return CopyBackedVerificationResult(
        scope=scope,
        status=status,
        match_kind=match_kind,
        provenance=provenance,
        source_span=source_span,
        candidate_span_count=candidate_span_count,
        normalization_rule=normalization_rule,
        fail_closed=status not in VERIFIED_STATUS_VALUES,
        reason=reason,
    )
