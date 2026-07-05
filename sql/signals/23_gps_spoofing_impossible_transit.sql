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
-- D. High-Speed Rail / Multi-Modal Transit: The driver boards high-speed rail (e.g., Acela Express
--    at ~250 km/h) with their phone, resulting in high transit speeds where they are not driving.
--
-- 3. EXCLUSION & MITIGATION LOGIC
-- ------------------------------
-- A. Highway driving: Gated out by speed threshold (implied_kph > 180).
-- B. GPS Multipath: Gated out by GPS accuracy requirement (gps_accuracy_m <= 80).
-- C. Clock-Skew / Timezone shifts: Requires COUNT(*) >= 2 separate impossible segments.
-- D. High-Speed Rail vs. Evasion Hole (Two-Tier Design):
--    - Tier 1 (implied_kph > 400): Exceeds any commercial rail or surface transit. This is
--      physically impossible on land, so it triggers IMMEDIATELY with no device flag required.
--      This closes the evasion hole for spoofers on clean/custom-rooted devices.
--    - Tier 2 (implied_kph BETWEEN 180 AND 400): Overlaps with high-speed rail (~250 km/h).
--      To prevent false positives on clean-phone rail passengers, this tier REQUIRES active
--      hardware compromise indicators (emulator_flag + gps_mock_flag >= 1) ON THE SAME SEGMENT.
--
-- 4. ACKNOWLEDGED BLIND SPOT
-- --------------------------
-- A spoofer holding speeds between 180 and 400 km/h on a clean/rooted device (avoiding emulator
-- and developer mock flags) will evade this signal. This is a deliberate, documented trade-off
-- to avoid false-positive flagging of legitimate commuters. This residual risk is covered by
-- Graph payout cluster checks and Signal 25 (device-forensics account-hopping).
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
  AND (
    -- Tier 1: Physically impossible land speed (no device compromise required)
    implied_kph > 400
    OR
    -- Tier 2: Bullet-train overlap band (requires hardware compromise indicators on the SAME segment)
    (implied_kph <= 400 AND (emulator_flag + gps_mock_flag) >= 1)
  )
GROUP BY driver_id
HAVING COUNT(*) >= 2;
