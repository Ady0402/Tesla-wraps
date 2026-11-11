"""W16 'Silver Arrow' - the clean version, an upright and tidied-up take on the
owner's current wrap.

Silver nose and front doors, a blocky number plate and PETRONAS on the front
door, one straight teal band along the bottom of the door, broad teal bands on
the hood's edges with a big race number between them, and a three-pointed-star
field that takes over as the body fades to black toward the tail.  The paint
is layered silver with a soft tonal finish (designs.w16_common.FINISH).
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
    c.paint(seam_fade(c, 126.0), black)          # starts on the front/rear door gap

    # star field over the dark rear half: every star the same size, angle and brightness
    keep = keep_clear(c, rects=[(842, 220, 926, 241)])            # the teal flash on the bumper corner
    star_field(c, 532, 990, 46, 290, 36, STAR_R_A, keep=keep, inner=0.15, colour=WHITE, where=in_dark(126.0))

    # one straight teal band along the bottom edge of the front door
    c.paint(c.mask_polygon([(302, SILL_Y - 17), (516, SILL_Y - 17), (512, SILL_Y - 4), (302, SILL_Y - 4)]), TEAL)
    # short teal flash low on the corner of the rear bumper
    c.paint(c.mask_rect(852, 228, 916, 233, radius=2.5), TEAL)

    s.decal(block_plate(NUMBER, 50), 398, 168)
    s.decal(wordmark("PETRONAS", 25, BLACK), 414, 224)
    # on the flat of the fender, ahead of and above the side indicator
    s.decal(text_decal("IWC", F_SERIF, 26, fill=BLACK, tracking=1.2), 196, 140)
    return s.render()


def paint_hood():
    c = Canvas("hood", SILVER)
    hood_base(c)
    # broad teal bands on the hood's side edges, windscreen to nose
    c.paint(hood_edge_bands(c, -4, lambda y: float(np.interp(y, [14, 150, 240], [17, 17, 13]))), TEAL)
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
    star_field(c, 0, c.w, 30, 240, 36, STAR_R_A, keep=keep, inner=0.15, colour=WHITE, margin=1.5)
    return c.out()


def build():
    painted = {}
    painted.update(paint_sides())
    painted.update(black_rails().render())
    painted.update(striped_mirrors())
    painted["hood"] = paint_hood()
    painted["front"] = paint_front()
    painted["rear"] = paint_rear()
    painted["deck"] = paint_deck(36, STAR_R_A, colour=WHITE, inner=0.15)
    return compose(painted, finish=FINISH)
