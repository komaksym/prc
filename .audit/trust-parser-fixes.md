Model: gpt-6.1-sol. Archive: /private/tmp/prc-quoted-fix-RKyp1s.

TL;DR: Fixed the collision using explicit model `gpt-6.1-sol`, entirely within the frozen archive. Final parser/map tests pass, and generated facts correctly report one changed symbol without test evidence. Browser and package-build validation remain open.

Modified paths:

- [codegraph.py](/private/tmp/prc-quoted-fix-RKyp1s/src/prc/codegraph.py) preserves property boundaries and quoted identifier equivalence, including Unicode.
- [test_codegraph.py](/private/tmp/prc-quoted-fix-RKyp1s/tests/test_codegraph.py) covers collisions, escapes, Unicode identifiers, and exported-object calls.
- [test_changemap.py](/private/tmp/prc-quoted-fix-RKyp1s/tests/test_changemap.py) asserts the corrected fact verdict and saves generated artifacts.

Root cause: stripping quotes and joining keys with dots merged distinct functions. The RED test showed an extra false `exact` edge. [RED evidence](/private/tmp/prc-quoted-fix-RKyp1s/proof/worker-red-final.log).

Verification:

- `pytest tests/test_codegraph.py tests/test_changemap.py`: **107 passed**. [GREEN](/private/tmp/prc-quoted-fix-RKyp1s/proof/final-parser.log).
- Broader acceptance: **159 passed**.
- Ruff lint, formatting, and mypy: **passed**.
- [Generated map and facts](/private/tmp/prc-quoted-fix-RKyp1s/proof/green-collision-results.json): `untested_total=1`.

The larger suite had one unavailable-Chromium failure. Build was not run because required tooling is absent and installs are prohibited. No real-workspace writes, installs, network, commits, or publication occurred.

Next step: parent computes the patch and completes combined release verification. [Full handoff report](/private/tmp/prc-quoted-fix-RKyp1s/proof/parser-report.md).
