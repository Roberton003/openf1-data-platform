# Plano F1-017: Unificação da Governança do Harness OpenF1

## 1. Contexto

A governança do harness OpenCode está fragmentada em **4 diretórios**:

| Diretório | Função | Dependência |
|-----------|--------|-------------|
| `~/.claude/` | Claude Code legacy | `CLAUDE.md` na hierarquia; skills auto-carregadas |
| `~/.agents/` | Agentes externos | 1 skill úncia (`codex-harness-architect`) auto-carregada |
| `~/.config/opencode/` | Config global nativa | `opencode.jsonc` com 5 referências a `~/.claude/` e `~/.agents/` |
| `~/.opencode/` | Harness projeto-específico | Duplica agents/skills/commands do config global |

**Problemas identificados:**

1. **5 referências** a `~/.claude/` e `~/.agents/` no `opencode.jsonc` (skills.paths, permissions, MCP)
2. **10 skills duplicadas** entre `~/.claude/skills/` e `~/.config/opencode/skills/`
3. **Commands em inline JSON** no `opencode.jsonc` — o harness `opencode-openf1-harness` já mostra que arquivos `.md` em `commands/` é o padrão correto
4. **Runtime Governance** é um pacote separado, não integrado à governança nativa
5. **Projetos duplicam** agents/skills/commands em vez de herdar de um harness global

**Artefatos únicos a preservar** (não existem em `~/.config/opencode/`):

| Artefato | Origem | Tipo | Razão |
|----------|--------|------|-------|
| `beautiful-prose` | `~/.claude/skills/` | Skill | Escrita técnica sem AI tics |
| `concise-planning` | `~/.claude/skills/` | Skill | Plano curto e acionável |
| `skill-frontend-design` | `~/.claude/skills/` | Skill | Design visual |
| `workflow-triggers` | `~/.claude/skills/` | Skill | Workflow automático |
| `codex-harness-architect` | `~/.agents/skills/` | Skill | Arquitetura de harness Codex |
| `multi-agent-coordinator` | `~/.opencode/opencode-openf1-harness/.opencode/agents/` | Agent | Decisão de topologia multiagente |

---

## 2. Decisões do Plano

| Decisão | Motivo | Premissas | Alternativas Rejeitadas |
|---------|--------|-----------|------------------------|
| `~/.opencode/` como diretório único de governança | Elimina fragmentação em 4 diretórios; unifica num local nativo | OpenCode permite `skills.paths` customizados | Manter split (mais complexidade); migrar para `~/.config/opencode/` (não é o desejo de Roberto) |
| Commands como arquivos `.md` em vez de inline JSON | Padrão mais limpo, versionável, extensível; já demonstrado no harness | OpenCode suporta comandos em arquivo | Manter inline (menos flexível) |
| Runtime Governance como skills/agents nativos, não pacote separado | Integração evita "camada externa"; skills ficam disponíveis como qualquer outra | As 8 skills + 8 agents + 6 commands do pacote são compatíveis com OpenCode | Instalar via script Python (menos rastreável) |
| `multi-agent-coordinator` no core | Agente único que decide topologia (SINGLE/SEQUENTIAL/PARALLEL/HYBRID) — cobre lacuna de orquestração | O agente é chamado pelo frontier-orchestrator | Ignorar (perde capacidade de orquestração) |
| Preservar originais em `~/.claude/` e `~/.agents/` como backup | Rollback imediato sem perda de dados | Nenhum — cópia não destrutiva | Mover (destrutivo) |

---

## 3. Escopo

### Incluído
- [ ] Estrutura de diretórios em `~/.opencode/` (agents, commands, skills, docs)
- [ ] Constituição unificada `~/.opencode/opencode.md` (22 seções)
- [ ] 41 skills migradas + 8 runtime = 49 skills
- [ ] 35 agentes organizados em core/domain/phase/runtime
- [ ] 7 commands existentes + 6 runtime = 13 commands
- [ ] 8 políticas runtime-governance em `~/.opencode/docs/`
- [ ] ADR-010
- [ ] `~/.config/opencode/opencode.jsonc` atualizado (0 referências a `~/.claude/`)
- [ ] Projetos existentes atualizados (AGENTS.md, `.opencode/` duplicatas removidas)

