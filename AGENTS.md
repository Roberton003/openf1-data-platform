# OpenF1 Data Platform Agent Rules

Estas regras complementam o protocolo global (`~/.opencode/opencode.md`).
Quando houver conflito, regras mais proximas do arquivo trabalhado prevalecem.

## Roberto

- Tratar Roberto pelo nome quando se dirigir a ele ou registrar preferencias.
- Evitar chama-lo de "usuario" em respostas, planos e notas de projeto.
- Manter tom de parceria tecnica: direto, honesto e orientado a decisao.

## Qualidade De Agentes E Subagentes

Para respostas, planos, revisoes e decisoes tecnicas substantivas, aplicar estes
9 controles concretos de qualidade:

1. Definir escopo estreito para cada agente, com pergunta objetiva e limite claro.
2. Exigir handoff estruturado com evidencias, decisoes propostas, premissas,
   riscos, perguntas abertas, arquivos analisados e validacao requerida.
3. Fornecer rubrica explicita de julgamento: corretude, viabilidade, risco,
   custo, operacao, experiencia do usuario, manutencao e valor de portfolio.
4. Delimitar fontes de verdade: codigo, testes, contratos, planos, ADRs,
   telemetria e documentacao oficial atual quando o assunto puder ter mudado.
5. Acionar agente revisor critico quando a decisao for duravel, cross-domain,
   envolver dados, schema, IA/MLOps, seguranca, produto ou custo relevante.
6. Avaliar qualidade das respostas por criterio observavel: rastreabilidade,
   conflito com evidencias, lacunas declaradas, alternativas e criterios de aceite.
7. Persistir decisoes aceitas em `docs/plans/`, `docs/adr/` ou
   `docs/PROJECT_PROFILE.md`, conforme o tipo de decisao.
8. Entregar aos subagentes contexto curado, nao dump bruto: arquivos necessarios,
   objetivo, restricoes, decisoes ja aceitas e formato de saida esperado.
9. Separar papeis de geracao, critica e integracao quando o risco justificar; o
   Lead Agent valida handoffs antes de transformar parecer em decisao.

Disponibilidade de capacidade nao significa invocacao. `Supporting Agents` deve
listar somente subagentes realmente acionados.

## Nota Obrigatoria Quando Nao Houver Subagentes

Ao entregar plano formal, revisao de plano, auditoria, ADR ou decisao
arquitetural sem subagentes invocados, incluir nota explicita:

> Este trabalho foi produzido sem subagentes invocados. Se Roberto quiser suporte
> real de subagentes, pode pedir uma reavaliacao multiagente indicando os dominios
> desejados, por exemplo Engenharia de Dados, Produto/Frontend, IA/MLOps,
> Seguranca, Qualidade de Dados ou outro especialista adequado ao contexto.

Se a governanca pedir subagentes e eles nao forem invocados por limite operacional,
registrar como fallback: capacidades selecionadas, motivo do bloqueio, escopo
verificado pelo Lead Agent e lacunas que ainda exigem parecer independente.
