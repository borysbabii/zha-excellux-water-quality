"""Decode Tuya 0xEF00 datapoints from a Home Assistant zigpy debug log."""
import ast
import re
import sys
from collections import OrderedDict

NWK = sys.argv[2] if len(sys.argv) > 2 else "0x2A17"
TYPES = {0: "raw", 1: "bool", 2: "value", 3: "string", 4: "enum", 5: "bitmap"}

pkt = re.compile(
    r"^(\S+ \S+).*Received a packet.*address=" + NWK + r"\).*cluster_id=61184.*"
    r"data=Serialized\[(b'.*?'|b\".*?\")\]",
)

rows = []
for line in open(sys.argv[1], errors="replace"):
    m = pkt.search(line.strip())
    if not m:
        continue
    ts, blob = m.group(1), ast.literal_eval(m.group(2))
    fc = blob[0]
    i = 1
    if fc & 0x04:  # manufacturer specific
        i += 2
    i += 1  # tsn
    cmd = blob[i]
    i += 1
    payload = blob[i:]
    if cmd not in (0x01, 0x02, 0x06):  # data report variants
        continue
    seq = int.from_bytes(payload[:2], "big")
    p = payload[2:]
    while len(p) >= 4:
        dp, dtype = p[0], p[1]
        length = int.from_bytes(p[2:4], "big")
        raw = p[4:4 + length]
        if dtype == 3:
            value = raw.decode("utf8", "replace")
        elif dtype == 0:
            value = raw.hex()
        else:
            value = int.from_bytes(raw, "big")
        rows.append((ts, seq, dp, TYPES.get(dtype, dtype), value))
        p = p[4 + length:]

print(f"{len(rows)} datapoint reports\n")
seen = OrderedDict()
for ts, seq, dp, dtype, value in rows:
    seen.setdefault(dp, []).append((ts, dtype, value))

print(f"{'DP':>5} {'hex':>6} {'type':<7} {'n':>3}  distinct values (last first)")
for dp in sorted(seen):
    vals = seen[dp]
    distinct = list(OrderedDict.fromkeys(v for _, _, v in reversed(vals)))
    print(f"{dp:>5} {hex(dp):>6} {vals[0][1]:<7} {len(vals):>3}  {distinct[:6]}")

print("\nchronological tail:")
for ts, seq, dp, dtype, value in rows[-25:]:
    print(f"  {ts}  seq={seq:<5} dp={dp:<4}({hex(dp)})  {dtype:<6} = {value}")
