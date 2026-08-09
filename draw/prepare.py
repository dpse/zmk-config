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

dts_path, yaml_path, json_path, keymap_path = sys.argv[1:5]

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

# --- leader pseudo-layer -----------------------------------------------------
# Leader sequences are not a ZMK layer, so keymap-drawer cannot see them. Draw
# them as one: every sequence's first key shows what it produces, on the key
# that starts it. The characters come from the `// x` comment on each sequence
# in the keymap, so the diagram cannot drift from the firmware.
#
# Sequences whose first key is not on the base layer (^ and _, which need
# Shift) have nowhere to be drawn and are left to the readme.
SEQ = re.compile(
    r"lead_\w+\s*\{\s*sequence = <([^>]+)>;\s*bindings = <[^>]+>;\s*\};(?:\s*//\s*(\S+))?"
)
# Board titles: the key that starts the group, then what it holds, so the
# diagram reads without the readme.
NAMES = {"A": "arrows", "K": "relations", "L": "logic & sets", "F": "operators",
         "SQT": "typography", "G": "greek", "HASH": "number sets",
         "CARET": "superscript", "UNDER": "subscript"}


def board(first):
    key = PUNCT.get(first, first.lower())
    return f"Leader {key}" + (f" · {NAMES[first]}" if first in NAMES else "")


PUNCT = {"DOT": ".", "FSLH": "/", "COMMA": ",", "SEMI": ";", "SQT": "'",
         "HASH": "#", "LBRC": "{", "CARET": "^", "UNDER": "_", "MINUS": "-",
         "PLUS": "+", "EQUAL": "=", "LPAR": "(", "RPAR": ")", "EXCL": "!",
         "QMARK": "?", "PIPE": "|", "PERCENT": "%", "COLON": ":", "LT": "<",
         "GT": ">", "BSLH": chr(92), "ASTRK": "*",
         **{f"N{d}": str(d) for d in range(10)}}

groups: dict[str, list[tuple[list[str], str | None]]] = {}
for seq, char in SEQ.findall(open(keymap_path, encoding="utf-8").read()):
    keys_ = seq.split()
    groups.setdefault(keys_[0], []).append((keys_[1:], char or None))

# Where each key sits, by the text keymap-drawer drew on it. Base first, then
# the layers that carry the digits and brackets, so a sequence ending in a
# digit can still be shown in the position it is actually pressed.
base = km["layers"]["Base"]
pos = {}
for layer in ("Base", "Num", "Sym", "Nav"):
    for i, b in enumerate(km["layers"][layer]):
        text = b if isinstance(b, str) else b.get("t")
        if isinstance(text, str):
            pos.setdefault(text, i)

undrawn = []


def place(mapping, label=""):
    """Draw {key name: cell} onto a blank copy of the board.

    A key that is not on the base layer has nowhere to go. Record it rather
    than dropping it silently, or the diagram reads as complete when it is not.
    """
    layer = [""] * len(base)
    for name, cell in mapping.items():
        key = pos.get(PUNCT.get(name, name))
        if key is None:
            undrawn.append(f"{label}{name}")
        else:
            layer[key] = cell
    return layer


leader, subs = {}, {}
for first, entries in groups.items():
    if all(c for _, c in entries):  # every sequence produces a character
        chars = [c for _, c in entries]
        leader[first] = {"t": "".join(chars[:5]) + ("…" if len(chars) > 5 else "")}
    else:  # word sequences such as BOOT and BLE
        leader[first] = {"t": "/".join(sorted("".join(first + "".join(r)).lower()
                                              for r, _ in entries))}
    # A group of two-key sequences becomes its own board, so the second key is
    # shown in the position you actually press.
    if len(entries) > 1 and all(len(r) == 1 and c for r, c in entries):
        leader[first]["s"] = first.lower()
        # Shift on the second key gives the capital, where one exists.
        subs[first] = {r[0]: {"t": c} if c.upper() == c else {"t": c, "s": c.upper()}
                       for r, c in entries}

# Greek is a passthrough prefix, so there are no per-letter sequences to read
# and it would otherwise go undrawn. This is the compose table's own letter
# mapping, which is why several are not phonetic. The other passthrough
# prefixes (^ _ { #) take digits and brackets that are not on the base layer,
# so they stay in the readme.
GREEK = {"A": "α", "B": "β", "G": "γ", "D": "δ", "E": "ε", "Z": "ζ", "H": "η",
         "U": "θ", "I": "ι", "K": "κ", "L": "λ", "M": "μ", "N": "ν", "J": "ξ",
         "O": "ο", "P": "π", "R": "ρ", "S": "σ", "W": "ς", "T": "τ", "Y": "υ",
         "F": "φ", "X": "χ", "C": "ψ", "V": "ω"}
if "G" in groups:
    # Mark it as leading to a board, the same way the real groups are marked.
    leader["G"]["s"] = "g"

km["layers"]["Leader"] = place(leader, "leader ")
for first, mapping in subs.items():
    km["layers"][board(first)] = place(
        mapping, f"leader {PUNCT.get(first, first.lower())} ")
if "G" in groups:
    km["layers"][board("G")] = place(
        {k: {"t": v, "s": v.upper()} for k, v in GREEK.items()})

# The remaining passthrough prefixes. Their second keys are digits and brackets
# rather than leader sequences, so they are listed here for the same reason as
# Greek: otherwise the diagram would not show them at all.
DIGITS = "0123456789"
PASSTHRU = {
    "CARET": dict(zip([f"N{d}" for d in DIGITS], "⁰¹²³⁴⁵⁶⁷⁸⁹"),
                  **{"MINUS": "⁻", "PLUS": "⁺", "EQUAL": "⁼",
                     "LPAR": "⁽", "RPAR": "⁾"}),
    "UNDER": dict(zip([f"N{d}" for d in DIGITS], "₀₁₂₃₄₅₆₇₈₉"),
                  **{"MINUS": "₋", "PLUS": "₊", "EQUAL": "₌",
                     "LPAR": "₍", "RPAR": "₎"}),
}
for prefix, mapping in PASSTHRU.items():
    if prefix in groups:
        km["layers"][board(prefix)] = place(
            {k: {"t": v} for k, v in mapping.items()}, f"leader {PUNCT[prefix]} ")
drawn = sum(1 for c in km["layers"]["Leader"] if c)

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

print(f"kept {len(kept)} of {len(keys)} keys; drew {drawn} leader keys")
if undrawn:
    print("  not on the base layer, so undrawn: " + ", ".join(undrawn))
