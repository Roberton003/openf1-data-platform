# F1-014: Migração 100% Free + DeepSeek V4 Flash como Workhorse Econômico

**Status:** Concluído
**Data:** 2026-06-18
**Agente:** Roberto + explore agent (análise de custos)

---

## Objetivo

Migrar todos os 26 agentes do harness OpenCode para a distribuição ótima: FREE models para agentes especializados, DeepSeek V4 Flash PAID para agentes supervisionados, consumindo ~90% da cota mensal Go ($54 de $60) ao menor custo possível.

## Problema Original

- **Schema quebrado**: `opencode.jsonc` com 3 erros (`commands`, `agents`, `mcp.env`)
- **12 agentes sem `model:`** no frontmatter
- **Modelos caros**: Qwen3.7 Max ($0,01258/req) dominava 65% do custo ($9,87)
- **Cota subaproveitada**: 25% ($15,17) para 49.200 requests
- **Qwen3.7 Max prestes a estourar**: projetado para ultrapassar $60/mês

## Solução

| Componente | Antes | Depois |
|---|---|---|
| Modelos | 5 (todos PAID, mix ineficiente) | 7 FREE + PAID Flash |
| Custo/mês | $15,17 (25% cota) | ~$5-54 (variável conforme volume) |
| Agentes com `model:` | 14 de 26 | **26 de 26** |
| Workhorse | DeepSeek V4 Flash (PAID, implícito) | Flash PAID ($0,000379/req) + FREE Flash |
| Comandos | 7 arquivos em `commands/` | Inline em `opencode.jsonc` |
| Schema | 3 erros | **Válido** |

## O que foi feito

### Fase 1 — Correção de Schema (3 erros)

| Erro | Linha | Antes | Depois |
|---|---|---|---|
| `commands` → `command` | L6-L9 | `"commands": {"paths": [...]}` | `"command": { "rag-plan": {...}, ... }` |
| `agents` removido | L38-L44 | `"agents": {"paths": [...]}` | Removido (auto-descoberta) |
| `mcp.env` → `environment` | L95 | `"env": { ... }` | `"environment": { ... }` |
| `share` | L11 | `false` (boolean) | `"disabled"` (string enum) |
| `snapshot` | L12-L14 | `{ "strategy": "plan" }` | `true` (boolean) |

### Fase 2 — Distribuição de Modelos

#### PAID Workhorse (consomem cota Go): `opencode-go/deepseek-v4-flash`

| Agente | Tipo | Motivo |
|---|---|---|
| economy-plan | Core | Supervisão Roberto, alto volume |
| economy-build | Core | Supervisão Roberto, alto volume |
| completion-auditor | Domain | Supervisão Roberto |
| adr-decision-recorder | Domain | Supervisão Roberto |
| cost-budget-governor | Domain | Supervisão Roberto |
| documentation-curator | Domain | Supervisão Roberto |
| rag-context-curator | Domain | Supervisão Roberto |

#### FREE 384K: `opencode/deepseek-v4-flash-free`

| Agente | Tipo |
|---|---|
| lead-engineer | Core (primary, 384K contexto) |
| harness-operator | Core (execução) |
| data-engineer | Domain (pipelines, contexto grande) |
| frontier-orchestrator | Core (orquestração) |
| phase-1, phase-2, phase-3-port, phase-5, phase-7 | Phase (execução de fases) |

#### FREE 131K: `opencode/mimo-v2.5-free`

| Agente | Tipo |
|---|---|
| harness-architect | Core (arquitetura) |
| harness-skeptic | Core (debate adversarial) |
| verification-engineer | Domain (verificação) |
| decision-memory-keeper | Domain (memória) |
| test-engineer | Domain (testes) |
| security-reviewer | Domain (segurança) |
| devops-release-engineer | Domain (devops) |
| phase-3-skills-create | Phase (criação de skills) |

#### FREE 128K: `opencode/nemotron-3-ultra-free`

| Agente | Tipo |
|---|---|
| adversarial-reviewer | Domain (revisão adversarial gratuita) |

### Fase 3 — Comandos Inline

7 comandos migrados de `commands/*.md` para `opencode.jsonc` `command.*`. Diretório `commands/` removido.

### Fase 4 — OPENCODE.md §24

Seção adicionada: rotação automática, fallbacks, estratégia de cota 90%, comandos inline.

### Fase 5 — MODEL_ROUTER.md

Tabelas atualizadas com:
- Custo por request ($/req)
- FREE vs PAID tiers
- Todos os 26 agentes com modelo atual
- Fallbacks reescritos (FREE → FREE → FREE)

## Validação

- ✅ `opencode --version` → 1.17.7 (sem ConfigInvalidError)
- ✅ `opencode models` → 58 modelos listados
- ✅ Todos os 26 agentes com `model:` no frontmatter
- ✅ Backups criados (`.bak-f1-014`)

## Impacto Financeiro

| Métrica | Antes | Depois |
|---|---|---|
| Cota mensal | 25% ($15,17) | Variável conforme volume |
| Custo/request médio | $0,000308 | $0,000379 (Flash PAID) ou $0 (FREE) |
| Modelo mais caro | Qwen3.7 Max ($0,01258/req) | Não usado em agentes padrão |
| Requests possíveis/$60 | ~196K (mix antigo) | 158K (Flash PAID) ou ilimitado (FREE) |
| Agentes sem modelo | 12 | **0** |

## Handoff

Próximos passos sugeridos:
1. Monitorar consumo real por 1 semana
2. Ajustar proporção FREE/PAID conforme volume observado
3. Se necessário, adicionar mais agentes PAID para consumir cota
