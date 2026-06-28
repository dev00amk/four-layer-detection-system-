-- Signal: driver-store concentration | Fraud: collusion
SELECT driver_id FROM spark_trips GROUP BY driver_id, store_id HAVING COUNT(*) >= 3 AND AVG(isFraud) > 0.10;
