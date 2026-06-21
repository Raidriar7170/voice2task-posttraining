# Recommended Next Action

Do not automatically start another OpenSpec change from this blocked result.

The next action is to recover or commit public-safe raw step-matched prediction
and gold contract artifacts for:

- Control dev/test;
- Treatment dev/test;
- aligned dev/test gold contracts.

After those current inputs exist, rerun `design-and-evaluate-contract-v2-projection`
with the same bounded scope.

Do not substitute older non-step-matched predictions. Do not train, run DPO,
generate new predictions, expand data, modify V1 schema, relax evaluators, or
implement production Contract V2 from this blocked evidence.
