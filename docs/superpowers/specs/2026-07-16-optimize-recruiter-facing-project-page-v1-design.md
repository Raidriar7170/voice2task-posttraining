# Voice2Task Recruiter-Facing Project Page V1 Design

## Status

- Approved by the user on 2026-07-16.
- Change type: documentation-only GitHub project-page optimization.
- Working branch: `codex/optimize-recruiter-facing-project-page-v1`.
- Stacked base: `codex/materialize-manifest-bound-train-only-sft-v1` at
  `38db124`.
- Intended Draft PR base: `codex/materialize-manifest-bound-train-only-sft-v1`.
- Merge is explicitly out of scope.

## Objective

Rewrite the Chinese and English repository homepages so an HR reviewer,
interviewer, or machine-learning engineer can understand within 30 seconds:

1. the problem Voice2Task solves;
2. the technically substantive work completed;
3. the real quantitative results, including the negative result;
4. why the evidence is credible; and
5. where to inspect code, experiments, and evidence.

The page must lead with project value and measured results instead of internal
phase names. It must remain conservative enough for public recruiting use.

## Delivery Topology

The required 282-row manifest-bound train-only artifact, the latest bounded
real A100 smoke evidence, and its CLI fix are not present on `origin/main`.
They are available on the approved stacked base.

The project-page branch therefore starts from that base, and its Draft PR will
target that base. Relative to the Draft PR base, the change remains docs-only.
After the prerequisite lineage reaches `main`, the Draft PR can be retargeted
without changing the README content.

The project-page PR must not absorb, rewrite, or duplicate prerequisite code,
data, metrics, or OpenSpec history.

## Scope

### Files to change

- `README.md`
- `README_en.md`
- this approved design record

Purely presentational local assets are permitted only if required. The planned
design uses GitHub-native Markdown and Mermaid, so no asset is currently needed.

### Explicitly excluded

- model or training logic;
- prediction or evaluation logic;
- dataset rows or manifest content;
- metrics, reports, historical evidence, or experimental conclusions;
- training, prediction, evaluation, DPO, or GRPO execution;
- repository settings, description, or topics mutation;
- merge, release, deploy, checkpoint publication, or adapter publication.

## Sources of Truth

All public claims must be derived from the approved stacked base. The primary
authority order for this page is:

1. `reports/lockbox-v1/final-evaluation/comparison.json`
2. `data/public-samples/manifest_public_sample.json`
3. `reports/public-sample/step-matched-canonical-slot-ablation/comparison.json`
4. `reports/public-sample/slot-error-mechanism-analysis/summary.json`
5. `reports/public-sample/EVIDENCE_INDEX.md`
6. `docs/current-status.md`
7. `openspec/specs/supervised-contract-tuning/spec.md`
8. `openspec/specs/voice2task-dataset-preparation/spec.md`
9. the archived July 2026 A100 smoke, CLI-fix, and train-only changes
10. `CONTEXT.md`

When existing README wording conflicts with these files, the README must be
corrected without mutating the evidence.

## Verified Facts for the Homepage

### Data and infrastructure

- Model path: Qwen2.5-7B-Instruct with LoRA.
- Public dataset: 247 seed rows, 696 SFT rows, and 2,100 preference pairs.
- Bound training derivative: 282 canonical train-only SFT rows.
- Frozen evaluation: 120 rows across 120 semantic families.
- Step-matched ablation: 3,132 optimizer steps per arm; not token matched.
- Fresh approved-base test baseline: 1,485 passing tests.
- A bounded private A100 smoke completed exactly one optimizer step on two
  training rows and verified non-zero finite adapter updates.
- The adapter and checkpoint remain private and are not released.

### Frozen lockbox results

The compact result table will show decimal scores and percentage-point deltas:

| Metric | Base | Final SFT | Delta |
| --- | ---: | ---: | ---: |
| Semantic contract valid rate | 82.50% | 86.67% | +4.17 pp |
| Task type accuracy | 79.17% | 85.83% | +6.67 pp |
| Route accuracy | 80.00% | 85.83% | +5.83 pp |
| Confirmation accuracy | 70.83% | 79.17% | +8.33 pp |
| Strict contract exact match | 1.67% | 0.83% | -0.83 pp |

The interpretation immediately below the table must state that semantic
structure, task classification, routing, and confirmation judgment improved,
while strict full-contract exact match did not. The repository therefore does
not claim overall model-quality improvement.

Confirmation accuracy must never be described as overall accuracy.

## Homepage Information Architecture

Both language versions will use the same section order and evidence links.
Wording may be idiomatic rather than sentence-for-sentence literal.

### 1. Hero

- Title: `Voice2Task Post-Training`.
- One-sentence input/output positioning.
- One short sentence covering data, assistant-only SFT, gold-free prediction,
  strict evaluation, step-matched ablation, and error attribution.
- A plain-text technical stack line: Python, PyTorch, Transformers, TRL, PEFT,
  Qwen2.5-7B, and LoRA.
- Four to six compact highlight items. Qwen/LoRA belongs in the stack line so
  the numeric highlights can prioritize 247 -> 696, 282, 2,100, 120/120,
  bounded A100 training, and 1,485 tests.

