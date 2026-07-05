from __future__ import annotations

import duckdb
import pandas as pd
from pathlib import Path
import pytest


def get_mock_trips_df():
    trips_data = [
        # 1. D_LEGIT_UPGRADE: permanent device upgrade (unidirectional migration DEV_UP_1 -> DEV_UP_2)
        {"driver_id": "D_UP_A", "trip_id": "T1", "trip_start_ts": "2026-07-05 12:00:00", "trip_end_ts": "2026-07-05 12:30:00",
         "pickup_lat": 40.7128, "pickup_lon": -74.0060, "device_id": "DEV_UP_1", "payout_account": "BANK_UP_A", "payout_change_72h": 0, "emulator_flag": 0, "rooted_device_flag": 0},
        {"driver_id": "D_UP_A", "trip_id": "T2", "trip_start_ts": "2026-07-05 13:00:00", "trip_end_ts": "2026-07-05 13:30:00",
         "pickup_lat": 40.7128, "pickup_lon": -74.0060, "device_id": "DEV_UP_2", "payout_account": "BANK_UP_A", "payout_change_72h": 0, "emulator_flag": 0, "rooted_device_flag": 0},
        {"driver_id": "D_UP_A", "trip_id": "T3", "trip_start_ts": "2026-07-05 14:00:00", "trip_end_ts": "2026-07-05 14:30:00",
         "pickup_lat": 40.7128, "pickup_lon": -74.0060, "device_id": "DEV_UP_2", "payout_account": "BANK_UP_A", "payout_change_72h": 0, "emulator_flag": 0, "rooted_device_flag": 0},

        # 2. D_LEGIT_RESALE: Device sold (A -> B permanent transfer DEV_RES)
        {"driver_id": "D_RES_A", "trip_id": "T4", "trip_start_ts": "2026-07-05 12:00:00", "trip_end_ts": "2026-07-05 12:30:00",
         "pickup_lat": 40.7128, "pickup_lon": -74.0060, "device_id": "DEV_RES", "payout_account": "BANK_RES_A", "payout_change_72h": 0, "emulator_flag": 0, "rooted_device_flag": 0},
        {"driver_id": "D_RES_B", "trip_id": "T5", "trip_start_ts": "2026-07-06 12:00:00", "trip_end_ts": "2026-07-06 12:30:00",
         "pickup_lat": 40.7128, "pickup_lon": -74.0060, "device_id": "DEV_RES", "payout_account": "BANK_RES_B", "payout_change_72h": 0, "emulator_flag": 0, "rooted_device_flag": 0},

        # 3. D_LEGIT_FAMILY_SEQUENTIAL: spouses share family tablet sequentially (A -> B -> A) but no payout modifications
        {"driver_id": "D_FAM_A", "trip_id": "T6", "trip_start_ts": "2026-07-05 12:00:00", "trip_end_ts": "2026-07-05 12:30:00",
         "pickup_lat": 40.7128, "pickup_lon": -74.0060, "device_id": "DEV_FAM", "payout_account": "BANK_FAM_A", "payout_change_72h": 0, "emulator_flag": 0, "rooted_device_flag": 0},
        {"driver_id": "D_FAM_B", "trip_id": "T7", "trip_start_ts": "2026-07-05 13:00:00", "trip_end_ts": "2026-07-05 13:30:00",
         "pickup_lat": 40.7128, "pickup_lon": -74.0060, "device_id": "DEV_FAM", "payout_account": "BANK_FAM_B", "payout_change_72h": 0, "emulator_flag": 0, "rooted_device_flag": 0},
        {"driver_id": "D_FAM_A", "trip_id": "T8", "trip_start_ts": "2026-07-05 14:00:00", "trip_end_ts": "2026-07-05 14:30:00",
         "pickup_lat": 40.7128, "pickup_lon": -74.0060, "device_id": "DEV_FAM", "payout_account": "BANK_FAM_A", "payout_change_72h": 0, "emulator_flag": 0, "rooted_device_flag": 0},

        # 4. D_DEPOT_OVERLAP: two drivers overlap temporally at same store kiosk/geofence
        {"driver_id": "D_DEP_A", "trip_id": "T9", "trip_start_ts": "2026-07-05 12:00:00", "trip_end_ts": "2026-07-05 12:30:00",
         "pickup_lat": 40.7128, "pickup_lon": -74.0060, "device_id": "DEV_DEP", "payout_account": "BANK_DEP_A", "payout_change_72h": 0, "emulator_flag": 0, "rooted_device_flag": 0},
        {"driver_id": "D_DEP_B", "trip_id": "T10", "trip_start_ts": "2026-07-05 12:10:00", "trip_end_ts": "2026-07-05 12:40:00",
         "pickup_lat": 40.7129, "pickup_lon": -74.0061, "device_id": "DEV_DEP", "payout_account": "BANK_DEP_B", "payout_change_72h": 0, "emulator_flag": 0, "rooted_device_flag": 0},

        # 5. D_COLLISION_UNCORROBORATED: overlapping trips (>10km apart) on same device (DEV_COLL) but no payout link or change (synthetic noise)
        {"driver_id": "D_COL_A", "trip_id": "T11", "trip_start_ts": "2026-07-05 12:00:00", "trip_end_ts": "2026-07-05 12:30:00",
         "pickup_lat": 40.7128, "pickup_lon": -74.0060, "device_id": "DEV_COLL", "payout_account": "BANK_COL_A", "payout_change_72h": 0, "emulator_flag": 0, "rooted_device_flag": 0},
        {"driver_id": "D_COL_B", "trip_id": "T12", "trip_start_ts": "2026-07-05 12:10:00", "trip_end_ts": "2026-07-05 12:40:00",
         "pickup_lat": 39.9526, "pickup_lon": -75.1652, "device_id": "DEV_COLL", "payout_account": "BANK_COL_B", "payout_change_72h": 0, "emulator_flag": 0, "rooted_device_flag": 0},

        # 6. D_TIER1_CORROBORATED: overlapping trips (>10km apart) on same device (DEV_C_T1) sharing a payout account
        {"driver_id": "D_T1_A", "trip_id": "T13", "trip_start_ts": "2026-07-05 12:00:00", "trip_end_ts": "2026-07-05 12:30:00",
         "pickup_lat": 40.7128, "pickup_lon": -74.0060, "device_id": "DEV_C_T1", "payout_account": "BANK_SHARED", "payout_change_72h": 0, "emulator_flag": 0, "rooted_device_flag": 0},
        {"driver_id": "D_T1_B", "trip_id": "T14", "trip_start_ts": "2026-07-05 12:10:00", "trip_end_ts": "2026-07-05 12:40:00",
         "pickup_lat": 39.9526, "pickup_lon": -75.1652, "device_id": "DEV_C_T1", "payout_account": "BANK_SHARED", "payout_change_72h": 0, "emulator_flag": 0, "rooted_device_flag": 0},

        # 7. D_TIER2_CORROBORATED: bidirectional reuse (A -> B -> A DEV_T2) with payout_change_72h = 1 on the account
        {"driver_id": "D_T2_A", "trip_id": "T15", "trip_start_ts": "2026-07-05 12:00:00", "trip_end_ts": "2026-07-05 12:30:00",
         "pickup_lat": 40.7128, "pickup_lon": -74.0060, "device_id": "DEV_T2", "payout_account": "BANK_T2_A", "payout_change_72h": 1, "emulator_flag": 0, "rooted_device_flag": 0},
        {"driver_id": "D_T2_B", "trip_id": "T16", "trip_start_ts": "2026-07-05 13:00:00", "trip_end_ts": "2026-07-05 13:30:00",
         "pickup_lat": 40.7128, "pickup_lon": -74.0060, "device_id": "DEV_T2", "payout_account": "BANK_T2_B", "payout_change_72h": 0, "emulator_flag": 0, "rooted_device_flag": 0},
        {"driver_id": "D_T2_A", "trip_id": "T17", "trip_start_ts": "2026-07-05 14:00:00", "trip_end_ts": "2026-07-05 14:30:00",
         "pickup_lat": 40.7128, "pickup_lon": -74.0060, "device_id": "DEV_T2", "payout_account": "BANK_T2_A", "payout_change_72h": 1, "emulator_flag": 0, "rooted_device_flag": 0},

        # 8. D_BLIND_SPOT: single-device spoofer (no device hopping, stable device DEV_STABLE), no concurrent trips
        {"driver_id": "D_BLIND_A", "trip_id": "T18", "trip_start_ts": "2026-07-05 12:00:00", "trip_end_ts": "2026-07-05 12:30:00",
         "pickup_lat": 40.7128, "pickup_lon": -74.0060, "device_id": "DEV_STABLE", "payout_account": "BANK_BLIND", "payout_change_72h": 0, "emulator_flag": 0, "rooted_device_flag": 1},
        {"driver_id": "D_BLIND_A", "trip_id": "T19", "trip_start_ts": "2026-07-05 13:00:00", "trip_end_ts": "2026-07-05 13:30:00",
         "pickup_lat": 40.7128, "pickup_lon": -74.0060, "device_id": "DEV_STABLE", "payout_account": "BANK_BLIND", "payout_change_72h": 0, "emulator_flag": 0, "rooted_device_flag": 1}
    ]
    df = pd.DataFrame(trips_data)
    df["trip_start_ts"] = pd.to_datetime(df["trip_start_ts"])
    df["trip_end_ts"] = pd.to_datetime(df["trip_end_ts"])
    return df


