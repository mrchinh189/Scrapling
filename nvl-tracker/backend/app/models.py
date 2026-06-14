"""Các kiểu dữ liệu dùng chung (Pydantic)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


def _now() -> datetime:
    return datetime.now(timezone.utc)


class SourceConfig(BaseModel):
    """Định nghĩa một nguồn crawl giá NVL (nạp từ sources.yaml)."""

    code: str  # mã NVL, vd: "STEEL", "CEMENT"
    name: str  # tên hiển thị, vd: "Thép xây dựng"
    unit: str = "VND"  # đơn vị giá, vd: "VND/kg"
    url: str
    fetcher: str = "static"  # static | stealthy (dùng trình duyệt ẩn danh)
    # Bộ chọn CSS để lấy giá. Nếu để trống và có table_* thì parse theo bảng.
    price_selector: Optional[str] = None
    name_selector: Optional[str] = None
    # Tách số từ chuỗi text (regex), mặc định lấy cụm số có dấu . ,
    price_regex: Optional[str] = None
    enabled: bool = True


class PriceRecord(BaseModel):
    """Một bản ghi giá tại một thời điểm."""

    material_code: str
    material_name: str
    price: float
    unit: str = "VND"
    currency: str = "VND"
    source: str = ""
    source_url: str = ""
    raw_text: str = ""
    scraped_at: datetime = Field(default_factory=_now)

    def to_db(self) -> dict:
        d = self.model_dump()
        d["scraped_at"] = self.scraped_at.isoformat()
        return d


class PriceChange(BaseModel):
    """So sánh giá hiện tại với lần trước cho một NVL."""

    material_code: str
    material_name: str
    unit: str
    current_price: float
    previous_price: Optional[float] = None
    change_abs: Optional[float] = None
    change_pct: Optional[float] = None
    source: str = ""
    scraped_at: datetime = Field(default_factory=_now)


class RunResult(BaseModel):
    """Kết quả một lần chạy cập nhật giá."""

    run_id: str
    status: str = "success"  # success | partial | failed
    started_at: datetime
    finished_at: datetime
    records: list[PriceRecord] = Field(default_factory=list)
    changes: list[PriceChange] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    report_id: Optional[str] = None
    docx_path: Optional[str] = None


class Report(BaseModel):
    """Báo cáo phân tích sinh bởi Claude."""

    report_id: str
    title: str
    summary: str = ""
    content_md: str = ""
    docx_path: Optional[str] = None
    created_at: datetime = Field(default_factory=_now)
