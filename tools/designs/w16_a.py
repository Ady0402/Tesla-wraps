"""W16 'Silver Arrow' - the clean version, an upright and tidied-up take on the
owner's current wrap.

Silver nose and front doors, a blocky number plate and PETRONAS on the front
door, one straight teal band along the bottom of the door, broad teal bands on
the hood's edges with a big race number between them, and a three-pointed-star
field that takes over as the body fades to black toward the tail.  The paint
carries baked studio reflections (designs.w16_common.FINISH).
"""
from __future__ import annotations

import numpy as np

from wrapkit import Canvas, block_digits, compose, smoothstep, text_decal
from designs.w16_common import *

NAME = "W16_Silver_Arrow"
TITLE = "A - Silver Arrow"
NUMBER = "63"
STAR_R_A = 10.0            # one star size everywhere on this design


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

    # star field over the rear half: every star the same size, the field fades in
    # with the black and dims a little toward the tail
    def fade(x, y):
        return float(smoothstep(530, 590, x - (y - 190) * 0.22)) * (1.0 - 0.3 * float(smoothstep(770, 925, x)))
    keep = keep_clear(c, rects=[(842, 220, 926, 241)])            # the teal flash on the bumper corner
    star_field(c, 532, 990, 46, 290, 36, STAR_R_A, keep=keep, inner=0.15, colour=WHITE, opacity=fade)

    # one straight teal band along the bottom edge of the front door
    c.paint(c.mask_polygon([(302, SILL_Y - 17), (516, SILL_Y - 17), (512, SILL_Y - 4), (302, SILL_Y - 4)]), TEAL)
    # short teal flash low on the corner of the rear bumper
    c.paint(c.mask_rect(852, 228, 916, 233, radius=2.5), TEAL)

    s.decal(block_plate(NUMBER, 50), 398, 168)
    s.decal(wordmark("PETRONAS", 25, BLACK), 414, 224)
    # on the flat of the fender, ahead of and above the side indicator
    s.decal(text_decal("IWC", F_SERIF, 26, fill=BLACK, tracking=1.2), 204, 138)
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
    rear_marks(c)
    keep = keep_clear(c, **REAR_KEEP)
    star_field(c, 0, c.w, 30, 240, 36, STAR_R_A, keep=keep, inner=0.15, colour=WHITE, opacity=0.7, margin=1.5)
    return c.out()


def build():
    painted = {}
    painted.update(paint_sides())
    painted.update(black_rails().render())
    painted.update(striped_mirrors())
    painted["hood"] = paint_hood()
    painted["front"] = paint_front()
    painted["rear"] = paint_rear()
    painted["deck"] = paint_deck(36, STAR_R_A, colour=WHITE, opacity=0.7, inner=0.15)
    return compose(painted, finish=FINISH)
