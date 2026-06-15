"""Kho dữ liệu Supabase (Postgres) — dùng cho môi trường production."""

from __future__ import annotations

from typing import Optional

from app.models import PriceRecord, Report


class SupabaseRepository:
    def __init__(self, url: str, key: str) -> None:
        from supabase import create_client  # import trễ để test không cần lib

        self.client = create_client(url, key)

    # --- Giá ---
    def save_prices(self, records: list[PriceRecord]) -> None:
        if not records:
            return
        self.client.table("price_records").insert([r.to_db() for r in records]).execute()

    def latest_price(self, material_code: str, before: Optional[str] = None) -> Optional[dict]:
        q = (
            self.client.table("price_records")
            .select("*")
            .eq("material_code", material_code)
            .order("scraped_at", desc=True)
            .limit(1)
        )
        if before:
            q = q.lt("scraped_at", before)
        res = q.execute()
        return res.data[0] if res.data else None

    def price_history(self, material_code: str, limit: int = 30) -> list[dict]:
        res = (
            self.client.table("price_records")
            .select("*")
            .eq("material_code", material_code)
            .order("scraped_at", desc=True)
            .limit(limit)
            .execute()
        )
        return res.data or []

    def latest_prices(self) -> list[dict]:
        # Dùng view `latest_prices` định nghĩa trong schema.sql.
        res = self.client.table("latest_prices").select("*").execute()
        return res.data or []

    # --- Báo cáo ---
    def save_report(self, report: Report) -> None:
        self.client.table("reports").upsert(
            {
                "report_id": report.report_id,
                "title": report.title,
                "summary": report.summary,
                "content_md": report.content_md,
                "docx_path": report.docx_path,
                "created_at": report.created_at.isoformat(),
            }
        ).execute()

    def list_reports(self, limit: int = 20) -> list[dict]:
        res = (
            self.client.table("reports")
            .select("report_id,title,summary,docx_path,created_at")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return res.data or []

    def get_report(self, report_id: str) -> Optional[dict]:
        res = (
            self.client.table("reports")
            .select("*")
            .eq("report_id", report_id)
            .limit(1)
            .execute()
        )
        return res.data[0] if res.data else None
