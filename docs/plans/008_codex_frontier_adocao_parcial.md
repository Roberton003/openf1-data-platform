# Plano de Implementacao 008: Adocao Parcial do Pacote Codex Frontier

## Status E Metadados
- Status: Completed
- Data: 2026-06-17
- Responsavel: Codex (Engenheiro Chefe)
- Complexidade: HIGH
- Decisoes relacionadas: Harness agentic do OpenF1, governanca de skills e subagentes, formato de work package/handoff
- Supersedes: none
- Superseded by: none

## Objetivo E Resultado Esperado
Adotar apenas os conceitos de maior valor do pacote `codex_frontier_agentic_ecosystem_pack` para o OpenF1 Data Platform, sem instalar o pacote completo.

Resultado esperado:
- manter `AGENTS.md` e `docs/PROJECT_PROFILE.md` como fonte de verdade principal;
- evitar duplicacao de governanca, skills e agentes ja cobertos no projeto;
- reaproveitar apenas os conceitos que reduzirem friccao operacional real;
- deixar a adocao completa explicitamente fora de escopo ate nova decisao.

## Contexto E Estado Atual
- O OpenF1 ja possui governanca local forte em `AGENTS.md`, `docs/PROJECT_PROFILE.md`, `docs/plans/README.md`, `docs/adr/README.md` e skill set nativo.
- O pacote frontier propoe 20 skills e 15 agentes especializados, alem de scripts, templates e addendum global.
- O pacote instala por copia direta para `.agents/`, `.codex/`, `scripts/` e templates, com opcao repo-scoped e user-scoped.
- A revisao specialist mostrou ganho marginal baixo para adocao total e risco alto de excesso de governanca.
- O pacote ainda e util como catalogo de formas, mas nao como nova camada normativa para o OpenF1.

## Registro De Decisoes Do Plano
| ID | Decisao | Por Quê | Premissas | Alternativas Rejeitadas | Evidencia | Impacto | Validacao |
|---|---|---|---|---|---|---|---|
| D1 | Nao instalar o pacote completo | O OpenF1 ja cobre bootstrap, planos, ADRs, evidencia e multi-agent orchestration | O ganho incremental do pacote inteiro e baixo | Instalar tudo no repo; instalar globalmente | `AGENTS.md`, `docs/PROJECT_PROFILE.md`, catalogos do pacote | Evita duplicacao e ruido | Manter a decisao se o mapeamento continuar mostrando sobreposicao |
| D2 | Adotar apenas conceitos pontuais traduzidos para o harness atual | O valor esta em formatacao e disciplina operacional, nao em mais taxonomia | Podemos expressar os conceitos com os artefatos atuais | Copiar 20 skills e 15 agentes sem filtro | Scripts/templates do pacote + skills nativas atuais | Baixa custo de manutencao | Validar caso a caso antes de criar novos arquivos |
| D3 | Manter qualquer adocao futura repo-scoped, nunca global por default | Limita raio de influencia e conflitos com o projeto | Se houver algo util, deve viver no OpenF1 primeiro | `install_user_pack.sh` como padrao | `install_repo_pack.sh`, `install_user_pack.sh` | Reversibilidade maior | Se um artefato mover para global, exigir nova decisao |
| D4 | Reaproveitar somente scripts/templates que passarem no filtro de utilidade | Utilitarios pequenos podem melhorar auditoria sem aumentar muito a superficie | Os scripts do pacote sao simples e adaptaveis | Adotar a cadeia completa de autonomia | `audit_frontier_harness.py`, `generate_work_package.py`, `record_handoff.py`, `render_task_router.py` | Pode reduzir friccao em trabalho longo | Rodar verificacao read-only e comparar com os fluxos atuais |

