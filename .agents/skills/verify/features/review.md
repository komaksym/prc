# Review state

A reviewer creates a local review, checks freshness, and records a decision against the displayed revision.

## Sub-features

- `review-create` writes review files and identities.
- `review-status` checks the captured basis.
- `review-decide` records a decision for expected identities.
- `review-brief` produces computed facts separately.

## How to get to it (user POV)

Run `prc review`, `status`, `decide`, or `brief` with a source.
Open index.html and entry.md before recording a decision.

## Driving it with CLI and Playwright

Preconditions: use a disposable store and `fixture:basic`.

- Run `.venv/bin/python -m prc.cli review --source fixture:basic --store "$VERIFY_STORE" --out "$VERIFY_PROOF/reviews"`. Save snapshot_id, view_id, and out_dir.
- Read manifest.json and snapshot.json. Open index.html and capture a screenshot before deciding.
- Run `.venv/bin/python -m prc.cli status --source fixture:basic --store "$VERIFY_STORE"`. Require `status: match`.
- Set `SNAPSHOT` and `VIEW` to returned identities. Run `.venv/bin/python -m prc.cli decide --source fixture:basic --store "$VERIFY_STORE" --expect-snapshot "$SNAPSHOT" --expect-view "$VIEW" --reviewer verification --decision request_changes --confidence 70`.
- Require `recorded: request_changes`. Read the stored row before cleanup:

```sh
.venv/bin/python - "$VERIFY_STORE" "$SNAPSHOT" "$VIEW" "$VERIFY_PROOF" <<'PY'
import json, sqlite3, sys
from pathlib import Path
store, snapshot, view, proof = sys.argv[1:]
with sqlite3.connect((Path(store) / 'prc.sqlite').as_uri() + '?mode=ro', uri=True) as db:
    db.row_factory = sqlite3.Row
    row = dict(db.execute('SELECT * FROM decisions ORDER BY decision_id DESC LIMIT 1').fetchone())
assert (row['snapshot_id'], row['view_id']) == (snapshot, view)
assert (row['reviewer'], row['decision'], row['confidence']) == ('verification', 'request_changes', 70)
(Path(proof) / 'decision.json').write_text(json.dumps(row, indent=2) + '\n')
PY
```
- Run status with `--clock-offset 100000`. Require stale verification evidence.
- Run `.venv/bin/python -m prc.cli brief --source fixture:basic --store "$VERIFY_STORE" --out "$VERIFY_PROOF/brief"`. Inspect the printed file.

## Gotchas

- Fixture mutations must use this run's store.
- Fixture semantic results do not prove live model review quality.
- Local decisions do not merge or publish GitHub PRs.
