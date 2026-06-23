from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from voice2task import copy_backed_prediction_shadow_hook as shadow_hook
from voice2task import training
from voice2task.evaluation import load_predictions
from voice2task.io import read_json
from voice2task.training import run_sft_prediction_export

REPO_ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = REPO_ROOT / "configs/copy-backed-scope-policy-v1.json"


def _contract(task_type: str, route: str, slots: dict[str, Any], *, normalized: str = "fixture") -> dict[str, Any]:
    return {
        "task_type": task_type,
        "route": route,
        "safety": {"allow": task_type != "blocked", "reason": "fixture"},
        "confirmation_required": False,
        "slots": slots,
        "normalized_command": normalized,
        "language": "zh-CN",
        "contract_version": "v1",
    }


def _write_manifest(tmp_path: Path) -> Path:
    rows = [
        ("sft-test-search", "test", "帮我搜索北京天气", _contract("search", "search_web", {"query": "北京天气"})),
        ("sft-test-form", "test", "把姓名字段填成张三", _contract("form_fill", "fill_form", {"field": "姓名"})),
        ("sft-test-extract", "test", "提取目标是价格", _contract("extract", "extract_page", {"target": "价格"})),
        ("sft-test-action", "test", "请取消订单", _contract("blocked", "deny", {"action": "取消订单"})),
    ]
    sft_path = tmp_path / "sft_public_sample.jsonl"
    sft_path.write_text(
        "\n".join(
            json.dumps(
                {
                    "id": row_id,
                    "split": split,
                    "input_text": input_text,
                    "target_contract": contract,
                    "provenance": {"source_id": row_id, "public_safe": True},
                },
                ensure_ascii=False,
            )
            for row_id, split, input_text, contract in rows
        )
        + "\n",
        encoding="utf-8",
    )
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "manifest_id": "copy-shadow-hook-fixture",
                "files": {"sft": sft_path.name},
                "counts": {"sft_rows": len(rows)},
                "public_safe": True,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return manifest


