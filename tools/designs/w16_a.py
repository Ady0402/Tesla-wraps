"""W16 'Silver Arrow' - the clean version, closest to the touchscreen reference.

Silver nose and front doors, a blocky number plate and PETRONAS on the front
door, one straight teal band along the bottom of the door, broad teal bands on
the hood's edges with a big race number between them, and a three-pointed-star
field that takes over as the body fades to black toward the tail.
"""
from __future__ import annotations

import numpy as np

from wrapkit import Canvas, block_digits, compose, smoothstep, text_decal
from designs.w16_common import *

NAME = "W16_Silver_Arrow"
TITLE = "A - Silver Arrow"
NUMBER = "63"


def paint_sides() -> dict:
    s = Mirrored("side_L")
    c = s.art
    X, Y = c.grid()
    c.paint(np.ones_like(X), metallic(c))
    nose_fade_side(c)
    black = c.gradient_field([(0, CARBON), (c.h, BLACK)], axis="y")

    # silver front doors; the fade to black happens across the rear door,
    # leaning forward at the top like the engine-cover line of the F1 car
    edge = 508 + (Y - 150) * 0.22
    c.paint(smoothstep(-6, 120, X - edge), black)

    # star field over the rear half, thinning slightly toward the tail
    def radius(x, y):
        if x < 516:
            return 0.0
        grow = float(smoothstep(498, 540, x - (y - 150) * 0.22))
        fade = 1.0 - 0.45 * float(smoothstep(740, 890, x))
        r = 13.0 * grow * fade
        return r if r >= 5 else 0.0
    c.paint(c.mask_polygons(star_lattice(486, 900, 16, 250, 36, radius, inner=0.15)), WHITE)

    # one straight teal band along the bottom edge of the front door
    c.paint(c.mask_polygon([(268, SILL_Y - 15), (496, SILL_Y - 15), (490, SILL_Y - 3), (268, SILL_Y - 3)]), TEAL)
    # teal flash at the foot of the A-pillar (continues onto the roof rail)
    c.polygon([(244, 50), (272, 46), (280, 74), (262, 78)], TEAL)

    s.decal(block_plate(NUMBER, 50), 372, 124)
    s.decal(wordmark("PETRONAS", 25, BLACK), 392, 182)
    s.decal(text_decal("IWC", F_SERIF, 31, fill=BLACK, tracking=1.4), 176, 76)
    return s.render()


def paint_rails() -> dict:
    # black A-pillar and roof rail, with the teal flash carried over the foot of the A-pillar
    r = Mirrored("rail_L", base=BLACK)
    c = r.art
    c.paint(c.mask_rect(-2, -2, 11, c.h + 2), TEAL)
    return r.render()


def paint_mirrors() -> dict:
    m = Mirrored("mirror_L", base=BLACK)
    c = m.art
    c.paint(c.mask_rect(0, c.h * 0.36, c.w, c.h * 0.62), TEAL)
    return m.render()


def paint_hood():
    c = Canvas("hood", SILVER)
    hood_base(c)
    # broad teal bands on the hood's side edges, windscreen to nose
    c.paint(hood_edge_bands(c, 9, lambda y: float(np.interp(y, [8, 150, 238], [13, 13, 9])), y1=240), TEAL)
    # big race number, kept clear of the Tesla badge that sits near the nose
    c.stamp(block_digits(NUMBER, 62, BLACK, weight=0.25, shear=0.12), c.w / 2, 116)
    return c.result()


def paint_front():
    c = Canvas("front", SILVER)
    bumper_base(c)
    c.stamp(wordmark("PETRONAS", 18, WHITE), c.w / 2, 60)
    return c.result()


def paint_liftgate():
    c = Canvas("liftgate", BLACK)
    c.paint(c.mask_polygons(star_lattice(0, c.w, 6, c.h, 36, 11.0, inner=0.15)), WHITE, 0.92)
    liftgate_marks(c, NUMBER)
    return c.result()


def paint_rear():
    c = Canvas("rear", BLACK)
    # teal flashes low on the bumper corners (they show in side view behind the wheel)
    for x0, x1 in ((12, 92), (c.w - 92, c.w - 12)):
        c.paint(c.mask_rect(x0, 96, x1, 101, radius=2.5), TEAL)
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
