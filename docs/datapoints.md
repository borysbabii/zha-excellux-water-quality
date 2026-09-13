# Reverse-engineering the datapoints

This is the full method used to map the Excellux water quality monitor, so you
can repeat it for a different unit or a different Tuya device.

## 1. Turn on ZHA debug logging

Call the `logger.set_level` service (Developer Tools → Actions, or the REST API):

```yaml
service: logger.set_level
data:
  zigpy: debug
  zigpy.zcl: debug
  zigpy.application: debug
  zhaquirks: debug
  zha: debug
```

## 2. Wake the device and change the water

The meter is a sleepy end device. It reports in bursts after the button press or
a measurement change. To label the datapoints, change one physical condition at
a time and watch which values move:

- **Water vs air**: the conductivity probes (TDS, EC) fall to ~0 in air.
- **Tap vs filtered water**: carbon filtering removes chlorine, which lowers ORP.
- **Warm vs cool water**: the temperature datapoint tracks the change.

## 3. Read the log

Home Assistant OS exposes the core log over the Supervisor proxy:

```
GET /api/hassio/core/logs?lines=4000
Authorization: Bearer <long-lived token>
Accept: text/plain
```

The device frames look like this (network address `0x2A17` here):

```
[0x2A17:1:0xef00] Received ZCL frame: '0d 01 00 11 02 01 ad 7f 02 00 04 00 00 01 f3'
```

The frame control byte `0x0D` sets the manufacturer-specific bit, and the
manufacturer id is `0x0001`. The `TuyaQuirkBuilder` cluster handles this
correctly; a plain unquirked device logs `No explicit handler for cluster
command 0x02` and decodes nothing.

## 4. Decode

Save the log and run [`../tools/parse_tuya.py`](../tools/parse_tuya.py):

```sh
python3 tools/parse_tuya.py ha-debug.log 0x2A17
```

Each Tuya datapoint is `dp_id, type, length, value`:

| type | meaning |
|------|---------|
| 0 | raw bytes |
| 1 | bool |
| 2 | 4-byte value (big-endian) |
| 3 | string |
| 4 | enum (1 byte) |
| 5 | bitmap |

## 5. Confirmation tests (this device)

Live values captured while changing the water:

| Test | DP 1 (tds?) | DP 2 | DP 5 | DP 118 | DP 124 | DP 127 |
|------|------|------|------|--------|--------|--------|
| tap water | 225 | 58 | 2511 | 5871 | 98 | 196 |
| filtered water | 223 | 57 | 2551 | 5701 | 100 | 28 |
| air | 225 | 54 | 2553 | 5466 | 1 | 0 |
| warm water | 318–333 | 51 | 2493* | 5198* | 248 | 498 |

`*` slow datapoints; they update every ~3 minutes, so the warm-water row shows
the previous air value that had not re-reported yet.

Conclusions:

- **DP 124 → TDS**, **DP 127 → EC**: both collapse in air; DP 127 = 2 × DP 124,
  which is TDS(ppm) = 0.5 × EC(µS/cm).
- **DP 5 → temperature ÷100**: steady across water and air at ~25 °C.
- **DP 118 → ORP** (probable): drops from tap to filtered water (chlorine loss).
- **DP 2 → pH** (probable): reads ~5.4–5.8 at ÷10.
- **DP 1**: does not collapse in air, so it is not a live probe. Purpose unknown.

## 6. Turn debug logging back off

```yaml
service: logger.set_level
data:
  zigpy: info
  zigpy.zcl: info
  zigpy.application: info
  zhaquirks: info
  zha: info
```

## Reference

A closely related Tuya water quality device (`_TZE200_v1jqz5cy`, model
`BLE-YL01`) is already supported in zigbee-herdsman-converters. Its map differs
from this unit but shows the shape of the family: DP 1 = TDS, 2 = temperature,
10 = pH, 11 = EC, 101 = ORP, 102 = free chlorine, 117 = salinity.
