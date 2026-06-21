# Step-matched projection input recovery

- Decision label: `RECOVERED_FROM_EXISTING_ARTIFACTS`
- Recovery method: `recovered_from_existing_artifacts`
- Raw predictions found: yes, four original step-matched prediction files were recovered.
- Prediction-only reproduction: not used.
- Adapter identity: verified by adapter model hash, adapter metadata, training manifest, row count, and optimizer step count.
- Boundary: dev=207 rows, test=207 rows; Control, Treatment, and Gold IDs match; dev/test IDs do not overlap.
- Dev gold hash: `6086ab1aacafec12c1219e3e6353beb93caecc22dab22a2e283f992b710a8d5b`
- Test gold hash: `593f7d167e5698ee3687c2177bba7731cf91740f2d623b7c8966b4063855bc2c`
- Metric reproduction: passed against the committed step-matched aggregate report using the current evaluator.
- Projection inputs ready: true for a later bounded Contract V2 projection rerun.
- Not done: no training, no prediction-only reproduction, no prediction repair, no evaluator/schema/prompt/gold/split change, no Contract V2 projection.
- Next recommended change: `rerun-contract-v2-projection-with-recovered-inputs`.
