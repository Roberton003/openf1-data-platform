# 🏎️ OpenF1 Data Platform

[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Dagster](https://img.shields.io/badge/Dagster-25292E?style=for-the-badge&logo=dagster&logoColor=white)](https://dagster.io/)
[![DuckDB](https://img.shields.io/badge/DuckDB-FFF000?style=for-the-badge&logo=duckdb&logoColor=black)](https://duckdb.org/)
[![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Plotly](https://img.shields.io/badge/Plotly-3F4F75?style=for-the-badge&logo=plotly&logoColor=white)](https://plotly.com/)
[![Scikit-Learn](https://img.shields.io/badge/scikit--learn-F7931E?style=for-the-badge&logo=scikit-learn&logoColor=white)](https://scikit-learn.org/)

Uma plataforma de engenharia de dados e MLOps de alto desempenho (FAANG-level) projetada para ingestão, processamento resiliente, orquestração declarativa e predição de telemetria da Fórmula 1 em alta frequência. A plataforma consome dados públicos da **OpenF1 API**, orquestra o pipeline com **Dagster** sob a **Arquitetura Medalhão**, armazena em **Parquet particionado** e serve previsões físicas analíticas através do motor OLAP **DuckDB** de forma serverless.

---

## 🌟 Recursos Principais

- **Orquestração Declarativa (Dagster):** Pipeline analítico completo modelado como assets declarativos em árvore de linhagem robusta, gerenciando as camadas do Lakehouse de forma transparente e modular.
- **Arquitetura Medalhão (Lakehouse Local Serverless):**
  - **Camada Bronze (Raw):** Ingestão resiliente e paralela dos dados brutos com tratamento de erros de API (como capturas automáticas de retornos 404 e timeouts de rede com retentativas exponenciais `tenacity`), salvos em Parquet.
  - **Camada Silver (Dimensões e Fatos):** Validação estrita de tipos via contratos **Pydantic**, limpeza de ruídos físicos (ex: tratamento de picos espúrios de marchas na telemetria) e ASOF JOIN analítico executado no DuckDB em memória para alinhar espacialmente coordenadas físicas de localização (~1.5Hz) com parâmetros de telemetria (~3.7Hz).
  - **Camada Gold (Feature Store e IA):** Consolidação analítica e expansão de stints Pirelli em voltas físicas individuais para treinar modelos preditivos.
- **Serverless DuckDB (Zero Writes Locks):** O webserver FastAPI abre conexões ao DuckDB totalmente em memória (`:memory:`) mapeando as tabelas Parquet locais como Views dinâmicas sob demanda com *Predicate Pushdown*. Isso elimina travamentos concorrentes de banco e garante respostas analíticas na casa de milissegundos.
- **IA e MLOps Físico:** Treinamento local e serialização automática de um regressor `RandomForestRegressor` (`models/lap_regressor.joblib`) no final da esteira do Dagster, utilizado pelo FastAPI para estimar o tempo ideal físico de volta e calcular o delta de desgaste de pneus.
- **Interface Visual Premium (Ferrari Theme):** Dashboard responsivo com estética *dark/carbon* Scuderia Ferrari, gráficos Plotly.js independentes de velocidade, RPM, marchas e pedais, timeline Gantt de stints Pirelli e um mapa 2D interativo com gradiente dinâmico de velocidade.

---

## 📐 Arquitetura da Plataforma

```mermaid
flowchart TD
    API[OpenF1 API] -->|Dagster Ingestão Resiliente| Bronze[(Bronze Layer: data/bronze/)]
    Bronze -->|ASOF JOIN Analítico + Validação Pydantic| Silver[(Silver Layer: data/silver/)]
    Silver -->|Feature Engineering & Expansão de Voltas| Gold[(Gold Layer: data/gold/)]
    Gold -->|Treinamento RandomForest| ML[models/lap_regressor.joblib]
    
    subgraph Lakehouse Storage Parquet
        Silver -->|Particionado por GP e Piloto| telemetry[fact_car_telemetry]
        Silver -->|Particionado por GP e Piloto| location[fact_car_location]
        Silver -->|Metadados Consolidados| metadata[dim_drivers, dim_sessions, dim_stints, dim_weather]
        Gold -->|Feature Store & Predições| predictions[lap_predictions.parquet]
    end
    
    Lakehouse Storage Parquet -.->|Mapeado como Views temporárias| DuckDB[(DuckDB :memory:)]
    ML -.->|Predictor de Performance| FastAPI[FastAPI Backend - Porta 8001]
    
    DuckDB -->|Leitura OLAP Concorrente asyncio.to_thread| FastAPI
    FastAPI -->|Endpoints JSON /api/predictions/lap_time| UI[Ferrari Dashboard: HTML5 + Plotly.js]
```

---

## 📊 Modelagem de Dados

Os dados são estruturados de forma relacional no DuckDB in-memory a partir dos Parquets do Lakehouse:

### Dimensões
- `dim_drivers`: Nome, escuderia, acrônimo e país de origem dos pilotos.
- `dim_sessions`: Ano, tipo de sessão, GP, circuito e país do evento.
- `dim_stints`: Composto de pneu (Soft, Medium, Hard, etc.) e voltas associadas a cada stint.
- `dim_weather`: Condições climáticas detalhadas da pista e do ar.

### Fatos
- `fact_car_telemetry`: Telemetria contínua (velocidade, RPM, marcha limpa, pedais de aceleração/freio, DRS) alinhada espacialmente com localização.
- `fact_car_location`: Coordenadas geográficas bidimensionais `x`, `y`, `z` no circuito.
- `fact_pit_stops`: Registro e duração de pit-stops.
- `fact_race_control`: Mensagens de controle de prova da FIA (incidentes, bandeiras).

---

## 🛠️ Tecnologias Utilizadas

- **Orquestração de Dados:** Dagster Core & Dagster Webserver
- **Processamento & OLAP Engine:** DuckDB, Pandas, PyArrow (Apache Parquet)
- **Modelagem de Machine Learning:** Scikit-Learn (RandomForestRegressor), Joblib (Serialização)
- **Backend API:** FastAPI, Uvicorn, Jinja2, Pydantic v2
- **Frontend & Design:** HTML5, Vanilla CSS3 (Scuderia Ferrari Palette), JavaScript ES6, Plotly.js
- **Qualidade & CI/CD:** Flake8, Black, Isort, Pytest, GitHub Actions

---

## 🚀 Como Executar Localmente

### Pré-requisitos
- **Python 3.10** ou superior
- **Make** (atalhos rápidos)

### 1. Configurar Ambiente
```bash
git clone https://github.com/Roberton003/openf1-data-platform.git
cd openf1-data-platform

# Criar ambiente virtual e instalar dependências + hooks do git
make setup
source .venv/bin/activate
make install
```

### 2. Executar a Orquestração (Materialização dos Dados e Treinamento do Modelo)
Você pode rodar a materialização completa das 3 camadas do Lakehouse e o treinamento da IA preditiva diretamente pelo terminal:
```bash
# Materializar todos os assets locais do Lakehouse
PYTHONPATH=. .venv/bin/dagster asset materialize --select \* -f src/ingestion/assets.py
```
*Dica: Você também pode iniciar o console visual do Dagster para acompanhar o grafo de linhagem de dados abrindo o painel na porta 3000:*
```bash
dagster dev
# Abra no navegador: http://localhost:3000
```

### 3. Iniciar a API e o Dashboard
Com a base de dados em Parquet gerada localmente, suba o webserver FastAPI:
```bash
make run
```
Acesse [http://localhost:8001](http://localhost:8001) para ver a interface gráfica animada.

---

## 🧪 Qualidade de Código & Testes

Garantimos a integridade do pipeline através de um loop rígido de qualidade estática e testes analíticos:

```bash
# Formatar estilos e ordenação de imports
make format

# Executar linting estático PEP 8
make lint

# Executar a suíte completa de testes (22 testes unitários e de qualidade analítica)
make test
```
*A suíte de testes unitários valida os endpoints da API, contratos de ingestão do Pydantic, e a qualidade física dos dados Parquet (limites físicos reais de telemetria de F1).*

---

> **Desenvolvido por:** [Roberton003](https://github.com/Roberton003) & **Antigravity AI Platform** 🚀
