# Literal-backslash property fix

Dalton, gpt-6.1-sol at high effort, fixed Lorentz finding A1 in an isolated archive of 334e1f8.

A decoded quoted key containing a literal backslash now keeps a bracket identity.
It cannot resolve as a JavaScript escaped identifier call to another property.
Genuine escaped identifiers retain their existing dot identity.

The worker wrote tests first. The red run had 16 failures and 6 passes.
The green run passed 54 focused tests through Index and compute_facts.
The parent read and applied the patch after git apply --check passed.

Evidence lives under artifacts/trustworthiness/2026-10-09/regressions/literal-backslash.
commands.json records the exact commands. red.log and green.log preserve outcomes.
green-map.json and green-facts.json show no false incoming test edge and an untested count of one.

The archive lacked hatchling, so its package build was not available.
The parent's clean-cache release verifier supplies build evidence.
