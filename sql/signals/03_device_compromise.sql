-- Signal: device_compromise
-- Consolidates row-level mock-location, emulator, and root indicators.
-- Frequency gate: require >=2 compromised trips to avoid one-off telemetry noise.
SELECT driver_id
FROM spark_trips
GROUP BY driver_id
HAVING SUM(
    CASE WHEN gps_mock_flag = 1
           OR emulator_flag = 1
           OR rooted_device_flag = 1
         THEN 1 ELSE 0 END
) >= 2;
