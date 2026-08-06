#!/usr/bin/env bash
# Regenerate the keymap diagram:  ./draw/generate.sh
#
# PYTHONIOENCODING is set because keymap-drawer emits glyphs such as U+25BD and
# Python's stdout defaults to cp1252 on Windows, which fails before writing
# anything.
#
# prepare.py replaces the layout keymap-drawer infers from the file name
# ("zmk_keyboard: corne_choc_pro", which it cannot resolve for an out-of-tree
# board) with one derived from the board's own devicetree, minus the optional
# inner keys this unit does not have.
set -euo pipefail
cd "$(dirname "$0")/.."

KEYMAP="config/corne_choc_pro.keymap"
LAYOUT_DTS="boards/keebart/corne_choc_pro/corne_choc_pro-layouts.dtsi"
CONFIG="draw/keymap_drawer.config.yaml"
OUT_YAML="draw/corne_choc_pro.yaml"
OUT_JSON="draw/physical_layout.json"
OUT_SVG="draw/corne_choc_pro.svg"

export PYTHONIOENCODING=utf-8

keymap -c "$CONFIG" parse -z "$KEYMAP" -o "$OUT_YAML"
python draw/prepare.py "$LAYOUT_DTS" "$OUT_YAML" "$OUT_JSON"
keymap -c "$CONFIG" draw "$OUT_YAML" -o "$OUT_SVG"

echo "wrote $OUT_SVG"
