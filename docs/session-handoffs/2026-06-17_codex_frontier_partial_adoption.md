# Session Handoff: Codex Frontier Partial Adoption

Date: 2026-06-17
Project: OpenF1 Data Platform
Current Objective: Avaliar e planejar a incorporacao do pacote `codex_frontier_agentic_ecosystem_pack` ao harness do OpenF1 sem importar o pacote completo.
Accepted Decisions:
- Nao adotar o pacote completo.
- Adotar apenas conceitos pontuais e absorve-los no harness atual do OpenF1.
- Usar `ABSORVER_NO_HARNESS` para capacidades que viram regra, etapa ou fluxo existente.
- Manter `EXTENSAO_DE_DOMINIO` apenas para dados ou work packages longos.
- Manter `JA_EXISTE` para capacidades que o OpenF1 ja cobre de forma nativa.
- Descartar instalacao global, copia integral de skills/agentes e governanca paralela.
- Manter `AGENTS.md` e `docs/PROJECT_PROFILE.md` como fonte de verdade principal.
- Evitar instalacao global por padrao.
Relevant Files:
- `AGENTS.md`
- `docs/PROJECT_PROFILE.md`
- `docs/plans/008_codex_frontier_adocao_parcial.md`
- `docs/templates/handoff.md`
- `docs/public-safe/agentic-capabilities-summary.md`
- `docs/session-handoffs/2026-06-17_fase-4-validacao-operacional-do-harness-frontier.md`
- `docs/session-handoffs/2026-06-17_smoke-test-do-alvo-handoff.md`
- `docs/plans/009_handoff_make_target.md`
- `docs/plans/README.md`
- `codex_frontier_agentic_ecosystem_pack/codex_frontier_agentic_ecosystem/README.md`
- `codex_frontier_agentic_ecosystem_pack/codex_frontier_agentic_ecosystem/docs/01_SKILLS_CATALOG.md`
- `codex_frontier_agentic_ecosystem_pack/codex_frontier_agentic_ecosystem/docs/02_AGENTS_CATALOG.md`
- `codex_frontier_agentic_ecosystem_pack/codex_frontier_agentic_ecosystem/install_repo_pack.sh`
- `codex_frontier_agentic_ecosystem_pack/codex_frontier_agentic_ecosystem/install_user_pack.sh`
- `scripts/codex/record_handoff.py`
Commands/Checks Executed:
- Read pacote frontier: README, catalogs, playbook, templates and installers.
- Read OpenF1 `AGENTS.md` and `docs/PROJECT_PROFILE.md`.
- Consulted specialist agents for MCP integration, Python/RAG tooling and harness architecture.
Open Risks:
- Pacote frontier tem alta sobreposicao com a governanca ja existente no OpenF1.
- Adocao completa aumentaria manutencao e risco de ruido operacional.
- Qualquer utilitario reaproveitado precisa ser validado caso a caso antes de entrar no repo.
- O conjunto descartado precisa continuar amarrado a justificativas de especialistas, para evitar retorno por conveniencia.
Next Steps:
- Se Roberto quiser seguir, aplicar a mesma matriz conservadora a qualquer pacote agente/skill futuro.
- Reaproveitar apenas scripts/templates que passem no filtro de utilidade e nao criem taxonomia paralela.
- O recorte aceito da Fase 3 foi apenas o scaffold canônico de handoff e seu gerador.
- A Fase 4 foi executada com um handoff real gerado pelo novo scaffold.
- A entrada padrão do fluxo passou a existir via `make handoff`.
- O smoke test do alvo confirmou geração real do arquivo de handoff.
- O perfil operacional do projeto agora documenta o novo comando.
- Usar a versao `public-safe` quando for preciso comunicar o harness fora do contexto interno.
- Registrar qualquer decisao duravel em `docs/adr/` se a implementacao sair do draft.
Resume Prompt:
- Continue a partir do plano `docs/plans/008_codex_frontier_adocao_parcial.md` e da visao `docs/public-safe/agentic-capabilities-summary.md`; use a matriz conservadora atual e mantenha descartes amarrados a parecer tecnico de especialista.
Public/Private Boundary:
- Documento privado/local. Nao publicar fora do repo sem nova decisao.
