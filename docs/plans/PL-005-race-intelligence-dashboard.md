# Plano de Implementação F1-007: Race Intelligence Dashboard

## Status E Metadados

- Status: Completed
- Data: 2026-06-16
- Responsável: Roberto / Codex (Engenheiro Chefe)
- Complexidade: HIGH
- Decisões relacionadas: F1-003, F1-004, F1-005, F1-006
- Revisão multiagente: Completed em 2026-06-16
- Supersedes: None
- Superseded by: None

## Objetivo E Resultado Esperado

Transformar o OpenF1 Data Platform em uma experiência de Race Intelligence
consumível por recrutadores, tech leads e futuros usuários analíticos, conectando
o lakehouse local, a API FastAPI e uma interface visual de análise de corrida.

Resultado esperado: um dashboard navegável por sessão e piloto, com visão de
estratégia, telemetria, eventos de corrida, pit stops, stints, predições Gold e
saúde do pipeline, sem expor documentação interna ou depender de dados manuais
fora do lakehouse.

## Contexto E Estado Atual

- VERIFIED: O plano F1-006 registra que a parametrização CLI, escrita atômica,
  Gold particionada, endpoint de execução de pipeline e testes de API/integridade
  já foram implementados e verificados.
- VERIFIED: `src/web/routers/analytics.py` já expõe endpoints para sessões,
  pilotos, clima, stints, race control, vencedor, duelo, predições, ultrapassagens,
  execução de pipeline, SQL seguro e chat TF-IDF.
- VERIFIED: `src/web/database.py` mapeia views DuckDB sobre Parquet Silver/Gold,
  incluindo Gold particionada.
- VERIFIED: `src/dashboard/app.py` ainda lê arquivos Parquet planos como
  `data/weather.parquet`, `data/drivers.parquet`, `data/intervals.parquet` e
  `data/car_data.parquet`, divergindo do layout medalhão atual.
- VERIFIED: `Formula Insights/` existe como inspiração visual local, mas não deve
  ser tratado como produto final nem copiado como arquitetura do projeto.
- VERIFIED: F1-005 ainda possui pendências para MLflow, ChromaDB e
  `sentence-transformers`; F1-006 recomenda tratá-las como próxima etapa apenas
  se o objetivo for completar integralmente o F1-005.
- VERIFIED: Reavaliação multiagente concluiu que o F1-007 é válido como MVP de
  dashboard, mas precisa de revisão de contrato/API antes da execução.
- VERIFIED: Reavaliação de Produto/Frontend recomenda fechar a decisão por
  frontend web próprio consumindo FastAPI, mantendo Streamlit como legado ou
  fallback exploratório.
- VERIFIED: Reavaliação de IA/MLOps recomenda manter MLflow, ChromaDB,
  `sentence-transformers`, SLA detalhado e freshness por fonte fora do F1-007 e
  criar F1-008 separado se Roberto quiser fechar integralmente o F1-005.

## Registro De Decisões Do Plano

