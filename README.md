# SkyGate API

Backend inicial do SkyGate, um web app de navegação inteligente em aeroportos. O MVP representa o aeroporto como um grafo e calcula a rota de menor tempo entre dois pontos, incluindo instruções, tempo livre e serviços encontrados no caminho.

> **Aviso:** o mapa e os dados do seed de Fortaleza são exclusivamente esquemáticos e demonstrativos. Eles não representam distâncias oficiais e não constituem mapa oficial ou licenciado do Aeroporto de Fortaleza.

## Arquitetura

O projeto usa Python 3.12, FastAPI, Pydantic, SQLAlchemy e Postgres/Supabase. As responsabilidades estão separadas em:

- `src/api`: endpoints e dependências HTTP;
- `src/services`: regras de negócio e Dijkstra;
- `src/repositories`: acesso aos dados;
- `src/schemas`: contratos de entrada e saída;
- `src/models`: modelos SQLAlchemy;
- `src/db`: engine, sessão e base do ORM;
- `src/core`: configurações da aplicação;
- `src/utils`: funções auxiliares;
- `migrations`: schema SQL e seed do Aeroporto de Fortaleza.

## Como rodar localmente

Requer Python 3.12 e acesso a um banco Postgres/Supabase.

```bash
python -m venv .venv
```

No Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn main:app --reload
```

A API ficará disponível em `http://127.0.0.1:8000`. A documentação interativa estará em `http://127.0.0.1:8000/docs`.

## Configuração do `.env`

Copie `.env.example` para `.env` e ajuste:

- `DATABASE_URL`: connection string do Postgres. Strings iniciadas em `postgres://` ou `postgresql://` são normalizadas para o driver `psycopg`;
- `SUPABASE_URL`: URL do projeto Supabase, reservada para integrações futuras;
- `SUPABASE_SERVICE_ROLE_KEY`: chave de serviço do Supabase, sem expô-la no repositório;
- `APP_ENV`: ambiente, por exemplo `development` ou `production`;
- `CORS_ORIGINS`: origens permitidas separadas por vírgula.
- `CORS_ORIGIN_REGEX`: expressão regular para deployments de preview da Vercel.

Em produção, defina `APP_ENV=production` e informe em `CORS_ORIGINS` a URL
canônica exata do frontend na Vercel. Origens locais só são adicionadas quando
`APP_ENV` é `development`, `dev` ou `local`.

## Deploy em produção com Traefik

O domínio público do backend é `https://api.skygate.com.br`. O serviço entra na
rede Docker externa `n8n_default`, usada pelo Traefik, e não publica a porta 8000
no host na configuração final. O certresolver esperado no Traefik é
`mytlschallenge`.

Antes do deploy, aponte somente o registro DNS `A` de `api.skygate.com.br` para
`212.85.0.237`. O domínio do frontend permanece na Vercel.

No primeiro deploy, use o override temporário para manter a porta legada 8003
até o HTTPS ser validado:

```bash
cp .env ".env.backup_$(date +%Y%m%d-%H%M%S)"
# Edite .env: use APP_ENV=production e a URL canonica real em CORS_ORIGINS.
docker network inspect n8n_default
docker compose -f docker-compose.yml -f docker-compose.bootstrap.yml config
docker compose -f docker-compose.yml -f docker-compose.bootstrap.yml up -d --build
curl -fsS https://api.skygate.com.br/health
```

Depois que o último comando confirmar o HTTPS, remova a publicação
`0.0.0.0:8003->8000` recriando o serviço apenas com a configuração final:

```bash
docker compose up -d --build --force-recreate
docker compose ps
curl -fsS https://api.skygate.com.br/health
curl -fsS http://127.0.0.1:8003/health && echo "ERRO: porta 8003 ainda publicada" || echo "OK: porta 8003 fechada"
```

## Migrations no Supabase

No painel do Supabase, abra o **SQL Editor** e execute os arquivos de `migrations/` em ordem, de `001_create_airports.sql` até `006_seed_fortaleza_airport.sql`. O último arquivo cria os dados simplificados do Aeroporto de Fortaleza e pode ser executado novamente sem duplicar arestas ou serviços.

Também é possível aplicar os arquivos com uma ferramenta Postgres, usando a connection string do projeto:

```bash
psql "$DATABASE_URL" -f migrations/001_create_airports.sql
```

Repita o comando para os demais arquivos, seguindo a ordem numérica.

## Docker e Traefik

Crie o `.env` e execute:

```bash
docker compose up -d --build
```

O serviço e o container se chamam `skygate-api`. O compose usa a rede externa `n8n_default`, que deve existir na VPS, e mantém `api.SEUDOMINIO.com` como placeholder. Substitua apenas no ambiente de deploy.

## Endpoints

- `GET /health`: verifica se a API está ativa;
- `GET /health/database`: verifica a disponibilidade do Postgres com `SELECT 1`;
- `GET /airports/{slug}`: retorna os dados básicos do aeroporto;
- `GET /airports/{slug}/map`: retorna nós, arestas e serviços para o mapa;
- `POST /routes/calculate`: calcula e salva uma sessão de rota.

### Modos de rota

- `fastest`: menor tempo de caminhada respeitando a direção das arestas;
- `accessible`: exclui nós e arestas não acessíveis, nós restritos e escadas;
- `with_stop`: calcula uma única parada opcional em um business vinculado a um nó físico.

O request antigo continua válido e assume `route_mode: "fastest"`. Para uma parada, informe um `business_id` específico ou uma `stop_category`, nunca ambos:

