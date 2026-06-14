"""Khi chưa cấu hình Supabase, mọi hàm intel_store fail-soft (None/0), pipeline dùng CSV."""

from app.db import intel_store
from app.config import get_settings


def test_no_supabase_loads_return_none(monkeypatch):
    get_settings.cache_clear()
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_KEY", raising=False)
    assert intel_store.load_prices() is None
    assert intel_store.load_fx() is None
    assert intel_store.load_news() is None


def test_no_supabase_persist_noop(monkeypatch):
    get_settings.cache_clear()
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_KEY", raising=False)
    assert intel_store.persist_prices([{"date": "2026-06-10", "product": "PP",
                                        "raw_price": 1, "region": "US", "source": "x"}]) == 0
    assert intel_store.persist_fx({"date": "2026-06-10", "usd_vnd": 25000}) == 0
    assert intel_store.persist_analysis({"meta": {}, "kpis": []}) is False


def test_viewmodel_falls_back_to_fixtures_without_db(monkeypatch):
    """Không có DB → view-model vẫn dựng từ fixtures (datasource fail-soft)."""
    get_settings.cache_clear()
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    from app.viewmodel import build_view_model

    vm = build_view_model()
    assert vm["meta"]["n_materials"] >= 5
