# 🏎️ OpenF1 Data Platform

[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![DuckDB](https://img.shields.io/badge/DuckDB-FFF000?style=for-the-badge&logo=duckdb&logoColor=black)](https://duckdb.org/)
[![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Plotly](https://img.shields.io/badge/Plotly-3F4F75?style=for-the-badge&logo=plotly&logoColor=white)](https://plotly.com/)
[![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)

Uma plataforma analítica local de alto desempenho projetada para ingestão, processamento e visualização de telemetria e dados de corrida da Fórmula 1 em alta frequência. A plataforma consome dados públicos da **OpenF1 API** e os estrutura utilizando a **Arquitetura Medalhão** local, permitindo consultas analíticas sub-segundo através do motor OLAP **DuckDB**.

---

## 🌟 Recursos Principais

- **Ingestão Paralela & Concorrente:** Extração assíncrona de telemetria de alta frequência (~3.7Hz) para múltiplos pilotos concorrentes utilizando `ThreadPoolExecutor`.
- **Arquitetura Medalhão (Lakehouse Local):**
  - **Bronze:** Dados brutos preservados no formato Apache Parquet particionado.
  - **Silver:** Esquemas estruturados e tipados no DuckDB organizados em um modelo dimensional (Star Schema).
  - **Gold:** Visões de agregação prontas para o consumo analítico.
- **Contratos de Dados (Data Contracts):** Validação estrita de tipos e regras de negócio com **Pydantic** no processamento de transição de camadas.
- **Quarentena de Dados:** Isolamento automático de registros corrompidos na camada física sem interrupção do pipeline.
- **Linhagem e Observabilidade:** Rastreamento ponta a ponta dos tempos de execução, volumetria e status das execuções na tabela `fact_pipeline_execution`.
- **FastAPI Assíncrono:** Backend robusto que delega consultas pesadas ao DuckDB fora da Thread de Loop do Evento (`asyncio.to_thread`) para evitar travamentos de concorrência.
- **Interface Visual Premium (Ferrari Theme):** Dashboard responsivo com estética *dark/carbon* e acentos em vermelho corrida, renderização dinâmica no lado do cliente com gráficos interativos do **Plotly.js**.

---

## 📐 Arquitetura da Plataforma

```mermaid
flowchart TD
    API[OpenF1 API] -->|Extract Concorrente| E[extract.py]
    E -->|Salva Parquet Bruto| Bronze[(Bronze Layer: data/bronze/)]
    Bronze -->|Processamento & Validação Pydantic| P[process.py]
    P -->|Falha no Contrato| Q[(Quarantine: data/quarantine/)]
    P -->|Sucesso no Contrato| Silver[(Silver/Gold Layer: DuckDB Local)]
    
    subgraph DuckDB OLAP Engine
        Silver -->|Modelagem Dimensional| dim_d[dim_drivers]
        Silver -->|Modelagem Dimensional| dim_s[dim_sessions]
        Silver -->|Modelagem Dimensional| dim_st[dim_stints]
        Silver -->|Modelagem Dimensional| dim_w[dim_weather]
        Silver -->|Modelagem Dimensional| fact_t[fact_car_telemetry]
        Silver -->|Modelagem Dimensional| fact_p[fact_pit_stops]
        Silver -->|Modelagem Dimensional| fact_rc[fact_race_control]
        Silver -->|Linhagem de Dados| fact_ex[fact_pipeline_execution]
    end
    
    DuckDB OLAP Engine -->|Queries Assíncronas asyncio.to_thread| FastAPI[FastAPI Backend - Porta 8001]
    FastAPI -->|Endpoints JSON| UI[Dashboard Premium: Jinja2 + Plotly.js]
```

---

## 📊 Modelagem de Dados (Star Schema)

Os dados são estruturados analiticamente no DuckDB local para otimização de consultas colunares OLAP:

### Tabelas de Dimensões
- `dim_drivers`: Nome, escuderia, acrônimo e país de origem dos pilotos.
- `dim_sessions`: Ano, tipo de sessão, GP, circuito e país do evento.
- `dim_stints`: Registro cronológico do composto de pneu e número de voltas em cada stint.
- `dim_weather`: Histórico das condições climáticas da pista e do ar durante as sessões.

### Tabelas de Fatos
- `fact_car_telemetry`: Telemetria de carro a ~3.7Hz (velocidade, RPM, marcha, acelerador, freio, DRS) por piloto, sessão e data.
- `fact_pit_stops`: Registro detalhado e duração exata de cada pit-stop realizado.
- `fact_race_control`: Histórico de mensagens do controle de prova da FIA (incidentes, bandeiras, safety cars).

---

## 🛠️ Tecnologias Utilizadas

- **Linguagem:** Python 3.10+
- **Processamento & Armazenamento:** DuckDB, Apache Parquet (via PyArrow & Pandas), Pydantic v2
- **Backend API:** FastAPI, Uvicorn, Jinja2 (Templates)
- **Frontend:** HTML5, Vanilla CSS3 (Ferrari Palette), JavaScript ES6 (Fetch API), Plotly.js
- **DevOps / Qualidade:** Git, Pre-commit Hooks (Black, Isort, Flake8), Docker & Docker Compose, GitHub Actions (CI/CD)

---

## 🚀 Como Executar Localmente

### Pré-requisitos
Certifique-se de possuir instalado em sua máquina:
- **Python 3.10** ou superior
- **Docker** e **Docker Compose** (caso prefira rodar via containers)
- **Make** (para uso dos atalhos de execução rápidos)

### 1. Clonar o Repositório & Configurar Ambiente
```bash
git clone https://github.com/Roberton003/openf1-data-platform.git
cd openf1-data-platform

# Criar ambiente virtual
make setup
source .venv/bin/activate

# Instalar dependências e hooks do pre-commit
make install
```

### 2. Executar a Ingestão de Dados (Bahrain 2025)
A ingestão realiza o download dos dados direto da OpenF1 API, salva os Parquets na camada Bronze, valida com Pydantic e popula o DuckDB local.
```bash
make ingest
```
*Os dados processados serão armazenados localmente no arquivo relacional: `data/silver/openf1_silver.duckdb`.*

### 3. Iniciar o Servidor Web e Dashboard
Para iniciar a aplicação FastAPI localmente na porta configurada (`http://localhost:8001`):
```bash
make run
```
Abra o navegador no endereço [http://localhost:8001](http://localhost:8001) para interagir com o painel premium.

---

## 🐳 Executando com Docker

Se preferir rodar a plataforma completamente isolada em containers:

```bash
# Compilar e subir os serviços
docker-compose up --build -d

# Acessar a aplicação no navegador
# URL: http://localhost:8001
```

---

## 🧪 Suíte de Testes & Linting

O repositório garante a entrega de código livre de regressões através de um loop rígido de qualidade:

```bash
# Executar formatadores de código (Black e Isort)
make format

# Executar análises estáticas (Flake8)
make lint

# Executar suíte de testes unitários com Pytest
make test
```

---

> **Desenvolvido por:** [Roberton003](https://github.com/Roberton003) & **Antigravity AI Platform** 🚀
