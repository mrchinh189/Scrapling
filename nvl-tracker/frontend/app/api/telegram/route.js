// Webhook Telegram 2 chiều (chạy trên Vercel).
// - Xác thực secret token của Telegram.
// - Lệnh NHẸ (/gia /dubao /baocao /help): trả ngay từ backend API.
// - Lệnh NẶNG (/capnhat): bắn GitHub repo_dispatch để Actions chạy pipeline
//   (Python + nhiều secret + chạy lâu, vượt giới hạn function của Vercel).

const TG = (token, method) => `https://api.telegram.org/bot${token}/${method}`;
const API = process.env.BACKEND_API_URL || process.env.NEXT_PUBLIC_API_URL || "";

async function tgSend(chatId, text) {
  const token = process.env.TELEGRAM_BOT_TOKEN;
  if (!token) return;
  await fetch(TG(token, "sendMessage"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ chat_id: chatId, text, parse_mode: "Markdown", disable_web_page_preview: true }),
  });
}

async function repoDispatch() {
  const { GH_DISPATCH_PAT, GH_OWNER, GH_REPO } = process.env;
  if (!GH_DISPATCH_PAT || !GH_OWNER || !GH_REPO) {
    return { ok: false, error: "Thiếu cấu hình GitHub (GH_DISPATCH_PAT/GH_OWNER/GH_REPO)" };
  }
  const res = await fetch(`https://api.github.com/repos/${GH_OWNER}/${GH_REPO}/dispatches`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${GH_DISPATCH_PAT}`,
      Accept: "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28",
    },
    body: JSON.stringify({ event_type: "telegram-update" }),
  });
  return { ok: res.status === 204, error: res.status === 204 ? "" : `GitHub ${res.status}` };
}

async function fetchIntel() {
  if (!API) return null;
  try {
    const r = await fetch(`${API}/api/intel`, { cache: "no-store" });
    return r.ok ? await r.json() : null;
  } catch {
    return null;
  }
}

function fmtPrices(vm, query) {
  if (!vm) return "Chưa có dữ liệu giá.";
  let kpis = vm.kpis || [];
  if (query) kpis = kpis.filter((k) => k.product.toLowerCase().includes(query.toLowerCase()));
  if (kpis.length === 0) return `Không thấy NVL khớp "${query}".`;
  return ["*Giá NVL mới nhất:*", ...kpis.slice(0, 12).map((k) => {
    const pct = k.change_pct == null ? "" : ` (${k.change_pct > 0 ? "▲" : "▼"}${Math.abs(k.change_pct)}%)`;
    return `• *${k.product}* ${Number(k.latest_usd_ton).toLocaleString("vi-VN")} USD/t${pct} ${k.freshness}`;
  })].join("\n");
}

function fmtForecast(vm) {
  if (!vm || !vm.forecasts) return "Chưa có dự báo.";
  return ["*Dự báo (baseline):*", ...Object.values(vm.forecasts).map((f) => {
    const end = f.points[f.points.length - 1];
    return `• ${f.product}: T+${f.horizon} ≈ ${Number(end.yhat).toLocaleString("vi-VN")} (${f.model}, tin cậy ${f.confidence})`;
  })].join("\n");
}

const HELP = [
  "🤖 *Bot Price Intelligence NVL*",
  "/capnhat — Chạy cập nhật giá + báo cáo (qua GitHub Actions)",
  "/gia [mã] — Xem giá mới nhất (vd /gia PP)",
  "/dubao — Xem dự báo",
  "/baocao — Link dashboard + báo cáo",
  "/help — Trợ giúp",
].join("\n");

export async function POST(request) {
  // 1) Xác thực secret token (Telegram gửi kèm khi setWebhook có secret_token)
  const secret = process.env.TELEGRAM_WEBHOOK_SECRET;
  if (secret && request.headers.get("x-telegram-bot-api-secret-token") !== secret) {
    return new Response("forbidden", { status: 403 });
  }

  let update;
  try {
    update = await request.json();
  } catch {
    return Response.json({ ok: true });
  }

  const msg = update.message || update.channel_post;
  const text = (msg && msg.text) || "";
  const chatId = msg && msg.chat && msg.chat.id;
  if (!chatId || !text.startsWith("/")) return Response.json({ ok: true });

  const [cmd, ...rest] = text.trim().split(/\s+/);
  const arg = rest.join(" ");
  const base = (cmd.split("@")[0] || "").toLowerCase();

  if (base === "/capnhat") {
    const r = await repoDispatch();
    await tgSend(chatId, r.ok
      ? "⏳ Đã kích hoạt cập nhật. Báo cáo sẽ gửi tới đây khi pipeline chạy xong (vài phút)."
      : `❌ Không kích hoạt được: ${r.error}`);
  } else if (base === "/gia") {
    await tgSend(chatId, fmtPrices(await fetchIntel(), arg));
  } else if (base === "/dubao") {
    await tgSend(chatId, fmtForecast(await fetchIntel()));
  } else if (base === "/baocao") {
    const url = process.env.NEXT_PUBLIC_SITE_URL || "";
    await tgSend(chatId, `📊 Dashboard: ${url || "(đặt NEXT_PUBLIC_SITE_URL)"}\nGõ /capnhat để tạo báo cáo mới.`);
  } else {
    await tgSend(chatId, HELP);
  }

  return Response.json({ ok: true });
}

export async function GET() {
  return Response.json({ status: "telegram webhook ready" });
}
