from __future__ import annotations

import duckdb
import pandas as pd
from pathlib import Path
from sentinel.signals import run_signals


def test_signal_23_exclusion_logic(tmp_path):
    # Load the actual SQL query for signal 23
    sql_path = Path("sql/signals/23_gps_spoofing_impossible_transit.sql")
    query = sql_path.read_text(encoding="utf-8")
    
    # Construct mock data tracing each enumerated legitimate mimic vs. real fraud
    trips_data = [
        # D_LEGIT_HIGHWAY: NY to Newark to Trenton (normal driving times, speeds < 120 kph)
        {"driver_id": "D_LEGIT_HIGHWAY", "trip_id": "T1", "trip_start_ts": "2026-07-05 12:00:00", 
         "pickup_lat": 40.7128, "pickup_lon": -74.0060, "dropoff_lat": 40.7356, "dropoff_lon": -74.1724,
         "gps_accuracy_m": 15, "emulator_flag": 0, "gps_mock_flag": 0, "rooted_device_flag": 0},
        {"driver_id": "D_LEGIT_HIGHWAY", "trip_id": "T2", "trip_start_ts": "2026-07-05 13:00:00", 
         "pickup_lat": 40.7356, "pickup_lon": -74.1724, "dropoff_lat": 40.2170, "dropoff_lon": -74.7429,
         "gps_accuracy_m": 15, "emulator_flag": 0, "gps_mock_flag": 0, "rooted_device_flag": 0},
        {"driver_id": "D_LEGIT_HIGHWAY", "trip_id": "T3", "trip_start_ts": "2026-07-05 14:00:00", 
         "pickup_lat": 40.2170, "pickup_lon": -74.7429, "dropoff_lat": 40.2200, "dropoff_lon": -74.7500,
         "gps_accuracy_m": 15, "emulator_flag": 0, "gps_mock_flag": 0, "rooted_device_flag": 0},
         
        # D_LEGIT_TRAIN (Legitimate multi-modal transit): fast speed (>180 kph) but no device compromise
        {"driver_id": "D_LEGIT_TRAIN", "trip_id": "T4", "trip_start_ts": "2026-07-05 12:00:00", 
         "pickup_lat": 40.7128, "pickup_lon": -74.0060, "dropoff_lat": 40.7200, "dropoff_lon": -74.0100,
         "gps_accuracy_m": 10, "emulator_flag": 0, "gps_mock_flag": 0, "rooted_device_flag": 0},
        {"driver_id": "D_LEGIT_TRAIN", "trip_id": "T5", "trip_start_ts": "2026-07-05 12:02:00", 
         "pickup_lat": 39.9526, "pickup_lon": -75.1652, "dropoff_lat": 39.9600, "dropoff_lon": -75.1700,
         "gps_accuracy_m": 10, "emulator_flag": 0, "gps_mock_flag": 0, "rooted_device_flag": 0},
        {"driver_id": "D_LEGIT_TRAIN", "trip_id": "T6", "trip_start_ts": "2026-07-05 12:04:00", 
         "pickup_lat": 39.2904, "pickup_lon": -76.6122, "dropoff_lat": 39.3000, "dropoff_lon": -76.6200,
         "gps_accuracy_m": 10, "emulator_flag": 0, "gps_mock_flag": 0, "rooted_device_flag": 0},
         
        # D_GPS_MULTIPATH (Urban Canyon): high-speed jump but accuracy is bad (>80m)
        {"driver_id": "D_GPS_MULTIPATH", "trip_id": "T7", "trip_start_ts": "2026-07-05 12:00:00", 
         "pickup_lat": 40.7128, "pickup_lon": -74.0060, "dropoff_lat": 40.7200, "dropoff_lon": -74.0100,
         "gps_accuracy_m": 120, "emulator_flag": 1, "gps_mock_flag": 1, "rooted_device_flag": 0},
        {"driver_id": "D_GPS_MULTIPATH", "trip_id": "T8", "trip_start_ts": "2026-07-05 12:02:00", 
         "pickup_lat": 34.0522, "pickup_lon": -118.2437, "dropoff_lat": 34.0600, "dropoff_lon": -118.2500,
         "gps_accuracy_m": 120, "emulator_flag": 1, "gps_mock_flag": 1, "rooted_device_flag": 0},
        {"driver_id": "D_GPS_MULTIPATH", "trip_id": "T9", "trip_start_ts": "2026-07-05 12:04:00", 
         "pickup_lat": 48.8566, "pickup_lon": 2.3522, "dropoff_lat": 48.8600, "dropoff_lon": 2.3600,
         "gps_accuracy_m": 120, "emulator_flag": 1, "gps_mock_flag": 1, "rooted_device_flag": 0},
         
        # D_FRAUD_SPOOF: physically impossible travel corroborated by emulator device and high GPS accuracy
        {"driver_id": "D_FRAUD_SPOOF", "trip_id": "T10", "trip_start_ts": "2026-07-05 12:00:00", 
         "pickup_lat": 40.7128, "pickup_lon": -74.0060, "dropoff_lat": 40.7200, "dropoff_lon": -74.0100,
         "gps_accuracy_m": 10, "emulator_flag": 1, "gps_mock_flag": 0, "rooted_device_flag": 0},
        {"driver_id": "D_FRAUD_SPOOF", "trip_id": "T11", "trip_start_ts": "2026-07-05 12:02:00", 
         "pickup_lat": 34.0522, "pickup_lon": -118.2437, "dropoff_lat": 34.0600, "dropoff_lon": -118.2500,
         "gps_accuracy_m": 10, "emulator_flag": 1, "gps_mock_flag": 0, "rooted_device_flag": 0},
        {"driver_id": "D_FRAUD_SPOOF", "trip_id": "T12", "trip_start_ts": "2026-07-05 12:04:00", 
         "pickup_lat": 48.8566, "pickup_lon": 2.3522, "dropoff_lat": 48.8600, "dropoff_lon": 2.3600,
         "gps_accuracy_m": 10, "emulator_flag": 1, "gps_mock_flag": 0, "rooted_device_flag": 0}
    ]
    df = pd.DataFrame(trips_data)
    df["trip_start_ts"] = pd.to_datetime(df["trip_start_ts"])
    
    con = duckdb.connect()
    con.execute(
        """
        CREATE OR REPLACE MACRO haversine_km(lat1, lon1, lat2, lon2) AS
          2 * 6371 * asin(sqrt(
            pow(sin(radians(lat2-lat1)/2), 2) +
            cos(radians(lat1))*cos(radians(lat2))*pow(sin(radians(lon2-lon1)/2), 2)
          ))
        """
    )
    con.register("spark_trips", df)
    
    result = con.execute(query).df()
    triggered_drivers = set(result["driver_id"])
    
    assert "D_FRAUD_SPOOF" in triggered_drivers
    assert "D_LEGIT_HIGHWAY" not in triggered_drivers
    assert "D_LEGIT_TRAIN" not in triggered_drivers
    assert "D_GPS_MULTIPATH" not in triggered_drivers