### Fora de Escopo
- Implementação do F1-016 (IA/MLOps) — plano separado
- Migração de MCP (mantido desativado)
- Criação de novos agentes/skills além dos listados
- Testes de integração do harness (apenas validação estrutural)

---

## 4. Stack

### Ferramentas
- OpenCode nativo (sem dependências externas)
- `cp -r` para cópia de skills (preservar originais)
- Nenhum script Python — todas as operações via OpenCode skills + agents

### Diretório Alvo
```
~/.opencode/
```

---

## 5. Fases de Implementação

### Fase 0 — Diagnóstico e Leitura (T3, todos os steps paralelos)
**Lead Agent:** OpenCode Chief Engineer
**Skills:** `project-session-bootstrap`, `rag-first-context`
**Agentes:** Nenhum (leitura direta)

| Step | Ação | Arquivos | Verificação |
|------|------|----------|-------------|
| 0.1 | Ler `~/.config/opencode/opencode.jsonc` | `opencode.jsonc` | Extrair: skills.paths, commands, permissions, MCP config |
| 0.2 | Ler `~/.config/opencode/OPENCODE.md` | `OPENCODE.md` | Extrair: 24 seções, modelos, agentes |
| 0.3 | Ler `~/.claude/CLAUDE.md` | `CLAUDE.md` | Extrair: prioridades, comandos, subagentes |
| 0.4 | Listar skills em `~/.claude/skills/` vs `~/.config/opencode/skills/` | Ambos os diretórios | Identificar 4 únicas |
| 0.5 | Listar agents em `~/.opencode/opencode-openf1-harness/.opencode/agents/` | Diretório do harness | Identificar multi-agent-coordinator |
| 0.6 | Ler Runtime Governance Pack completo | `~/.opencode/opencode_runtime_governance_pack/` | Listar 8 skills, 8 agents, 6 commands, 8 policies |
| 0.7 | Verificar `~/.claude/mcp/` config | `opencode.jsonc` line 117 | Confirmar MCP desativado |
| **Gate** | Confirmar com Roberto que o diagnóstico está completo | — | `git diff --stat` limpo |

---

### Fase 1 — Estrutura de Diretórios (T2)
**Skills:** `safe-file-editing-protocol`
**Agentes:** Nenhum (criação de diretórios)

| Step | Ação | Verificação |
|------|------|-------------|
| 1.1 | Criar `~/.opencode/agents/core/` | `ls ~/.opencode/agents/core/` → vazio |
| 1.2 | Criar `~/.opencode/agents/domain/` | `ls ~/.opencode/agents/domain/` → vazio |
| 1.3 | Criar `~/.opencode/agents/runtime/` | `ls ~/.opencode/agents/runtime/` → vazio |
| 1.4 | Criar `~/.opencode/commands/` | `ls ~/.opencode/commands/` → vazio |
| 1.5 | Criar `~/.opencode/skills/` | `ls ~/.opencode/skills/` → vazio |
| 1.6 | Criar `~/.opencode/docs/runtime-governance/` | `ls ~/.opencode/docs/runtime-governance/` → vazio |
| 1.7 | Criar `~/.opencode/docs/adr/` | `ls ~/.opencode/docs/adr/` → vazio |
| 1.8 | Criar `~/.opencode/scripts/` | `ls ~/.opencode/scripts/` → vazio |

---

### Fase 2 — Constituição Unificada `~/.opencode/opencode.md` (T3)
**Skills:** `write-implementation-plan`, `concise-planning`, `beautiful-prose`
**Agentes:** `domain/documentation-curator`

**Entrada:** `OPENCODE.md` (678 linhas) + `CLAUDE.md` (79 linhas) + harness `opencode.md` (80 linhas)