## Evidencias, Premissas E Lacunas
| Tipo | Item | Fonte/Validacao |
|---|---|---|
| VERIFIED | OpenF1 ja tem AGENTS, PROJECT_PROFILE, plans, ADRs, multi-agent orchestration e skills nativas | `AGENTS.md`, `docs/PROJECT_PROFILE.md`, `docs/plans/README.md`, skills locais |
| VERIFIED | O pacote frontier contem 20 skills e 15 agentes, mais scripts, templates e addendum global | `codex_frontier_agentic_ecosystem_pack/.../README.md`, `docs/01_SKILLS_CATALOG.md`, `docs/02_AGENTS_CATALOG.md` |
| VERIFIED | O instalador repo-scoped copia `.agents/`, `.codex/`, `scripts/` e templates para o alvo | `install_repo_pack.sh` |
| VERIFIED | O instalador user-scoped escreve em `~/.agents/skills` e `~/.codex/agents` | `install_user_pack.sh` |
| SOURCED | O playbook do pacote recomenda usar o workflow de fronteira para T4/T5 | `docs/03_ORCHESTRATION_PLAYBOOK.md` |
| SOURCED | Os pareceres dos especialistas convergiram para adocao parcial e rejeicao de instalacao total, copia integral e governanca paralela | Handoffs de Tesla, Mill, Huygens e Descartes |
| PROJECTED | Adocao parcial deve trazer mais valor que adocao total | Releitura do harness atual e parecer dos especialistas |
| ASSUMED | Roberto quer melhorar o harness sem transformar o projeto em um ecossistema agentic pesado | Pedido atual e contexto do projeto |

> Nota de leitura: a crosswalk abaixo foi ajustada para refletir os pareceres
> especialistas mais recentes. O padrao agora e conservador: o pacote serve como
> referencia de forma, nao como nova camada normativa. O que for descartado tem
> apoio explicito de especialistas e skill adequada; o que for mantido tende a
> ser traduzido para capacidades ja existentes no OpenF1.

## Crosswalk De Capabilities

### Legenda De Decisao
- `ABSORVER_NO_HARNESS`: a ideia entra, mas como regra, etapa, fluxo ou contrato usando capacidades já existentes.
- `EXTENSAO_DE_DOMINIO`: a capacidade fica disponível, porém apenas para projetos com esse perfil.
- `JA_EXISTE`: o OpenF1 já cobre isso; manter como base nativa.
- `DESCARTAR`: não entra no harness, porque o custo operacional supera o ganho.

### Skills

| Skill do pacote | Decisao | Como entra no OpenF1 | Base |
|---|---|---|---|
| `frontier-agentic-workflow` | ABSORVER_NO_HARNESS | Absorvido por `AGENTS.md`, `docs/PROJECT_PROFILE.md`, `write-implementation-plan` e `multi-agent-orchestration` | Huygens + Descartes |
| `ambitious-task-router` | ABSORVER_NO_HARNESS | Virar triagem de esforco dentro do bootstrap/plan, nao skill separada | Huygens + Descartes |
| `strategic-supervision-protocol` | ABSORVER_NO_HARNESS | Expressar como regra de Lead Agent e limites de autonomia no harness atual | Huygens |
| `effort-budget-governor` | ABSORVER_NO_HARNESS | Expressar como rubric de complexidade e gates do plano | Descartes |
| `advanced-plan-interrogator` | ABSORVER_NO_HARNESS | Vira etapa de revisao de plano e ADR, nao nova camada permanente | Huygens |
| `goal-driven-execution` | ABSORVER_NO_HARNESS | Absorvido por `write-implementation-plan` e Definition of Done | Huygens |
| `context-over-constraints` | ABSORVER_NO_HARNESS | Absorvido por `project-session-bootstrap` e `engineering-decisions` | Descartes |
| `autonomy-loop-controller` | EXTENSAO_DE_DOMINIO | Manter apenas como opcao para pacotes longos; nao como padrao universal | Huygens |
| `long-running-work-package` | EXTENSAO_DE_DOMINIO | Reutilizar so quando houver trabalho multi-sessao real | Huygens |
| `spec-interrogator` | ABSORVER_NO_HARNESS | Virar etapa de descoberta e refinamento antes do plano | Huygens |
| `prototype-options-generator` | DESCARTAR | Duplicaria o fluxo de plano/ADR e vira subfuncao, nao capacidade de primeira classe | Descartes |
| `verification-workflow-designer` | ABSORVER_NO_HARNESS | Absorvido pelo fluxo de verificacao do OpenF1 e pelo plano formal | Descartes |
| `adversarial-review` | ABSORVER_NO_HARNESS | Virar revisao critica dentro do processo atual, com subagente quando fizer sentido | Descartes |
| `completion-auditor` | ABSORVER_NO_HARNESS | Incorporar ao fechamento de planos e handoffs existentes | Descartes |
| `decision-memory` | ABSORVER_NO_HARNESS | Expressar por handoffs locais, planos e ADRs | Descartes |
| `data-engineering` | EXTENSAO_DE_DOMINIO | Manter como dominio explicito para projetos de dados | Huygens |
| `codex-harness-architect` | JA_EXISTE | Ja existe como skill no ecossistema local e deve continuar como capacidade base | Huygens |
| `project-session-bootstrap` | JA_EXISTE | Ja existe e e transversal a qualquer repositorio | Huygens |
| `write-implementation-plan` | JA_EXISTE | Ja e a via formal do projeto para decisao versionada | Huygens |
| `multi-agent-orchestration` | JA_EXISTE | Ja e a via formal de topologia e handoff | Huygens |

