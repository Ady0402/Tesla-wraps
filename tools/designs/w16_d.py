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


def paint_sides() -> dict:
    s = Mirrored("side_L", base=BLACK)
    c = s.art
    X, Y = c.grid()
    c.paint(np.ones_like(X), c.gradient_field([(0, CARBON), (c.h, BLACK)], axis="y"))

    # silver nose: covers the front of the fender and dissolves by the door
    edge = 150 + (Y - 120) * 0.55
    silver = Canvas("side_L", SILVER)
    silver.paint(np.ones_like(X), metallic(silver))
    nose_fade_side(silver)
    c.paint(1 - smoothstep(-70, 60, X - edge), silver.px)

    # star field: bright and large where the silver ends, thinning out to the tail
    def radius(x, y):
        d = x - (150 + (y - 120) * 0.55)
        if d < -20:
            return 0.0
        grow = min(1.0, (d + 20) / 50.0)
        fade = 1.0 - 0.8 * min(1.0, max(0.0, (d - 60) / 520.0))
        r = 12.5 * grow * fade
        return r if r >= 2.5 else 0.0
    stars = c.mask_polygons(star_lattice(90, 900, 12, 250, 29, radius, inner=0.15))
    keep = 1 - c.mask_rect(318, 100, 462, 184, radius=8)        # clear space for the number
    keep = keep * (1 - rocker(c, 258, 664, -12))                # and nothing below the teal lines
    c.paint(stars * keep, STAR)

    # teal follows the lower door crease from wheel arch to wheel arch:
    # a band on the crease and a pinstripe just above it
    c.paint(crease_band(c, 264, 628, 8, end_slant=-12), TEAL)
    c.paint(crease_band(c, 264, 636, 2.2, offset=-7, end_slant=-4), TEAL_DEEP)

    s.decal(block_digits(NUMBER, 56, TEAL, weight=0.23, shear=0.1), 390, 142)
    s.decal(wordmark("PETRONAS", 18, WHITE, tracking=0.8), 598, 160)
    return s.render()


def paint_rails() -> dict:
    r = Mirrored("rail_L", base=BLACK)
    c = r.art
    c.paint(c.mask_rect(20, c.h / 2 - 1.5, c.w - 20, c.h / 2 + 1.5, radius=1.5), TEAL)
    return r.render()


def paint_mirrors() -> dict:
    return Mirrored("mirror_L", base=TEAL).render()


def paint_hood():
    c = Canvas("hood", BLACK)
    X, Y = c.grid()
    silver = Canvas("hood", SILVER)
    hood_base(silver)
    # black at the windscreen (it meets the black A-pillars), silver from mid-hood to the nose
    c.paint(smoothstep(40, 120, Y), silver.px)
    def radius(x, y):
        return float(np.interp(y, [20, 60, 110, 150], [4.0, 9.0, 9.0, 0.0]))
    c.paint(c.mask_polygons(star_lattice(0, c.w, 6, 150, 24, radius, inner=0.15)), STAR)
    c.paint(hood_edge_bands(c, 7, lambda y: float(np.interp(y, [8, 60, 236], [7, 7, 1.5]))), TEAL)
    # number kept clear of the Tesla badge that sits near the nose
    c.stamp(block_digits(NUMBER, 30, BLACK, weight=0.23, shear=0.1), c.w / 2, 164)
    return c.result()


def paint_front():
    c = Canvas("front", SILVER)
    bumper_base(c)
    c.stamp(wordmark("PETRONAS", 18, WHITE), c.w / 2, 60)
    return c.result()


def paint_liftgate():
    c = Canvas("liftgate", BLACK)
    c.paint(c.mask_polygons(star_lattice(0, c.w, 6, c.h, 29, 6.5, inner=0.15)), STAR, 0.6)
    liftgate_marks(c, NUMBER)
    return c.result()


def paint_rear():
    c = Canvas("rear", BLACK)
    c.paint(c.mask_rect(160, 78, c.w - 160, 82, radius=2), TEAL)
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
