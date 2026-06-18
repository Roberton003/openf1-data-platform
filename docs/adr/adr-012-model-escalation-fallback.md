# ADR-012: Model Escalation & Fallback Automático

## Status
Accepted

## Date
2026-06-18

## Context
O modelo primário `deepseek-v4-flash-opencode-zen` (Free) sofre rate limiting em
tarefas longas (T3+), manifestado como timeouts consecutivos de bash (exit -1),
comandos sem output, e execução trancada em subprocessos.

Solução anterior exigia que Roberto percebesse e pedisse troca manual — ineficiente
e frustrante.

## Decision
Implementar cadeia de fallback automático na governança do harness com gatilho
observável:

### Cadeia
1. `deepseek-v4-flash-opencode-zen` (Free) — padrão
2. `mimo-v2.5-opencode-go-medium` — fallback automático

### Gatilho
2+ timeouts consecutivos de bash (exit code -1 / exceeded) em operações
determinísticas.

### Ação
1. Emitir: "[Model Escalation] Rate limit detectado. Ativando fallback..."
2. Migrar para `mimo-v2.5-opencode-go-medium`
3. Se fallback também falhar (1+ timeout): handoff + parada

## Consequences
### Positive
- Execução continua sem intervenção do usuário
- Gatilho observável (exit code -1) — não depende de heurística frágil
- Fallback documentado em 4 pontos da governança

### Negative
- Modelo pago pode aumentar custo em execuções longas
- Transição de modelo não preserva contexto de sessão automaticamente
- Timeout pode ter causas não relacionadas a rate limiting (bug, rede)

## References
- `~/.opencode/opencode-core.md` seção 10
- `~/.config/opencode/skills/effort-budget-governor/SKILL.md`
- `~/.config/opencode/skills/task-router/SKILL.md`
- `AGENTS.md` (workspace)
