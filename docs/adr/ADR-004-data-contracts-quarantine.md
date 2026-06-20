# ADR-004: Contratos de Dados (Pydantic) e Quarentena

## Status
**Accepted**

## Data
2026-06-09

## Contexto
Durante o processamento de dados brutos na fronteira entre a camada **Bronze** e a **Silver**, encontramos anomalias estruturais na API OpenF1 (tais como tipos de dados mistos com strings e floats em colunas de gaps, nulos inesperados em variáveis de telemetria e falhas de inferência de tipos pelo motor PyArrow do Apache Parquet). 
Sem um controle rígido de validação na ingestão:
1. Esquemas de tabelas da Silver/Gold podem ser corrompidos de forma silenciosa por dados sujos ou modificações de resposta do servidor de origem.
2. A quebra de um tipo de dados pode interromper o pipeline analítico inteiro da F1, gerando falhas nos JOINs analíticos do DuckDB e quebrando a renderização de gráficos no dashboard.

## Decisão
Implementamos a validação de schemas em tempo de execução através de **Data Contracts (Contratos de Dados)** estritos na fronteira de processamento de dados. 

Utilizaremos a biblioteca **Pydantic** para definir o contrato de dados de cada endpoint (`src/ingestion/schemas.py`). O script `src/ingestion/process.py` fará a validação de cada registro contra seu respectivo schema Pydantic. 

Se um registro ou conjunto de dados violar o schema, ele será isolado na pasta de **Quarentena** (`data/quarantine/`), enquanto os dados válidos serão carregados normalmente na camada Silver.

## Consequências
### Ganhos (Prós):
* **Impedimento de Corrupção de Dados:** Garante que a camada Silver possua um schema 100% limpo, consistente e seguro para consumo da API do FastAPI e do DuckDB.
* **Resiliência do Pipeline (Sem Travamentos):** Erros em uma linha ou sensor específico de telemetria não derrubam a pipeline de dados inteira. Os dados corrompidos são isolados de forma autônoma na quarentena e a pipeline continua.
* **Auditoria Avançada:** A quarentena serve como repositório de depuração de dados. Permite identificar exatamente quando e por que o schema da API pública sofreu alterações ou anomalias.
* **Demonstração Sênior:** A implementação de contratos de dados em pipelines de Big Data local é altamente valorizada e vista como o estado da arte em Engenharia de Dados corporativa.

### Perdas/Restrições (Contras):
* **Overhead de CPU na Ingestão:** Validar registro por registro com Pydantic consome ciclos de CPU na etapa de ETL da Bronze para a Silver, atrasando levemente o processamento.
* **Gerenciamento de Pastas:** Introduz uma nova pasta física (`data/quarantine/`) e tabelas de controle de erros que precisam ser monitoradas para evitar consumo excessivo de disco.
