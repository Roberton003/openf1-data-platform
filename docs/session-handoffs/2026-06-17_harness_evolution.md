# Handoff: 2026-06-17 — Evolução do Harness Global

## Resumo
Expansão do harness OpenCode em `~/.config/opencode/` com 8 novos skills portados do Claude, reorganização de agentes em subdiretórios, limpeza de artefatos órfãos (node_modules/), e validação de consistência.

## Progresso
- [x] Portar 8 skills: planning-checklist, expert-data-engineering, expert-python-modern, writing-plans, executing-plans, memory-protocol, auto-boot, skill-diagrams-as-code
- [x] Remover `node_modules/` (~62MB) + package.json/lock do harness
- [x] Reorganizar agents: `core/` (4), `domain/` (8), `phase/` (7)
- [x] Atualizar `opencode.jsonc` com `agents.paths` e `skills.paths` expandido
- [x] Atualizar plan F1-012: DRAFT → COMPLETED (97%)
- [x] Smoke test: 19 agents com frontmatter OK, 22 skills com SKILL.md OK

## Decisões
- **Agents organizados em subdiretórios:** `core/` (lead + harness), `domain/` (especialistas), `phase/` (fases do plano 001)
- **`default_agent`:** `core/lead-engineer` — path relativo aos `agents.paths`
- **Skills.paths:** agora inclui `~/.claude/skills` e `~/.agents/skills` como fallback
- **F1-012:** Marcado como COMPLETED com 30/31 tarefas (97%). Pendente: Docker digest pinning (tag → @sha256)

## Pendências
- **Docker digest pin:** `Dockerfile.api` usa `python:3.12.10-slim` — ideal seria `@sha256:...` (Fase 4, 1 tarefa)
- **Test environment:** `pytest-asyncio==1.3.0` conflita com `pytest==7.4.4` — `FixtureDef` import error
- **MCP claude-context-local:** `enabled: false`, depende de Milvus (não rodando)
- **OpenRouter token:** exposto em `~/.claude/settings.json` — Roberto deve rotacionar

## Próximos Passos (Roberto decide)
1. Focar em features do OpenF1 Data Platform (nova ingestão, endpoint, dashboard)
2. Consertar Docker digest pin + test env
3. Evoluir harness com mais skills ou agentes
4. Tentar ativar MCP claude-context-local

## Arquivos Relevantes
- `~/.config/opencode/opencode.jsonc` — config atualizada
- `~/.config/opencode/skills/` — 22 skills (14 originais + 8 novos)
- `~/.config/opencode/agents/{core,domain,phase}/` — 19 agents organizados
- `~/.config/opencode/MODEL_ROUTER.md` — tabela de roteamento
- `docs/plans/012_consolidacao_harness_openf1.md` — atualizado para COMPLETED
