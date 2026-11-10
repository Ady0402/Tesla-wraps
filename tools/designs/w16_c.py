"""W16 'Black Arrow' - the dark one: carbon-black body, a silver nose that
dissolves into a star field, twin teal flow lines and a large teal number.
"""
from __future__ import annotations

import numpy as np

from wrapkit import Canvas, compose, ribbon, smoothstep, spline, text_decal
from designs.w16_common import *

NAME = "W16_Black_Arrow"
TITLE = "C - Black Arrow"
NUMBER = "63"


def paint_sides() -> dict:
    s = Mirrored("side_L", base=BLACK)
    c = s.art
    X, Y = c.grid()
    c.paint(np.ones_like(X), c.gradient_field([(0, CARBON), (c.h, BLACK)], axis="y"))

    # silver nose: covers the front of the fender and dissolves by the door
    edge = 150 + (Y - 120) * 0.55
    c.paint(1 - smoothstep(-70, 60, X - edge), metallic(c))

    # star field: bright and large where the silver ends, thinning out to the tail
    def radius(x, y):
        d = x - (150 + (y - 120) * 0.55)
        if d < -20:
            return 0.0
        grow = min(1.0, (d + 20) / 50.0)
        fade = 1.0 - 0.8 * min(1.0, max(0.0, (d - 60) / 520.0))
        return 12.5 * grow * fade
    stars = c.mask_polygons(star_lattice(90, 900, 12, 250, 29, radius))
    keep = 1 - c.mask_rect(330, 104, 480, 200, radius=10)       # clear space for the number
    c.paint(stars * keep, STAR)

    # twin teal flow lines: rise over the front arch, run the length, kick up at the tail
    main = spline([(92, 136), (170, 104), (262, 108), (400, 222), (560, 226), (660, 214), (740, 132), (880, 104)], 22)
    c.polygon(ribbon(main, np.interp(np.linspace(0, 1, len(main)), [0, 0.3, 0.6, 1], [2, 7, 7, 2])), TEAL)
    thin = spline([(110, 148), (176, 118), (254, 122), (392, 234), (560, 238), (668, 226), (750, 146), (880, 118)], 22)
    c.line(thin, 2.0, TEAL_DEEP)

    s.decal(text_decal(NUMBER, F_BLACK_IT, 62, fill=TEAL, stroke=1.6, stroke_fill=WHITE, tracking=-1.5), 404, 150)
    s.decal(wordmark("PETRONAS", 18, WHITE, tracking=0.8), 600, 176)
    s.decal(text_decal("IWC", F_SERIF, 13, fill=BLACK, tracking=0.8), 96, 52)
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
    cx = c.w / 2
    # silver arrow: full width at the nose, narrowing to a point at the windscreen
    half = 26 + (Y / c.h) ** 1.25 * 150
    arrow = smoothstep(0, 10, half - np.abs(X - cx))
    c.paint(arrow, metallic(c, SILVER_LO, SILVER, SILVER_HI))
    # stars spill off the arrow edges onto the black
    def radius(x, y):
        h = 26 + (max(0.0, y) / c.h) ** 1.25 * 150
        d = abs(x - cx) - h
        return 9.0 * max(0.0, 1.0 - d / 80.0) if d > 4 else 0.0
    c.paint(c.mask_polygons(star_lattice(0, c.w, 6, c.h, 24, radius)), STAR)
    for sgn in (-1, 1):
        pts = [(cx + sgn * (26 + (y / c.h) ** 1.25 * 150), y) for y in np.linspace(0, c.h, 40)]
        c.line(pts, 3.0, TEAL)
    # keep clear of the Tesla badge that sits near the nose
    c.stamp(text_decal(NUMBER, F_BLACK_IT, 34, fill=BLACK, tracking=-0.5), cx, 148)
    return c.result()


def paint_front():
    c = Canvas("front", SILVER)
    X, Y = c.grid()
    c.paint(np.ones_like(X), metallic(c))
    cx = c.w / 2
    c.paint(smoothstep(150, 235, np.abs(X - cx)), BLACK)
    c.stamp(wordmark("PETRONAS", 14, BLACK), cx, 58)
    return c.result()


def paint_liftgate():
    c = Canvas("liftgate", BLACK)
    c.paint(c.mask_polygons(star_lattice(0, c.w, 150, c.h, 29, 6.0)), STAR, 0.55)
    c.paint(c.mask_rect(110, 222, c.w - 110, 226, radius=2), TEAL)
    c.stamp(wordmark("PETRONAS", 16, TEAL), c.w / 2, 268)
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
