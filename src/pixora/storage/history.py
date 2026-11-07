"""Histórico local de downloads em SQLite.

Apenas metadados são armazenados (nunca as imagens). Baixar a mesma publicação
para a mesma pasta atualiza o registro existente em vez de duplicá-lo.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from . import paths

log = logging.getLogger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS downloads (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    shortcode    TEXT NOT NULL,
    url          TEXT NOT NULL,
    owner        TEXT,
    folder       TEXT NOT NULL,
    saved_count  INTEGER NOT NULL DEFAULT 0,
    failed_count INTEGER NOT NULL DEFAULT 0,
    files        TEXT NOT NULL DEFAULT '[]',
    created_at   TEXT NOT NULL,
    updated_at   TEXT NOT NULL,
    UNIQUE (shortcode, folder)
);
CREATE INDEX IF NOT EXISTS idx_downloads_updated ON downloads(updated_at DESC);
"""


@dataclass(frozen=True)
class HistoryEntry:
    id: int
    shortcode: str
    url: str
    owner: str | None
    folder: str
    saved_count: int
    failed_count: int
    files: tuple[str, ...]
    created_at: datetime
    updated_at: datetime


class HistoryStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or (paths.config_dir() / "history.db")
        self._lock = threading.Lock()
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        """Abre, confirma (commit) e fecha a conexão — evita arquivos presos no Windows."""
        conn = sqlite3.connect(self.path, timeout=5)
        conn.row_factory = sqlite3.Row
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def record(self, *, shortcode: str, url: str, owner: str | None, folder: Path,
               saved_files: list[str], failed_count: int) -> None:
        now = datetime.now().isoformat(timespec="seconds")
        folder_s = str(Path(folder).resolve())
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT files FROM downloads WHERE shortcode=? AND folder=?", (shortcode, folder_s)
            ).fetchone()
            if row:
                merged = list(dict.fromkeys([*json.loads(row["files"]), *saved_files]))
                conn.execute(
                    "UPDATE downloads SET files=?, saved_count=?, failed_count=?, owner=COALESCE(?, owner),"
                    " updated_at=? WHERE shortcode=? AND folder=?",
                    (json.dumps(merged), len(merged), failed_count, owner, now, shortcode, folder_s),
                )
            else:
                conn.execute(
                    "INSERT INTO downloads (shortcode, url, owner, folder, saved_count, failed_count, files,"
                    " created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?)",
                    (shortcode, url, owner, folder_s, len(saved_files), failed_count,
                     json.dumps(saved_files), now, now),
                )

    def list(self, limit: int = 500) -> list[HistoryEntry]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM downloads ORDER BY updated_at DESC, id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [
            HistoryEntry(
                id=r["id"], shortcode=r["shortcode"], url=r["url"], owner=r["owner"], folder=r["folder"],
                saved_count=r["saved_count"], failed_count=r["failed_count"],
                files=tuple(json.loads(r["files"])),
                created_at=datetime.fromisoformat(r["created_at"]),
                updated_at=datetime.fromisoformat(r["updated_at"]),
            )
            for r in rows
        ]

    def delete(self, entry_id: int) -> None:
        with self._lock, self._connect() as conn:
            conn.execute("DELETE FROM downloads WHERE id=?", (entry_id,))

    def clear(self) -> None:
        with self._lock, self._connect() as conn:
            conn.execute("DELETE FROM downloads")
