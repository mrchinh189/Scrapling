"""Lưu/đọc dữ liệu Price Intelligence trên Supabase (fail-soft).

Khi chưa cấu hình Supabase → mọi hàm trả None / no-op, pipeline tự dùng CSV.
Khi có Supabase → DB là nguồn chân lý: collectors ghi vào đây, view-model đọc lại.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Optional

from app.config import get_settings

logger = logging.getLogger(__name__)


def _client():
    s = get_settings()
    if not s.has_supabase:
        return None
    try:
        from supabase import create_client

        return create_client(s.supabase_url, s.supabase_key)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Không tạo được Supabase client: %s", exc)
        return None


# ---------------- GHI ----------------
def persist_prices(rows: list[dict]) -> int:
    c = _client()
    if not c or not rows:
        return 0
    try:
        payload = [{
            "date": r["date"], "product": r["product"], "region": r.get("region"),
            "price_type": r.get("price_type"), "payment_term": r.get("payment_term", "at_sight"),
            "raw_price": float(r["raw_price"]), "raw_unit": r.get("raw_unit"),
            "source": r.get("source"),
        } for r in rows]
        c.table("price_master").upsert(
            payload, on_conflict="date,product,region,source,payment_term"
        ).execute()
        return len(payload)
    except Exception as exc:  # noqa: BLE001
        logger.warning("persist_prices lỗi: %s", exc)
        return 0


def persist_fx(fx: dict) -> int:
    c = _client()
    if not c or not fx:
        return 0
    try:
        c.table("fx_rates").upsert({
            "date": fx["date"], "usd_vnd": fx["usd_vnd"], "rmb_vnd": fx.get("rmb_vnd"),
        }, on_conflict="date").execute()
        return 1
    except Exception as exc:  # noqa: BLE001
        logger.warning("persist_fx lỗi: %s", exc)
        return 0


def persist_news(news: list[dict]) -> int:
    c = _client()
    if not c or not news:
        return 0
    try:
        c.table("news").upsert(news, on_conflict="url").execute()
        return len(news)
    except Exception as exc:  # noqa: BLE001
        logger.warning("persist_news lỗi: %s", exc)
        return 0


def persist_analysis(vm: dict) -> bool:
    """Ghi landed/spreads/forecast + analysis(kpi/narrative/alerts) cho parity."""
    c = _client()
    if not c:
        return False
    run_date = vm["meta"].get("price_date") or date.today().isoformat()
    try:
        # analysis (kpi/narrative/alerts/meta) — đọc chung bởi DOCX/Web/Telegram
        rows = [{"run_date": run_date, "kind": k, "payload": vm[k]}
                for k in ("kpis", "narrative", "alerts") if k in vm]
        rows.append({"run_date": run_date, "kind": "meta", "payload": vm["meta"]})
        c.table("analysis").upsert(
            [{**r, "kind": r["kind"]} for r in rows], on_conflict="run_date,kind"
        ).execute()

        # spreads
        if vm.get("spreads"):
            c.table("spreads").insert(
                [{"date": run_date, **s} for s in vm["spreads"]]
            ).execute()
        # forecast
        fc_rows = []
        for prod, fc in vm.get("forecasts", {}).items():
            for p in fc["points"]:
                fc_rows.append({"run_date": run_date, "product": prod, "week": p["week"],
                                "yhat": p["yhat"], "lower": p["lower"], "upper": p["upper"],
                                "model": fc["model"], "theils_u": fc["theils_u"],
                                "confidence": fc["confidence"], "basis": fc["basis"]})
        if fc_rows:
            c.table("forecast").upsert(fc_rows, on_conflict="run_date,product,week").execute()
        # landed
        landed_rows = []
        for prod, rows_ in vm.get("landed", {}).items():
            for r in rows_:
                landed_rows.append({"date": run_date, "product": prod, **{
                    k: r.get(k) for k in ("region", "price_type", "payment_term", "raw_price",
                                          "raw_unit", "usd_per_ton", "landed_vnd_kg",
                                          "usance_benefit", "at_sight_equiv", "is_best", "source")}})
        if landed_rows:
            c.table("landed").insert(landed_rows).execute()
        # audit_log (QC) — giữ bản ghi flag, không xoá dữ liệu
        if vm.get("audit"):
            c.table("audit_log").insert(
                [{"kind": a["kind"], "detail": a["detail"]} for a in vm["audit"]]
            ).execute()
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("persist_analysis lỗi: %s", exc)
        return False


# ---------------- ĐỌC ----------------
def load_prices() -> Optional[list[dict]]:
    c = _client()
    if not c:
        return None
    try:
        res = c.table("price_master").select(
            "date,product,region,price_type,payment_term,raw_price,raw_unit,source"
        ).order("date").execute()
        rows = res.data or []
        for r in rows:
            r["raw_price"] = float(r["raw_price"])
        return rows or None
    except Exception as exc:  # noqa: BLE001
        logger.warning("load_prices lỗi: %s", exc)
        return None


def load_fx() -> Optional[list[dict]]:
    c = _client()
    if not c:
        return None
    try:
        res = c.table("fx_rates").select("date,usd_vnd,rmb_vnd").order("date").execute()
        rows = res.data or []
        for r in rows:
            r["usd_vnd"] = float(r["usd_vnd"])
            r["rmb_vnd"] = float(r["rmb_vnd"]) if r.get("rmb_vnd") is not None else None
        return rows or None
    except Exception as exc:  # noqa: BLE001
        logger.warning("load_fx lỗi: %s", exc)
        return None


def load_news() -> Optional[list[dict]]:
    c = _client()
    if not c:
        return None
    try:
        res = c.table("news").select(
            "published_at,title,summary,url,source,category"
        ).order("published_at", desc=True).limit(12).execute()
        return res.data or None
    except Exception as exc:  # noqa: BLE001
        logger.warning("load_news lỗi: %s", exc)
        return None
