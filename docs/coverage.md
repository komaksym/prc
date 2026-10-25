# Coverage reporting

PRC collects coverage from the one pytest run in the isolated release verifier.
The verifier writes one XML report for each run at:

```text
artifacts/release/verify/run-*/coverage.xml
```

The report uses relative `src/prc/` file names. Its source configuration includes product modules that the tests did not import.
The report instruments Python modules under `src/prc` only. Browser JavaScript and CSS assets are outside the report.
The CI job sends this report to Codecov after release verification succeeds. It authenticates with GitHub OIDC and needs no Codecov token.

## Install the Codecov App

1. Install the Codecov GitHub App for the `komaksym/prc` repository from the Codecov organization settings.
2. Grant the App access to this repository.
3. Keep the `id-token: write` permission in the `ci` job. The upload fails if it cannot use OIDC.
4. Run the workflow on `main` and on a pull request. Confirm that both runs upload a report before you change a ruleset.

The workflow accepts only the explicit report path. It disables Codecov's report search, so a missing report fails CI.

## Baseline prerequisites

Codecov needs a base report before it can calculate patch coverage.
Before you require `codecov/patch`, complete these steps:

1. Land the workflow and release verifier changes on `main`.
2. Wait for the `main` workflow to upload its coverage report.
3. Open a pull request and wait for its report upload.
4. Confirm that Codecov processes both reports without an error.
5. Confirm that the pull request shows `codecov/patch` and that it calculates changed lines.
6. Require the exact `codecov/patch` status only after those checks pass.

The patch target is 80% with a 0% threshold. Codecov fails the patch status when changed code has no report. Overall project coverage is informational.
Do not require an overall project status.
