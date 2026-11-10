"""W16 'Russell 63' - the number-panel version, after the third reference:
a white panel on the front door with a big blocky 63, PETRONAS and a teal
base line, broad teal stripes over the hood, and a halftone of three-pointed
stars that grows out of the silver and shrinks into the black tail.
"""
from __future__ import annotations

import numpy as np

from wrapkit import Canvas, block_digits, compose, smoothstep, text_decal
from designs.w16_common import *

NAME = "W16_Russell_63"
TITLE = "C - Russell 63"
NUMBER = "63"
INITIALS = "GR"

PANEL = (276, 92, 498, 216)     # white number panel on the front door (x0, y0, x1, y1)


def paint_sides() -> dict:
    s = Mirrored("side_L")
    c = s.art
    X, Y = c.grid()
    c.paint(np.ones_like(X), metallic(c))
    nose_fade_side(c)

    # silver -> black across the rear door
    t = smoothstep(505, 650, X + (Y - 150) * 0.15)
    c.paint(t, c.gradient_field([(0, CARBON), (c.h, BLACK)], axis="y"))

    # halftone stars: so big they merge with the silver at the door gap,
    # shrinking to specks on the black tail
    def radius(x, y):
        d = x + (y - 150) * 0.15
        if d < 498:
            return 0.0
        return float(np.interp(d, [498, 520, 600, 700, 800, 890], [9.0, 17.0, 13.5, 9.5, 6.0, 3.0]))
    c.paint(c.mask_polygons(star_lattice(492, 900, 14, 250, 27, radius, inner=0.2)), SILVER_HI)

    # number panel
    x0, y0, x1, y1 = PANEL
    c.paint(c.mask_rect(x0, y0, x1, y1, radius=3), WHITE)
    c.paint(c.mask_rect(x0, y1 - 15, x1, y1, radius=0), TEAL)
    c.paint(c.mask_rect(x0, y1, x1, y1 + 3.5, radius=0), BLACK)
    # teal-over-black flash running forward from the panel to the front wheel arch
    c.polygon([(206, 101), (x0, 96), (x0, 109), (212, 113)], TEAL)
    c.polygon([(212, 113), (x0, 109), (x0, 115), (216, 118)], BLACK)

    cx = (x0 + x1) / 2
    s.decal(block_digits(NUMBER, 44, BLACK, weight=0.23, shear=0.1), cx - 12, 126)
    s.decal(text_decal(INITIALS, "Jura-Bold.otf", 19, fill=BLACK, tracking=-1.2), x0 + 28, 128)
    # kit-supplier bars sit below the door handle (X 458-497, Y ~115)
    s.decal(three_bars(19, BLACK), x1 - 34, 137)
    s.decal(wordmark("PETRONAS", 25, BLACK, font=F_WORD, tracking=1.0), cx, 177)
    s.decal(text_decal("IWC", F_SERIF, 17, fill="#2A2D31", tracking=1.0), 196, 68)
    return s.render()


def paint_rails() -> dict:
    r = Mirrored("rail_L", base=BLACK)
    c = r.art
    # a single row of stars along the roof line, as on the reference
    c.paint(c.mask_polygons(star_lattice(170, c.w - 14, c.h / 2 + 1, c.h / 2 + 2, 24, 7.5, stagger=False, inner=0.2)), WHITE)
    return r.render()


def paint_mirrors() -> dict:
    m = Mirrored("mirror_L", base=BLACK)
    c = m.art
    c.paint(c.mask_rect(0, c.h * 0.36, c.w, c.h * 0.62), TEAL)
    return m.render()


def paint_hood():
    c = Canvas("hood", SILVER)
    race_hood(c, NUMBER)
    return c.result()


def paint_front():
    c = Canvas("front", SILVER)
    race_bumper(c)
    return c.result()


def paint_liftgate():
    c = Canvas("liftgate", BLACK)
    c.paint(c.mask_polygons(star_lattice(0, c.w, 6, c.h, 27, 6.0, inner=0.2)), SILVER_HI, 0.8)
    liftgate_marks(c, NUMBER)
    return c.result()


def paint_rear():
    c = Canvas("rear", BLACK)
    c.paint(c.mask_rect(140, 78, c.w - 140, 82, radius=2), TEAL)
    return c.result()


def build():
    painted = {}
    painted.update(paint_sides())
    painted.update(paint_rails())
    painted.update(paint_mirrors())
    painted["hood"] = paint_hood()
    painted["front"] = paint_front()
    painted["liftgate"] = paint_liftgate()
    painted["rear"] = paint_rear()
    return compose(painted)
