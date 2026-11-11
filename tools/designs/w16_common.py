"""Shared building blocks for the Mercedes-AMG F1 W16 tribute wraps.

All coordinates are canvas pixels (174 px per metre, see wrapkit/carmap.py).
Side elevation, left side: the nose is at X ~ 45, the tail at X ~ 925.
"""
from __future__ import annotations

import numpy as np

from PIL import Image
from scipy import ndimage as ndi

from wrapkit import (Canvas, block_digits, box_decal, facing_min, layer, mix, normal_image, panel_image, rgb, tonal,
                     smoothstep, star3, text_decal)

# ---- palette --------------------------------------------------------------
SILVER = "#C6CACE"
SILVER_HI = "#DADDE0"
SILVER_LO = "#AAB0B6"
BLACK = "#0B0C0E"
CARBON = "#17191C"
TEAL = "#00D2BE"        # the turquoise the team is known for on screen
TEAL_DEEP = "#00A19B"   # PETRONAS corporate green
WHITE = "#F4F5F6"
STAR = "#D3D7DB"
NOSE = "#B2B7BC"        # silver as it reaches the nose (hood front edge / top of the bumper)
BUMPER_MID = "#42464B"
BUMPER_LOW = "#131518"

# the car renders a wrap as matte vinyl, so the metallic look is painted in -
# from colour, not from reflections (owner's call: light along the body lines
# looked odd on the nose): layered light-to-dark gradients in the silver
# itself (silver_gradient, hood_base, bumper_gradient) plus a soft change of
# tone with the broad shape of the body (wrapkit/finish.py, Tonal), with no
# lines on creases.  The wrap stays fully opaque - a translucent wrap would
# let the car's own paint colour show through.
FINISH = tonal(1.0)

# ---- fonts ----------------------------------------------------------------
F_WORD = "Montserrat-ExtraBold.otf"       # PETRONAS-style wide bold caps
F_WORD_IT = "Montserrat-ExtraBoldItalic.otf"
F_BLACK_IT = "Montserrat-BlackItalic.otf"
F_COND = "BebasNeue-Bold.otf"
F_SERIF = "LiberationSerif-Bold.ttf"
F_SANS = "Inter-Bold.otf"

# ---- side elevation landmarks (measured on the 3D model) --------------------
SIDE_W, SIDE_H = 976, 288
FENDER = (43, 300)            # X extent of each panel
FRONT_DOOR = (288, 533)       # its rear edge leans: X 540 at the window line, 527 at the sill
REAR_DOOR = (533, 748)
QUARTER = (734, 906)
SILL_Y = 276                  # bottom edge of the doors
HANDLE_F = (473, 513, 139)    # door handles: X0, X1, Y
HANDLE_R = (678, 720, 127)
REPEATER = (238, 152, 282, 163)   # side indicator on the fender (x0, y0, x1, y1): keep decals off it
REAR_BADGE = (200.0, 90.0, 16.0)  # Tesla badge on the liftgate in the rear canvas (x, y, keep-out radius)
BUMPER_SIDE_Y0 = 165.3        # a point at height Y on the front canvas sits at Y + this on the side canvas

CREASE_X0, CREASE_Y0, CREASE_SLOPE = 390.0, 248.0, -0.09   # the lower door crease: rises toward the rear


def shoulder_y(x):
    """The shoulder crease (the body line the door handles sit on), measured on
    the model: Y 156 at the front of the front door rising to 141 on the rear door."""
    return 156.0 - 0.0625 * (np.asarray(x, dtype=np.float64) - 380.0)


@__import__("functools").lru_cache(maxsize=8)
def door_edge(panel: str, which: str):
    """Straight line x(y) fitted to a door's front or rear edge in side_L
    (the door gap), so graphics can run parallel to it."""
    from wrapkit import panel_image
    from wrapkit.template import PANELS
    p = panel_image("side_L") == PANELS[panel]
    ys, xs = [], []
    for y in range(p.shape[0]):
        row = np.nonzero(p[y])[0]
        if len(row) > 40:
            ys.append(y)
            xs.append(row.min() if which == "front" else row.max())
    ys, xs = np.array(ys, float), np.array(xs, float)
    keep = (ys > ys.min() + 10) & (ys < ys.max() - 10)
    a, b = np.polyfit(ys[keep], xs[keep], 1)
    return lambda y: a * np.asarray(y, dtype=np.float64) + b


