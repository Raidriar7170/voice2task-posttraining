from __future__ import annotations

from pathlib import Path

from voice2task.evaluation import EvaluationResult
from voice2task.io import write_json


def write_metrics_report(
    result: EvaluationResult,
    output_dir: Path,
    title: str = "Voice2Task contract metrics",
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "metrics.json"
    markdown_path = output_dir / "metrics.md"
    write_json(json_path, result.to_dict())
    lines = [
        f"# {title}",
        "",
        (
            "This report summarizes contract-level metrics only. "
            "No live-browser improvement claim is made from these numbers."
        ),
        "",
        "## Metrics",
        "",
    ]
    for name, value in sorted(result.metrics.items()):
        lines.append(f"- `{name}`: {value:.4f}")
    lines.extend(["", "## Failure Slices", ""])
    for name, entry in sorted(result.failure_slices.items()):
        examples = ", ".join(entry["examples"]) if entry["examples"] else "none"
        lines.append(f"- `{name}`: {entry['count']} examples ({examples})")
    markdown_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": json_path, "markdown": markdown_path}
