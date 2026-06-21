## Context

The archived `run-canonical-slot-paired-sft-ablation` phase produced fresh
control and treatment SFT adapters, but the two arms were epoch-matched while
the treatment train split contained additional canonical slot-boundary rows.
That means treatment received more optimizer updates, so its result cannot
isolate the canonical-data effect from extra training compute.

This change runs one bounded, fixed-seed SFT A/B with identical optimizer-step
budgets. It keeps the same base model, LoRA policy, prompt, tokenizer,
decoding, evaluator, and frozen dev/test inputs, and it does not start DPO,
Contract V2, data expansion, candidate design, or multi-seed confirmation.

## Goals

- Verify the control and treatment comparison boundary from concrete artifacts,
  not from `CONTEXT.md` or split counts alone.
- Recover the prior control run's actual optimizer-step budget from training
  evidence, or block if it cannot be recovered honestly.
- Train fresh control and treatment adapters with the same explicit `max_steps`
  and fixed random seed.
- Publish public-safe metrics, paired row deltas, family deltas, bootstrap
  diagnostics, comparison, decision, and a concise Human Brief.
- End with one bounded decision label and next-step recommendation.

## Non-Goals

- No DPO, GRPO, LLM judge, semantic-equivalence scoring, prediction repair, or
  evaluator relaxation.
- No new candidate design, data expansion, challenge set, Contract V2
  implementation, prompt hardening, LoRA/base model tuning change, or public
  adapter/checkpoint release.
- No automatic multi-seed confirmation from this phase.
- No production-readiness, live-browser, safety-certification, or held-out
  recovery claim beyond observed strict metrics.

## Boundary Verification

The phase must discover and record:

- Control manifest, train split, dev/test gold files, and formal gold contracts.
- Treatment manifest, train split, dev/test gold files, and formal gold
  contracts.
- Whether treatment changes are restricted to reviewed canonical slot
  train-only data.
- Dev/test row id equality, row order equality, input hash equality, gold
  contract hash equality, and per-row gold contract equality.

If dev/test rows cannot be proven identical, or cannot be safely aligned by
stable sample id with identical gold contracts, the phase writes only blocked
evidence and stops before training.

## Step-Matched Training Budget

The unified training budget is derived from the previous paired control run's
observed training evidence. Preferred source order:

1. Trainer state or training summary with observed optimizer/global steps.
2. Public-safe prior control training summary linked to the real run.
3. Exact reconstruction from the prior control config, train-row count, batch
   size, gradient accumulation, and epoch count, explicitly labeled as
   reconstructed.

If none of these sources can be verified, training is blocked. The new control
and treatment configs must use the same explicit `max_steps`, effective batch
size, scheduler step budget, random seed, prompt template, tokenizer, decoding
policy, evaluator, and frozen dev/test inputs. `target_tokens_seen` is recorded
for disclosure but is not matched unless a later scoped change authorizes a
token-matched experiment.

## Evidence Shape

The committed public-safe evidence root is:

```text
reports/public-sample/step-matched-canonical-slot-ablation/
```

Required artifacts:

- `boundary-verification.json`
- `control/config.json`
- `control/training-summary.json`
- `control/dev-metrics.json`
- `control/test-metrics.json`
- `treatment/config.json`
- `treatment/training-summary.json`
- `treatment/dev-metrics.json`
- `treatment/test-metrics.json`
- `paired-row-analysis.json`
- `family-level-deltas.json`
- `bootstrap-analysis.json`
- `comparison.json`
- `comparison.md`
- `decision.md`

Private A100 paths, raw logs, checkpoints, adapters, caches, private override
configs, host details, SSH details, tokens, secrets, and private corpus rows
remain out of git.

## Pilot Gate

The one-seed result recommends three-seed confirmation only if treatment meets
all gate conditions on both dev and test:

- `slot_value_exact_f1` delta is at least `0.03`.
- `executable_contract_pass_rate` delta is at least `0.02`.
- `safety_recall` does not decrease.
- `unsafe_false_negative_rate` does not increase.
- `requires_confirmation_accuracy` drops by no more than `0.01`.
- `schema_validity` and `json_valid_rate` do not decrease.

The decision label must be exactly one of:

- `PASS_STEP_MATCHED_PILOT`
- `POSITIVE_BUT_INCONCLUSIVE`
- `NO_CANONICAL_DATA_SIGNAL`
- `REGRESSION_OR_GUARDRAIL_FAILURE`

If A100 connectivity, safe GPU placement, previous control training-budget
evidence, remote dependencies, boundary verification, or prediction evaluation
cannot be verified, the phase writes one blocked artifact and stops.
