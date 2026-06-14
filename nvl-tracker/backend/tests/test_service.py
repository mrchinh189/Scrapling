"""Test pipeline so sánh giá + báo cáo, dùng SQLite tạm và không gọi mạng."""

import importlib

import pytest

from app.models import PriceChange, PriceRecord


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """Repository SQLite trỏ vào DB tạm; reset cache get_repository."""
    from app.db.sqlite_repo import SQLiteRepository
    import app.db as db

    r = SQLiteRepository(db_path=tmp_path / "test.db")
    db.get_repository.cache_clear()
    monkeypatch.setattr(db, "get_repository", lambda: r)
    # service.py import get_repository từ app.db -> patch luôn ở đó
    import app.service as service
    monkeypatch.setattr(service, "get_repository", lambda: r)
    return r


def test_compute_changes_first_run(repo):
    from app.service import compute_changes

    recs = [PriceRecord(material_code="STEEL", material_name="Thép", price=16000, unit="VND/kg")]
    changes = compute_changes(recs)
    assert len(changes) == 1
    assert changes[0].previous_price is None
    assert changes[0].change_pct is None


def test_compute_changes_with_history(repo):
    from app.service import compute_changes

    repo.save_prices([PriceRecord(material_code="STEEL", material_name="Thép", price=15000, unit="VND/kg")])
    recs = [PriceRecord(material_code="STEEL", material_name="Thép", price=16500, unit="VND/kg")]
    changes = compute_changes(recs)
    assert changes[0].previous_price == 15000
    assert changes[0].change_abs == 1500
    assert round(changes[0].change_pct, 2) == 10.0


def test_fallback_report_without_ai(monkeypatch):
    """Khi không có ANTHROPIC_API_KEY, build_analysis trả báo cáo cơ bản."""
    from app.config import get_settings
    get_settings.cache_clear()
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    import app.report.analyzer as analyzer
    importlib.reload(analyzer)

    changes = [
        PriceChange(material_code="STEEL", material_name="Thép", unit="VND/kg",
                    current_price=16500, previous_price=15000, change_abs=1500, change_pct=10.0),
    ]
    md = analyzer.build_analysis(changes, period_label="14/06/2026")
    assert "Tóm tắt điều hành" in md
    assert "Thép" in md


def test_docx_generation(tmp_path, monkeypatch):
    from app.config import DATA_DIR
    import app.report.docx_report as docx_report

    monkeypatch.setattr(docx_report, "DATA_DIR", tmp_path)
    changes = [
        PriceChange(material_code="STEEL", material_name="Thép", unit="VND/kg",
                    current_price=16500, previous_price=15000, change_abs=1500, change_pct=10.0),
    ]
    path = docx_report.build_docx("Báo cáo test", "## Tóm tắt\n- Thép tăng 10%", changes, "rpt-1")
    assert path.endswith("rpt-1.docx")
    from pathlib import Path
    assert Path(path).exists()
