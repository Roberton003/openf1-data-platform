# ADR-006: Parametrização da Ingestão de Dados e Ingestão sob Demanda (On-Demand)

## Status
**Accepted**

## Data
2026-06-14

## Contexto
O projeto `openf1-data-platform` foi configurado para ingerir e processar uma massa de teste restrita a 3 GPs estratégicos de 2025 (Bahrain, Mônaco e Austrália/Espanha) e 6 pilotos de foco (Verstappen, Norris, Leclerc, Hamilton, Russell, Piastri) como documentado em [data_architecture_sizing.md](file:///media/Arquivos/Engenharia%20TI%202026/openf1-data-platform/data_architecture_sizing.md).

Esta limitação é justificada pelos seguintes fatores:
1. A API pública do OpenF1 é instável e sujeita a limites de taxa (*Rate Limits* / HTTP 429).
2. Uma ingestão completa da temporada inteira (24 GPs × 20 pilotos × 5 endpoints analíticos) geraria mais de 2.400 requisições HTTP massivas, levando de 4 a 6 horas para concluir e falhando frequentemente na rede.

No entanto, manter os GPs e pilotos chumbados (*hardcoded*) no código cria um acoplamento rígido. Se um analista de dados (BI) precisar de dados de um piloto estreante ou de um circuito específico fora da lista padrão, ele dependerá de alterações manuais de código feitas por um Engenheiro de Dados e de um novo deploy. A parametrização permite a execução de pipelines de forma dinâmica e sob demanda (*on-demand*).

## Decisão
Adotamos a parametrização do pipeline de ingestão e processamento por meio de parâmetros dinâmicos na CLI e no orquestrador Dagster, viabilizando a execução *on-demand*:

1. **CLI Parametrizada:** Os scripts [extract.py](file:///media/Arquivos/Engenharia%20TI%202026/openf1-data-platform/src/ingestion/extract.py) e `process.py` aceitarão o argumento opcional `--drivers` (ex: `--drivers 10,23`) para especificar a lista de pilotos a serem ingeridos/processados diretamente no terminal, sobrescrevendo a lista fixa em memória.
2. **Dagster Run Configuration:** No arquivo [assets.py](file:///media/Arquivos/Engenharia%20TI%202026/openf1-data-platform/src/ingestion/assets.py), a lista estática de GPs (`SESSIONS_TO_PROCESS`) será integrada com as classes de configuração do Dagster (`RunConfig`/`Config`). Isso permite que os parâmetros de execução sejam informados em tempo de execução na aba "Launchpad" da interface web do Dagster.
3. **Escalabilidade Transparente no Lakehouse (Hive-style):** Os novos arquivos Parquet serão salvos em diretórios particionados dinamicamente (ex: `data/silver/fact_car_telemetry/year=2025/gp=Monaco/session=Race/driver_number=10/`). O banco DuckDB mapeia essas partições usando globbing automático (`data/silver/**/*.parquet`). Consequentemente, novos dados inseridos pelo analista sob demanda são integrados às Views analíticas instantaneamente, sem necessidade de alterações ou deploys de código.

## Consequências
### Ganhos (Prós):
* **Autonomia do Analista (Self-Service):** O time de BI pode rodar execuções pontuais para qualquer piloto ou circuito diretamente pela interface do Dagster ou via terminal.
* **Time to Insight (TTI) Acelerado:** Uma ingestão cirúrgica de 1 GP focado (ex: 2 pilotos rivais) reduz o tempo de sincronização de 5 horas para menos de 3 minutos (apenas 13 requisições HTTP).
* **Mitigação de Rate Limits (HTTP 429):** Rodadas sob demanda limitadas mantêm o tráfego de rede da plataforma abaixo do radar de bloqueios da API.
* **Modularidade de Infraestrutura:** Desacoplamento total de parâmetros e lógica operacional.

### Perdas/Restrições (Contras):
* **Risco de Ingestão Descontrolada por Usuários:** Se um analista disparar pipelines para múltiplos GPs simultâneos sem controle, as limitações de rede e rate limits originais descritas no [data_architecture_sizing.md](file:///media/Arquivos/Engenharia%20TI%202026/openf1-data-platform/data_architecture_sizing.md) voltarão a ocorrer. Isso exige documentação clara de uso no catálogo e boas práticas operacionais.
