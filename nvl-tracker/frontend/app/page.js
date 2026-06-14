"use client";

import { useEffect, useState, useCallback } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const fmt = (n) => (n === null || n === undefined ? "—" : Number(n).toLocaleString("vi-VN"));
const SEV = { MUA: "#16a34a", THEO_DÕI: "#2563eb", PHÂN_KỲ: "#ea580c", CHỜ: "#64748b" };

export default function Dashboard() {
  const [vm, setVm] = useState(null);
  const [reports, setReports] = useState([]);
  const [running, setRunning] = useState(false);
  const [msg, setMsg] = useState("");
  const [token, setToken] = useState("");

  const load = useCallback(async () => {
    try {
      const [intel, reps] = await Promise.all([
        fetch(`${API}/api/intel`).then((x) => x.json()),
        fetch(`${API}/api/reports`).then((x) => x.json()).catch(() => ({ data: [] })),
      ]);
      setVm(intel);
      setReports(reps.data || []);
    } catch (e) {
      setMsg("Không kết nối được backend: " + e.message);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  async function runNow() {
    setRunning(true);
    setMsg("Đang dựng báo cáo Price Intelligence...");
    try {
      const res = await fetch(`${API}/api/intel/run?telegram=true`, {
        method: "POST", headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Lỗi");
      setMsg(`✅ Hoàn tất: ${data.meta.n_materials} NVL · ngày giá ${data.meta.price_date}`);
      await load();
    } catch (e) {
      setMsg("❌ " + e.message);
    } finally {
      setRunning(false);
    }
  }

  if (!vm) {
    return (
      <main style={wrap}>
        <h1>📊 Price Intelligence — Giá NVL</h1>
        <p style={{ opacity: 0.6 }}>{msg || "Đang tải..."}</p>
      </main>
    );
  }

  const m = vm.meta || {};
  return (
    <main style={wrap}>
      <header style={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: 12, alignItems: "center" }}>
        <h1 style={{ margin: 0, fontSize: 24 }}>📊 Price Intelligence — Giá NVL Masterbatch</h1>
        <span style={{ fontSize: 13, opacity: 0.7 }}>
          Ngày giá {m.price_date} · USD/VND {fmt(m.usd_vnd)} · {m.n_materials} NVL
        </span>
      </header>

      <section style={card}>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <input type="password" placeholder="API token (nếu có)" value={token}
                 onChange={(e) => setToken(e.target.value)} style={input} />
          <button onClick={runNow} disabled={running} style={btn(running)}>
            {running ? "Đang chạy..." : "▶ Chạy báo cáo ngay"}
          </button>
          <button onClick={load} style={btnGhost}>↻ Tải lại</button>
        </div>
        {msg && <p style={{ marginTop: 10, fontSize: 14 }}>{msg}</p>}
      </section>

      {/* KPI */}
      <h2 style={h2}>① Tổng quan KPI (theo chi tiêu)</h2>
      <section style={card}>
        <table style={table}>
          <thead><tr style={thr}>
            <th style={th}>NVL</th><th style={th}>Giá USD/t</th><th style={th}>%tuần</th>
            <th style={th}>At-sight đ/kg</th><th style={th}>Nguồn tốt nhất</th><th style={th}>Tươi</th>
          </tr></thead>
          <tbody>
            {vm.kpis.map((k) => (
              <tr key={k.product} style={tr}>
                <td style={td}>{k.label}</td>
                <td style={{ ...td, fontWeight: 600 }}>{fmt(k.latest_usd_ton)}</td>
                <td style={{ ...td, color: k.change_pct > 0 ? "#f87171" : "#4ade80" }}>
                  {k.change_pct == null ? "—" : `${k.change_pct > 0 ? "▲" : "▼"} ${Math.abs(k.change_pct)}%`}
                </td>
                <td style={td}>{fmt(k.best_at_sight_vnd_kg)}</td>
                <td style={{ ...td, opacity: 0.8 }}>{k.best_source || "—"}</td>
                <td style={td}>{k.freshness} <span style={{ opacity: 0.5, fontSize: 12 }}>{k.date}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      {/* Narrative */}
      <h2 style={h2}>② Phân tích tổng hợp</h2>
      <section style={card}>
        {(vm.narrative?.combined_md || "").split("\n\n").map((p, i) => (
          <p key={i} style={{ margin: "6px 0", lineHeight: 1.6 }}
             dangerouslySetInnerHTML={{ __html: p.replace(/\*\*(.+?)\*\*/g, "<b>$1</b>") }} />
        ))}
      </section>

      {/* At-sight ranking (mục ④) */}
      {vm.landed && Object.keys(vm.landed).length > 0 && (
        <>
          <h2 style={h2}>③ Quy đổi at-sight tương đương (xếp hạng nguồn)</h2>
          <section style={card}>
            {Object.entries(vm.landed).map(([prod, rows]) => (
              <div key={prod} style={{ marginBottom: 14 }}>
                <div style={{ fontWeight: 600, marginBottom: 4 }}>{prod}</div>
                <table style={table}>
                  <thead><tr style={thr}>
                    <th style={th}>Khu vực</th><th style={th}>Thanh toán</th>
                    <th style={th}>Landed đ/kg</th><th style={th}>At-sight đ/kg</th><th style={th}>Nguồn</th>
                  </tr></thead>
                  <tbody>
                    {[...rows].sort((a, b) => (a.at_sight_equiv ?? 9e15) - (b.at_sight_equiv ?? 9e15)).map((r, i) => (
                      <tr key={i} style={{ ...tr, background: r.is_best ? "#13351f" : "transparent" }}>
                        <td style={td}>{r.region}</td>
                        <td style={td}>{r.payment_term}</td>
                        <td style={td}>{fmt(r.landed_vnd_kg)}</td>
                        <td style={{ ...td, fontWeight: 600 }}>{fmt(r.at_sight_equiv)}{r.is_best ? " ⭐" : ""}</td>
                        <td style={{ ...td, opacity: 0.8 }}>{r.source}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ))}
          </section>
        </>
      )}

      {/* Spreads */}
      <h2 style={h2}>④ Spread / chỉ báo dẫn</h2>
      <section style={{ ...card, display: "flex", gap: 12, flexWrap: "wrap" }}>
        {vm.spreads.map((s) => (
          <div key={s.name} style={chip}>
            <div style={{ fontSize: 13, opacity: 0.7 }}>{s.name}</div>
            <div style={{ fontSize: 20, fontWeight: 700 }}>{fmt(s.value)} <span style={{ fontSize: 12, opacity: 0.6 }}>{s.unit}</span></div>
            {s.signal && <div style={{ fontSize: 12, color: "#fbbf24" }}>{s.signal}</div>}
          </div>
        ))}
      </section>

      {/* Alerts */}
      <h2 style={h2}>⑤ Cảnh báo & Đề xuất</h2>
      <section style={card}>
        {vm.alerts.map((a, i) => (
          <div key={i} style={{ padding: "10px 0", borderTop: i ? "1px solid #1e293b" : "none" }}>
            <span style={{ ...badge, background: SEV[a.severity] || "#475569" }}>{a.severity}</span>
            <b style={{ marginLeft: 8 }}>{a.title}</b>
            <div style={{ fontSize: 14, opacity: 0.85, marginTop: 4 }}>{a.detail}</div>
            <div style={{ fontSize: 14, color: "#93c5fd", marginTop: 2 }}>{a.recommendation}</div>
          </div>
        ))}
      </section>

      {/* Forecast */}
      <h2 style={h2}>⑥ Dự báo (baseline)</h2>
      <section style={card}>
        <table style={table}>
          <thead><tr style={thr}>
            <th style={th}>NVL</th><th style={th}>Model</th><th style={th}>Tin cậy</th>
            <th style={th}>Theil's U</th><th style={th}>T+6 (yhat)</th>
          </tr></thead>
          <tbody>
            {Object.values(vm.forecasts).map((f) => (
              <tr key={f.product} style={tr}>
                <td style={td}>{f.product}</td>
                <td style={td}>{f.model}</td>
                <td style={td}>{f.confidence}</td>
                <td style={td}>{f.theils_u ?? "—"}</td>
                <td style={{ ...td, fontWeight: 600 }}>{fmt(f.points[f.points.length - 1].yhat)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      {/* Sources */}
      <h2 style={h2}>⑦ Nguồn & độ tươi</h2>
      <section style={card}>
        <ul style={{ margin: 0, paddingLeft: 18 }}>
          {vm.sources.map((s) => (
            <li key={s.name} style={{ padding: "3px 0" }}>
              {s.url ? <a href={s.url} target="_blank" rel="noreferrer" style={link}>{s.label}</a>
                     : <span style={{ opacity: 0.7 }}>{s.label}</span>}
              <span style={{ opacity: 0.6, fontSize: 13 }}> — {s.latest_date} {s.freshness}</span>
            </li>
          ))}
        </ul>
      </section>

      {/* News */}
      {vm.news && vm.news.length > 0 && (
        <>
          <h2 style={h2}>⑧ Tin tức mới cập nhật</h2>
          <section style={card}>
            <ul style={{ margin: 0, paddingLeft: 18 }}>
              {vm.news.map((n, i) => (
                <li key={i} style={{ padding: "5px 0" }}>
                  <span style={{ opacity: 0.55, fontSize: 12 }}>{n.published_at} · {n.category}</span><br />
                  {n.url ? <a href={n.url} target="_blank" rel="noreferrer" style={link}>{n.title}</a>
                         : <span>{n.title}</span>}
                  {n.summary && <span style={{ opacity: 0.7, fontSize: 13 }}> — {n.summary}</span>}
                </li>
              ))}
            </ul>
          </section>
        </>
      )}

      {/* Reports */}
      <h2 style={h2}>⑨ Báo cáo .docx</h2>
      <section style={card}>
        {reports.length === 0 ? <p style={{ opacity: 0.6 }}>Chưa có báo cáo.</p> : (
          <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
            {reports.map((r) => (
              <li key={r.report_id} style={{ padding: "8px 0", borderTop: "1px solid #1e293b" }}>
                <b>{r.title}</b>
                {r.docx_path && <a href={`${API}/api/reports/${r.report_id}/docx`} style={{ ...link, marginLeft: 10 }}>⬇ Tải .docx</a>}
              </li>
            ))}
          </ul>
        )}
      </section>

      <footer style={{ marginTop: 32, fontSize: 12, opacity: 0.5, textAlign: "center" }}>
        DOCX = Web = Telegram cùng một view-model · Tạo lúc {m.generated_at?.slice(0, 16).replace("T", " ")} · {API}
      </footer>
    </main>
  );
}

const wrap = { maxWidth: 1000, margin: "0 auto", padding: "32px 20px" };
const card = { background: "#1e293b", borderRadius: 12, padding: 18, marginTop: 12 };
const h2 = { marginTop: 26, fontSize: 18 };
const table = { width: "100%", borderCollapse: "collapse", fontSize: 14 };
const thr = { textAlign: "left", opacity: 0.7 };
const th = { padding: "6px 8px", fontWeight: 500 };
const tr = { borderTop: "1px solid #1e293b" };
const td = { padding: "8px" };
const chip = { background: "#0f172a", borderRadius: 10, padding: "10px 14px", minWidth: 150 };
const badge = { fontSize: 11, fontWeight: 700, color: "#fff", padding: "2px 8px", borderRadius: 6 };
const input = { background: "#0f172a", border: "1px solid #334155", color: "#e2e8f0", padding: "8px 12px", borderRadius: 8, fontSize: 14, flex: "1 1 160px" };
const btn = (d) => ({ background: d ? "#475569" : "#2563eb", color: "#fff", border: "none", padding: "9px 16px", borderRadius: 8, fontSize: 14, cursor: d ? "default" : "pointer" });
const btnGhost = { background: "transparent", color: "#94a3b8", border: "1px solid #334155", padding: "9px 16px", borderRadius: 8, fontSize: 14, cursor: "pointer" };
const link = { color: "#60a5fa", textDecoration: "none" };
