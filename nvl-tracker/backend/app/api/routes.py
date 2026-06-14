"""REST API: xem giá, chạy cập nhật thủ công, tải báo cáo."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import FileResponse

from app.config import get_settings
from app.db import get_repository

router = APIRouter()


def require_token(authorization: str = Header(default="")) -> None:
    """Bảo vệ các route ghi/chạy bằng Bearer token (nếu API_TOKEN được đặt)."""
    settings = get_settings()
    if not settings.api_token:
        return  # không đặt token => mở (chỉ nên dùng khi chạy nội bộ)
    expected = f"Bearer {settings.api_token}"
    if authorization != expected:
        raise HTTPException(status_code=401, detail="Token không hợp lệ")


@router.get("/health")
def health() -> dict:
    s = get_settings()
    return {
        "status": "ok",
        "anthropic": s.has_anthropic,
        "telegram": s.has_telegram,
        "supabase": s.has_supabase,
        "schedule": s.schedule_enabled,
    }


@router.get("/prices")
def latest_prices() -> dict:
    return {"data": get_repository().latest_prices()}


@router.get("/prices/{material_code}/history")
def price_history(material_code: str, limit: int = Query(30, ge=1, le=365)) -> dict:
    return {"data": get_repository().price_history(material_code, limit)}


@router.get("/reports")
def list_reports(limit: int = Query(20, ge=1, le=100)) -> dict:
    return {"data": get_repository().list_reports(limit)}


@router.get("/reports/{report_id}")
def get_report(report_id: str) -> dict:
    rep = get_repository().get_report(report_id)
    if not rep:
        raise HTTPException(status_code=404, detail="Không tìm thấy báo cáo")
    return rep


@router.get("/reports/{report_id}/docx")
def download_report(report_id: str):
    rep = get_repository().get_report(report_id)
    if not rep or not rep.get("docx_path") or not Path(rep["docx_path"]).exists():
        raise HTTPException(status_code=404, detail="Không tìm thấy file báo cáo")
    return FileResponse(
        rep["docx_path"],
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=f"{report_id}.docx",
    )


@router.get("/intel")
def intel_view_model() -> dict:
    """View-model Price Intelligence (KPI, at-sight, spreads, forecast, alerts, narrative).

    Đọc report-data.json nếu có (do pipeline sinh), ngược lại dựng tại chỗ từ fixtures.
    """
    from app.config import BASE_DIR

    p = BASE_DIR / "data" / "report-data.json"
    if p.exists():
        import json

        return json.loads(p.read_text(encoding="utf-8"))
    from app.viewmodel import build_view_model

    return build_view_model()


@router.post("/intel/run", dependencies=[Depends(require_token)])
def intel_run(telegram: bool = Query(False)) -> dict:
    """Chạy pipeline Price Intelligence (dựng view-model + DOCX + Telegram)."""
    from app.service import run_intel

    vm = run_intel(send_telegram=telegram)
    return {"status": "ok", "meta": vm["meta"], "artifacts": vm.get("_artifacts", {})}


@router.post("/run", dependencies=[Depends(require_token)])
def run_now(telegram: bool = Query(True), report: bool = Query(True)) -> dict:
    """Chạy cập nhật giá ngay (theo yêu cầu)."""
    from app.service import run_update

    result = run_update(send_telegram=telegram, make_report=report)
    return {
        "run_id": result.run_id,
        "status": result.status,
        "records": len(result.records),
        "changes": [c.model_dump() for c in result.changes],
        "report_id": result.report_id,
        "errors": result.errors,
    }
