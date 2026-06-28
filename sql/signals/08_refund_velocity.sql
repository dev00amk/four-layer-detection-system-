-- Signal: refund velocity | Fraud: refund abuse
SELECT driver_id FROM spark_trips GROUP BY driver_id HAVING MAX(refund_count_30d) >= 5;