def seam_fade(c: Canvas, length: float, start: float = 3.0):
    """0..1 field for a silver-to-black gradient that starts exactly on the gap
    between the front and rear doors (the front door stays silver) and is fully
    dark ``length`` px further back; parallel to the door gap."""
    gap = door_edge("rear_door_L", "front")
    X, Y = c.grid()
    return smoothstep(0.0, length, X - gap(Y) - start)


STAR_DARK = 0.4      # stars start where the fade to black is this far along (they need dark paint to show)


def in_dark(length: float, start: float = 3.0):
    """where= rule for star_field: the part of a seam fade that has turned dark."""
    return lambda x, y: seam_darkness(x, y, length, start) >= STAR_DARK


def seam_darkness(x, y, length: float, start: float = 3.0) -> float:
    """seam_fade at one point (for star fields)."""
    gap = door_edge("rear_door_L", "front")
    t = float(np.clip((x - float(gap(y)) - start) / length, 0.0, 1.0))
    return t * t * (3 - 2 * t)


def belt_y(x):
    """Height of the window line (top edge of the doors) at side X."""
    return np.interp(x, [288, 540, 748], [122, 111, 96])


def crease_y(x):
    """Height of the lower door crease at side X."""
    return CREASE_Y0 + CREASE_SLOPE * (np.asarray(x, dtype=np.float64) - CREASE_X0)


def crease_band(c: Canvas, x0, x1, thickness, offset=0.0, end_slant=0.0):
    """Mask of a straight band lying on the lower door crease (its top edge is
    the crease, moved down by ``offset``).  end_slant leans the rear end."""
    top0, top1 = float(crease_y(x0)) + offset, float(crease_y(x1)) + offset
    return c.mask_polygon([(x0, top0), (x1 - end_slant, top1), (x1, top1 + thickness), (x0, top0 + thickness)])


def rocker(c: Canvas, x0, x1, offset):
    """Mask of everything from the crease (moved down by ``offset``) to the sill."""
    return c.mask_polygon([(x0, float(crease_y(x0)) + offset), (x1, float(crease_y(x1)) + offset),
                           (x1, c.h + 2), (x0, c.h + 2)])


RAIL_MID = ([10, 70, 130, 190, 250, 310, 370, 430, 490], [19, 24, 27, 30.5, 31, 31, 29.5, 29, 26])


def rail_mid(x):
    """Centre of the part of the roof-rail strip the car really shows (only
    about half of the strip's height is used)."""
    return np.interp(x, *RAIL_MID)


def rail_x(side_x):
    """Strip X of the roof rail above a given side-elevation X."""
    return (np.asarray(side_x, dtype=np.float64) - 273.0) / 0.966


# ---- base paint -------------------------------------------------------------
# layered silver on the side canvases, by height (canvas Y): bright along the
# top of the body, a little deeper over the door faces, darkest at the sills
SIDE_TONES = [(96, "#E3E6E9"), (150, "#D1D5D9"), (180, "#C2C7CC"), (218, "#AFB5BB"), (252, "#9DA3AA"), (288, "#8E949B")]


def silver_gradient(c: Canvas):
    """Light-to-dark layers of silver down the body side - the metal look comes
    from these tones rather than from painted reflections."""
    return c.gradient_field(SIDE_TONES, axis="y")


def bumper_gradient(c: Canvas, y0=0.0):
    """Colour field of the front bumper by height: silver under the hood lip
    falling away to near-black at the splitter.  y0 shifts it for canvases
    whose Y origin differs from the front elevation's."""
    return c.gradient_field([(y0 + 4, NOSE), (y0 + 26, "#A7ACB1"), (y0 + 66, BUMPER_MID), (y0 + 116, BUMPER_LOW)],
                            axis="y")


def silver_side(c: Canvas):
    """Silver body side: sheen, a slightly deeper tone toward the nose, and the
    side of the front bumper in the same gradient as its front."""
    X, Y = c.grid()
    c.paint(np.ones_like(X), silver_gradient(c))
    c.paint((1 - smoothstep(40, 290, X)) * 0.9, NOSE)
    c.paint((1 - smoothstep(134, 144, X)) * smoothstep(166, 176, Y), bumper_gradient(c, BUMPER_SIDE_Y0))


