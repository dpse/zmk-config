# zmk-config — Corne Choc Pro BT

[ZMK](https://zmk.dev) firmware for a
[Keebart Corne Choc Pro BT](https://www.keebart.com/products/corne-wireless).
[Miryoku](https://github.com/manna-harbour/miryoku)-derived layout, ported from
a [ZSA Voyager](https://www.zsa.io/voyager) running
[QMK](https://qmk.fm).

![keymap](draw/corne_choc_pro.svg)

## Building

GitHub Actions builds on every push (`build.yaml`). For local builds, clone ZMK
*outside* this repo — west would otherwise clone Zephyr over this repo's
`zephyr/` module manifest — then from `zmk/app`:

```sh
west build -p -b corne_choc_pro_left/nrf52840/zmk -d build/left -- \
  -DSHIELD=nice_view \
  -DZMK_CONFIG=".../zmk-config/config" \
  -DZMK_EXTRA_MODULES=".../zmk-config;.../modules/zmk-helpers;..."
```

`ZMK_EXTRA_MODULES` needs this repo (it supplies the board) plus every module
in `config/west.yml`.

Diagram: `bash draw/generate.sh`, or the `draw-keymaps` workflow on push.

## Notes

- `boards/keebart/corne_choc_pro/` is a **Zephyr HWMv2** port of Keebart's
  board definition.
- RGB underglow hardware is described in the board `.dts` and left disabled in
  `config/corne_choc_pro.conf`, for battery life.
