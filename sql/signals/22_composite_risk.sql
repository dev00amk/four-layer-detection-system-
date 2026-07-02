-- Signal: composite risk | Fraud: overall prioritization
SELECT driver_id FROM spark_trips GROUP BY driver_id
HAVING MAX(
  COALESCE(gps_mock_flag, 0) + COALESCE(emulator_flag, 0) + COALESCE(rooted_device_flag, 0)
  + COALESCE(payout_change_72h, 0) + COALESCE(off_hours_flag, 0)
) >= 2;

