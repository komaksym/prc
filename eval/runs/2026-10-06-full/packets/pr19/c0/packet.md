# Reconcile legacy evidence and publish private DM reports

## Summary

Consolidates the legacy reconciliation stack and adds the private DM report slices:

- Connections / invitations shortlist with historical exclusion, company caps, and all-history event bindings.
- Inbox evidence with exact CREATE-to-INBOX DM correlation, UTC parsing, and replay idempotence.
- Private DM action planner: manual reply / follow-up / first-DM queues with strict withholding and an offline private CLI.
- Three-doc publication: owner-only Google Docs for connections, first-time DMs, and follow-ups through one marker-safe, revision-checked publisher with dual preflight and retained-evidence binding.

## DAG

```
inbox/invitation evidence ──► DM action planner ──► DM Doc publication ──► CI wiring
        (existing stack)         (dm_actions.py)      (dm_doc_report.py +
                                                      publish_private_dm_docs.py)
```

## Test plan

- tests/e2e_private_dm_actions.py — synthetic classifier, planner, and CLI matrix
- tests/e2e_dm_uncertainty_scope.py — anonymous-evidence timing boundary
- tests/e2e_private_dm_doc_report.py — two-Document Google boundary matrix (privacy, markers, revision conflicts, retained-evidence staleness)
- tests/e2e_doc_report.py — connections report plus generic publish_text boundary
- pytest -q: 35 passed; ruff and strict mypy clean on changed files

<!-- This is an auto-generated comment: release notes by coderabbit.ai -->

## Summary by CodeRabbit

* **New Features**
  * Added private invitation shortlists that rank eligible prospects using verified identity, employer, qualification, and invitation-history evidence.
  * Added inbox syncing with dry-run by default and duplicate-safe event recording when explicitly applied.
  * Added private direct-message action reports and Google Docs publishing for connection and DM reports. Automated DM report publishing is not yet available.
* **Bug Fixes**
  * Improved validation of inbox snapshots, pagination, profile identities, and ambiguous message evidence to prevent unsupported recommendations.
* **Documentation**
  * Added guidance on report contents, privacy safeguards, eligibility rules, and verification.

<!-- end of auto-generated comment: release notes by coderabbit.ai -->
