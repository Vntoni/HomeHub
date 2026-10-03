# Offline tests and audit baseline for stabilization

HomeHub's existing 196 tests pass despite the audited AC readback, MQTT
persistence and weather defects. This draft adds an offline runner, isolation
self-check, lifecycle/repository tests, four explicit failing acceptance tests,
and the approved audit/test/development documentation, based on 2552c9b.

The application code, active deployment workflow and production configuration
are unchanged. New regression failures are deliberately visible (no skip or
xfail). Baseline: 196 passed; extended baseline: 199 passed, 4 failed (HH-01–04).
Existing startup and interaction QML smokes passed locally on macOS/Python 3.12.
GitHub/Linux/Python 3.11 results must be read separately from the Actions run.

This is a review base for independent fix PRs, not a deployable change by itself.
Do not merge while acceptance tests are failing. The fixes target this branch
so their reviews show only their individual changes; the AC state fix depends
on the AC SDK refresh fix. Integration of approved changes requires a separate
review and a full green run. No automatic merge or production deployment is requested.

The CI proposal remains under docs/ci-tests.proposed.yml. No branch protection,
repository settings, secrets, runner setup or active workflows were changed.
All device tests use fakes. Raspberry Pi SDK versions and real hardware still
need separate verification. See docs/PHASE4_STATUS.md for local fix results.
