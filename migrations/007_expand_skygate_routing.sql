-- Expansão idempotente do roteamento. Não executa nem altera o seed demonstrativo.

alter table airport_nodes add column if not exists zone text not null default 'public';
alter table airport_nodes add column if not exists connector_group text;
alter table airport_nodes add column if not exists is_accessible boolean not null default true;
alter table airport_nodes add column if not exists is_restricted boolean not null default false;
alter table airport_nodes add column if not exists is_estimated boolean not null default false;
alter table airport_nodes add column if not exists source_note text;
alter table airport_nodes add column if not exists validated_at timestamptz;

alter table airport_edges add column if not exists edge_type text not null default 'corridor';
alter table airport_edges add column if not exists is_bidirectional boolean not null default false;
alter table airport_edges add column if not exists is_estimated boolean not null default false;
alter table airport_edges add column if not exists source_note text;
alter table airport_edges add column if not exists validated_at timestamptz;

alter table airport_businesses add column if not exists external_id text;
alter table airport_businesses add column if not exists floor text;
alter table airport_businesses add column if not exists x numeric;
alter table airport_businesses add column if not exists y numeric;
alter table airport_businesses add column if not exists opening_hours jsonb;
alter table airport_businesses add column if not exists location_is_estimated boolean not null default false;
alter table airport_businesses add column if not exists source_note text;
alter table airport_businesses add column if not exists validated_at timestamptz;

alter table route_sessions add column if not exists route_mode text not null default 'fastest';
alter table route_sessions add column if not exists preferences jsonb;
alter table route_sessions add column if not exists selected_business_id uuid;
alter table route_sessions add column if not exists direct_estimated_time_minutes numeric;
alter table route_sessions add column if not exists stop_time_minutes numeric;
alter table route_sessions add column if not exists total_estimated_time_minutes numeric;
alter table route_sessions add column if not exists detour_minutes numeric;
alter table route_sessions add column if not exists stop_feasible boolean;
alter table route_sessions add column if not exists floor_segments jsonb;
alter table route_sessions add column if not exists warnings jsonb;

do $$
begin
    if not exists (select 1 from pg_constraint where conname = 'airport_nodes_zone_check') then
        alter table airport_nodes add constraint airport_nodes_zone_check
            check (zone in ('public', 'checkin', 'security', 'domestic_airside', 'international_airside', 'connection', 'baggage_claim', 'restricted'));
    end if;
    if not exists (select 1 from pg_constraint where conname = 'airport_edges_edge_type_check') then
        alter table airport_edges add constraint airport_edges_edge_type_check
            check (edge_type in ('corridor', 'ramp', 'stairs', 'escalator', 'elevator', 'security', 'boarding', 'restricted_transition'));
    end if;
    if not exists (select 1 from pg_constraint where conname = 'route_sessions_route_mode_check') then
        alter table route_sessions add constraint route_sessions_route_mode_check
            check (route_mode in ('fastest', 'accessible', 'with_stop'));
    end if;
    if not exists (select 1 from pg_constraint where conname = 'route_sessions_selected_business_fk') then
        alter table route_sessions add constraint route_sessions_selected_business_fk
            foreign key (selected_business_id) references airport_businesses(id) on delete set null;
    end if;
end $$;

create index if not exists airport_nodes_airport_floor_idx on airport_nodes(airport_id, floor);
create index if not exists airport_nodes_connector_group_idx on airport_nodes(airport_id, connector_group) where connector_group is not null;
create index if not exists airport_edges_airport_edge_type_idx on airport_edges(airport_id, edge_type);
create index if not exists airport_businesses_active_category_idx on airport_businesses(airport_id, category) where is_active = true;
create unique index if not exists airport_businesses_airport_external_id_key on airport_businesses(airport_id, external_id) where external_id is not null;
create index if not exists route_sessions_route_mode_idx on route_sessions(route_mode);
create index if not exists route_sessions_selected_business_id_idx on route_sessions(selected_business_id);
