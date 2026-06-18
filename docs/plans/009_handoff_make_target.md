# Plano de Implementacao 009: Entrada Padrao Para Handoff Via Makefile

## Status E Metadados
- Status: Completed
- Data: 2026-06-17
- Responsavel: Codex (Engenheiro Chefe)
- Complexidade: MEDIUM
- Decisoes relacionadas: harness local, memoria operacional, handoff padrao, ergonomia de execucao
- Supersedes: none
- Superseded by: none

## Objetivo E Resultado Esperado
Expor a geracao de handoff como entrada padrao do projeto por meio de `make handoff`,
sem criar nova camada de automacao ou nova taxonomia de governanca.

Resultado esperado:
- um comando padrao e previsivel para gerar handoffs locais;
- menor friccao para encerrar tarefas com memoria operacional consistente;
- reuse do scaffold canônico sem duplicar os artefatos de governo do projeto;
- manutencao do fluxo simples e repo-scoped.

## Contexto E Estado Atual
- O OpenF1 ja possui `docs/session-handoffs/` como memoria operacional local.
- A Fase 3 do pacote frontier introduziu `docs/templates/handoff.md` como scaffold canonico.
- `scripts/codex/record_handoff.py` ja gera handoffs a partir desse scaffold.
- Falta uma entrada ergonomica padrao para acionar o fluxo sem memorizar o caminho do script.

## Registro De Decisoes Do Plano
| ID | Decisao | Por Quê | Premissas | Alternativas Rejeitadas | Evidencia | Impacto | Validacao |
|---|---|---|---|---|---|---|---|
| D1 | Adicionar `make handoff` | Reduz friccao e torna o fluxo de memoria acessivel como os demais comandos do projeto | O Makefile ja e um ponto de entrada do repo | Deixar apenas o script solto | `Makefile`, `scripts/codex/record_handoff.py` | Baixa friccao operacional | `make handoff TITLE=...` gerar arquivo valido |
| D2 | Exigir `TITLE` explicito | Evita handoffs vazios ou ambíguos | O titulo e o slug do arquivo | Inferir titulo a partir do contexto implícito | `scripts/codex/record_handoff.py` | Menos erro humano | Falhar com mensagem clara se `TITLE` ausente |
| D3 | Manter o gerador simples e repo-scoped | Evita nova camada de automacao ou dependencia externa | O valor esta na previsibilidade, nao na complexidade | Adicionar preenchimento automatizado de seções ou roteamento adicional | Plano 008, handoffs anteriores, `AGENTS.md` | Menor manutencao | Validar que o comando apenas gera o handoff |

## Evidencias, Premissas E Lacunas
| Tipo | Item | Fonte/Validacao |
|---|---|---|
| VERIFIED | O Makefile ja concentra comandos do projeto | `Makefile` |
| VERIFIED | O gerador de handoff ja existe e passa em `py_compile` | `scripts/codex/record_handoff.py` |
| VERIFIED | O scaffold de handoff ja existe | `docs/templates/handoff.md` |
| SOURCED | Handoff local e memoria operacional do projeto | `AGENTS.md`, `docs/session-handoffs/2026-06-17_codex_frontier_partial_adoption.md` |
| PROJECTED | `make handoff` reduz friccao de uso no dia a dia | estimativa operacional baseada no fluxo atual |

## Escopo Incluido
- Adicionar alvo `make handoff`.
- Manter o script como unica implementacao.
- Validar geracao do arquivo com `TITLE=...`.

## Fora De Escopo
- Gerar automaticamente conteudo de handoff.
- Introduzir novas seções ou roteadores.
- Criar automatizacao de work package ou auditoria.

## Abordagem Escolhida E Justificativa
Entrada padrao via Makefile.

O projeto ja usa `make` como ponto de entrada para tarefas frequentes. Inserir o handoff nesse mesmo padrao reduz carga mental sem criar nova interface nem nova taxonomia.

## Impacto E Riscos
- Positivo: o encerramento de tarefas fica mais simples e repetivel.
- Positivo: o scaffold canônico passa a ter uma entrada padrao de uso.
- Negativo: um alvo mal documentado pode gerar handoffs vazios.
- Risco: se `TITLE` for omitido, o comando falha; isso e desejado para evitar saida ruim.

## Dependencias
- `scripts/codex/record_handoff.py`
- `docs/templates/handoff.md`
- `docs/session-handoffs/`

## Etapas De Implementacao
### Fase 1: Atualizacao do Makefile
- [x] Adicionar o alvo `handoff`.
- Arquivos: `Makefile`.
- Verificacao: o alvo exige `TITLE`.
- Rollback: remover o alvo.

### Fase 2: Validacao
- [x] Executar `make handoff TITLE="..."`.
- Arquivos: `docs/session-handoffs/`.
- Verificacao: arquivo novo com nome correto e conteudo valido.
- Rollback: excluir apenas o handoff gerado durante o teste.

## Estrategia De Testes
- Validar sintaxe com `make handoff TITLE="..."`.
- Verificar que o arquivo gerado segue o scaffold canônico.
- Confirmar que o script funciona sem depender do `cwd`.

## Observabilidade
- Registrar o comando padrão em handoffs futuros.
- Atualizar a memoria operacional local quando o alvo for usado em tarefas reais.

## Rollout E Rollback
- Rollout: imediato, repo-scoped.
- Rollback: remover o alvo `handoff` do Makefile.

## Criterios De Aceite
- Existe alvo `make handoff`.
- O comando gera um handoff valido em `docs/session-handoffs/`.
- O fluxo continua simples e sem dependencias externas.
- Nenhuma camada adicional de automacao foi criada.

## Resultado Observado E Revisao
O alvo foi adicionado e validado com geracao real de handoff. O smoke test gerou
`docs/session-handoffs/2026-06-17_smoke-test-do-alvo-handoff.md` e confirmou que
o fluxo funciona de ponta a ponta via `make`.

## Perguntas Em Aberto
- Vale adicionar um `make handoff TITLE=... PROJECT=...` mais flexivel no futuro?
- Há ganho real em documentar esse atalho em uma nota publica?

## Registro De Evidencias
- `Makefile`
- `scripts/codex/record_handoff.py`
- `docs/templates/handoff.md`
- `docs/session-handoffs/2026-06-17_codex_frontier_partial_adoption.md`
- `docs/session-handoffs/2026-06-17_fase-4-validacao-operacional-do-harness-frontier.md`

### ◈ Processing Context
- ✦ **Lead Agent:** Codex (Engenheiro Chefe)
- ▫ **Supporting Agents:** None
- ⌥ **Skills Used:** write-implementation-plan, engineering-decisions, multi-agent-orchestration
- ☄ **Knowledge Sources:** AGENTS.md, PROJECT_PROFILE, Makefile, handoff scaffold, record_handoff script, plano 008 e handoff local
- ☱ **Files Analyzed:** `Makefile`, `scripts/codex/record_handoff.py`, `docs/templates/handoff.md`, `docs/session-handoffs/*`, `docs/plans/008_codex_frontier_adocao_parcial.md`
- ◬ **Decision Complexity:** MEDIUM

> Este trabalho foi produzido sem subagentes invocados. Se Roberto quiser suporte real de subagentes, pode pedir uma reavaliacao multiagente indicando os dominios desejados, por exemplo Engenharia de Dados, Produto/Frontend, IA/MLOps, Seguranca, Qualidade de Dados ou outro especialista adequado ao contexto.
