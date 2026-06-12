# Linhagem de Dados e Arquitetura Medallion: Do Dado Bruto à IA Preditiva (Didática Técnica)

Este documento descreve detalhadamente o ciclo de vida do dado, as transformações físicas e as justificativas técnicas das transições de camadas no **OpenF1 Data Platform**.

---

## 🛠️ 1. O Pipeline Medallion (Linhagem de Fatores)

```
 [ API OpenF1 ]
       |
       |  (Ingestão HTTP + Retries)
       v
 +-------------------------------------------------------------------+
 | 1. CAMADA BRONZE (Raw Storage)                                    |
 |    - Dado bruto em Snappy Parquet sem tratamentos.                |
 |    - Localização física: data/bronze/                             |
 +-------------------------------------------------------------------+
       |
       |  (Validação Pydantic + Sincronização ASOF JOIN no DuckDB)
       v
 +-------------------------------------------------------------------+
 | 2. CAMADA SILVER (Cleaned & Aligned Fact Tables)                  |
 |    - Dados higienizados, tipados e alinhados espacialmente.       |
 |    - Localização física: data/silver/                             |
 +-------------------------------------------------------------------+
       |
       |  (Feature Engineering + Predição de IA Regressora)
       v
 +-------------------------------------------------------------------+
 | 3. CAMADA GOLD (Serving Layer & ML Outcomes)                     |
 |    - Métricas analíticas agregadas por volta e predições de IA.   |
 |    - Localização física: data/gold/                               |
 +-------------------------------------------------------------------+
       |
       |  (Consumo Serverless via FastAPI)
       v
 [ Dashboard UI / Aplicação Consumidora ]
```

---

## 📐 2. Detalhamento Técnico das Camadas e Transições

### Camada Bronze: Ingestão Resiliente (Raw Data)
* **Objetivo:** Garantir a imutabilidade da fonte. O dado bruto representa exatamente o que a API do OpenF1 enviou, protegendo o sistema contra falhas futuras se as regras de transformação mudarem.
* **Storage Físico:** Arquivos Parquet locais salvos na partição:
  `data/bronze/{session_key}/{driver_number}/telemetry_raw.parquet`
* **Transição (Ingestão):** O asset do **Dagster** realiza o fetch incremental por blocos de timestamp. Ele implementa uma política de retentativa automática (exponential backoff) para contornar limites de taxa e instabilidades de rede.

### Camada Silver: Sincronização e Validação (Cleaned Layer)
* **Objetivo:** Estabelecer a integridade estrutural e alinhar os dados.
* **Transição Bronze $\rightarrow$ Silver:**
  1. **Contratos de Dados (Data Contracts):** Os registros passam por validações automáticas com schemas **Pydantic**. Linhas com coordenadas nulas inexplicáveis, velocidades negativas ou timestamps corrompidos são descartadas ou tratadas.
  2. **ASOF JOIN (Séries Temporais Assíncronas):** A telemetria física (registrada em alta frequência de ~3.7Hz) e a geolocalização do carro na pista (registrada a ~1.5Hz) operam em frequências assíncronas. Executamos uma junção do tipo ASOF no DuckDB para alinhar espacialmente cada ponto de velocidade e controle com a sua respectiva posição no circuito:
     ```sql
     SELECT l.x, l.y, t.speed, t.n_gear
     FROM fact_car_location l
     ASOF JOIN fact_car_telemetry t 
       ON l.session_key = t.session_key 
      AND l.driver_number = t.driver_number 
      AND l.date >= t.date
     ```
* **Storage Físico:** Datasets Parquet estruturados e particionados em disco por session e driver (facilitando a leitura seletiva via *Predicate Pushdown*):
  `data/silver/fact_car_telemetry/session_key={session_key}/driver_number={driver_number}/data.parquet`

### Camada Gold: Agregações & Machine Learning (Curated Layer)
* **Objetivo:** Maximizar o valor analítico e preditivo para a tomada de decisão.
* **Transição Silver $\rightarrow$ Gold:**
  1. **Feature Engineering:** O pipeline do Dagster agrega a telemetria Silver em nível de volta (`lap_number`), calculando métricas de estresse como porcentagem da volta sob pé cravado (throttle > 90%), intensidade de frenagem e desgaste de pneu estimado.
  2. **Pipeline de MLOps Preditivo:** O modelo leve de IA (`RandomForestRegressor` treinado e versionado em `models/`) lê as features estruturadas por volta e infere o **tempo de volta ideal esperado (Lap Duration)** com base na temperatura do asfalto e idade do pneu.
  3. **Fusão Analítica:** Os dados analíticos reais são combinados com as predições geradas pelo modelo de IA.
* **Storage Físico:**
  `data/gold/lap_predictions.parquet` (dados de IA preditiva)
  `data/gold/metrics_summary.parquet` (métricas e recordes de GP)

---

## 🔒 3. Benefícios Arquiteturais no Mercado (FAANG Standard)

1. **Idempotência Garantida:** Se a execução do pipeline falhar na metade, reexecutar o Dagster para a mesma sessão simplesmente recalcula e sobrescreve de forma limpa os arquivos Parquet daquela partição, impedindo duplicação silenciosa de linhas.
2. **Escala Horizontal Infinita (Serverless):** Ao eliminar o banco físico e ler diretamente de arquivos Parquet em disco usando o DuckDB em memória, a API FastAPI torna-se totalmente independente de estado (stateless). Isso permite replicar a API em múltiplos nós para suportar alto tráfego sem riscos de lock concorrente de banco de dados.
