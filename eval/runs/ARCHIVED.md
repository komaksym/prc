# Local historical evaluation runs

Summary. The committed `2026-10-08-release-check` is the last complete scored snapshot. It describes earlier output, not the reconciled source. Preserve its frozen verdicts.

The following local run directories remain on disk and are excluded from new commits. Their pending files are also backed up under `artifacts/reconciliation/2026-10-08/pending-before.tar.gz`.

| Local directory | Retained status |
| --- | --- |
| `2026-10-07-rebaseline` | Incomplete readers; 40 missing answers. |
| `2026-10-08-fixround1` | Incomplete pilot and drifted packet sources. |
| `2026-10-08-fixround2` | Authored boards only. |
| `2026-10-08-release-check-interrupted` | Interrupted rendering attempt. |
| `2026-10-08-release-check-interrupted-2` | Interrupted pilot rendering attempt. |
| `2026-10-08-release-candidate` | Twelve output sets, no scored readers. Superseded by later source fixes. |

Rendering staging directories and raw media stay local. Packet payload screenshots for the complete scored run are preserved in the committed snapshot. These records do not establish current-source acceptance.
