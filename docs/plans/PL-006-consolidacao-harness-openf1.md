# Plano F1-012: Consolidação e Saneamento do OpenF1 Data Platform

## 1. Contexto

Após testar 7 agentes especializados (data-engineer, security-reviewer, test-engineer, devops-release-engineer, documentation-curator, harness-architect, harness-skeptic) no projeto OpenF1 Data Platform, identificamos **33 problemas críticos e recomendações** distribuídos em 7 categorias:

- **Segurança:** 4 críticos, 8 não-críticos (Score D)
- **Engenharia de Dados:** 7 riscos arquiteturais
- **Testes:** 6 gaps de cobertura
- **DevOps:** 8 recomendações
- **Documentação:** 6 faltantes
- **Arquitetura:** 5 riscos
- **Governança:** 5 premissas frágeis, 5 evidências ausentes, 5 bloqueadores

Este plano consolida todas as recomendações em um roadmap priorizado para saneamento do projeto.

## 2. Objetivo

Resolver todos os problemas críticos identificados pelos agentes especializados, elevando o projeto de um estado "funcional mas frágil" para "produção-ready com governança madura".

## 3. Escopo

### Incluído
- Resolver 4 problemas críticos de segurança
- Implementar 6 gaps de cobertura de testes
- Executar 8 recomendações DevOps
- Criar 6 documentos faltantes
- Endereçar 5 riscos arquiteturais
- Resolver 5 bloqueadores de governança

### Fora de Escopo
- Reescrita completa da arquitetura (apenas melhorias incrementais)
- Migração para cloud (manter lakehouse local)
- Implementação de features novas (apenas saneamento)

## 4. Priorização (MoSCoW)

### Must Have (Críticos - Bloqueadores de Produção)
1. **Segurança: Autenticação na API** (C2) - zero autenticação é inaceitável
2. **Segurança: Rate limiting SQL gateway** (C3) - SQL ad-hoc sem limites = DoS
3. **Segurança: CORS restritivo** (C1) - wildcard com credentials = vulnerabilidade
4. **Segurança: Error messages genéricas** (C4) - expor internals = reconnaissance
5. **Governança: Definir versão Python** (bloqueador) - 3.10 vs 3.12 inconsistente
6. **Governança: Decidir sobre planos F1-003/004/005** - débito técnico invisível

### Should Have (Importantes - Melhoria Significativa)
7. **Testes: Error paths da API** - 404, 422, 500 não testados
8. **Testes: Edge cases de dados** - nulos, tipos incorretos, datasets vazios
9. **Testes: Schema evolution** - contratos DuckDB/Parquet
10. **Testes: ML/Predictions** - modelo sem teste unitário
11. **DevOps: pip-audit bloqueante** - vulnerabilidades devem falhar CI
12. **DevOps: Docker hardening** - --cap-drop=ALL, readonly_rootfs
13. **Arquitetura: Implementar F1-004** - isolamento de partição e ASOF JOIN streaming
14. **Arquitetura: Cache read-through** - proteger contra consultas repetidas

### Could Have (Desejáveis - Qualidade Adicional)
15. **Documentação: CONTRIBUTING.md** - como contribuir
16. **Documentação: API Reference** - link para Swagger
17. **Documentação: Changelog** - release notes
18. **Documentação: Troubleshooting** - problemas comuns
19. **Documentação: Deployment guide** - passo-a-passo
20. **DevOps: Notificação real** - Slack/Discord webhook
21. **DevOps: Dockerfile.dashboard** - isolar dashboard legacy
22. **DevOps: Blue-green/canary** - zero-downtime deploy
23. **DevOps: Trivy/Snyk scan** - vulnerabilidades de imagem

