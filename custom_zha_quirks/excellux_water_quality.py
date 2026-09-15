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
  * DP 5   -> temperature (C)  CONFIRMED, divisor 100. Slow-responding: it does
                               not follow brief dips, but over 3 days it tracked
                               ambient (21 C cool morning, 24-27 C daytime/warm).
  * DP 1   -> temperature (C)  CONFIRMED, divisor 10. Same reading as DP 5 at
                               coarser resolution; the two agree and move
                               together (DP 1 = DP 5 / 10).
  * DP 118 -> ORP   (mV)       CANDIDATE, divisor 10  (reads ~550 mV, drops
                               after carbon filtering, which fits chlorine loss)
  * DP 2   -> unknown          was a pH CANDIDATE, but stays in a tight 50-55
                               band and even rose slightly under strong acid
                               (lemon, vinegar). pH must fall with acid, so
                               DP 2 is NOT pH. Left raw.
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
from zhaquirks.builder import EntityType, SensorDeviceClass, SensorStateClass
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
    # --- temperature: slow-responding, confirmed over 3 days of ambient trend ---
    .tuya_sensor(
        dp_id=5,
        attribute_name="temperature",
        type=t.uint32_t,
        divisor=100,
        unit="°C",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        translation_key="temperature",
        fallback_name="Temperature",
    )
    # DP 1 is the same temperature at coarser /10 resolution; it tracks DP 5.
    .tuya_sensor(
        dp_id=1,
        attribute_name="temperature_coarse",
        type=t.uint32_t,
        divisor=10,
        unit="°C",
        device_class=SensorDeviceClass.TEMPERATURE,
        entity_type=EntityType.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        translation_key="temperature_coarse",
        fallback_name="Temperature (coarse, /10)",
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
