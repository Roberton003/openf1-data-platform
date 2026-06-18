# Plano F1-015: Fechamento de Pendências e Sanitização Final

## 1. Contexto

A auditoria de pendências (2026-06-18) identificou **68 itens pendentes** no OpenF1 Data Platform, distribuídos entre o plano F1-012 (97% concluído), worktree sujo com ~1900 linhas não commitadas, gaps de testes, documentação desatualizada e o plano F1-004 parcial.

Os agentes especialistas (data-engineer, test-engineer, security-reviewer) avaliaram cada dimensão e corrigiram premissas do plano original — incluindo a descoberta de que `pytest-asyncio` já está em versão compatível e que `test_data_integrity.py` está quebrado em CI por usar paths absolutos.

Este plano consolida todas as correções em um roadmap priorizado para fechamento definitivo.

## 2. Objetivo

Fechar todos os itens pendentes identificados, partindo do gargalo real (worktree sujo) até os gaps de documentação e governança, deixando o projeto em estado "committado, documentado e verificável".

## 3. Escopo

### Incluído
- Commit organizado do worktree (20 modificados + 13 não rastreados)
- Docker digest pinning + `.dockerignore`
- Tag `pre-f1-012` para rollback
- ADR-009 formalizando conclusão do F1-012 + ADR-008 no índice
- `test_data_integrity.py` migrado para `tmp_path`
- Testes de auth (401, 429, CORS)
- ML fixture sintética (substituir `pytest.skip`)
- Dagster RunConfig (F1-004)
- Schema Nullable Types (SESSION_RESULTS_SCHEMA)
- README + PROJECT_PROFILE + `implementation_plan.md` atualizados
- Handoff vazio preenchido ou deletado
- `pyproject.toml` com configuração de pytest

### Fora de Escopo
- F1-005 completo (ChromaDB, MLflow, sentence-transformers, SLA, freshness)
- Notificação real (Slack/Discord webhook)
- Dockerfile.dashboard
- Blue-green/canary deploy
- Trivy/Snyk scan
- Cache read-through (`lru_cache` + TTL)
- Bronze archive automação
- Melhorias de features novas

## 4. Decisões do Plano

| Decisão | Motivo | Premissas | Alternativas Rejeitadas | Evidência |
|---------|--------|-----------|------------------------|-----------|
| Remover task pytest-asyncio do plano | Versões já compatíveis (`pytest==8.1.1`, `pytest-asyncio==0.23.6`) | requirements.txt reflete ambiente real | Manter task como "verificação" | test-engineer report |
| `test_data_integrity.py` como Must Have | Usa `os.path.join(..., "../data")` — no-op em CI | Arquivo precisa de rewrite com `tmp_path` | Postergar (rejeitado: risco de CI falso-positivo) | test-engineer report |
| Auth tests condicionais ao bypass | `auth.py` linha 16: sem API_KEY, auth é ignorado | Bypass pode ser intencional para dev; precisa decisão documentada antes | Criar testes de 401/429 cegamente (rejeitado: testes verdes falsos) | security-reviewer report, adversarial-review |
| Schema Nullable Types: validar Gold readers | `pd.BooleanDtype()` retorna `pd.NA` (truthy), não `None` — `if row['finished']:` quebra | Consumidores Gold precisam ser mapeados antes da mudança | Migrar schema sem validar consumidores (rejeitado: risco de bug silencioso) | data-engineer report, adversarial-review |
| ADR-009 movido para pós-gate | "Resultados dos testes" precisa dos testes reais | Testes e implementação concluídos antes de documentar | Criar ADR-009 junto com Fase 5 (rejeitado: ficção) | adversarial-review |
| Rollback ampliado para dados/infra | Só `git checkout` não restaura DuckDB, volumes, imagens | Estado mutável precisa de rollback específico | Manter rollback só git (rejeitado: risco de dados corrompidos) | adversarial-review |
| Fase 1 dividida em 1a + 1b | 33 arquivos em 7 commits = 4-6h, não 1-2h | Senior dev, commits atômicos com validação entre cada um | Manter Fase 1 única (rejeitado: subestimação de risco) | adversarial-review |

