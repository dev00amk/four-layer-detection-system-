-- Signal: device_forensics_account_hopping
-- Fraud type: account farm / ban evasion / ATO monetization
-- FP mitigation: require at least three accounts and rooted/emulated corroboration.
WITH risky_devices AS (
  SELECT device_id
  FROM spark_trips
  GROUP BY device_id
  HAVING COUNT(DISTINCT driver_id) >= 3
     AND MAX(emulator_flag + root_flag) >= 1
)
SELECT DISTINCT driver_id
FROM spark_trips
WHERE device_id IN (SELECT device_id FROM risky_devices);

