# Session Handoffs

Este diretório contém os registros de handoff operacional do OpenF1 Data Platform. Cada handoff captura o estado de uma sessão de trabalho: objetivo, decisões, arquivos alterados, pendências, riscos, comandos executados e prompt de retomada.

## Índice

| Data | Handoff | Descrição |
|------|---------|-----------|
| 2026-06-16 | [Agent Governance Public Safe](2026-06-16_agent_governance_public_safe.md) | Governança de agentes e subagentes |
| 2026-06-17 | [Codex Frontier Partial Adoption](2026-06-17_codex_frontier_partial_adoption.md) | Adoção parcial do pacote Codex Frontier |
| 2026-06-17 | [Doc Check do Alvo Handoff](2026-06-17_doc-check-do-alvo-handoff.md) | Verificação do alvo de handoff |
| 2026-06-17 | [Fase 4 Validação Harness Frontier](2026-06-17_fase-4-validacao-operacional-do-harness-frontier.md) | Validação operacional do harness |
| 2026-06-17 | [Smoke Test do Alvo Handoff](2026-06-17_smoke-test-do-alvo-handoff.md) | Smoke test do handoff |

## Como Criar um Handoff

```bash
make handoff TITLE="descricao_do_trabalho"
```
