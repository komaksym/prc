# `The owner had no durable inbox evidence.`

![PR card](card.png)

Upload `card.png` with this comment: images do not embed from the repo.

```mermaid
flowchart LR
n1["insert_events_ignore_duplicates"]
n2["read_events"]
n3["_require"]
n4["snapshot"]
n5["_get_paged"]
n6["_validate_snapshot_paging"]
n7["_next_link"]
n8["main"]
n9["verify"]
n10["VerifiedStore"]
n11["main"]
n12["reconcile"]
classDef added fill:#123626,stroke:#3fd68a,color:#eceef3;
classDef modified fill:#3a2b10,stroke:#f2b33d,color:#eceef3;
classDef deleted fill:#3d1a1d,stroke:#f4676f,color:#eceef3;
n1 --> n2
linkStyle 0 stroke:#3fd68a,stroke-width:2px
n1 --> n3
linkStyle 1 stroke:#3fd68a,stroke-width:2px
n2 --> n3
linkStyle 2 stroke:#3fd68a,stroke-width:2px
n8 --> n9
linkStyle 3 stroke:#3fd68a,stroke-width:2px
n9 --> n10
linkStyle 4 stroke:#3fd68a,stroke-width:2px
n9 --> n3
linkStyle 5 stroke:#3fd68a,stroke-width:2px
n5 --- n7
n5 --> n6
linkStyle 7 stroke:#3fd68a,stroke-width:2px
n4 --- n5
n11 --> n12
linkStyle 9 stroke:#3fd68a,stroke-width:2px
class n1 added
class n2 added
class n3 added
class n4 modified
class n5 modified
class n6 added
class n7 modified
class n8 added
class n9 added
class n10 added
class n11 added
class n12 added
```

Showing 12 of 61 changed symbols. Full map: map.html

## Look here first

- `reconcile_inbox` in `src/linkedin_mdp_mcp/inbox_sync.py`
- `LinkedInMDPClient` in `src/linkedin_mdp_mcp/client.py`
- `run` in `scripts/sync_inbox.py`

## Risky surfaces and description vs diff

- `diagnostics/verify_inbox_live.py`: external calls
- `scripts/sync_inbox.py`: external calls
- `src/linkedin_mdp_mcp/inbox_sync.py`: external calls
- `tests/e2e_inbox_review.py`: external calls
- `tests/e2e_inbox_sync.py`: external calls

## Not covered by tests

- `FrozenInbox` in `diagnostics/verify_inbox_live.py`
- `FrozenInbox.__init__` in `diagnostics/verify_inbox_live.py`
- `FrozenInbox.snapshot` in `diagnostics/verify_inbox_live.py`
- `VerifiedStore` in `diagnostics/verify_inbox_live.py`
- `VerifiedStore.__init__` in `diagnostics/verify_inbox_live.py`
- `VerifiedStore.insert_events_ignore_duplicates` in `diagnostics/verify_inbox_live.py`
- `VerifiedStore.read_events` in `diagnostics/verify_inbox_live.py`
- `VerifiedStore.verify_readback` in `diagnostics/verify_inbox_live.py`
- `_require` in `diagnostics/verify_inbox_live.py`
- `main` in `diagnostics/verify_inbox_live.py`
- `verify` in `diagnostics/verify_inbox_live.py`
- `main` in `scripts/sync_inbox.py`
- `LinkedInMDPClient._get_paged` in `src/linkedin_mdp_mcp/client.py`
- `LinkedInMDPClient._next_link` in `src/linkedin_mdp_mcp/client.py`
- `LinkedInMDPClient._validate_snapshot_paging` in `src/linkedin_mdp_mcp/client.py`
- `LinkedInMDPClient.snapshot` in `src/linkedin_mdp_mcp/client.py`
- `InboxSyncError` in `src/linkedin_mdp_mcp/inbox_sync.py`
- `InboxSyncPlan` in `src/linkedin_mdp_mcp/inbox_sync.py`
- `InboxSyncSummary` in `src/linkedin_mdp_mcp/inbox_sync.py`
- `_attachments` in `src/linkedin_mdp_mcp/inbox_sync.py`
- `_event_key` in `src/linkedin_mdp_mcp/inbox_sync.py`
- `_participants` in `src/linkedin_mdp_mcp/inbox_sync.py`
- `_safe_one_to_one_row` in `src/linkedin_mdp_mcp/inbox_sync.py`
- `_timestamp` in `src/linkedin_mdp_mcp/inbox_sync.py`
- `normalize_profile_url` in `src/linkedin_mdp_mcp/inbox_sync.py`
- `plan_inbox_events` in `src/linkedin_mdp_mcp/inbox_sync.py`
- `plan_inbox_events.skip` in `src/linkedin_mdp_mcp/inbox_sync.py`

Files 29, symbols 61, CI 1/1.

*Written by prc from the code at head `dc3f451dd61a`.*
