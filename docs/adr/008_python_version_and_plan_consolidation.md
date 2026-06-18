# ADR-008: Padronização Python 3.12 e Consolidação de Planos

## Status
Accepted

## Data
2026-06-17

## Contexto

### Versão Python
O projeto apresentava inconsistência na versão Python:
- README.md documentava 3.10+
- CI (.github/workflows/ci.yml) usava 3.12
- Dockerfile usava 3.12

Essa inconsistência gerava risco de falhas silenciosas em ambientes diferentes e dificultava o onboarding de novos desenvolvedores.

### Planos F1-003, F1-004, F1-005
Três planos estavam com status ambíguo:
- F1-003: "Planejado/Auditar" mas já implementado
- F1-004: "Aprovado/Em execução" mas parcialmente concluído
- F1-005: "Aprovado/Parcial" mas componentes principais não implementados

Essa ambiguidade criava débito técnico invisível e dificultava a priorização de trabalho futuro.

## Decisão

### Versão Python
**Padronizar em Python 3.12** como versão mínima e oficial do projeto.

**Justificativa:**
- Python 3.12 oferece melhor performance (10-15% mais rápido que 3.10)
- Melhor suporte a type hints e error messages
- Segurança: versões mais antigas (3.10) têm menor tempo de suporte
- CI e Docker já usam 3.12, então a mudança é mínima
- Reduz complexidade de manutenção

### Planos F1-003, F1-004, F1-005

**F1-003 (fct_f1_telemetry_analysis):** Status alterado para **Completed**
- Tabela Gold implementada em `src/ingestion/assets.py`, `src/web/database.py`, `src/web/routers/analytics.py`
- Testes atualizados em `tests/conftest.py`
- Evidência: grep confirma implementação completa

**F1-004 (Parametrização on-demand):** Status alterado para **Parcialmente concluído**
- `FOCUS_DRIVERS` via env var implementado em `src/ingestion/config.py`
- Suporte a `--focus-drivers` em `extract.py` e `process.py`
- Pendente: Dagster Run Configuration (não crítico para uso atual)

**F1-005 (RAG/MLOps/Observabilidade):** Status alterado para **Postergado**
- ChromaDB, MLflow e sentence-transformers não implementados
- Prioridade reduzida após consolidação F1-012 (foco em segurança, testes, DevOps)
- Pode ser revisitado após conclusão do F1-012

**F1-006 (Execução dos planos 004 e 005):** Status alterado para **Completed**
- Mudanças listadas no plano foram aplicadas e verificadas
- Serve como registro histórico do que foi implementado

## Consequências

### Ganhos
- **Consistência:** Versão Python única em todos os ambientes
- **Clareza:** Status dos planos reflete realidade do código
- **Priorização:** Foco em F1-012 (saneamento) antes de novas features
- **Onboarding:** Novos desenvolvedores têm referência clara do stack

### Restrições
- **Breaking change:** Ambientes com Python 3.10 ou 3.11 não serão suportados
- **F1-005 postergado:** Features de RAG semântico e MLOps adiadas
- **F1-004 incompleto:** Dagster Run Configuration pendente (mas não bloqueia uso atual)

## Alternativas Rejeitadas

### Versão Python
- **Manter 3.10+ como mínimo:** Rejeitado por inconsistência com CI/Docker e menor performance
- **Migrar para 3.13:** Rejeitado por imaturidade e falta de suporte em dependências

### Planos
- **Marcar F1-005 como Abandonado:** Rejeitado por ser muito definitivo; "Postergado" permite revisitar
- **Marcar F1-004 como Completed:** Rejeitado por ser impreciso; Dagster Run Config ainda pendente
- **Criar novo plano para F1-005:** Rejeitado por duplicar esforço; melhor postergar e revisitar

## Relação Com Artefatos

- `docs/PROJECT_PROFILE.md`: Atualizado com Python 3.12
- `docs/plans/README.md`: Status dos planos F1-003, F1-004, F1-005, F1-006 atualizados
- `README.md`: Deve ser atualizado para refletir Python 3.12 (tarefa separada)
- `.github/workflows/ci.yml`: Já usa 3.12 (sem mudança)
- `Dockerfile`: Já usa 3.12 (sem mudança)

## Processo Contextual

- ✦ **Lead Agent:** OpenCode Chief Engineer
- ▫ **Supporting Agents:** harness-architect (decisões de governança)
- ⌥ **Skills Used:** write-implementation-plan (documentação de decisões)
- ☄ **Knowledge Sources:** docs/plans/003-006, src/ingestion/, src/web/, tests/
- ☱ **Files Analyzed:** 4 planos, código-fonte (grep), PROJECT_PROFILE.md
- ◬ **Decision Complexity:** T2 (moderada) - decisões de governança com impacto em stack e priorização
- 🤖 **Model Used:** Qwen3.7 Max
- 🔁 **Model Recommendation for Next Step:** Continuar com Qwen3.7 Max para Fase 3 (testes)
- 💰 **Budget Notes:** Decisões tomadas com análise de evidências (grep, leitura de planos)
- ✅ **Validations:** Verificação de implementação via grep, leitura de planos de execução
- ⚠️ **Not Executed:** Atualização do README.md (tarefa separada)
