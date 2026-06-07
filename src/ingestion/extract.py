import os
import requests
import pandas as pd
from tenacity import retry, stop_after_attempt, wait_exponential

BASE_URL = "https://api.openf1.org/v1"
DATA_DIR = os.path.join(os.path.dirname(__file__), "../../data")

os.makedirs(DATA_DIR, exist_ok=True)

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def fetch_endpoint(endpoint: str, params: dict = None) -> list:
    url = f"{BASE_URL}/{endpoint}"
    print(f"Fetching {url} with params {params}")
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            print(f"Endpoint {endpoint} returned 404 (No data). Treating as empty.")
            return None
        raise e

def extract_latest_session_data():
    """
    Extracts summary data for the most recent session, including weather,
    pit stops, intervals, drivers, and a sample of high-frequency car telemetry.
    """
    # 1. Get latest sessions for 2024 (as baseline)
    sessions = fetch_endpoint("sessions", {"year": 2024})
    if not sessions:
        print("No sessions found.")
        return
    
    sessions_df = pd.DataFrame(sessions)
    sessions_df["date_start"] = pd.to_datetime(sessions_df["date_start"])
    latest_session = sessions_df.sort_values("date_start", ascending=False).iloc[0]
    session_key = int(latest_session["session_key"])
    
    print(f"Latest Session: {latest_session["session_name"]} (Key: {session_key})")
    
    # 2. Extract standard metadata
    endpoints = ["weather", "pit_stops", "intervals", "drivers"]
    for ep in endpoints:
        print(f"Extracting {ep}...")
        data = fetch_endpoint(ep, {"session_key": session_key})
        if data:
            df = pd.DataFrame(data)
            
            # Data quality fix for PyArrow mixed types conversions
            if ep == "intervals":
                for col in ["gap_to_leader", "interval"]:
                    if col in df.columns:
                        df[col] = df[col].astype(str)
                        
            output_path = os.path.join(DATA_DIR, f"{ep}.parquet")
            df.to_parquet(output_path, index=False)
            print(f"Saved {ep} to {output_path}")
        else:
            print(f"No data for {ep} in session {session_key}")
            
    # 3. Extract high-frequency telemetry (car_data) for the first driver in the session
    drivers_data = fetch_endpoint("drivers", {"session_key": session_key})
    if drivers_data:
        first_driver = drivers_data[0]
        driver_number = int(first_driver["driver_number"])
        driver_name = first_driver["full_name"]
        print(f"Extracting telemetry for driver {driver_name} (#{driver_number})...")
        
        telemetry_data = fetch_endpoint("car_data", {
            "session_key": session_key,
            "driver_number": driver_number,
            "limit": 5000
        })
        
        if telemetry_data:
            df_tel = pd.DataFrame(telemetry_data)
            output_path = os.path.join(DATA_DIR, "car_data.parquet")
            df_tel.to_parquet(output_path, index=False)
            print(f"Saved car_data (telemetry) to {output_path}")
        else:
            print(f"No telemetry data found for driver {driver_name} in session {session_key}")

if __name__ == "__main__":
    print("Starting OpenF1 Data Ingestion...")
    extract_latest_session_data()
    print("Ingestion complete.")