| Step | Ação | Conteúdo | Verificação |
|------|------|----------|-------------|
| 2.1 | Seção 1-3: Identidade, Prioridade de Fontes, Bootstrap | OPENCODE.md §§1-3 + CLAUDE.md Priority | `head -100 opencode.md` |
| 2.2 | Seção 4: Task Router T0-T5 (estendido) | OPENCODE.md §4 + Runtime Governance §5 | Task classification table completa |
| 2.3 | Seção 5: Skill Preflight (NOVO) | skill-preflight-orchestrator + preflight matrix | Gates T1-T5 listados |
| 2.4 | Seção 6-8: Budget, Model Router, RAG | OPENCODE.md §§5-7 | Model assignment table |
| 2.5 | Seção 9: Multiagente + multi-agent-coordinator | OPENCODE.md §§9-10 + novo agente | Topology rules SINGLE/SEQUENTIAL/PARALLEL/HYBRID |
| 2.6 | Seção 10-11: Skills + Commands | OPENCODE.md §11; commands como arquivos | Lista de 13 commands |
| 2.7 | Seção 12-13: Planejamento + Evidência | OPENCODE.md §§12-13 + citation-evidence-guardian | Classification VERIFIED/SOURCED/INFERRED/ASSUMED |
| 2.8 | Seção 14-15: Edição Segura + Segurança Op. | safe-file-editing-protocol + OPENCODE.md §14 | Safe editing checklist |
| 2.9 | Seção 16-18: Memória, Gates, Comunicação | OPENCODE.md §§15-17 | Gate pipeline T0-T5 |
| 2.10 | Seção 19-22: Processing Context, Operating Order, Stop Conditions, Report | OPENCODE.md §§18-24 | Template final report |
| **Gate** | Validar com Roberto | `wc -l opencode.md` | Confirmar 22 seções |

---

### Fase 3 — Skills (T3, steps paralelos)
**Skills:** `safe-file-editing-protocol`
**Agentes:** Nenhum (cópia de arquivos)

| Step | Ação | Origem → Destino | Skills |
|------|------|------------------|--------|
| 3.1 | Copiar 28 skills nativas | `~/.config/opencode/skills/` → `~/.opencode/skills/` | N/A (cp) |
| 3.2 | Copiar `beautiful-prose` | `~/.claude/skills/beautiful-prose/` → `~/.opencode/skills/` | UNIQUE |
| 3.3 | Copiar `concise-planning` | `~/.claude/skills/concise-planning/` → `~/.opencode/skills/` | UNIQUE |
| 3.4 | Copiar `skill-frontend-design` | `~/.claude/skills/skill-frontend-design/` → `~/.opencode/skills/` | UNIQUE |
| 3.5 | Copiar `workflow-triggers` | `~/.claude/skills/workflow-triggers/` → `~/.opencode/skills/` | UNIQUE |
| 3.6 | Copiar `codex-harness-architect` | `~/.agents/skills/codex-harness-architect/` → `~/.opencode/skills/` | UNIQUE |
| 3.7 | Criar `skill-preflight-orchestrator` | Runtime Governance Pack → `~/.opencode/skills/` | NOVO |
| 3.8 | Criar `tool-use-governor` | Runtime Governance Pack → `~/.opencode/skills/` | NOVO |
| 3.9 | Criar `artifact-decision-router` | Runtime Governance Pack → `~/.opencode/skills/` | NOVO |
| 3.10 | Criar `safe-file-editing-protocol` | Runtime Governance Pack → `~/.opencode/skills/` | NOVO |
| 3.11 | Criar `citation-evidence-guardian` | Runtime Governance Pack → `~/.opencode/skills/` | NOVO |
| 3.12 | Criar `context-window-compaction-manager` | Runtime Governance Pack → `~/.opencode/skills/` | NOVO |
| 3.13 | Criar `connector-governance` | Runtime Governance Pack → `~/.opencode/skills/` | NOVO |
| 3.14 | Criar `copyright-safe-knowledge-consumer` | Runtime Governance Pack → `~/.opencode/skills/` | NOVO |
| **Gate** | Listar skills e verificar SKILL.md | `for d in ~/.opencode/skills/*/; do [ -f "$d/SKILL.md" ] && echo "OK $d" || echo "MISSING $d"; done` | 49 skills, todas com SKILL.md |

---

### Fase 4 — Agentes (T3, steps paralelos)
**Skills:** `safe-file-editing-protocol`
**Agentes:** Nenhum (cópia de arquivos + frontmatter update)

