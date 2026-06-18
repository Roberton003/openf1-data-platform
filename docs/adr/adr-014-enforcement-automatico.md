# ADR-014: Enforcement Automático de Suporte de Agentes

## Status
Accepted

## Date
2026-06-18

## Context
ADR-013 estabeleceu que toda atividade T1+ deve ter suporte documentado de agents
e skills. Porém, o Lead Agent executou F1-020/021/022 sem invocar agents reais —
apenas documentou no plano. O enforcement existente (verify_agent_support.py) só
verificava conteúdo de arquivos, não comportamento de execução.

Revisão pelo domain/documentation-curator revelou ambiguidades críticas:
- "HARD BLOCK" soava como jargão de programação (thread sync), não governance
- "Campos vazios" permitia listar agents sem invocação real
- Checklist de 5 itens tinha contradição entre ação e documentação

## Decision
Implementar enforcement em 3 camadas com linguagem corrigida:

### Camada 1 — Governance Gate na Constituição
- `opencode-core.md` §3: "GOVERNANCE GATE — NO EXCEPTIONS" (substitui "HARD BLOCK")
- "Campos vazios" → "Agents/skills não invocados (tool task / skill tool)"
- Checklist AGENTS.md: 5 itens → 3 itens de ação obrigatória
- `executing-plans/SKILL.md` Step 0: "Invoke at least 1 domain agent via task"

### Camada 2 — Pre-Commit Hook
- `.pre-commit-config.yaml`: hook local que roda `verify_agent_support.py`
- Bloqueia commits se regras de agents/skills não forem atendidas

### Camada 3 — Script de Verificação Expandido
- `scripts/verify_agent_support.py`: 27 checks (era 22)
- 25 checks de falha (bloqueiam commit) + 2 warnings (handoffs antigos)
- Verifica plans e handoffs recentes

## Consequences
### Positive
- Enforcement automático: hook impede commit sem suporte
- Linguagem inequívoca: "GOVERNANCE GATE", "não invocados", 3 itens de ação
- Verificação expansível: novos checks podem ser adicionados
- Agent documentation-curator validou e corrigiu ambiguidades

### Negative
- Overhead: pre-commit hook adiciona ~1s a cada commit
- Modelo Free pode limitar invocação de agents múltiplos em paralelo
- Mitigação: fallback para mimo-v2.5-opencode-go-medium documentado no ADR-012

### Lição Aprendida
A regra "agents obrigatórios" só funciona se executada com agents reais.
Este ADR foi criado usando agent documentation-curator (invocado via task),
que encontrou bugs de linguagem que o Lead Agent não viu sozinho.

## References
- `~/.opencode/opencode-core.md` §3, §4
- `AGENTS.md` Checklist Pré-Execução
- `scripts/verify_agent_support.py`
- `.pre-commit-config.yaml`
- ADR-012 (fallback de modelo)
- ADR-013 (suporte obrigatório)
