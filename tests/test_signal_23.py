from __future__ import annotations

import duckdb
import pandas as pd
from pathlib import Path
import pytest


def get_haversine_python(lat1, lon1, lat2, lon2):
    import numpy as np
    # Vectorized Haversine distance in km
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat/2.0)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2.0)**2
    c = 2 * np.arcsin(np.sqrt(a))
    return 6371 * c


def get_mock_trips_df():
    trips_data = [
        # 1. D_LEGIT_HIGHWAY: normal driving times (speed <= 70 km/h)
        {"driver_id": "D_LEGIT_HIGHWAY", "trip_id": "T1", "trip_start_ts": "2026-07-05 12:00:00", 
         "pickup_lat": 40.7128, "pickup_lon": -74.0060, "dropoff_lat": 40.7356, "dropoff_lon": -74.1724,
         "gps_accuracy_m": 15, "emulator_flag": 0, "gps_mock_flag": 0},
        {"driver_id": "D_LEGIT_HIGHWAY", "trip_id": "T2", "trip_start_ts": "2026-07-05 13:00:00", 
         "pickup_lat": 40.7356, "pickup_lon": -74.1724, "dropoff_lat": 40.2170, "dropoff_lon": -74.7429,
         "gps_accuracy_m": 15, "emulator_flag": 0, "gps_mock_flag": 0},
        {"driver_id": "D_LEGIT_HIGHWAY", "trip_id": "T3", "trip_start_ts": "2026-07-05 14:00:00", 
         "pickup_lat": 40.2170, "pickup_lon": -74.7429, "dropoff_lat": 39.9526, "dropoff_lon": -75.1652,
         "gps_accuracy_m": 15, "emulator_flag": 0, "gps_mock_flag": 0},

        # 2. D_LEGIT_TRAIN: NY -> Philly -> Baltimore. Speed ~245 km/h. Clean phone.
        {"driver_id": "D_LEGIT_TRAIN", "trip_id": "T4", "trip_start_ts": "2026-07-05 12:00:00", 
         "pickup_lat": 40.7128, "pickup_lon": -74.0060, "dropoff_lat": 40.7200, "dropoff_lon": -74.0100,
         "gps_accuracy_m": 10, "emulator_flag": 0, "gps_mock_flag": 0},
        {"driver_id": "D_LEGIT_TRAIN", "trip_id": "T5", "trip_start_ts": "2026-07-05 12:37:22", 
         "pickup_lat": 39.9526, "pickup_lon": -75.1652, "dropoff_lat": 39.9600, "dropoff_lon": -75.1700,
         "gps_accuracy_m": 10, "emulator_flag": 0, "gps_mock_flag": 0},
        {"driver_id": "D_LEGIT_TRAIN", "trip_id": "T6", "trip_start_ts": "2026-07-05 13:15:31", 
         "pickup_lat": 39.2904, "pickup_lon": -76.6122, "dropoff_lat": 39.3000, "dropoff_lon": -76.6200,
         "gps_accuracy_m": 10, "emulator_flag": 0, "gps_mock_flag": 0},

        # 3. D_GPS_MULTIPATH: High speed jumps (>180 km/h) but poor GPS accuracy (>80m). Clean phone.
        {"driver_id": "D_GPS_MULTIPATH", "trip_id": "T7", "trip_start_ts": "2026-07-05 12:00:00", 
         "pickup_lat": 40.7128, "pickup_lon": -74.0060, "dropoff_lat": 40.7200, "dropoff_lon": -74.0100,
         "gps_accuracy_m": 120, "emulator_flag": 0, "gps_mock_flag": 0},
        {"driver_id": "D_GPS_MULTIPATH", "trip_id": "T8", "trip_start_ts": "2026-07-05 12:37:22", 
         "pickup_lat": 39.9526, "pickup_lon": -75.1652, "dropoff_lat": 39.9600, "dropoff_lon": -75.1700,
         "gps_accuracy_m": 120, "emulator_flag": 0, "gps_mock_flag": 0},
        {"driver_id": "D_GPS_MULTIPATH", "trip_id": "T9", "trip_start_ts": "2026-07-05 13:15:31", 
         "pickup_lat": 39.2904, "pickup_lon": -76.6122, "dropoff_lat": 39.3000, "dropoff_lon": -76.6200,
         "gps_accuracy_m": 120, "emulator_flag": 0, "gps_mock_flag": 0},

        # 4. D_SINGLE_GLITCH: NY -> LA (speed 120,000 km/h) but only 1 segment.
        {"driver_id": "D_SINGLE_GLITCH", "trip_id": "T10", "trip_start_ts": "2026-07-05 12:00:00", 
         "pickup_lat": 40.7128, "pickup_lon": -74.0060, "dropoff_lat": 40.7200, "dropoff_lon": -74.0100,
         "gps_accuracy_m": 10, "emulator_flag": 1, "gps_mock_flag": 0},
        {"driver_id": "D_SINGLE_GLITCH", "trip_id": "T11", "trip_start_ts": "2026-07-05 12:02:00", 
         "pickup_lat": 34.0522, "pickup_lon": -118.2437, "dropoff_lat": 34.0600, "dropoff_lon": -118.2500,
         "gps_accuracy_m": 10, "emulator_flag": 1, "gps_mock_flag": 0},

        # 5. D_FRAUD_SPOOF_TIER1: Fast jumps (>400 km/h) on clean device. Triggers Tier 1.
        {"driver_id": "D_FRAUD_SPOOF_TIER1", "trip_id": "T12", "trip_start_ts": "2026-07-05 12:00:00", 
         "pickup_lat": 40.7128, "pickup_lon": -74.0060, "dropoff_lat": 40.7200, "dropoff_lon": -74.0100,
         "gps_accuracy_m": 10, "emulator_flag": 0, "gps_mock_flag": 0},
        {"driver_id": "D_FRAUD_SPOOF_TIER1", "trip_id": "T13", "trip_start_ts": "2026-07-05 12:02:00", 
         "pickup_lat": 34.0522, "pickup_lon": -118.2437, "dropoff_lat": 34.0600, "dropoff_lon": -118.2500,
         "gps_accuracy_m": 10, "emulator_flag": 0, "gps_mock_flag": 0},
        {"driver_id": "D_FRAUD_SPOOF_TIER1", "trip_id": "T14", "trip_start_ts": "2026-07-05 12:04:00", 
         "pickup_lat": 48.8566, "pickup_lon": 2.3522, "dropoff_lat": 48.8600, "dropoff_lon": 2.3600,
         "gps_accuracy_m": 10, "emulator_flag": 0, "gps_mock_flag": 0},

        # 6. D_FRAUD_SPOOF_TIER2: Train-like speed (250 km/h) on emulator. Triggers Tier 2.
        {"driver_id": "D_FRAUD_SPOOF_TIER2", "trip_id": "T15", "trip_start_ts": "2026-07-05 12:00:00", 
         "pickup_lat": 40.7128, "pickup_lon": -74.0060, "dropoff_lat": 40.7200, "dropoff_lon": -74.0100,
         "gps_accuracy_m": 10, "emulator_flag": 1, "gps_mock_flag": 0},
        {"driver_id": "D_FRAUD_SPOOF_TIER2", "trip_id": "T16", "trip_start_ts": "2026-07-05 12:37:22", 
         "pickup_lat": 39.9526, "pickup_lon": -75.1652, "dropoff_lat": 39.9600, "dropoff_lon": -75.1700,
         "gps_accuracy_m": 10, "emulator_flag": 1, "gps_mock_flag": 0},
        {"driver_id": "D_FRAUD_SPOOF_TIER2", "trip_id": "T17", "trip_start_ts": "2026-07-05 13:15:31", 
         "pickup_lat": 39.2904, "pickup_lon": -76.6122, "dropoff_lat": 39.3000, "dropoff_lon": -76.6200,
         "gps_accuracy_m": 10, "emulator_flag": 1, "gps_mock_flag": 0},

        # 7. D_FRAUD_BLIND_SPOT: Train-like speed (250 km/h) on clean device. Evades (Expected Blind Spot).
        {"driver_id": "D_FRAUD_BLIND_SPOT", "trip_id": "T18", "trip_start_ts": "2026-07-05 12:00:00", 
         "pickup_lat": 40.7128, "pickup_lon": -74.0060, "dropoff_lat": 40.7200, "dropoff_lon": -74.0100,
         "gps_accuracy_m": 10, "emulator_flag": 0, "gps_mock_flag": 0},
        {"driver_id": "D_FRAUD_BLIND_SPOT", "trip_id": "T19", "trip_start_ts": "2026-07-05 12:37:22", 
         "pickup_lat": 39.9526, "pickup_lon": -75.1652, "dropoff_lat": 39.9600, "dropoff_lon": -75.1700,
         "gps_accuracy_m": 10, "emulator_flag": 0, "gps_mock_flag": 0},
        {"driver_id": "D_FRAUD_BLIND_SPOT", "trip_id": "T20", "trip_start_ts": "2026-07-05 13:15:31", 
         "pickup_lat": 39.2904, "pickup_lon": -76.6122, "dropoff_lat": 39.3000, "dropoff_lon": -76.6200,
         "gps_accuracy_m": 10, "emulator_flag": 0, "gps_mock_flag": 0},

        # 8. D_LEAK: Mixed segments. 1 flagged segment and 1 clean segment in Tier 2 band (250 km/h).
        # Should NOT trigger because device flags are not present on BOTH segments.
        {"driver_id": "D_LEAK", "trip_id": "T21", "trip_start_ts": "2026-07-05 12:00:00", 
         "pickup_lat": 40.7128, "pickup_lon": -74.0060, "dropoff_lat": 40.7200, "dropoff_lon": -74.0100,
         "gps_accuracy_m": 10, "emulator_flag": 1, "gps_mock_flag": 0},
        {"driver_id": "D_LEAK", "trip_id": "T22", "trip_start_ts": "2026-07-05 12:37:22", 
         "pickup_lat": 39.9526, "pickup_lon": -75.1652, "dropoff_lat": 39.9600, "dropoff_lon": -75.1700,
         "gps_accuracy_m": 10, "emulator_flag": 1, "gps_mock_flag": 0}, # Flagged
        {"driver_id": "D_LEAK", "trip_id": "T23", "trip_start_ts": "2026-07-05 13:15:31", 
         "pickup_lat": 39.2904, "pickup_lon": -76.6122, "dropoff_lat": 39.3000, "dropoff_lon": -76.6200,
         "gps_accuracy_m": 10, "emulator_flag": 0, "gps_mock_flag": 0}  # Clean
    ]
    df = pd.DataFrame(trips_data)
    df["trip_start_ts"] = pd.to_datetime(df["trip_start_ts"])
    return df


