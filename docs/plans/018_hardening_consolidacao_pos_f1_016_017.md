# Plano F1-018: Hardening e Consolidação Pós F1-016/017

## 1. Contexto

O harness OpenF1 foi unificado (F1-017) e a camada IA/MLOps + Observabilidade foi implantada (F1-016). Um conselho técnico com 5 subagentes (Segurança, Data Engineering, DevOps, Documentação, Testes) auditou o estado atual e identificou gaps comuns:

1. **Governança aspiracional** — gates definidos na constituição, enforcement zero
2. **Legacy artifacts** — `~/.claude/` (37 arquivos) e `~/.agents/` (1 arquivo) mortos ainda presentes
3. **Inventory bloat** — 41 skills + 35 agents + 13 commands = 89 artefatos para projeto solo
4. **Phantom references** — constituição cita 8 skills, `MODEL_ROUTER.md`, `scripts/rag/reindex_if_needed.sh` que não existem
5. **Sem observabilidade** — tokens, coverage, freshness, latência: nada é medido
6. **Segurança declarativa** — sem secret-scanning, sem `.env.example`, permissões super-broad
7. **Freshness falsa** — SLA endpoint sempre reporta `data_freshness_minutes: 0.0`
8. **CI sem enforcement** — coverage não verificado, security scanning ausente
9. **Evidência não persistida** — relatórios dos 5 agentes do conselho não foram versionados em `docs/session-handoffs/`

| Domínio | Score | Pior Gap |
|---------|-------|----------|
| Segurança | 3.0/5 | Sem detect-secrets no pre-commit |
| Data Engineering | 3.3/5 | Freshness sempre 0.0 (cosmética) |
| DevOps | 2.7/5 | max-line-length conflitante (100 vs 120) |
| Documentação | 3.5/5 | 8 skills fantasmas na constituição |
| Testes | ⚠️ | Suite não verificada — coleção não confirmada |

---

## 2. Decisões do Plano

| Decisão | Motivo | Premissas | Alternativas Rejeitadas |
|---------|--------|-----------|------------------------|
| Harness reduction: ~15 skills, ~10 agents, ~8 commands | 89 artefatos é desproporcional para projeto solo; 12 skills bastam (task-router, data-engineering, adversarial-review, completion-auditor, systematic-debugging, rag-first-context, verification-workflow-designer, goal-driven-execution, decision-memory, project-session-bootstrap, handoff-writer, write-implementation-plan) | Skills redundantes podem ser removidas sem afetar orçamento de tokens | Manter 41 (overhead de manutenção); reduzir para 8 (perde cobertura) |
| Constituição em duas camadas: ~200 linhas + skill extended | 766 linhas = ~20K tokens carregados em toda sessão; ~80% das tarefas são T0-T2 que não precisam de toda a constituição. Regra de precedência: `opencode-core.md` > `extended-constitution` | OpenCode permite skills que carregam regras sob demanda | Manter monolithic (custo fixo de 20K tokens/sessão) |
| `~/.claude/` e `~/.agents/` arquivados (não deletados) | Rollback imediato se algo quebrar; não polui contexto ativo | Backup em `~/.opencode/_archive/` com timestamp | Deletar (irreversível); manter (polui contexto) |
| Freshness real no SLA endpoint | Métrica cosmética é pior que nenhuma — dá falsa confiança | Pipeline tem acesso a timestamps de arquivos ou tabelas Bronze | Manter 0.0 (falso positivo eterno) |
| CI com `--cov-fail-under=60` | F1-015 definiu target de 60%; sem enforcement, cobertura pode cair | pytest-cov já está em requirements.txt | Manter sem enforcement (perde accountability) |
| Phantom skills: remover referências da constituição | Skills não existem e não devem ser criadas como stub — eliminar a referência é mais limpo | Decisão validada pelo adversarial-reviewer | Criar stubs (mascara o problema) |
| Script único de validação (`make validate`) | Unifica lint+test+security+coverage em um comando | Makefile aceita novo target | Manter targets separados (perde gate único) |
| Rollback coverage para config global | `~/.config/opencode/opencode.jsonc` não está no git — rollback manual documentado | Nenhuma — risco aceito com documentação | Ignorar (perde recoverability) |
| Evidência persistida em handoff | Relatórios dos 5 agentes do conselho devem ficar acessíveis | `docs/session-handoffs/` aceita múltiplos formatos | Não versionar (evidência se perde) |

---

## 3. Escopo

