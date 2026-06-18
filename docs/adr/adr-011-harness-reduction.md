# ADR-011: Redução do Harness OpenCode

## Status
Accepted

## Contexto
O harness OpenCode para o OpenF1 Data Platform foi unificado (F1-017) com 41 skills, 35 agents e 13 commands — totalizando 89 artefatos de governança para um projeto solo. Uma auditoria multi-agente (segurança, data engineering, devops, documentação, testes) concluiu que o harness estava superdimensionado.

Problemas identificados:
- Skills redundantes (ex: `data-engineering` vs `expert-data-engineering`, `rag-first-context` vs `rag-context-retrieval`)
- Agentes phase/ e runtime/ nunca invocados — existiam apenas por herança do pacote Codex Frontier
- 5-6 skills "fantasma" referenciadas na constituição mas sem uso real catalogado
- Constituição de 766 linhas consumia ~20K tokens em cada sessão, mesmo para tarefas T0-T2

## Decisão
Reduzir o harness para o mínimo funcional baseado em evidência de uso real:

1. **Skills:** de 41 para 18 skills. Mantidas as 15 skills com evidência de invocação em planos/ADRs/handoffs + 3 skills essenciais (task-router, adr-decision-recording, extended-constitution). Skills redundantes movidas para `~/.opencode/_archive/skills/`
2. **Agents:** de 35 para 20 agents (8 core + 12 domain). Agents phase/ (7) e runtime/ (8) movidos para `~/.opencode/_archive/agents/`
3. **Constituição:** criada `opencode-core.md` (~90 linhas) como instrução primária; constituição completa mantida como referência, carregável via skill `extended-constitution` sob demanda
4. **Commands:** mantidos os 6 commands como inline no `opencode.jsonc` (estrutura suficiente)

## Motivação
- Economia de ~15K tokens por sessão (766 → 90 linhas de constituição)
- Eliminação de ambiguidade entre skills duplicadas
- Redução de manutenção de artefatos de harness
- Foco em skills que efetivamente agregam valor ao projeto

## Premissas
- Skills em archive podem ser restauradas se necessário
- Constituição completa (`opencode.md`) permanece como referência imutável
- O workflow de T0-T2 não precisa das regras detalhadas das seções 5-27

## Alternativas Rejeitadas
- Manter 41 skills: overhead de manutenção sem contrapartida de uso
- Reduzir para 8 skills: perda de cobertura para tarefas complexas
- Consolidar em `~/.config/opencode/` em vez de `~/.opencode/`: XDG-compliant mas exigiria migração de todos os projetos

## Consequências
Positivas:
- Sessões T0-T2 mais rápidas (menos tokens de contexto)
- Catálogo de skills gerenciável
- Archive preserva rollback imediato

Negativas:
- Tarefas T4-T5 podem exigir ativação manual da skill `extended-constitution`
- Archive precisa ser mantido (ou perderá valor histórica)

## Validação
- `ls ~/.opencode/skills/ | wc -l` ≤ 20
- `ls ~/.opencode/agents/ | wc -l` ≤ 22 (core + domain)
- `~/.config/opencode/opencode.jsonc instructions` aponta para `~/.opencode/opencode-core.md`
- `wc -l ~/.opencode/opencode-core.md` ≤ 250
