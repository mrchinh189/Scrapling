"use client";

import { useEffect, useState, useCallback } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function fmt(n) {
  if (n === null || n === undefined) return "—";
  return Number(n).toLocaleString("vi-VN");
}

export default function Dashboard() {
  const [prices, setPrices] = useState([]);
  const [reports, setReports] = useState([]);
  const [health, setHealth] = useState(null);
  const [running, setRunning] = useState(false);
  const [msg, setMsg] = useState("");
  const [token, setToken] = useState("");

  const load = useCallback(async () => {
    try {
      const [p, r, h] = await Promise.all([
        fetch(`${API}/api/prices`).then((x) => x.json()),
        fetch(`${API}/api/reports`).then((x) => x.json()),
        fetch(`${API}/api/health`).then((x) => x.json()),
      ]);
      setPrices(p.data || []);
      setReports(r.data || []);
      setHealth(h);
    } catch (e) {
      setMsg("Không kết nối được backend API: " + e.message);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function runNow() {
    setRunning(true);
    setMsg("Đang chạy cập nhật giá...");
    try {
      const res = await fetch(`${API}/api/run?telegram=true&report=true`, {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Lỗi");
      setMsg(`✅ Hoàn tất: ${data.records} bản ghi, trạng thái ${data.status}`);
      await load();
    } catch (e) {
      setMsg("❌ " + e.message);
    } finally {
      setRunning(false);
    }
  }

  return (
    <main style={{ maxWidth: 960, margin: "0 auto", padding: "32px 20px" }}>
      <header style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12 }}>
        <h1 style={{ margin: 0, fontSize: 26 }}>📊 Bảng giá Nguyên Vật Liệu</h1>
        {health && (
          <span style={{ fontSize: 13, opacity: 0.7 }}>
            AI {health.anthropic ? "🟢" : "⚪"} · Telegram {health.telegram ? "🟢" : "⚪"} ·
            Supabase {health.supabase ? "🟢" : "⚪"} · Lịch {health.schedule ? "🟢" : "⚪"}
          </span>
        )}
      </header>

      <section style={card}>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
          <input
            type="password"
            placeholder="API token (nếu có)"
            value={token}
            onChange={(e) => setToken(e.target.value)}
            style={input}
          />
          <button onClick={runNow} disabled={running} style={btn(running)}>
            {running ? "Đang chạy..." : "▶ Cập nhật giá ngay"}
          </button>
          <button onClick={load} style={btnGhost}>↻ Tải lại</button>
        </div>
        {msg && <p style={{ marginTop: 12, fontSize: 14 }}>{msg}</p>}
      </section>

      <h2 style={h2}>Giá mới nhất</h2>
      <section style={card}>
        {prices.length === 0 ? (
          <p style={{ opacity: 0.6 }}>Chưa có dữ liệu. Bấm "Cập nhật giá ngay".</p>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 15 }}>
            <thead>
              <tr style={{ textAlign: "left", opacity: 0.7 }}>
                <th style={th}>NVL</th>
                <th style={th}>Giá</th>
                <th style={th}>Đơn vị</th>
                <th style={th}>Nguồn</th>
                <th style={th}>Cập nhật</th>
              </tr>
            </thead>
            <tbody>
              {prices.map((p, i) => (
                <tr key={i} style={{ borderTop: "1px solid #1e293b" }}>
                  <td style={td}>{p.material_name || p.material_code}</td>
                  <td style={{ ...td, fontWeight: 600 }}>{fmt(p.price)}</td>
                  <td style={td}>{p.unit}</td>
                  <td style={{ ...td, opacity: 0.7 }}>{p.source}</td>
                  <td style={{ ...td, opacity: 0.6, fontSize: 13 }}>
                    {p.scraped_at ? new Date(p.scraped_at).toLocaleString("vi-VN") : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <h2 style={h2}>Báo cáo phân tích</h2>
      <section style={card}>
        {reports.length === 0 ? (
          <p style={{ opacity: 0.6 }}>Chưa có báo cáo.</p>
        ) : (
          <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
            {reports.map((r) => (
              <li key={r.report_id} style={{ padding: "10px 0", borderTop: "1px solid #1e293b" }}>
                <div style={{ fontWeight: 600 }}>{r.title}</div>
                <div style={{ fontSize: 13, opacity: 0.65 }}>
                  {r.created_at ? new Date(r.created_at).toLocaleString("vi-VN") : ""}
                </div>
                {r.docx_path && (
                  <a href={`${API}/api/reports/${r.report_id}/docx`} style={link}>
                    ⬇ Tải báo cáo .docx
                  </a>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>

      <footer style={{ marginTop: 32, fontSize: 13, opacity: 0.5, textAlign: "center" }}>
        NVL Price Tracker · Scrapling + Claude API · Backend: {API}
      </footer>
    </main>
  );
}

const card = { background: "#1e293b", borderRadius: 12, padding: 20, marginTop: 16 };
const h2 = { marginTop: 28, fontSize: 19 };
const th = { padding: "6px 8px", fontWeight: 500 };
const td = { padding: "8px" };
const input = {
  background: "#0f172a", border: "1px solid #334155", color: "#e2e8f0",
  padding: "8px 12px", borderRadius: 8, fontSize: 14, flex: "1 1 180px",
};
const btn = (disabled) => ({
  background: disabled ? "#475569" : "#2563eb", color: "#fff", border: "none",
  padding: "9px 16px", borderRadius: 8, fontSize: 14, cursor: disabled ? "default" : "pointer",
});
const btnGhost = {
  background: "transparent", color: "#94a3b8", border: "1px solid #334155",
  padding: "9px 16px", borderRadius: 8, fontSize: 14, cursor: "pointer",
};
const link = { color: "#60a5fa", fontSize: 14, textDecoration: "none" };