| ID | Decisão | Por Quê | Premissas | Alternativas Rejeitadas | Evidência | Impacto | Validação |
|---|---|---|---|---|---|---|---|
| RID-001 | Priorizar o dashboard Race Intelligence antes de MLflow/ChromaDB. | O projeto já tem dados, API e predições básicas suficientes para demonstrar valor; o gargalo de portfolio agora é experiência consumível. | O objetivo atual é desenvolvimento de portfolio/produto, não completar integralmente F1-005. | Implementar MLflow/ChromaDB primeiro. | F1-006 linhas 23-26; `analytics.py`; `dashboard/app.py`. | Entrega valor visível mais cedo e reduz risco de adicionar dependências sem UX clara. | Dashboard deve consumir endpoints reais e passar smoke tests. |
| RID-002 | Usar FastAPI como contrato principal da UI, não leitura direta de Parquet no dashboard. | A API já encapsula DuckDB, segurança SQL e views Silver/Gold; a UI deve consumir produto analítico, não acoplar ao layout físico. | API local será executada junto do dashboard. | Manter Streamlit/HTML lendo arquivos Parquet diretamente. | `src/web/database.py`; `src/web/routers/analytics.py`; `src/dashboard/app.py`. | Menor acoplamento entre armazenamento e experiência visual. | Testes de contrato dos endpoints e smoke test da UI. |
| RID-003 | Definir uma camada de endpoints agregados para tela, evitando lógica analítica pesada no frontend. | Métricas de duelo, timeline, saúde do pipeline e cards executivos devem ter grão e semântica claros no backend. | FastAPI/DuckDB suporta agregações locais com latência aceitável para uso local. | Recalcular tudo no navegador/Streamlit. | Endpoints atuais já executam agregações em DuckDB. | Backend vira serving layer consistente e testável. | Testes unitários por endpoint agregado. |
| RID-004 | Tratar AI/RAG como recurso assistivo posterior, não como eixo principal da tela inicial. | Literatura local sustenta começar com soluções simples e visíveis antes de sistemas de ML mais complexos. | O chat TF-IDF atual pode permanecer como aba secundária. | Bloquear dashboard até ChromaDB/MLflow. | Designing ML Systems linhas 7008-7030; F1-005/F1-006. | Reduz risco operacional e mantém evolução incremental. | Critério de aceite: dashboard funciona sem dependências novas de IA. |
| RID-005 | Expor observabilidade orientada a sintomas do usuário analítico: freshness, duração, linhas, quarentena e status por sessão. | Observabilidade deve ajudar a entender estado interno e sintomas visíveis, não apenas logs soltos. | `fact_pipeline_execution` é a fonte inicial de execução. | Criar alertas complexos antes de métricas visíveis. | Observability Engineering linhas 2542-2612; F1-006 linhas 19-26. | Melhora confiança de consumo e narrativa de operação. | Endpoint e painel de saúde retornam dados mesmo quando não há execução recente. |
| RID-006 | Fechar F1-007 em frontend web próprio servido por/consumindo FastAPI, não Streamlit como MVP principal. | O README já anuncia HTML/CSS/JS/Plotly e o Streamlit atual lê Parquet direto, não entrega a experiência prometida nem o contrato de produto. | Roberto aceita priorizar valor de portfolio/produto sobre menor tempo absoluto de implementação. | Evoluir Streamlit como vitrine principal. | Parecer Produto/Frontend; `README.md`; `src/dashboard/app.py`. | Aumenta valor visual e deixa clara a separação entre serving e UI. | Smoke visual desktop/mobile e consumo real da API. |
| RID-007 | Tornar contratos de serving gate obrigatório antes da UI. | Endpoints atuais não usam `response_model`, alguns retornam lista vazia em exceções e o fallback DuckDB `dummy` pode mascarar schema quebrado. | Endpoints novos preservarão compatibilidade dos endpoints existentes. | Implementar UI antes de contratos agregados. | Parecer Engenharia de Dados/API; `src/web/database.py`; `src/web/routers/analytics.py`. | Reduz risco de UI instável e estados vazios falsos. | Testes negativos de schema/dataset ausente e modelos Pydantic. |
| RID-008 | Tratar F1-005 restante como F1-008 separado, se aprovado. | MLflow, ChromaDB, embeddings densos, SLA detalhado e freshness por fonte são pendências substantivas, não pré-requisitos do dashboard MVP. | F1-007 é portfolio/product-first. | Misturar MLOps completo no F1-007. | Parecer IA/MLOps; F1-005; F1-006; `requirements.txt`. | Mantém escopo executável e reduz dependências novas neste ciclo. | F1-007 não declara fechamento de MLflow/ChromaDB/SLA detalhado. |

## Evidências, Premissas E Lacunas

