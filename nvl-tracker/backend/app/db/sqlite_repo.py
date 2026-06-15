"""Kho dữ liệu SQLite — dùng khi chưa cấu hình Supabase (dev/test/offline)."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional

from app.config import DATA_DIR
from app.models import PriceRecord, Report

_SCHEMA = """
CREATE TABLE IF NOT EXISTS price_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    material_code TEXT NOT NULL,
    material_name TEXT,
    price REAL NOT NULL,
    unit TEXT,
    currency TEXT,
    source TEXT,
    source_url TEXT,
    raw_text TEXT,
    scraped_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_price_code_time
    ON price_records (material_code, scraped_at DESC);

CREATE TABLE IF NOT EXISTS reports (
    report_id TEXT PRIMARY KEY,
    title TEXT,
    summary TEXT,
    content_md TEXT,
    docx_path TEXT,
    created_at TEXT NOT NULL
);
"""


class SQLiteRepository:
    def __init__(self, db_path: Optional[Path] = None) -> None:
        self.db_path = db_path or (DATA_DIR / "nvl.db")
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.executescript(_SCHEMA)

    # --- Giá ---
    def save_prices(self, records: list[PriceRecord]) -> None:
        with self._conn() as conn:
            conn.executemany(
                """INSERT INTO price_records
                   (material_code, material_name, price, unit, currency,
                    source, source_url, raw_text, scraped_at)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                [
                    (
                        r.material_code, r.material_name, r.price, r.unit, r.currency,
                        r.source, r.source_url, r.raw_text, r.scraped_at.isoformat(),
                    )
                    for r in records
                ],
            )

    def latest_price(self, material_code: str, before: Optional[str] = None) -> Optional[dict]:
        q = "SELECT * FROM price_records WHERE material_code = ?"
        params: list = [material_code]
        if before:
            q += " AND scraped_at < ?"
            params.append(before)
        q += " ORDER BY scraped_at DESC LIMIT 1"
        with self._conn() as conn:
            row = conn.execute(q, params).fetchone()
            return dict(row) if row else None

    def price_history(self, material_code: str, limit: int = 30) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM price_records WHERE material_code = ?"
                " ORDER BY scraped_at DESC LIMIT ?",
                (material_code, limit),
            ).fetchall()
            return [dict(r) for r in rows]

    def latest_prices(self) -> list[dict]:
        """Bản ghi mới nhất của mỗi NVL."""
        with self._conn() as conn:
            rows = conn.execute(
                """SELECT p.* FROM price_records p
                   JOIN (SELECT material_code, MAX(scraped_at) AS m
                         FROM price_records GROUP BY material_code) t
                   ON p.material_code = t.material_code AND p.scraped_at = t.m
                   ORDER BY p.material_code"""
            ).fetchall()
            return [dict(r) for r in rows]

    # --- Báo cáo ---
    def save_report(self, report: Report) -> None:
        with self._conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO reports
                   (report_id, title, summary, content_md, docx_path, created_at)
                   VALUES (?,?,?,?,?,?)""",
                (
                    report.report_id, report.title, report.summary,
                    report.content_md, report.docx_path, report.created_at.isoformat(),
                ),
            )

    def list_reports(self, limit: int = 20) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT report_id, title, summary, docx_path, created_at"
                " FROM reports ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_report(self, report_id: str) -> Optional[dict]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM reports WHERE report_id = ?", (report_id,)
            ).fetchone()
            return dict(row) if row else None