### Incluído
- [ ] Verificar coleção de testes + unificar max-line-length em 120
- [ ] Arquivar `~/.claude/` e `~/.agents/` em `~/.opencode/_archive/`
- [ ] Consolidar skills para ≤20 (remover redundantes, mover para archive)
- [ ] Consolidar agents para ≤12 (core + domain, remover phase/runtime)
- [ ] Constituição enxuta (`~/.opencode/opencode-core.md`, ≤250 linhas) + skill extended
- [ ] Criar `.env.example` com variáveis tipadas
- [ ] Adicionar detect-secrets + hooks de segurança no pre-commit
- [ ] Restringir `external_directory` no `~/.config/opencode/opencode.jsonc`
- [ ] Adicionar deny rules expandidas para pipe-to-shell (`| sh`, `| bash`, `python -c`, `base64 -d`, `chmod +x`, `curl *|*`, `wget *|*`, `eval *`, `rm -rf /`, `rm -rf ~`)
- [ ] Substituir `data_freshness_minutes: 0.0` por cálculo real com guard clause
- [ ] Adicionar validação de Gold com constraints físicas (teste, não só grep)
- [ ] Adicionar `--cov-fail-under=60` ao CI + job security (Bandit + Safety)
- [ ] Criar `make validate` (lint+test+security+coverage)
- [ ] Corrigir phantom skills na constituição (remover 8 referências)
- [ ] Adicionar SLA por tabela no endpoint `/api/pipeline_execution/sla/tables`
- [ ] ADR-011 documentando redução do harness
- [ ] Handoff final: `docs/session-handoffs/2026-06-18_f1-018-hardening.md`
- [ ] Verificar `~/.config/opencode/opencode.md` (só `.bak` encontrado — corrigir antes da Fase 2)

### Fora de Escopo
- Migração para ruff (recomendado mas postergado — baixo impacto)
- Terraform state backend (requer bucket GCS — depende de Roberto)
- Orquestração ativa com scheduler (Dagster daemon ou cron)
- Notificação Slack/Discord (requer webhook)
- Great Expectations (pesado para o projeto atual)
- Sistema de métricas/observabilidade (tracking de tokens)

---

## 4. Stack

- OpenCode CLI + .venv Python 3.12
- pytest + pytest-cov + detect-secrets (pre-commit)
- Bandit + Safety (CI security scanning)
- DuckDB (SLA queries)
- `jq` (verificação de JSON config) — `which jq` antes de usar
- `act` (CI local) — fallback: `make validate --dry-run`

---

## 5. Fases de Implementação

### Fase 0 — Quick Wins (T1, paralelo)
**Skills:** `systematic-debugging`
**Agentes:** Nenhum

| Step | Ação | Verificação |
|------|------|-------------|
| 0.1 | Verificar coleção de testes: `pytest tests/ --collect-only -q` | Contagem de tests registrada |
| 0.2 | Unificar max-line-length em 120 nos 3 arquivos (`.pre-commit-config.yaml`, `Makefile`, `.github/workflows/ci.yml`) | `grep 'max-line-length' .pre-commit-config.yaml Makefile .github/workflows/ci.yml` → todos 120 |
| 0.3 | Trocar `--host 0.0.0.0` por `--host 127.0.0.1` no Makefile `run` | `grep '--host' Makefile` → 127.0.0.1 |
| Gate | Roberto valida lock semântico | `git diff --stat` limpo |

---

### Fase 1 — Segurança (T2)
**Skills:** `verification-workflow-designer`
**Agentes:** Nenhum (edições de arquivo)

| Step | Ação | Verificação |
|------|------|-------------|
| 1.1 | Criar `.env.example` com variáveis (OPENF1_API_BASE_URL, GCP_PROJECT_ID, GOOGLE_APPLICATION_CREDENTIALS) | `ls .env.example` |
| 1.2 | Adicionar hooks `detect-private-key`, `check-added-large-files`, `check-merge-conflict` ao `.pre-commit-config.yaml` | `pre-commit run --all-files` → hooks executam |
| 1.3 | Adicionar `detect-secrets` com baseline: `pip install detect-secrets && detect-secrets scan > .secrets.baseline` + hook no pre-commit | `pre-commit run detect-secrets --all-files` |
| 1.4 | Restringir `external_directory` no `opencode.jsonc`: `~/.config/opencode/**` → `~/.config/opencode/commands/**`; `~/.local/share/**` → `~/.local/share/rag-indexes/**` | `jq '.permissions.external_directory' ~/.config/opencode/opencode.jsonc` → sem `**` catch-all |
| 1.5 | Adicionar deny rules expandidas: `curl *|*`, `wget *|*`, `eval *`, `rm -rf /`, `rm -rf ~`, `*| sh`, `*| bash`, `python -c`, `base64 -d`, `chmod +x` | `jq '.permissions.bash' ~/.config/opencode/opencode.jsonc` |
| 1.6 | Arquivar `~/.claude/` e `~/.agents/` em `~/.opencode/_archive/` com timestamp | `ls ~/.opencode/_archive/` → `claude-YYYYMMDD/`, `agents-YYYYMMDD/` |
| Gate | Pre-commit passa sem secrets vazados | `pre-commit run --all-files` |