## 5. Priorização (MoSCoW)

### Must Have (Bloqueadores)
1. Tag `pre-f1-012` + `.dockerignore`
2. Commit organizado do worktree (20 mod + 13 untracked em commits atômicos)
3. Docker digest pinning (`Dockerfile.api`)
4. `test_data_integrity.py` → `tmp_path` + fixture sintética
5. ADR-009 formalizando conclusão do F1-012
6. ADR-008 adicionado ao índice do README
7. `doc-check-do-alvo-handoff.md` — preencher ou deletar
8. README (contagem de testes, diagrama) + PROJECT_PROFILE (AGENTS.md) + `implementation_plan.md`

### Should Have (Qualidade)
9. Auth tests (401, 429, CORS) — 8 testes mínimos
10. ML fixture sintética (substituir `pytest.skip`)
11. Dagster RunConfig (RunConfig class em `assets.py`)
12. Schema Nullable Types (`SESSION_RESULTS_SCHEMA` bool → `pd.BooleanDtype()`)
13. `pyproject.toml` com `[tool.pytest.ini_options]`

### Could Have (Polimento)
14. Renomear ADR-008 para `adr-008-python-version-and-plan-consolidation.md`
15. `test_api.py` — refatorar `TestClient` module-scope para fixture

### Won't Have (Neste Momento)
- F1-005 completo (ChromaDB, MLflow, sentence-transformers, SLA, freshness)
- Notificação real (webhook)
- Dockerfile.dashboard
- Blue-green/canary deploy
- Trivy/Snyk scan
- Cache read-through
- Bronze archive automação
- CLI regex sanitization (silent fallback existe, baixo risco)
- ASOF JOIN via COPY TO (scaling risk apenas, sem volume atual)

## 6. Fases de Execução

### Fase 0: Baseline Seguro + Diagnóstico (10 min)
Tag `pre-f1-012` + `.dockerignore` + baseline commands.

**Tarefas:**
1. Executar baseline commands e anexar outputs: `git status --porcelain`, `git diff --stat`, `find . -name "Dockerfile*"`, `pytest --collect-only -q | wc -l`
2. Criar tag `git tag pre-f1-012` no commit atual (HEAD antes de qualquer mudança)
3. Criar `.dockerignore` na raiz
4. Verificar `Formula Insights/` e `codex_frontier_*` — decidir versionar ou `.gitignore`
5. Verificar se há secrets no worktree: `git diff -- .env .env.* 2>/dev/null || true`

**Critérios de Aceite:**
- [ ] `git tag -l pre-f1-012` retorna o tag
- [ ] `.dockerignore` existe e ignora `.env`, `.venv`, `__pycache__`, `.git`, `node_modules/`, `Formula\ Insights/`, `codex_frontier_*/`
- [ ] Baseline commands registrados
- [ ] Nenhum secret no worktree

**Agente Executor:** Lead Agent

### Fase 1a: Limpeza e Preparação (30 min)
Sanitizar worktree antes dos commits.

**Tarefas:**
1. Revisar `git diff` e `git status` completos — verificar se `.env` ou secrets estão diffados
2. Decidir sobre untracked: `Formula Insights/` → `.gitignore`, `codex_frontier_*` → `.gitignore`, `Dockerfile.api` → versionar, `src/orchestration/` → versionar, `src/web/auth.py` → versionar, `tests/conftest.py` → versionar
3. Atualizar `.gitignore` com decisões
4. Verificar auth bypass: ler `auth.py` linha 16 e documentar decisão (feature ou bug)
5. Agrupar arquivos modificados por tema para commits atômicos

**Critérios de Aceite:**
- [ ] `.gitignore` atualizado e committed
- [ ] Decisão de versionamento registrada
- [ ] Auth bypass documentado

