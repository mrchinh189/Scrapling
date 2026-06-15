"""Sinh biểu đồ PNG (matplotlib) cho DOCX. Fail-soft nếu thiếu matplotlib."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from app.config import DATA_DIR

logger = logging.getLogger(__name__)


def _plt():
    import matplotlib

    matplotlib.use("Agg")  # không cần màn hình (chạy trong CI/server)
    import matplotlib.pyplot as plt

    return plt


def build_index_chart(vm: dict, report_id: str) -> Optional[str]:
    """Chỉ số gốc-100: phân kỳ resin▼ vs phụ gia▲."""
    index = vm.get("index_base100") or {}
    if not index:
        return None
    fam = {k["product"]: k.get("family") for k in vm.get("kpis", [])}
    try:
        plt = _plt()
        fig, ax = plt.subplots(figsize=(7, 3.5))
        for prod, series in index.items():
            if len(series) < 2:
                continue
            xs = list(range(len(series)))
            ys = [v for _, v in series]
            color = {"resin": "#1d4ed8", "additive": "#c2410c"}.get(fam.get(prod), "#64748b")
            ax.plot(xs, ys, label=prod, color=color, linewidth=1.6)
        ax.axhline(100, color="#94a3b8", linewidth=0.8, linestyle="--")
        ax.set_title("Chỉ số giá gốc-100 (resin xanh ▼ vs phụ gia cam ▲)")
        ax.set_xlabel("Tuần"); ax.set_ylabel("Chỉ số (gốc=100)")
        ax.legend(fontsize=7, ncol=4)
        return _save(fig, plt, report_id, "index")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Vẽ index chart lỗi: %s", exc)
        return None


def build_forecast_chart(vm: dict, product: str, report_id: str) -> Optional[str]:
    """Dải tin cậy dự báo cho một NVL."""
    fc = (vm.get("forecasts") or {}).get(product)
    if not fc or not fc.get("points"):
        return None
    try:
        plt = _plt()
        fig, ax = plt.subplots(figsize=(7, 3.2))
        weeks = [p["week"] for p in fc["points"]]
        yhat = [p["yhat"] for p in fc["points"]]
        lower = [p["lower"] for p in fc["points"]]
        upper = [p["upper"] for p in fc["points"]]
        ax.fill_between(weeks, lower, upper, color="#93c5fd", alpha=0.4, label="Khoảng tin cậy")
        ax.plot(weeks, yhat, color="#1d4ed8", marker="o", label="Dự báo")
        ax.set_title(f"Dự báo {product} ({fc['model']} · tin cậy {fc['confidence']})")
        ax.set_xlabel("Tuần tới (T+)"); ax.set_ylabel("Giá")
        ax.legend(fontsize=8)
        return _save(fig, plt, report_id, f"fc_{product}")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Vẽ forecast chart lỗi: %s", exc)
        return None


def _save(fig, plt, report_id: str, name: str) -> str:
    out_dir = DATA_DIR / "reports" / "charts"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{report_id}_{name}.png"
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)
    return str(path)
