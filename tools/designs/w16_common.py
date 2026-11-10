"""Shared building blocks for the Mercedes-AMG F1 W16 tribute wraps.

All coordinates are canvas pixels (174 px per metre, see wrapkit/carmap.py).
Side elevation, left side: the nose is at X ~ 45, the tail at X ~ 925.
"""
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

# ---- side elevation landmarks (measured on the 3D model) --------------------
SIDE_W, SIDE_H = 976, 288
FENDER = (43, 300)            # X extent of each panel
FRONT_DOOR = (288, 533)       # its rear edge leans: X 540 at the window line, 527 at the sill
REAR_DOOR = (533, 748)
QUARTER = (734, 906)
SILL_Y = 276                  # bottom edge of the doors
HANDLE_F = (473, 513, 139)    # door handles: X0, X1, Y
HANDLE_R = (678, 720, 127)
BUMPER_SIDE_Y0 = 165.3        # a point at height Y on the front canvas sits at Y + this on the side canvas

CREASE_X0, CREASE_Y0, CREASE_SLOPE = 390.0, 248.0, -0.09   # the lower door crease: rises toward the rear


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
def metallic(c: Canvas, top=SILVER_HI, mid=SILVER, bottom=SILVER_LO):
    """Soft top-to-bottom sheen so flat silver does not look like grey primer."""
    return c.gradient_field([(c.h * 0.3, top), (c.h * 0.65, mid), (c.h, bottom)], axis="y")


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
    c.paint(np.ones_like(X), metallic(c))
    c.paint((1 - smoothstep(40, 290, X)) * 0.9, NOSE)
    c.paint((1 - smoothstep(134, 144, X)) * smoothstep(166, 176, Y), bumper_gradient(c, BUMPER_SIDE_Y0))


def hood_base(c: Canvas):
    """Silver hood, bright at the windscreen and deeper toward the nose."""
    X, _ = c.grid()
    c.paint(np.ones_like(X), c.gradient_field([(8, SILVER_HI), (c.h * 0.5, SILVER), (c.h - 10, NOSE)], axis="y"))


def hood_edge_bands(c: Canvas, inset, width, y0=14, y1=236):
    """Mask of two bands that hug the hood's side edges (the shut line next to
    the fenders).  inset / width: number or callable of canvas Y."""
    m = c.view.mask()
    rows = [y for y in range(int(y0), int(y1) + 1) if m[y].sum() >= 20]
    left = np.array([np.nonzero(m[y])[0][0] for y in rows], dtype=np.float64)
    right = np.array([np.nonzero(m[y])[0][-1] + 1 for y in rows], dtype=np.float64)
    ry = np.asarray(rows, dtype=np.float64)          # a smooth curve through the pixel staircase of the outline
    left = np.polyval(np.polyfit(ry, left, 4), ry)
    right = np.polyval(np.polyfit(ry, right, 4), ry)
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
    c.paint(hood_edge_bands(c, 8, lambda y: float(np.interp(y, [14, 90, 236], [15, 15, 5]))), TEAL)
    c.paint(hood_edge_bands(c, lambda y: float(np.interp(y, [14, 90, 228], [30, 30, 14])), 3.2, y1=228), TEAL)
    cx = c.w / 2 + 1
    c.stamp(block_plate(number, 44), cx, 92)
    c.stamp(wordmark("PETRONAS", 12, TEAL_DEEP, font=F_WORD, tracking=1.4), cx, 138)


def race_bumper(c: Canvas):
    """Front bumper of the preferred front: the silver-to-black gradient with
    the lubricant wordmark in white on the dark part, above the grille."""
    X, _ = c.grid()
    c.paint(np.ones_like(X), bumper_gradient(c))
    cx = c.w / 2
    c.stamp(wordmark("PETRONAS", 12, WHITE, font=F_WORD, tracking=1.6), cx, 44)
    c.stamp(text_decal("Syntium", "Montserrat-BoldItalic.otf", 17, fill=WHITE), cx, 62)


def rear_marks(c: Canvas):
    """Rear elevation: a teal line under the lip of the spoiler (the Tesla
    badge sits just below it) and one across the bumper."""
    c.paint(c.mask_rect(70, 64, c.w - 70, 67.5, radius=1.5), TEAL)
    c.paint(c.mask_rect(112, 189, c.w - 112, 192.5, radius=1.5), TEAL)


def paint_deck(number: str, stars=None):
    """The liftgate from above: black frame round the rear glass, wordmark and
    race number on top of the spoiler.  stars: optional (pitch, radius, colour, opacity)."""
    c = Canvas("deck", BLACK)
    if stars:
        pitch, radius, colour, opacity = stars
        field = c.mask_polygons(star_lattice(0, c.w, 4, 150, pitch, radius, inner=0.17))
        c.paint(field, colour, opacity)
    c.stamp(wordmark("PETRONAS", 14, TEAL, tracking=0.5), 170, 203)
    c.stamp(block_digits(number, 15, TEAL, weight=0.24, shear=0.1), 262, 203)
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
        return {self.left_name: left.out(), self.right_name: right.out()}


def black_rails(teal_foot=True) -> Mirrored:
    """Black A-pillars and roof rails; the teal flash from the top of the
    fender can be carried over the foot of the A-pillar."""
    r = Mirrored("rail_L", base=BLACK)
    if teal_foot:
        r.art.paint(r.art.mask_rect(-2, -2, 11, r.art.h + 2), TEAL)
    return r


def striped_mirrors() -> dict:
    """Black mirror caps with a teal stripe."""
    m = Mirrored("mirror_L", base=BLACK)
    c = m.art
    c.paint(c.mask_rect(0, c.h * 0.36, c.w, c.h * 0.62), TEAL)
    return m.render()


# teal flash on the top of the fender at the foot of the A-pillar; it ties the
# stripe on the hood's edge to whatever starts on the door
A_PILLAR_FLASH = [(262, 100), (302, 96), (302, 124), (274, 126)]
