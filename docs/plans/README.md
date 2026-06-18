# Indice de Planos

Este diretorio e o registro operacional dos planos formais do projeto
OpenF1 Data Platform. Ele existe para permitir auditoria, analise de decisao,
execucao incremental e rastreabilidade entre plano, ADR, codigo, testes e
evidencias.

## Funcao

- Registrar planos aprovados antes de implementacoes substantivas.
- Preservar o historico quando um plano for substituido, revisado ou executado.
- Separar intencao arquitetural de execucao real: o plano diz o que deveria ser
  feito; planos de execucao e testes dizem o que foi efetivamente aplicado.
- Apoiar revisoes por recrutadores, tech leads e auditorias tecnicas, mostrando
  criterio de engenharia, trade-offs, riscos e validacoes.

## Convencao

- `NNN_slug_descritivo.md`: plano formal numerado.
- Planos que substituem outro plano devem criar novo arquivo e marcar o anterior
  como `Superseded`, sem apagar historico.
- Planos de execucao devem registrar arquivos alterados, verificacoes realizadas,
  pendencias e diferencas entre plano aprovado e implementacao real.
- Decisoes arquiteturais duraveis devem ser refletidas em `docs/adr/`.
- Mudancas materiais no perfil do projeto devem ser refletidas em
  `docs/PROJECT_PROFILE.md`.

## Indice Atual

| Plano | Status | Funcao | Observacao |
|---|---|---|---|
| [F1-003](003_fct_f1_telemetry_analysis.md) | **Completed** | Pipeline Gold `fct_f1_telemetry_analysis` | Tabela Gold implementada em `assets.py`, `database.py`, `analytics.py` e testes. |
| [F1-004](004_parametrizacao_on_demand.md) | **Parcialmente concluído** | Parametrizacao de ingestao e processamento sob demanda | `FOCUS_DRIVERS` via env var implementado. Dagster Run Configuration pendente. |
| [F1-005](005_ia_mlops_observabilidade.md) | **Superseded** | IA, MLOps e observabilidade | Substituído por F1-016. ChromaDB, MLflow e sentence-transformers postergados desde ADR-008. |
| [F1-006](006_execucao_planos_004_005.md) | **Completed** | Registro de execucao dos planos F1-004 e F1-005 | Mudanças listadas aplicadas e verificadas. |
| [F1-007](007_race_intelligence_dashboard.md) | **Completed** | Race Intelligence Dashboard | Frontend web proprio consumindo FastAPI, endpoints agregados contract-first e fallback DuckDB com schema compativel. |
| [F1-008](008_codex_frontier_adocao_parcial.md) | **Completed** | Adocao parcial do pacote Codex Frontier | Adoacao seletiva de conceitos de harness; rejeita instalacao completa e global por sobreposicao com a governanca atual. |
| [F1-009](009_handoff_make_target.md) | **Completed** | Entrada padrao para handoff via Makefile | Adiciona `make handoff` como entrada ergonomica para o scaffold canônico de memoria operacional. |
| [F1-012](012_consolidacao_harness_openf1.md) | **Superseded** | Consolidação e saneamento do OpenF1 | Substituído por F1-015. Pendências migradas para plano de fechamento. |
| [F1-015](015_fechamento_pendencias.md) | **Completed** | Fechamento de pendências e sanitização final | 68 itens fechados: testes (112 verdes), Docker, auth, schemas, docs. ADR-009. |
| [F1-016](016_ia_mlops_e_observabilidade.md) | **Completed** | IA, MLOps e observabilidade (substitui F1-005) | ChromaDB RAG, MLflow Model Registry, SLA endpoint. 138 testes. |
| [F1-017](017_harness_openf1_unificacao_governanca.md) | **Active** | Unificação da governança do harness OpenF1 | Migrar toda governança de ~/.claude/ e ~/.agents/ para ~/.opencode/. 8 fases com skills + agentes. |

## Regras Para Novos Planos

Todo plano formal deve registrar:

1. contexto e objetivo;
2. escopo e fora de escopo;
3. decisoes tomadas e alternativas rejeitadas;
4. riscos, premissas e dependencias;
5. impacto em dados, schema, API, operacao e testes;
6. rollout, rollback e criterios de aceite;
7. evidencias usadas e lacunas conhecidas;
8. `Processing Context`, incluindo skills e subagentes realmente invocados.

Quando um plano for entregue sem subagentes invocados, registrar explicitamente
essa condicao conforme `AGENTS.md`.