| Step | Ação | Origem → Destino | Observação |
|------|------|------------------|------------|
| 4.1 | Copiar agents core (8) | `~/.config/opencode/agents/core/` → `~/.opencode/agents/core/` | lead-engineer, economy-plan, economy-build, frontier-orchestrator, harness-architect, harness-operator, harness-skeptic, multi-agent-coordinator |
| 4.2 | Copiar agents domain (12) | `~/.config/opencode/agents/domain/` → `~/.opencode/agents/domain/` | data-engineer, test-engineer, security-reviewer, devops-release-engineer, documentation-curator, cost-budget-governor, rag-context-curator, adr-decision-recorder, adversarial-reviewer, completion-auditor, decision-memory-keeper, verification-engineer |
| 4.3 | Copiar agents phase (7) | `~/.config/opencode/agents/phase/` → `~/.opencode/agents/phase/` | phase-1 a phase-7 |
| 4.4 | Copiar multi-agent-coordinator | Do harness → `~/.opencode/agents/core/multi-agent-coordinator.md` | UNIQUE do harness |
| 4.5 | Criar runtime-policy-architect | Runtime Governance Pack → `~/.opencode/agents/runtime/` | NOVO |
| 4.6 | Criar tool-use-governor | Runtime Governance Pack → `~/.opencode/agents/runtime/` | NOVO |
| 4.7 | Criar artifact-router | Runtime Governance Pack → `~/.opencode/agents/runtime/` | NOVO |
| 4.8 | Criar safe-editor | Runtime Governance Pack → `~/.opencode/agents/runtime/` | NOVO |
| 4.9 | Criar evidence-guardian | Runtime Governance Pack → `~/.opencode/agents/runtime/` | NOVO |
| 4.10 | Criar context-compactor | Runtime Governance Pack → `~/.opencode/agents/runtime/` | NOVO |
| 4.11 | Criar connector-steward | Runtime Governance Pack → `~/.opencode/agents/runtime/` | NOVO |
| 4.12 | Criar knowledge-compliance-guardian | Runtime Governance Pack → `~/.opencode/agents/runtime/` | NOVO |
| **Gate** | Verificar frontmatter de cada agente | `for f in ~/.opencode/agents/**/*.md; do head -3 "$f" | grep -q "description:" && echo "OK $f" || echo "NO FRONTMATTER $f"; done` | 35 agents, todos com frontmatter |

---

### Fase 5 — Commands (T2)
**Skills:** `safe-file-editing-protocol`
**Agentes:** Nenhum (criar arquivos)

| Step | Ação | Conteúdo | Verificação |
|------|------|----------|-------------|
| 5.1 | Criar `audit.md` | Template: adversarial-review + completion-auditor. Skills: adversarial-review, completion-auditor. Agent: adversarial-reviewer | Template completo |
| 5.2 | Criar `data-patch.md` | Template: rag-first-context + data-engineering. Skills: rag-first-context, data-engineering, verification-workflow-designer. Agent: data-engineer | Template completo |
| 5.3 | Criar `economy-patch.md` | Template: rag-first-context + goal-driven-execution. Skills: rag-first-context, goal-driven-execution, verification-workflow-designer, completion-auditor. Agent: economy-build | Template completo |
| 5.4 | Criar `frontier-plan.md` | Template: frontier-agentic-workflow. Skills: frontier-agentic-workflow. Agent: frontier-orchestrator | Template completo |
| 5.5 | Criar `handoff.md` | Template: decision-memory + completion-auditor. Skills: decision-memory, handoff-writer. Agent: decision-memory-keeper | Template completo |
| 5.6 | Criar `rag-plan.md` | Template: effort-budget-governor + goal-driven-execution. Skills: effort-budget-governor, goal-driven-execution, rag-first-context. Agent: economy-plan | Template completo |
| 5.7 | Criar `verify.md` | Template: verification-workflow-designer + completion-auditor. Skills: verification-workflow-designer, completion-auditor. Agent: verification-engineer | Template completo |
| 5.8 | Criar `runtime-audit.md` | Runtime Governance Pack → `~/.opencode/commands/` | NOVO |
| 5.9 | Criar `evidence-audit.md` | Runtime Governance Pack → `~/.opencode/commands/` | NOVO |
| 5.10 | Criar `safe-patch.md` | Runtime Governance Pack → `~/.opencode/commands/` | NOVO |
| 5.11 | Criar `runtime-plan.md` | Runtime Governance Pack → `~/.opencode/commands/` | NOVO |
| 5.12 | Criar `context-compact.md` | Runtime Governance Pack → `~/.opencode/commands/` | NOVO |
| 5.13 | Criar `artifact-route.md` | Runtime Governance Pack → `~/.opencode/commands/` | NOVO |
| **Gate** | Listar commands | `ls ~/.opencode/commands/` | 13 commands |

