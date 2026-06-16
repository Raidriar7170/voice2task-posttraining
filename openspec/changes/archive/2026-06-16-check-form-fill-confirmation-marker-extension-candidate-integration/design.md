## Context

The archived `materialize-form-fill-confirmation-marker-extension-candidates` phase created:

- `data/public-samples/form_fill_confirmation_marker_extension_seed_candidates.jsonl`
- `reports/public-sample/form-fill-confirmation-marker-extension-materialized-candidates/`

Those artifacts are candidate-only and explicitly not part of the formal public sample. Before any later merge decision, the repository needs a local preview integration check that confirms the candidate seeds can be appended to the current formal seed rows and built by the normal public dataset builder.

This mirrors the earlier `check-form-fill-remediation-candidate-integration` pattern, but uses the confirmation-marker extension candidate source mode and 12-row expected count.

## Goals / Non-Goals

**Goals:**

- Validate the 12 standalone extension candidate seed rows.
- Build a report-scoped preview dataset by combining formal public seeds plus candidate seeds.
- Run public dataset validation on the preview SFT/DPO/manifest artifacts.
- Publish preview-only evidence with candidate contribution counts, preview counts, formal counts, validation status, and no-recovery claims.
- Keep formal public sample files unchanged.

**Non-Goals:**

- No formal merge into `data/public-samples/seed_traces.jsonl`.
- No committed preview SFT/DPO corpus outside the evidence report directory.
- No prediction, training, A100 execution, prompt change, evaluator relaxation, checkpoint release, adapter release, or model/held-out recovery claim.

## Decisions

- Use a report-scoped preview directory under the evidence output directory.
  - Rationale: this keeps build artifacts inspectable while avoiding formal public sample mutation.
  - Alternative considered: build in a temporary directory and commit only summary counts. Rejected because the existing preview pattern keeps enough local evidence for validation debugging.

- Validate candidate rows before preview build.
  - Rationale: the candidate file is standalone and must fail closed if rows are missing, duplicated, already formal, or have unsupported provenance.
  - Alternative considered: let the public builder fail later. Rejected because provenance failures should be reported as candidate-source errors.

- Keep the phase preview-only.
  - Rationale: materialization and integration compatibility are separate from formal merge, prediction, or model-quality evidence.
  - Alternative considered: merge immediately after successful preview. Rejected because the next merge decision should be a later bounded OpenSpec phase.

## Risks / Trade-offs

- [Risk] Preview counts may be mistaken for current formal public sample counts. -> Mitigation: evidence records formal counts before preview, preview counts separately, and `formal_public_sample_modified=false`.
- [Risk] Candidate DPO pairs generated inside preview may be mistaken for committed formal DPO pairs. -> Mitigation: report labels them preview-only and keeps formal DPO files unchanged.
- [Risk] A successful preview may be overstated as model recovery. -> Mitigation: claims explicitly prohibit held-out recovery, prediction, training, and production-readiness claims.
