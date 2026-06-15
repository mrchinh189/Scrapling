"""Spread & chỉ báo dẫn (leading indicators) + chỉ số gốc-100."""

from __future__ import annotations

from typing import Optional

from app import configs
from app.analytics import datasource as ds


def latest_usd_ton(product: str, rows=None, fx=None) -> Optional[float]:
    series = ds.normalized_series(product, rows, fx)
    return series[-1][1] if series else None


def compute_spreads(rows=None, fx=None) -> list[dict]:
    """Tính các spread chính từ giá mới nhất (USD/tấn)."""
    rows = rows if rows is not None else ds.load_price_master()
    fx = fx if fx is not None else ds.load_fx()
    th = configs.thresholds().get("alerts", {})
    floor = float(th.get("naphtha_ethylene_floor_usd", 250))

    def g(p):
        return latest_usd_ton(p, rows, fx)

    out: list[dict] = []
    naph, eth, prop, pp, pe = g("NAPHTHA"), g("ETHYLENE"), g("PROPYLENE"), g("PP"), g("PE")

    if naph is not None and eth is not None:
        val = round(eth - naph, 1)
        signal = "resin có thể tạo đáy" if val < floor else "biên ổn định"
        out.append({"name": "Naphtha–Ethylene", "value": val, "unit": "USD/tấn",
                    "signal": signal, "note": f"ngưỡng đáy < {floor:.0f}"})
    if pp is not None and prop is not None:
        out.append({"name": "PP–Propylene", "value": round(pp - prop, 1), "unit": "USD/tấn",
                    "signal": "", "note": "biên chế biến PP"})
    if pe is not None and eth is not None:
        out.append({"name": "Ethylene–PE", "value": round(pe - eth, 1), "unit": "USD/tấn",
                    "signal": "", "note": "biên chế biến PE"})
    return out


def index_base100(products: list[str], rows=None, fx=None) -> dict[str, list[tuple[str, float]]]:
    """Chuỗi chỉ số gốc-100 cho mỗi NVL (để thấy phân kỳ resin▼ vs phụ gia▲)."""
    rows = rows if rows is not None else ds.load_price_master()
    fx = fx if fx is not None else ds.load_fx()
    out: dict[str, list[tuple[str, float]]] = {}
    for p in products:
        series = ds.normalized_series(p, rows, fx)
        if not series:
            continue
        base = series[0][1]
        if base == 0:
            continue
        out[p] = [(d, round(v / base * 100, 1)) for d, v in series]
    return out
