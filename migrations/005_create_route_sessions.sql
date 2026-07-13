create table if not exists route_sessions (
    id uuid primary key default gen_random_uuid(),
    airport_id uuid references airports(id),
    origin_node_id uuid references airport_nodes(id),
    destination_node_id uuid references airport_nodes(id),
    journey_type text,
    boarding_time timestamptz,
    estimated_time_minutes numeric,
    free_time_minutes numeric,
    path jsonb,
    services_on_path jsonb,
    created_at timestamptz default now()
);

create index if not exists route_sessions_airport_id_idx on route_sessions(airport_id);

