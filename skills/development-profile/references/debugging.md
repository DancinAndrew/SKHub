# Debugging with a verifiable signal

Use when the cause is unclear, fixes have repeatedly failed, or performance has regressed. Scale the process to the defect; a clear typo does not need a hypothesis report.

1. **Define the symptom.** Record the user's expected and observed behavior, relevant inputs, and environment. Distinguish the reported failure from a nearby error, setup failure, or access problem.
2. **Establish a feedback loop.** Prefer an existing test, CLI invocation, HTTP request, or browser flow that exercises the real failing path. Run it and retain the relevant result. Use a replay, small harness, or comparison with a known-good version when needed. Inspect code as necessary to construct the reproduction.
3. **Narrow the cause.** Reduce inputs or components while preserving the same failure. If several causes remain plausible, rank a small set of hypotheses and state the observation that would support or refute each. Probe one distinguishing variable at a time.
4. **Fix and verify.** Where practical, capture the failure in a regression test before changing the code. Ensure the test can catch this bug through the real interface; a test of a simplified helper is insufficient when multiple callers, state, or persistence cause the defect. Run the same signal after the fix and check the original scenario if the reproduction was reduced.
5. **Clean up.** Remove temporary instrumentation or retain it in the project's approved debug location. Report the supported cause, changed behavior, checks actually run, and unresolved limitations.

For intermittent failures, record attempts and failures under comparable conditions. One successful run is not proof of a fix. For performance, measure the same workload before and after, including relevant environment conditions; do not substitute intuition for a baseline.

If reproduction is blocked, state the missing environment, input, or access and continue useful read-only analysis. Label hypotheses as unverified. Ask for the specific missing evidence or authorization only when necessary; do not claim the bug is fixed from inspection alone. Do not keep retrying the same unavailable mechanism without new evidence.

Keep credentials and unrelated private data out of reproduction artifacts and user-visible logs. A debugging workflow does not authorize production mutations or new infrastructure.

For order-dependent tests, isolate the smallest preceding-test set and inspect leaked globals, fixtures, environment, caches, and unclosed resources. For flaky async behavior, wait on a bounded observable condition rather than adding arbitrary sleep. Trace invalid data back to its first incorrect state; validate at the responsible boundary instead of scattering defensive defaults that hide the cause.