def hood_base(c: Canvas):
    """Silver hood in layers: bright at the windscreen and along the crown,
    deeper toward the nose and toward the side edges."""
    X, Y = c.grid()
    c.paint(np.ones_like(X), c.gradient_field([(8, "#E2E5E8"), (c.h * 0.5, SILVER), (c.h - 10, NOSE)], axis="y"))
    side = np.clip(np.abs(X - c.w / 2) / (c.w / 2), 0, 1)
    c.paint(0.55 * smoothstep(0.35, 1.0, side), "#A3A9AF")


def hood_edge_bands(c: Canvas, inset, width, y0=2, y1=254):
    """Mask of two bands that hug the hood's side edges (the shut line next to
    the fenders).  inset / width: number or callable of canvas Y.  A band that
    should start right at the edge uses a small negative inset (it then runs
    a few pixels past the edge, so no sliver of base colour is left there)."""
    m = c.view.mask()
    rows = [y for y in range(int(y0), int(y1) + 1) if m[y].sum() >= 20]
    left = np.array([np.nonzero(m[y])[0][0] for y in rows], dtype=np.float64)
    right = np.array([np.nonzero(m[y])[0][-1] + 1 for y in rows], dtype=np.float64)
    # follow the real outline, only evening out its pixel staircase
    left = ndi.uniform_filter1d(left, 7, mode="nearest")
    right = ndi.uniform_filter1d(right, 7, mode="nearest")
    polys = []
    for side in (0, 1):
        outer, inner = [], []
        for i, y in enumerate(rows):
            a = inset(y) if callable(inset) else inset
            w = width(y) if callable(width) else width
            if side == 0:
                outer.append((left[i] + a, y)); inner.append((left[i] + a + w, y))
            else:
                outer.append((right[i] - a, y)); inner.append((right[i] - a - w, y))
        polys.append(outer + inner[::-1])
    return c.mask_polygons(polys)


def race_hood(c: Canvas, number: str):
    """Hood of the preferred front: a broad teal stripe with a pinstripe inside
    it along each hood edge, a black number plate up near the windscreen and a
    small teal wordmark ahead of it; clear of the Tesla badge at the nose."""
    hood_base(c)
    # broad stripe starting right at the hood edge (no white border), pinstripe inside it
    c.paint(hood_edge_bands(c, -4, lambda y: float(np.interp(y, [14, 90, 240], [19, 19, 10]))), TEAL)
    c.paint(hood_edge_bands(c, lambda y: float(np.interp(y, [14, 90, 240], [21, 21, 10])), 4.6, y1=244), TEAL)
    cx = c.w / 2 + 1
    c.stamp(block_plate(number, 52), cx, 96)
    c.stamp(wordmark("PETRONAS", 13, TEAL_DEEP, font=F_WORD, tracking=1.4), cx, 146)


def race_bumper(c: Canvas):
    """Front bumper of the preferred front: the silver-to-black gradient with
    the lubricant wordmark in white on the dark part, above the grille."""
    X, _ = c.grid()
    c.paint(np.ones_like(X), bumper_gradient(c))
    cx = c.w / 2
    c.stamp(wordmark("PETRONAS", 12, WHITE, font=F_WORD, tracking=1.6), cx, 44)
    c.stamp(text_decal("Syntium", "Montserrat-BoldItalic.otf", 17, fill=WHITE), cx, 62)


def rear_marks(c: Canvas):
    """Rear elevation: one teal line across the bumper (the band of the
    liftgate with the tail lamps is left to the star field)."""
    c.paint(c.mask_rect(112, 189, c.w - 112, 192.5, radius=1.5), TEAL)


REAR_KEEP = dict(rects=[(100, 182, 304, 199)], circles=[REAR_BADGE])   # bumper line, Tesla badge


def paint_deck(pitch, radius, colour=STAR, opacity=1.0, inner=0.17):
    """The liftgate from above (frame of the rear glass, top of the spoiler):
    black, filled with the same stars as the rest of the tail."""
    c = Canvas("deck", BLACK)
    star_field(c, 0, c.w, 4, c.h, pitch, radius, colour=colour, opacity=opacity, inner=inner, margin=1.5)
    return c.out()


# ---- decals -----------------------------------------------------------------
def star_lattice(x0, x1, y0, y1, pitch, radius, rot=0.0, inner=0.17, stagger=True):
    """List of star polygons on a triangular lattice.  radius: number or
    callable (x, y) -> radius in px (<= 0 skips the star)."""
    polys = []
    row = 0
    y = y0
    while y <= y1:
        x = x0 + (pitch / 2 if (stagger and row % 2) else 0.0)
        while x <= x1:
            r = radius(x, y) if callable(radius) else radius
            if r > 0.7:
                polys.append(star3(x, y, r, rot, inner))
            x += pitch
        y += pitch * 0.866
        row += 1
    return polys


