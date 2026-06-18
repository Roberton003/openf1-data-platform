# ADR-007: Governanca de Agentes, Subagentes e Qualidade de Planos

## Status
**Accepted**

## Data
2026-06-16

## Contexto
O OpenF1 Data Platform passou a usar planos formais, revisoes multiagente,
skills especializadas e registros de execucao para orientar evolucoes tecnicas
de engenharia de dados, analytics, IA/MLOps e produto.

Durante a revisao dos planos F1-004, F1-005 e F1-006, ficou claro que respostas
sem parecer independente podem ser uteis, mas nao devem ser apresentadas como
revisao multiagente. Tambem ficou claro que a qualidade dos agentes melhora
quando cada especialista recebe escopo estreito, fontes delimitadas, rubrica de
julgamento e contrato de handoff.

## Decisao
Adotamos uma governanca explicita para o uso de agentes e subagentes no projeto:

1. Criar `AGENTS.md` local com regras de tratamento de Roberto, orquestracao e
   qualidade de respostas.
2. Aplicar 9 controles concretos de qualidade para respostas, planos, revisoes,
   auditorias, ADRs e decisoes tecnicas substantivas.
3. Distinguir capacidade disponivel de subagente realmente invocado.
4. Exigir nota explicita quando um plano, auditoria, ADR ou decisao arquitetural
   for entregue sem subagentes invocados.
5. Usar `docs/plans/` como indice de planos aprovados, executados e auditaveis.
6. Usar `docs/adr/` para decisoes arquiteturais duraveis.
7. Manter `docs/PROJECT_PROFILE.md` como perfil operacional do projeto e ponto
   de roteamento de skills/capacidades.

## Controles De Qualidade

1. Escopo estreito por agente.
2. Handoff estruturado.
3. Rubrica explicita de julgamento.
4. Fontes de verdade delimitadas.
5. Revisor critico quando a decisao for duravel ou cross-domain.
6. Avaliacao observavel da qualidade da resposta.
7. Persistencia das decisoes aceitas.
8. Contexto curado para subagentes.
9. Separacao entre geracao, critica e integracao quando o risco justificar.

## Consequencias

### Ganhos

- Melhora a rastreabilidade entre pergunta, parecer, decisao, plano e execucao.
- Reduz risco de parecer falso-multiagente.
- Torna planos e auditorias mais defensaveis para tech leads e recrutadores.
- Cria padrao replicavel para projetos futuros.

### Restricoes

- Aumenta custo de coordenacao em tarefas substantivas.
- Exige disciplina para nao confundir `Available Supporting Capabilities` com
  `Supporting Agents` realmente invocados.
- Pode haver fallback para execucao `SINGLE` quando subagentes estiverem
  indisponiveis; nesse caso, a lacuna deve ser declarada.

## Relacao Com Artefatos

- Regras operacionais: `AGENTS.md`.
- Planos e auditorias: `docs/plans/README.md`.
- Perfil do projeto: `docs/PROJECT_PROFILE.md`.
- Indice de decisoes: `docs/adr/README.md`.
