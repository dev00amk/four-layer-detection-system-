-- Signal: payout change | Fraud: account takeover cash-out
SELECT driver_id FROM spark_trips GROUP BY driver_id HAVING MAX(payout_change_72h) = 1;
