# Wrap tools (legacy Model Y)

Small Python toolkit used to paint the wraps in [`modely/w16/`](../modely/w16/).
Instead of drawing on Tesla's unfolded template you paint **true views of the
car** - a side elevation, the hood from above, the front and the rear - and the
kit works out which pixel of the 1024 x 1024 texture shows each point of those
views.  What you draw is what you see from that side of the car: text is
upright and un-mirrored on both sides, and a straight line stays straight
across the door gaps.

```
python3 tools/build.py                    # rebuild every design + flat preview sheets
python3 tools/build.py w16_b              # just one
python3 tools/build.py --render           # also take 3D pictures (see below)
python3 tools/check.py modely/w16/*.png   # verify Tesla's file rules
```

Requirements: Python 3 with `numpy`, `pillow`, `scipy`; `optipng` (re-compresses
every file when present) and `pngquant` (only used when a design would exceed
900 kB); fonts Montserrat, Bebas Neue and Jura on top of Liberation / Inter.
`bash tools/setup.sh` installs all of it on Debian/Ubuntu. Rebuilds give the
same pixels everywhere; the exact bytes depend on the library versions.

## Layout

| path | what it is |
| --- | --- |
| `wrapkit/template.py` | finds the 16 paintable islands of `modely/template.png`; lists the canvases |
| `wrapkit/carmap.py` | where every texel of the texture sits on the car (reads `wrapkit/data/`) |
| `wrapkit/canvas.py` | 4x supersampled drawing surface, text and blocky race-number decals, splines, three-pointed stars |
| `wrapkit/compose.py` | canvases -> texture (`compose`) and texture -> canvases (`decompose`) |
| `wrapkit/export.py` | saves a PNG that satisfies Tesla's rules (`save_wrap`) and checks one (`validate`: container, bit depth, size, name, alpha against the template) |
| `wrapkit/preview.py` | flat sheet of every side, built from the saved file |
| `render_visualizer.js` | uploads wraps to the Tesla Wrap Gallery visualizer and screenshots the 3D car |
| `calibrate/` | how `wrapkit/data/` was produced |
| `designs/w16_*.py` | the four designs; `designs/w16_common.py` holds the palette, the body landmarks and shared parts |

## Canvases

All coordinates are canvas pixels, origin top-left, 174 px per metre (about one
texel per pixel on the doors).

| canvas | size | what it shows |
| --- | --- | --- |
| `side_L` / `side_R` | 976 x 288 | side elevation, roof up. The nose is at the **left** on `side_L` and at the **right** on `side_R`. Fenders, doors, quarter panels and the sides of both bumpers |
| `hood` | 332 x 256 | the hood from above, as seen by someone standing in front: windscreen at the top, nose at the bottom |
| `front` | 404 x 124 | front elevation: the front-facing part of the front bumper |
| `rear` | 404 x 252 | rear elevation: the upright faces of the liftgate and the rear bumper |
| `deck` | 404 x 232 | the liftgate from above, seen from behind: frame of the rear glass and the top of the spoiler |
| `rail_L` / `rail_R` | 502 x 46 | A-pillar and roof rail as a straight strip (only the middle ~14 px are on the car) |
| `mirror_L` / `mirror_R` | about 53 x 88 | mirror cap |

`designs.w16_common.Mirrored` paints one side and mirrors it to the other,
while decals (text, numbers) are stamped un-mirrored on both.

Landmarks on `side_L` (measured, see `designs/w16_common.py`): fender X 43-300,
front door 288-533, rear door 533-748, quarter panel 734-906; window line Y 122
falling to 96 toward the tail; sill Y 276; door handles at X 473-513 / Y 139 and
X 678-720 / Y 127; the lower door crease runs from about (390, 248) to (590, 230).

## Where the mapping comes from

`wrapkit/data/` is a calibration measured on a 3D model of the legacy Model Y
that carries Tesla's own wrap UVs (the one the
[Tesla Wrap Gallery visualizer](https://teslawrapgallery.com/visualizer/) shows
for "Model Y (Pre-2025)"; the model itself is not in this repository):

* `modely_viewmap.png` - which canvas each texel belongs to, or 0 if the car
  never shows it. About 18 % of the template's white area is hidden margin
  (a 5-8 px rim round every island, the lower grille, the door-handle recesses,
  half of each roof-rail strip); `compose` fills it with the neighbouring colour.
* `modely_projection.json` - per panel, a polynomial from texel coordinates to
  canvas coordinates. Fit error is below 0.5 px on the body sides and the hood
  and about 1 px on the bumpers and liftgate.

An earlier version of this kit guessed the mapping from Tesla's example wraps
(assuming the side islands overlap at the door gaps). That guess was wrong by
up to 12 px per gap, which showed as broken lines on the car - hence the
measured calibration.

## Checking a wrap in 3D

```
node tools/render_visualizer.js /tmp/out modely/w16/W16_Race_Livery.png
```

opens the visualizer in headless Chromium (Playwright), uploads the file the
same way the "Drop image or click to upload" box does, and saves a screenshot
from each angle. `build.py --render` does this for every design and assembles
`preview/*_3d.jpg` and `preview/compare.jpg`. It needs network access to
teslawrapgallery.com. The visualizer is a third-party community project; the
car's own screen and the Tesla app remain the final judge.