**Agente Executor:** Lead Agent

### Fase 1b: Commits Atômicos (2-4h)
20 arquivos modificados em commits temáticos com validação entre cada um.

**Tarefas:**
1. Commits na ordem:
   - `feat: storage layer — atomic write + storage.py`
   - `feat: orquestração — módulo src/orchestration/ + Dagster definitions`
   - `feat: segurança — auth middleware, rate limiting, CORS, error messages`
   - `feat: race intelligence dashboard — frontend + router + endpoints`
   - `test: testes de error paths, conftest, compress_bronze`
   - `chore: CI/CD, Makefile, docker-compose, requirements.txt`
   - `docs: README, handoff scaffold, scripts`
2. Validar cada commit com `ruff check src/` e `pytest tests/ -q --tb=short` (apenas testes relevantes)

**Critérios de Aceite:**
- [ ] `git status --porcelain` retorna vazio
- [ ] Nenhum secrets ou `.env` no histórico
- [ ] Cada commit passa lint e testes relevantes

**Agente Executor:** Lead Agent

### Fase 2: Docker Hardening (15 min)
Digest pinning + verificação.

**Tarefas:**
1. Substituir `FROM python:3.12.10-slim` por `FROM python:3.12.10-slim@sha256:...` em `Dockerfile.api`
2. Obter o digest atual com `docker pull` ou consulta ao registry

**Critérios de Aceite:**
- [ ] `grep "@sha256" Dockerfile.api` retorna linha
- [ ] `docker build` reproduzível com o digest

**Agente Executor:** devops-release-engineer

### Fase 3: Testes (2-4h)
Correção dos gaps de teste identificados.

**Tarefas:**
1. Migrar `test_data_integrity.py` para `tmp_path` com dados sintéticos
2. Decidir auth bypass (Fase 1a já documentou): se feature, criar `tests/test_auth.py` com 8 testes (401 missing key, 401 invalid key, 200 valid key, 429 rate limit, 429 headers, 429 different endpoint, CORS preflight blocked, CORS preflight allowed); se bug, remover bypass e criar testes
3. Criar fixture sintética para ML em `tests/conftest.py` (com `random.seed()` para determinismo)
4. Refatorar `test_error_paths.py` para usar fixture em vez de `pytest.skip`
5. Criar `pyproject.toml` com `[tool.pytest.ini_options]` (`testpaths = ["tests"]`, `asyncio_mode = "auto"`, `markers`)

**Critérios de Aceite:**
- [ ] `pytest tests/ -v --tb=short -rs` verde
- [ ] `test_data_integrity.py` sem referências a `os.path.join(..., "../data")`
- [ ] Auth tests verdes (ou skipped com reason documentado se bypass confirmado)
- [ ] ML tests com fixture sintética, sem `pytest.skip`
- [ ] Testes isolados por `tmp_path`

**Agente Executor:** test-engineer

### Fase 4: Data Pipeline (2-3h)
Fechamento do F1-004 + schema fix + validação de Gold layer.

**Tarefas:**
1. Mapear consumidores Gold: `grep -r "finished\|dnf\|BooleanDtype\|SESSION_RESULTS" src/web/` — verificar se routers tratam `pd.NA`
2. Schema Nullable Types: `SESSION_RESULTS_SCHEMA` bool → `pd.BooleanDtype()`; verificar se há outros schemas com `bool`
3. Dagster RunConfig: criar `RunConfig` class em `assets.py` com `session_keys`, `focus_drivers`; manter fallback para `SESSIONS_TO_PROCESS`
4. Verificar compatibilidade do `definitions.py` com Launchpad

**Critérios de Aceite:**
- [ ] `ruff check src/ingestion/` passa
- [ ] Consumidores Gold validados para `pd.NA`
- [ ] Dagster dev carrega sem erro com `dagster dev -m src.orchestration.definitions`
- [ ] Launchpad UI mostra schema config

