# `The owner had no durable invitation history.`

![PR card](card.png)

Upload `card.png` with this comment: images do not embed from the repo.

```mermaid
flowchart LR
n1["main"]
n2["main"]
n3["reconcile_invitations"]
n4["_complete_rows"]
n5["InvitationSyncError"]
n6["plan_invitation_events"]
n7["_provider_timestamp"]
n8["InvitationSyncPlan"]
n9["InvitationSyncSummary"]
n10["snapshot"]
n11["Boundary"]
n12["__init__"]
classDef added fill:#123626,stroke:#3fd68a,color:#eceef3;
classDef modified fill:#3a2b10,stroke:#f2b33d,color:#eceef3;
classDef deleted fill:#3d1a1d,stroke:#f4676f,color:#eceef3;
n2 --> n3
linkStyle 0 stroke:#3fd68a,stroke-width:2px
n4 --> n5
linkStyle 1 stroke:#3fd68a,stroke-width:2px
n6 --> n8
linkStyle 2 stroke:#3fd68a,stroke-width:2px
n6 --> n7
linkStyle 3 stroke:#3fd68a,stroke-width:2px
n3 --> n5
linkStyle 4 stroke:#3fd68a,stroke-width:2px
n3 --> n9
linkStyle 5 stroke:#3fd68a,stroke-width:2px
n3 --> n4
linkStyle 6 stroke:#3fd68a,stroke-width:2px
n3 --> n6
linkStyle 7 stroke:#3fd68a,stroke-width:2px
class n1 added
class n2 added
class n3 added
class n4 added
class n5 added
class n6 added
class n7 added
class n8 added
class n9 added
class n10 modified
class n11 added
class n12 added
```

Showing 12 of 25 changed symbols. Full map: map.html

## Look here first

- `reconcile_invitations` in `src/linkedin_mdp_mcp/invitation_sync.py`
- `plan_invitation_events` in `src/linkedin_mdp_mcp/invitation_sync.py`
- `main` in `scripts/sync_invitations.py`

## Risky surfaces and description vs diff

- `.github/workflows/sync-invitations.yml`: CI workflow
- `artifacts/invitation_sync_verification.json`: external calls
- `scripts/sync_invitations.py`: external calls
- `scripts/verify_invitation_sync.py`: external calls
- `src/linkedin_mdp_mcp/invitation_sync.py`: external calls
- `tests/test_invitation_sync_e2e.py`: external calls

## Not covered by tests

- `main` in `scripts/sync_invitations.py`
- `main` in `scripts/verify_invitation_sync.py`
- `LinkedInMDPClient._get_paged` in `src/linkedin_mdp_mcp/client.py`
- `LinkedInMDPClient._next_link` in `src/linkedin_mdp_mcp/client.py`
- `LinkedInMDPClient.changelog` in `src/linkedin_mdp_mcp/client.py`
- `LinkedInMDPClient.snapshot` in `src/linkedin_mdp_mcp/client.py`
- `InvitationSyncError` in `src/linkedin_mdp_mcp/invitation_sync.py`
- `InvitationSyncPlan` in `src/linkedin_mdp_mcp/invitation_sync.py`
- `InvitationSyncSummary` in `src/linkedin_mdp_mcp/invitation_sync.py`
- `_complete_rows` in `src/linkedin_mdp_mcp/invitation_sync.py`
- `_provider_timestamp` in `src/linkedin_mdp_mcp/invitation_sync.py`
- `plan_invitation_events` in `src/linkedin_mdp_mcp/invitation_sync.py`

Files 17, symbols 25, CI 1/1.

*Written by prc from the code at head `1f2f010c57e1`.*
