CREATE OR REPLACE VIEW cross_role_risk AS
WITH driver_rollup AS (
  SELECT
    driver_id,
    MAX(CAST(geofence_dist_m > 750 OR off_hours_flag = 1 AS INTEGER)) AS gps_or_offhours,
    MAX(CAST(refund_count_30d >= 3 AS INTEGER)) AS refund_cluster,
    MAX(CAST(emulator_flag = 1 OR payout_change_72h = 1 AS INTEGER)) AS shared_device_or_payout,
    MAX(CAST(gps_mock_flag + emulator_flag + rooted_device_flag + payout_change_72h + off_hours_flag >= 2 AS INTEGER)) AS driver_risk
  FROM spark_trips
  GROUP BY driver_id
)
SELECT *,
  driver_risk + gps_or_offhours + refund_cluster + shared_device_or_payout AS collusion_signal_count,
  CAST(driver_risk + gps_or_offhours + refund_cluster + shared_device_or_payout >= 2 AS INTEGER) AS collusion_flag
FROM driver_rollup;

