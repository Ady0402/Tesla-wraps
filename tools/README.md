# Wrap tools (legacy Model Y)

Small Python toolkit used to paint the wraps in [`modely/w16/`](../modely/w16/).
Instead of drawing straight onto Tesla's unfolded template, you paint each part
of the car in an upright **view** and the kit folds it into the 1024 x 1024
texture, so text is never sideways or mirror-written and stripes run straight
across the door gaps.

```
python3 tools/build.py            # rebuild every design + previews
python3 tools/build.py w16_a      # just one
python3 tools/check.py modely/w16/*.png   # verify Tesla's file rules
```

Requirements: Python 3 with `numpy`, `pillow`, `scipy`; the `pngquant` and
`optipng` binaries (only used if a file would exceed 1 MB); fonts Montserrat,
Bebas Neue and Play on top of Liberation / Inter (Debian/Ubuntu packages
`fonts-montserrat fonts-bebas-neue fonts-play`).

## Layout

| path | what it is |
| --- | --- |
| `wrapkit/template.py` | finds the 16 paintable islands of `modely/template.png` and defines the views |
| `wrapkit/canvas.py` | 4x supersampled drawing surface, text / plate decals, splines, three-pointed stars |
| `wrapkit/compose.py` | views -> texture (`compose`) and texture -> views (`decompose`) |
| `wrapkit/export.py` | saves a PNG that satisfies Tesla's rules (`save_wrap`, `validate`) |
| `wrapkit/preview.py` | flat preview sheet built from the saved file |
| `wrapkit/mock.py` | three-quarter mock-up draped over `modely/vehicle_image.png` |
| `designs/w16_*.py` | the three designs; `designs/w16_common.py` holds palette and shared parts |

## Views

All view coordinates are texture pixels, origin top-left.

| view | size | orientation |
| --- | --- | --- |
| `side_L` / `side_R` | 891 x 255 | flank seen from outside, roof up. Front of the car is at the **left** on `side_L` and at the **right** on `side_R` |
| `hood` | 312 x 253 | seen by someone standing in front of the car: windscreen edge at the top, nose at the bottom |
| `front` | 529 x 152 | front bumper seen from the front, upright |
| `liftgate`, `rear` | 430 x 320, 530 x 139 | seen from behind, upright |
| `rail_L` / `rail_R` | 502 x 46 | roof rail strip (A-pillar to C-pillar), front of car at the left / right |
| `mirror_L` / `mirror_R` | about 53 x 88 | mirror cap |

`designs.w16_common.Mirrored` paints one flank and mirrors it to the other,
while decals (text, numbers) are stamped un-mirrored on both.

## What was measured on Tesla's own examples

The mapping was checked against the 20 official example wraps in
`modely/example/` (text such as `TESLA`, `ANI`, `RUDI` comes out upright on both
flanks, and Tesla's diagonal stripes come out straight):

* Left-column islands are the car's left side rotated 90 degrees clockwise, the
  right column is rotated 90 degrees counter-clockwise; the hood and the front
  bumper are upside-down for a viewer standing in front of the car; the
  liftgate and rear bumper are upright.
* The outer 5-7 px of each side island is edge wrap that is not seen on the
  car, so neighbouring islands must overlap by about 12 px in view space for
  artwork to line up across a door gap (`SEAM_OVERLAP`), and the fender /
  quarter islands sit a few pixels out of register vertically (`V_SHIFT`).
* The band at the very bottom of the `front` view is the recessed lower grille;
  keep graphics out of it.

The preview and mock-up are approximations made from the saved file. The car
and the Tesla app are the final judge.