def run_duckdb_signal(df):
    sql_path = Path("sql/signals/25_device_forensics_account_hopping.sql")
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


def test_legit_hardware_upgrade():
    df = get_mock_trips_df()
    triggered = run_duckdb_signal(df)
    assert "D_UP_A" not in triggered


def test_legit_resale():
    df = get_mock_trips_df()
    triggered = run_duckdb_signal(df)
    assert "D_RES_A" not in triggered
    assert "D_RES_B" not in triggered


def test_legit_sequential_sharing():
    df = get_mock_trips_df()
    triggered = run_duckdb_signal(df)
    assert "D_FAM_A" not in triggered
    assert "D_FAM_B" not in triggered


def test_depot_overlapping_trips():
    df = get_mock_trips_df()
    triggered = run_duckdb_signal(df)
    assert "D_DEP_A" not in triggered
    assert "D_DEP_B" not in triggered


def test_uncorroborated_overlapping_trips():
    df = get_mock_trips_df()
    triggered = run_duckdb_signal(df)
    assert "D_COL_A" not in triggered
    assert "D_COL_B" not in triggered


def test_tier1_corroborated_overlapping_trips():
    df = get_mock_trips_df()
    triggered = run_duckdb_signal(df)
    assert "D_T1_A" in triggered
    assert "D_T1_B" in triggered


def test_tier2_bidirectional_reuse_with_payout_change():
    df = get_mock_trips_df()
    triggered = run_duckdb_signal(df)
    assert "D_T2_A" in triggered
    # D_T2_B has no payout change registered, so only D_T2_A triggers
    assert "D_T2_B" not in triggered


def test_acknowledged_blind_spot_evades():
    df = get_mock_trips_df()
    triggered = run_duckdb_signal(df)
    assert "D_BLIND_A" not in triggered
