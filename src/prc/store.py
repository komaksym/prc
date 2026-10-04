"""SQLite store: content-addressed objects, atomic canonical publication, CAS decision recording."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from prc.identity import canonical_json, sha256_hex

SCHEMA = """
CREATE TABLE IF NOT EXISTS objects (sha TEXT PRIMARY KEY, data BLOB NOT NULL);
CREATE TABLE IF NOT EXISTS snapshots (
    snapshot_id TEXT PRIMARY KEY, pr_key TEXT NOT NULL, body TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS publications (
    publication_key TEXT PRIMARY KEY, snapshot_id TEXT NOT NULL, semantic_id TEXT NOT NULL,
    semantic_sha TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS views (
    view_id TEXT PRIMARY KEY, publication_key TEXT NOT NULL, snapshot_id TEXT NOT NULL,
    semantic_id TEXT NOT NULL, files TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS current (
    pr_key TEXT PRIMARY KEY, snapshot_id TEXT NOT NULL, view_id TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS decisions (
    decision_id INTEGER PRIMARY KEY AUTOINCREMENT, pr_key TEXT NOT NULL,
    snapshot_id TEXT NOT NULL, view_id TEXT NOT NULL, reviewer TEXT NOT NULL,
    decision TEXT NOT NULL, confidence INTEGER, note TEXT NOT NULL, freshness TEXT NOT NULL);
"""
DECISIONS = ("approve", "reject", "request_changes")


class StaleExpectation(RuntimeError):
    """The expected snapshot/view is no longer the local current exposure."""


class Store:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        with self._connect() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path, timeout=30, isolation_level=None)

        try:
            conn.execute("PRAGMA journal_mode=WAL")
            yield conn
        finally:
            conn.close()

    @contextmanager
    def _immediate(self) -> Iterator[sqlite3.Connection]:
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")

            try:
                yield conn
            except BaseException:
                conn.execute("ROLLBACK")
                raise
            else:
                conn.execute("COMMIT")

    def put_object(self, conn: sqlite3.Connection, data: bytes) -> str:
        digest = sha256_hex(data)
        conn.execute("INSERT OR IGNORE INTO objects(sha, data) VALUES (?, ?)", (digest, data))

        return digest

    def get_object(self, digest: str) -> bytes:
        with self._connect() as conn:
            row = conn.execute("SELECT data FROM objects WHERE sha = ?", (digest,)).fetchone()

        if row is None:
            raise KeyError(digest)

        return bytes(row[0])

    def publish(
        self,
        *,
        pr_key: str,
        snapshot_id: str,
        snapshot_body: object,
        publication_key: str,
        semantic_id: str,
        semantic_body: object,
        view_id: str,
        files: dict[str, bytes],
        supporting: dict[str, bytes],
    ) -> tuple[str, str, bool]:
        """Canonicalize one semantic artifact per publication key, then record this exposure.

        Returns (canonical_semantic_id, view_id, won). A losing candidate is discarded and the
        canonical view is returned instead; nothing partial is ever visible.
        """

        semantic_bytes = canonical_json(semantic_body)

        with self._immediate() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO publications VALUES (?, ?, ?, ?)",
                (publication_key, snapshot_id, semantic_id, sha256_hex(semantic_bytes)),
            )
            canonical = conn.execute(
                "SELECT semantic_id FROM publications WHERE publication_key = ?", (publication_key,)
            ).fetchone()[0]

            if canonical != semantic_id:
                row = conn.execute(
                    "SELECT view_id FROM views WHERE publication_key = ? ORDER BY rowid DESC",
                    (publication_key,),
                ).fetchone()
                self._set_current(conn, pr_key, snapshot_id, row[0])

                return canonical, row[0], False

            conn.execute(
                "INSERT OR IGNORE INTO snapshots VALUES (?, ?, ?)",
                (snapshot_id, pr_key, canonical_json(snapshot_body).decode()),
            )
            hashes = {name: self.put_object(conn, data) for name, data in files.items()}

            for data in supporting.values():
                self.put_object(conn, data)

            self.put_object(conn, semantic_bytes)
            conn.execute(
                "INSERT OR IGNORE INTO views VALUES (?, ?, ?, ?, ?)",
                (
                    view_id,
                    publication_key,
                    snapshot_id,
                    semantic_id,
                    json.dumps(hashes, sort_keys=True),
                ),
            )
            self._set_current(conn, pr_key, snapshot_id, view_id)

        return canonical, view_id, True

    def _set_current(
        self, conn: sqlite3.Connection, pr_key: str, snapshot_id: str, view_id: str
    ) -> None:
        conn.execute(
            "INSERT INTO current VALUES (?, ?, ?) ON CONFLICT(pr_key) DO UPDATE SET "
            "snapshot_id = excluded.snapshot_id, view_id = excluded.view_id",
            (pr_key, snapshot_id, view_id),
        )

    def canonical_semantic(self, publication_key: str) -> dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT semantic_sha FROM publications WHERE publication_key = ?",
                (publication_key,),
            ).fetchone()

        if row is None:
            raise KeyError(publication_key)

        return dict(json.loads(self.get_object(row[0])))

    def view_files(self, view_id: str) -> dict[str, bytes]:
        with self._connect() as conn:
            row = conn.execute("SELECT files FROM views WHERE view_id = ?", (view_id,)).fetchone()

        if row is None:
            raise KeyError(view_id)

        return {name: self.get_object(digest) for name, digest in json.loads(row[0]).items()}

    def current(self, pr_key: str) -> tuple[str, str] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT snapshot_id, view_id FROM current WHERE pr_key = ?", (pr_key,)
            ).fetchone()

        return None if row is None else (row[0], row[1])

    def snapshot_body(self, snapshot_id: str) -> dict[str, object]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT body FROM snapshots WHERE snapshot_id = ?", (snapshot_id,)
            ).fetchone()

        if row is None:
            raise KeyError(snapshot_id)

        return dict(json.loads(row[0]))

    def record_decision(
        self,
        *,
        pr_key: str,
        expected_snapshot_id: str,
        expected_view_id: str,
        reviewer: str,
        decision: str,
        confidence: int | None,
        note: str,
        freshness: object,
    ) -> int:
        """Compare-and-swap on the local current exposure. Does not lock GitHub."""

        if decision not in DECISIONS:
            raise ValueError(f"decision must be one of {DECISIONS}")

        if confidence is not None and not 0 <= confidence <= 100:
            raise ValueError("confidence must be 0-100")

        with self._immediate() as conn:
            row = conn.execute(
                "SELECT snapshot_id, view_id FROM current WHERE pr_key = ?", (pr_key,)
            ).fetchone()

            if row is None or (row[0], row[1]) != (expected_snapshot_id, expected_view_id):
                raise StaleExpectation("expected snapshot/view is not the current local exposure")

            cursor = conn.execute(
                "INSERT INTO decisions(pr_key, snapshot_id, view_id, reviewer, decision, confidence, "
                "note, freshness) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    pr_key,
                    expected_snapshot_id,
                    expected_view_id,
                    reviewer,
                    decision,
                    confidence,
                    note,
                    canonical_json(freshness).decode(),
                ),
            )

        return int(cursor.lastrowid or 0)

    def decisions(self, pr_key: str) -> list[dict[str, object]]:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM decisions WHERE pr_key = ? ORDER BY decision_id", (pr_key,)
            )

            return [dict(row) for row in rows]