---

### Fase 6 — Config Global `~/.config/opencode/opencode.jsonc` (T3)
**Skills:** `customize-opencode`, `safe-file-editing-protocol`
**Agentes:** `domain/security-reviewer` (auditar mudanças de permissão)

| Step | Ação | Antigo → Novo | Risco |
|------|------|---------------|-------|
| 6.1 | Atualizar `instructions` | `["OPENCODE.md"]` → `["~/.opencode/opencode.md"]` | Baixo — caminho absoluto |
| 6.2 | Remover `skills.paths[1]` | `"~/.claude/skills"` → removido | Médio — perder skills únicas se não copiadas antes |
| 6.3 | Remover `skills.paths[2]` | `"~/.agents/skills"` → removido | Médio — perder codex-harness-architect se não copiado antes |
| 6.4 | Adicionar `skills.paths[1]` | NOVO: `"~/.opencode/skills"` | Baixo |
| 6.5 | Remover `permission.external_directory` entries | `"~/.claude/skills/**"` e `"~/.agents/skills/**"` → removidos | Médio — OpenCode pode negar acesso se tentar ler |
| 6.6 | Adicionar `permission.external_directory` | `"~/.opencode/**"` → NOVO | Baixo |
| 6.7 | Remover `command` inline | Linhas 7-43 → removidos | Médio — commands agora em `~/.opencode/commands/` |
| 6.8 | Remover/adicionar MCP | Remover referência a `~/.claude/mcp/` | Baixo — MCP já desativado |
| 6.9 | Adicionar `default_agent` explícito | `"core/lead-engineer"` → manter | Baixo |
| **Gate** | Validar JSON syntax | `.venv/bin/python3 -c "import json; json.load(open('$HOME/.config/opencode/opencode.jsonc'))"` | Parse OK |

---

### Fase 7 — Políticas Runtime Governance + ADR (T4)
**Skills:** `adr-decision-recording`, `documentation-curator`
**Agentes:** `domain/documentation-curator`, `domain/adr-decision-recorder`

| Step | Ação | Conteúdo | Verificação |
|------|------|----------|-------------|
| 7.1 | Criar `docs/runtime-governance/README.md` | Visão geral da camada | `head -3` |
| 7.2 | Criar `docs/runtime-governance/skill-preflight-matrix.md` | Matriz T0-T5 × skills obrigatórias | Matrix completa |
| 7.3 | Criar `docs/runtime-governance/tool-use-policy.md` | Política de uso de ferramentas | 3+ regras |
| 7.4 | Criar `docs/runtime-governance/artifact-routing-policy.md` | Roteamento de artefatos por nível T | Tabela T0-T5 |
| 7.5 | Criar `docs/runtime-governance/evidence-policy.md` | Classificação VERIFIED/SOURCED/INFERRED/ASSUMED | 6 níveis |
| 7.6 | Criar `docs/runtime-governance/safe-editing-policy.md` | Protocolo de edição segura | Checklist |
| 7.7 | Criar `docs/runtime-governance/context-compaction-policy.md` | Quando compactar contexto | Gatilhos |
| 7.8 | Criar `docs/runtime-governance/knowledge-consumption-policy.md` | Consumo da biblioteca técnica | 7 regras |
| 7.9 | Criar ADR-010 (`docs/adr/adr-010-runtime-governance.md`) | Decisão: adotar Runtime Governance | ADR completo |
| **Gate** | Listar docs | `ls ~/.opencode/docs/runtime-governance/` + `ls ~/.opencode/docs/adr/` | 8 policies + 1 ADR |

