from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from voice2task.schemas import PRIVATE_IP_RE, PRIVATE_PATH_RE, SECRET_RE, ValidationError

SSH_DETAIL_RE = re.compile(
    r"(?i)("
    r"\bssh\s+[^@\s]+@|"
    "ssh-" + "rsa|"
    "BEGIN OPENSSH PRIVATE " + r"KEY|"
    r"^\s*Host" + r"Name\s+\S+|"
    r"^\s*Identity" + r"File\s+\S+"
    r")"
)


@dataclass(frozen=True)
class Finding:
    path: str
    category: str
    line: int
    detail: str


@dataclass(frozen=True)
class ScanResult:
    ok: bool
    findings: list[Finding]

    def to_dict(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "findings": [finding.__dict__ for finding in self.findings],
        }


def _iter_files(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    skipped_parts = {".git", "__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache", "local-private"}
    for path in paths:
        if path.is_dir():
            for child in path.rglob("*"):
                if child.is_file() and skipped_parts.isdisjoint(child.parts):
                    files.append(child)
        elif path.exists():
            files.append(path)
    return files


def scan_paths(
    paths: list[Path],
    max_public_jsonl_rows: int = 5000,
    raise_on_error: bool = False,
) -> ScanResult:
    findings: list[Finding] = []
    for path in _iter_files(paths):
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for line_number, line in enumerate(text.splitlines(), start=1):
            if PRIVATE_PATH_RE.search(line):
                findings.append(Finding(path.as_posix(), "private_path", line_number, "local absolute path"))
            if SECRET_RE.search(line):
                findings.append(Finding(path.as_posix(), "secret", line_number, "secret-like token"))
            if PRIVATE_IP_RE.search(line):
                findings.append(Finding(path.as_posix(), "private_ip", line_number, "private IP address"))
            if SSH_DETAIL_RE.search(line):
                findings.append(Finding(path.as_posix(), "ssh_detail", line_number, "SSH command or key detail"))
        if path.suffix == ".jsonl":
            row_count = 0
            for line_number, line in enumerate(text.splitlines(), start=1):
                if not line.strip():
                    continue
                row_count += 1
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                provenance = row.get("provenance") if isinstance(row, dict) else None
                if isinstance(provenance, dict) and provenance.get("public_safe") is False:
                    findings.append(
                        Finding(path.as_posix(), "raw_private_row", line_number, "public JSONL row marked private")
                    )
            if row_count > max_public_jsonl_rows:
                findings.append(
                    Finding(
                        path.as_posix(),
                        "oversized_public_corpus",
                        0,
                        f"{row_count} rows exceeds {max_public_jsonl_rows}",
                    )
                )
    result = ScanResult(ok=not findings, findings=findings)
    if raise_on_error and findings:
        categories = ", ".join(sorted({finding.category for finding in findings}))
        raise ValidationError(f"{categories}: public leak scan failed")
    return result