| Tipo | Item | Fonte/Validação |
|---|---|---|
| VERIFIED | Planos ativos e pendências existentes. | `docs/plans/PL-004-execucao-planos-004-005.md` linhas 1-26. |
| VERIFIED | Convenção de planos numerados e necessidade de registrar evidências, riscos, rollout e aceite. | `docs/plans/README.md` linhas 17-50. |
| VERIFIED | API analítica existente com endpoints de corrida, Gold, pipeline execution, SQL e chat. | `src/web/routers/analytics.py`. |
| VERIFIED | DuckDB views mapeadas para Silver/Gold particionadas. | `src/web/database.py`. |
| VERIFIED | Dashboard Streamlit atual está desalinhado do layout medalhão atual. | `src/dashboard/app.py`. |
| VERIFIED | FastAPI atual não serve frontend estático e inclui apenas routers de telemetry, analytics e CI alerts. | `src/web/main.py`. |
| VERIFIED | Docker Compose ainda sobe Streamlit como serviço `dashboard`. | `docker-compose.yml`. |
| VERIFIED | `requirements.txt` não contém `mlflow`, `chromadb` ou `sentence-transformers`. | `requirements.txt`. |
| SOURCED | Data product deve ser desenhado a partir dos consumidores e entregar valor de negócio. | Deciphering Data Architectures linhas 6875-6905, sha256 `2beb6920fe906c2a9aac124f89d25fb54d52dbf8e491e01c7172cc99e86468d4`. |
| SOURCED | Sistemas de dados/ML precisam de observabilidade e deployment operacionalizado. | Fundamentals of Data Engineering linhas 15749-15758, sha256 `02f5198105a3ce549217c6f345ec7bc557f6e0f8de9989fcaa461f86315791fe`. |
| SOURCED | Em ML, começar simples pode ser suficiente antes de sistemas complexos. | Designing Machine Learning Systems linhas 7008-7030, sha256 `04bbe6aea8aeb48959e924f887b5b9bbf89661c2642ef876c1ef4ae025090e7e`. |
| SOURCED | Observabilidade deve apoiar raciocínio sobre estado interno e sintomas de falhas. | Observability Engineering linhas 2542-2612, sha256 `c891daf1bd86fecea730b4f6d92c1bdbae3d3faefe3a2378691cae106953df0a`. |
| ASSUMED | O dashboard será inicialmente local e portfolio-first, sem autenticação pública. | Validar antes de deploy externo. |
| VERIFIED | Streamlit fica fora do caminho crítico do MVP após reavaliação multiagente. | Parecer Produto/Frontend e decisão RID-006. |

## Premissas Críticas

- A experiência visual deve consumir dados da API ou de contratos equivalentes,
  não caminhos físicos internos do lakehouse.
- O primeiro release deve funcionar com os dados e modelos já existentes, mesmo
  que MLflow/ChromaDB permaneçam pendentes.
- O dashboard deve deixar claro quando dados de Gold, predições ou pipeline
  execution ainda não existem para determinada sessão.
- Estados vazios devem distinguir `dataset_absent`, `no_rows_for_session`,
  `schema_incompatible`, `gold_unavailable`, `pipeline_history_unavailable` e
  `api_unavailable`.
- Endpoints novos consumidos pela UI devem ter modelos Pydantic de resposta ou
  contrato equivalente versionado no código.
- Nenhuma métrica de latência, performance ou acurácia será declarada sem teste
  reproduzível.
- Documentação pública deve permanecer sanitizada; planos detalhados continuam
  locais/privados salvo decisão explícita de publicação.

## Escopo Incluído

- Definir a experiência Race Intelligence por telas e jornadas.
- Criar ou ajustar endpoints backend para uma UI orientada a análise:
  - resumo de sessão;
  - cards de pilotos;
  - timeline de eventos;
  - stints/pit stops;
  - duelo entre pilotos;
  - predições Gold;
  - saúde do pipeline.
- Corrigir o dashboard para consumir a camada serving atual.
- Criar frontend web próprio, preferencialmente HTML/CSS/JS/Plotly servido por
  FastAPI ou consumindo FastAPI localmente.
- Adicionar testes de contrato para endpoints novos/alterados.
- Adicionar smoke test mínimo da aplicação visual quando houver servidor.
- Atualizar documentação pública com resumo seguro da experiência entregue.

## Fora De Escopo

- Deploy público com autenticação, billing ou multi-tenant.
- MLflow Model Registry, ChromaDB e embeddings densos, salvo se uma fase posterior
  deste plano for explicitamente aprovada.
