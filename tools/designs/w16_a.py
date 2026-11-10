"""W16 'Silver Arrow' - the clean version, an upright and tidied-up take on the
owner's current wrap.

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
    silver_side(c)
    black = c.gradient_field([(60, CARBON), (c.h, BLACK)], axis="y")

    # silver front doors; the fade to black happens across the rear door,
    # leaning forward at the top like the engine-cover line of the F1 car
    edge = 536 + (Y - 190) * 0.22
    c.paint(smoothstep(-6, 120, X - edge), black)

    # star field over the rear half, thinning slightly toward the tail
    def radius(x, y):
        if x < 546:
            return 0.0
        grow = float(smoothstep(526, 568, x - (y - 190) * 0.22))
        fade = 1.0 - 0.45 * float(smoothstep(770, 925, x))
        r = 13.0 * grow * fade
        return r if r >= 5 else 0.0
    c.paint(c.mask_polygons(star_lattice(514, 990, 46, 290, 36, radius, inner=0.15)), WHITE)

    # one straight teal band along the bottom edge of the front door
    c.paint(c.mask_polygon([(293, SILL_Y - 17), (528, SILL_Y - 17), (522, SILL_Y - 4), (293, SILL_Y - 4)]), TEAL)
    c.polygon(A_PILLAR_FLASH, TEAL)
    # short teal flash low on the corner of the rear bumper
    c.paint(c.mask_rect(852, 228, 916, 233, radius=2.5), TEAL)

    s.decal(block_plate(NUMBER, 50), 398, 168)
    s.decal(wordmark("PETRONAS", 25, BLACK), 414, 224)
    s.decal(text_decal("IWC", F_SERIF, 26, fill=BLACK, tracking=1.2), 226, 143)
    return s.render()


def paint_hood():
    c = Canvas("hood", SILVER)
    hood_base(c)
    # broad teal bands on the hood's side edges, windscreen to nose
    c.paint(hood_edge_bands(c, 9, lambda y: float(np.interp(y, [14, 150, 236], [13, 13, 9]))), TEAL)
    # big race number, kept clear of the Tesla badge that sits near the nose
    c.stamp(block_digits(NUMBER, 60, BLACK, weight=0.25, shear=0.12), c.w / 2 + 1, 118)
    return c.out()


def paint_front():
    c = Canvas("front", SILVER)
    X, _ = c.grid()
    c.paint(np.ones_like(X), bumper_gradient(c))
    c.stamp(wordmark("PETRONAS", 17, WHITE), c.w / 2, 52)
    return c.out()


def paint_rear():
    c = Canvas("rear", BLACK)
    c.paint(c.mask_polygons(star_lattice(0, c.w, 80, 186, 36, 11.0, inner=0.15)), WHITE, 0.92)
    rear_marks(c)
    return c.out()


def build():
    painted = {}
    painted.update(paint_sides())
    painted.update(black_rails().render())
    painted.update(striped_mirrors())
    painted["hood"] = paint_hood()
    painted["front"] = paint_front()
    painted["rear"] = paint_rear()
    painted["deck"] = paint_deck(NUMBER, stars=(36, 9.0, WHITE, 0.92))
    return compose(painted)