### Agentes

| Agent do pacote | Decisao | Como entra no OpenF1 | Base |
|---|---|---|---|
| `strategic_director` | ABSORVER_NO_HARNESS | Vira o papel de Lead Agent / direcao estrategica, nao novo subagente fixo | Descartes |
| `effort_budget_governor` | ABSORVER_NO_HARNESS | Vira rubric de esforco e budget dentro do planner | Descartes |
| `advanced_plan_interrogator` | ABSORVER_NO_HARNESS | Vira revisor de plano, nao agente sempre ligado | Huygens |
| `goal_architect` | ABSORVER_NO_HARNESS | Vira Definition of Done e framing de objetivo dentro do plano | Huygens |
| `context_engineer` | ABSORVER_NO_HARNESS | Vira bootstrap + engenharia de decisao | Descartes |
| `autonomy_controller` | EXTENSAO_DE_DOMINIO | Apenas para pacotes longos e controlados | Huygens |
| `long_run_operator` | EXTENSAO_DE_DOMINIO | So quando houver work package de longa duracao | Huygens |
| `verification_engineer` | ABSORVER_NO_HARNESS | Vira etapa de verificacao do plano e dos testes do projeto | Descartes |
| `completion_auditor` | ABSORVER_NO_HARNESS | Vira fechamento de tarefa e auditoria de DoD | Descartes |
| `harness_architect` | JA_EXISTE | Ja existe como papel global no ecossistema local | Huygens |
| `harness_skeptic` | JA_EXISTE | Ja existe como papel critico necessario | Descartes |
| `harness_operator` | DESCARTAR | Implementacao de harness deve ficar sob o Codex e plano aprovado, nao como agente permanente | Descartes |
| `data_architect` | EXTENSAO_DE_DOMINIO | Mantido como extensao para projetos de dados | Huygens |
| `pipeline_engineer` | EXTENSAO_DE_DOMINIO | Mantido como extensao para projetos de dados | Huygens |
| `project_explorer` | ABSORVER_NO_HARNESS | Vira bootstrap read-only e mapeamento de repo | Huygens |

### Itens Descartados Com Fundamentacao