- SLA detalhado por fonte/partição, `data_freshness_minutes` por fonte e endpoint
  `/api/pipeline_execution/sla`; estes itens devem entrar em F1-008 se Roberto
  aprovar completar o F1-005.
- Reescrita completa do pipeline de ingestão.
- Alterar contratos Silver/Gold sem plano de compatibilidade separado.
- Copiar diretamente arquivos do `Formula Insights/` como produto final.

## Alternativas Avaliadas E Rejeitadas

1. Completar F1-005 antes da UI.
   - Rejeitado neste ciclo porque adiciona dependências e complexidade antes de
     validar a experiência analítica principal.

2. Manter Streamlit lendo Parquet direto.
   - Rejeitado como direção principal porque acopla a UI ao layout físico e
     ignora a camada FastAPI/DuckDB já existente.

3. Copiar o HTML do Formula Insights e adaptar dados depois.
   - Rejeitado porque geraria vitrine visual sem demonstrar engenharia de dados,
     contratos, serving e operação.

4. Criar frontend moderno separado imediatamente.
   - Reavaliado após parecer de Produto/Frontend: adotado para o MVP, desde que
     seja web próprio, leve, consumindo FastAPI e sem copiar Formula Insights.

5. Embutir MLflow/ChromaDB/SLA detalhado no F1-007.
   - Rejeitado neste ciclo porque as pendências de F1-005 são substantivas e
     devem ser tratadas em F1-008 separado para não bloquear o dashboard MVP.

## Abordagem Escolhida E Justificativa

Construir o Race Intelligence Dashboard em camadas:

1. consolidar contratos backend orientados à tela;
2. substituir o caminho crítico Streamlit por frontend web próprio consumindo
   FastAPI;
3. adicionar visualizações e estados vazios profissionais;
4. validar API, dados e smoke visual;
5. criar F1-008 separado para MLflow/ChromaDB/SLA detalhado se Roberto aprovar.

Essa abordagem mantém o projeto coerente com o objetivo de data product: a
experiência deve ser desenhada a partir do consumidor e sustentada por dados
confiáveis, acessíveis e compreensíveis.

## Impacto E Riscos

- Dados: risco de inconsistência se endpoints agregados assumirem colunas que nem
  todas as partições possuem. Mitigação: testes com tabelas mock e retornos vazios
  explícitos.
- Serving: risco alto no fallback DuckDB atual com tabela `dummy`, que pode
  transformar dataset ausente em erro de coluna. Mitigação: schemas vazios por
  tabela ou camada explícita de disponibilidade.
- Contratos: risco alto de UI depender de payload implícito. Mitigação:
  `response_model` Pydantic para endpoints novos e testes negativos.
- API: risco de expandir `analytics.py` em excesso. Mitigação: separar helpers ou
  roteadores se a superfície crescer.
- UI: risco de estética sobrepor legibilidade. Mitigação: priorizar layout denso,
  estados vazios e leitura de comparação.
- Operação: risco de dashboard quebrar quando Gold não foi materializada.
  Mitigação: fallback por seção e banners de disponibilidade.
- Portfolio: risco de expor documentação interna. Mitigação: atualizar apenas
  `docs/public-safe/` com resumo sanitizado.

## Dependências

- `src/web/database.py` com views DuckDB funcionais.
- `src/web/routers/analytics.py` como camada de serving.
- Dados Silver/Gold materializados localmente ou mocks nos testes.
- Frontend web próprio servido por/consumindo FastAPI. Streamlit permanece legado
  ou fallback exploratório até a nova UI responder localmente.

## Etapas De Implementação

### Fase 1: Contratos De Serving E Produto

- [x] Definir telas do MVP: overview, race strategy, driver duel, AI/predictions,
  pipeline health.
- [x] Definir contratos Pydantic ou equivalente para:
  - `GET /api/race_intelligence/session_summary?session_key=...`
  - `GET /api/race_intelligence/driver_options?session_key=...`
  - `GET /api/race_intelligence/driver_duel?session_key=...&driver_1=...&driver_2=...`
  - `GET /api/race_intelligence/strategy_timeline?session_key=...`
  - `GET /api/race_intelligence/pipeline_health?session_key=...`
  - `GET /api/race_intelligence/prediction_status?session_key=...`
