# Plano F1-016: IA, MLOps e Observabilidade

## 1. Contexto

O F1-005 (original) foi **Postergado** no ADR-008 (2026-06-17) após constatar que ChromaDB, MLflow e sentence-transformers não estavam implementados. Desde então:

- F1-015 concluiu saneamento: 112 testes, Docker digest, auth modular, Schema Nullable Types
- O RAG continua usando **TF-IDF esparso** (`sklearn.feature_extraction.text.TfidfVectorizer`) — fit_transform por request, semântica nula para sinônimos
- O ML usa **joblib dump/load** — sem versionamento, métricas, staging ou fallback
- A observabilidade tem **métricas hardcoded em zero** — sem endpoint SLA, sem freshness tracking

Este plano **substitui** o F1-005 original (que permanece como referência histórica em `docs/plans/PL-003-ia-mlops-observabilidade.md`).

---

## 2. Decisões do Plano

| Decisão | Motivo | Premissas | Alternativas Rejeitadas | Evidência |
|---------|--------|-----------|------------------------|-----------|
| ChromaDB em vez de DuckDB VSS | ChromaDB é especializado em RAG com HNSW + embedding functions integrados; DuckDB VSS exige extensão experimental | ChromaDB 0.5+ roda local sem servidor | DuckDB VSS (extensão `vss` — experimental, sem ecossistema de embedding); FAISS puro (exige gerenciamento manual de índice + metadados) | data-engineer assessment; `analytics.py:919-924` |
| MLflow com ModelLoader singleton | MLflow fornece registry, staging (Staging→Production), rollback em 30s, tracking de métricas | MLflow 2.15+ roda com backend SQLite local, zero custo operacional | Optuna/Hyperopt (só hyperparameter tuning, sem registry); DVC (versionamento de dados, não de modelos) | data-engineer assessment; `assets.py:936-941` |
| SLA endpoint dedicado | Isola responsabilidade, schema versionado, testes independentes | A rota atual `/api/pipeline_execution` existe mas não expõe métricas de SLA | Estender rota existente (acoplamento, quebra de contrato) | `analytics.py:762-806`; `database.py:88-100` |
| sentence-transformers all-MiniLM-L6-v2 | Melhor custo-benefício: 384d embeddings, 80MB RAM, CPU-only, recall ~92% | Modelo já está disponível no HuggingFace Hub (download único de ~80MB) | BERT-large (lento em CPU, ~400MB); TF-IDF (mantido como fallback) | data-engineer assessment |
| lazy indexing no endpoint `/analytics/chat` | Evita dependência de pipeline para usar RAG — se ChromaDB vazio, indexa on-the-fly | A coleção ChromaDB é identificável por session_key | Indexação síncrona obrigatória no pipeline (bloqueia RAG até pipeline executar) | `analytics.py:885-912` (função já lê DuckDB se vazio) |
| MLflow tracking com fallback joblib | Resiliência: pipeline não quebra se servidor MLflow estiver offline | `models/lap_regressor.joblib` continua sendo escrito a cada treino | Só MLflow (pipeline quebra sem servidor); só joblib (sem versionamento) | `assets.py:940-941` |

---

## 3. Escopo

### Incluído

| Track | Componentes | Esforço estimado |
|-------|-------------|------------------|
| A — ChromaDB RAG | `vector_store.py`, `RACE_CONTROL_SCHEMA`, lazy indexing, substituição TF-IDF, testes | 6-8h |
| B — MLflow Registry | MLflow tracking + registry, ModelLoader singleton, fallback joblib, testes | 8-10h |
| C — SLA Endpoint | Schema estendido, métricas reais, rota `/api/pipeline_execution/sla`, testes | 4-6h |
| D — Testes transversais | 6 novos arquivos de teste, fixtures, regression gate | 4-6h |
| E — Documentação | ADR-010, handoff, atualização PROJECT_PROFILE | 2h |

### Fora de Escopo

- Notificação real (Slack/Discord webhook)
- Dashboard de SLA (frontend)
- Blue-green/canary deploy de modelos
- Bronze archive automation
- Cache read-through (`lru_cache` + TTL)
- DuckDB VSS como alternativa

---

## 4. Stack e Dependências

