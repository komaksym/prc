# `fix(collector): fetch prospect timestamps`

![PR card](card.png)

Upload `card.png` with this comment: images do not embed from the repo.

```mermaid
flowchart LR
n1["main"]
n2["exercise"]
n3["database"]
n4["provider"]
n5["synthetic_export"]
n6["failing_export"]
classDef added fill:#123626,stroke:#3fd68a,color:#eceef3;
classDef modified fill:#3a2b10,stroke:#f2b33d,color:#eceef3;
classDef deleted fill:#3d1a1d,stroke:#f4676f,color:#eceef3;
n1 --> n2
linkStyle 0 stroke:#3fd68a,stroke-width:2px
n5 --> n2
linkStyle 1 stroke:#3fd68a,stroke-width:2px
class n1 added
class n2 added
class n3 added
class n4 added
class n5 added
class n6 added
```

## Look here first

- `main` in `diagnostics/action-report-private-source-20261002/e2e_private_source.py`
- `exercise` in `diagnostics/action-report-private-source-20261002/e2e_private_source.py`
- `exercise.database` in `diagnostics/action-report-private-source-20261002/e2e_private_source.py`

## Risky surfaces and description vs diff

No risky surfaces.
Everything the description names is in the diff.

## Not covered by tests

- `exercise` in `diagnostics/action-report-private-source-20261002/e2e_private_source.py`
- `exercise.database` in `diagnostics/action-report-private-source-20261002/e2e_private_source.py`
- `exercise.provider` in `diagnostics/action-report-private-source-20261002/e2e_private_source.py`
- `main` in `diagnostics/action-report-private-source-20261002/e2e_private_source.py`
- `main.failing_export` in `diagnostics/action-report-private-source-20261002/e2e_private_source.py`
- `main.synthetic_export` in `diagnostics/action-report-private-source-20261002/e2e_private_source.py`

Files 12, symbols 6, CI 1/1.

*Written by prc from the code at head `306ff5a26ca6`.*