- [x] Definir estados vazios com `available`, `reason`, `data` e `metadata` quando
  aplicável.
- [x] Definir schema físico esperado para as views Silver/Gold no serving DuckDB.
- Arquivos: `src/web/database.py`, `src/web/routers/race_intelligence.py`,
  `src/web/routers/analytics.py`, `tests/test_api.py`.
- Verificação: contrato JSON revisável no código e testes negativos planejados.
- Rollback: manter endpoints existentes sem alteração incompatível.

### Fase 2: Endpoints Agregados Para Dashboard

- [x] Criar endpoint de resumo de sessão com vencedor, total de pilotos, total de
  eventos, pit stops, stints, disponibilidade de Gold e última execução.
- [x] Criar endpoint de timeline normalizada unindo race control, pit stops e
  ultrapassagens em uma resposta consistente.
- [x] Criar endpoint de saúde por sessão usando `fact_pipeline_execution`.
- [x] Substituir fallback `dummy` por schemas vazios compatíveis ou disponibilidade
  explícita por dataset.
- [x] Diferenciar dataset ausente, sessão sem linhas e schema incompatível.
- [x] Manter endpoints existentes compatíveis.
- Arquivos: `src/web/routers/analytics.py`, possivelmente novo roteador
  `src/web/routers/race_intelligence.py`.
- Verificação: `pytest tests/test_api.py`.
- Rollback: remover roteador novo sem alterar endpoints existentes.

### Fase 3: Dashboard MVP

- [x] Implementar seleção de sessão e pilotos.
- [x] Exibir cards de sessão e saúde do pipeline.
- [x] Exibir gráficos de clima, stints/pit stops, timeline de eventos e duelo.
- [x] Exibir predições Gold com estado vazio quando não houver materialização.
- [x] Exibir chat apenas como recurso secundário TF-IDF local ou ocultá-lo até
  F1-008, sem prometer busca semântica densa.
- [x] Garantir navegação por teclado, foco visível, contraste legível, labels em
  controles e resumo textual para gráficos críticos.
- [x] Garantir responsividade desktop, laptop e mobile; em mobile, usar layout
  empilhado com cards essenciais.
- [x] Usar Formula Insights apenas como referência de categoria visual; não copiar
  HTML, CSS, assets, nomes, copy, pricing, rotas ou estrutura comercial.
- Arquivos: novo diretório de frontend, `src/web/main.py`, `src/dashboard/app.py`
  apenas como legado/fallback.
- Verificação: smoke local com API ligada e screenshots desktop/mobile.
- Rollback: manter rota/dashboard antigo acessível até validação.

### Fase 4: Testes E Qualidade De Dados Para Serving

- [x] Adicionar fixtures/mocks para endpoints agregados.
- [x] Validar estados vazios para ausência de Gold, ausência de pipeline execution
  e ausência de eventos.
- [x] Validar `schema_incompatible` sem mascarar erro como lista vazia.
- [x] Validar fallback de views DuckDB com schema vazio compatível.
- [x] Validar que SQL ad hoc permanece restrito a leitura.
- Arquivos: `tests/test_api.py`, `tests/test_data_integrity.py`, novo teste se
  necessário.
- Verificação:
  - `python3 -m py_compile src/web/routers/analytics.py src/web/database.py`
  - `env PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest tests/test_api.py tests/test_data_integrity.py -q`
- Rollback: remover endpoints novos e testes associados.

### Fase 5: Documentação Pública E Handoff Local

- [x] Atualizar `docs/public-safe/implementation-plans-summary.md` com resumo
  sanitizado do F1-007.
- [x] Atualizar `docs/public-safe/architecture-decisions.md` se houver decisão
  durável de UI/serving.
- [x] Atualizar handoff local após conclusão material.
- Arquivos: `docs/public-safe/*`, `docs/session-handoffs/`.
- Verificação: `rg` para termos internos sensíveis em `docs/public-safe/`.
- Rollback: reverter apenas as mudanças públicas do F1-007 se a estratégia mudar.

