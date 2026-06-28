-- Signal: shared payout | Fraud: coordinated cash-out
SELECT driver_id FROM spark_trips WHERE payout_account IN (
  SELECT payout_account FROM spark_trips GROUP BY payout_account HAVING COUNT(DISTINCT driver_id) >= 2
) GROUP BY driver_id;
