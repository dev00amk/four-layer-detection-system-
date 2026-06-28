-- Signal: incentive threshold clustering | Fraud: incentive gaming
SELECT driver_id FROM spark_trips GROUP BY driver_id HAVING SUM(CAST(incentive_trip_count BETWEEN 18 AND 20 AS INTEGER)) >= 2;