def _edge_distance(view: str) -> np.ndarray:
    """Distance (px) from every canvas pixel to the nearest panel edge."""
    p = panel_image(view)
    edge = np.zeros(p.shape, bool)
    edge[:-1] |= p[:-1] != p[1:]
    edge[1:] |= p[:-1] != p[1:]
    edge[:, :-1] |= p[:, :-1] != p[:, 1:]
    edge[:, 1:] |= p[:, :-1] != p[:, 1:]
    return ndi.distance_transform_edt(~edge)


_EDGE = {}


def _frame(n):
    """Tangent frame of a surface with normal n = (along canvas X, along canvas
    Y, toward the viewer): (right, up) unit vectors in the same coordinates,
    'up' being the canvas' up direction (world up on the side, front and rear
    views) laid onto the surface."""
    n = np.asarray(n, dtype=np.float64)
    n = n / np.linalg.norm(n)
    up = np.array([0.0, -1.0, 0.0]) - (-n[1]) * n
    up /= np.linalg.norm(up)
    right = np.cross(up, n)
    if right[0] < 0:
        right = -right
    return right, up


def _lift(d, n):
    """Canvas offset d (px) -> offset on the surface with normal n (px, 3D)."""
    return np.array([d[0], d[1], -(n[0] * d[0] + n[1] * d[1]) / n[2]])


def on_body(view: str, shape, cx, cy, iterations=3):
    """Lay a flat shape onto the car: ``shape`` is a list of (x, y) offsets as
    the shape should measure on the body (px at the canvas scale, y down,
    so (0, -r) points straight up), centred on canvas point (cx, cy).  Returns
    the canvas points that draw it at that size and angle on the surface: the
    projection's foreshortening and the direction of 'up' on a slanted panel
    are both undone, and each point is refined with the normal under it so a
    shape that sits on a gentle curve keeps its size too."""
    ni = normal_image(view)
    h, w = ni.shape[:2]

    def normal_at(x, y):
        v = ni[int(np.clip(round(y), 0, h - 1)), int(np.clip(round(x), 0, w - 1))].astype(np.float64)
        return v / max(np.linalg.norm(v), 1e-9)
    n0 = normal_at(cx, cy)
    if n0[2] < 0.2:
        return [(cx + x, cy + y) for x, y in shape]
    right, up = _frame(n0)
    Tu, Tv = _lift((1.0, 0.0), n0), _lift((0.0, 1.0), n0)
    J = np.array([[right @ Tu, right @ Tv], [up @ Tu, up @ Tv]])   # canvas -> (right, up) on the surface
    Ji = np.linalg.inv(J)
    out = []
    for x, y in shape:
        s = np.array([x, -y], dtype=np.float64)                      # wanted offset on the surface
        d = Ji @ s
        L = float(np.linalg.norm(s))
        for _ in range(iterations if L > 0 else 0):
            n1 = normal_at(cx + d[0], cy + d[1])
            nm = n0 + n1
            nm /= np.linalg.norm(nm)
            if nm[2] < 0.2:
                break
            P = _lift(d, nm)                                           # where d lands on the body
            got = np.array([right @ P, up @ P])
            got *= np.linalg.norm(P) / max(np.linalg.norm(got), 1e-9)   # its length along the surface
            d = d + Ji @ (s - got)
        out.append((cx + float(d[0]), cy + float(d[1])))
    return out


