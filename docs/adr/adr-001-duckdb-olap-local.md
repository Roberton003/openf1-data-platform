# ADR-001: Seleção do DuckDB como Motor OLAP Local

## Status
**Accepted**

## Data
2026-06-09

## Contexto
A plataforma analisa dados de telemetria da Fórmula 1 (amostrados a ~3.7Hz). Uma única corrida gera mais de 500.000 registros de telemetria para o grupo de pilotos foco.
Armazenar e consultar esses dados em um banco de dados transacional relacional convencional (como SQLite ou PostgreSQL bruto) localmente ou na nuvem acarreta:
1. Gargalo de IO na leitura do sistema de arquivos local sob consultas complexas (JOINs entre pilotos, sessões e intervalos).
2. Alto custo financeiro para hospedagem na nuvem de instâncias gerenciadas capazes de responder consultas complexas sub-segundo em grandes volumes de dados.
3. Necessidade de processos de banco de dados ativos na nuvem que aumentam a complexidade de deploy da aplicação pessoal na web.

## Decisão
Adotamos o **DuckDB** como motor OLAP (Online Analytical Processing) embutido no local de deploy da aplicação. Os dados de telemetria e metadados serão limpos e salvos na camada Silver no arquivo de banco DuckDB consolidado `data/silver/openf1_silver.duckdb` (ou em memória no front via leitura de Parquets).

No servidor web FastAPI, a conexão com o DuckDB será aberta estritamente em modo de leitura:
```python
conn = duckdb.connect(database="data/silver/openf1_silver.duckdb", read_only=True)
```

## Consequências
### Ganhos (Prós):
* **Performance Sub-segundo:** DuckDB é vetorizado e otimizado para consultas analíticas complexas (agregações, window functions e JOINs), processando milhões de registros de telemetria em milissegundos.
* **Custo Zero:** Roda embutido na aplicação de forma serverless local, eliminando custos com servidores gerenciados de banco de dados na nuvem (RDS, BigQuery).
* **Segurança Impecável (Read-Only):** Ao abrir o banco de dados em modo de leitura estrito (`read_only=True`) na API pública do FastAPI, inviabilizamos qualquer ataque de SQL Injection destrutivo (ex: `DROP TABLE`, `DELETE`), pois o motor rejeitará operações de DDL/DML.
* **Sem Superfície de Rede:** O DuckDB funciona como arquivo. Nenhuma porta de rede (como a 5432 do PostgreSQL) precisa ser aberta na VPS para a internet, eliminando vetores de ataque externos.

### Perdas/Restrições (Contras):
* **Concorrência de Escrita Limitada:** DuckDB não é projetado para múltiplos processos escrevendo simultaneamente na mesma base. Isso exige que nosso pipeline de processamento (ETL) seja executado de forma isolada, gravando as atualizações em lote de forma sequencial ou bloqueando o acesso de gravação temporariamente, o que atende perfeitamente ao escopo de ETL analítico em lote.