---

### Fase 8 — Atualizar Projetos (T2)
**Skills:** `safe-file-editing-protocol`
**Agentes:** Nenhum

| Step | Ação | Arquivo | Mudança |
|------|------|---------|---------|
| 8.1 | Atualizar `AGENTS.md` no projeto | `AGENTS.md` | Remover referência a `~/.claude/CLAUDE.md` da hierarquia |
| 8.2 | Adicionar `~/.opencode/opencode.md` na hierarquia | `AGENTS.md` | NOVA prioridade 2 |
| 8.3 | Verificar `docs/adr/ADR-008` (conflito numeração) | `docs/adr/adr-008-python-version-and-plan-consolidation.md` | Confirmar que ADR-008 do Runtime Governance virou ADR-010 |
| **Gate** | git status limpo | `git status --short` | Nenhum arquivo não-planejado |

---

## 6. Dependências entre Fases

```
Fase 0 (diagnóstico)
 └─► Fase 1 (diretórios) ──► Fase 2 (constituição)
 │                          └─► Fase 3 (skills) ──► Fase 4 (agentes)
 │                          └─► Fase 5 (commands)
 │                          └─► Fase 6 (config) ←─ depende de 3, 4, 5
 └─► Fase 7 (políticas + ADR) ← independente
 └─► Fase 8 (projetos) ← depende de 6
```

**Execução recomendada:**
- Fase 0 → 1 → 2 (sequencial)
- Fase 3, 4, 5, 7 (paralelo — sem dependência)
- Fase 6 (após 3+4+5)
- Fase 8 (após 6)

---

## 7. Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|--------------|---------|-----------|
| `skill-preflight-orchestrator` pode tornar sessões lentas para T0 | Alta | Produtividade | Documentar que T0 não exige preflight; regra na constituição |
| Remover `~/.claude/skills` do `skills.paths` quebra acesso se skills não copiadas | Média | Skills indisponíveis | Copiar 4 únicas ANTES de atualizar config (Fase 6 depende de Fase 3) |
| `multi-agent-coordinator` não funciona como esperado | Baixa | Orquestração falha | Fallback para SINGLE; agente read-only |
| Commands inline removidos do JSON mas commands file não carregam | Média | Comandos indisponíveis | OpenCode carrega commands de ambos; testar `/verify` após mudança |
| Projetos com `.opencode/agents/` próprio entram em conflito | Baixa | Agente errado | Documentar que project override > global |

---

## 8. Rollback

| Fase | Procedimento |
|------|-------------|
| 0-1 | `rm -rf ~/.opencode/agents/ ~/.opencode/commands/ ~/.opencode/skills/ ~/.opencode/docs/` (se falhou antes do conteúdo) |
| 2 | `rm ~/.opencode/opencode.md` |
| 3 | `rm -rf ~/.opencode/skills/` + restaurar skills.paths no config |
| 4 | `rm -rf ~/.opencode/agents/` |
| 5 | `rm -rf ~/.opencode/commands/` + restaurar command inline no config |
| 6 | `git checkout ~/.config/opencode/opencode.jsonc` (backup preservado) |
| 7 | `rm -rf ~/.opencode/docs/runtime-governance/` |
| 8 | `git checkout AGENTS.md` |

---

## 9. Critérios de Aceite

- [ ] `~/.opencode/opencode.md` existe com 22 seções
- [ ] `~/.opencode/skills/` contém 49 skills, todas com SKILL.md
- [ ] `~/.opencode/agents/` contém 35 agents, organizados em core/domain/phase/runtime
- [ ] `~/.opencode/commands/` contém 13 commands
- [ ] `~/.opencode/docs/runtime-governance/` contém 8 políticas
- [ ] `~/.opencode/docs/adr/` contém ADR-010
- [ ] `~/.config/opencode/opencode.jsonc` — 0 referências a `~/.claude/` ou `~/.agents/`
- [ ] `~/.config/opencode/opencode.jsonc` — `skills.paths` contém `~/.opencode/skills`
- [ ] `~/.config/opencode/opencode.jsonc` — commands inline removidos
- [ ] Projeto `AGENTS.md` — sem referência a `~/.claude/CLAUDE.md`
- [ ] Projeto `AGENTS.md` — hierarquia inclui `~/.opencode/opencode.md`
- [ ] Nenhum arquivo original deletado (originais em `~/.claude/` e `~/.agents/` intactos)

