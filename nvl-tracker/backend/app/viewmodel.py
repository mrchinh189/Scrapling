"""View-model dùng chung — TÍNH MỘT LẦN, mọi nơi (DOCX/Web/Telegram) đọc lại.

Bảo đảm parity: DOCX = Web = Telegram cùng số liệu, cùng nguồn, cùng narrative.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from app import configs
from app.analytics import datasource as ds
from app.analytics import spreads as spreads_mod
from app.analytics.alerts import build_alerts
from app.analytics.freshness import freshness
from app.analytics.landed import compute_landed, landed_spread
from app.analytics.narrative import build_narrative
from app.config import BASE_DIR
from app.forecast.run import forecast_all


def _change_pct(series: list[tuple[str, float]]) -> Optional[float]:
    if len(series) < 2 or series[-2][1] == 0:
        return None
    return round((series[-1][1] - series[-2][1]) / series[-2][1] * 100, 2)


def build_view_model(rows=None, fx=None) -> dict:
    rows = rows if rows is not None else ds.load_price_master()
    fx = fx if fx is not None else ds.load_fx()
    fxn = ds.latest_fx(fx)
    mats = configs.materials()
    mat_by_key = {m["key"]: m for m in mats}

    # --- KPI + landed cho từng NVL ---
    kpis: list[dict] = []
    landed_by_product: dict[str, list] = {}
    series_map: dict[str, list[tuple[str, float]]] = {}

    for m in sorted(mats, key=lambda x: (-x.get("spend_weight", 0), x.get("priority", 9))):
        prod = m["key"]
        series = ds.normalized_series(prod, rows, fx)
        if not series:
            continue
        series_map[prod] = series
        latest_date = series[-1][0]
        kpi = {
            "product": prod,
            "label": m.get("label", prod),
            "family": m.get("family", ""),
            "spend_weight": m.get("spend_weight", 0),
            "latest_usd_ton": series[-1][1],
            "change_pct": _change_pct(series),
            "date": latest_date,
            "freshness": freshness(latest_date),
        }
        # landed/at-sight (bỏ qua feedstock dạng bbl)
        duty_key = m.get("duty_key")
        if duty_key:
            quotes = ds.latest_quotes(prod, rows)
            lrows = compute_landed(quotes, fxn["usd_vnd"], fxn["rmb_vnd"], duty_key)
            landed_by_product[prod] = lrows
            best = next((r for r in lrows if r.is_best), None)
            if best:
                kpi["best_at_sight_vnd_kg"] = best.at_sight_equiv
                kpi["best_source"] = best.source
                kpi["landed_spread"] = landed_spread(lrows)
        kpis.append(kpi)

    # --- Spreads, index, forecast ---
    spreads = spreads_mod.compute_spreads(rows, fx)
    index100 = spreads_mod.index_base100(list(series_map.keys()), rows, fx)
    forecasts = forecast_all(series_map)

    # --- QC (flag biến động bất thường, giữ dữ liệu) ---
    from app.analytics.qc import check_jumps

    audit = check_jumps(rows, fx)

    # --- Alerts + narrative ---
    alerts = build_alerts(landed_by_product, spreads, forecasts, kpis)
    narrative = build_narrative(kpis, spreads, alerts)

    # --- Bảng nguồn & độ tươi (kèm link + ngày giá gần nhất) ---
    src_latest: dict[str, str] = {}
    for r in rows:
        if r["source"] not in src_latest or r["date"] > src_latest[r["source"]]:
            src_latest[r["source"]] = r["date"]
    sources = []
    for name, last_date in sorted(src_latest.items()):
        label, url = configs.source_link(name)
        sources.append({"name": name, "label": label, "url": url,
                        "latest_date": last_date, "freshness": freshness(last_date)})

    return {
        "meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "price_date": ds.latest_date(rows),
            "usd_vnd": fxn["usd_vnd"],
            "rmb_vnd": fxn["rmb_vnd"],
            "n_materials": len(kpis),
        },
        "kpis": kpis,
        "landed": {p: [vars(r) for r in rows_] for p, rows_ in landed_by_product.items()},
        "spreads": spreads,
        "index_base100": {p: s for p, s in index100.items()},
        "forecasts": {p: _fc_to_dict(f) for p, f in forecasts.items()},
        "alerts": alerts,
        "narrative": narrative,
        "sources": sources,
        "news": ds.load_news(),
        "audit": audit,
    }


def _fc_to_dict(fc) -> dict:
    return {
        "product": fc.product, "model": fc.model, "horizon": fc.horizon,
        "points": fc.points, "theils_u": fc.theils_u,
        "confidence": fc.confidence, "basis": fc.basis,
    }


def export_json(vm: dict, path: Optional[Path] = None) -> str:
    """Ghi view-model ra JSON cho frontend (web/public/report-data.json)."""
    path = path or (BASE_DIR / "data" / "report-data.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(vm, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)
