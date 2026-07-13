-- DADOS EXCLUSIVAMENTE ESQUEMÁTICOS E DEMONSTRATIVOS.
-- Este seed não representa distâncias oficiais e não constitui mapa oficial
-- ou licenciado do Aeroporto de Fortaleza.

insert into airports (name, slug, city, country)
values ('Aeroporto de Fortaleza', 'fortaleza', 'Fortaleza', 'Brasil')
on conflict (slug) do update set
    name = excluded.name,
    city = excluded.city,
    country = excluded.country;

with airport as (
    select id from airports where slug = 'fortaleza'
), node_data(code, name, type, floor, x, y) as (
    values
        ('entrada_principal', 'Entrada principal', 'entrance', 'térreo', 10, 80),
        ('area_checkin', 'Área de check-in', 'checkin', 'térreo', 20, 70),
        ('controle_seguranca', 'Controle de segurança', 'security', 'térreo', 30, 60),
        ('corredor_central', 'Corredor central', 'corridor', 'térreo', 45, 50),
        ('juncao_portoes_10_12', 'Junção dos portões 10 e 12', 'junction', 'térreo', 65, 45),
        ('juncao_portao_15', 'Junção do portão 15', 'junction', 'térreo', 60, 65),
        ('portao_10', 'Portão 10', 'gate', 'térreo', 80, 30),
        ('portao_12', 'Portão 12', 'gate', 'térreo', 85, 50),
        ('portao_15', 'Portão 15', 'gate', 'térreo', 80, 70),
        ('desembarque_domestico', 'Desembarque doméstico', 'arrival', 'térreo', 35, 90),
        ('desembarque_internacional', 'Desembarque internacional', 'arrival', 'térreo', 35, 10),
        ('area_bagagens', 'Área de bagagens', 'baggage_claim', 'térreo', 55, 90),
        ('saida_principal', 'Saída principal', 'exit', 'térreo', 80, 90)
)
insert into airport_nodes (airport_id, code, name, type, floor, x, y)
select airport.id, node_data.code, node_data.name, node_data.type, node_data.floor, node_data.x, node_data.y
from airport cross join node_data
on conflict (airport_id, code) do update set
    name = excluded.name,
    type = excluded.type,
    floor = excluded.floor,
    x = excluded.x,
    y = excluded.y;

with airport as (
    select id from airports where slug = 'fortaleza'
), edge_data(from_code, to_code, walk_time, distance, instruction) as (
    values
        ('entrada_principal', 'area_checkin', 3, 180, 'Siga até a área de check-in.'),
        ('area_checkin', 'entrada_principal', 3, 180, 'Siga até a entrada principal.'),
        ('area_checkin', 'controle_seguranca', 5, 300, 'Depois vá para o controle de segurança.'),
        ('controle_seguranca', 'area_checkin', 5, 300, 'Siga até a área de check-in.'),
        ('controle_seguranca', 'corredor_central', 3, 180, 'Siga pelo corredor central.'),
        ('corredor_central', 'controle_seguranca', 3, 180, 'Siga até o controle de segurança.'),
        ('corredor_central', 'juncao_portoes_10_12', 3, 180, 'Siga até a junção dos portões 10 e 12.'),
        ('juncao_portoes_10_12', 'corredor_central', 3, 180, 'Retorne ao corredor central.'),
        ('juncao_portoes_10_12', 'portao_10', 2, 120, 'Continue até o Portão 10.'),
        ('portao_10', 'juncao_portoes_10_12', 2, 120, 'Siga até a junção dos portões 10 e 12.'),
        ('juncao_portoes_10_12', 'portao_12', 4, 240, 'Continue até o Portão 12.'),
        ('portao_12', 'juncao_portoes_10_12', 4, 240, 'Siga até a junção dos portões 10 e 12.'),
        ('corredor_central', 'juncao_portao_15', 4, 240, 'Siga até a junção do Portão 15.'),
        ('juncao_portao_15', 'corredor_central', 4, 240, 'Retorne ao corredor central.'),
        ('juncao_portao_15', 'portao_15', 4, 240, 'Continue até o Portão 15.'),
        ('portao_15', 'juncao_portao_15', 4, 240, 'Siga até a junção do Portão 15.'),
        ('desembarque_internacional', 'corredor_central', 4, 240, 'Siga até o corredor central.'),
        ('corredor_central', 'desembarque_internacional', 4, 240, 'Siga até o desembarque internacional.'),
        ('desembarque_domestico', 'area_bagagens', 4, 240, 'Siga até a área de bagagens.'),
        ('area_bagagens', 'desembarque_domestico', 4, 240, 'Siga até o desembarque doméstico.'),
        ('area_bagagens', 'saida_principal', 5, 300, 'Continue até a saída principal.'),
        ('saida_principal', 'area_bagagens', 5, 300, 'Siga até a área de bagagens.')
)
insert into airport_edges (
    airport_id, from_node_id, to_node_id, walk_time_minutes,
    distance_meters, instruction, is_accessible
)
select airport.id, source_node.id, target_node.id, edge_data.walk_time,
       edge_data.distance, edge_data.instruction, true
from airport
join edge_data on true
join airport_nodes source_node
    on source_node.airport_id = airport.id and source_node.code = edge_data.from_code
join airport_nodes target_node
    on target_node.airport_id = airport.id and target_node.code = edge_data.to_code
where not exists (
    select 1 from airport_edges existing
    where existing.airport_id = airport.id
      and existing.from_node_id = source_node.id
      and existing.to_node_id = target_node.id
);

with airport as (
    select id from airports where slug = 'fortaleza'
), business_data(node_code, name, category, description, stop_minutes) as (
    values
        ('corredor_central', 'Café Central', 'cafe', 'Café e lanches rápidos.', 5),
        ('corredor_central', 'Farmácia Aero', 'pharmacy', 'Medicamentos e itens de viagem.', 4),
        ('juncao_portoes_10_12', 'Banheiro Próximo', 'bathroom', 'Banheiro próximo aos portões 10 e 12.', 3),
        ('controle_seguranca', 'Duty Free Fortaleza', 'shopping', 'Loja de produtos nacionais e importados.', 8)
)
insert into airport_businesses (
    airport_id, node_id, name, category, description,
    estimated_stop_minutes, is_active
)
select airport.id, node.id, business_data.name, business_data.category,
       business_data.description, business_data.stop_minutes, true
from airport
join business_data on true
join airport_nodes node
    on node.airport_id = airport.id and node.code = business_data.node_code
where not exists (
    select 1 from airport_businesses existing
    where existing.airport_id = airport.id and existing.name = business_data.name
);