---

### Fase 2 — Documentação e Constituição (T3)
**Skills:** `write-implementation-plan`
**Agentes:** domain/documentation-curator (read-only de verificação)

| Step | Ação | Verificação |
|------|------|-------------|
| 2.0 | Verificar `~/.config/opencode/opencode.md` existe (só `.bak` encontrado na auditoria) | `ls ~/.config/opencode/opencode.md` → existe ou corrigir |
| 2.1 | Phantom skills: remover 8 referências da matriz preflight no `~/.opencode/opencode.md` (skill-preflight-orchestrator, artifact-decision-router, citation-evidence-guardian, context-window-compaction-manager, safe-file-editing-protocol, multi-agent-coordinator, multi-agent-orchestration, frontier-agentic-workflow). Manter apenas skills que existem no catálogo | `grep -c 'skill-' ~/.opencode/opencode.md` → ≤ skills existentes |
| 2.2 | Corrigir referência a `scripts/codex/record_handoff.py` no PROJECT_PROFILE | `grep 'codex' docs/PROJECT_PROFILE.md` → vazio |
| 2.3 | Adicionar handoff `2026-06-18_f1-015-closure.md` ao índice do README de handoffs | `grep 'f1-015-closure' docs/session-handoffs/README.md` |
| 2.4 | Adicionar `docs/QUICKSTART.md` (~30 linhas) para novos agentes | `ls docs/QUICKSTART.md` |
| 2.5 | Constituição enxuta: criar `~/.opencode/opencode-core.md` (~200 linhas) com identidade, prioridade de fontes, task router T0-T4, budget tiers, regras de segurança, regras de evidência | `wc -l ~/.opencode/opencode-core.md` ≤ 250 |
| 2.6 | Skill extended-constitution: criar `~/.opencode/skills/extended-constitution/SKILL.md` que carrega seções 5-27 sob demanda (precedência: `opencode-core.md` > `extended-constitution`) | `ls ~/.opencode/skills/extended-constitution/SKILL.md` |
| 2.7 | Migrar `~/.config/opencode/opencode.jsonc` `instructions` para apontar `~/.opencode/opencode-core.md` | `jq '.instructions[0]' ~/.config/opencode/opencode.jsonc` → `~/.opencode/opencode-core.md` |
| Gate | Roberto valida que a constituição enxuta cobre casos de uso diários | Revisão manual |

---

### Fase 3 — Harness Reduction (T3)
**Skills:** `decision-memory`
**Agentes:** core/harness-architect (read-only de verificação)

| Step | Ação | Verificação |
|------|------|-------------|
| 3.1 | Auditar skills: `grep -rohE "skill:" docs/plans/ docs/adr/ docs/session-handoffs/ \| cut -d: -f2 \| sort -u` para listar skills efetivamente invocadas em decisões passadas | Lista de skills invocadas — output salvo |
| 3.2 | Skills para archive: mover para `~/.opencode/_archive/skills/` as skills redundantes (`expert-data-engineering`, `rag-context-retrieval`, `beautiful-prose`, `skill-frontend-design`, `copyright-safe-knowledge-consumer`, `connector-governance`, `tool-use-governor`) e skills não invocadas (Step 3.1) | `ls ~/.opencode/skills/ \| wc -l` ≤ 20 |
| 3.3 | Mover agentes phase/ e runtime/ para `~/.opencode/_archive/agents/` | `ls ~/.opencode/agents/` → apenas `core/` e `domain/` |
| 3.4 | ADR-011: redução do harness | `ls docs/adr/adr-011-harness-reduction.md` |
| 3.5 | Atualizar AGENTS.md com novo número de skills/agents | `wc -l AGENTS.md` ≈ 50 |
| Gate | Skills ≤ 20, agents ≤ 12, ADR-011 salvo | Verificação manual |

