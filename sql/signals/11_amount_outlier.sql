-- Signal: amount outlier | Fraud: fare manipulation
SELECT driver_id FROM spark_trips GROUP BY driver_id HAVING MAX(TransactionAmt) > 250;