| Item | Decisao | Fundamentacao especialista | Skill adequada |
|---|---|---|---|
| Instalar o pacote completo no OpenF1 | DISCARD | Huygens e Descartes convergiram: o ganho marginal e baixo e a manutencao e alta; o pacote vira segunda camada normativa. | `codex-harness-architect`, `engineering-decisions` |
| Instalar globalmente por default | DISCARD | Descartes rejeitou ampliar raio de influencia sem necessidade demonstrada; conflita com reversibilidade e confinamento. | `engineering-decisions` |
| Copiar todos os 20 skills sem filtro | DISCARD | Descartes destacou contexto inflado e selecao artificial sem ganho proporcional. | `multi-agent-orchestration`, `engineering-decisions` |
| Copiar todos os 15 agents sem filtro | DISCARD | Descartes apontou teatro de subagentes e taxonomia paralela sem necessidade comprovada. | `multi-agent-orchestration`, `codex-harness-architect` |
| `install_user_pack.sh` como fluxo padrão | DISCARD | Huygens e Descartes concordaram que o fluxo deve viver no repo e nao no ambiente pessoal. | `engineering-decisions` |
| `playbook` T4/T5 como fluxo padrão para tudo | DISCARD | Descartes rejeitou peso excessivo para o trabalho comum e o risco de sobreprocesso. | `engineering-decisions`, `multi-agent-orchestration` |
| `audit_frontier_harness.py` como gate obrigatório | DISCARD | Descartes aceitou isso apenas como checagem opcional, nao como autoridade do dominio. | `engineering-decisions` |
| `templates/` copiados em massa | DISCARD | Huygens observou que isso replica estrutura sem resolver necessidade especifica. | `codex-harness-architect` |
| `prompt library` generica | DISCARD | O projeto ja tem normas proprias; material generico nao substitui regras versionadas. | `engineering-decisions` |
| Nova governanca paralela para handoffs/autonomia | DISCARD | Duplicaria regras ja existentes em AGENTS, plans e ADRs. | `multi-agent-orchestration`, `engineering-decisions` |
| `prototype-options-generator` como capacidade permanente | DISCARD | Recomendado como subfuncao do plano/ADR, nao como skill independente. | `engineering-decisions` |
| `harness_operator` como agente permanente | DISCARD | A implementacao do harness deve ficar sob o Lead Agent e plano aprovado, nao em uma fila separada de operacao. | `codex-harness-architect`, `engineering-decisions` |

## Premissas Criticas
- O OpenF1 deve continuar com `AGENTS.md` e `docs/PROJECT_PROFILE.md` como camada principal de governanca.
- O pacote frontier nao deve virar uma segunda fonte normativa concorrente.
- Qualquer utilitario reaproveitado precisa ser pequeno, explicitamente justificado e reversivel.
- Se houver conflito entre o pacote e as regras locais, as regras locais vencem.

## Escopo Incluido
- Mapear as 20 skills e 15 agentes do pacote contra as skills e agentes nativos do OpenF1.
- Identificar apenas os conceitos com ganho operacional real.
- Reaproveitar, se aprovado, scripts/templates simples de auditoria, handoff e work package.
- Manter um plano de adocao parcial e rastreavel.

## Fora De Escopo
- Instalar o pacote completo no OpenF1.
- Instalar skills/agentes globalmente por padrao.
- Substituir o harness atual do projeto por uma nova taxonomia.
- Alterar pipeline, schema, API ou dados apenas por causa deste pacote.

## Alternativas Avaliadas E Rejeitadas
- Instalacao completa repo-scoped.
- Instalacao completa global/user-scoped.
- Copia literal de todos os 20 skills e 15 agents.
- Adocao sem mapeamento contra o harness atual.

## Abordagem Escolhida E Justificativa
Adocao parcial e traduzida.

A decisao e manter o OpenF1 como fonte de verdade e importar apenas mecanismos que reduzam atrito operacional real. O pacote frontier e forte como catalogo de principios e formatos, mas o projeto ja possui governanca suficiente para bootstrap, planos, ADRs, memoria e multi-agent orchestration. O melhor retorno vem de absorver o que for util sem duplicar o que ja existe.