### Atual (antes)
```
sklearn.feature_extraction.text.TfidfVectorizer  # RAG esparso
sklearn.metrics.pairwise.cosine_similarity         # RAG esparso
joblib                                              # ML serialization
```

### Futuro (depois)
```
chromadb>=0.5.0                                     # Vector store
sentence-transformers>=2.7.0                        # Embeddings (~800MB com torch)
mlflow>=2.15.0                                      # Model registry (+ Flask, SQLAlchemy, Alembic)
sklearn.feature_extraction.text → REMOVIDO          # Substituído por ChromaDB
sklearn.metrics.pairwise.cosine_similarity → REMOVIDO
```

**Impacto em imagem Docker**: ~1.2GB adicionais (principalmente torch). Usar `--no-cache-dir`.

---

## 5. Arquitetura de Dados

```
Bronze/(raw JSON)
  └─ Silver/fact_race_control/session_key=*/*.parquet
       ├─ [NOVO] vector_store.index_race_control_messages(session_key, df)
       │    └─ ChromaDB collection "race_control" [HNSW index + embedding 384d]
       └─ [NOVO] Lazy Indexing (se ChromaDB vazio, indexa on-the-fly no endpoint)

Silver/fact_car_telemetry/ + dim_stints/
  └─ Gold/features_lap_data/
       ├─ [MODIFICADO] gold_lap_time_prediction_model
       │    ├─ MLflow run com metrics (MSE, MAE, R²)
       │    ├─ mlflow.sklearn.log_model + register_model → stage "Production"
       │    └─ Fallback: models/lap_regressor.joblib
       └─ [MODIFICADO] gold_lap_predictions
            └─ ModelLoader().load() (MLflow → joblib fallback)

Silver/fact_pipeline_execution/
  ├─ [MODIFICADO] schema extendido: data_freshness_minutes, records_rejected, sla_*
  └─ [NOVO] GET /api/pipeline_execution/sla
```

---

## 6. Fases de Implementação

### Fase 0 — Fundação (4-6h)
**Sem mudança de comportamento. Apenas estrutura e testes.**

1. Adicionar `chromadb`, `sentence-transformers`, `mlflow` ao `requirements.txt`
2. Adicionar fixtures ao `tests/conftest.py`: `synthetic_random_forest`, `mock_mlflow`, `chroma_client`, `populated_race_control_collection`, `mock_db_with_sla_columns`
3. Criar `tests/test_regression_gate.py` — trava os 112 testes atuais
4. Criar `tests/test_smoke_imports.py` — import safety net
5. Executar regression gate

### Fase 1 — Track C: SLA Endpoint (4-6h)
**Mais simples, sem dependências externas.**

1. Estender `database.py:fact_pipeline_execution` com colunas:
   - `records_rejected INTEGER`
   - `data_freshness_minutes DOUBLE`
   - `sla_runtime_status VARCHAR`
   - `sla_quality_status VARCHAR`
   - `sla_freshness_status VARCHAR`
2. Atualizar `EMPTY_TABLE_SCHEMAS` em `database.py`
3. Modificar `assets.py:631-656`: popular `data_freshness_minutes` e `records_rejected` reais
4. Criar `src/web/routers/sla.py` com GET `/api/pipeline_execution/sla`
5. Registrar rota em `main.py`
6. Criar `tests/test_sla_endpoint.py`
7. Regression gate

### Fase 2 — Track A: ChromaDB RAG (6-8h)
**Maior ganho de qualidade. Substitui TF-IDF.**

1. Criar `src/ingestion/vector_store.py`:
   - `get_chroma_client()` — `chromadb.PersistentClient(path=DATA_DIR/chromadb)`
   - `get_embedding_fn()` — `SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")`
   - `index_race_control_messages(session_key, df_rc)` — delete + add (idempotente)
   - `query_race_control(session_key, question, n_results=5)` — query HNSW
2. Adicionar `RACE_CONTROL_SCHEMA` em `schemas.py`
3. Modificar `assets.py`: chamar `index_race_control_messages()` no asset silver race control
4. Modificar `process.py` (CLI): idem
5. Substituir `analytics.py:919-929` (TF-IDF) por ChromaDB query
   - Remover imports: `TfidfVectorizer`, `cosine_similarity`
   - Adicionar lazy indexing: se ChromaDB vazio para session_key, indexar on-the-fly