**Agente Executor:** data-engineer

### Fase 5: Documentação e Governança (1h)
README, profile, planos, índice ADR.

**Tarefas:**
1. Adicionar ADR-008 ao índice em `docs/adr/README.md`
2. Atualizar README.md: contagem real de testes, diagrama com Race Intelligence
3. Atualizar PROJECT_PROFILE.md: AGENTS.md existe, Python 3.12
4. Atualizar `implementation_plan.md` na raiz (apontar F1-015 como ativo ou deletar)
5. Preencher ou deletar `doc-check-do-alvo-handoff.md`

**Critérios de Aceite:**
- [ ] ADR index inclui ADR-008
- [ ] README reflete estado real do projeto
- [ ] PROJECT_PROFILE sem referências obsoletas

**Agente Executor:** documentation-curator

### Fase 6: Gate Final + ADR-009 + Handoff (1h)
Validação final, registro da conclusão e handoff.

**Tarefas:**
1. Executar `pytest tests/ -v --tb=short -rs` como gate final local
2. Executar `ruff check src/`
3. Executar `git status --porcelain` (deve estar limpo)
4. Criar ADR-009 com: contexto do F1-012, o que foi implementado em cada fase, resultados dos testes, pendências residuais, status final
5. Registrar handoff em `docs/session-handoffs/`

**Critérios de Aceite:**
- [ ] Gate de verificação local passa
- [ ] ADR-009 criado com resultados reais dos testes
- [ ] Handoff criado com next steps e riscos residuais

**Agente Executor:** Lead Agent

## 7. Matriz de Roteamento

| Fase | Executor | Revisor | Modelo Sugerido |
|------|----------|---------|-----------------|
| Fase 0 | devops-release-engineer | security-reviewer | DeepSeek V4 Flash |
| Fase 1 | Lead Agent | — | DeepSeek V4 Flash Free |
| Fase 2 | devops-release-engineer | — | DeepSeek V4 Flash |
| Fase 3 | test-engineer | code-quality | DeepSeek V4 Flash |
| Fase 4 | data-engineer | adversarial-review | DeepSeek V4 Flash |
| Fase 5 | documentation-curator | — | DeepSeek V4 Flash |
| Fase 6 | Lead Agent | completion-auditor | DeepSeek V4 Flash Free |

## 8. Riscos

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Commit worktree introduz conflito | Média | Alto | Revisar diff antes de cada commit, validar com pytest |
| Auth bypass é intencional e testes falham | Média | Médio | Documentar como skip com reason, não forçar mudança |
| Dagster RunConfig quebra Launchpad | Baixa | Médio | Manter fallback para SESSIONS_TO_PROCESS constante |
| Schema Nullable Types quebra leitores Gold | Baixa | Médio | Verificar se routers tratam `pd.NA` |
| README desatualiza novamente | Média | Baixo | Revisão trimestral |

## 9. Dependências

- **Fase 0:** Nenhuma
- **Fase 1a:** Fase 0 (tag + `.dockerignore` + baseline)
- **Fase 1b:** Fase 1a (limpeza concluída)
- **Fase 2:** Fase 1b (Dockerfile.api precisa estar committed)
- **Fase 3:** Fase 1b (código fonte precisa estar committed)
- **Fase 4:** Fase 1b (código fonte precisa estar committed)
- **Fase 5:** Fases 1-4 (documentar o que foi implementado)
- **Fase 6:** Fases 1-5 (gate final + ADR + handoff)

Fases 2-5 podem rodar em paralelo após Fase 1b, desde que toquem arquivos diferentes (verificar conflitos).

## 10. Rollout e Rollback

### Pré-requisitos
- Ambiente de desenvolvimento local funcionando
- `pytest tests/` verde no estado atual (ou skipping documentado)