## Impacto E Riscos
- Positivo: padroes mais claros para task routing, work package, handoff e verificacao se houver adopcao seletiva.
- Positivo: menor chance de drift em tarefas grandes quando o fluxo estiver bem definido.
- Negativo: qualquer importacao ruim aumenta manutencao e pode duplicar taxonomia.
- Risco: o pacote pode induzir governanca excessiva e consumo operacional sem ganho proporcional.
- Risco: instalar globalmente ampliaria o raio de influencia e o risco de conflito com regras locais.

## Ganhos Locais E Globais
### Ganhos Locais No OpenF1
- Menos duplicacao de governanca: o harness atual absorve o que ja faz sentido, sem criar uma camada paralela.
- Menos carga cognitiva: os rulos viram linguagem operacional simples, nao taxonomia nova.
- Melhor rastreabilidade: cada descarte fica amarrado a justificativa tecnica e skill adequada.
- Melhor retomada: `AGENTS.md`, `PROJECT_PROFILE.md`, planos e handoffs continuam como fonte principal.

### Ganhos Globais Para Outros Projetos
- Um vocabulario comum de decisao para projetos que precisem de orquestracao, sem copiar o pacote inteiro.
- Um padrao reutilizavel de triagem: absorver, estender, manter ou descartar com justificativa.
- Reuso seletivo de `long-running-work-package`, `autonomy_controller` e `data-engineering` quando o contexto pedir.
- Menor risco de levar para outros repositorios uma governanca pesada que nao agrega valor fora de projetos de dados ou tarefas longas.

## Dependencias
- `AGENTS.md`
- `docs/PROJECT_PROFILE.md`
- `docs/plans/README.md`
- `docs/adr/README.md`
- catologo de skills/agentes nativos do OpenF1
- revisao final do Lead Agent antes de qualquer criacao de novos arquivos

## Etapas De Implementacao
### Fase 1: Mapeamento e triagem
- [x] Construir a matriz `frontier skill/agent -> capacidade nativa OpenF1 -> manter/rejeitar`.
- Arquivos: pacote frontier, `AGENTS.md`, `docs/PROJECT_PROFILE.md`, skills nativas.
- Verificacao: lista fechada com candidatos e rejeitados.
- Rollback: n/a.

### Fase 2: Decisao de subconjunto util
- [x] Selecionar somente os conceitos com valor operacional claro.
- Arquivos: este plano.
- Verificacao: decisao assinada pelo Lead Agent.
- Rollback: marcar como `Superseded` se a decisao mudar.

### Fase 3: Prototipacao local, se aprovada
- [x] Reaproveitar apenas scripts/templates que passem no filtro de utilidade.
- Arquivos: `scripts/` e `templates/` do OpenF1, quando aplicavel.
- Verificacao: scripts read-only e sem conflito com o harness atual.
- Rollback: remover os utilitarios adicionados.

### Fase 4: Validacao operacional
- [x] Executar um fluxo representativo com o harness parcial.
- Arquivos: tarefas e docs associados ao fluxo escolhido.
- Verificacao: evidencias, handoff e verificacao final.
- Rollback: voltar ao harness atual do OpenF1 sem perda de funcionalidade.

## Estrategia De Testes
- Validar o mapeamento de capacidades antes de criar arquivos novos.
- Testar scripts read-only antes de qualquer integracao.
- Confirmar que nao ha duplicacao de skills/agentes com o harness existente.

## Observabilidade
- Registrar decisao final em `docs/plans/` e, se duravel, em `docs/adr/`.
- Guardar evidencias de comparacao entre o pacote e o harness atual.

## Rollout E Rollback
- Rollout: repo-scoped, incremental, somente do subconjunto aprovado.
- Rollback: remover utilitarios novos e manter o harness atual intacto.

## Criterios De Aceite
- Nao houve adocao completa do pacote.
- Existe mapeamento claro entre o pacote frontier e as capacidades nativas do OpenF1.
- Qualquer utilitario adotado tem valor operacional demonstrado.
- Nenhuma nova camada global de governanca foi criada sem necessidade.
- A terminologia usada no plano ficou legivel para Roberto e para a manutencao futura.

