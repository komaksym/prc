# `The bundle now carries the changelog.`

![PR card](card.png)

Upload `card.png` with this comment: images do not embed from the repo.

```mermaid
flowchart LR
n1["provider"]
n2["collect_sources"]
n3["main"]
n4["seeded_provider"]
n5["changelog"]
n6["_get_paged"]
n7["_next_link"]
n8["export"]
n9["snapshot"]
classDef added fill:#123626,stroke:#3fd68a,color:#eceef3;
classDef modified fill:#3a2b10,stroke:#f2b33d,color:#eceef3;
classDef deleted fill:#3d1a1d,stroke:#f4676f,color:#eceef3;
n8 --- n2
n6 --- n7
n5 --- n6
n9 --- n6
class n1 modified
class n2 modified
class n3 modified
class n4 added
class n5 modified
class n6 modified
class n7 modified
```

## Look here first

- `LinkedInMDPClient._get_paged` in `src/linkedin_mdp_mcp/client.py`
- `collect_sources` in `diagnostics/action-report-private-source-20261002/collect_private_source.py`
- `LinkedInMDPClient._next_link` in `src/linkedin_mdp_mcp/client.py`

## Risky surfaces and description vs diff

No risky surfaces.
Everything the description names is in the diff.

## Not covered by tests

- `collect_sources` in `diagnostics/action-report-private-source-20261002/collect_private_source.py`
- `LinkedInMDPClient._get_paged` in `src/linkedin_mdp_mcp/client.py`
- `LinkedInMDPClient._next_link` in `src/linkedin_mdp_mcp/client.py`
- `LinkedInMDPClient.changelog` in `src/linkedin_mdp_mcp/client.py`

Files 13, symbols 7, CI 1/1.

*Written by prc from the code at head `66e8fe47d8cf`.*
