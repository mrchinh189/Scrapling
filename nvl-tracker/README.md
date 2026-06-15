# NVL Price Tracker — Hệ thống cập nhật & phân tích giá Nguyên Vật Liệu

Hệ thống full-stack tự động **crawl giá NVL → lưu Supabase → phân tích bằng Claude AI →
gửi báo cáo qua Telegram (text + file .docx)**, chạy theo lịch hàng tuần hoặc theo yêu cầu,
có dashboard web (Vercel) và bot Telegram.

Lõi crawl dùng [Scrapling](https://github.com/D4Vinci/Scrapling) — thư viện scraping
chống phát hiện, hiệu năng cao.

> **Lõi Price Intelligence** (theo yêu cầu dự án gốc — xem [`docs/YEU-CAU-priceintel.md`](docs/YEU-CAU-priceintel.md)):
> quy đổi **at-sight tương đương** để xếp hạng nguồn, **spread/chỉ báo dẫn**, **forecast** baseline
> (Theil's U), **cảnh báo quyết định**, **narrative**, gom vào **một view-model dùng chung**
> để DOCX = Web = Telegram cùng số liệu. Chạy thử offline ngay (không cần key):
> ```bash
> cd backend && pip install -r requirements.txt
> python fixtures/_generate.py        # sinh dữ liệu mẫu 12 tuần
> python -m app.cli intel             # dựng view-model + DOCX 10 mục
> ```

---

## 1. Kiến trúc

```
                         ┌──────────────────────────────────────────────┐
                         │  Backend (Python, Docker)                    │
   sources.yaml ───────► │  Scrapling crawl ─► so sánh giá ─► Supabase  │
                         │            │                                  │
   Lịch tuần (cron) ───► │   run_update()                               │
   POST /api/run ──────► │            │                                  │
   Bot /capnhat ───────► │            ▼                                  │
                         │   Claude API ─► phân tích ─► .docx            │
                         │            │                                  │
                         │            ▼                                  │
                         │   Telegram (text + file)                     │
                         └───────────────┬──────────────────────────────┘
                                         │ REST API (/api/*)
                         ┌───────────────▼──────────────┐
                         │  Frontend (Next.js @ Vercel) │
                         │  Dashboard: giá, báo cáo,    │
                         │  nút "Cập nhật ngay"         │
                         └──────────────────────────────┘
```

| Thành phần | Công nghệ | Vai trò |
|---|---|---|
| Crawl | Scrapling + curl_cffi | Lấy giá NVL từ các trang web |
| API + lịch | FastAPI + APScheduler | REST API, cron tuần (nhúng) |
| CSDL | Supabase (Postgres) · fallback SQLite | Lưu lịch sử giá + báo cáo |
| AI | Claude API (`claude-opus-4-8`) | Viết báo cáo phân tích |
| Báo cáo | python-docx | Xuất file .docx |
| Thông báo | python-telegram-bot + Bot API | Gửi text + file, nhận lệnh |
| Frontend | Next.js (Vercel) | Dashboard web |

---

## 2. Yêu cầu

- Docker & Docker Compose (deploy backend) — hoặc Python 3.10+ để chạy trực tiếp
- Tài khoản **Supabase** (miễn phí) — tuỳ chọn, không có thì dùng SQLite
- **Claude API key** (https://console.anthropic.com) — tuỳ chọn, không có thì báo cáo cơ bản
- **Bot Telegram** (qua @BotFather) — tuỳ chọn
- Tài khoản **Vercel** (deploy frontend) — tuỳ chọn

> Hệ thống chạy được ngay cả khi thiếu các dịch vụ ngoài: tự động fallback (SQLite,
> báo cáo không-AI, bỏ qua Telegram) để bạn dựng dần.

---

## 3. Cấu hình nguồn giá NVL  ⚠️ QUAN TRỌNG

Sửa `backend/sources.yaml`, mỗi NVL một mục:

```yaml
sources:
  - code: STEEL                       # mã NVL (duy nhất)
    name: "Thép xây dựng Hòa Phát"
    unit: "VND/kg"
    url: "https://trang-nguon.vn/gia-thep"
    fetcher: static                   # static | stealthy (trang chặn bot/JS)
    price_selector: ".price-value"    # CSS selector tới ô chứa giá
    enabled: true
```

Dò selector nhanh:

```bash
cd backend
python -m app.cli inspect "https://trang-nguon.vn/gia-thep" ".price-value"
```

### Collectors thu thập giá thật (Scrapling + API)

`config/price_sources.yaml` khai báo nguồn giá cho **Price Intelligence** (ThePlasticsExchange,
DCE, businessanalytiq…). Tầng API (EIA Brent, Vietcombank USD/VND) chạy sẵn khi có key.
Mọi nguồn **fail-soft**: thiếu key / bị chặn → SKIP, không gãy lượt.

```bash
python -m app.cli collect            # thu thập → data/price_master.csv, data/fx.csv
python -m app.cli intel --collect    # thu thập rồi dựng báo cáo trên dữ liệu THẬT
```

Pipeline tự ưu tiên `data/` (dữ liệu thật) rồi mới đến `fixtures/` (mẫu offline).

---

## 4. Chạy nhanh (local, không cần Docker)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env          # điền key nếu có

# Chạy 1 lượt cập nhật thử
python -m app.cli run

# API + dashboard backend
uvicorn app.main:app --reload     # http://localhost:8000/docs

# Bot Telegram (cửa sổ khác)
python -m app.telegram_bot.bot
```

## 5. Deploy bằng Docker Compose (server/cloud của bạn)

```bash
cd nvl-tracker
cp .env.example .env              # điền đầy đủ key
docker compose up -d --build
docker compose logs -f
```

Lệnh trên dựng 2 service: `api` (REST + lịch tuần) và `bot` (Telegram).
Dữ liệu lưu ở volume `nvl-data` (hoặc Supabase nếu đã cấu hình).

## 6. Cấu hình Supabase

1. Tạo project tại https://supabase.com
2. **SQL Editor** → dán & chạy `supabase/schema.sql`
3. **Project Settings → API**: copy `URL` và `service_role` key vào `.env`
   (`SUPABASE_URL`, `SUPABASE_KEY`)

## 7. Cấu hình Telegram

1. Chat với **@BotFather** → `/newbot` → lấy `TELEGRAM_BOT_TOKEN`
2. Chat với **@userinfobot** → lấy `chat_id` của bạn → `TELEGRAM_CHAT_ID`
3. Điền vào `.env`. Lệnh bot: `/capnhat`, `/gia`, `/baocao`, `/help`

## 8. Deploy frontend lên Vercel

1. Push repo lên GitHub
2. Vercel → **New Project** → chọn repo, **Root Directory = `nvl-tracker/frontend`**
3. **Environment Variables**: `NEXT_PUBLIC_API_URL = https://<backend-cua-ban>`
4. Deploy. (Backend cần truy cập được công khai; đã bật CORS sẵn.)

Xem chi tiết từng bước trong [`docs/DEPLOY.md`](docs/DEPLOY.md).

---

## 9. Lịch tự động

`SCHEDULE_CRON` trong `.env` (định dạng cron). Mặc định `0 7 * * 1` = 7h sáng thứ Hai.
Tắt bằng `SCHEDULE_ENABLED=false`. Lịch nhúng trong service `api`.

## 10. REST API

| Method | Endpoint | Mô tả |
|---|---|---|
| GET | `/api/health` | Trạng thái cấu hình |
| GET | `/api/prices` | Giá mới nhất mỗi NVL |
| GET | `/api/prices/{code}/history?limit=30` | Lịch sử giá |
| GET | `/api/reports` | Danh sách báo cáo |
| GET | `/api/reports/{id}/docx` | Tải file .docx |
| POST | `/api/run?telegram=true&report=true` | Chạy cập nhật ngay (cần `Authorization: Bearer <API_TOKEN>` nếu đã đặt) |

Swagger UI: `http://localhost:8000/docs`

## 11. Kiểm thử

```bash
cd backend
python -m pytest          # 12 test: parser, scraper, pipeline, báo cáo, docx
```

## 12. Cấu trúc thư mục

```
nvl-tracker/
├── backend/
│   ├── app/
│   │   ├── config.py          # cấu hình (.env)
│   │   ├── models.py          # kiểu dữ liệu
│   │   ├── service.py         # orchestrator pipeline
│   │   ├── scraper/           # crawl (Scrapling) + parse giá
│   │   ├── db/                # Supabase + SQLite
│   │   ├── report/            # Claude analyzer + DOCX
│   │   ├── telegram_bot/      # bot + notifier
│   │   ├── scheduler/         # cron tuần
│   │   ├── api/               # REST routes
│   │   ├── cli.py             # tiện ích dòng lệnh
│   │   └── main.py            # FastAPI app
│   ├── tests/                 # pytest
│   ├── sources.yaml           # ⚙️ cấu hình nguồn NVL
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                  # Next.js (Vercel)
├── supabase/schema.sql        # lược đồ CSDL
├── docker-compose.yml
├── .env.example
└── docs/DEPLOY.md
```

## 13. Khắc phục sự cố

| Hiện tượng | Nguyên nhân / cách xử lý |
|---|---|
| `/api/prices` rỗng | Chưa chạy lần nào — bấm "Cập nhật giá ngay" hoặc `python -m app.cli run` |
| "Không tìm thấy giá" | Sai `price_selector` — dùng `app.cli inspect` để dò lại |
| Báo cáo không có phân tích AI | Thiếu `ANTHROPIC_API_KEY` |
| Trang chặn bot / cần JS | Đổi `fetcher: stealthy` và build image với `INSTALL_BROWSERS=true` |
| Frontend không gọi được API | Kiểm tra `NEXT_PUBLIC_API_URL` và backend có public không |
