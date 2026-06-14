"""Forecast baseline thuần Python (không cần statsmodels/prophet).

Tự hạ cấp model theo độ dài chuỗi; chọn model có Theil's U < 1 (tốt hơn naive),
ngược lại dùng naive. Số dự báo do THỐNG KÊ quyết định (Claude chỉ diễn giải).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable, Optional

from app import configs


@dataclass
class ForecastResult:
    product: str
    model: str
    horizon: int
    points: list[dict] = field(default_factory=list)  # [{week, yhat, lower, upper}]
    theils_u: Optional[float] = None
    confidence: str = "thấp"
    basis: str = "spot"


# ---------- Các model dự báo (trả hàm dự báo h bước) ----------

def _naive(y: list[float]) -> Callable[[int], float]:
    last = y[-1]
    return lambda h: last


def _linear_trend(y: list[float]) -> Callable[[int], float]:
    n = len(y)
    xs = list(range(n))
    mx = sum(xs) / n
    my = sum(y) / n
    denom = sum((x - mx) ** 2 for x in xs) or 1e-9
    b = sum((xs[i] - mx) * (y[i] - my) for i in range(n)) / denom
    a = my - b * mx
    return lambda h: a + b * (n - 1 + h)


def _holt(y: list[float], alpha: float = 0.5, beta: float = 0.3) -> Callable[[int], float]:
    level = y[0]
    trend = y[1] - y[0] if len(y) > 1 else 0.0
    for val in y[1:]:
        prev_level = level
        level = alpha * val + (1 - alpha) * (level + trend)
        trend = beta * (level - prev_level) + (1 - beta) * trend
    return lambda h: level + h * trend


MODELS: dict[str, Callable[[list[float]], Callable[[int], float]]] = {
    "naive": _naive,
    "linear": _linear_trend,
    "holt": _holt,
}


def theils_u(y: list[float], fit: Callable[[list[float]], Callable[[int], float]],
             start: int) -> Optional[float]:
    """Theil's U2 walk-forward một bước. < 1 = tốt hơn naive (no-change)."""
    num = den = 0.0
    for t in range(start, len(y) - 1):
        pred = fit(y[: t + 1])(1)
        actual_next = y[t + 1]
        actual_now = y[t]
        num += (pred - actual_next) ** 2
        den += (actual_next - actual_now) ** 2
    if den == 0:
        return None
    return math.sqrt(num) / math.sqrt(den)


def _residual_sigma(y: list[float], fit, start: int) -> float:
    errs = []
    for t in range(start, len(y) - 1):
        errs.append(fit(y[: t + 1])(1) - y[t + 1])
    if not errs:
        return abs(y[-1]) * 0.03
    mean = sum(errs) / len(errs)
    var = sum((e - mean) ** 2 for e in errs) / len(errs)
    return math.sqrt(var)


def forecast_product(product: str, series: list[tuple[str, float]]) -> ForecastResult:
    th = configs.thresholds().get("forecast", {})
    horizon = int(th.get("horizon_weeks", 6))
    min_trend = int(th.get("min_points_trend", 8))

    y = [v for _, v in series]
    n = len(y)

    if n < int(th.get("min_points_naive", 4)):
        # Quá ngắn → chỉ giữ mức hiện tại, ghi rõ hạn chế
        last = y[-1] if y else 0.0
        pts = [{"week": h, "yhat": round(last, 1), "lower": round(last * 0.95, 1),
                "upper": round(last * 1.05, 1)} for h in range(1, horizon + 1)]
        return ForecastResult(product, "naive", horizon, pts, None, "thấp",
                              "chuỗi chưa đủ")

    # Ứng viên model theo độ dài
    candidates = ["naive"]
    if n >= min_trend:
        candidates += ["linear", "holt"]

    start = max(1, n // 3)
    best_model, best_u = "naive", None
    for name in candidates:
        u = theils_u(y, MODELS[name], start)
        if u is None:
            continue
        if name == "naive":
            best_u = u if best_u is None else best_u
            continue
        if u < 1 and (best_u is None or u < best_u or best_model == "naive"):
            best_model, best_u = name, u

    fit = MODELS[best_model](y)
    sigma = _residual_sigma(y, MODELS[best_model], start)
    pts = []
    for h in range(1, horizon + 1):
        yhat = fit(h)
        band = 1.96 * sigma * math.sqrt(h)
        pts.append({"week": h, "yhat": round(yhat, 1),
                    "lower": round(yhat - band, 1), "upper": round(yhat + band, 1)})

    if n >= 24 and best_u is not None and best_u < 0.8:
        confidence = "cao"
    elif n >= min_trend and best_u is not None and best_u < 1:
        confidence = "vừa"
    else:
        confidence = "thấp"

    return ForecastResult(product, best_model, horizon, pts,
                          round(best_u, 3) if best_u is not None else None,
                          confidence, "spot dài" if n >= 24 else "spot")


def forecast_all(series_map: dict[str, list[tuple[str, float]]]) -> dict[str, ForecastResult]:
    return {p: forecast_product(p, s) for p, s in series_map.items() if s}