def _write_config(tmp_path: Path, copy_backed_shadow: dict[str, Any] | None = None) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    config: dict[str, Any] = {
        "base_model": "Qwen/Qwen2.5-0.5B-Instruct",
        "model_source": "modelscope",
        "allow_private_prediction": True,
        "adapter_path": "<a100_project_root>/runs/adapter",
        "output_root": "<a100_project_root>",
        "prediction_split": "test",
    }
    if copy_backed_shadow is not None:
        config["copy_backed_shadow"] = copy_backed_shadow
    config_path = tmp_path / "prediction-config.json"
    config_path.write_text(json.dumps(config, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    return config_path


def _jsonl_rows(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_scope_policy_validation_is_complete_and_records_version() -> None:
    from voice2task.copy_backed_shadow_interface import load_scope_policy, validate_scope_policy

    policy = load_scope_policy(POLICY_PATH)
    validation = validate_scope_policy(policy)

    assert validation["ok"] is True
    assert validation["policy_id"] == "copy-backed-scope-policy-v1"
    assert validation["policy_version"] == "1.0.0"
    assert validation["policy_hash"] == validation["computed_policy_hash"]
    assert validation["enabled_triples"] == [
        "search:search_web:query",
        "form_fill:fill_form:field",
        "extract:extract_page:target",
    ]
    assert validation["disabled_triples"] == ["blocked:deny:action"]
    assert validation["scope_row_keys_match_policy_sets"] is True
    assert validation["action_enabled"] is False
    assert validation["normalized_trusted"] is False

    drifted = json.loads(json.dumps(policy))
    drifted["scope_rows"].append(dict(drifted["scope_rows"][0]))
    drifted_validation = validate_scope_policy(drifted)
    assert drifted_validation["ok"] is False
    assert "duplicate_scope_rows" in drifted_validation["blocking_reasons"]

    missing_row = json.loads(json.dumps(policy))
    missing_row["scope_rows"] = missing_row["scope_rows"][:-1]
    missing_validation = validate_scope_policy(missing_row)
    assert missing_validation["ok"] is False
    assert "scope_rows_do_not_match_enabled_disabled_sets" in missing_validation["blocking_reasons"]


def test_prediction_shadow_hook_is_default_off_and_preserves_prediction_output(tmp_path: Path) -> None:
    manifest = _write_manifest(tmp_path)
    disabled_config = _write_config(tmp_path / "disabled")
    null_config = _write_config(
        tmp_path / "null",
        {
            "enabled": True,
            "policy_path": POLICY_PATH.as_posix(),
            "sidecar_output_path": None,
            "retain_span_text": False,
            "retain_input_text": False,
            "retain_raw_model_output": False,
            "fail_isolated": True,
        },
    )
    jsonl_sidecar = tmp_path / "jsonl" / "copy-shadow.jsonl"
    jsonl_config = _write_config(
        tmp_path / "jsonl",
        {
            "enabled": True,
            "policy_path": POLICY_PATH.as_posix(),
            "sidecar_output_path": jsonl_sidecar.as_posix(),
            "retain_span_text": False,
            "retain_input_text": False,
            "retain_raw_model_output": False,
            "fail_isolated": True,
        },
    )
    disabled_output = tmp_path / "disabled" / "predictions.jsonl"
    null_output = tmp_path / "null" / "predictions.jsonl"
    jsonl_output = tmp_path / "jsonl" / "predictions.jsonl"

    disabled_metadata = run_sft_prediction_export(
        disabled_config,
        manifest,
        disabled_output,
        dry_run=False,
        fixture_mode=True,
    )
    null_metadata = run_sft_prediction_export(null_config, manifest, null_output, dry_run=False, fixture_mode=True)
    jsonl_metadata = run_sft_prediction_export(jsonl_config, manifest, jsonl_output, dry_run=False, fixture_mode=True)

    disabled_bytes = disabled_output.read_bytes()
    assert disabled_bytes == null_output.read_bytes() == jsonl_output.read_bytes()
    assert load_predictions(disabled_output) == load_predictions(null_output) == load_predictions(jsonl_output)
    assert not (tmp_path / "disabled" / "copy-shadow.jsonl").exists()
    assert not (tmp_path / "null" / "copy-shadow.jsonl").exists()
    assert jsonl_sidecar.exists()
    assert "copy_backed_shadow" not in disabled_metadata
    assert null_metadata["copy_backed_shadow"]["sidecar_write_status"] == "disabled"
    assert jsonl_metadata["copy_backed_shadow"]["sidecar_write_status"] == "written"
    assert jsonl_metadata["copy_backed_shadow"]["main_prediction_unchanged"] is True

    sidecars = _jsonl_rows(jsonl_sidecar)
    assert len(sidecars) == 4
    assert all(sidecar["sidecar_version"] == "copy-prediction-shadow-v1" for sidecar in sidecars)
    assert all(sidecar["main_prediction_unchanged"] is True for sidecar in sidecars)
    assert all(sidecar["sidecar_write_status"] == "written" for sidecar in sidecars)
    assert all("request_id" not in sidecar for sidecar in sidecars)
    assert all("request_id_hash" in sidecar for sidecar in sidecars)
    assert all("input_text" not in json.dumps(sidecar, ensure_ascii=False) for sidecar in sidecars)
    assert all("gold" not in json.dumps(sidecar, ensure_ascii=False).lower() for sidecar in sidecars)
    spans = [diag.get("source_span") for sidecar in sidecars for diag in sidecar["slot_diagnostics"]]
    assert any(span for span in spans)
    assert all("text" not in span for span in spans if isinstance(span, dict))
    assert all(
        {"start", "end", "source_text_hash", "span_hash"} <= set(span)
        for span in spans
        if isinstance(span, dict)
    )


def test_prediction_shadow_hook_accepts_repo_relative_policy_path_from_external_config(tmp_path: Path) -> None:
    manifest = _write_manifest(tmp_path)
    sidecar_path = tmp_path / "external" / "copy-shadow.jsonl"
    config_path = _write_config(
        tmp_path / "external",
        {
            "enabled": True,
            "policy_path": "configs/copy-backed-scope-policy-v1.json",
            "sidecar_output_path": sidecar_path.as_posix(),
            "retain_span_text": False,
            "retain_input_text": False,
            "retain_raw_model_output": False,
            "fail_isolated": True,
        },
    )

    metadata = run_sft_prediction_export(
        config_path,
        manifest,
        tmp_path / "external" / "predictions.jsonl",
        dry_run=False,
        fixture_mode=True,
    )

    assert metadata["copy_backed_shadow"]["hook_status_counts"]["COMPLETED"] == 4
    assert metadata["copy_backed_shadow"]["sidecar_write_status"] == "written"


def test_prediction_shadow_hook_rejects_reserved_config_values_without_writing_sidecar(tmp_path: Path) -> None:
    from voice2task.copy_backed_prediction_shadow_hook import PredictionShadowHookConfig, run_prediction_shadow_hook

    cases = [
        ("retain_input_text", {"retain_input_text": True}),
        ("retain_raw_model_output", {"retain_raw_model_output": True}),
        ("fail_isolated", {"fail_isolated": False}),
    ]
    for field_name, overrides in cases:
        sidecar_path = tmp_path / f"{field_name}.jsonl"
        outcome = run_prediction_shadow_hook(
            source_text="帮我搜索北京天气",
            prediction=_contract("search", "search_web", {"query": "北京天气"}),
            config=PredictionShadowHookConfig(
                enabled=True,
                policy_path=POLICY_PATH,
                sidecar_output_path=sidecar_path,
                **overrides,
            ),
            request_id=f"reserved-{field_name}",
        )

        assert outcome.hook_status == "SHADOW_CONFIG_INVALID_ISOLATED"
        assert outcome.error_code == f"reserved_config_non_default:{field_name}"
        assert outcome.sidecar is None
        assert outcome.sidecar_write_status == "disabled"
        assert outcome.main_prediction_unchanged is True
        assert outcome.exception_isolated is True
        assert not sidecar_path.exists()


def test_prediction_shadow_hook_loads_policy_once_per_prediction_export_and_records_freeze_metadata(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    manifest = _write_manifest(tmp_path)
    sidecar_path = tmp_path / "jsonl" / "copy-shadow.jsonl"
    config_path = _write_config(
        tmp_path / "jsonl",
        {
            "enabled": True,
            "policy_path": POLICY_PATH.as_posix(),
            "sidecar_output_path": sidecar_path.as_posix(),
            "retain_span_text": False,
            "retain_input_text": False,
            "retain_raw_model_output": False,
            "fail_isolated": True,
        },
    )
    real_load_scope_policy = shadow_hook.load_scope_policy
    load_calls: list[Path] = []

    def counted_load_scope_policy(path: Path) -> dict[str, Any]:
        load_calls.append(path)
        return real_load_scope_policy(path)

    monkeypatch.setattr(shadow_hook, "load_scope_policy", counted_load_scope_policy)

    metadata = run_sft_prediction_export(
        config_path,
        manifest,
        tmp_path / "jsonl" / "predictions.jsonl",
        dry_run=False,
        fixture_mode=True,
    )

    hook_summary = metadata["copy_backed_shadow"]
    assert len(load_calls) == 1
    assert hook_summary["policy_loaded_once"] is True
    assert hook_summary["policy_id"] == "copy-backed-scope-policy-v1"
    assert hook_summary["policy_version"] == "1.0.0"
    assert hook_summary["policy_hash"] == "5dc14efb8ded13dc048ddb067c7c63a1a62b6c03896950e861303973d505cbc7"
    assert hook_summary["policy_start_hash"] == hook_summary["policy_hash"]
    assert hook_summary["policy_end_hash"] == hook_summary["policy_hash"]
    assert hook_summary["policy_drift_detected"] is False
    sidecars = _jsonl_rows(sidecar_path)
    assert len(sidecars) == 4
    assert {sidecar["policy_hash"] for sidecar in sidecars} == {hook_summary["policy_hash"]}
    assert all(sidecar["policy_loaded_once"] is True for sidecar in sidecars)


def test_prediction_shadow_hook_records_policy_drift_without_mutating_predictions(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    manifest = _write_manifest(tmp_path)
    config_path = _write_config(
        tmp_path / "jsonl",
        {
            "enabled": True,
            "policy_path": POLICY_PATH.as_posix(),
            "sidecar_output_path": (tmp_path / "jsonl" / "copy-shadow.jsonl").as_posix(),
            "retain_span_text": False,
            "retain_input_text": False,
            "retain_raw_model_output": False,
            "fail_isolated": True,
        },
    )
    monkeypatch.setattr(shadow_hook, "_current_policy_end_hash", lambda path: "drifted-policy-hash", raising=False)

    disabled_config = _write_config(tmp_path / "disabled")
    disabled_output = tmp_path / "disabled" / "predictions.jsonl"
    drift_output = tmp_path / "jsonl" / "predictions.jsonl"
    run_sft_prediction_export(disabled_config, manifest, disabled_output, dry_run=False, fixture_mode=True)
    metadata = run_sft_prediction_export(config_path, manifest, drift_output, dry_run=False, fixture_mode=True)

    hook_summary = metadata["copy_backed_shadow"]
    assert disabled_output.read_bytes() == drift_output.read_bytes()
    assert hook_summary["policy_loaded_once"] is True
    assert hook_summary["policy_start_hash"] == "5dc14efb8ded13dc048ddb067c7c63a1a62b6c03896950e861303973d505cbc7"
    assert hook_summary["policy_end_hash"] == "drifted-policy-hash"
    assert hook_summary["policy_drift_detected"] is True
    assert hook_summary["main_prediction_unchanged"] is True


def test_prediction_shadow_hook_isolates_sidecar_path_conflicts_with_primary_prediction_artifacts(
    tmp_path: Path,
) -> None:
    manifest = _write_manifest(tmp_path)
    disabled_config = _write_config(tmp_path / "disabled")
    disabled_output = tmp_path / "disabled" / "predictions.jsonl"
    run_sft_prediction_export(disabled_config, manifest, disabled_output, dry_run=False, fixture_mode=True)
    reserved_paths = {
        "prediction_output": tmp_path / "jsonl" / "predictions.jsonl",
        "prediction_metadata": tmp_path / "jsonl" / "prediction_metadata.json",
        "prompt_snapshot": tmp_path / "jsonl" / "prompt_snapshot.json",
        "raw_decoded_summary": tmp_path / "jsonl" / "raw_decoded_summary.jsonl",
        "generation_trace": tmp_path / "jsonl" / "generation_trace.jsonl",
    }

    for name, sidecar_path in reserved_paths.items():
        run_dir = tmp_path / f"conflict-{name}"
        output = run_dir / "predictions.jsonl"
        configured_sidecar = run_dir / sidecar_path.name
        config_path = _write_config(
            run_dir,
            {
                "enabled": True,
                "policy_path": POLICY_PATH.as_posix(),
                "sidecar_output_path": configured_sidecar.as_posix(),
                "retain_span_text": False,
                "retain_input_text": False,
                "retain_raw_model_output": False,
                "fail_isolated": True,
            },
        )

        metadata = run_sft_prediction_export(config_path, manifest, output, dry_run=False, fixture_mode=True)

        assert output.read_bytes() == disabled_output.read_bytes()
        hook_summary = metadata["copy_backed_shadow"]
        assert hook_summary["hook_status_counts"] == {"SHADOW_SINK_PATH_CONFLICT_ISOLATED": 4}
        assert hook_summary["error_code_counts"] == {"sidecar_path_conflicts_with_primary_artifact": 4}
        assert hook_summary["sidecar_write_status"] == "disabled"
        assert hook_summary["path_conflict_count"] == 4
        assert hook_summary["main_prediction_unchanged"] is True
        assert "COMPLETED" not in hook_summary["hook_status_counts"]


def test_prediction_shadow_report_scans_complete_output_bundle(monkeypatch: Any, tmp_path: Path) -> None:
    import importlib.util

    script_path = REPO_ROOT / "scripts/run_copy_backed_prediction_shadow_hook_review.py"
    spec = importlib.util.spec_from_file_location("copy_backed_prediction_shadow_hook_review", script_path)
    assert spec is not None
    assert spec.loader is not None
    review = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(review)

    class ScanResult:
        ok = True
        findings: list[Any] = []

    scans: list[set[str]] = []

    def fake_scan_paths(paths: list[Path]) -> ScanResult:
        output_dir = Path(paths[0])
        scans.append({path.name for path in output_dir.iterdir() if path.is_file()} if output_dir.exists() else set())
        return ScanResult()

    monkeypatch.setattr(review, "scan_paths", fake_scan_paths)

    summary = review.write_reports(REPO_ROOT, tmp_path / "report", POLICY_PATH)

    required_report_files = {
        "summary.json",
        "integration-audit.json",
        "per-scope-metrics.json",
        "latency-benchmark.json",
        "recommended-next-change.md",
        "summary.md",
        "sample-online-sidecars.jsonl",
    }
    assert summary["decision_label"] == "PREDICTION_SHADOW_HOOK_READY_OBSERVE_ONLY"
    assert len(scans) >= 2
    assert required_report_files <= scans[-1]


def test_prediction_shadow_hook_fail_isolates_invalid_policy_sink_and_predictions(tmp_path: Path) -> None:
    from voice2task.copy_backed_prediction_shadow_hook import (
        JsonlShadowSink,
        PredictionShadowHookConfig,
        run_prediction_shadow_hook,
    )

    policy_missing = tmp_path / "missing-policy.json"
    outcome = run_prediction_shadow_hook(
        source_text="帮我搜索北京天气",
        prediction={"task_type": "search"},
        config=PredictionShadowHookConfig(enabled=True, policy_path=policy_missing),
        request_id="req-invalid-policy",
    )
    assert outcome.hook_status == "SHADOW_POLICY_INVALID"
    assert outcome.main_prediction_unchanged is True
    assert outcome.exception_isolated is True
    assert outcome.trusted_provenance_count == 0

    invalid_contract = run_prediction_shadow_hook(
        source_text="帮我搜索北京天气",
        prediction={"task": {"description": "generic normalization output"}},
        config=PredictionShadowHookConfig(enabled=True, policy_path=POLICY_PATH),
        request_id="req-invalid-contract",
    )
    assert invalid_contract.hook_status == "SHADOW_INVALID_CONTRACT"
    assert invalid_contract.main_prediction_unchanged is True
    assert invalid_contract.exception_isolated is True

    malformed_json = run_prediction_shadow_hook(
        source_text="帮我搜索北京天气",
        prediction="{not-json",
        config=PredictionShadowHookConfig(enabled=True, policy_path=POLICY_PATH),
        request_id="req-malformed-json",
    )
    assert malformed_json.hook_status == "SHADOW_INVALID_INPUT"
    assert malformed_json.main_prediction_unchanged is True

    class ExplodingSink(JsonlShadowSink):
        def write(self, sidecar: dict[str, Any]) -> str:
            raise OSError("fixture sink failure with private detail")

    sink_failure = run_prediction_shadow_hook(
        source_text="帮我搜索北京天气",
        prediction=_contract("search", "search_web", {"query": "北京天气"}),
        config=PredictionShadowHookConfig(enabled=True, policy_path=POLICY_PATH),
        request_id="req-sink",
        sink=ExplodingSink(tmp_path / "sink.jsonl"),
    )
    assert sink_failure.hook_status == "SHADOW_SINK_ERROR_ISOLATED"
    assert sink_failure.sidecar_write_status == "failed_isolated"
    assert sink_failure.error_code == "sink_write_failed"
    assert sink_failure.main_prediction_unchanged is True
    assert sink_failure.exception_isolated is True


def test_prediction_shadow_hook_trusts_exact_only_and_never_action_or_normalized(tmp_path: Path) -> None:
    from voice2task.copy_backed_prediction_shadow_hook import PredictionShadowHookConfig, run_prediction_shadow_hook

    config = PredictionShadowHookConfig(enabled=True, policy_path=POLICY_PATH, retain_span_text=True)
    exact = run_prediction_shadow_hook(
        source_text="帮我搜索北京天气",
        prediction=_contract("search", "search_web", {"query": "北京天气"}),
        config=config,
        request_id="req-exact",
    )
    normalized = run_prediction_shadow_hook(
        source_text="字段是 A B",
        prediction=_contract("form_fill", "fill_form", {"field": "AB"}),
        config=config,
        request_id="req-normalized",
    )
    action = run_prediction_shadow_hook(
        source_text="请取消订单",
        prediction=_contract("blocked", "deny", {"action": "取消订单"}),
        config=config,
        request_id="req-action",
    )

    assert exact.hook_status == "COMPLETED"
    assert exact.trusted_provenance_count == 1
    assert exact.candidate_provenance_count == 0
    assert exact.sidecar is not None
    assert exact.sidecar["slot_diagnostics"][0]["source_span"]["text"] == "北京天气"
    assert exact.sidecar["slot_diagnostics"][0]["policy_version"] == "1.0.0"

    normalized_diag = normalized.sidecar["slot_diagnostics"][0]
    assert normalized_diag["verification_status"] == "VERIFIED_NORMALIZED_UNIQUE"
    assert normalized_diag["trusted_provenance"] is False
    assert normalized_diag["candidate_provenance"] is True
    assert normalized.trusted_provenance_count == 0
    assert normalized.candidate_provenance_count == 1

    action_diag = action.sidecar["slot_diagnostics"][0]
    assert action_diag["policy_enabled"] is False
    assert action_diag["trusted_provenance"] is False
    assert action.trusted_provenance_count == 0


def test_private_prediction_shadow_hook_is_post_artifact_and_fail_isolated(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    manifest = _write_manifest(tmp_path)
    sidecar = tmp_path / "copy-shadow.jsonl"
    config = _write_config(
        tmp_path,
        {
            "enabled": True,
            "policy_path": POLICY_PATH.as_posix(),
            "sidecar_output_path": sidecar.as_posix(),
            "retain_span_text": False,
            "retain_input_text": False,
            "retain_raw_model_output": False,
            "fail_isolated": True,
        },
    )
    config_payload = json.loads(config.read_text(encoding="utf-8"))
    config_payload["adapter_path"] = (tmp_path / "adapter").as_posix()
    config.write_text(json.dumps(config_payload, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    output = tmp_path / "predictions.jsonl"

    monkeypatch.setattr(training, "_prediction_dependencies_available", lambda: True)

    def write_mixed_predictions(
        config_payload: dict[str, Any],
        rows: list[Any],
        output_path: Path,
        *,
        sidecar_paths: dict[str, Path],
    ) -> int:
        records = [
            {
                "id": rows[0].id,
                "prediction": rows[0].target_contract.to_dict(),
                "prediction_source_kind": "private_a100_adapter",
                "provenance": {"public_safe": True},
            },
            {
                "id": rows[1].id,
                "prediction": "{not-json",
                "prediction_source_kind": "private_a100_adapter",
                "provenance": {"public_safe": True},
            },
        ]
        output_path.write_text(
            "\n".join(json.dumps(record, ensure_ascii=False, sort_keys=True) for record in records) + "\n",
            encoding="utf-8",
        )
        return len(records)

    monkeypatch.setattr(training, "_run_real_sft_prediction", write_mixed_predictions)

    metadata = run_sft_prediction_export(config, manifest, output, dry_run=False, fixture_mode=False)

    assert metadata["prediction_status"] == "private_adapter_predictions_written"
    assert metadata["prediction_count"] == 2
    assert load_predictions(output)["sft-test-form"] == "{not-json"
    assert sidecar.exists()
    hook_summary = metadata["copy_backed_shadow"]
    assert hook_summary["main_prediction_unchanged"] is True
    assert hook_summary["hook_status_counts"]["COMPLETED"] == 1
    assert hook_summary["hook_status_counts"]["SHADOW_INVALID_INPUT"] == 1
    assert hook_summary["exception_isolated_count"] == 1
    assert hook_summary["sidecar_write_status"] == "written"
    assert read_json(output.parent / "prediction_metadata.json")["copy_backed_shadow"] == hook_summary
