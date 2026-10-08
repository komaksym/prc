# `One sync stages LinkedIn evidence and applies only with apply.`

![PR card](card.png)

Upload `card.png` with this comment: images do not embed from the repo.

```mermaid
flowchart LR
n1["reconcile_invitations"]
n2["_complete_rows"]
n3["InvitationSyncError"]
n4["plan_invitation_events"]
n5["_provider_timestamp"]
n6["InvitationSyncPlan"]
n7["InvitationSyncSummary"]
n8["main"]
n9["_Parser"]
n10["run"]
n11["Services"]
n12["__init__"]
classDef added fill:#123626,stroke:#3fd68a,color:#eceef3;
classDef modified fill:#3a2b10,stroke:#f2b33d,color:#eceef3;
classDef deleted fill:#3d1a1d,stroke:#f4676f,color:#eceef3;
n8 --> n9
linkStyle 0 stroke:#3fd68a,stroke-width:2px
n8 --> n10
linkStyle 1 stroke:#3fd68a,stroke-width:2px
n2 --> n3
linkStyle 2 stroke:#3fd68a,stroke-width:2px
n4 --> n6
linkStyle 3 stroke:#3fd68a,stroke-width:2px
n4 --> n5
linkStyle 4 stroke:#3fd68a,stroke-width:2px
n1 --> n3
linkStyle 5 stroke:#3fd68a,stroke-width:2px
n1 --> n7
linkStyle 6 stroke:#3fd68a,stroke-width:2px
n1 --> n2
linkStyle 7 stroke:#3fd68a,stroke-width:2px
n1 --> n4
linkStyle 8 stroke:#3fd68a,stroke-width:2px
class n1 added
class n2 added
class n3 added
class n4 added
class n5 added
class n6 added
class n7 added
class n8 added
class n9 added
class n10 added
class n11 added
class n12 added
```

Showing 12 of 48 changed symbols. Full map: map.html

## Look here first

- `sync_actual_actions` in `src/linkedin_mdp_mcp/actual_action_sync.py`
- `acquire_actual_action_sources` in `src/linkedin_mdp_mcp/actual_action_sync.py`
- `plan_verified_dm_events` in `src/linkedin_mdp_mcp/actual_action_sync.py`

## Risky surfaces and description vs diff

- `scripts/sync_actual_actions.py`: external calls
- `src/linkedin_mdp_mcp/actual_action_sync.py`: external calls
- `src/linkedin_mdp_mcp/invitation_sync.py`: external calls

## Not covered by tests

- `_Parser` in `scripts/sync_actual_actions.py`
- `_Parser.error` in `scripts/sync_actual_actions.py`
- `_new_output_path` in `scripts/sync_actual_actions.py`
- `_write_manifest` in `scripts/sync_actual_actions.py`
- `main` in `scripts/sync_actual_actions.py`
- `ActualActionSyncSummary` in `src/linkedin_mdp_mcp/actual_action_sync.py`
- `ActualSyncError` in `src/linkedin_mdp_mcp/actual_action_sync.py`
- `ActualSyncError.__init__` in `src/linkedin_mdp_mcp/actual_action_sync.py`
- `DmSyncPlan` in `src/linkedin_mdp_mcp/actual_action_sync.py`
- `_aware` in `src/linkedin_mdp_mcp/actual_action_sync.py`
- `_digest` in `src/linkedin_mdp_mcp/actual_action_sync.py`
- `_fresh` in `src/linkedin_mdp_mcp/actual_action_sync.py`
- `_matched_source` in `src/linkedin_mdp_mcp/actual_action_sync.py`
- `_validate_sources` in `src/linkedin_mdp_mcp/actual_action_sync.py`
- `LinkedInMDPClient._get_paged` in `src/linkedin_mdp_mcp/client.py`
- `LinkedInMDPClient._next_link` in `src/linkedin_mdp_mcp/client.py`
- `LinkedInMDPClient.changelog` in `src/linkedin_mdp_mcp/client.py`
- `InvitationSyncError` in `src/linkedin_mdp_mcp/invitation_sync.py`
- `InvitationSyncPlan` in `src/linkedin_mdp_mcp/invitation_sync.py`
- `InvitationSyncSummary` in `src/linkedin_mdp_mcp/invitation_sync.py`
- `_complete_rows` in `src/linkedin_mdp_mcp/invitation_sync.py`
- `_provider_timestamp` in `src/linkedin_mdp_mcp/invitation_sync.py`
- `plan_invitation_events` in `src/linkedin_mdp_mcp/invitation_sync.py`
- `reconcile_invitations` in `src/linkedin_mdp_mcp/invitation_sync.py`

Files 15, symbols 48, CI 1/1.

*Written by prc from the code at head `df74ac34650a`.*
