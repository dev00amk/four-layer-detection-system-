-- ===========================================================================
-- Signal: gps_spoofing_impossible_transit (Signal 23)
-- ===========================================================================
--
-- 1. COMPLIANCE EXPLANATION
-- -------------------------
-- Suspected Abuse: The driver is using software tools to manipulate their GPS location,
-- claiming to complete deliveries instantly across physically impossible distances.
-- This allows them to collect transit payouts and trip earnings without actually driving.
--
-- 2. ENUMERATED LEGITIMATE MIMICS (FALSE POSITIVES)
-- ------------------------------------------------
-- A. Highway driving between metropolitan areas: Placing a delivery, driving down the
--    highway at 100-110 kph, and immediately picking up another delivery.
-- B. GPS Multipath / Urban Canyons: Signal bounce off tall buildings creates temporary
--    spikes in accuracy, shifting the apparent position by hundreds of meters between pings.
-- C. Timezone / Clock-Skew Artifacts: Local device time changes or clock synchronization
--    delays cause the registered timestamps to appear closer together than they physically are.
-- D. Multi-Modal Transit (Ferry/Train): The driver boards a ferry or train with their phone,
--    resulting in high transit speeds over water or rail where they are not physically driving.
--
-- 3. EXCLUSION & MITIGATION LOGIC
-- ------------------------------
-- A. Highway driving: implied speed threshold is set to 180 kph (implied_kph > 180).
--    This is a safe physical ceiling that no motor vehicle can legitimately maintain on roads.
-- B. GPS Multipath: gated on gps_accuracy_m <= 80. Coarse GPS locks with high error bounds
--    are programmatically ignored.
-- C. Clock-Skew / Timezone shifts: requires COUNT(*) >= 2 separate impossible segments
--    per driver. A single timestamp glitch or clock jump is rejected.
-- D. Multi-modal / App anomalies: requires MAX(emulator_flag + gps_mock_flag) >= 1.
--    The presence of impossible transit must be corroborated by hardware-level compromises
--    (emulator environments or active developer mock location settings) to prevent flagging
--    legitimate ferry/train passengers.
--
-- ===========================================================================

WITH ordered AS (
  SELECT
    driver_id,
    trip_id,
    trip_start_ts,
    pickup_lat,
    pickup_lon,
    gps_accuracy_m,
    emulator_flag,
    gps_mock_flag,
    LAG(dropoff_lat) OVER (PARTITION BY driver_id ORDER BY trip_start_ts) AS previous_lat,
    LAG(dropoff_lon) OVER (PARTITION BY driver_id ORDER BY trip_start_ts) AS previous_lon,
    LAG(trip_start_ts) OVER (PARTITION BY driver_id ORDER BY trip_start_ts) AS previous_start
  FROM spark_trips
),
segments AS (
  SELECT *,
    haversine_km(previous_lat, previous_lon, pickup_lat, pickup_lon)
      / NULLIF(date_diff('second', previous_start, trip_start_ts) / 3600.0, 0) AS implied_kph
  FROM ordered
  WHERE previous_start IS NOT NULL AND trip_start_ts > previous_start
)
SELECT driver_id
FROM segments
WHERE implied_kph > 180
  AND gps_accuracy_m <= 80
GROUP BY driver_id
HAVING COUNT(*) >= 2
  AND MAX(emulator_flag + gps_mock_flag) >= 1;