## Estratégia De Testes

- Unit/API: cobrir agregações e estados vazios com DuckDB in-memory.
- Data integrity: confirmar que Gold particionada e `fact_pipeline_execution`
  continuam legíveis.
- Contratos: validar payloads dos endpoints agregados com `response_model` ou
  contrato equivalente.
- Negativos: Gold ausente, pipeline execution ausente, sessão sem eventos,
  schema incompatível e dataset ausente.
- UI smoke: iniciar API/dashboard localmente e validar renderização mínima.
- Segurança: manter bloqueio de DDL/DML no endpoint SQL.

## Observabilidade

O MVP deve expor ao menos:

- última execução por sessão;
- status;
- duração;
- linhas Bronze/Silver;
- linhas em quarentena;
- taxa de quarentena;
- disponibilidade de Gold/predições.

Freshness detalhada por fonte e latência por partição ficam como extensão
posterior e devem ser tratadas em F1-008 se Roberto aprovar completar F1-005.
No F1-007, a saúde do pipeline é operacional básica por sessão, não SLA completo.

## Rollout E Rollback

- Rollout local em branch/worktree atual, sem deploy externo.
- Primeiro liberar endpoints novos mantendo compatibilidade.
- Depois conectar a UI ao backend.
- Rollback por remoção do roteador/tela nova, preservando pipeline e endpoints
  existentes.

## Critérios De Aceite

- Dashboard permite escolher sessão e pelo menos dois pilotos.
- Dashboard é frontend web próprio consumindo FastAPI; Streamlit não é a vitrine
  principal do MVP.
- Overview mostra sessão, vencedor, disponibilidade de dados e saúde do pipeline.
- Race strategy mostra stints/pit stops e eventos em ordem temporal.
- Driver duel mostra métricas comparativas e trajetória/telemetria quando houver
  dados.
- Predições Gold aparecem quando `gold_lap_predictions` está disponível e mostram
  estado vazio quando ausente.
- Endpoints agregados têm contrato explícito e retornam estados vazios
  diferenciados.
- O MVP não declara MLflow, ChromaDB, embeddings densos ou SLA detalhado como
  concluídos.
- Testes selecionados passam.
- Documentação pública é atualizada sem expor governança interna.

## Resultado Observado E Revisão

Implementado em 2026-06-16.

Arquivos alterados:

- `src/web/database.py`: fallback DuckDB agora cria tabelas vazias com schema
  compatível por dataset, removendo o fallback genérico `dummy`.
- `src/web/routers/race_intelligence.py`: novo roteador contract-first com
  `response_model` Pydantic para resumo de sessão, opções de pilotos, duelo,
  timeline, saúde do pipeline e disponibilidade de predições.
- `src/web/main.py`: registra o roteador Race Intelligence e serve a UI web em
  `/`.
- `src/web/static/race_intelligence/index.html`: shell HTML da experiência.
- `src/web/static/race_intelligence/styles.css`: layout responsivo, estados
  visuais, foco e painéis.
- `src/web/static/race_intelligence/app.js`: consumo da FastAPI, seleção de
  sessão/pilotos, gráficos Plotly e estados vazios.
- `tests/test_api.py`: testes de contrato dos endpoints Race Intelligence e smoke
  da página HTML.
- `docs/public-safe/implementation-plans-summary.md`: resumo público sanitizado.
- `docs/public-safe/architecture-decisions.md`: decisão pública sanitizada de
  serving/API-first.
- `docs/session-handoffs/2026-06-16_agent_governance_public_safe.md`: memória
  local da execução.

Comandos executados:

- `python3 -m py_compile src/web/database.py src/web/main.py src/web/routers/race_intelligence.py src/web/routers/analytics.py`
- `env PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest tests/test_api.py -q`
- `env PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest tests/test_api.py tests/test_data_integrity.py -q`
- `.venv/bin/black src/web/database.py src/web/main.py src/web/routers/race_intelligence.py tests/test_api.py`
- `.venv/bin/isort src/web/database.py src/web/main.py src/web/routers/race_intelligence.py tests/test_api.py`
- `.venv/bin/flake8 src/web/database.py src/web/main.py src/web/routers/race_intelligence.py tests/test_api.py --max-line-length=120 --extend-ignore=E203,W503,E501,W291,F841,F541`
- `curl` em `http://127.0.0.1:8002/`, `/api/sessions` e endpoints
  `race_intelligence`.
