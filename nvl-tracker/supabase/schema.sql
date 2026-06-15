-- =============================================================================
-- Lược đồ Supabase / PostgreSQL — Price Intelligence NVL (đầy đủ)
-- Chạy trong Supabase Studio > SQL Editor. Idempotent (chạy lại không vỡ DB).
-- =============================================================================

-- 1) Giá thô (một nguồn chân lý cho mọi báo giá)
create table if not exists price_master (
    id            bigint generated always as identity primary key,
    date          date        not null,                 -- NGÀY của mức giá
    product       text        not null,
    region        text,
    price_type    text,                                 -- spot|futures|unit_value|quote
    payment_term  text        default 'at_sight',
    raw_price     double precision not null,
    raw_unit      text,                                  -- usd_per_ton|cents_per_lb|rmb_per_ton|usd_per_bbl
    value_vnd_kg  double precision,                      -- quy đổi (tuỳ chọn)
    source        text,
    note          text,
    created_at    timestamptz not null default now(),
    unique (date, product, region, source, payment_term)
);
create index if not exists idx_pm_prod_date on price_master (product, date desc);

-- 2) Tỷ giá
create table if not exists fx_rates (
    date       date primary key,
    usd_vnd    double precision not null,
    rmb_vnd    double precision,
    created_at timestamptz not null default now()
);

-- 3) Landed + at-sight tương đương (tính 1 lần)
create table if not exists landed (
    id             bigint generated always as identity primary key,
    date           date not null,
    product        text not null,
    region         text,
    price_type     text,
    payment_term   text,
    raw_price      double precision,
    raw_unit       text,
    usd_per_ton    double precision,
    landed_vnd_kg  double precision,
    usance_benefit double precision,
    at_sight_equiv double precision,
    is_best        boolean default false,
    source         text,
    created_at     timestamptz not null default now()
);
create index if not exists idx_landed_prod_date on landed (product, date desc);

-- 4) Spread / chỉ báo dẫn
create table if not exists spreads (
    id         bigint generated always as identity primary key,
    date       date not null,
    name       text not null,
    value      double precision,
    unit       text,
    signal     text,
    note       text,
    created_at timestamptz not null default now()
);

-- 5) Dự báo
create table if not exists forecast (
    id         bigint generated always as identity primary key,
    run_date   date not null,
    product    text not null,
    week       int  not null,
    yhat       double precision,
    lower      double precision,
    upper      double precision,
    model      text,
    mape       double precision,
    theils_u   double precision,
    confidence text,
    basis      text,
    created_at timestamptz not null default now(),
    unique (run_date, product, week)
);

-- 6) Tin tức (chỉ tiêu đề + tóm tắt + link)
create table if not exists news (
    id           bigint generated always as identity primary key,
    published_at date,
    title        text,
    summary      text,
    url          text unique,
    source       text,
    category     text,
    created_at   timestamptz not null default now()
);

-- 7) Kết quả phân tích tính-1-lần (để DOCX/Web/Telegram đọc chung — đảm bảo parity)
create table if not exists analysis (
    run_date   date not null,
    kind       text not null,            -- kpi | narrative | alerts | meta
    payload    jsonb not null,
    created_at timestamptz not null default now(),
    primary key (run_date, kind)
);

-- 8) Nhật ký kiểm toán (QC: bản ghi nhảy >10% → flag review, KHÔNG xoá)
create table if not exists audit_log (
    id         bigint generated always as identity primary key,
    at         timestamptz not null default now(),
    kind       text,
    detail     text
);

-- 9) Báo cáo (metadata DOCX)
create table if not exists reports (
    report_id  text primary key,
    title      text,
    summary    text,
    content_md text,
    docx_path  text,
    created_at timestamptz not null default now()
);
create index if not exists idx_reports_created on reports (created_at desc);

-- View: giá mới nhất mỗi NVL (dùng bởi dashboard/API)
create or replace view latest_prices as
select distinct on (product)
    product as material_code, product as material_name, raw_price as price,
    raw_unit as unit, source, date as scraped_at
from price_master
order by product, date desc;

-- =============================================================================
-- (Tuỳ chọn) RLS chỉ-đọc cho frontend dùng anon key. Backend dùng service_role.
-- =============================================================================
-- alter table price_master enable row level security;
-- alter table news enable row level security;
-- create policy "read price_master" on price_master for select using (true);
-- create policy "read news" on news for select using (true);
