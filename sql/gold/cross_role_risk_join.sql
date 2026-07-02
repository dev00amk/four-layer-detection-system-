CREATE OR REPLACE VIEW cross_role_risk AS
WITH driver_rollup AS (
  SELECT
    driver_id,
    MAX(COALESCE(CAST(geofence_dist_m > 750 OR off_hours_flag = 1 AS INTEGER), 0)) AS gps_or_offhours,
    MAX(COALESCE(CAST(refund_count_30d >= 3 AS INTEGER), 0)) AS refund_cluster,
    MAX(COALESCE(CAST(emulator_flag = 1 OR payout_change_72h = 1 AS INTEGER), 0)) AS shared_device_or_payout,
    MAX(COALESCE(CAST(
      COALESCE(gps_mock_flag, 0) + COALESCE(emulator_flag, 0) + COALESCE(rooted_device_flag, 0)
      + COALESCE(payout_change_72h, 0) + COALESCE(off_hours_flag, 0) >= 2 AS INTEGER
    ), 0)) AS driver_risk
  FROM spark_trips
  GROUP BY driver_id
)
SELECT *,
  driver_risk + gps_or_offhours + refund_cluster + shared_device_or_payout AS collusion_signal_count,
  CAST(driver_risk + gps_or_offhours + refund_cluster + shared_device_or_payout >= 2 AS INTEGER) AS collusion_flag
FROM driver_rollup;