---

### Fase 4 — Data Pipeline Hardening (T2)
**Skills:** `data-engineering`
**Agentes:** Nenhum (edições de código)

| Step | Ação | Verificação |
|------|------|-------------|
| 4.1 | Substituir `data_freshness_minutes: 0.0` hardcoded em `process.py` e `assets.py` por cálculo baseado no mtime dos arquivos Bronze. Guard clause: se Bronze não existir ou estiver vazio, freshness = `None` (não `0.0`) | `grep 'data_freshness_minutes: 0.0' src/ingestion/process.py src/ingestion/assets.py` → vazio |
| 4.2 | Adicionar validação de Gold: constraints físicas (`validate_gold_constraints` em `src/ingestion/process.py` e `assets.py`). Teste de unidade: dados com lap_duration < 30 ou max_speed > 400 são rejeitados | `pytest tests/ -k gold -v` |
| 4.3 | Adicionar SLA por tabela no endpoint (`/api/pipeline_execution/sla/tables`) | `grep 'sla/tables' src/web/routers/sla.py` |
| Gate | `pytest tests/ -k sla -v` passa + freshness retorna valor dinâmico | Testes de SLA |

---

### Fase 5 — CI/CD Hardening (T2)
**Skills:** `verification-workflow-designer`
**Agentes:** Nenhum (edições de arquivo YAML)

| Step | Ação | Verificação |
|------|------|-------------|
| 5.1 | Adicionar `--cov=src --cov-report=term-missing --cov-fail-under=60` ao CI (`ci.yml` step "Run tests") | `grep 'cov-fail-under' .github/workflows/ci.yml` |
| 5.2 | Adicionar job `security` no CI com Bandit + Safety | `grep 'bandit\|safety' .github/workflows/ci.yml` |
| 5.3 | Criar `make validate` (lint + test + security + coverage). Criar `make security` (detect-secrets + bandit + safety). Fallback se `act` não disponível: `make validate --dry-run` | `make validate --dry-run` → executa lint, test, security |
| Gate | CI passa em execução local (ou dry-run) | `make validate` ou `make validate --dry-run` |

---

### Fase 6 — Verificação Final (T2)
**Skills:** `completion-auditor`
**Agentes:** domain/completion-auditor

| Step | Ação | Verificação |
|------|------|-------------|
| 6.1 | Rodar suite completa: `pytest tests/ --cov=src --cov-report=term-missing` | 138+ tests passing, coverage report |
| 6.2 | Rodar `make validate` | Saída limpa |
| 6.3 | Executar `pre-commit run --all-files` | Todos os hooks passam |
| 6.4 | Verificar `external_directory` restrito: `jq '.permissions.external_directory[]' ~/.config/opencode/opencode.jsonc \| grep -vE '^\"/|~'` → vazio (nenhum catch-all) | Comando jq |
| 6.5 | Verificar legacy artifacts arquivados | `ls ~/.claude/` → vazio; `ls ~/.agents/` → vazio; `ls ~/.opencode/_archive/` → populado |
| 6.6 | Escrever handoff: `docs/session-handoffs/2026-06-18_f1-018-hardening.md` | `ls docs/session-handoffs/ \| grep f1-018` |
| Gate | Auditoria de completude (Roberto) | Revisão final |

---

## 6. Rollback

| Componente | Rollback |
|------------|----------|
| Constituição enxuta | Reverter `instructions` no `opencode.jsonc` para apontar `opencode.md` original |
| Skills removidas | Restaurar de `~/.opencode/_archive/skills/` para `~/.opencode/skills/` |
| Agents removidos | Restaurar de `~/.opencode/_archive/agents/` para `~/.opencode/agents/` |
| Legacy artifacts | Restaurar de `~/.opencode/_archive/` para `~/.claude/` e `~/.agents/` |
| Detect-secrets | Reverter `.pre-commit-config.yaml` + deletar `.secrets.baseline` |
| Pipe-to-shell deny rules | Reverter `~/.config/opencode/opencode.jsonc` permissions.bash |
| external_directory | Reverter `~/.config/opencode/opencode.jsonc` permissions.external_directory |
| CI/CD changes | Reverter `.github/workflows/` via git |
| Pipeline freshness | Reverter `process.py` e `assets.py` via git |