def test_fixtures_are_physically_honest():
    df = get_mock_trips_df()
    # Check D_LEGIT_TRAIN speed
    # NYC dropoff: (40.7200, -74.0100) -> Philly pickup: (39.9526, -75.1652)
    dist1 = get_haversine_python(40.7200, -74.0100, 39.9526, -75.1652)
    time_hours1 = 2242.0 / 3600.0
    speed1 = dist1 / time_hours1
    
    # Philly dropoff: (39.9600, -75.1700) -> Baltimore pickup: (39.2904, -76.6122)
    dist2 = get_haversine_python(39.9600, -75.1700, 39.2904, -76.6122)
    time_hours2 = 2289.0 / 3600.0
    speed2 = dist2 / time_hours2
    
    # Verify speeds are realistic for bullet trains (e.g. between 180 and 300 km/h)
    assert 180 < speed1 < 300, f"Speed 1 is physically dishonest: {speed1} km/h"
    assert 180 < speed2 < 300, f"Speed 2 is physically dishonest: {speed2} km/h"


def run_duckdb_signal(df):
    sql_path = Path("sql/signals/23_gps_spoofing_impossible_transit.sql")
    query = sql_path.read_text(encoding="utf-8")
    
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
    return set(result["driver_id"])


def test_legit_highway_driver():
    df = get_mock_trips_df()
    triggered = run_duckdb_signal(df)
    assert "D_LEGIT_HIGHWAY" not in triggered