## Resultado Observado E Revisao
Inventario consolidado:
- 20 capacidades do pacote foram absorvidas no harness atual como regra, etapa, fluxo ou contrato.
- 7 capacidades ficaram como extensao de dominio para projetos de dados ou work packages longos.
- 6 capacidades ja existem nativamente no ecossistema local e permanecem como base.
- 2 capacidades foram descartadas com fundamentacao tecnica especifica.

Leitura pratica:
- no OpenF1, o ganho principal e reduzir duplicacao de governanca e tornar o harness mais legivel;
- em outros projetos, o ganho principal e importar a forma de decisao sem importar o peso total do pacote.
Fase 3 implementada:
- `docs/templates/handoff.md` virou o scaffold canonico de handoff local.
- `scripts/codex/record_handoff.py` gera novos handoffs a partir desse scaffold.
- `scripts/audit_frontier_harness.py`, `scripts/generate_work_package.py`, `scripts/render_task_router.py`, `templates/adr.md`, `templates/autonomy_ledger.md`, `templates/verification_report.md` e `templates/work_package.md` ficaram como referencias descartadas ou nao adotadas.
Fase 4 implementada:
- O scaffold foi exercitado com o handoff `2026-06-17_fase-4-validacao-operacional-do-harness-frontier.md`.
- O handoff gerado ficou pronto para retomada futura e seguiu o formato esperado.
- A validação confirmou que o gerador escreve no diretório certo e não depende do `cwd`.

## Perguntas Em Aberto
- Qual subconjunto minimo vale a pena importar como padrao do OpenF1?
- Vale reescrever o `audit_frontier_harness.py` para OpenF1 se aparecer necessidade futura de verificacao?
- Existe algum caso real em que subagentes permanentes `.codex/agents/` tragam ganho suficiente?

## Registro De Evidencias
- `AGENTS.md`
- `docs/PROJECT_PROFILE.md`
- `docs/plans/README.md`
- `docs/adr/README.md`
- `docs/templates/handoff.md`
- `codex_frontier_agentic_ecosystem_pack/codex_frontier_agentic_ecosystem/README.md`
- `codex_frontier_agentic_ecosystem_pack/codex_frontier_agentic_ecosystem/docs/01_SKILLS_CATALOG.md`
- `codex_frontier_agentic_ecosystem_pack/codex_frontier_agentic_ecosystem/docs/02_AGENTS_CATALOG.md`
- `codex_frontier_agentic_ecosystem_pack/codex_frontier_agentic_ecosystem/install_repo_pack.sh`
- `codex_frontier_agentic_ecosystem_pack/codex_frontier_agentic_ecosystem/install_user_pack.sh`
- `scripts/codex/record_handoff.py`

### ◈ Processing Context
- ✦ **Lead Agent:** Codex (Engenheiro Chefe)
- ▫ **Supporting Agents:** Tesla, Mill, Huygens, Descartes
- ⌥ **Skills Used:** write-implementation-plan, multi-agent-orchestration, engineering-decisions
- ☄ **Knowledge Sources:** AGENTS.md, PROJECT_PROFILE, docs/plans, docs/adr, pacote frontier, pareceres dos especialistas
- ☱ **Files Analyzed:** `docs/PROJECT_PROFILE.md`, `docs/plans/README.md`, `docs/adr/README.md`, pacote frontier docs/scripts/installers, catalogos de skills/agentes
- ◬ **Decision Complexity:** HIGH

> Este trabalho foi produzido com subagentes invocados. Se Roberto quiser suporte real de subagentes, pode pedir uma reavaliacao multiagente indicando os dominios desejados, por exemplo Engenharia de Dados, Produto/Frontend, IA/MLOps, Seguranca, Qualidade de Dados ou outro especialista adequado ao contexto.