**Nota:** `~/.config/opencode/opencode.jsonc` não está no git. Backup manual antes de editar: `cp ~/.config/opencode/opencode.jsonc ~/.config/opencode/opencode.jsonc.bak.$(date +%Y%m%d)`

---

## 7. Riscos

| Risco | Probabilidade | Impacto | Mitigação |
|-------|--------------|---------|-----------|
| Remover skill que estava sendo usada indiretamente | Baixa | Médio | Mover para archive, não deletar. Restaurável em 1 comando |
| Constituição enxuta não cobre caso de uso | Média | Alto | Skill `extended-constitution` carrega texto completo sob demanda |
| Duas camadas de constituição divergem | Média | Médio | Regra de precedência documentada: `opencode-core.md` > `extended-constitution` |
| CI security scanning gera alertas falsos | Alta | Baixo | Baseline + allowlist mantidos no repositório |
| Freshness com Bronze vazio retorna erro | Baixa | Médio | Guard clause: se Bronze vazio, freshness = None (não quebra pipeline) |
| `act` não disponível para CI gate | Média | Baixo | Fallback: `make validate --dry-run` |
| `~/.config/opencode/opencode.md` não existe | Média | Alto | Verificar antes da Fase 2; se ausente, recriar a partir de `.bak` |
| Config global editada sem backup | Baixa | Alto | Step obrigatório de backup antes de editar `opencode.jsonc` |

---

## 8. Critérios de Aceite

- [ ] `pytest tests/` — 138+ tests passando, 0 failures
- [ ] `pre-commit run --all-files` — todos os hooks passam
- [ ] `~/.config/opencode/opencode.jsonc` — sem `**` catch-all em `external_directory`
- [ ] `~/.config/opencode/opencode.jsonc` — deny rules para pipe-to-shell ativas
- [ ] `.github/workflows/ci.yml` — `--cov-fail-under=60` ativo + job security
- [ ] `make validate` — executa lint + test + security + coverage
- [ ] `~/.opencode/skills/` — ≤ 20 skills
- [ ] `~/.opencode/agents/` — ≤ 12 agents (core + domain)
- [ ] `~/.claude/` e `~/.agents/` — arquivados em `~/.opencode/_archive/`
- [ ] Constituição enxuta `~/.opencode/opencode-core.md` — ≤ 250 linhas
- [ ] Phantom skills removidas da constituição
- [ ] `data_freshness_minutes` — retorna valor dinâmico (curl + assert)
- [ ] `.env.example` — presente no root do projeto
- [ ] ADR-011 — salvo em `docs/adr/`
- [ ] Handoff final — salvo em `docs/session-handoffs/`
- [ ] Freshness tem guard clause para Bronze vazio (retorna None)

---

## 9. Dependências

- **Pré-requisito:** F1-016 e F1-017 concluídos ✓
- **Ferramentas:** `detect-secrets`, `bandit`, `safety` (instalar via pip); `jq` (verificar `which jq`); `act` (opcional — fallback `make validate --dry-run`)
- **Config global:** `~/.config/opencode/opencode.jsonc` — backup antes de editar
- **Próximo:** F1-019 (coverage target 60%, testes de integração)

---

### ◈ Processing Context

- **Lead Agent:** OpenCode Chief Engineer
- **Supporting Agents:** domain/security-reviewer, domain/data-engineer, domain/devops-release-engineer, domain/documentation-curator, domain/test-engineer (5-agent council), domain/adversarial-reviewer (1ª rodada adversarial), domain/completion-auditor (auditoria de completude)
- **Commands/Subagents Used:** `skill` (write-implementation-plan, adversarial-review, completion-auditor), `task` (7 agent invocations)
- **Knowledge Sources:** Relatórios dos 5 domain agents, revisão adversarial, auditoria de completude, `docs/plans/017_harness_openf1_unificacao_governanca.md`, `~/.opencode/opencode.md`, `AGENTS.md`, `docs/PROJECT_PROFILE.md`, `.pre-commit-config.yaml`, `Makefile`, `.github/workflows/`, `src/ingestion/process.py`, `src/ingestion/assets.py`, `src/web/routers/sla.py`, `~/.config/opencode/opencode.jsonc`
- **Files Analyzed:** 20+ arquivos (via agentes e leitura direta)
- **Task Level:** T3 (plano multi-domínio, 6 fases, 30+ steps)
- **Validations:** Scores de 5 domínios, adversarial review, completion audit, verificação de claims contra código real
- **Not Executed:** Implementação (build mode iniciado após aprovação de Roberto)