6. Criar `tests/test_vector_store.py`
7. Criar `tests/test_analytics_rag.py`
8. Regression gate

### Fase 3 — Track B: MLflow Model Registry (8-10h)
**Governança de modelos.**

1. Criar `src/web/model_loader.py`:
   - Classe `ModelLoader` com construtor injetável: `ModelLoader(mlflow_uri, joblib_path)`
   - Singleton via factory function `get_model_loader()`
   - `load()`: tenta MLflow (`models:/lap_regressor/Production`), fallback joblib
   - Cache com TTL 300s, thread-safe via `threading.Lock`
2. Modificar `assets.py:gold_lap_time_prediction_model`:
   - `mlflow.start_run()`, `mlflow.log_params()`, `mlflow.log_metrics()` (MSE, MAE, R²)
   - `mlflow.sklearn.log_model()`, `mlflow.register_model()`
   - `client.transition_model_version_stage()` → "Production"
   - Manter joblib.dump como fallback
3. Modificar `assets.py:gold_lap_predictions`:
   - Substituir `joblib.load()` por `ModelLoader().load()`
4. Instalar e configurar script de inicialização do MLflow (Make target)
5. Criar `tests/test_model_loader.py`
6. Criar `tests/test_mlflow_tracking.py`
7. Regression gate

### Fase 4 — Verificação Final (2h)
1. Suite completa: `pytest tests/ -v --tb=short --cov=src --cov-fail-under=60`
2. Lint: `ruff check src/ tests/`
3. Confirmar zero imports sklearn em `analytics.py`
4. ADR-010
5. Handoff final
6. Atualizar `docs/plans/README.md` — marcar F1-005 como Superseded, F1-016 como Active

---

## 7. Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|--------------|---------|-----------|
| sentence-transformers + torch ~1.2GB em CI/CD | Média | CI lento, imagem Docker grande | Usar `--no-cache-dir`, considerar cache de camada Docker |
| MLflow server não disponível em produção | Alta | Pipeline quebra sem fallback | ModelLoader com fallback joblib OBRIGATÓRIO; servidor MLflow é opcional |
| ChromaDB race condition (2 pipelines mesma session_key) | Baixa | Dados duplicados ou perda de índice | Serializar indexação por session_key no asset Dagster |
| ModelLoader cache stale (300s) | Média | Predições usam modelo antigo por até 5min | TTL configurável via env var; recarregar se detectar drift |
| Testes de embedding baixam modelo (~80MB) | Alta | Primeira execução lenta | Usar fixture `pytest.mark.slow` para testes de embedding; pular em CI |
| TF-IDF removido mas referenciado em outro lugar | Baixa | ImportError | `grep -r "TfidfVectorizer\|cosine_similarity" src/` é gate obrigatório |

---

## 8. Rollback

| Componente | Procedimento |
|------------|-------------|
| ChromaDB | Deletar `data/chromadb/` e restaurar TF-IDF via git revert |
| MLflow | Manter joblib fallback sempre funcional; `git revert` do assets.py |
| SLA endpoint | Remover rota e colunas (git revert do schema + router) |
| Dependências | `pip uninstall chromadb sentence-transformers mlflow` |
| Geral | `git revert` do commit do plano + `pytest tests/` para confirmar |

---

## 9. Critérios de Aceite

- [ ] 112+ testes originais passando (regression gate)
- [ ] 30-40 novos testes passando em 6 novos arquivos
- [ ] Cobertura >= 60%
- [ ] `ruff check src/ tests/` — 0 erros
- [ ] 0 imports sklearn em `analytics.py`
- [ ] `GET /api/pipeline_execution/sla` retorna 200 com dados SLA
- [ ] ChromaDB query retorna resultados semânticos para sinônimos
- [ ] ModelLoader carrega modelo com fallback sem crash
- [ ] ADR-010 registrado
- [ ] Handoff registrado

---

## 10. Mapeamento de Testes

