# `This pull request changes who makes the LinkedIn invitation shortlist.`

![PR card](card.png)

Upload `card.png` with this comment: images do not embed from the repo.

```mermaid
flowchart LR
n1["build_invitation_shortlist"]
n2["_current_employers"]
n3["CurrentEmployer"]
n4["_make_markdown"]
n5["employer_set"]
n6["test_conflicting_canonical_present_sets_are_not_unioned"]
n7["test_identical_canonical_present_sets_merge_citations_only"]
n8["test_invalid_present_sets_keep_global_withholding"]
n9["test_legacy_employer_rows_reject_completeness_metadata"]
n10["test_present_set_charges_each_company_once_and_keeps_flat_au"]
n11["test_present_set_selection_requires_and_consumes_every_compa"]
n12["test_present_set_membership_does_not_invent_primary_employer"]
classDef added fill:#123626,stroke:#3fd68a,color:#eceef3;
classDef modified fill:#3a2b10,stroke:#f2b33d,color:#eceef3;
classDef deleted fill:#3d1a1d,stroke:#f4676f,color:#eceef3;
n2 --- n3
n1 --- n2
n6 --> n5
linkStyle 2 stroke:#3fd68a,stroke-width:2px
n7 --> n5
linkStyle 3 stroke:#3fd68a,stroke-width:2px
n8 --> n5
linkStyle 4 stroke:#3fd68a,stroke-width:2px
n9 --> n5
linkStyle 5 stroke:#3fd68a,stroke-width:2px
n10 --> n5
linkStyle 6 stroke:#3fd68a,stroke-width:2px
n12 --> n5
linkStyle 7 stroke:#3fd68a,stroke-width:2px
n11 --> n5
linkStyle 8 stroke:#3fd68a,stroke-width:2px
class n1 modified
class n2 modified
class n3 modified
class n4 modified
class n5 added
class n6 added
class n7 added
class n8 added
class n9 added
class n10 added
class n11 added
class n12 added
```

Showing 12 of 13 changed symbols. Full map: map.html

## Look here first

- `build_invitation_shortlist` in `src/linkedin_mdp_mcp/invitation_shortlist.py`
- `_current_employers` in `src/linkedin_mdp_mcp/invitation_shortlist.py`
- `CurrentEmployer` in `src/linkedin_mdp_mcp/invitation_shortlist.py`

## Risky surfaces and description vs diff

No risky surfaces.
Everything the description names is in the diff.

## Not covered by tests

- `CurrentEmployer` in `src/linkedin_mdp_mcp/invitation_shortlist.py`
- `_current_employers` in `src/linkedin_mdp_mcp/invitation_shortlist.py`
- `_make_markdown` in `src/linkedin_mdp_mcp/invitation_shortlist.py`

Files 11, symbols 13, CI 1/1.

*Written by prc from the code at head `537a16de03f9`.*
