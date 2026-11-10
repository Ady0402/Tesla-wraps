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
STAR_R_C = 9.5             # one star size everywhere on this design
INITIALS = "GR"

PANEL = (301, 133, 523, 256)     # white number panel on the front door (x0, y0, x1, y1)


def paint_sides() -> dict:
    s = Mirrored("side_L")
    c = s.art
    X, Y = c.grid()
    silver_side(c)

    # silver -> black across the rear door
    t = smoothstep(532, 678, X + (Y - 190) * 0.15)
    c.paint(t, c.gradient_field([(60, CARBON), (c.h, BLACK)], axis="y"))

    # stars all the same size: bright where the silver gives way to black,
    # dimming toward the tail
    def fade(x, y):
        d = x + (y - 190) * 0.15
        return float(np.interp(d, [536, 560, 700, 920], [0.0, 1.0, 0.85, 0.4]))
    star_field(c, 540, 990, 44, 290, 27, STAR_R_C, inner=0.2, colour=SILVER_HI, margin=1.5, opacity=fade)

    # number panel
    x0, y0, x1, y1 = PANEL
    c.paint(c.mask_rect(x0, y0, x1, y1, radius=3), WHITE)
    c.paint(c.mask_rect(x0, y1 - 15, x1, y1, radius=0), TEAL)
    c.paint(c.mask_rect(x0, y1, x1, y1 + 3.5, radius=0), BLACK)
    # teal-over-black flash running forward from the panel across the fender
    c.polygon([(231, 143), (x0, 138), (x0, 151), (237, 155)], TEAL)
    c.polygon([(237, 155), (x0, 151), (x0, 157), (241, 160)], BLACK)

    cx = (x0 + x1) / 2
    s.decal(block_digits(NUMBER, 44, BLACK, weight=0.23, shear=0.1), cx - 12, 170)
    s.decal(text_decal(INITIALS, "Jura-Bold.otf", 19, fill=BLACK, tracking=-1.2), x0 + 28, 172)
    # kit-supplier bars sit below the door handle (X 473-513, Y 139)
    s.decal(three_bars(19, BLACK), x1 - 34, 180)
    s.decal(wordmark("PETRONAS", 25, BLACK, font=F_WORD, tracking=1.0), cx, 218)
    # on the flat of the fender, level with the flash (higher up it folds onto the shoulder)
    s.decal(text_decal("IWC", F_SERIF, 16, fill="#2A2D31", tracking=1.0), 190, 148)
    return s.render()


def paint_rails() -> dict:
    r = black_rails()
    c = r.art
    # a single row of stars along the roof line, as on the reference
    xs = np.arange(170, c.w - 14, 24)
    c.paint(c.mask_polygons([star3(x, float(rail_mid(x)), 6.0, 0.0, 0.2) for x in xs]), WHITE)
    return r.render()


def paint_hood():
    c = Canvas("hood", SILVER)
    race_hood(c, NUMBER)
    return c.out()


def paint_front():
    c = Canvas("front", SILVER)
    race_bumper(c)
    return c.out()


def paint_rear():
    c = Canvas("rear", BLACK)
    rear_marks(c)
    keep = keep_clear(c, **REAR_KEEP)
    star_field(c, 0, c.w, 30, 240, 27, STAR_R_C, keep=keep, inner=0.2, colour=SILVER_HI, opacity=0.45, margin=1.5)
    return c.out()


def build():
    painted = {}
    painted.update(paint_sides())
    painted.update(paint_rails())
    painted.update(striped_mirrors())
    painted["hood"] = paint_hood()
    painted["front"] = paint_front()
    painted["rear"] = paint_rear()
    painted["deck"] = paint_deck(27, STAR_R_C, colour=SILVER_HI, opacity=0.45, inner=0.2)
    return compose(painted, finish=FINISH)
