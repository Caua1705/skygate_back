create table if not exists airport_edges (
    id uuid primary key default gen_random_uuid(),
    airport_id uuid not null references airports(id) on delete cascade,
    from_node_id uuid not null,
    to_node_id uuid not null,
    walk_time_minutes numeric not null,
    distance_meters numeric,
    instruction text,
    is_accessible boolean default true,
    created_at timestamptz default now(),
    constraint airport_edges_from_node_fk
        foreign key (airport_id, from_node_id)
        references airport_nodes(airport_id, id) on delete cascade,
    constraint airport_edges_to_node_fk
        foreign key (airport_id, to_node_id)
        references airport_nodes(airport_id, id) on delete cascade,
    constraint airport_edges_airport_from_to_key
        unique (airport_id, from_node_id, to_node_id),
    constraint airport_edges_walk_time_non_negative
        check (walk_time_minutes >= 0),
    constraint airport_edges_distance_non_negative
        check (distance_meters is null or distance_meters >= 0)
);

create index if not exists airport_edges_airport_id_idx on airport_edges(airport_id);
create index if not exists airport_edges_from_node_id_idx on airport_edges(from_node_id);
