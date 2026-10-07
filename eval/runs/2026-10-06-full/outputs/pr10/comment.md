# `The invitation report ignored history outside the CRM.`

![PR card](card.png)

Upload `card.png` with this comment: images do not embed from the repo.

```mermaid
flowchart LR
n1["main"]
n2["_arguments"]
n3["_Parser"]
n4["_private_json"]
n5["ShortlistInputError"]
n6["build_invitation_shortlist"]
n7["_object"]
n8["_timestamp"]
n9["_validate_provider_snapshot"]
n10["_array"]
n11["candidate"]
n12["citation"]
classDef added fill:#123626,stroke:#3fd68a,color:#eceef3;
classDef modified fill:#3a2b10,stroke:#f2b33d,color:#eceef3;
classDef deleted fill:#3d1a1d,stroke:#f4676f,color:#eceef3;
n2 --> n3
linkStyle 0 stroke:#3fd68a,stroke-width:2px
n4 --> n5
linkStyle 1 stroke:#3fd68a,stroke-width:2px
n1 --> n2
linkStyle 2 stroke:#3fd68a,stroke-width:2px
n1 --> n4
linkStyle 3 stroke:#3fd68a,stroke-width:2px
n1 --> n5
linkStyle 4 stroke:#3fd68a,stroke-width:2px
n1 --> n6
linkStyle 5 stroke:#3fd68a,stroke-width:2px
n10 --> n5
linkStyle 6 stroke:#3fd68a,stroke-width:2px
n7 --> n5
linkStyle 7 stroke:#3fd68a,stroke-width:2px
n8 --> n5
linkStyle 8 stroke:#3fd68a,stroke-width:2px
n9 --> n5
linkStyle 9 stroke:#3fd68a,stroke-width:2px
n9 --> n10
linkStyle 10 stroke:#3fd68a,stroke-width:2px
n9 --> n7
linkStyle 11 stroke:#3fd68a,stroke-width:2px
n6 --> n5
linkStyle 12 stroke:#3fd68a,stroke-width:2px
n6 --> n10
linkStyle 13 stroke:#3fd68a,stroke-width:2px
n6 --> n7
linkStyle 14 stroke:#3fd68a,stroke-width:2px
n6 --> n8
linkStyle 15 stroke:#3fd68a,stroke-width:2px
n6 --> n9
linkStyle 16 stroke:#3fd68a,stroke-width:2px
n11 --> n12
linkStyle 17 stroke:#3fd68a,stroke-width:2px
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

Showing 12 of 128 changed symbols. Full map: map.html

## Look here first

- `build_invitation_shortlist` in `src/linkedin_mdp_mcp/invitation_shortlist.py`
- `ShortlistInputError` in `src/linkedin_mdp_mcp/invitation_shortlist.py`
- `_citation_list` in `src/linkedin_mdp_mcp/invitation_shortlist.py`

## Risky surfaces and description vs diff

No risky surfaces.
Everything the description names is in the diff.

## Not covered by tests

- `_Parser` in `scripts/build_invitation_shortlist.py`
- `_Parser.error` in `scripts/build_invitation_shortlist.py`
- `_arguments` in `scripts/build_invitation_shortlist.py`
- `_private_json` in `scripts/build_invitation_shortlist.py`
- `_write_new_private` in `scripts/build_invitation_shortlist.py`
- `main` in `scripts/build_invitation_shortlist.py`
- `Citation` in `src/linkedin_mdp_mcp/invitation_shortlist.py`
- `Company` in `src/linkedin_mdp_mcp/invitation_shortlist.py`
- `CurrentEmployer` in `src/linkedin_mdp_mcp/invitation_shortlist.py`
- `Factor` in `src/linkedin_mdp_mcp/invitation_shortlist.py`
- `HistoryEvidence` in `src/linkedin_mdp_mcp/invitation_shortlist.py`
- `QualifiedCandidate` in `src/linkedin_mdp_mcp/invitation_shortlist.py`
- `ShortlistInputError` in `src/linkedin_mdp_mcp/invitation_shortlist.py`
- `ShortlistInputError.__init__` in `src/linkedin_mdp_mcp/invitation_shortlist.py`
- `_array` in `src/linkedin_mdp_mcp/invitation_shortlist.py`
- `_attributes` in `src/linkedin_mdp_mcp/invitation_shortlist.py`
- `_candidate` in `src/linkedin_mdp_mcp/invitation_shortlist.py`
- `_candidate_json` in `src/linkedin_mdp_mcp/invitation_shortlist.py`
- `_citation_json` in `src/linkedin_mdp_mcp/invitation_shortlist.py`
- `_citation_list` in `src/linkedin_mdp_mcp/invitation_shortlist.py`
- `_company_registry` in `src/linkedin_mdp_mcp/invitation_shortlist.py`
- `_crm_history` in `src/linkedin_mdp_mcp/invitation_shortlist.py`
- `_crm_invited` in `src/linkedin_mdp_mcp/invitation_shortlist.py`
- `_crm_positive` in `src/linkedin_mdp_mcp/invitation_shortlist.py`
- `_crm_sent` in `src/linkedin_mdp_mcp/invitation_shortlist.py`
- `_current_employers` in `src/linkedin_mdp_mcp/invitation_shortlist.py`
- `_date` in `src/linkedin_mdp_mcp/invitation_shortlist.py`
- `_event_history` in `src/linkedin_mdp_mcp/invitation_shortlist.py`
- `_event_suppressed` in `src/linkedin_mdp_mcp/invitation_shortlist.py`
- `_factor_score` in `src/linkedin_mdp_mcp/invitation_shortlist.py`
- `_history_evidence_id` in `src/linkedin_mdp_mcp/invitation_shortlist.py`
- `_key` in `src/linkedin_mdp_mcp/invitation_shortlist.py`
- `_legacy_name` in `src/linkedin_mdp_mcp/invitation_shortlist.py`
- `_make_markdown` in `src/linkedin_mdp_mcp/invitation_shortlist.py`
- `_object` in `src/linkedin_mdp_mcp/invitation_shortlist.py`
- `_optional_timestamp` in `src/linkedin_mdp_mcp/invitation_shortlist.py`
- `_parse_factor` in `src/linkedin_mdp_mcp/invitation_shortlist.py`
- `_profile_queue_id` in `src/linkedin_mdp_mcp/invitation_shortlist.py`
- `_provider_history` in `src/linkedin_mdp_mcp/invitation_shortlist.py`
- `_provider_local_date` in `src/linkedin_mdp_mcp/invitation_shortlist.py`
- `_reconcile_legacy_history` in `src/linkedin_mdp_mcp/invitation_shortlist.py`
- `_source_history` in `src/linkedin_mdp_mcp/invitation_shortlist.py`
- `_source_profile_index` in `src/linkedin_mdp_mcp/invitation_shortlist.py`
- `_stable_hash` in `src/linkedin_mdp_mcp/invitation_shortlist.py`
- `_suppressed` in `src/linkedin_mdp_mcp/invitation_shortlist.py`
- `_timestamp` in `src/linkedin_mdp_mcp/invitation_shortlist.py`
- `_validate_database_snapshot` in `src/linkedin_mdp_mcp/invitation_shortlist.py`
- `_validate_provider_snapshot` in `src/linkedin_mdp_mcp/invitation_shortlist.py`

Files 14, symbols 128, CI 1/1.

*Written by prc from the code at head `5498b6c605ec`.*
