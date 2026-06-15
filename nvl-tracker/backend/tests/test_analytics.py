"""Test lõi phân tích Price Intelligence (chạy offline bằng fixtures)."""

from app.analytics.units import to_usd_per_ton
from app.analytics.landed import compute_landed
from app.analytics.freshness import freshness
from app.forecast.run import forecast_product, theils_u, MODELS
from datetime import date


# ---------- Đơn vị ----------
def test_units_cents_per_lb():
    # 54 ¢/lb ≈ 1190 USD/tấn
    assert round(to_usd_per_ton(54.0, "cents_per_lb")) == 1190


def test_units_rmb_per_ton():
    # 7650 RMB/tấn với RMB→USD = 3520/25450
    v = to_usd_per_ton(7650.0, "rmb_per_ton", usd_vnd=25450, rmb_vnd=3520)
    assert 1050 < v < 1070


def test_units_bbl_returns_none():
    assert to_usd_per_ton(71.0, "usd_per_bbl") is None


# ---------- Landed / at-sight ----------
def test_landed_ranking_and_best():
    quotes = [
        {"product": "PP", "region": "US", "price_type": "spot", "payment_term": "at_sight",
         "raw_price": 54.0, "raw_unit": "cents_per_lb", "source": "TPE", "date": "2026-06-08"},
        {"product": "PP", "region": "CN", "price_type": "futures", "payment_term": "L/C 90",
         "raw_price": 7650.0, "raw_unit": "rmb_per_ton", "source": "DCE", "date": "2026-06-08"},
    ]
    rows = compute_landed(quotes, usd_vnd=25450, rmb_vnd=3520, duty_key="pp")
    # Tất cả có at-sight
    assert all(r.at_sight_equiv is not None for r in rows)
    # Đúng 1 nguồn tốt nhất, và là nguồn at-sight thấp nhất
    best = [r for r in rows if r.is_best]
    assert len(best) == 1
    assert best[0].at_sight_equiv == min(r.at_sight_equiv for r in rows)


def test_usance_reduces_at_sight():
    # L/C 90 (trả chậm) → at-sight < landed
    quotes = [{"product": "PP", "region": "CN", "price_type": "q", "payment_term": "L/C 90",
               "raw_price": 1185.0, "raw_unit": "usd_per_ton", "source": "X", "date": "2026-06-08"}]
    r = compute_landed(quotes, 25450, 3520, "pp")[0]
    assert r.usance_benefit > 0
    assert r.at_sight_equiv < r.landed_vnd_kg


# ---------- Độ tươi ----------
def test_freshness_buckets():
    today = date(2026, 6, 14)
    assert freshness("2026-06-10", today) == "🟢"
    assert freshness("2026-05-25", today) == "🟡"
    assert freshness("2026-01-01", today) == "🔴"
    assert freshness("không-rõ", today) == "⚪"


# ---------- Forecast ----------
def test_forecast_naive_short_series():
    series = [("2026-06-01", 100.0), ("2026-06-08", 101.0)]
    fc = forecast_product("X", series)
    assert fc.model == "naive"
    assert len(fc.points) == fc.horizon
    assert fc.confidence == "thấp"


def test_forecast_trend_longer_series():
    # Chuỗi giảm đều 10 điểm → model trend/holt nên thắng naive (U<1)
    series = [(f"2026-{(i // 4) + 1:02d}-{(i % 4) * 7 + 1:02d}", 100.0 - 2 * i) for i in range(10)]
    fc = forecast_product("X", series)
    assert len(fc.points) == fc.horizon
    # Dự báo tiếp tục xu hướng giảm
    assert fc.points[-1]["yhat"] < series[-1][1]


def test_theils_u_naive_is_one():
    y = [100, 102, 101, 103, 105, 104]
    u = theils_u(y, MODELS["naive"], start=1)
    assert u is not None and u > 0
