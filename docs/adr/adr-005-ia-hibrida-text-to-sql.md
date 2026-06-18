# ADR-005: Arquitetura Híbrida de Inteligência Artificial

## Status
**Accepted**

## Data
2026-06-09

## Contexto
O projeto visa integrar IA para permitir consultas inteligentes em linguagem natural sobre os dados coletados da F1 (telemetria física de velocidade, pit-stops, stints, ultrapassagens e incidentes do controle de corrida). 
A abordagem clássica de IA de dados é aplicar **RAG (Retrieval-Augmented Generation)** vetorial em toda a base. No entanto, para dados numéricos e físicos estruturados em alta frequência (como milhões de linhas de telemetria):
1. Vetorizar números e ler trechos textuais de tabelas causa **alucinações severas** por parte dos modelos de linguagem (LLM). O modelo inventa valores de velocidade, RPM e posições de corrida.
2. O modelo perde a capacidade lógica de fazer cálculos matemáticos exatos e ordenação cronológica complexa (ex: médias de tempo ou deltas de velocidade).
3. O consumo de tokens seria inviável de ser mantido devido ao enorme volume de números representados como texto nas bases vetoriais.

## Decisão
Adotamos uma **Arquitetura Híbrida de IA de Dados (OLAP-Agent)** desacoplada no backend FastAPI:
1. **RAG clássico para dados textuais (não estruturados):** As transcrições do rádio da equipe (`/team_radio`) e os logs de mensagens da FIA (`/race_control`) serão vetorizados localmente usando **ChromaDB** e o LLM responderá baseando-se em busca semântica direta.
2. **Mecanismo Text-to-SQL para dados numéricos (estruturados):** Para consultas de telemetria, tempos, pneus e classificação final, o LLM receberá o esquema do banco DuckDB da Silver. O LLM traduzirá a pergunta do usuário em uma query SQL analítica estruturada. A query será executada no DuckDB local, que retornará os dados exatos (DataFrame) para serem expostos em gráficos interativos e analisados textualmente pela IA de forma segura.

Toda a interação com a IA usará o **Google Gemini (1.5 Pro ou 2.0 Flash)** limitado a **4.000 tokens** por requisição de contexto.

## Consequências
### Ganhos (Prós):
* **Exatidão de Insights:** Ao delegar os cálculos para o DuckDB via SQL e a busca contextual de incidentes para a base de vetores ChromaDB, reduzimos a taxa de alucinação de dados matemáticos a **zero**.
* **Visualização Dinâmica sob Demanda:** O usuário pode plotar qualquer gráfico comparativo (ex: curva de velocidade Hamilton vs Leclerc na volta 10) apenas escrevendo o que deseja analisar, sem necessidade de filtros estáticos.
* **Eficiência de Custo e Velocidade:** Limitar a janela a 4.000 tokens e usar SQL em DuckDB in-memory torna as requisições extremamente leves, rápidas e baratas.
* **Complexidade Sênior Demonstrada:** Apresenta um design moderno de **Agentes de Dados corporativos** amplamente valorizado no mercado de IA Aplicada a Dados.

### Perdas/Restrições (Contras):
* **Necessidade de Chave de API Externa:** Depende do fornecimento de uma API Key do Google Gemini por meio de variáveis de ambiente.
* **Raciocínio Text-to-SQL Complexo:** Exige que a modelagem relacional do DuckDB (Star Schema) esteja muito bem estruturada e com nomes de tabelas/colunas claros (Linguagem Ubíqua) para que o LLM consiga gerar as queries SQL sem errar sintaxe.