| Teste | Fase | Arquivo | Nível |
|-------|------|---------|-------|
| Regression gate | 0 | `test_regression_gate.py` | Regressão |
| Import smoke | 0 | `test_smoke_imports.py` | Smoke |
| SLA endpoint | 1 | `test_sla_endpoint.py` | Integração |
| ChromaDB unit | 2 | `test_vector_store.py` | Unitário |
| RAG integration | 2 | `test_analytics_rag.py` | Integração |
| ModelLoader | 3 | `test_model_loader.py` | Unitário |
| MLflow tracking | 3 | `test_mlflow_tracking.py` | Integração |

---

## 11. Agentes e Skills

Este plano foi produzido sob a **skill `write-implementation-plan`** com **topologia HYBRID** multiagente:

### Pareceres Independentes (Fase de Assessment)

| Especialista | Domínio | Produziu | Status |
|-------------|---------|----------|--------|
| `domain/data-engineer` | Engenharia de dados | Assessment completo: arquitetura, data flow, schema impact, idempotency, dependências, ordem de implementação | Completou |
| `domain/adversarial-reviewer` | Revisão adversarial | Parecer parcial: confirmou TF-IDF O(n*m), exception silenciosa, zeros hardcoded, schema pipeline execution | Steps limitados — complementado por análise do Lead Agent |
| `domain/test-engineer` | Testes | Estratégia completa: 6 arquivos de teste, mocking, fixtures, edge cases, regression gate, testability concerns | Completou |

### Skills Carregadas

- `write-implementation-plan` — criação do plano formal
- `data-engineering` — avaliação de pipeline, schema e data flow
- `multi-agent-orchestration` — definição de topologia HYBRID, coordenação entre especialistas
- `adversarial-review` — revisão crítica de premissas e riscos
- `expert-python-modern` — análise de código Python existente (não invocada como subagente, mas presente como skill referenciada)

### Nota de Governança

Para a **Fase A (reanálise do F1-015)**, a ser executada após este plano, serão invocados:
- `domain/security-reviewer` — auditoria de secrets, auth, CORS
- `domain/devops-release-engineer` — Docker digest, .dockerignore, CI/CD hardening
- `domain/documentation-curator` — docs, ADR, handoff
- `domain/adr-decision-recorder` — ADR-008 já registrado, porém com necessidade de reauditoria

---

## 12. Verificação

```bash
# Regression gate
.venv/bin/python3 -m pytest tests/ -v --tb=short -rs

# Full suite after implementation
.venv/bin/python3 -m pytest tests/ -v --cov=src --cov-report=term-missing --cov-fail-under=60

# Lint
ruff check src/ tests/

# Confirm TF-IDF removal
grep -n "TfidfVectorizer\|cosine_similarity" src/web/routers/analytics.py || echo "CLEAN"
```

---

### ◈ Processing Context

- **Lead Agent**: OpenCode (Chief Engineer) com skills `write-implementation-plan`, `multi-agent-orchestration`, `data-engineering`, `adversarial-review`
- **Supporting Agents**: `domain/data-engineer`, `domain/adversarial-reviewer` (parcial), `domain/test-engineer`
- **Commands/Subagents Used**: `task(domain/data-engineer)`, `task(domain/adversarial-reviewer)`, `task(domain/test-engineer)`, `skill(write-implementation-plan)`, `skill(data-engineering)`, `skill(multi-agent-orchestration)`, `skill(adversarial-review)`
- **Knowledge Sources**: `docs/plans/PL-003-ia-mlops-observabilidade.md`, `docs/adr/ADR-007-python-version-plan-consolidation.md`, `docs/adr/ADR-008-f1-015-consolidacao-saneamento.md`, `src/web/routers/analytics.py:885-939`, `src/web/routers/analytics.py:762-806`, `src/ingestion/assets.py:930-983`, `src/ingestion/assets.py:631-656`, `src/web/database.py:88-100`, `tests/conftest.py`, `README.md`
- **Files Analyzed**: 9 arquivos fonte, 4 arquivos de teste, 3 planos anteriores, 2 ADRs
- **Task Level**: T3 (multi-componente, cross-domain: RAG + ML + SLA)
- **Validations**: Todos os pareceres verificados contra código real (linhas específicas); adversarial review complementado pelo Lead Agent onde steps limitaram o subagente
- **Not Executed**: Nenhuma mudança de código — apenas plano formal
