# `The owner juggled two separate private action reports.`

![PR card](card.png)

Upload `card.png` with this comment: images do not embed from the repo.

```mermaid
flowchart LR
n1["main"]
n2["_Parser"]
n3["_private_file"]
n4["CombinedReportError"]
n5["combine_action_reports"]
n6["_object"]
n7["_json_contract"]
n8["_rows"]
n9["_counts"]
n10["_profile"]
n11["cli_case"]
n12["dm"]
classDef added fill:#123626,stroke:#3fd68a,color:#eceef3;
classDef modified fill:#3a2b10,stroke:#f2b33d,color:#eceef3;
classDef deleted fill:#3d1a1d,stroke:#f4676f,color:#eceef3;
n3 --> n4
linkStyle 0 stroke:#3fd68a,stroke-width:2px
n1 --> n2
linkStyle 1 stroke:#3fd68a,stroke-width:2px
n1 --> n3
linkStyle 2 stroke:#3fd68a,stroke-width:2px
n1 --> n4
linkStyle 3 stroke:#3fd68a,stroke-width:2px
n1 --> n5
linkStyle 4 stroke:#3fd68a,stroke-width:2px
n9 --> n4
linkStyle 5 stroke:#3fd68a,stroke-width:2px
n9 --> n6
linkStyle 6 stroke:#3fd68a,stroke-width:2px
n7 --> n4
linkStyle 7 stroke:#3fd68a,stroke-width:2px
n6 --> n4
linkStyle 8 stroke:#3fd68a,stroke-width:2px
n10 --> n4
linkStyle 9 stroke:#3fd68a,stroke-width:2px
n8 --> n4
linkStyle 10 stroke:#3fd68a,stroke-width:2px
n5 --> n4
linkStyle 11 stroke:#3fd68a,stroke-width:2px
n5 --> n9
linkStyle 12 stroke:#3fd68a,stroke-width:2px
n5 --> n7
linkStyle 13 stroke:#3fd68a,stroke-width:2px
n5 --> n6
linkStyle 14 stroke:#3fd68a,stroke-width:2px
n5 --> n10
linkStyle 15 stroke:#3fd68a,stroke-width:2px
n5 --> n8
linkStyle 16 stroke:#3fd68a,stroke-width:2px
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

Showing 12 of 41 changed symbols. Full map: map.html

## Look here first

- `combine_action_reports` in `src/linkedin_mdp_mcp/combined_action_report.py`
- `GoogleDocPublisher.publish_text` in `src/linkedin_mdp_mcp/google_doc_report.py`
- `main` in `scripts/build_combined_action_report.py`

## Risky surfaces and description vs diff

- `scripts/publish_combined_action_report.py`: external calls
- `tests/e2e_combined_action_report.py`: external calls

## Not covered by tests

- `_Parser` in `scripts/build_combined_action_report.py`
- `_Parser.error` in `scripts/build_combined_action_report.py`
- `_private_file` in `scripts/build_combined_action_report.py`
- `_remove_owned` in `scripts/build_combined_action_report.py`
- `_write` in `scripts/build_combined_action_report.py`
- `_Parser` in `scripts/publish_combined_action_report.py`
- `_Parser.error` in `scripts/publish_combined_action_report.py`
- `_publish` in `scripts/publish_combined_action_report.py`
- `CombinedReportError` in `src/linkedin_mdp_mcp/combined_action_report.py`
- `_citations` in `src/linkedin_mdp_mcp/combined_action_report.py`
- `_counts` in `src/linkedin_mdp_mcp/combined_action_report.py`
- `_dm_lines` in `src/linkedin_mdp_mcp/combined_action_report.py`
- `_invitation_lines` in `src/linkedin_mdp_mcp/combined_action_report.py`
- `_json_contract` in `src/linkedin_mdp_mcp/combined_action_report.py`
- `_object` in `src/linkedin_mdp_mcp/combined_action_report.py`
- `_profile` in `src/linkedin_mdp_mcp/combined_action_report.py`
- `_rows` in `src/linkedin_mdp_mcp/combined_action_report.py`
- `_show` in `src/linkedin_mdp_mcp/combined_action_report.py`
- `_string` in `src/linkedin_mdp_mcp/combined_action_report.py`
- `GoogleDocPublisher.publish` in `src/linkedin_mdp_mcp/google_doc_report.py`
- `validate_report_text` in `src/linkedin_mdp_mcp/google_doc_report.py`

Files 14, symbols 41, CI 1/1.

*Written by prc from the code at head `1b183458ae48`.*