def star_field(c: Canvas, x0, x1, y0, y1, pitch, radius, keep=None, inner=0.17,
               margin=2.0, min_tilt=0.55, colour=STAR, opacity=1.0, where=None, view=None):
    """Three-pointed stars on a triangular lattice, laid out in this canvas but
    shaped on the car (on_body): every star has the same size, one arm pointing
    straight up, and the same colour and opacity everywhere.  Only whole stars
    are drawn: a star that would cross a panel gap, an edge, a bend, a strongly
    foreshortened area or a ``keep`` hole (boolean canvas mask, False = keep
    clear) is left out instead of being cut.  ``where``: optional callable
    (x, y) -> bool choosing where the field is - a star is either there in
    full or not at all, never faded."""
    if callable(opacity):
        raise TypeError("star_field: opacity is one number for every star; use where= to shape the field")
    view = view or c.view.name
    p = panel_image(view)
    if view not in _EDGE:
        _EDGE[view] = _edge_distance(view)
    edge = _EDGE[view]
    ni = normal_image(view)
    fm = facing_min(view)
    h, w = p.shape
    shape = star3(0.0, 0.0, radius, 0.0, inner)
    polys = []
    for poly in star_lattice(x0, x1, y0, y1, pitch, radius, inner=inner):
        cx = float(np.mean([q[0] for q in poly]))
        cy = float(np.mean([q[1] for q in poly]))
        ix0, iy0 = int(np.clip(cx, 0, w - 1)), int(np.clip(cy, 0, h - 1))
        n0 = ni[iy0, ix0]
        if n0[2] < min_tilt:                 # facing away, or seen too obliquely
            continue
        if where is not None and not where(cx, cy):
            continue
        pid = p[iy0, ix0]
        if pid == 0:
            continue
        pts = on_body(view, shape, cx, cy)
        ok = True
        # every vertex and points along every edge (the arms are thin)
        probe = [(cx, cy)] + list(pts)
        for (ax_, ay_), (bx_, by_) in zip(pts, pts[1:] + pts[:1]):
            probe += [(ax_ + (bx_ - ax_) * t, ay_ + (by_ - ay_) * t) for t in (0.25, 0.5, 0.75)]
        for x, y in probe:
            ix, iy = int(round(x)), int(round(y))
            if not (0 <= ix < w and 0 <= iy < h) or p[iy, ix] != pid or edge[iy, ix] < margin:
                ok = False
                break
            nv = ni[iy, ix]
            if nv[2] < min_tilt or fm[iy, ix] < min_tilt or float(np.dot(nv, n0)) < 0.94:
                ok = False                   # seen too obliquely, over a fold, or wrapping over a bend
                break
            if keep is not None and not keep[iy, ix]:
                ok = False
                break
        if ok:
            polys.append(pts)
    if polys:
        c.paint(c.mask_polygons(polys), colour, opacity)
    return len(polys)


def keep_clear(c: Canvas, rects=(), circles=()):
    """Boolean canvas mask that is False inside the given rectangles
    (x0, y0, x1, y1) and circles (x, y, r): pass it to star_field as keep."""
    m = np.ones((c.h, c.w), bool)
    yy, xx = np.mgrid[0:c.h, 0:c.w]
    for x0, y0, x1, y1 in rects:
        m &= ~((xx >= x0) & (xx <= x1) & (yy >= y0) & (yy <= y1))
    for x, y, r in circles:
        m &= (xx - x) ** 2 + (yy - y) ** 2 > r * r
    return m


def surface_decal(img: Image.Image, view: str, cx, cy) -> Image.Image:
    """Pre-squash a decal (rendered at the canvas supersampling) so it keeps its
    proportions on a tilted part of the body (squashed by the foreshortening, as in on_body)."""
    ni = normal_image(view)
    h, w = ni.shape[:2]
    nx, ny, nv = ni[int(np.clip(cy, 0, h - 1)), int(np.clip(cx, 0, w - 1))]
    f = float(abs(nv))
    d = np.array([nx, ny], dtype=np.float64)
    if np.linalg.norm(d) < 1e-6 or f > 0.98:
        return img
    d /= np.linalg.norm(d)
    M = np.eye(2) - (1.0 - f) * np.outer(d, d)          # output = M @ input, about the centre
    Minv = np.linalg.inv(M)
    W, H = img.size
    c = np.array([W / 2, H / 2])
    off = c - Minv @ c
    return img.transform((W, H), Image.AFFINE, (Minv[0, 0], Minv[0, 1], off[0], Minv[1, 0], Minv[1, 1], off[1]),
                         resample=Image.BICUBIC)


def deck_band_y(x):
    """Centre line of the top of the rear spoiler in the deck canvas."""
    from wrapkit import silhouette
    m = silhouette("deck")
    xi = int(np.clip(round(x), 0, m.shape[1] - 1))
    ys = np.nonzero(m[150:, xi])[0] + 150
    return float((ys.min() + ys.max()) / 2) if len(ys) else 200.0


def block_plate(number="63", size=44.0, plate=BLACK, digits=WHITE, radius=4.0):
    """Race number in blocky digits on a dark plate."""
    num = block_digits(number, size * 0.6, digits, weight=0.22)
    return layer(box_decal(num.width / 4 + size * 0.5, size, plate, radius=radius), num)


