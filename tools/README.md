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
| `wrapkit/compose.py` | canvases -> texture (`compose`, optionally with a `finish`; a canvas's optional 4th channel says which paint the finish may shade) and texture -> canvases (`decompose`) |
| `wrapkit/finish.py` | `tonal()`: a soft change of tone with the broad shape of the body (used); `metallic()`: studio reflections and light on the body lines (kept, not used) |
| `wrapkit/export.py` | saves a PNG that satisfies Tesla's rules (`save_wrap`) and checks one (`validate`: container, bit depth, size, name, alpha against the template) |
| `wrapkit/preview.py` | flat sheet of every side, built from the saved file |
| `render_visualizer.js` | uploads wraps to the Tesla Wrap Gallery visualizer and screenshots the 3D car |
| `calibrate/` | how `wrapkit/data/` was produced |
| `designs/w16_*.py` | the designs (`w16_a` .. `w16_d`; `w16_b2` .. `w16_b4` and `w16_e1` .. `w16_e3` reuse B's front and rear with other sides via `w16_b_side.py` / `w16_e_side.py`); `designs/w16_common.py` holds the palette, the body landmarks (`shoulder_y`, `door_edge`, `door_curve`, `seam_fade`), the star field, mirrors and rails |

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
`door_edge()` gives the slant of each door gap as a straight line; `door_curve()` follows the
real (slightly curved) gap row by row - use it for anything that must sit on the gap. On `rear` the Tesla badge sits
at about (200, 90).

## Stars

`designs.w16_common.star_field` lays three-pointed stars out on a lattice in a
canvas and draws them so that, **on the car**, every star has the same size,
angle and brightness: `on_body()` builds each star in the surface's own frame
('up' = the canvas' up laid onto the surface), maps it back into the canvas
through the local foreshortening and refines every point with the normal under
it, so a star on a slanted or gently curved panel keeps its proportions. Only
whole stars are drawn - a star that would cross a panel gap, an edge, a bend,
a fold (`carmap.facing_min`: the lip under the spoiler, where the body turns
under itself and two surfaces share a canvas pixel) or a keep-clear zone
(`keep_clear`), the side indicator, or a flank sloped more than about 50
degrees is left out rather than cut. Stars are never faded: `where=` says
where the field is, and a star is there in full or not at all; they are
painted `lit=False`, so the finish does not shade them and every star of a
design has exactly the same colour. Faces that look at the sky (the `deck`
canvas: spoiler top, rear-glass frame) get no stars - no direction on them
reads as 'up' from behind the car.

Measured on the 3D model (every star of every design, mapped through the
model's own UVs): size within about 1 %, every arm within 2 degrees of where it
should point.

## Finish

The car and the app blend a wrap over the car's own paint by the wrap's alpha
(`colour = mix(paint, wrap, a)`, roughness from ~0.1 to 0.9 and metallic from
~0.7 to 0 as `a` goes to 1), so an opaque wrap is always lit as matte vinyl.
Making the silver translucent does let the car's glossy paint through - but it
also lets the car's paint *colour* through (a grey car turned the silver grey),
so the wraps stay fully opaque and the metallic look is painted in instead.

The designs get the metal look from colour: layered silver gradients
(`SIDE_TONES` / `silver_gradient`, `hood_base`, `bumper_gradient` in
`designs/w16_common.py`) plus `wrapkit.finish.Tonal` - a soft, low-contrast
change of tone with the broad shape of the body (normals smoothed over 14
texels inside each panel, a wide sky-to-ground transition), so creases and body
lines leave no light or dark line. `FINISH` in `designs/w16_common.py` sets it.

`wrapkit.finish.Metallic` - studio reflections with a bright horizon line and
light on the body lines - is kept for reference; on the car's own lighting it
made the nose look streaky. (`silver_alpha`, `shade_alpha` and `compose(...,
finish)` still support a translucent finish for cars painted silver.)

## Resolution

Tesla accepts 512..1024 px; 1024 x 1024 is the maximum, whatever the file size.
Within that, `compose()` samples each texel 4 x 4 over its exact footprint on
the canvas and applies a light unsharp mask; each island's colours are carried 16 px
past its edge (under alpha 0), so the car's texture filtering never pulls black into
a seam. Every texel covers about 5-6 mm of
the car on every panel. `compose.compose_hires()` can render 2048 x 2048 with
real detail for testing whether a car accepts a larger file.

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
  canvas coordinates, and `modely_residual_x.png` / `modely_residual_y.png` -
  what the polynomial misses at every texel (canvas px x 256 around 32768,
  16-bit). A polynomial cannot follow a fold such as the liftgate lip (it was
  up to 9 px off there, enough to stretch a star by a fifth), so `texel_coords`
  adds the stored remainder, interpolated inside each region: the mapping is
  then exact to about 0.01 px everywhere.
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
