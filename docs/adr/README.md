# 📓 Registro de Decisões de Arquitetura (Architectural Decision Records - ADR)

Este diretório contém os registros formais de todas as decisões arquiteturais tomadas durante o design e implementação da **OpenF1 Data Platform**. 

Cada arquivo segue o padrão de mercado de **ADR (Nygard format)**, registrando o contexto do problema, a decisão tomada, os motivos de escolha, alternativas consideradas e as consequências (trade-offs). Isso serve como a memória técnica do projeto, garantindo que o design permaneça íntegro ao longo do tempo.

---

## 📋 Índice de Decisões (ADRs)

| ID | Título | Status | Data | Descrição Simplificada |
|---|---|---|---|---|
| **[ADR-001](file:///media/Arquivos/Engenharia%20TI%202026/openf1-data-platform/docs/adr/adr-001-duckdb-olap-local.md)** | [Seleção do DuckDB como Motor OLAP Local](file:///media/Arquivos/Engenharia%20TI%202026/openf1-data-platform/docs/adr/adr-001-duckdb-olap-local.md) | **Accepted** | 2026-06-09 | Uso do DuckDB embutido de baixo custo em substituição a bancos de dados na nuvem. |
| **[ADR-002](file:///media/Arquivos/Engenharia%20TI%202026/openf1-data-platform/docs/adr/adr-002-ingestao-concorrente.md)** | [Ingestão Concorrente Segmentada por Piloto](file:///media/Arquivos/Engenharia%20TI%202026/openf1-data-platform/docs/adr/adr-002-ingestao-concorrente.md) | **Accepted** | 2026-06-09 | Paralelismo na extração para mitigar timeouts de telemetria massiva na API. |
| **[ADR-003](file:///media/Arquivos/Engenharia%20TI%202026/openf1-data-platform/docs/adr/adr-003-fastapi-async-duckdb.md)** | [FastAPI Assíncrono com Delegamento de Threads OLAP](file:///media/Arquivos/Engenharia%20TI%202026/openf1-data-platform/docs/adr/adr-003-fastapi-async-duckdb.md) | **Accepted** | 2026-06-09 | Uso de `asyncio.to_thread` para consultas no DuckDB para evitar travamento do servidor. |
| **[ADR-004](file:///media/Arquivos/Engenharia%20TI%202026/openf1-data-platform/docs/adr/adr-004-data-contracts-quarantine.md)** | [Contratos de Dados (Pydantic) e Quarentena](file:///media/Arquivos/Engenharia%20TI%202026/openf1-data-platform/docs/adr/adr-004-data-contracts-quarantine.md) | **Accepted** | 2026-06-09 | Validação de schemas na fronteira Bronze -> Silver para evitar corrupção silenciosa. |
| **[ADR-005](file:///media/Arquivos/Engenharia%20TI%202026/openf1-data-platform/docs/adr/adr-005-ia-hibrida-text-to-sql.md)** | [Arquitetura Híbrida de Inteligência Artificial](file:///media/Arquivos/Engenharia%20TI%202026/openf1-data-platform/docs/adr/adr-005-ia-hibrida-text-to-sql.md) | **Accepted** | 2026-06-09 | Uso de RAG apenas para texto e Text-to-SQL sobre DuckDB para garantir precisão matemática. |
| **[ADR-006](file:///media/Arquivos/Engenharia%20TI%202026/openf1-data-platform/docs/adr/adr-006-parametrizacao-ingestao-demand.md)** | [Parametrização da Ingestão de Dados e Ingestão sob Demanda](file:///media/Arquivos/Engenharia%20TI%202026/openf1-data-platform/docs/adr/adr-006-parametrizacao-ingestao-demand.md) | **Accepted** | 2026-06-14 | Flexibilização do escopo do pipeline para pilotos e GPs dinâmicos com particionamento Hive local. |
| **[ADR-007](file:///media/Arquivos/Engenharia%20TI%202026/openf1-data-platform/docs/adr/adr-007-governanca-agentes-subagentes.md)** | [Governança de Agentes, Subagentes e Qualidade de Planos](file:///media/Arquivos/Engenharia%20TI%202026/openf1-data-platform/docs/adr/adr-007-governanca-agentes-subagentes.md) | **Accepted** | 2026-06-16 | Padronização de uso de agentes, subagentes, handoffs, notas obrigatórias e rastreabilidade entre planos, ADRs e perfil do projeto. |
| **[ADR-008](file:///media/Arquivos/Engenharia%20TI%202026/openf1-data-platform/docs/adr/008_python_version_and_plan_consolidation.md)** | [Padronização Python 3.12 e Consolidação de Planos](file:///media/Arquivos/Engenharia%20TI%202026/openf1-data-platform/docs/adr/008_python_version_and_plan_consolidation.md) | **Accepted** | 2026-06-17 | Padronização da versão Python para 3.12 e consolidação do status dos planos F1-003 a F1-006. |
| **[ADR-009](adr-009-f1-015-consolidacao-saneamento.md)** | [Consolidação e Saneamento F1-015](adr-009-f1-015-consolidacao-saneamento.md) | **Accepted** | 2026-06-18 | Consolidação do plano F1-015. |
| **[ADR-010](adr-010-runtime-governance.md)** | [Runtime Governance](adr-010-runtime-governance.md) | **Accepted** | 2026-06-18 | Runtime Governance como camada nativa. |
| **[ADR-011](adr-011-harness-reduction.md)** | [Redução do Harness](adr-011-harness-reduction.md) | **Accepted** | 2026-06-18 | Redução de 41 para 18 skills, 35 para 20 agents. |
| **[ADR-012](adr-012-model-escalation-fallback.md)** | [Model Escalation & Fallback Automático](adr-012-model-escalation-fallback.md) | **Accepted** | 2026-06-18 | Cadeia deepseek Free → mimo pago com gatilho automático por timeout. |

---

## 🛠️ Por que documentamos as decisões?

Na engenharia de software sênior, **o código nos diz *como* o sistema funciona, mas a documentação arquitetural nos diz *por que* ele funciona assim**. 

Ao registrar as decisões, garantimos:
1. **Redução de Atrito no Onboarding:** Desenvolvedores e tech leads entendem imediatamente os trade-offs e restrições técnicas adotados ao clonar o repositório.
2. **Prevenção de Regressões de Design:** Impede que modificações futuras destruam escolhas críticas por falta de contexto (ex: alterar a conexão do DuckDB para leitura/escrita no FastAPI, expondo o banco a SQL Injection).
3. **Padrão Corporativo Real:** Demonstra maturidade técnica alinhada com as melhores práticas de Engenharia de Plataforma e Domain-Driven Design (DDD).