```json
{
  "airport_slug": "fortaleza",
  "journey_type": "boarding",
  "origin_code": "entrada_principal",
  "destination_code": "portao_06",
  "boarding_time": "2026-07-13T20:30:00-03:00",
  "route_mode": "with_stop",
  "preferences": {
    "avoid_stairs": true,
    "stop_category": "cafe",
    "max_detour_minutes": 5
  }
}
```

`estimated_time_minutes` é apenas o tempo de caminhada da rota escolhida. Quando há parada, `total_estimated_time_minutes` soma a caminhada e o tempo estimado no estabelecimento. A API também retorna a rota direta, o desvio, a viabilidade antes do embarque e warnings estruturados quando a parada não cabe no horário disponível.

Os pisos são agrupados em `floor_segments`; a troca de piso exige uma aresta real de elevador, escada ou escada rolante. `connector_group` apenas identifica equipamentos correlatos e não cria conexões automáticas. Lojas e serviços permanecem vinculados a nós físicos e nunca são usados como atalhos pelo Dijkstra. O MVP suporta no máximo uma parada.

Os dados de mapa e tempos podem ser estimados. Consulte `is_estimated`, `location_is_estimated`, `source_note` e `validated_at` antes de tratá-los como informação operacional oficial.

Exemplo:

```bash
curl -X POST http://127.0.0.1:8000/routes/calculate \
  -H "Content-Type: application/json" \
  -d '{
    "airport_slug": "fortaleza",
    "journey_type": "boarding",
    "origin_code": "entrada_principal",
    "destination_code": "portao_12",
    "boarding_time": "2026-05-25T18:30:00-03:00"
  }'
```

Com o seed fornecido, o caminho esquemático de `entrada_principal` até `portao_12` passa apenas por nós físicos de navegação: `area_checkin`, `controle_seguranca`, `corredor_central` e `juncao_portoes_10_12`. O percurso demonstrativo leva 18 minutos. O tempo livre é calculado entre o instante atual e o embarque, descontando o tempo estimado da rota, e nunca fica negativo.

Os estabelecimentos não são vértices do grafo. Cada business é vinculado ao nó físico mais próximo e só aparece em `services_on_path` quando esse nó pertence ao caminho calculado. Serviços próximos com desvio (`nearby`) ainda não fazem parte deste MVP.

## Dijkstra

O algoritmo está implementado manualmente em `src/services/dijkstra_service.py`. Ele usa `heapq` como fila de prioridade, considera `walk_time_minutes` como peso de cada aresta e reconstrói o caminho mais rápido. Quando o destino não é alcançável, o serviço retorna um erro de rota impossível.

## Editor interno do mapa de Fortaleza

Os mapas de referência ficam em `data/airports/fortaleza/maps/`, um SVG por piso (`fortaleza_piso_0.svg` a `fortaleza_piso_3.svg`). Eles são somente referência visual; o editor não extrai corredores dos paths.

Para abrir o editor, inicie um servidor HTTP na raiz e abra `http://localhost:8001/tools/map-editor/` (não abra o HTML diretamente, pois os SVGs são carregados pelo navegador):

```powershell
python -m http.server 8001
```

O editor salva rascunhos no `localStorage`, desenha nós e arestas, valida o grafo e testa Dijkstra normal ou acessível. Ao clicar no mapa, salva as coordenadas reais do `viewBox`. O download se chama `graph_v1.json`; mova/substitua esse arquivo em `data/airports/fortaleza/graph_v1.json` antes da importação. O arquivo já nesse caminho é o template canônico vazio.

### Regra de modelagem de nós e businesses

Nós representam pontos físicos de navegação. Lojas, companhias aéreas e serviços não devem virar nós separados quando estiverem na mesma área física. Vários registros de `businesses` podem compartilhar o mesmo `node_id`; por exemplo, LATAM, Azul e GOL podem apontar para o único nó físico **Área de check-in doméstico**.

### Conectar nós

Ative **Conectar nós**, clique em um nó existente para definir a origem e depois em outro nó para definir o destino. O editor cria somente uma aresta bidirecional, acessível e do tipo `corridor`; nenhum nó é criado ou alterado. A distância é calculada automaticamente pelas coordenadas dos dois nós.

Depois de criar a aresta, o nó de destino permanece destacado e passa a ser a origem da próxima conexão. Assim é possível conectar uma sequência inteira sem sair do modo. Ligações duplicadas são recusadas, inclusive quando os códigos aparecem no sentido inverso em uma aresta bidirecional. Para inspecionar, editar ou excluir uma ligação, saia do modo e clique na linha correspondente.

Na primeira abertura desta versão, o conteúdo textual atual de `skygate:fortaleza:graph:v1` é copiado, sem conversão, para `skygate:fortaleza:graph:v1:backup:before-corridor-v2`. A cópia é idempotente e a chave original continua sendo usada, preservando importação, exportação e o formato de `graph_v1.json`.

Os testes unitários do modo de conexão usam o runner nativo do Node.js:

```powershell
node --test tools/map-editor/connections.test.js
```

Para validar sem gravar no banco:

```powershell
python scripts/import_airport_graph.py data/airports/fortaleza/graph_v1.json --dry-run
```

Para importar em um banco configurado por `DATABASE_URL`, remova `--dry-run`. O script localiza o aeroporto por `airport.slug`, faz upsert de nós por `airport_id + code`, resolve `from_code`/`to_code`, atualiza ou insere arestas e associa estabelecimentos por `node_code`, em uma única transação. Não remove dados existentes. O JSON usa `walk_time_seconds`, convertido para `walk_time_minutes` pelo modelo atual.

## Testes

```bash
pytest
```

Os testes cobrem o menor caminho, a rota impossível e o fluxo básico do serviço de cálculo sem exigir banco de dados.
