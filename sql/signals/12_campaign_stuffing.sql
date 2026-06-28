-- Signal: campaign stuffing | Fraud: incentive abuse
SELECT driver_id FROM spark_trips GROUP BY driver_id, campaign_id HAVING COUNT(*) >= 3;
