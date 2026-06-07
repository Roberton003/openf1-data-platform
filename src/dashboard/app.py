import os
import streamlit as st
import pandas as pd
import duckdb
import plotly.express as px

DATA_DIR = os.path.join(os.path.dirname(__file__), "../../data")

st.set_page_config(page_title="OpenF1 Telemetry Dashboard", layout="wide", page_icon="🏎️")

# Custom CSS for Premium Design
st.markdown("""
    <style>
        .main {
            background-color: #0f1115;
            color: #e0e6ed;
        }
        h1, h2, h3 {
            color: #ff1801 !important;
            font-family: "Outfit", sans-serif;
        }
        .stDataFrame, .stTable {
            border: 1px solid #2d3139;
            border-radius: 8px;
            background-color: #161920;
        }
        .css-1avcm0n {
            background-color: #161920;
        }
    </style>
""", unsafe_allow_html=True)

st.title("🏎️ OpenF1 Telemetry & Analytics Platform")
st.markdown("""
Esta plataforma de nível **Sênior** consome dados em *Near Real-Time* da API do OpenF1, persistidos localmente no formato **Apache Parquet** (Simulando uma Camada Silver de Data Lake) e processados de forma analítica instantânea utilizando o motor OLAP **DuckDB**.
""")

# Helper to load data via DuckDB
def query_duckdb(query):
    try:
        res = duckdb.query(query)
        if res:
            return res.df()
    except Exception as e:
        print(f"Error querying DuckDB: {e}")
    return pd.DataFrame()

# File paths check
weather_path = os.path.join(DATA_DIR, "weather.parquet")
drivers_path = os.path.join(DATA_DIR, "drivers.parquet")
intervals_path = os.path.join(DATA_DIR, "intervals.parquet")
car_data_path = os.path.join(DATA_DIR, "car_data.parquet")

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("🌦️ Condições da Pista (Weather Data)")
    if os.path.exists(weather_path):
        # DuckDB query to clean and fetch weather data
        query = f"""
            SELECT 
                strptime(date, '%Y-%m-%dT%H:%M:%S.%f') as timestamp, 
                air_temperature, 
                track_temperature,
                humidity
            FROM read_parquet('{weather_path}')
            ORDER BY date ASC
        """
        weather_df = query_duckdb(query)
        if not weather_df.empty:
            fig = px.line(
                weather_df, 
                x="timestamp", 
                y=["air_temperature", "track_temperature"],
                labels={"value": "Temperatura (°C)", "timestamp": "Horário"},
                title="Evolução da Temperatura no GP",
                color_discrete_sequence=["#ff1801", "#3b82f6"]
            )
            fig.update_layout(template="plotly_dark", paper_bgcolor="#161920", plot_bgcolor="#161920")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Erro ao processar dados de clima.")
    else:
        st.info("Aguardando ingestão de dados de clima (weather.parquet).")

with col2:
    st.subheader("⏱️ Histórico de Distâncias (Race Gaps)")
    if os.path.exists(intervals_path) and os.path.exists(drivers_path):
        # DuckDB Analytical JOIN
        query = f"""
            SELECT DISTINCT
                d.full_name as Piloto,
                d.team_name as Escuderia,
                d.name_acronym as Sigla,
                i.gap_to_leader as GapLeader,
                i.interval as Intervalo
            FROM read_parquet('{intervals_path}') i
            JOIN read_parquet('{drivers_path}') d ON CAST(i.driver_number AS INTEGER) = CAST(d.driver_number AS INTEGER)
            WHERE i.gap_to_leader IS NOT NULL AND i.gap_to_leader != 'None'
            LIMIT 15
        """
        gaps_df = query_duckdb(query)
        if not gaps_df.empty:
            st.dataframe(gaps_df, use_container_width=True)
        else:
            st.info("Sem dados de intervalos estruturados na última volta.")
    else:
        st.info("Execute a ingestão para processar o JOIN analítico de drivers e intervalos.")

st.markdown("---")

col3, col4 = st.columns([1, 1])

with col3:
    st.subheader("🏁 Grid de Pilotos Oficial")
    if os.path.exists(drivers_path):
        query = f"""
            SELECT DISTINCT 
                driver_number as Numero, 
                full_name as Nome, 
                team_name as Escuderia,
                country_code as Pais
            FROM read_parquet('{drivers_path}')
            ORDER BY team_name, driver_number
        """
        grid_df = query_duckdb(query)
        if not grid_df.empty:
            st.dataframe(grid_df, use_container_width=True)
    else:
        st.info("Grid de pilotos indisponível localmente.")

with col4:
    st.subheader("⚡ Telemetria Real-Time do Carro")
    if os.path.exists(car_data_path):
        query = f"""
            SELECT 
                date, 
                speed, 
                rpm, 
                gear
            FROM read_parquet('{car_data_path}')
            ORDER BY date ASC
            LIMIT 500
        """
        tel_df = query_duckdb(query)
        if not tel_df.empty:
            fig_tel = px.line(
                tel_df,
                y="speed",
                title="Curva de Velocidade (Telemetria)",
                labels={"value": "Velocidade (km/h)", "index": "Amostras"},
                color_discrete_sequence=["#22c55e"]
            )
            fig_tel.update_layout(template="plotly_dark", paper_bgcolor="#161920", plot_bgcolor="#161920")
            st.plotly_chart(fig_tel, use_container_width=True)
        else:
            st.info("Sem telemetria ativa para esta sessão.")
    else:
        st.info("Telemetria (car_data.parquet) não ingerida ou indisponível para esta sessão de corrida.")

st.caption("DuckDB Local In-Memory Engine - Projetado por Roberto Nascimento (Engenheiro de Dados)")
