# ADR-010: Runtime Governance como Camada Nativa do Harness

## Status
Accepted

## Data
2026-06-18

## Contexto
O projeto OpenF1 Data Platform opera com um harness OpenCode (Claude Code) que possui governança distribuída em 4 diretórios. Durante a análise F1-017, identificou-se que a camada de governança operacional (preflight, evidência, edição segura, artefato, contexto, uso de ferramentas, conectores, consumo de conhecimento) não estava formalizada como parte do harness, mas como um pacote externo (`opencode_runtime_governance_pack`).

O pacote `opencode_runtime_governance_pack` foi gerado externamente e continha políticas, ADR e script de instalação, mas sem integração com o ecossistema nativo de skills/agents/commands do OpenCode. Isso criava uma barreira de adoção: aplicar o pacote exigia execução de script separado e não havia equivalência direta com os mecanismos nativos.

O ADR-008 do pacote conflitava numericamente com o ADR-008 do projeto (`docs/adr/adr-008-python-version-and-plan-consolidation.md`).

## Decisão
Adotar o Runtime Governance como camada nativa do harness OpenCode, integrada em `~/.opencode/`:

1. As 8 políticas do pacote são convertidas para skills com SKILL.md em `~/.opencode/skills/`.
2. Os 8 agentes do pacote são criados como agentes runtime em `~/.opencode/agents/runtime/`.
3. Os 6 comandos do pacote são criados como arquivos `.md` em `~/.opencode/commands/`.
4. As 8 políticas são documentadas em `~/.opencode/docs/runtime-governance/`.
5. O ADR passa a ser ADR-010 (renumerado para evitar conflito).
6. O pacote original `opencode_runtime_governance_pack/` permanece como referência histórica, sem ser apagado.

## Consequências

### Ganhos
- Skills e agentes runtime disponíveis como qualquer skill/agente nativo.
- Preflight de skills obrigatórias por nível T vira mecanismo automático.
- Evidência citada passa a ser rastreável (VERIFIED/SOURCED/etc).
- Edição segura tem protocolo formalizado com backup automático.
- ADR-010 substitui ADR-008 do pacote sem conflito de numeração.

### Restrições
- Runtime Governance só funciona se `~/.opencode/` estiver nos `skills.paths` do config global.
- Skills e agentes dependem do OpenCode v4 para resolução de caminhos.
- As políticas são documentação — enforcement ainda depende do operador.

## Relação Com Artefatos
- Plano: `docs/plans/017_harness_openf1_unificacao_governanca.md`
- Config: `~/.config/opencode/opencode.jsonc` (skills.paths apontando para `~/.opencode/`)
- Skills: 8 novas em `~/.opencode/skills/` (preflight, tool-use, artifact, safe-edit, evidence, context, connector, knowledge)
- Agents: 8 novos em `~/.opencode/agents/runtime/`
- Políticas: 8 documentos em `~/.opencode/docs/runtime-governance/`
