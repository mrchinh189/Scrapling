"""Test collectors — chạy offline với HTML/XML/JSON mẫu, không ra mạng."""

from app.collect.web import parse_web_source, collect_web
from app.collect.eia import parse_eia_json, collect_eia
from app.collect.vietcombank import parse_vcb_xml
from app.collect.runner import _merge_csv, PRICE_COLS


# ---------- Web (Scrapling parse) ----------
WEB_HTML = """
<html><body>
  <table class="spot"><tr><td>PP Homo</td><td class="px">54.25 ¢/lb</td></tr></table>
</body></html>
"""
WEB_CFG = {
    "source": "ThePlasticsExchange", "url": "https://x", "fetcher": "static",
    "product": "PP", "region": "US", "price_type": "spot", "payment_term": "at_sight",
    "raw_unit": "cents_per_lb", "price_selector": ".px", "enabled": True,
}


def test_parse_web_source():
    row = parse_web_source(WEB_HTML, WEB_CFG, date_="2026-06-10")
    assert row is not None
    assert row["product"] == "PP"
    assert row["raw_price"] == 54.25
    assert row["raw_unit"] == "cents_per_lb"
    assert row["source"] == "ThePlasticsExchange"
    assert row["date"] == "2026-06-10"


def test_parse_web_source_placeholder_selector():
    cfg = {**WEB_CFG, "price_selector": "REPLACE_ME"}
    assert parse_web_source(WEB_HTML, cfg) is None


ANCHOR_HTML = "<html><body><p>Brent crude latest: 71.35 USD/bbl as of today</p></body></html>"


def test_parse_web_source_anchor_text():
    cfg = {"source": "X", "product": "BRENT", "region": "GLOBAL", "raw_unit": "usd_per_bbl",
           "anchor_text": "Brent crude latest"}
    row = parse_web_source(ANCHOR_HTML, cfg, date_="2026-06-10")
    assert row and row["raw_price"] == 71.35


def test_parse_web_source_page_regex():
    cfg = {"source": "X", "product": "BRENT", "region": "GLOBAL", "raw_unit": "usd_per_bbl",
           "page_regex": r"latest:\s*([0-9.,]+)"}
    row = parse_web_source(ANCHOR_HTML, cfg)
    assert row and row["raw_price"] == 71.35


def test_suggest_selectors():
    from app.collect.discover import suggest_selectors

    html = """<html><body>
      <div class="nav">Trang chủ 2024</div>
      <table><tr><td>Sản phẩm</td><td class="px">1.250 USD/tấn</td></tr></table>
    </body></html>"""
    out = suggest_selectors(html, hint="USD")
    assert out, "phải gợi ý ít nhất 1 selector"
    # Ô có 'USD/tấn' phải xếp điểm cao nhất
    assert "USD" in out[0]["text"]


def test_collect_web_failsoft(monkeypatch):
    """Nguồn lỗi tải → ok=False, không ném exception."""
    import app.collect.web as web

    def boom(*a, **k):
        raise RuntimeError("blocked")

    monkeypatch.setattr(web, "fetch_html", boom)
    results = collect_web([WEB_CFG])
    assert len(results) == 1 and results[0].ok is False


def test_collect_web_success(monkeypatch):
    import app.collect.web as web

    monkeypatch.setattr(web, "fetch_html", lambda url, fetcher="static": WEB_HTML)
    results = collect_web([WEB_CFG])
    assert results[0].ok and results[0].rows[0]["raw_price"] == 54.25


# ---------- EIA ----------
def test_parse_eia_json():
    payload = {"response": {"data": [{"period": "2026-06-10", "value": 71.35}]}}
    row = parse_eia_json(payload)
    assert row["product"] == "BRENT" and row["raw_unit"] == "usd_per_bbl"
    assert row["raw_price"] == 71.35


def test_collect_eia_no_key(monkeypatch):
    monkeypatch.delenv("EIA_KEY", raising=False)
    res = collect_eia()
    assert res.ok is False and "EIA_KEY" in res.error


# ---------- Vietcombank ----------
VCB_XML = """<?xml version="1.0" encoding="utf-8"?>
<ExrateList>
  <Exrate CurrencyCode="USD" Buy="25400" Transfer="25538" Sell="25700"/>
  <Exrate CurrencyCode="CNY" Buy="3480" Transfer="3525" Sell="3600"/>
  <DateTime>6/14/2026 4:00:00 PM</DateTime>
</ExrateList>"""


def test_parse_vcb_xml():
    fx = parse_vcb_xml(VCB_XML)
    assert fx["usd_vnd"] == 25538.0
    assert fx["rmb_vnd"] == 3525.0
    assert fx["date"] == "2026-06-14"


# ---------- Runner merge/dedup ----------
def test_merge_csv_dedup(tmp_path):
    p = tmp_path / "pm.csv"
    rows1 = [{"date": "2026-06-10", "product": "PP", "region": "US", "price_type": "spot",
              "payment_term": "at_sight", "raw_price": 54.0, "raw_unit": "cents_per_lb",
              "source": "TPE"}]
    key = lambda r: (r["date"], r["product"], r["region"], r["source"])
    assert _merge_csv(p, PRICE_COLS, rows1, key) == 1
    # Lần 2 cùng key → không thêm dòng mới (ghi đè)
    assert _merge_csv(p, PRICE_COLS, rows1, key) == 0
    import csv
    with p.open() as f:
        assert len(list(csv.DictReader(f))) == 1
