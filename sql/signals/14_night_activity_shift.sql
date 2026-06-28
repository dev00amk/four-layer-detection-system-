-- Signal: night activity | Fraud: account takeover
SELECT driver_id FROM spark_trips GROUP BY driver_id HAVING AVG(off_hours_flag) > 0.25 AND MAX(payout_change_72h) = 1;