def three_bars(height=20.0, fill=BLACK):
    """Three slanted bars of rising height (kit-supplier mark)."""
    from PIL import Image, ImageDraw
    S = 4
    w, h = int(height * 1.5 * S), int(height * S)
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    col = tuple(int(v) for v in rgb(fill)) + (255,)
    bar = 0.24 * w
    for i, frac in enumerate((0.38, 0.69, 1.0)):
        x0 = i * 0.29 * w
        top = h * (1 - frac)
        lean = 0.58 * (h - top)
        d.polygon([(x0, h), (x0 + bar, h), (x0 + bar + lean, top), (x0 + lean, top)], fill=col)
    return im.crop(im.getbbox())


def wordmark(text, size, fill, font=F_WORD_IT, tracking=0.6, **kw):
    return text_decal(text, font, size, fill=fill, tracking=tracking, **kw)


class Mirrored:
    """A pair of mirror-image canvases (both sides, both roof rails, both
    mirror caps).  Paint geometry once on ``art`` (drawn for the LEFT side,
    front of the car at X = 0); add text and logos with ``decal`` so they read
    correctly on both sides instead of being mirror-written on the right."""

    def __init__(self, left_view: str, base=SILVER):
        self.left_name = left_view
        self.right_name = left_view[:-1] + "R"
        self.art = Canvas(left_view, base)
        self._decals = []

    def decal(self, img, x, y, rot=0.0, sides="LR", opacity=1.0, surface=False):
        """surface=True pre-squashes the decal so it keeps its proportions on a
        tilted part of the body (only for the side canvases)."""
        self._decals.append((img, x, y, rot, sides, opacity, surface))

    def render(self) -> dict:
        left = self.art
        right = self.art.mirrored()
        for img, x, y, rot, sides, op, surface in self._decals:
            if "L" in sides:
                im = surface_decal(img, self.left_name, x, y) if surface else img
                left.stamp(im, x, y, rot, op)
            if "R" in sides:
                im = surface_decal(img, self.right_name, right.w - x, y) if surface else img
                right.stamp(im, right.w - x, y, -rot, op)
        return {self.left_name: left.out(), self.right_name: right.out()}


def black_rails(pillar_line=True, teal_foot=False) -> Mirrored:
    """Black A-pillars and roof rails.  pillar_line: a thin teal line up the
    middle of the A-pillar, to go with the black mirror cap and its teal line
    (it starts at the foot of the pillar, level with the mirror stripe, and
    tapers out where the pillar meets the roof)."""
    r = Mirrored("rail_L", base=BLACK)
    c = r.art
    if pillar_line:
        m = c.view.mask()
        xs = np.arange(0, 252, 2, dtype=np.float64)
        mid = []
        for x in xs.astype(int):
            ys = np.nonzero(m[:, x])[0]
            mid.append((ys.min() + ys.max()) / 2.0 if len(ys) else np.nan)
        mid = np.array(mid)
        ok = ~np.isnan(mid)
        mid = np.interp(xs, xs[ok], mid[ok])
        mid = ndi.uniform_filter1d(mid, 7, mode="nearest")
        half = np.interp(xs, [0, 200, 250], [2.2, 2.2, 0.0])          # ~2.5 cm wide, tapering at the roof
        xs[0] = -3.0
        c.polygon([(x, y - w) for x, y, w in zip(xs, mid, half)] +
                  [(x, y + w) for x, y, w in zip(xs[::-1], mid[::-1], half[::-1])], TEAL)
    if teal_foot:
        c.paint(c.mask_rect(-2, -2, 11, c.h + 2), TEAL)
    return r


def striped_mirrors(y0=1.312, y1=1.338) -> dict:
    """Black mirror caps with a level teal stripe: every point of the cap between
    heights y0 and y1 (metres above the ground, measured on the 3D model), so it
    reads as a horizontal line from the side and from the front."""
    out = {}
    for name in ("mirror_L", "mirror_R"):
        c = Canvas(name, BLACK)
        h = np.repeat(np.repeat(c.view.height(), 4, 0), 4, 1)
        h = ndi.grey_dilation(h, size=(9, 9))                 # carry the band into the hidden rim
        band = ((h >= y0) & (h <= y1)).astype(np.float32)
        band = ndi.uniform_filter(band, 3)                     # soften the staircase
        c.paint(band, TEAL)
        out[name] = c.out()
    return out
