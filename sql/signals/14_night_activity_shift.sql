-- Signal: night activity | Fraud: account takeover
-- Note: partial overlap with signal 19 (payout bank change). Signal 14 adds
-- an off-hours activity dimension. In production, evaluate merging both into
-- an ATO-precursor composite that also requires rapid device hopping.
SELECT driver_id FROM spark_trips GROUP BY driver_id HAVING AVG(off_hours_flag) > 0.25 AND MAX(payout_change_72h) = 1;
