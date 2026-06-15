"""Test các tính năng nâng cao: backfill FRED, QC, charts."""

from app.collect.history import parse_fred_observations
from app.analytics.qc import check_jumps


# ---------- FRED backfill ----------
def test_parse_fred_skips_missing():
    payload = {"observations": [
        {"date": "2024-01-01", "value": "80.5"},
        {"date": "2024-02-01", "value": "."},      # giá trị thiếu → bỏ
        {"date": "2024-03-01", "value": "82.1"},
    ]}
    cfg = {"product": "BRENT", "region": "GLOBAL", "raw_unit": "usd_per_bbl",
           "price_type": "spot", "source": "FRED"}
    rows = parse_fred_observations(payload, cfg)
    assert len(rows) == 2
    assert rows[0]["product"] == "BRENT" and rows[0]["raw_price"] == 80.5
    assert rows[0]["source"] == "FRED"


# ---------- QC ----------
def test_qc_flags_big_jump():
    rows = [
        {"date": "2026-06-01", "product": "PP", "region": "US", "source": "TPE",
         "price_type": "spot", "payment_term": "at_sight", "raw_price": 1000.0,
         "raw_unit": "usd_per_ton"},
        {"date": "2026-06-08", "product": "PP", "region": "US", "source": "TPE",
         "price_type": "spot", "payment_term": "at_sight", "raw_price": 1200.0,  # +20%
         "raw_unit": "usd_per_ton"},
    ]
    fx = [{"date": "2026-06-08", "usd_vnd": 25450, "rmb_vnd": 3520}]
    audit = check_jumps(rows, fx)
    assert len(audit) == 1
    assert audit[0]["kind"] == "price_jump" and audit[0]["product"] == "PP"


def test_qc_no_flag_small_change():
    rows = [
        {"date": "2026-06-01", "product": "PP", "region": "US", "source": "TPE",
         "price_type": "spot", "payment_term": "at_sight", "raw_price": 1000.0,
         "raw_unit": "usd_per_ton"},
        {"date": "2026-06-08", "product": "PP", "region": "US", "source": "TPE",
         "price_type": "spot", "payment_term": "at_sight", "raw_price": 1020.0,  # +2%
         "raw_unit": "usd_per_ton"},
    ]
    fx = [{"date": "2026-06-08", "usd_vnd": 25450, "rmb_vnd": 3520}]
    assert check_jumps(rows, fx) == []


# ---------- Charts ----------
def test_build_index_chart(tmp_path, monkeypatch):
    import app.report.charts as charts
    monkeypatch.setattr(charts, "DATA_DIR", tmp_path)
    vm = {
        "index_base100": {"PP": [("d1", 100.0), ("d2", 98.0)],
                          "TIO2": [("d1", 100.0), ("d2", 105.0)]},
        "kpis": [{"product": "PP", "family": "resin"}, {"product": "TIO2", "family": "additive"}],
    }
    path = charts.build_index_chart(vm, "rpt-x")
    assert path and path.endswith(".png")
    from pathlib import Path
    assert Path(path).exists()
