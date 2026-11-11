"""W16 'Black Arrow' - the dark one: carbon-black body, a silver nose that
dissolves into a star field, a straight teal band on the lower door crease
and a large teal number.
"""
from __future__ import annotations

import numpy as np

from wrapkit import Canvas, block_digits, compose, smoothstep, text_decal
from designs.w16_common import *

NAME = "W16_Black_Arrow"
TITLE = "D - Black Arrow"
NUMBER = "63"
STAR_R_D = 10.0            # one star size everywhere on this design
STAR_ALPHA_D = 0.6         # ... and one brightness


def paint_sides() -> dict:
    s = Mirrored("side_L", base=BLACK)
    c = s.art
    X, Y = c.grid()
    c.paint(np.ones_like(X), c.gradient_field([(60, CARBON), (c.h, BLACK)], axis="y"))

    # silver nose: covers the front of the fender and dissolves by the door
    edge = 178 + (Y - 160) * 0.55
    silver = Canvas("side_L", SILVER)
    silver_side(silver)
    c.paint(1 - smoothstep(-70, 60, X - edge), silver.px)

    # star field from where the silver has dissolved: every star the same size, angle and brightness
    keep = keep_clear(c, rects=[(340, 138, 488, 222), (560, 184, 680, 208)])   # the number and PETRONAS
    keep &= np.arange(c.h)[:, None] < crease_y(np.arange(c.w))[None, :] - 14   # nothing on or below the teal lines
    star_field(c, 110, 990, 44, 290, 29, STAR_R_D, keep=keep, inner=0.15, colour=STAR, opacity=STAR_ALPHA_D,
               where=lambda x, y: x - (178 + (y - 160) * 0.55) >= 20)

    # teal follows the lower door crease from wheel arch to wheel arch:
    # a band on the crease and a pinstripe just above it
    c.paint(crease_band(c, 292, 662, 8, end_slant=-12), TEAL)
    c.paint(crease_band(c, 292, 670, 2.2, offset=-7, end_slant=-4), TEAL_DEEP)

    s.decal(block_digits(NUMBER, 56, TEAL, weight=0.23, shear=0.1), 414, 180)
    s.decal(wordmark("PETRONAS", 18, WHITE, tracking=0.8), 620, 196)
    return s.render()


def paint_rails() -> dict:
    r = black_rails(pillar_line=False)
    c = r.art
    xs = np.linspace(14, c.w - 14, 60)
    c.line([(x, float(rail_mid(x))) for x in xs], 2.6, TEAL)
    return r.render()


def paint_mirrors() -> dict:
    return striped_mirrors()


def paint_hood():
    c = Canvas("hood", BLACK)
    X, Y = c.grid()
    silver = Canvas("hood", SILVER)
    hood_base(silver)
    # black at the windscreen (it meets the black A-pillars), silver from mid-hood to the nose
    c.paint(smoothstep(46, 122, Y), silver.px)
    star_field(c, 0, c.w, 10, 84, 29, STAR_R_D, inner=0.15, colour=STAR, opacity=STAR_ALPHA_D)   # on the black part only
    c.paint(hood_edge_bands(c, -4, lambda y: float(np.interp(y, [14, 70, 240], [11, 11, 6]))), TEAL)
    # number kept clear of the Tesla badge that sits near the nose
    c.stamp(block_digits(NUMBER, 30, BLACK, weight=0.23, shear=0.1), c.w / 2 + 1, 164)
    return c.out()


def paint_front():
    c = Canvas("front", SILVER)
    X, _ = c.grid()
    c.paint(np.ones_like(X), bumper_gradient(c))
    c.stamp(wordmark("PETRONAS", 17, WHITE), c.w / 2, 52)
    return c.out()


def paint_rear():
    c = Canvas("rear", BLACK)
    rear_marks(c)
    keep = keep_clear(c, **REAR_KEEP)
    star_field(c, 0, c.w, 30, 240, 29, STAR_R_D, keep=keep, inner=0.15, colour=STAR, opacity=STAR_ALPHA_D, margin=1.5)
    return c.out()


def build():
    painted = {}
    painted.update(paint_sides())
    painted.update(paint_rails())
    painted.update(paint_mirrors())
    painted["hood"] = paint_hood()
    painted["front"] = paint_front()
    painted["rear"] = paint_rear()
    painted["deck"] = paint_deck(29, STAR_R_D, colour=STAR, opacity=STAR_ALPHA_D, inner=0.15)
    return compose(painted, finish=FINISH)
