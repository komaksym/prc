# `This pull request adds a date to each row of the invitation report.`

![PR card](card.png)

Upload `card.png` with this comment: images do not embed from the repo.

```mermaid
flowchart LR
n1["_make_markdown"]
n2["build_invitation_shortlist"]
n3["_date_added"]
n4["test_cli_writes_private_outputs_and_sanitized_stdout"]
n5["test_date_added_uses_exact_canonical_source_match_and_never_"]
n6["test_invalid_or_future_date_added_stays_unknown_with_safe_po"]
n7["test_missing_date_added_stays_unknown_and_does_not_change_me"]
n8["test_invitation_shortlist_e2e"]
n9["main"]
n10["run"]
n11["test_real_cap_policy_is_explicit_and_never_defaults_to_crm"]
classDef added fill:#123626,stroke:#3fd68a,color:#eceef3;
classDef modified fill:#3a2b10,stroke:#f2b33d,color:#eceef3;
classDef deleted fill:#3d1a1d,stroke:#f4676f,color:#eceef3;
n9 --- n1
n9 --- n2
n2 --> n3
linkStyle 2 stroke:#3fd68a,stroke-width:2px
n10 --- n2
n5 --> n10
linkStyle 4 stroke:#3fd68a,stroke-width:2px
n6 --> n10
linkStyle 5 stroke:#3fd68a,stroke-width:2px
n7 --> n10
linkStyle 6 stroke:#3fd68a,stroke-width:2px
n11 --- n2
class n1 modified
class n2 modified
class n3 added
class n4 modified
class n5 added
class n6 added
class n7 added
class n8 modified
```

## Look here first

- `build_invitation_shortlist` in `src/linkedin_mdp_mcp/invitation_shortlist.py`
- `_date_added` in `src/linkedin_mdp_mcp/invitation_shortlist.py`
- `_make_markdown` in `src/linkedin_mdp_mcp/invitation_shortlist.py`

## Risky surfaces and description vs diff

No risky surfaces.
Everything the description names is in the diff.

## Not covered by tests

- `_date_added` in `src/linkedin_mdp_mcp/invitation_shortlist.py`
- `_make_markdown` in `src/linkedin_mdp_mcp/invitation_shortlist.py`

Files 12, symbols 8, CI 1/1.

*Written by prc from the code at head `0c54c1ae2f0c`.*
