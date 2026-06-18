# OpenF1 Data Platform Agent Rules

Estas regras complementam o protocolo global (`~/.opencode/opencode-core.md`).
Quando houver conflito, regras mais proximas do arquivo trabalhado prevalecem.
O harness ativo tem 18 skills e 20 agents (8 core + 12 domain) em `~/.opencode/`.

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

## Modelo de Execução

Cadeia de fallback automático:
1. `deepseek-v4-flash-opencode-zen` (Free) — padrão para T0-T5
2. `mimo-v2.5-opencode-go-medium` — fallback automático

### Estratégia de invocação:
- **TIER PAGO:** `task` tool em SEQUENTIAL (skeptic → test → devops → architect)
- **FREE TIER:** SINGLE — Lead Agent aplica metodologias das skills diretamente

### SINGLE Protocol (quando `task` tool falha):
1. Emitir: "[Model Escalation] `task` tool bloqueado. Ativando SINGLE."
2. Carregar skills via `skill` tool (adversarial-review, verification-workflow-designer, etc.)
3. Aplicar metodologia de cada skill (questions, checks, output format)
4. Consolidar findings em handoff único
5. Documentar: "Supporting Agents: Lead Agent (via skill methodologies)"

### Gatilho:
- 2+ timeouts consecutivos de bash
- `task` tool retorna erro/timeout/cancel
- Agents cancelados por Free tier

## Suporte Obrigatório

Toda atividade substantiva (T1+) deve ter suporte documentado de agentes e skills.

| T-Level | Agents Mínimos | Skills Mínimas |
|---------|----------------|----------------|
| T0 | Lead Agent | — |
| T1 | Lead Agent | 1 skill |
| T2 | Lead + 1 domain | 1-2 skills |
| T3 | Lead + 2 domain | 3+ skills |
| T4 | Lead + 3 domain + adversarial | 3+ skills |
| T5 | Full council | 4+ skills |

**Regra:** Sem suporte documentado, a atividade não inicia. Se agentes não puderem
ser invocados por limite operacional, registrar como `Rejected/Blocked` com motivo.

**Fallback:** Lead Agent executa sozinho + justificativa explícita + handoff com lacunas.

## Checklist Pré-Execução (Obrigatório para T1+)

Antes de qualquer edição de código:
- [ ] Classificação T-level emitida (task-router YAML com `agents:` e `skills:`)
- [ ] Mínimo de agents invocados via `task` tool (ou `Rejected/Blocked` documentado)
- [ ] Mínimo de skills carregadas via `skill` tool

**Sem estes 3 itens, NENHUMA edição de código é permitida.**

`Supporting Agents` deve listar somente subagentes realmente acionados.

`Supporting Agents` deve listar somente subagentes realmente acionados.

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
