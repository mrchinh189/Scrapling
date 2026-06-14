# Hướng dẫn triển khai chi tiết (bàn giao)

Tài liệu này hướng dẫn đưa hệ thống lên môi trường thật, từ A→Z.

## Tổng quan kiến trúc triển khai

- **Backend** (API + bot + lịch): chạy bằng `docker compose` trên server/VPS/cloud của bạn.
- **CSDL**: Supabase (khuyến nghị) — không cần tự quản Postgres.
- **Frontend**: deploy lên Vercel, gọi tới backend qua biến `NEXT_PUBLIC_API_URL`.

```
[Vercel: frontend]  ──HTTPS──►  [VPS: docker compose: api + bot]  ──►  [Supabase]
                                              │
                                              └──►  Telegram, Claude API
```

---

## Bước 1 — Chuẩn bị secrets

| Biến | Lấy ở đâu |
|---|---|
| `ANTHROPIC_API_KEY` | https://console.anthropic.com → API Keys |
| `TELEGRAM_BOT_TOKEN` | Telegram @BotFather → `/newbot` |
| `TELEGRAM_CHAT_ID` | Telegram @userinfobot |
| `SUPABASE_URL`, `SUPABASE_KEY` | Supabase → Project Settings → API (dùng `service_role`) |
| `API_TOKEN` | Tự đặt một chuỗi bí mật để bảo vệ `POST /api/run` |

## Bước 2 — Supabase

1. Tạo project mới.
2. **SQL Editor** → New query → dán nội dung `supabase/schema.sql` → **Run**.
3. Kiểm tra **Table Editor** thấy 2 bảng `price_records`, `reports` và view `latest_prices`.

## Bước 3 — Deploy backend (VPS có Docker)

```bash
git clone <repo-cua-ban>
cd <repo>/nvl-tracker
cp .env.example .env
nano .env                      # điền toàn bộ secrets ở Bước 1
# Cập nhật backend/sources.yaml với nguồn NVL thật

docker compose up -d --build
docker compose ps              # api + bot đang chạy
curl http://localhost:8000/api/health
```

### Mở public an toàn (khuyến nghị reverse proxy + HTTPS)

Ví dụ với Caddy (`Caddyfile`):

```
api.tencongty.com {
    reverse_proxy localhost:8000
}
```

> Đặt `API_TOKEN` trong `.env` để chỉ người có token mới gọi được `POST /api/run`.
> Các endpoint đọc (GET) để mở cho frontend hiển thị.

## Bước 4 — Chạy thử & xác minh

```bash
# Chạy 1 lượt cập nhật ngay
curl -X POST "http://localhost:8000/api/run" \
     -H "Authorization: Bearer $API_TOKEN"
```

Kỳ vọng: nhận tin nhắn Telegram + file .docx, dữ liệu xuất hiện trong Supabase,
`GET /api/prices` trả về danh sách.

## Bước 5 — Deploy frontend (Vercel)

1. Push repo lên GitHub.
2. Vercel → **Add New → Project** → import repo.
3. **Root Directory**: `nvl-tracker/frontend`.
4. **Environment Variables**: `NEXT_PUBLIC_API_URL = https://api.tencongty.com`.
5. **Deploy**. Mở URL Vercel → thấy dashboard, bảng giá, nút "Cập nhật giá ngay".

## Bước 6 — Lịch tự động

Mặc định 7h sáng thứ Hai (`SCHEDULE_CRON=0 7 * * 1`). Lịch chạy trong service `api`.
Đổi giờ/tần suất bằng cách sửa `SCHEDULE_CRON` rồi `docker compose up -d`.

Một vài ví dụ cron:
- `0 7 * * 1` — 7h sáng thứ Hai hàng tuần
- `0 8 * * 1,4` — 8h sáng thứ Hai và thứ Năm
- `0 6 * * *` — 6h sáng hàng ngày

## Bước 7 — Vận hành

```bash
docker compose logs -f api      # log API + lịch
docker compose logs -f bot      # log bot Telegram
docker compose restart          # khởi động lại sau khi sửa .env / sources.yaml
docker compose pull && docker compose up -d --build   # cập nhật phiên bản
```

## Checklist bàn giao

- [ ] `sources.yaml` đã cấu hình đúng nguồn NVL thật, `enabled: true`
- [ ] `.env` đã điền đủ secrets
- [ ] Supabase schema đã chạy, 2 bảng tồn tại
- [ ] `docker compose up -d` chạy 2 service không lỗi
- [ ] `POST /api/run` trả kết quả + nhận Telegram + .docx
- [ ] Lịch tuần bật (`/api/health` → `schedule: true`)
- [ ] Frontend Vercel hiển thị bảng giá và tải được báo cáo
- [ ] `pytest` xanh
