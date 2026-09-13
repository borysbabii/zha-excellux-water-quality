"""ZHA quirk for the Excellux 7-in-1 water quality monitor.

Sold as ZG-101TDS / ZG-109TDS. In Zigbee Home Automation (ZHA) the device
reports manufacturer "DTS1XM9", model "Excellux", and speaks the Tuya
manufacturer cluster 0xEF00. Without a quirk ZHA drops every datapoint, so the
device exposes only battery, LQI and RSSI.

This quirk maps the Tuya datapoints (DPs) to Home Assistant sensors. The DP
numbers and scaling come from live capture on one physical device. See
docs/datapoints.md for the capture method and the confirmation tests.

Status of each DP:
  * DP 124 -> TDS   (ppm)      CONFIRMED
  * DP 127 -> EC    (uS/cm)    CONFIRMED (DP 127 == 2 x DP 124, the standard
                               TDS = 0.5 x EC relationship)
  * DP 118 -> ORP   (mV)       CANDIDATE, divisor 10  (reads ~550 mV, drops
                               after carbon filtering, which fits chlorine loss)
  * DP 2   -> unknown          was a pH CANDIDATE, but stays in a tight 50-55
                               band and even rose slightly under strong acid
                               (lemon, vinegar). pH must fall with acid, so
                               DP 2 is NOT pH. Left raw.
  * DP 5   -> unknown          CANDIDATE for temperature, but stays ~25 (raw
                               ~2500) even in water known to be warmer than
                               25 C, so it does NOT track water temperature.
                               Left raw.
  * DP 1   -> unknown          does NOT collapse in air, so not a live probe.
                               No clean pH response either.
  * pH / salinity / chlorine   NOT identified over Zigbee on this unit. No live
                               datapoint fell with acid the way pH must.
  * others (constant)          alarm limits and mode flags, exposed as
                               diagnostics so you can compare with your display

If your unit differs, put the probe in water, read the display, and match each
number to the raw value below. Pull requests with corrections are welcome.

Install:
  1. Copy this file to /config/custom_zha_quirks/excellux_water_quality.py
  2. Add to configuration.yaml:
         zha:
           custom_quirks_path: /config/custom_zha_quirks/
  3. Restart Home Assistant.
  4. Press the device button to wake it. It is a sleepy end device and
     reports in bursts.
"""

import zigpy.types as t
from zhaquirks.builder import EntityType, SensorStateClass
from zhaquirks.tuya.builder import TuyaQuirkBuilder
from zigpy.zcl.clusters.closures import DoorLock

# Constant across reports -> alarm limits (32-bit values).
LIMIT_DPS = (101, 108, 109, 110, 115, 116, 119, 120, 121, 125, 129, 131, 132)
# Enum / bool datapoints (one byte) -> mode flags.
FLAG_DPS = (112, 117, 126, 130, 133)

builder = (
    TuyaQuirkBuilder("DTS1XM9", "Excellux")
    # The device answers every lock command with UNSUP_CLUSTER_COMMAND, so the
    # standard IAS_ZONE device type creates a useless lock entity. Remove it.
    .removes(DoorLock.cluster_id)
    # --- confirmed measurements ---
    .tuya_sensor(
        dp_id=124,
        attribute_name="tds",
        type=t.uint32_t,
        unit="ppm",
        state_class=SensorStateClass.MEASUREMENT,
        translation_key="tds",
        fallback_name="TDS",
    )
    .tuya_sensor(
        dp_id=127,
        attribute_name="ec",
        type=t.uint32_t,
        unit="µS/cm",
        state_class=SensorStateClass.MEASUREMENT,
        translation_key="ec",
        fallback_name="EC",
    )
    # --- candidate measurement, exposed raw so you can confirm the divisor ---
    .tuya_sensor(
        dp_id=118,
        attribute_name="orp_raw",
        type=t.uint32_t,
        state_class=SensorStateClass.MEASUREMENT,
        translation_key="orp_raw",
        fallback_name="ORP (raw, /10?)",
    )
    # --- DP 2: ruled out as pH (see header), kept raw for reference ---
    .tuya_sensor(
        dp_id=2,
        attribute_name="dp_2",
        type=t.uint32_t,
        entity_type=EntityType.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        translation_key="dp_2",
        fallback_name="DP 2 (not pH)",
    )
    .tuya_sensor(
        dp_id=5,
        attribute_name="dp_5",
        type=t.uint32_t,
        entity_type=EntityType.DIAGNOSTIC,
        # Keep MEASUREMENT so existing long-term statistics continue; the value
        # is a raw number of an unknown quantity, not confirmed temperature.
        state_class=SensorStateClass.MEASUREMENT,
        translation_key="dp_5",
        fallback_name="DP 5 (temperature? does not track)",
    )
    .tuya_sensor(
        dp_id=1,
        attribute_name="dp_1",
        type=t.uint32_t,
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="dp_1",
        fallback_name="DP 1 (unknown)",
    )
)

for dp in LIMIT_DPS:
    builder = builder.tuya_sensor(
        dp_id=dp,
        attribute_name=f"dp_{dp}",
        type=t.uint32_t,
        entity_type=EntityType.DIAGNOSTIC,
        translation_key=f"dp_{dp}",
        fallback_name=f"DP {dp}",
    )

for dp in FLAG_DPS:
    builder = builder.tuya_sensor(
        dp_id=dp,
        attribute_name=f"dp_{dp}",
        type=t.uint8_t,
        entity_type=EntityType.DIAGNOSTIC,
        translation_key=f"dp_{dp}",
        fallback_name=f"DP {dp}",
    )

builder.skip_configuration().add_to_registry()