The page will not use externally hosted badge images. This avoids CI-like badge
implications and external image dependencies.

### 2. Key Results

Use the five-row frozen-lockbox table above, followed by the explicit negative
result and links to the comparison JSON and current status.

### 3. What I Built

Keep exactly three high-value modules:

1. Data and post-training pipeline: Qwen2.5-7B LoRA, assistant-only loss,
   public data construction, manifest/SHA-256 binding, and private offline A100
   operation.
2. Trustworthy evaluation and experimental design: frozen one-look lockbox,
   fixed prompt/decoder/evaluator, strict layered metrics, and the 3,132-step
   matched A/B.
3. Error attribution and safety boundaries: core-slot failure concentration,
   mixed slot representation, observe-only provenance hooks, false-trust
   findings, and fail-closed execution gates.

Each module will use at most two short paragraphs or bullets.

### 4. System Overview

Use one GitHub-native Mermaid flowchart:

`Chinese Voice / ASR -> Dataset & Contract Validation -> Qwen2.5-7B LoRA SFT
-> Gold-free Prediction -> JSON / Schema Guard -> Strict Contract Evaluation
-> Error Analysis & Provenance Shadow Audit`

The diagram must not show browser execution, production deployment, or online
automation.

### 5. Evaluation Design

Use no more than five bullets covering:

- family-aware splits and split-integrity audit;
- frozen one-look lockbox;
- recursive JSON type-strict equality;
- step-matched experiment with fixed prompt, decoder, schema guard, and
  evaluator; and
- `DEVELOPMENT_ONLY_SPENT` public dev/test plus symmetric reporting of positive
  and negative metrics.

### 6. Repository Map

Use a compact table with verified relative links to:

- public data manifest;
- train-only SFT artifact;
- training CLI;
- evaluation CLI;
- lockbox comparison;
- step-matched ablation;
- slot-error analysis;
- evidence index;
- current OpenSpec specifications; and
- tests.

Every linked path must exist on the Draft PR base and final branch.

### 7. Reproducibility

Only list public-safe commands that do not download a model or initiate private
training:

```bash
PYTHONPATH=src pytest -q
PYTHONPATH=src ruff check .
OPENSPEC_TELEMETRY=0 openspec validate --all --strict
PYTHONPATH=src python scripts/check_current_truth_surface.py
```

Mention that real training requires an ignored private config and local model
weights. Do not expose hosts, SSH commands, paths, tokens, configs, raw logs,
or adapter locations.

### 8. Project Status

Separate completed engineering/evidence work from explicit non-claims.

Completed work may include dataset construction, the LoRA training path,
bounded real A100 smoke, strict evaluation, frozen lockbox, step-matched A/B,
slot-error analysis, and provenance shadow audit.

The page must explicitly reject claims of:

- overall model improvement;
- production readiness or safety certification;
- live-browser benchmark improvement;
- DPO benefit;
- clean held-out generalization; and
- released checkpoints or adapters.

`Portfolio-ready research and engineering project` is permitted if status text
needs a concise summary.

## Writing and Layout Constraints

- Chinese README is the primary recruiting page; English matches its structure.
- Each file should remain approximately 180 to 260 lines.
- No paragraph should exceed four rendered lines where practical.
- Use compact tables and short bullets; avoid uninterrupted prose blocks.
- Use project facts and first-person contribution framing, never “we.”
- All repository links must be relative.
- The result table and code blocks must remain usable on mobile widths.
- Do not add an unverified CI badge or external image dependency.
- Do not expose private infrastructure details.

## Validation Design

Before publication, run and report:

1. Markdown structure and Mermaid fence checks.
2. Relative-link existence checks for both READMEs.
3. Public leak and prohibited-private-detail scans.
4. Existing README/evidence-surface tests.
5. Full `PYTHONPATH=src pytest -q`.
6. `PYTHONPATH=src ruff check .`.
7. `OPENSPEC_TELEMETRY=0 openspec validate --all --strict`.
8. `PYTHONPATH=src python scripts/check_current_truth_surface.py`.
9. `git diff --check` and `git status --short`.
10. A full claim scan for unsupported overall-improvement, production,
    held-out-generalization, DPO, live-browser, checkpoint-release, and
    safety-certification wording.

The numeric table will also be checked directly against the lockbox comparison
JSON, and the dataset highlights against the current manifest.

## Acceptance Criteria

- A recruiter can identify the input, output, model, data scale, result, and
  result limitation from the first screen and Key Results section.
- A technical reviewer can find the training, evaluation, experimental-design,
  and error-analysis evidence without searching the repository.
- Chinese and English versions contain the same facts and section order.
- Every metric and dataset count matches an authoritative committed artifact.
- The strict exact-match regression is visible, not buried or softened.
- The Draft PR diff against its approved stacked base contains documentation
  changes only.
- The branch is pushed and a Draft PR is opened, but not merged.

## Repository Metadata Recommendation

The final handoff may recommend a repository description and topic list, but
must not change repository settings without separate authorization.
