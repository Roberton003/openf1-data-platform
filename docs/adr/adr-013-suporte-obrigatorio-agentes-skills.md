# ADR-013: Suporte Obrigatório de Agentes e Skills

## Status
Accepted

## Date
2026-06-18

## Context
Atividades T1+ eram executadas sem documentar quais agents e skills foram
acionados. A regra anterior ("Disponibilidade de capacidade não significa
invocação") era permissiva — permitia pular suporte sem justificativa.

Isso causava:
- Falta de rastreabilidade: impossível saber quem executou o quê
- Qualidade inconsistente: agentes especializados disponíveis mas não usados
- Dificuldade de revisão: sem suporte documentado, revisão adversarial não tem
  base para avaliar cobertura

## Decision
Tornar suporte de agentes e skills **obrigatório** para toda atividade T1+:

### Regra
Toda atividade T1+ deve documentar:
- Pelo menos 1 agente acionado (ou `Rejected/Blocked` com motivo)
- Pelo menos 1 skill carregada (ou justificativa para ausência)

### Gatilho de Bloqueio
Se `agents` ou `skills` estiverem vazios para T1+, a execução é bloqueada até
que o suporte seja documentado.

### Fallback
Se agentes/skills não puderem ser invocados por limite operacional:
1. Registrar como `Rejected/Blocked` com motivo
2. Executar com Lead Agent + justificativa explícita
3. Incluir lacunas no handoff final

### Arquivos Modificados
- `~/.opencode/opencode-core.md` §3 (Task Router com Agents Mínimos)
- `~/.opencode/opencode-core.md` §4 (Budget Governor com campos obrigatórios)
- `AGENTS.md` (seção "Suporte Obrigatório")
- `~/.config/opencode/skills/task-router/SKILL.md` (saída YAML com agents/skills)
- `~/.config/opencode/skills/effort-budget-governor/SKILL.md` (campos obrigatórios)
- `~/.config/opencode/skills/executing-plans/SKILL.md` (Step 0 Document Support)

## Consequences
### Positive
- Rastreabilidade total: cada atividade tem who/what/how documentado
- Qualidade consistente: agents especializados são acionados quando disponíveis
- Revisão adversarial efetiva: base concreta para avaliar cobertura
- Compliance automático: script de verificação detecta falhas

### Negative
- Overhead inicial: documentar suporte antes de executar
- Possível resistência: tarefas simples podem parecer sobrecarregadas
- Mitigação: T0 não requer suporte; T1 requer apenas 1 skill

## References
- `~/.opencode/opencode-core.md` §3, §4
- `AGENTS.md` seção "Suporte Obrigatório"
- `scripts/verify_agent_support.py`
