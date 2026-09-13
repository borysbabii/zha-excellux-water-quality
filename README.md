# ZHA quirk — Excellux 7-in-1 water quality monitor (ZG-101TDS / ZG-109TDS)

A Zigbee Home Automation (ZHA) quirk that exposes the sensor readings of a Tuya
7-in-1 water quality monitor in Home Assistant. Also included: the method and a
small tool to reverse-engineer the device's Tuya datapoints yourself.

## The problem

The device pairs with ZHA over a Texas Instruments CC2652 coordinator, but shows
**no measurements** — only battery, LQI and RSSI, plus a broken "lock" entity.

The cause: the meter is a Tuya device. It sends every reading on the Tuya
manufacturer-specific cluster `0xEF00` as numbered *datapoints* (DPs). ZHA has no
built-in handler for this exact device, so it drops every datapoint. This is the
normal symptom for an unsupported Tuya sensor.

In ZHA the device reports:

| Field | Value |
|-------|-------|
| Manufacturer | `DTS1XM9` |
| Model | `Excellux` |
| Endpoint 1 device type | `0x0402` (IAS_ZONE) |
| Input clusters | `0x0000 0x0001 0x0003 0x0101 0x0500 0x1000 0xEF00` |
| Node type | sleepy end device, 2×AAA |

## The fix

Install the quirk in [`custom_zha_quirks/excellux_water_quality.py`](custom_zha_quirks/excellux_water_quality.py).

1. Copy the file to `/config/custom_zha_quirks/excellux_water_quality.py`.
2. Add to `configuration.yaml`:
   ```yaml
   zha:
     custom_quirks_path: /config/custom_zha_quirks/
   ```
3. Restart Home Assistant.
4. Press the device button to wake it. It is a sleepy end device and reports in
   bursts, so values start as `unknown` and fill in on the next report.

After that the device exposes `sensor.<name>_tds`, `sensor.<name>_ec`,
`sensor.<name>_temperature`, raw pH/ORP candidates, and the alarm-limit
datapoints as diagnostics.

## Datapoint map

Captured live from one physical device. See [`docs/datapoints.md`](docs/datapoints.md)
for the capture method and the confirmation tests.

| DP | Meaning | Scaling | Status |
|----|---------|---------|--------|
| 124 | TDS (ppm) | raw | **confirmed** |
| 127 | EC (µS/cm) | raw | **confirmed** — DP 127 = 2 × DP 124, matching TDS = 0.5 × EC |
| 118 | ORP (mV) | ÷10? | candidate |
| 4 | Battery (%) | raw | duplicate of the standard battery entity |
| 2 | not pH | — | was a pH candidate; stays in a 50–55 band and rose under strong acid, so **not** pH |
| 5 | not temperature | — | stays ~25 (raw ~2500) even in water known to be warmer, so it does **not** track water temperature |
| 1 | unknown | — | does not collapse in air, so not a live probe |
| 101, 108–132 | alarm limits | — | constant, exposed as diagnostics |
| 112, 117, 126, 130, 133 | mode flags | — | enum / bool |

**pH, salinity and free chlorine are not identified** over Zigbee on this unit.
Under strong acid (lemon, vinegar) TDS and EC spiked as expected, but no live
datapoint fell the way pH must. Either this model does not stream those probes,
or they hide in a datapoint that only updates on the app/display. If you can read
per-parameter values off the screen and match them to raw datapoints, please open
an issue.

### How the labels were found

- **TDS and EC**: the only two datapoints that fall to ~0 when the probe leaves
  the water. Their ratio is a constant 1:2 across readings (98/196, 249/499),
  which is the standard TDS(ppm) = 0.5 × EC(µS/cm) relationship.
- **ORP**: dropped after switching from tap water to carbon-filtered water,
  which fits chlorine removal lowering the oxidation-reduction potential.

DP 5 looked like temperature at first (raw ~2500 → 25 °C at ÷100), but it stays
near 25 even in water the owner confirmed was warmer than 25 °C. So it does not
track the water temperature and is left raw.

## Help wanted

The pH divisor, the ORP divisor, DP 1, and the salinity / free-chlorine
datapoints are not confirmed. If you own this device, put the probe in water,
read the on-screen values, and open an issue or PR with the display readings
next to the raw DP values. That lets us finish the map.

## Tools

[`tools/parse_tuya.py`](tools/parse_tuya.py) decodes Tuya `0xEF00` datapoints
from a ZHA / zigpy debug log. Point it at a saved log and a device network
address:

```sh
python3 tools/parse_tuya.py ha-debug.log 0x2A17
```

It prints each DP, its type, the distinct values seen, and a chronological tail.
Use it to find which datapoints move when you change the water.

## Compatibility

Written against Home Assistant `2026.9.2` with `zha` / `zha-quirks` `2.2.2`,
using the v2 `TuyaQuirkBuilder` API. The quirk file names the exact API it
targets in comments.

## License

MIT. See [LICENSE](LICENSE).
