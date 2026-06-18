# ADR-002: Ingestão Concorrente Segmentada por Piloto

## Status
**Accepted**

## Data
2026-06-09

## Contexto
O endpoint `/car_data` da API do OpenF1 fornece telemetria em tempo real a uma frequência de ~3.7Hz. Tentar baixar a telemetria consolidada de todos os 20 pilotos para uma sessão de corrida inteira (cerca de 530.000 linhas) em uma única requisição HTTP provoca falhas graves:
1. **Timeouts da API:** O servidor da API do OpenF1 falha em processar e empacotar uma resposta JSON massiva, resultando em erros HTTP 504 Gateway Timeout ou conexões fechadas de forma abrupta.
2. **Urgência de Rede:** A ingestão síncrona linear de piloto por piloto seria extremamente lenta, estendendo o tempo de execução da pipeline desnecessariamente.

## Decisão
Decidimos segmentar a extração de dados de alta frequência por piloto e paralelizar a execução.
O script de ingestão [extract.py](file:///media/Arquivos/Engenharia%20TI%202026/openf1-data-platform/src/ingestion/extract.py) utilizará o `ThreadPoolExecutor` do Python (`concurrent.futures`) para disparar requisições HTTP paralelas isoladas para cada piloto foco (`/car_data?session_key=XXXX&driver_number=YY`), limitando o número de conexões simultâneas a 5 para evitar bloqueios de IP (rate-limiting) pelo provedor da API.

Os dados resultantes serão salvos na camada Bronze em arquivos Parquet brutos individuais (ex: `data/bronze/2025/gp_monaco/race/car_data_44.parquet`).

## Consequências
### Ganhos (Prós):
* **Resiliência de Rede:** Ao quebrar a busca de dados de telemetria por piloto, a resposta da API fica leve (cerca de 25k-100k registros por piloto), eliminando timeouts.
* **Velocidade de Ingestão:** O download simultâneo de múltiplos pilotos reduz o tempo de execução do pipeline em até 70% comparado à busca sequencial síncrona.
* **Granularidade Bronze:** Os arquivos são armazenados de forma isolada na Bronze, facilitando o reprocessamento em caso de falha de validação ou corrupção de dados de um piloto específico.

### Perdas/Restrições (Contras):
* **Complexidade do Código:** Exige gerenciamento de concorrência no Python, controle de exceções dentro das threads de execução e controle de rate-limiting ativo (backoff com `tenacity` em cada thread).
* **Consumo de Conexões:** Exige mais conexões HTTP simultâneas com a API de origem, o que requer monitoramento de erros de limite de requisições.