---

## 10. Verificação Final

```bash
# 1. Verificar estrutura
ls -d ~/.opencode/agents/*/ ~/.opencode/commands/ ~/.opencode/skills/*/ ~/.opencode/docs/runtime-governance/ ~/.opencode/docs/adr/

# 2. Contar skills
find ~/.opencode/skills/ -name SKILL.md | wc -l
# Deve ser 49

# 3. Contar agents
find ~/.opencode/agents/ -name "*.md" | wc -l
# Deve ser 35

# 4. Verificar config syntax
.venv/bin/python3 -m json.tool "$HOME/.config/opencode/opencode.jsonc" > /dev/null && echo "JSON OK"

# 5. Verificar zero referências claude
grep -c "\.claude" "$HOME/.config/opencode/opencode.jsonc" || echo "CLEAN"
grep -c "\.agents" "$HOME/.config/opencode/opencode.jsonc" || echo "CLEAN"

# 6. Verificar skills.paths
grep "opencode/skills" "$HOME/.config/opencode/opencode.jsonc" && echo "OK"
```

---

## 11. Agentes e Skills por Fase

| Fase | Skills | Agentes | Topologia |
|------|--------|---------|-----------|
| 0 | `project-session-bootstrap`, `rag-first-context` | Nenhum | SEQUENTIAL (steps 0.1-0.7) |
| 1 | `safe-file-editing-protocol` | Nenhum | SEQUENTIAL (mkdir) |
| 2 | `write-implementation-plan`, `concise-planning`, `beautiful-prose` | `domain/documentation-curator` | SEQUENTIAL (22 seções) |
| 3 | `safe-file-editing-protocol` | Nenhum | PARALLEL (cp + criar) |
| 4 | `safe-file-editing-protocol` | Nenhum | PARALLEL (cp + criar) |
| 5 | `safe-file-editing-protocol` | Nenhum | PARALLEL (13 files) |
| 6 | `customize-opencode`, `safe-file-editing-protocol` | `domain/security-reviewer` | SEQUENTIAL (9 edições no JSON) |
| 7 | `adr-decision-recording`, `documentation-curator` | `domain/documentation-curator`, `domain/adr-decision-recorder` | PARALLEL (8 policies + ADR) |
| 8 | `safe-file-editing-protocol` | Nenhum | SEQUENTIAL (2 arquivos) |

---

### ◈ Processing Context

- **Lead Agent:** OpenCode Chief Engineer
- **Supporting Agents:** `domain/documentation-curator` (Fase 2, 7), `domain/adr-decision-recorder` (Fase 7), `domain/security-reviewer` (Fase 6)
- **Commands/Subagents Used:** `task` para análises de overlap (agents, skills, commands)
- **Skills Used:** `write-implementation-plan`, `project-session-bootstrap`, `rag-first-context`, `safe-file-editing-protocol`, `concise-planning`, `beautiful-prose`, `customize-opencode`, `adr-decision-recording`, `documentation-curator`
- **Knowledge Sources:** `~/.config/opencode/opencode.jsonc`, `~/.config/opencode/OPENCODE.md`, `~/.claude/CLAUDE.md`, `~/.opencode/opencode-openf1-harness/`, Runtime Governance Pack, `docs/plans/016_ia_mlops_e_observabilidade.md`
- **Files Analyzed:** 4 diretórios de governança, 28 skills nativas, 10 agents do harness, 7 commands, 2 constituições, 1 pacote runtime
- **Task Level:** T4 (decisão durável, migração de governança, cross-domain)
- **Validations:** Overlap analysis por 3 subagentes (agents, skills, commands); comparação frontmatter a frontmatter
- **Not Executed:** Nenhuma mudança de arquivo — plano apenas. Fase 6 depende de Fase 3-5 terem sido executadas primeiro para não quebrar skills paths.
