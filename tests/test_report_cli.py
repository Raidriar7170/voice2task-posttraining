import json
from pathlib import Path

from voice2task.cli import report as report_cli


def test_leak_scan_cli_keeps_positional_paths_compatible(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    public_report = tmp_path / "report.md"
    public_report.write_text("Public sample report with aggregate metrics only.", encoding="utf-8")

    assert report_cli.main(["leak-scan", public_report.as_posix()]) == 0

    output = json.loads(capsys.readouterr().out)
    assert output["ok"] is True
    assert output["findings"] == []


def test_leak_scan_cli_writes_output_with_audit_metadata(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    public_dir = tmp_path / "public"
    public_dir.mkdir()
    (public_dir / "report.md").write_text("Public sample report with aggregate metrics only.", encoding="utf-8")
    output_path = tmp_path / "leak_scan_result.json"

    assert (
        report_cli.main(
            [
                "leak-scan",
                "--paths",
                public_dir.as_posix(),
                "--output",
                output_path.as_posix(),
                "--max-public-jsonl-rows",
                "5",
            ]
        )
        == 0
    )

    assert capsys.readouterr().out == ""
    output = json.loads(output_path.read_text(encoding="utf-8"))
    assert output["ok"] is True
    assert output["findings"] == []
    assert output["scanned_paths"] == [public_dir.as_posix()]
    assert output["max_public_jsonl_rows"] == 5
    assert "generated_at" in output


def test_leak_scan_cli_sanitizes_private_scanned_paths(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    private_path = Path("/mnt/data/" + "minghongsun/voice2task-post-training/evidence/a100-sft-smoke")
    output_path = tmp_path / "leak_scan_result.json"

    assert (
        report_cli.main(
            [
                "leak-scan",
                "--paths",
                private_path.as_posix(),
                "--output",
                output_path.as_posix(),
            ]
        )
        == 0
    )

    assert capsys.readouterr().out == ""
    output = json.loads(output_path.read_text(encoding="utf-8"))
    assert output["scanned_paths"] == ["<private_path>"]
    assert private_path.as_posix() not in output_path.read_text(encoding="utf-8")


def test_leak_scan_cli_combines_positional_and_flag_paths(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    positional = tmp_path / "positional.md"
    flagged = tmp_path / "flagged.md"
    positional.write_text("Public positional report.", encoding="utf-8")
    flagged.write_text("Public flagged report.", encoding="utf-8")

    assert report_cli.main(["leak-scan", positional.as_posix(), "--paths", flagged.as_posix()]) == 0

    output = json.loads(capsys.readouterr().out)
    assert output["ok"] is True
    assert output["scanned_paths"] == [positional.as_posix(), flagged.as_posix()]
