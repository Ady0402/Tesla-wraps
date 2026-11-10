"""Shared building blocks for the Mercedes-AMG F1 W16 tribute wraps."""
from __future__ import annotations

import numpy as np

from wrapkit import (Canvas, block_digits, box_decal, layer, mix, rgb, smoothstep, star3, text_decal)

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

# ---- fonts ----------------------------------------------------------------
F_WORD = "Montserrat-ExtraBold.otf"       # PETRONAS-style wide bold caps
F_WORD_IT = "Montserrat-ExtraBoldItalic.otf"
F_BLACK_IT = "Montserrat-BlackItalic.otf"
F_COND = "BebasNeue-Bold.otf"
F_SERIF = "LiberationSerif-Bold.ttf"
F_SANS = "Inter-Bold.otf"

# ---- side-view landmarks (texture px; front of car at X = 0) ---------------
SIDE_W, SIDE_H = 891, 255
SILL_Y = 236          # lowest visible line of the doors
BELT_Y = 80           # top of the front door (beltline) near the A-pillar
FENDER = (7, 277)
FRONT_DOOR = (261, 514)
REAR_DOOR = (495, 722)
QUARTER = (704, 881)


# ---- body lines the accents follow -------------------------------------------
# Tesla's own "Sketch" example draws the car's creases; in the side view the
# lower door crease runs from (290, 211) to (600, 193), rising 0.058 px per px.
CREASE_X0, CREASE_Y0, CREASE_SLOPE = 290.0, 211.0, -0.058


def crease_y(x):
    """Height of the lower door crease at side-view X."""
    return CREASE_Y0 + CREASE_SLOPE * (np.asarray(x, dtype=np.float64) - CREASE_X0)


def crease_band(c: Canvas, x0, x1, thickness, offset=0.0, end_slant=0.0):
    """Mask of a straight band lying on the lower door crease (its top edge
    is the crease, moved down by ``offset``).  end_slant leans the rear end
    forward at the top, like a cut stripe."""
    top0, top1 = float(crease_y(x0)) + offset, float(crease_y(x1)) + offset
    return c.mask_polygon([(x0, top0), (x1 - end_slant, top1), (x1, top1 + thickness), (x0, top0 + thickness)])


def rocker(c: Canvas, x0, x1, offset):
    """Mask of everything below the crease (moved down by ``offset``) to the sill."""
    return c.mask_polygon([(x0, float(crease_y(x0)) + offset), (x1, float(crease_y(x1)) + offset),
                           (x1, c.h + 2), (x0, c.h + 2)])


def hood_edge_bands(c: Canvas, inset, width, y0=8, y1=242):
    """Mask of two bands that hug the hood's side edges (the panel line next
    to the fenders).  inset / width: number or callable of view Y."""
    m = c.view.mask()
    polys = []
    for side in (0, 1):
        outer, inner = [], []
        for y in range(int(y0), int(y1) + 1):
            xs = np.nonzero(m[y])[0]
            if len(xs) < 20:
                continue
            a = inset(y) if callable(inset) else inset
            w = width(y) if callable(width) else width
            if side == 0:
                outer.append((xs[0] + a, y)); inner.append((xs[0] + a + w, y))
            else:
                outer.append((xs[-1] + 1 - a, y)); inner.append((xs[-1] + 1 - a - w, y))
        polys.append(outer + inner[::-1])
    return c.mask_polygons(polys)


def nose_fade_side(c: Canvas):
    """Darken the silver slightly toward the front tip of the fender so it
    meets the hood's front edge and the top of the bumper at the same tone."""
    X, _ = c.grid()
    c.paint((1 - smoothstep(10, 250, X)) * 0.9, NOSE)


def hood_base(c: Canvas):
    """Silver hood, bright at the windscreen and deeper toward the nose."""
    X, _ = c.grid()
    c.paint(np.ones_like(X), c.gradient_field([(0, SILVER_HI), (c.h * 0.5, SILVER), (c.h, NOSE)], axis="y"))


def bumper_base(c: Canvas):
    """Front bumper: carries on from the hood's nose tone and falls away to
    near-black at the splitter, like the underside of the F1 car's nose."""
    X, _ = c.grid()
    c.paint(np.ones_like(X), c.gradient_field(
        [(0, NOSE), (22, "#A7ACB1"), (72, BUMPER_MID), (c.h, BUMPER_LOW)], axis="y"))


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
    """A pair of mirror-image views (both flanks, both roof rails, both mirror
    caps).  Paint geometry once on ``art`` (drawn for the LEFT side, front of
    the car at X = 0); add text and logos with ``decal`` so they read correctly
    on both sides instead of being mirror-written on the right."""

    def __init__(self, left_view: str, base=SILVER):
        self.left_name = left_view
        self.right_name = left_view[:-1] + "R"
        self.art = Canvas(left_view, base)
        self._decals = []

    def decal(self, img, x, y, rot=0.0, sides="LR", opacity=1.0):
        self._decals.append((img, x, y, rot, sides, opacity))

    def render(self) -> dict:
        left = self.art
        right = self.art.mirrored()
        for img, x, y, rot, sides, op in self._decals:
            if "L" in sides:
                left.stamp(img, x, y, rot, op)
            if "R" in sides:
                right.stamp(img, right.w - x, y, -rot, op)
        return {self.left_name: left.result(), self.right_name: right.result()}


def metallic(c: Canvas, top=SILVER_HI, mid=SILVER, bottom=SILVER_LO):
    """Soft top-to-bottom sheen so flat silver does not look like grey primer."""
    return c.gradient_field([(0, top), (c.h * 0.45, mid), (c.h, bottom)], axis="y")


def liftgate_marks(c: Canvas, number: str):
    """Wordmark and race number on the wide band just below the rear glass.
    The narrow neck under it carries the Tesla badge (centre, Y ~ 200) and the
    lower lobe is the number-plate recess, so both are left clear."""
    cx = c.w / 2
    c.paint(c.mask_rect(40, 138, c.w - 40, 191, radius=3), BLACK)   # calm backing for the lettering
    c.paint(c.mask_rect(66, 186.5, c.w - 66, 190, radius=1.5), TEAL)
    c.stamp(wordmark("PETRONAS", 17, TEAL, tracking=0.5), cx - 88, 163)
    c.stamp(block_digits(number, 22, TEAL, weight=0.23, shear=0.1), cx + 96, 163)
