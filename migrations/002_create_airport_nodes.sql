create table if not exists airport_nodes (
    id uuid primary key default gen_random_uuid(),
    airport_id uuid not null references airports(id) on delete cascade,
    code text not null,
    name text not null,
    type text not null,
    floor text,
    x numeric,
    y numeric,
    created_at timestamptz default now(),
    constraint airport_nodes_airport_code_key unique (airport_id, code),
    constraint airport_nodes_airport_id_id_key unique (airport_id, id)
);

create index if not exists airport_nodes_airport_id_idx on airport_nodes(airport_id);
