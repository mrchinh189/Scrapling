-- =============================================================================
-- Lược đồ Supabase / PostgreSQL cho NVL Price Tracker
-- Chạy trong Supabase Studio > SQL Editor, hoặc: psql < schema.sql
-- =============================================================================

-- Bảng lưu lịch sử giá NVL
create table if not exists price_records (
    id            bigint generated always as identity primary key,
    material_code text        not null,
    material_name text,
    price         double precision not null,
    unit          text,
    currency      text default 'VND',
    source        text,
    source_url    text,
    raw_text      text,
    scraped_at    timestamptz not null default now()
);

create index if not exists idx_price_code_time
    on price_records (material_code, scraped_at desc);

-- Bảng báo cáo phân tích
create table if not exists reports (
    report_id   text primary key,
    title       text,
    summary     text,
    content_md  text,
    docx_path   text,
    created_at  timestamptz not null default now()
);

create index if not exists idx_reports_created
    on reports (created_at desc);

-- View: giá mới nhất của mỗi NVL (dùng bởi API /prices)
create or replace view latest_prices as
select distinct on (material_code)
    material_code, material_name, price, unit, currency,
    source, source_url, scraped_at
from price_records
order by material_code, scraped_at desc;

-- =============================================================================
-- Row Level Security (tuỳ chọn — bật nếu dùng anon key ở frontend)
-- Mặc định dùng service_role key ở backend nên không cần RLS.
-- =============================================================================
-- alter table price_records enable row level security;
-- alter table reports enable row level security;
-- create policy "read prices" on price_records for select using (true);
-- create policy "read reports" on reports for select using (true);