def test_legit_rail_passenger_clean_phone():
    df = get_mock_trips_df()
    triggered = run_duckdb_signal(df)
    assert "D_LEGIT_TRAIN" not in triggered


def test_gps_multipath_urban_canyon():
    df = get_mock_trips_df()
    triggered = run_duckdb_signal(df)
    assert "D_GPS_MULTIPATH" not in triggered


def test_single_impossible_segment_glitch():
    df = get_mock_trips_df()
    triggered = run_duckdb_signal(df)
    assert "D_SINGLE_GLITCH" not in triggered


def test_tier1_spoofer_clean_device():
    df = get_mock_trips_df()
    triggered = run_duckdb_signal(df)
    assert "D_FRAUD_SPOOF_TIER1" in triggered


def test_tier2_spoofer_emulator():
    df = get_mock_trips_df()
    triggered = run_duckdb_signal(df)
    assert "D_FRAUD_SPOOF_TIER2" in triggered


def test_acknowledged_blind_spot_clean_device_in_tier2_band_evades():
    df = get_mock_trips_df()
    triggered = run_duckdb_signal(df)
    assert "D_FRAUD_BLIND_SPOT" not in triggered


def test_leak_mixed_driver():
    df = get_mock_trips_df()
    triggered = run_duckdb_signal(df)
    assert "D_LEAK" not in triggered