- Playwright headless em desktop `1440x1000` e mobile `390x844`.

Evidência de testes:

- API e integridade: `33 passed, 1 warning`.
- Lint direcionado: aprovado sem saída.
- Compilação Python: aprovada sem saída.
- Servidor local: `/`, `/api/sessions` e `/api/race_intelligence/pipeline_health`
  retornaram HTTP 200 na porta 8002.
- Playwright: desktop e mobile renderizaram `Race Intelligence`, 3 sessões, 4
  cards de resumo, 3 abas, dois pilotos comparáveis e 2 cards de duelo, sem erros
  JavaScript. Screenshots temporários:
  - `/tmp/openf1_race_intelligence_screens/desktop.png`
  - `/tmp/openf1_race_intelligence_screens/mobile.png`

Divergências em relação ao plano:

- O MVP ocultou o chat na UI inicial em vez de exibi-lo como seção secundária,
  preservando a decisão de não prometer busca semântica densa antes do F1-008.
- A sessão padrão local foi Australia porque `/api/sessions` ordena por ano e
  país; essa sessão ainda não possui vencedor, eventos de race control ou
  histórico de pipeline. A UI exibiu esses estados vazios sem erro.

Pendências remanescentes:

- Refinar seleção padrão de sessão para priorizar sessões com mais dados completos
  se a vitrine pública precisar abrir diretamente em Bahrain ou Monaco.
- Criar F1-008 se Roberto aprovar completar MLflow, ChromaDB, embeddings densos,
  SLA detalhado e freshness por fonte/partição.

## Perguntas Em Aberto

- Roberto prefere evoluir o Streamlit atual por velocidade ou criar uma UI web
  própria para maior valor visual de portfolio? Resolvido pela reavaliação
  multiagente: frontend web próprio é a direção recomendada.
- O MVP deve incluir chat analítico na primeira tela ou manter o chat como aba
  secundária?
- O dashboard será apenas local/portfolio neste ciclo ou deve preparar deploy?
- O F1-005 deve virar F1-008 separado para MLflow/ChromaDB após o dashboard?

## Reavaliação Multiagente

```yaml
orchestration:
  topology: HYBRID
  rationale: Pareceres independentes de Dados/API, Produto/Frontend e IA/MLOps,
    seguidos de integração pelo Lead Agent.
  stages:
    - order: 1
      capability: Engenharia de Dados e API Serving
      status: completed
      agent: Poincare
      scope:
        - docs/plans/PL-005-race-intelligence-dashboard.md
        - docs/plans/PL-004-execucao-planos-004-005.md
        - src/web/database.py
        - src/web/routers/analytics.py
        - src/ingestion/process.py
        - src/ingestion/storage.py
        - tests/test_api.py
        - tests/test_data_integrity.py
      conclusion: needs_revision_before_execution
    - order: 1
      capability: Produto/Frontend
      status: completed
      agent: Pauli
      scope:
        - docs/plans/PL-005-race-intelligence-dashboard.md
        - src/dashboard/app.py
        - README.md
        - docs/public-safe/implementation-plans-summary.md
        - Formula Insights/
      conclusion: frontend web proprio recomendado; Streamlit deve ser legado/fallback.
    - order: 1
      capability: IA/MLOps e Observabilidade
      status: completed
      agent: Planck
      scope:
        - docs/plans/PL-005-race-intelligence-dashboard.md
        - docs/plans/PL-003-ia-mlops-observabilidade.md
        - docs/plans/PL-004-execucao-planos-004-005.md
        - src/web/routers/analytics.py
        - src/ingestion/process.py
        - src/ingestion/assets.py
        - requirements.txt
        - tests/test_api.py
        - tests/test_data_integrity.py
      conclusion: F1-007 aceitavel como dashboard MVP; F1-005 restante deve virar F1-008.
```

