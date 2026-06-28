-- Signal: off-hours claims | Fraud: fabricated trips
SELECT driver_id FROM spark_trips GROUP BY driver_id HAVING AVG(off_hours_flag) > 0.20;
