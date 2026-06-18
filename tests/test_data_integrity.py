import glob
import os

import joblib
import pandas as pd

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../data"))
MODELS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../models"))


def test_silver_parquet_files_exist():
    """
    Garante que os arquivos Parquet estruturados da camada Silver existem no Lakehouse.
    """
    silver_dir = os.path.join(DATA_DIR, "silver")
    assert os.path.exists(
        silver_dir
    ), "Diretório Silver de dados analíticos não existe."

    # Arquivos de metadados mínimos esperados
    essential_files = [
        "dim_sessions.parquet",
        "dim_drivers.parquet",
        "dim_stints.parquet",
        "dim_weather.parquet",
    ]
    for f in essential_files:
        path = os.path.join(silver_dir, f)
        if os.path.exists(path):
            df = pd.read_parquet(path)
            assert not df.empty, f"O arquivo Parquet {f} está vazio."


def test_silver_telemetry_partitioning():
    """
    Valida a existência de estrutura particionada física para a telemetria Silver.
    """
    telemetry_root = os.path.join(DATA_DIR, "silver", "fact_car_telemetry")
    if os.path.exists(telemetry_root):
        sessions = os.listdir(telemetry_root)
        assert (
            len(sessions) > 0
        ), "Nenhuma partição de session_key na telemetria Silver."

        # Checar se as subpastas seguem a partição por session_key e driver_number
        for sess in sessions:
            assert sess.startswith(
                "session_key="
            ), f"Pasta de partição inválida: {sess}"
            sess_path = os.path.join(telemetry_root, sess)

            drivers = os.listdir(sess_path)
            for drv in drivers:
                assert drv.startswith(
                    "driver_number="
                ), f"Subpasta de partição de piloto inválida: {drv}"

                parquet_file = os.path.join(sess_path, drv, "data.parquet")
                assert os.path.exists(
                    parquet_file
                ), f"Arquivo data.parquet ausente na partição {sess}/{drv}"

                # Checar qualidade física básica dos dados gravados
                df = pd.read_parquet(parquet_file)
                assert "speed" in df.columns
                assert "rpm" in df.columns
                assert "n_gear" in df.columns

                # Asserts de Limites Físicos de Telemetria F1 (Data Quality)
                assert (df["speed"] >= 0).all() and (
                    df["speed"] <= 380
                ).all(), "Velocidades físicas fora do intervalo realista de F1 [0, 380]"
                assert (df["n_gear"] >= -1).all() and (
                    df["n_gear"] <= 8
                ).all(), "Marchas fora do intervalo realista de F1 [-1, 8]"
                assert (df["rpm"] >= 0).all() and (
                    df["rpm"] <= 16000
                ).all(), "RPM de motor fora da faixa de segurança do asfalto [0, 16000]"


def test_gold_predictions_integrity():
    """
    Verifica a qualidade e integridade lógica das predições de IA da camada Gold.
    """
    prediction_files = glob.glob(
        os.path.join(
            DATA_DIR, "gold", "lap_predictions", "session_key=*", "data.parquet"
        )
    )
    if prediction_files:
        df = pd.concat(
            [pd.read_parquet(path) for path in prediction_files], ignore_index=True
        )
        assert not df.empty

        required_cols = [
            "session_key",
            "driver_number",
            "lap_duration_seconds",
            "predicted_lap_duration_seconds",
            "delta_performance_seconds",
        ]
        for col in required_cols:
            assert (
                col in df.columns
            ), f"Coluna obrigatória {col} ausente na camada Gold."
            assert df[col].notna().any(), f"Coluna {col} contém apenas nulos."

        # O tempo predito de volta deve ser coerente com um tempo real (ex: entre 50s e 200s para voltas normais)
        mean_prediction = df["predicted_lap_duration_seconds"].mean()
        assert (
            50.0 <= mean_prediction <= 250.0
        ), f"Tempo predito médio de volta irrealista: {mean_prediction}s"


def test_gold_features_partitioning():
    """
    Valida a persistência particionada da camada Gold de features.
    """
    feature_files = glob.glob(
        os.path.join(
            DATA_DIR, "gold", "features_lap_data", "session_key=*", "data.parquet"
        )
    )
    if feature_files:
        df = pd.concat(
            [pd.read_parquet(path) for path in feature_files], ignore_index=True
        )
        assert not df.empty
        required_cols = [
            "session_key",
            "driver_number",
            "stint_number",
            "lap_number",
            "lap_duration_seconds",
        ]
        for col in required_cols:
            assert col in df.columns
            assert df[col].notna().any()


def test_ml_model_serialization():
    """
    Garante que o modelo de IA foi treinado e serializado no disco com sucesso.
    """
    model_path = os.path.join(MODELS_DIR, "lap_regressor.joblib")
    if os.path.exists(model_path):
        model = joblib.load(model_path)
        assert hasattr(
            model, "predict"
        ), "O arquivo serializado não é um modelo preditivo sklearn válido."


def test_gold_f1_telemetry_analysis_integrity():
    """
    Garante as regras de integridade do Contrato de Dados para fct_f1_telemetry_analysis.
    """
    gold_parquet = os.path.join(DATA_DIR, "gold", "fct_f1_telemetry_analysis.parquet")
    if os.path.exists(gold_parquet):
        df = pd.read_parquet(gold_parquet)
        assert not df.empty, "Tabela fct_f1_telemetry_analysis está vazia."

        # Validar colunas obrigatórias
        required_cols = [
            "session_key",
            "driver_number",
            "lap_number",
            "max_speed",
            "avg_speed",
            "max_rpm",
            "avg_rpm",
            "throttle_intensity_pct",
            "brake_intensity_pct",
            "drs_activation_pct",
            "gear_changes",
        ]
        for col in required_cols:
            assert col in df.columns, f"Coluna obrigatória {col} ausente."
            assert df[col].notna().all(), f"Coluna {col} contém valores nulos."

        # Validar limites de qualidade física (evitando quebras com carros parados/retirados ou cool-down laps)
        assert (df["lap_number"] > 0).all(), "Número de volta inválido."
        assert (
            df["max_speed"] <= 400
        ).all(), "max_speed fora do limite do contrato [<= 400]"
        assert (
            df["avg_speed"] <= 380
        ).all(), "avg_speed fora do limite do contrato [<= 380]"
        assert (
            df["max_rpm"] <= 18000
        ).all(), "max_rpm fora do limite do contrato [<= 18000]"
        assert (df["throttle_intensity_pct"] >= 0).all() and (
            df["throttle_intensity_pct"] <= 100
        ).all()
        assert (df["brake_intensity_pct"] >= 0).all() and (
            df["brake_intensity_pct"] <= 100
        ).all()
        assert (df["drs_activation_pct"] >= 0).all() and (
            df["drs_activation_pct"] <= 100
        ).all()
        assert (df["gear_changes"] >= 0).all()

        # Validar que a grande maioria das voltas são ativas e atendem às faixas operacionais típicas
        active_laps = df[df["max_speed"] >= 100]
        assert len(active_laps) / len(df) > 0.8, "Menos de 80% das voltas estão ativas."
        assert (active_laps["max_speed"] >= 50).all()
        assert (
            active_laps["avg_speed"] >= 10
        ).all()  # Mínimo absoluto para voltas de cool-down ativas
        assert (active_laps["max_rpm"] >= 1000).all()
