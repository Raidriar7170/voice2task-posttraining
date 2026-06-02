from pathlib import Path

import pytest

from voice2task.leak_scan import scan_paths
from voice2task.schemas import ValidationError


def test_leak_scan_flags_private_paths_tokens_and_private_ips(tmp_path: Path) -> None:
    bad = tmp_path / "bad.md"
    private_path = "/" + "Users" + "/person/private.jsonl"
    secret = "sk-" + "live-secret"
    private_ip = "192." + "168.1.10"
    bad.write_text(f"path={private_path}\napi_key={secret}\nhttp://{private_ip}", encoding="utf-8")

    result = scan_paths([bad])

    assert result.ok is False
    assert {"private_path", "secret", "private_ip"}.issubset({finding.category for finding in result.findings})


def test_leak_scan_allows_clean_public_artifacts(tmp_path: Path) -> None:
    clean = tmp_path / "clean.md"
    clean.write_text("Public sample report with aggregate metrics only.", encoding="utf-8")

    result = scan_paths([clean])

    assert result.ok is True
    assert result.findings == []


def test_leak_scan_raises_for_oversized_public_jsonl(tmp_path: Path) -> None:
    big = tmp_path / "too-large.jsonl"
    big.write_text("{}\n" * 6, encoding="utf-8")

    with pytest.raises(ValidationError, match="oversized_public_corpus"):
        scan_paths([big], max_public_jsonl_rows=5, raise_on_error=True)


def test_leak_scan_flags_public_jsonl_rows_marked_private(tmp_path: Path) -> None:
    private_row = tmp_path / "private-row.jsonl"
    private_row.write_text('{"provenance":{"public_safe":false}}\n', encoding="utf-8")

    result = scan_paths([private_row])

    assert result.ok is False
    assert "raw_private_row" in {finding.category for finding in result.findings}
