-- Signal: bot_assisted_batch_grabbing
-- Fraud type: automated offer acceptance
-- FP mitigation: require repeated sub-800ms accepts plus emulator corroboration.
WITH latency AS (
  SELECT
    driver_id,
    emulator_flag,
    date_diff('millisecond', offer_sent_ts, accept_ts) AS accept_latency_ms
  FROM spark_trips
  WHERE accept_ts >= offer_sent_ts
)
SELECT driver_id
FROM latency
GROUP BY driver_id
HAVING COUNT(*) >= 5
   AND SUM(CAST(accept_latency_ms < 800 AS INTEGER)) >= 5
   AND MAX(emulator_flag) = 1;
