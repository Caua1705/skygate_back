create table if not exists airport_businesses (
    id uuid primary key default gen_random_uuid(),
    airport_id uuid not null references airports(id) on delete cascade,
    node_id uuid not null references airport_nodes(id) on delete cascade,
    name text not null,
    category text not null,
    description text,
    estimated_stop_minutes numeric default 0 check (estimated_stop_minutes >= 0),
    is_active boolean default true,
    created_at timestamptz default now()
);

create index if not exists airport_businesses_airport_id_idx on airport_businesses(airport_id);
create index if not exists airport_businesses_node_id_idx on airport_businesses(node_id);