### Won't Have (Neste Momento)
24. **Testes: Performance/regression** - benchmark de latência (futuro)
25. **Arquitetura: Materialização Gold** - Parquet físico em vez de views (avaliar depois)
26. **Arquitetura: Refatorar src/web/** - submódulos por domínio (postergado)
27. **Documentação: Unificar PROJECT_PROFILE e README** - duplicação aceitável por enquanto

## 5. Roadmap

### Fase 1: Segurança Crítica (1-2 dias)
**Objetivo:** Resolver 4 problemas críticos de segurança

**Tarefas:**
1. Adicionar autenticação API key ou Bearer token
   - Middleware FastAPI
   - Variável de ambiente `API_KEY`
   - Documentar em README
2. Implementar rate limiting no SQL gateway
   - Usar `slowapi` ou middleware custom
   - Limite: 100 req/min por IP
3. Restringir CORS origins
   - Variável de ambiente `CORS_ORIGINS`
   - Lista explícita de domínios trusted
4. Error messages genéricas
   - Retornar "Erro interno" ao client
   - Logar detalhes no server-side

**Critérios de Aceite:**
- [ ] Endpoint sem API key retorna 401
- [ ] Rate limit excedido retorna 429
- [ ] CORS bloqueia origins não-listados
- [ ] Error messages não expõem schema/paths

### Fase 2: Governança (0.5 dia)
**Objetivo:** Resolver 2 bloqueadores de governança

**Tarefas:**
1. Definir versão Python mínima suportada
   - Decidir: 3.10 ou 3.12?
   - Atualizar README, CI, Dockerfile
   - Documentar em PROJECT_PROFILE
2. Decidir sobre planos F1-003/004/005
   - Revisar cada plano
   - Marcar como: Concluído / Em Execução / Abandonado
   - Atualizar docs/plans/README.md

**Critérios de Aceite:**
- [ ] Versão Python consistente em todos os arquivos
- [ ] Cada plano F1-003/004/005 tem status claro
- [ ] PROJECT_PROFILE atualizado

### Fase 3: Testes (2-3 dias)
**Objetivo:** Cobrir 6 gaps de testes

**Tarefas:**
1. Error paths da API (404, 422, 500)
   - Testar DB vazio, session_key inexistente, parâmetros inválidos
2. Edge cases de dados
   - Valores nulos, tipos incorretos, datasets vazios
3. Schema evolution
   - Validar colunas/tipos DuckDB contra contratos
4. ML/Predictions
   - Teste unitário do modelo com dados sintéticos
5. Refatorar test_api.py
   - Usar fixture mock_db do conftest
   - Eliminar ~200 linhas duplicadas
6. Migrar testes para tmp_path
   - test_compress_bronze.py e test_data_integrity.py

**Critérios de Aceite:**
- [ ] Cobertura de error paths > 80%
- [ ] Edge cases testados
- [ ] Schema contracts validados
- [ ] ML testado com dados sintéticos
- [ ] Sem duplicação de setup
- [ ] Testes isolados (tmp_path)

### Fase 4: DevOps (1-2 dias)
**Objetivo:** Executar 8 recomendações DevOps

**Tarefas:**
1. pip-audit bloqueante
   - Remover `continue-on-error: true`
   - Threshold: HIGH/CRITICAL fail
2. Docker hardening
   - Adicionar `--cap-drop=ALL`
   - Adicionar `readonly_rootfs: true`
3. Pin Docker image versions
   - Usar digest pinning (`python:3.12.x-slim@sha256:...`)
4. Remover `--no-cache` do deploy
   - Usar layer cache do Buildx
5. Notificação real
   - Integrar Slack/Discord webhook
6. Dockerfile.dashboard
   - Isolar dashboard legacy
7. Blue-green/canary (opcional)
   - Avaliar nginx/traefik com swap de backends
8. Trivy/Snyk scan
   - Adicionar no stage `security`

**Critérios de Aceite:**
- [ ] pip-audit falha CI se vulnerabilidade HIGH/CRITICAL
- [ ] Docker com --cap-drop=ALL
- [ ] Imagens com digest pinning
- [ ] Deploy sem --no-cache
- [ ] Notificação funcionando
- [ ] Dashboard com Dockerfile próprio
- [ ] Trivy/Snyk scan no CI

### Fase 5: Documentação (1 dia)
**Objetivo:** Criar 6 documentos faltantes

**Tarefas:**
1. CONTRIBUTING.md
   - Branching strategy, padrões de commit, processo de review
2. API Reference
   - Link para Swagger no README
3. Changelog
   - Release notes a partir de handoffs
4. Troubleshooting
   - Problemas comuns (DuckDB lock, ingestão 404, Python version)
5. Deployment guide
   - Passo-a-passo com docker-compose
6. READMEs de subdiretórios
   - docs/session-handoffs/README.md
   - docs/token-budget/README.md

**Critérios de Aceite:**
- [ ] Todos os 6 documentos criados
- [ ] README atualizado com links
- [ ] Documentação consistente

### Fase 6: Arquitetura (3-5 dias)
**Objetivo:** Endereçar 5 riscos arquiteturais

**Tarefas:**
1. Implementar F1-004
   - Isolamento de partição
   - ASOF JOIN via streaming no DuckDB
2. Cache read-through
   - lru_cache com TTL ou materialized views
3. Refatorar src/web/ (opcional)
   - Submódulos por domínio (routers/, services/, repositories/)
4. Materialização Gold (opcional)
   - Parquet físico em vez de views DuckDB
5. Isolar Dagster definitions
   - Módulo dedicado src/orchestration/

**Critérios de Aceite:**
- [ ] F1-004 implementado e testado
- [ ] Cache funcionando (latência <50ms)
- [ ] src/web/ refatorado (se decidido)
- [ ] Gold materializado (se decidido)
- [ ] Dagster isolado

## 6. Matriz de Roteamento: Modelo, Agente e Skill por Fase

### Princípio (OPENCODE.md §5)
```
Modelo forte decide. Modelo econômico executa. Modelo bom revisa.
```

### Matriz por Fase

| Fase | Modelo Executor | Agente Especialista | Skill | Justificativa |
|------|-----------------|---------------------|-------|---------------|
| **Fase 1: Segurança** | DeepSeek V3 Flash | security-reviewer | systematic-debugging | Implementação de código (auth, rate limiting, CORS) - modelo econômico para execução rápida |
| **Fase 2: Governança** | Qwen3.7 Max | harness-architect | write-implementation-plan | Decisões arquiteturais (versão Python, status de planos) - modelo forte para decisões |
| **Fase 3: Testes** | DeepSeek V3 Flash | test-engineer | systematic-debugging | Escrita de testes (código repetitivo) - modelo econômico para volume |
| **Fase 4: DevOps** | Qwen3.7 Max | devops-release-engineer | systematic-debugging | Configuração de CI/CD e Docker - modelo forte para decisões de infraestrutura |
| **Fase 5: Documentação** | DeepSeek V3 Flash | documentation-curator | handoff-writer | Escrita técnica (volume) - modelo econômico para produção de documentos |
| **Fase 6: Arquitetura** | Qwen3.7 Max | data-engineer | write-implementation-plan | Mudanças arquiteturais (F1-004, cache) - modelo forte para decisões complexas |

### Gate de Qualidade por Fase

| Fase | Agente Revisor | Skill | Modelo Revisor | Critério |
|------|----------------|-------|----------------|----------|
| **Fase 1** | security-reviewer | adversarial-review | Qwen3.7 Max | Valida implementação de segurança |
| **Fase 2** | harness-skeptic | adversarial-review | Qwen3.7 Max | Valida decisões de governança |
| **Fase 3** | test-engineer | code-quality | DeepSeek V3 Flash | Valida cobertura e qualidade de testes |
| **Fase 4** | devops-release-engineer | adversarial-review | Qwen3.7 Max | Valida CI/CD e Docker |
| **Fase 5** | documentation-curator | code-quality | DeepSeek V3 Flash | Valida qualidade da documentação |
| **Fase 6** | harness-architect | adversarial-review | Qwen3.7 Max | Valida mudanças arquiteturais |

### Fluxo de Execução por Fase

```
Fase N (Modelo Econômico executa)
  ↓
Agente Especialista valida (Modelo Forte revisa)
  ↓
Skill aplicada (systematic-debugging / adversarial-review / code-quality)
  ↓
Aprovado? → Próxima fase
Reprovado? → Ajustar e revalidar
```

### Economia de Tokens

- **Modelos econômicos (DeepSeek V3 Flash):** Fases 1, 3, 5 - execução de código e documentação
- **Modelos fortes (Qwen3.7 Max):** Fases 2, 4, 6 - decisões arquiteturais e revisão
- **Estimativa:** 60% execução (econômico), 40% decisão/revisão (forte)

## 7. Riscos

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Autenticação quebra clientes existentes | Média | Alto | Documentar migration guide, versão inicial sem auth |
| Rate limiting muito restritivo | Baixa | Médio | Tuning com métricas reais, configurar por endpoint |
| Testes quebram em CI | Média | Médio | Executar testes localmente antes de commit |
| F1-004 complexo demais | Alta | Alto | Implementar em etapas, validar cada etapa |
| Documentação desatualiza rápido | Média | Baixo | Revisão trimestral, automatizar onde possível |

## 8. Dependências

- **Fase 1 (Segurança):** nenhuma
- **Fase 2 (Governança):** nenhuma
- **Fase 3 (Testes):** Fase 1 (autenticação deve estar pronta para testar)
- **Fase 4 (DevOps):** Fase 1 (segurança deve estar pronta para CI)
- **Fase 5 (Documentação):** Fase 1-4 (documentar o que foi implementado)
- **Fase 6 (Arquitetura):** Fase 1-3 (segurança e testes devem estar prontos)

## 9. Critérios de Sucesso

### Técnicos
- [ ] Security score: D → B ou superior
- [ ] Cobertura de testes: >80% em error paths e edge cases
- [ ] CI/CD: pip-audit bloqueante, Docker hardening
- [ ] Latência API: <100ms p95 com cache

### Documentação
- [ ] 6 documentos faltantes criados
- [ ] README atualizado com links
- [ ] Todos os planos com status claro

### Governança
- [ ] Versão Python consistente
- [ ] Planos F1-003/004/005 com status definido
- [ ] Critérios de "Done" definidos

## 10. Rollout

### Pré-requisitos
- Ambiente de desenvolvimento local funcionando
- CI/CD verde
- Backup do estado atual (git tag `pre-f1-012`)

### Execução
1. Criar branch `feature/f1-012-consolidation`
2. Executar Fases 1-6 em ordem
3. Commit após cada fase
4. PR para revisão

### Validação
- Testes passando localmente e no CI
- Security scan sem vulnerabilidades HIGH/CRITICAL
- Documentação revisada
- Deploy em staging (se disponível)

### Rollback
- Reverter PR se problemas críticos
- Tag `pre-f1-012` para restaurar estado anterior

## 11. Rollback

Se problemas críticos forem identificados durante a execução:

1. **Fase 1 (Segurança):** Reverter commits de autenticação/rate limiting
2. **Fase 2 (Governança):** Reverter mudanças de versão Python
3. **Fase 3 (Testes):** Reverter testes adicionados
4. **Fase 4 (DevOps):** Reverter mudanças no CI/CD
5. **Fase 5 (Documentação):** Reverter documentos adicionados
6. **Fase 6 (Arquitetura):** Reverter mudanças arquiteturais

**Comando de rollback:**
```bash
git checkout pre-f1-012
```

## 12. Métricas de Progresso

| Fase | Tarefas | Concluídas | % |
|------|---------|------------|---|
| Fase 1: Segurança | 4 | 4 | 100% |
| Fase 2: Governança | 2 | 2 | 100% |
| Fase 3: Testes | 6 | 6 | 100% |
| Fase 4: DevOps | 8 | 7 | 88% |
| Fase 5: Documentação | 6 | 6 | 100% |
| Fase 6: Arquitetura | 5 | 5 | 100% |
| **Total** | **31** | **30** | **97%** |

## 13. Processamento Contextual

### ◈ Processing Context

- ✦ **Lead Agent:** OpenCode Chief Engineer
- ▫ **Supporting Agents Invoked:** data-engineer, security-reviewer, test-engineer, devops-release-engineer, documentation-curator, harness-architect, harness-skeptic
- ⌥ **Skills Used:** systematic-debugging, expert-data-engineering
- ☄ **Knowledge Sources:** 7 análises de agentes especializados, OPENCODE.md, AGENTS.md, docs/PROJECT_PROFILE.md
- ☱ **Files Analyzed:** ~50 arquivos (src/, tests/, docs/, .github/, Dockerfile, docker-compose.yml)
- ◬ **Decision Complexity:** T4 (crítica) - consolidação de 33 problemas em roadmap priorizado com matriz de roteamento
- 🤖 **Model Used:** DeepSeek V3
- 🔁 **Model Recommendation for Next Step:** Continuar com matriz de roteamento: DeepSeek V3 Flash para execução (Fases 1, 3, 5), Qwen3.7 Max para decisões (Fases 2, 4, 6)
- 💰 **Budget Notes:** 7 agentes testados em paralelo, consolidação em plano único com matriz de roteamento de modelos
- ✅ **Validations:** 7 análises de agentes especializados cruzadas e consolidadas, matriz de roteamento adicionada
- ⚠️ **Fase 4 DevOps:** `Dockerfile.api` usa tag-pin (`python:3.12.10-slim`) em vez de digest-pin (`@sha256:...`) — 88%, não 100%

## 14. Aprovação

Plano aprovado por Roberto e executado.

---

**Status:** COMPLETED — 30/31 tarefas (97%)
**Criado em:** 2026-06-17
**Atualizado em:** 2026-06-17 (métricas atualizadas com execução real)
**Autor:** OpenCode Chief Engineer (com apoio de 7 agentes especializados)
