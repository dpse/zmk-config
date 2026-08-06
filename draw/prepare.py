"""Trim the drawn keymap down to the keys this board actually has.

The board's physical layout describes 46 positions, but this unit is not fitted
with the four optional inner keys (6, 7, 20 and 21). Drawing them produces four
empty keys in the middle of the diagram that do not exist on the keyboard.

This reads the board's own physical-layout devicetree so the diagram cannot
drift from the board definition, drops the missing positions, and renumbers the
combo positions to match.
"""

import json
import re
import sys

import yaml

MISSING = {6, 7, 20, 21}
LAYOUT_NODE = "default_layout"

dts_path, yaml_path, json_path = sys.argv[1:4]

# --- physical layout ---------------------------------------------------------
dts = open(dts_path, encoding="utf-8").read()
node = re.search(rf"{LAYOUT_NODE}:\s*{LAYOUT_NODE}\s*\{{(.*?)\n    \}};", dts, re.S)
if not node:
    raise SystemExit(f"could not find {LAYOUT_NODE} in {dts_path}")

keys = []
for w, h, x, y, rot, rx, ry in re.findall(
    r"&key_physical_attrs\s+"
    + r"\s+".join([r"\(?(-?\d+)\)?"] * 7),
    node.group(1),
):
    key = {"x": int(x) / 100, "y": int(y) / 100, "w": int(w) / 100, "h": int(h) / 100}
    if int(rot):
        key |= {"r": int(rot) / 100, "rx": int(rx) / 100, "ry": int(ry) / 100}
    keys.append(key)

if max(MISSING) >= len(keys):
    raise SystemExit(f"{dts_path} has only {len(keys)} keys")

kept = [i for i in range(len(keys)) if i not in MISSING]
renumber = {old: new for new, old in enumerate(kept)}

json.dump(
    {"layouts": {"LAYOUT": {"layout": [keys[i] for i in kept]}}},
    open(json_path, "w", encoding="utf-8"),
    indent=2,
)

# --- keymap ------------------------------------------------------------------
km = yaml.safe_load(open(yaml_path, encoding="utf-8"))
km["layout"] = {"qmk_info_json": json_path, "layout_name": "LAYOUT"}

for name, layer in km["layers"].items():
    if len(layer) != len(keys):
        raise SystemExit(f"layer {name} has {len(layer)} bindings, expected {len(keys)}")
    km["layers"][name] = [layer[i] for i in kept]

for combo in km.get("combos", []):
    if any(p in MISSING for p in combo["p"]):
        raise SystemExit(f"combo {combo} uses a position this board does not have")
    combo["p"] = [renumber[p] for p in combo["p"]]

with open(yaml_path, "w", encoding="utf-8") as f:
    yaml.safe_dump(km, f, width=160, sort_keys=False, default_flow_style=None, allow_unicode=True)

print(f"kept {len(kept)} of {len(keys)} keys")
