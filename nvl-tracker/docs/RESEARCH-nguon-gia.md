# Research nguồn giá bổ sung (đánh giá khả năng cào + pháp lý)

> Kết luận từ research ngày 2026-06-15. Nguyên tắc: **không cào nguồn cấm trong ToS**
> (giống ICIS/Platts/Argus). Ưu tiên nguồn chính phủ/free; nguồn thương mại → dùng
> chính thức (subscription/API) hoặc nhập tay qua "form nội bộ".

## Bảng đánh giá 4 nguồn bạn đưa

| # | Nguồn | Dữ liệu | Liên quan NVL | Truy cập | Cào được? | Khuyến nghị |
|---|---|---|---|---|---|---|
| 1 | **SCI99** (intl.sci99.com) | Giá hoá chất/nhựa/cao su/kim loại TQ (propylene 12605, carbon black 12969, styrene 12597…) | Propylene (feedstock PP), **Carbon black** (phụ gia), Styrene (PS) | **Dịch vụ trả phí**, cập nhật mỗi ngày làm việc; nhiều phần sau đăng nhập | ⚠️ Có thể vi phạm ToS nếu cào | Dùng **gói/API chính thức** của SCI; nếu không → **nhập tay**. Để `enabled: false`, ghi chú ToS |
| 2 | **MPOC** (mpoc.org.my) | Giá dầu cọ hằng ngày (CPO, FCPO settlement) | **Driver** dầu cọ → stearic acid, PE wax, zinc/calcium stearate | Công khai, miễn phí; trang động (JS) | ✅ Được (free) — cần `fetcher: stealthy` | Dùng làm **driver dầu cọ**. Hoặc dùng nguồn tốt hơn ở dưới |
| 3 | **Investing.com FCPO** (vn.investing.com) | Hợp đồng tương lai dầu cọ Malaysia (FCPO) | Driver dầu cọ | Chống bot mạnh (Cloudflare) + JS streaming | ❌ **ToS cấm scraping** | **KHÔNG cào**. Thay bằng MPOB/MPOC hoặc FRED |
| 4 | **LME Zinc** (lme.com) | Giá kẽm chính thức LME (3M/official) | **Driver** kẽm → zinc stearate | Trả phí/độ trễ ngày | ❌ **ToS cấm redistribute/scrape** | **KHÔNG cào**. Nhập tay/form, hoặc dùng index thay thế |

## Nguồn THAY THẾ tốt hơn (free, hợp pháp, dễ cào) — nên dùng

| Cần gì | Nguồn thay thế | Cách |
|---|---|---|
| Dầu cọ (thay Investing/MPOC) | **MPOB** `bepi.mpob.gov.my/index.php/price/daily` (chính phủ Malaysia, free) | Bảng HTML — `fetcher: stealthy`, anchor "CPO" |
| Dầu cọ lịch sử (backfill) | **FRED** `PPOILUSDM` (đã có trong `config/history.yaml`) | API free |
| Propylene/feedstock | **EIA** (đã có) + FRED | API free |
| Kẽm (driver zinc stearate) | Nhập tay (form nội bộ) hoặc index businessanalytiq | Thủ công/định kỳ |
| Carbon black, phụ gia đặc thù | businessanalytiq index / báo giá NCC (form) | Index/thủ công |

## Đã cấu hình sẵn (draft, `enabled: false` cho tới khi dò selector)

Trong `config/price_sources.yaml` đã thêm **MPOC** và **MPOB** (dầu cọ, dùng `anchor_text`
để bền layout) + **SCI carbon black/propylene** (ghi chú cần kiểm ToS/đăng nhập).
LME và Investing.com **KHÔNG** thêm làm mục tiêu cào (ToS) — để ở `source_links.yaml`
với ghi chú "form nội bộ".

## Bước tiếp để bật nguồn dầu cọ (MPOB/MPOC)
Vì các trang chống bot, **chạy trên máy/server bạn** (không chạy được trong sandbox này):
```bash
cd backend && pip install "scrapling[fetchers]" && scrapling install   # browser cho stealthy
python -m app.cli inspect "https://www.mpoc.org.my/market-insight/daily-palm-oil-prices/"
# -> xem selector gợi ý, hoặc lưu trang thành .html rồi gửi tôi dò offline
```

## Sources
- [SCI99](https://intl.sci99.com/) · [SCI Propylene](https://intl.sci99.com/industry/12605/price) · [SCI Carbon black](https://intl.sci99.com/industry/12969/price)
- [MPOC Daily Palm Oil Prices](https://www.mpoc.org.my/market-insight/daily-palm-oil-prices/)
- [MPOB daily prices](https://bepi.mpob.gov.my/index.php/price/daily)
- [Investing.com FCPO](https://vn.investing.com/commodities/malaysian-crude-palm-oil-futures-streaming-chart)
- [LME Zinc](https://www.lme.com/en/Metals/Non-ferrous/LME-Zinc) · [LME Official Prices](https://www.lme.com/Market-data/LME-reference-prices/LME-Official-Price)
