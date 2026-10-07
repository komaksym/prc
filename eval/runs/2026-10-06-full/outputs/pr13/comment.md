# `The owner had no offline plan for inbox messages.`

![PR card](card.png)

Upload `card.png` with this comment: images do not embed from the repo.

```mermaid
flowchart LR
n1["main"]
n2["_Parser"]
n3["_read"]
n4["_aware_time"]
n5["classify_dm_evidence"]
n6["DmEvidence"]
n7["_thread_suffix"]
n8["_row_identity"]
n9["_row_time"]
n10["_event_time"]
n11["anonymous_row"]
n12["main"]
classDef added fill:#123626,stroke:#3fd68a,color:#eceef3;
classDef modified fill:#3a2b10,stroke:#f2b33d,color:#eceef3;
classDef deleted fill:#3d1a1d,stroke:#f4676f,color:#eceef3;
n1 --> n2
linkStyle 0 stroke:#3fd68a,stroke-width:2px
n1 --> n3
linkStyle 1 stroke:#3fd68a,stroke-width:2px
n1 --> n4
linkStyle 2 stroke:#3fd68a,stroke-width:2px
n1 --> n5
linkStyle 3 stroke:#3fd68a,stroke-width:2px
n9 --> n4
linkStyle 4 stroke:#3fd68a,stroke-width:2px
n5 --> n6
linkStyle 5 stroke:#3fd68a,stroke-width:2px
n5 --> n4
linkStyle 6 stroke:#3fd68a,stroke-width:2px
n5 --> n10
linkStyle 7 stroke:#3fd68a,stroke-width:2px
n5 --> n8
linkStyle 8 stroke:#3fd68a,stroke-width:2px
n5 --> n9
linkStyle 9 stroke:#3fd68a,stroke-width:2px
n5 --> n7
linkStyle 10 stroke:#3fd68a,stroke-width:2px
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

Showing 12 of 42 changed symbols. Full map: map.html

## Look here first

- `classify_dm_evidence` in `src/linkedin_mdp_mcp/dm_actions.py`
- `plan_dm_actions` in `src/linkedin_mdp_mcp/dm_actions.py`
- `main` in `scripts/build_private_dm_actions.py`

## Risky surfaces and description vs diff

No risky surfaces.
Everything the description names is in the diff.

## Not covered by tests

- `_Parser` in `scripts/build_private_dm_actions.py`
- `_Parser.error` in `scripts/build_private_dm_actions.py`
- `_markdown` in `scripts/build_private_dm_actions.py`
- `_read` in `scripts/build_private_dm_actions.py`
- `_write` in `scripts/build_private_dm_actions.py`
- `main` in `scripts/build_private_dm_actions.py`
- `DmEvidence` in `src/linkedin_mdp_mcp/dm_actions.py`
- `DmMessage` in `src/linkedin_mdp_mcp/dm_actions.py`
- `DmUnknown` in `src/linkedin_mdp_mcp/dm_actions.py`
- `_aware_time` in `src/linkedin_mdp_mcp/dm_actions.py`
- `_citation_url` in `src/linkedin_mdp_mcp/dm_actions.py`
- `_connection_day` in `src/linkedin_mdp_mcp/dm_actions.py`
- `_content` in `src/linkedin_mdp_mcp/dm_actions.py`
- `_date_added` in `src/linkedin_mdp_mcp/dm_actions.py`
- `_event_time` in `src/linkedin_mdp_mcp/dm_actions.py`
- `_fingerprint` in `src/linkedin_mdp_mcp/dm_actions.py`
- `_qualified` in `src/linkedin_mdp_mcp/dm_actions.py`
- `_row_identity` in `src/linkedin_mdp_mcp/dm_actions.py`
- `_row_time` in `src/linkedin_mdp_mcp/dm_actions.py`
- `_saved_draft` in `src/linkedin_mdp_mcp/dm_actions.py`
- `_thread_suffix` in `src/linkedin_mdp_mcp/dm_actions.py`

Files 15, symbols 42, CI 1/1.

*Written by prc from the code at head `f59b09a1eb2e`.*
