# Filter rejection % sensor

A template sensor that shows how much your filter removes, live:

    rejection % = (1 − filtered_TDS ÷ tap_TDS) × 100

It needs a stored tap baseline (a Number helper) because the probe only measures
whatever water it currently sits in. Set the baseline whenever you measure your
tap water; the rejection then reads correctly while the probe is in the filtered
or RO output.

## Option A — UI helpers (no YAML)

1. **Tap baseline.** Settings → Devices & Services → Helpers → **+ Create Helper
   → Number**.
   - Name: `Tap water TDS baseline` (entity becomes
     `input_number.tap_water_tds_baseline`).
   - Min 1, Max 2000, Step 1, Unit `ppm`.
   - Set it to your measured tap value (e.g. 315).

2. **Rejection sensor.** Helpers → **+ Create Helper → Template → Template a
   sensor**.
   - Name: `Water filter rejection`.
   - Unit of measurement: `%`.
   - State template:
     ```jinja
     {% set tap = states('input_number.tap_water_tds_baseline') | float(0) %}
     {% set out = states('sensor.kukhnia_dts1xm9_excellux_tds') | float(-1) %}
     {% if tap > 0 and out >= 0 %}
     {{ ([0, (1 - out / tap) * 100, 100] | sort)[1] | round(1) }}
     {% else %}
     unknown
     {% endif %}
     ```

Replace `sensor.kukhnia_dts1xm9_excellux_tds` with your own TDS entity id if it
differs.

## Option B — YAML

Add to `configuration.yaml`. If you already have `input_number:` or `template:`
keys, merge these under them instead of pasting a second copy.

```yaml
input_number:
  tap_water_tds_baseline:
    name: Tap water TDS baseline
    min: 1
    max: 2000
    step: 1
    unit_of_measurement: ppm
    icon: mdi:water

template:
  - sensor:
      - name: Water filter rejection
        unique_id: water_filter_rejection
        unit_of_measurement: "%"
        state_class: measurement
        icon: mdi:water-percent
        state: >
          {% set tap = states('input_number.tap_water_tds_baseline') | float(0) %}
          {% set out = states('sensor.kukhnia_dts1xm9_excellux_tds') | float(-1) %}
          {% if tap > 0 and out >= 0 %}
            {{ ([0, (1 - out / tap) * 100, 100] | sort)[1] | round(1) }}
          {% else %}
            unknown
          {% endif %}
        availability: >
          {{ states('sensor.kukhnia_dts1xm9_excellux_tds') not in ['unknown', 'unavailable'] }}
```

Restart Home Assistant (YAML) or reload template entities.

## Reading it

- The probe must be in the **filtered / RO output** for the number to mean
  rejection. In tap water it reads ~0%.
- Healthy RO: **90–98%**. If it drifts down over weeks toward ~80% or lower, the
  membrane is wearing out.
- The number is only as good as the baseline — re-measure tap water and update
  the helper if your supply changes.
