# ADR-008: Consolidação e Saneamento (F1-015)

## Status
**Accepted**

## Data
2026-06-18

## Contexto

Após 14 planos anteriores (F1-001 a F1-014), o repositório acumulava 68 pendências de saneamento: secrets não rastreados, testes frágeis (dependência de dados reais), `.gitignore` mal configurado, Docker sem digest pinning, schema booleano não-nullable, ausência de testes de auth e isolamento de fixtures.

O plano **F1-015** foi criado para fechar todas essas pendências em 6 fases, com validação multiagente (data-engineer, test-engineer, security-reviewer, adversarial-reviewer).

## Decisão

Executar e concluir o plano F1-015 em 6 fases, com os seguintes resultados:

| Fase | O que fez | Resultado |
|---|---|---|
| 0 | Tag `pre-f1-012`, `.dockerignore`, baseline 112 tests | 5 falhas esperadas (DB vazio) |
| 1a | `.gitignore` corrigido, secrets removidos | `docs/adr/`, `docs/plans/` versionados |
| 1b | 5 commits atômicos (lint, src, tests, CI/CD, docs) | Pre-commit (black, isort, flake8) limpo |
| 2 | Docker digest pinning no `Dockerfile.api` | Ambas stages com SHA256 |
| 3 | Testes refatorados: auth modular, tmp_path, fixture sintética | 112/112 passando, 0 falhas |
| 4 | Schema Nullable Types (`pd.BooleanDtype`), `IngestionConfig`, Gold readers | Booleans nullable, RunConfig disponível |
| 5 | Docs: README, PROJECT_PROFILE, ADR index atualizados | 112 testes, Python 3.12, AGENTS.md |

## Consequências

### Ganhos
- **112 testes verdes em 15s** — baseline de qualidade rastreável
- **Nenhum segredo no repositório** — `.gitignore` com `.env`, `*.key`, `credentials*`
- **Auth testável** — módulo lê env var por request, sem cache módulo-level
- **Testes isolados** — `tmp_path`, sem dependência de dados reais
- **Schema booleano nullable** — `dnf`/`dns`/`dsq` aceitam `None` sem crash
- **Dagster RunConfig** — `IngestionConfig` disponível para Launchpad
- **Docker determinístico** — digest SHA256 evita surpresas de tag móvel

### Restrições
- F1-005 (ChromaDB, MLflow, SLA endpoint, sentence-transformers) **postergado** — fora do escopo
- Schema Nullable Types aplicado apenas nos booleans de sessão; demais tipos usam string/int64 inalterados
- Auth middleware permanece bypassável (dev mode sem `OPENF1_API_KEY`) — intencional para desenvolvimento
- Pipeline de ingestão não executa em CI atual; testes de pipeline são unitários/mockados

## Relação Com Artefatos
- **Plano:** `docs/plans/015_fechamento_pendencias.md`
- **Código:** `src/ingestion/schemas.py`, `src/ingestion/assets.py`, `src/web/auth.py`
- **Testes:** `tests/test_auth.py`, `tests/test_data_integrity.py`, `tests/conftest.py`
- **Config:** `pyproject.toml`, `.dockerignore`
- **Docs:** `docs/PROJECT_PROFILE.md`, `docs/adr/README.md`
