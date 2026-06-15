"""Test view-model dựng từ fixtures — bảo đảm đủ các mục cốt lõi."""

from app.viewmodel import build_view_model


def test_view_model_structure():
    vm = build_view_model()
    for key in ["meta", "kpis", "landed", "spreads", "forecasts", "alerts",
                "narrative", "sources"]:
        assert key in vm, f"thiếu mục {key}"

    # KPI có giá + ngày + độ tươi
    assert len(vm["kpis"]) >= 5
    pp = next(k for k in vm["kpis"] if k["product"] == "PP")
    assert pp["latest_usd_ton"] > 0
    assert pp["date"]
    assert pp["freshness"] in {"🟢", "🟡", "🔴", "⚪"}
    # PP có nhiều nguồn → có at-sight tốt nhất + chênh lệch
    assert "best_at_sight_vnd_kg" in pp

    # Spreads có naphtha–ethylene
    assert any(s["name"] == "Naphtha–Ethylene" for s in vm["spreads"])

    # Forecast PP đủ horizon
    assert vm["forecasts"]["PP"]["horizon"] == len(vm["forecasts"]["PP"]["points"])

    # Narrative 4 đoạn
    assert "Bức tranh hiện tại" in vm["narrative"]["combined_md"]

    # Nguồn có link cho nguồn công khai
    tpe = next((s for s in vm["sources"] if s["name"] == "ThePlasticsExchange"), None)
    assert tpe and tpe["url"]


def test_parity_single_source_of_truth():
    """Gọi build 2 lần cho cùng dữ liệu → KPI/landed/forecast nhất quán."""
    vm1 = build_view_model()
    vm2 = build_view_model()
    assert vm1["kpis"] == vm2["kpis"]
    assert vm1["forecasts"] == vm2["forecasts"]
