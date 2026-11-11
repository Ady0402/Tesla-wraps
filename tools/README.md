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
| `wrapkit/compose.py` | canvases -> texture (`compose`, optionally with a `finish`) and texture -> canvases (`decompose`) |
| `wrapkit/finish.py` | `metallic()`: studio reflections and light on the body lines, baked into the paint |
| `wrapkit/export.py` | saves a PNG that satisfies Tesla's rules (`save_wrap`) and checks one (`validate`: container, bit depth, size, name, alpha against the template) |
| `wrapkit/preview.py` | flat sheet of every side, built from the saved file |
| `render_visualizer.js` | uploads wraps to the Tesla Wrap Gallery visualizer and screenshots the 3D car |
| `calibrate/` | how `wrapkit/data/` was produced |
| `designs/w16_*.py` | the designs (`w16_a` .. `w16_d`, and `w16_b2` .. `w16_b4` which reuse B's front and rear with other sides via `w16_b_side.py`); `designs/w16_common.py` holds the palette, the body landmarks, the star field and other shared parts |

## Canvases

All coordinates are canvas pixels, origin top-left, 174 px per metre (about one
texel per pixel on the doors).

| canvas | size | what it shows |
| --- | --- | --- |
| `side_L` / `side_R` | 976 x 288 | side elevation, roof up. The nose is at the **left** on `side_L` and at the **right** on `side_R`. Fenders, doors, quarter panels and the sides of both bumpers |
| `hood` | 332 x 256 | the hood from above, as seen by someone standing in front: windscreen at the top, nose at the bottom |
| `front` | 404 x 124 | front elevation: the front-facing part of the front bumper |
| `rear` | 404 x 252 | rear elevation: the upright faces of the liftgate and the rear bumper |
| `deck` | 404 x 232 | the liftgate from above, seen from behind: frame of the rear glass and the top of the spoiler (the band over the tail lamps) |
| `rail_L` / `rail_R` | 502 x 46 | A-pillar and roof rail as a straight strip (only the middle ~14 px are on the car) |
| `mirror_L` / `mirror_R` | about 53 x 88 | mirror cap. The shell is strongly curved, so a level stripe is drawn from the measured height of each pixel (`view("mirror_L").height()`) |

`designs.w16_common.Mirrored` paints one side and mirrors it to the other,
while decals (text, numbers) are stamped un-mirrored on both.

Landmarks on `side_L` (measured, see `designs/w16_common.py`): fender X 43-300,
front door 288-533, rear door 533-748, quarter panel 734-906; window line Y 122
falling to 96 toward the tail; sill Y 276; door handles at X 473-513 / Y 139 and
X 678-720 / Y 127; side indicator on the fender X 238-282 / Y 152-163; the lower
door crease runs from about (390, 248) to (590, 230); the shoulder crease (the
line the door handles sit on) from (380, 156) to (620, 141) - see `shoulder_y`;
`door_edge()` gives the slant of each door gap. On `rear` the Tesla badge sits
at about (200, 90).

## Stars

`designs.w16_common.star_field` lays three-pointed stars out on a lattice in a
canvas and draws them so that, **on the car**, every star has the same size and
one arm pointing straight up: where the surface is tilted away from the view
the star is pre-squashed by the same amount the projection foreshortens it.
Only whole stars are drawn - a star that would cross a panel gap, an edge, a
strongly curved area or a keep-clear zone (`keep_clear`) is left out rather
than cut. Fades are done with brightness, never with size.

## Metallic finish

The car and the app blend a wrap over the car's own paint by the wrap's alpha
(`colour = mix(paint, wrap, a)`, roughness from ~0.1 to 0.9 and metallic from
~0.7 to 0 as `a` goes to 1), so an **opaque** wrap is always lit as matte vinyl
no matter what is painted on it. `wrapkit.finish.Metallic` therefore does two
things:

* `opacity()`: neutral silver / grey paint gets `silver_alpha` (0.45 in the
  designs) so the car's glossy metallic paint shows through; text, numbers,
  teal, white and black stay opaque (`black_alpha` = 1). The silver then takes
  on the colour of the car's paint, so these wraps are meant for a silver /
  grey paint choice in Paint Shop. `compose()` multiplies this into the
  template alpha; `validate()` accepts translucency but never more opacity
  than the template or fully transparent holes.
* the shading: per texel from the surface normal (`wrapkit/data/modely_normals.png`)
  it paints what a simple photo studio would mirror for a viewer beside the
  car - dark floor and horizon band, a bright horizon line, sky and an overhead
  light box - plus a little light where the body bends sharply (`crease_gain`),
  so light and dark edges land on the body lines.

The designs use `FINISH = metallic(1.0, crease_gain=55.0, silver_alpha=0.45,
black_alpha=1.0)` in `designs/w16_common.py`; `silver_alpha=1.0` gives an
opaque matte wrap again.

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
* `modely_normals.png` - the smooth surface normal of every texel the car
  shows, 8 bits per component (smoothed within each panel when read).
* `modely_height.png` - height above the ground of every texel in millimetres
  (16-bit), used for graphics that must stay level, such as the mirror stripe.

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
