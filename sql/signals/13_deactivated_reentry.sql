-- Signal: identity overlap proxy | Fraud: ban evasion
SELECT driver_id FROM spark_trips GROUP BY driver_id HAVING COUNT(DISTINCT device_id) >= 3;
