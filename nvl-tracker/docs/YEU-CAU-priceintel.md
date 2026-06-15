# Yêu cầu dự án Price Intelligence NVL (thu thập từ tài liệu gốc)

> Tổng hợp từ gói `priceintel` (START_HERE, CLAUDE.md, spec full-stack, 4 phase plan,
> catalog nguồn, masterlist). Đây là bản chốt **mục tiêu cốt lõi** để triển khai.
> Quyết định: **ưu tiên dùng Scrapling** cho thu thập; thiếu chức năng thì dùng phương án khác.

## Mục tiêu nghiệp vụ
Hệ thu thập → cập nhật → phân tích → (dự báo) giá NVL ngành **masterbatch** cho EUP Group.
NVL chiếm 70–85% giá vốn → mua tốt 1% ≈ +1% biên lợi nhuận. Chuỗi truyền dẫn
dầu Brent → naphtha → ethylene/propylene → PE/PP (trễ ~5 tuần → chỉ báo dẫn).

## Danh mục NVL (chốt theo % chi tiêu — `config/materials.yaml`)
- **Nhựa nền (42%)**: PP, PE (LLDPE/LDPE), HDPE, PS.
- **Feedstock (chỉ báo dẫn)**: Brent, naphtha, ethylene, propylene.
- **Phụ gia (24%)**: TiO₂ rutile, PE wax, base/paraffin oil, stearic acid, zinc/calcium
  stearate, carbon black, coupling agent, UV stabilizer, flame retardant.
- **Ngoài phạm vi**: CaCO₃/bột đá, BaSO₄, Talc, EVA, bao bì, pallet, BTP, thành phẩm.

## Nguyên tắc bất biến
1. **Fail-soft**: thiếu key nào → SKIP nguồn/bước đó, KHÔNG gãy pipeline.
2. **Demo chạy không cần key thật** (chế độ fixtures).
3. Không hardcode/không in khóa; đọc từ env.
4. ⛔ KHÔNG cào ICIS/Platts/Argus/ChemOrbis/Fastmarkets (bản quyền) — nhập qua form.
5. Tôn trọng robots.txt/ToS; comment tiếng Việt; test thật từng bước.
6. **Minh bạch nguồn**: mọi nơi hiện nguồn PHẢI kèm **link** + **ngày giá (date)** + **độ tươi 🟢🟡🔴**.
7. **Một nguồn chân lý — DOCX = Web = Telegram**: tính MỘT lần trong Python (view-model),
   mọi renderer chỉ ĐỌC LẠI, không tự suy diễn.

## Thu thập 3 tầng (ưu tiên Scrapling)
- **Tầng FREE (API)**: EIA (Brent), Vietcombank (USD/VND), UN Comtrade (unit value NK).
- **Tầng cào**: **Scrapling** (thay Firecrawl — miễn phí, adaptive, chống bot) cho
  ThePlasticsExchange, DCE, ICE/CME delayed, MPOB/FCPO, Polymerupdate-free, businessanalytiq,
  blog TiO₂/stearic. Firecrawl giữ làm fallback nếu Scrapling bị chặn.
- **Tầng AI**: HTML → markdown → Claude API → JSON schema (khi không có selector ổn định).
- **Backfill**: FRED (PPI nhựa, palm oil, Brent dài hạn), EIA, World Bank Pink Sheet (3–5 năm nền).

## Phân tích lõi (giá trị khác biệt)
- **Quy đổi at-sight tương đương** (mục ④): chuẩn hoá đơn vị → landed VND/kg → trừ lợi ích
  trả chậm → at-sight để **xếp hạng nguồn công bằng**. `config/landed.yaml` giữ thuế NK/cước/lãi.
- **Spread/chỉ báo dẫn**: naphtha–ethylene (ngưỡng đáy ~250$/t), PP–propylene, ethylene–PE,
  chỉ số gốc-100 (phân kỳ resin▼ vs phụ gia▲).
- **Forecast baseline**: tự hạ cấp model theo độ dài chuỗi (naive → trend → Holt),
  Theil's U<1 mới nhận, kèm độ tin cậy & cơ sở.
- **Cảnh báo quyết định**: thẻ {MUA, THEO DÕI, PHÂN KỲ, CHỜ} + "→ Đề xuất".
- **Narrative 4 đoạn** (template + Claude tinh chỉnh): Bức tranh · Vì sao · Hệ quả EUP · Khuyến nghị.

## Đầu ra
- **DOCX** 10 mục bám mẫu v4 (KPI, narrative, at-sight ranking, spread, cảnh báo, forecast, nguồn, tin tức).
- **Web** Next.js (Vercel) đọc cùng view-model → mirror các mục.
- **Telegram** 2 chiều: `/capnhat /gia /baocao /dubao /help`; text kèm link + ngày + dashboard + đính kèm DOCX.
- **Lịch**: GitHub Actions cron (Dự án A) hoặc APScheduler/Task Scheduler (dự phòng) + chạy theo yêu cầu.

---

## Hiện trạng triển khai trong repo này (`nvl-tracker/`)

### ✅ Đã có (cốt lõi — chạy offline, có test)
| Hạng mục | Vị trí |
|---|---|
| Catalog NVL + trọng số chi tiêu | `backend/config/materials.yaml` |
| Engine **landed + at-sight tương đương** | `backend/app/analytics/landed.py` |
| Chuẩn hoá đơn vị (¢/lb, RMB/t, USD/t, bbl) | `backend/app/analytics/units.py` |
| **Spread** + chỉ số gốc-100 | `backend/app/analytics/spreads.py` |
| **Forecast** baseline + Theil's U | `backend/app/forecast/run.py` |
| **Cảnh báo** quyết định (MUA/THEO DÕI/PHÂN KỲ/CHỜ) | `backend/app/analytics/alerts.py` |
| **Narrative** 4 đoạn (+ Claude tuỳ chọn) | `backend/app/analytics/narrative.py` |
| Độ tươi 🟢🟡🔴 từ ngày giá | `backend/app/analytics/freshness.py` |
| **View-model dùng chung** (DOCX=Web=Telegram) | `backend/app/viewmodel.py` |
| **DOCX 10 mục** + hyperlink nguồn | `backend/app/report/intel_docx.py` |
| Tóm tắt Telegram (link + ngày + nguồn) | `backend/app/report/intel_telegram.py` |
| Fixtures 12 tuần (chạy offline) | `backend/fixtures/` |
| API `/api/intel`, `/api/intel/run` · CLI `intel` | `backend/app/api/routes.py`, `app/cli.py` |
| Dashboard đọc `/api/intel` (parity) | `frontend/app/page.js` |
| Crawl Scrapling (khung) | `backend/app/scraper/` |
| Test (23) | `backend/tests/` |

### 🔜 Còn lại (lộ trình theo phase plan gốc)
- **Collectors thật bằng Scrapling**: EIA/Vietcombank/Comtrade (API) + ThePlasticsExchange/DCE/MPOB
  (Scrapling) → ghi `price_master`; backfill FRED/World Bank.
- **`collect/news.py`**: tin tức + link (Google News RSS/Polymerupdate) → mục 10 báo cáo.
- **Telegram webhook 2 chiều** qua Vercel `/api/telegram` → GitHub `repo_dispatch`.
- **GitHub Actions** workflows: weekly/update/backfill (Dự án A).
- **Schema Supabase đầy đủ**: `price_master, fx_rates, landed, spreads, forecast, news, analysis, audit_log`.
- Biểu đồ PNG (matplotlib) nhúng DOCX mục ⑦/⑨ + chart tương tác trên web.
