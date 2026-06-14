"""Tin nhắn Telegram tóm tắt từ VIEW-MODEL (KPI + at-sight + spread + dự báo + nguồn)."""

from __future__ import annotations


def build_intel_summary(vm: dict) -> str:
    meta = vm["meta"]
    lines = [f"*Price Intelligence — Giá NVL* (ngày giá {meta['price_date']})", ""]

    # KPI top theo chi tiêu
    for k in vm["kpis"][:6]:
        pct = k.get("change_pct")
        arrow = "➡️"
        if pct is not None:
            arrow = "🔺" if pct > 0 else ("🔻" if pct < 0 else "➡️")
        pcts = f" ({pct:+.1f}%)" if pct is not None else ""
        ats = f" · at-sight {k['best_at_sight_vnd_kg']:,.0f}đ/kg" if k.get("best_at_sight_vnd_kg") else ""
        lines.append(f"{arrow} *{k['product']}* {k['latest_usd_ton']:,.0f} USD/t{pcts} "
                     f"{k['freshness']}{ats}")

    # Spread tín hiệu
    sp = next((s for s in vm["spreads"] if s["name"] == "Naphtha–Ethylene"), None)
    if sp:
        lines += ["", f"📐 Spread {sp['name']}: {sp['value']} {sp['unit']} — _{sp['signal']}_"]

    # Cảnh báo nổi bật
    if vm["alerts"]:
        lines += ["", "*Cảnh báo:*"]
        for a in vm["alerts"][:3]:
            lines.append(f"• [{a['severity']}] {a['title']}")

    # Nguồn (kèm link + ngày)
    lines += ["", "🔗 *Nguồn:*"]
    for s in vm["sources"][:6]:
        if s["url"]:
            lines.append(f"• [{s['label']}]({s['url']}) — {s['latest_date']} {s['freshness']}")
        else:
            lines.append(f"• {s['label']} — {s['latest_date']} {s['freshness']}")

    # Tin mới
    if vm.get("news"):
        lines += ["", "📰 *Tin mới:*"]
        for n in vm["news"][:5]:
            if n.get("url"):
                lines.append(f"• [{n['title']}]({n['url']}) — {n.get('published_at', '')}")
            else:
                lines.append(f"• {n['title']} — {n.get('published_at', '')}")

    lines += ["", f"⏱ Chạy lúc {meta['generated_at'][:16].replace('T', ' ')} · 📎 DOCX đính kèm"]
    return "\n".join(lines)