### Execução
1. Fase 0 → tag pre-f1-012
2. Fase 1 → commits atômicos
3. Fases 2-5 → em paralelo onde possível
4. Fase 6 → handoff

### Rollback
```bash
# Código
git checkout pre-f1-012

# Dados e infra (se necessário)
docker compose down -v
rm -rf data/duckdb/*.duckdb data/duckdb/*.db-wal data/duckdb/*.db-shm 2>/dev/null || true
docker compose up --build -d
```

**Nota:** Rollback de código via `git checkout` é suficiente para a maioria dos cenários. O rollback de dados/infra só é necessário se Fase 4 (schema change) corromper dados — verificar antes de executar.

### Validação Final
```bash
pytest tests/ -v --tb=short -rs && echo "ALL TESTS PASSED"
ruff check src/ && echo "LINT PASSED"
git status --porcelain | wc -l  # deve ser 0
```

## 11. Critérios de Sucesso

### Técnicos
- [ ] `git status --porcelain` limpo
- [ ] `pytest tests/ -v --tb=short` 100% verde
- [ ] `ruff check src/` sem erros
- [ ] Dockerfile.api com digest pinning
- [ ] Tag `pre-f1-012` existente

### Documentação
- [ ] ADR-009 criado + ADR-008 no índice
- [ ] README com contagem real de testes e diagrama atualizado
- [ ] PROJECT_PROFILE sem referências obsoletas
- [ ] `implementation_plan.md` atualizado ou removido

### Governança
- [ ] Handoff final registrado
- [ ] Worktree limpo e versionado
- [ ] F1-004 com Dagster RunConfig implementado

## 12. Métricas de Progresso

| Fase | Tarefas | Estimativa |
|------|---------|------------|
| Fase 0 | 5 | 10 min |
| Fase 1a | 5 | 30 min |
| Fase 1b | 7 (commits) | 2-4h |
| Fase 2 | 2 | 15 min |
| Fase 3 | 5 | 2-4h |
| Fase 4 | 4 | 2-3h |
| Fase 5 | 5 | 1h |
| Fase 6 | 5 | 1h |
| **Total** | **38** | **~7-14h** |

## 13. Processamento Contextual

### ◈ Processing Context

- ✦ **Lead Agent:** OpenCode Chief Engineer
- ▫ **Supporting Agents Invoked:** data-engineer, test-engineer, security-reviewer
- ⌥ **Skills Used:** write-implementation-plan, multi-agent-orchestration, adversarial-review
- ☄ **Knowledge Sources:** Auditoria de pendências (68 itens), Planos F1-004, F1-012, ADR-008, session-handoffs, git status, relatórios dos 3 agentes especialistas
- ☱ **Files Analyzed:** docs/plans/, docs/adr/, docs/session-handoffs/, tests/, src/ingestion/, src/web/, Dockerfile.api, requirements.txt, pyproject.toml, README.md, PROJECT_PROFILE.md, .github/workflows/
- ◬ **Decision Complexity:** T3 (alta) — múltiplos arquivos, CI/CD, governança, sem alteração de schema ou dados persistentes
- 🤖 **Model Used:** DeepSeek V4 Flash Free
- 🔁 **Model Recommendation for Next Step:** DeepSeek V4 Flash para execução das fases; reavaliar modelo se alguma fase exigir decisão arquitetural
- 💰 **Budget Notes:** 3 agentes especialistas invocados em paralelo para avaliação de risco; execução planejada em 7 fases com validação incremental
- ✅ **Validations:** Relatórios independentes de data-engineer, test-engineer e security-reviewer; premissas do plano revisadas e corrigidas
- ⚠️ **Not Executed:** F1-005 (postergado por decisão do ADR-008), cache read-through, bronze archive, notificação real, Dockerfile.dashboard — fora de escopo

Este trabalho foi produzido com suporte de 3 subagentes especialistas (data-engineer, test-engineer, security-reviewer) em paralelo, seguindo topologia HYBRID conforme skill multi-agent-orchestration.
