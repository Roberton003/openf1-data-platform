# Plano de Arquitetura Sênior: OpenF1 Data Platform

O objetivo deste projeto é construir uma Plataforma de Telemetria e Analytics robusta aproveitando os dados da Fórmula 1 ([OpenF1 API](https://openf1.org/)). Este projeto substituirá os antigos e atuará como o **projeto-âncora Sênior** do seu portfólio no GitHub, abraçando simultaneamente Engenharia de Dados (Batch/Near-Real Time) e Infraestrutura como Código.

## User Review Required

> [!IMPORTANT]
> A aprovação deste plano é necessária para iniciar a codificação (Fase de Execução - E). Confirme se a escolha da stack condiz com o que você domina ou deseja aprender (Python, Docker, DuckDB/PostgreSQL, Metabase ou Streamlit).

## Proposed Changes e Arquitetura do Sistema

A solução será dividida em 3 camadas, seguindo as melhores práticas de Engenharia de Dados descritas no nosso RAG interno e nos Padrões de Design de Sistemas Distribuídos:

### 1. Camada de Ingestão e Processamento (Extraction & Load)
* **Design Pattern:** Idempotent ETL Pipelines (Puxa os dados até a última sessão/corrida perfeitamente sem duplicar linhas).
* **Ferramenta:** Python 3.12+ (moderno e tipado) ou Apache Airflow simplificado se precisarmos de agendamento (podemos usar cron no início).
* **Endpoints consumidos:** `/car_data` (telemetria 3.7Hz), `/pit_stops`, `/weather`, e `/intervals`.
* **Resiliência:** Tratamento de Rate Limits e retry-backoff utilizando a biblioteca `tenacity`.

### 2. Camada de Armazenamento Inteligente (Data Lakehouse)
* Em vez de colocar dados pesados (telemetria em 3.7Hz gera milhões de linhas) em um banco transacional relacional simples, usaremos **DuckDB** para *Analytics* (OLAP) ou **PostgreSQL** com particionamento (Sharding).
* Este nível de arquitetura valida suas habilidades Sênior perante Head-hunters, ao demonstrar preocupação com o volume do Big Data.

### 3. Camada de Visualização (Frontend/BI)
* Para demonstrar valor imediato, propomos construir um dashboard.
* **Opção A (Foco em Dados):** Subir uma instância do **Metabase** via Docker-Compose lendo o banco de dados processado. (Excelente para analistas).
* **Opção B (Foco Full-Stack):** Desenvolver uma aplicação em **Streamlit (Python)** ou **Next.js (Web)** que consuma o banco processado e desenhe gráficos de telemetria e posições da corrida em tempo real. Pela simplicidade inicial, sugiro **Streamlit**.

### 4. Fundação e Padronização Sênior (DevOps & MLOps)
A excelência deste repositório não será "apenas um código em Python", será um ambiente de engenharia:
* **CI/CD:** GitHub Actions que validará `pytest`, `flake8/black/isort` para garantir *Clean Code*.
* **IaC:** Terraform para provisionar (se fossemos subir na AWS/GCP) ou, inicialmente, um `docker-compose.yml` majestoso para "1-Click-Run" locally.
* **Makefile:** Comandos padronizados (`make up`, `make ingest`, `make test`) para agradar qualquer SRE (Site Reliability Engineer).

## Verification Plan

### Automated Tests
- Testes unitários com `pytest` testando _mocking_ da malha de rede para `https://api.openf1.org/v1/`.
- Linters ativados rigorosamente.

### Manual Verification
1. Você clonará o repositório.
2. Rodará `docker-compose up -d`.
3. Disparará `make run-pipeline`.
4. Acessará o dashboard em `localhost:8501`.
5. Inspecionaremos se os tempos, clima e telemetria da última corrida do GP carregaram perfeitamente no dashboard final.