### Síntese Do Lead Agent

- Decisão aceita: F1-007 continua como dashboard MVP, não como fechamento do
  F1-005.
- Decisão aceita: frontend web próprio consumindo FastAPI substitui Streamlit no
  caminho crítico.
- Decisão aceita: implementação deve começar por contratos de serving, estados
  vazios e schemas compatíveis no DuckDB.
- Decisão aceita: MLflow, ChromaDB, embeddings densos, SLA detalhado e freshness
  por fonte/partição devem ser tratados em F1-008 se aprovados.
- Bloqueio antes de execução: revisar `src/web/database.py` e endpoints novos
  para evitar fallback `dummy`, payload implícito e exceções mascaradas como
  ausência legítima de dados.

## Registro De Evidências

```yaml
literature_evidence:
  - claim_id: RID-001
    classification: SOURCED
    source_id: deciphering-data-architectures
    title: Deciphering Data Architectures
    lines: 6875-6905
    sha256: 2beb6920fe906c2a9aac124f89d25fb54d52dbf8e491e01c7172cc99e86468d4
    application: INFERRED - orientar o dashboard como data product consumível.
  - claim_id: RID-004
    classification: SOURCED
    source_id: designing-machine-learning-systems
    title: Designing Machine Learning Systems
    lines: 7008-7030
    sha256: 04bbe6aea8aeb48959e924f887b5b9bbf89661c2642ef876c1ef4ae025090e7e
    application: INFERRED - adiar IA mais complexa até validar experiência simples.
  - claim_id: RID-005
    classification: SOURCED
    source_id: observability-engineering
    title: Observability Engineering
    lines: 2542-2612
    sha256: c891daf1bd86fecea730b4f6d92c1bdbae3d3faefe3a2378691cae106953df0a
    application: INFERRED - expor saúde operacional por sintomas analíticos.
  - claim_id: OPS-001
    classification: SOURCED
    source_id: fundamentals-data-engineering
    title: Fundamentals of Data Engineering
    lines: 15749-15758
    sha256: 02f5198105a3ce549217c6f345ec7bc557f6e0f8de9989fcaa461f86315791fe
    application: INFERRED - versionar e operacionalizar código analítico, ML e orquestração.
project_evidence:
  - classification: VERIFIED
    source: docs/plans/PL-004-execucao-planos-004-005.md
    lines: 1-26
  - classification: VERIFIED
    source: docs/plans/README.md
    lines: 17-50
  - classification: VERIFIED
    source: src/web/routers/analytics.py
  - classification: VERIFIED
    source: src/web/database.py
  - classification: VERIFIED
    source: src/dashboard/app.py
```

### ◈ Processing Context

- ✦ **Lead Agent:** Codex (Engenheiro Chefe)
- ▫ **Supporting Agents:** Poincare (Engenharia de Dados/API), Pauli (Produto/Frontend), Planck (IA/MLOps e Observabilidade)
- ⌥ **Skills Used:** `project-session-bootstrap`, `data-engineering`, `write-implementation-plan`, `technical-literature-research`, `multi-agent-orchestration`
- ☄ **Knowledge Sources:** `docs/plans/PL-004-execucao-planos-004-005.md`; `docs/plans/README.md`; Deciphering Data Architectures linhas 6875-6905; Designing Machine Learning Systems linhas 7008-7030; Fundamentals of Data Engineering linhas 15749-15758; Observability Engineering linhas 2542-2612
- ☱ **Files Analyzed:** `docs/plans/PL-002-parametrizacao-on-demand.md`, `docs/plans/PL-003-ia-mlops-observabilidade.md`, `docs/plans/PL-004-execucao-planos-004-005.md`, `docs/plans/README.md`, `src/web/routers/analytics.py`, `src/web/database.py`, `src/dashboard/app.py`, `src/ingestion/process.py`, `src/ingestion/assets.py`, `src/ingestion/storage.py`, `tests/test_api.py`, `tests/test_data_integrity.py`
- ◬ **Decision Complexity:** HIGH
