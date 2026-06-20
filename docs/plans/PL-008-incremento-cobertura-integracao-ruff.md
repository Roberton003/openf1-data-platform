# Plano F1-019: Incremento de Cobertura, Testes de Integração e Migração Ruff

## 1. Contexto

156 testes, cobertura estimada ~50% (target: 60%). Três linters separados
(black + isort + flake8) geram 3 hooks pre-commit + 3 steps CI. Módulos
críticos sem teste: `assets.py` (1563 linhas, 0), `health.py` (0),
`analytics.py` (1149 linhas, 1 helper testado), `extract.py` (0).

Auditorias concluídas por 3 domain agents (data-engineer, test-engineer,
devops-release-engineer) em 18/06/2026.

## 2. Decisões

| Decisão | Motivo | Premissas | Alternativas Rejeitadas |
|---------|--------|-----------|------------------------|
| Ruff com regras conservadoras (E,W,F,I) na fase 1 | --fix não altera código funcional; adicionar UP/SIM gradualmente | ruff 0.15.27 compatível com black 24.4.2 output | UP+SIM desde o início (risco de quebra funcional) |
| Quick-win tests antes da migração ruff | Evita confundir diff do ruff com diff dos testes | Ordem não importa para o resultado final | Ruff primeiro (diff poluído) |
| Integration tests marcados `@pytest.mark.integration` | CI pode excluir com `-m "not integration"`; execução manual sob demanda | Marcador já registrado em pyproject.toml | Criar diretório separado tests/integration/ |
| 3 fases executáveis independentemente | Rollback parcial se uma fase falhar; cada fase commitável | Nenhuma dependência cruzada entre fases | Monolito (rollback total se qualquer fase quebrar) |

## 3. Escopo

### Fase 1 — Quick-Win Tests (5 targets)
- [ ] `tests/test_health.py` — liveness + readiness probes
- [ ] `tests/test_telemetry.py` — GET telemetry endpoint
- [ ] `tests/test_quarantine.py` — quarantine_invalid_rows
- [ ] `tests/test_analytics.py` — fetch_sessions + fetch_drivers
- [ ] `tests/test_schemas.py` — valid+invalid cases for all 5 Pydantic models

### Fase 2 — Integration Tests (3 targets)
- [ ] Expandir `test_cli_pipeline.py` — validar Gold + joblib após pipeline
- [ ] `tests/test_gold_assets.py` — fixture Silver + executar gold_f1_telemetry_analysis
- [ ] Adicionar variacão de compostos na fixture Bronze do pipeline

### Fase 3 — Ruff Migration
- [ ] `ruff.toml` criado (E,W,F,I + formatter)
- [ ] `.pre-commit-config.yaml` — 1 hook ruff + ruff-format (remove black/isort/flake8)
- [ ] `.github/workflows/ci.yml` — 1 step ruff check + 1 step ruff format
- [ ] `Makefile` — format/lint targets para ruff
- [ ] `ruff check src/ tests/ --fix` + `ruff format` aplicado
- [ ] pip uninstall black isort flake8

### Fora de Escopo
- Dagster asset tests (AssetsMaterialization mock — requer dagster test utilities)
- tests para `extract.py` (depende de API externa)
- tests para `race_intelligence.py` (muitas queries complexas)
- coverage de analytics.py > 20% (muito código, fase posterior)

## 4. Stack

- pytest + pytest-cov + TestClient (FastAPI)
- ruff 0.15.17 (já instalado)
- DuckDB (in-memory para fixtures de teste)

## 5. Critérios de Aceite

1. `ruff check src/ tests/` — zero violations
2. `ruff format src/ tests/ --check` — zero diff
3. Testes existentes continuam passando (coleta ≥ 156)
4. Cobertura ≥ 60% (via `pytest --cov=src --cov-fail-under=60`)
5. pre-commit passa com hook ruff (não black/isort/flake8)
6. CI (`make validate` local) — lint + test + security all green

## 6. Rollback

```bash
git revert HEAD --no-edit  # se commit único
# Ou por fase:
git checkout -- ruff.toml .pre-commit-config.yaml .github/workflows/ci.yml Makefile
pip install black==24.4.2 isort==5.13.2 flake8==7.1.0
```

## 7. Processing Context

```yaml
effort: T3
orchestration:
  topology: SEQUENTIAL
  rationale: quick tests first (baseline), then integration tests (safe order), then ruff (destructive)
  stages:
    - phase: 1
      capability: Lead Agent (test-engineer skill)
      scope: [tests/test_health.py, tests/test_telemetry.py, tests/test_quarantine.py, tests/test_analytics.py, tests/test_schemas.py]
    - phase: 2
      capability: Lead Agent (data-engineering skill)
      scope: [tests/test_cli_pipeline.py, tests/test_gold_assets.py]
    - phase: 3
      capability: Lead Agent (devops-release-engineer skill output)
      scope: [ruff.toml, .pre-commit-config.yaml, .github/workflows/ci.yml, Makefile]
```
