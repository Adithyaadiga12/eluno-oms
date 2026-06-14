-- Eluno OMS schema
-- Paste this whole file into Supabase SQL Editor and click "Run".
-- Idempotent: safe to re-run.

-- Drop in reverse-dependency order (safe re-run)
drop table if exists order_status_history cascade;
drop table if exists orders cascade;
drop table if exists lens_inventory cascade;
drop table if exists sla_config cascade;
drop table if exists stores cascade;

-- =============================================================
-- 1. Stores
-- =============================================================
create table stores (
    id uuid primary key default gen_random_uuid(),
    name text not null,
    city text not null,
    created_at timestamptz default now()
);

-- =============================================================
-- 2. Lens inventory
-- Each row = one SKU (lens type + index + power + optional coating) at one store
-- =============================================================
create table lens_inventory (
    id uuid primary key default gen_random_uuid(),
    lens_type text not null check (lens_type in ('Single Vision', 'Bifocal', 'Progressive')),
    lens_index numeric(3, 2) not null,
    sph_power numeric(4, 2) not null,
    cyl_power numeric(4, 2) default 0,
    coating text,
    quantity int not null default 0,
    reserved int default 0,
    store_id uuid references stores(id) on delete set null,
    created_at timestamptz default now()
);
create index on lens_inventory (lens_type, lens_index, sph_power);

-- =============================================================
-- 3. SLA config
-- Hours allowed per stage per lens type
-- =============================================================
create table sla_config (
    id uuid primary key default gen_random_uuid(),
    lens_type text not null,
    stage text not null,
    sla_hours int not null,
    unique (lens_type, stage)
);

-- =============================================================
-- 4. Orders
-- =============================================================
create table orders (
    id uuid primary key default gen_random_uuid(),
    order_number text unique not null,
    customer_name text not null,
    customer_phone text,
    customer_email text,
    source text default 'Website',
    store_id uuid references stores(id) on delete set null,

    -- Prescription
    sph_right numeric(4, 2),
    cyl_right numeric(4, 2),
    axis_right int,
    add_right numeric(3, 2),
    sph_left numeric(4, 2),
    cyl_left numeric(4, 2),
    axis_left int,
    add_left numeric(3, 2),
    pd numeric(4, 1),

    -- Lens
    lens_type text not null,
    lens_index numeric(3, 2) not null,
    coating text,
    frame_model text,

    -- Status
    status text not null default 'Placed',
    inventory_status text,

    -- SLA tracking
    stage_started_at timestamptz default now(),
    reorder_count int default 0,
    is_paused boolean default false,

    -- Alert tracking
    last_alert_sent_at timestamptz,
    breach_risk numeric(3, 2),
    breach_reason text,

    created_at timestamptz default now(),
    updated_at timestamptz default now()
);
create index on orders (status);
create index on orders (lens_type);
create index on orders (store_id);

-- =============================================================
-- 5. Order status history (audit trail)
-- =============================================================
create table order_status_history (
    id uuid primary key default gen_random_uuid(),
    order_id uuid not null references orders(id) on delete cascade,
    from_status text,
    to_status text not null,
    reason text,
    changed_by text default 'system',
    created_at timestamptz default now()
);
create index on order_status_history (order_id);

-- =============================================================
-- 6. RLS posture
-- Service role bypasses RLS. We keep RLS off on these tables since
-- all writes go through the backend (not from the browser).
-- =============================================================
alter table stores disable row level security;
alter table lens_inventory disable row level security;
alter table sla_config disable row level security;
alter table orders disable row level security;
alter table order_status_history disable row level security;
