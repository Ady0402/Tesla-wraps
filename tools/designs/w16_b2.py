"""B2 'Shoulder Line' - B's front and rear with a calmer side: silver front
doors that fade to black across the rear door, and two teal pinstripes laid
straight along the shoulder crease (the body line the door handles sit on)
from the front door to the end of the rear door.
"""
from __future__ import annotations

import numpy as np

from wrapkit import Canvas, smoothstep, text_decal
from designs.w16_common import *
from designs import w16_b
from designs.w16_b_side import QUARTER_KEEP, fender_marks, quarter_marks

NAME = "W16_B2_Shoulder"
TITLE = "B2 - Shoulder Line"
STAR_R = w16_b.STAR_R_B
X0, X1 = 300.0, 742.0          # the pinstripes run from the front door to the end of the rear door


def paint_sides() -> dict:
    s = Mirrored("side_L")
    c = s.art
    X, Y = c.grid()
    silver_side(c)
    black = c.gradient_field([(60, CARBON), (c.h, BLACK)], axis="y")
    c.paint(seam_fade(c, 120.0), black)           # starts on the front/rear door gap

    # stars on the black: all one size, angle and brightness
    xs, ys = np.arange(c.w), np.arange(c.h)[:, None]
    sy = shoulder_y(xs)[None, :]
    keep = keep_clear(c, rects=[] + QUARTER_KEEP["rects"], circles=QUARTER_KEEP["circles"])
    keep &= ~((ys >= sy - 2) & (ys <= sy + 26))                  # clear of the pinstripes
    star_field(c, 548, 990, 48, 290, 25, STAR_R, keep=keep, inner=0.19, colour=SILVER_HI, margin=1.2,
               where=in_dark(120.0))

    # two straight teal pinstripes just below the shoulder crease, ends cut parallel to the door gaps
    def stripe(off, thick, colour):
        f = door_curve("front_door_L", "front")
        r = door_curve("rear_door_L", "rear")
        ya0, ya1 = float(shoulder_y(X0)) + off, float(shoulder_y(X1)) + off
        xa0 = float(f(ya0)) + 10
        xa1 = float(r(ya1)) - 8
        y0a, y1a = float(shoulder_y(xa0)) + off, float(shoulder_y(xa1)) + off
        c.polygon([(xa0, y0a), (xa1, y1a), (xa1 - 0.08 * thick, y1a + thick), (xa0 - 0.08 * thick, y0a + thick)], colour)
    stripe(6, 6.5, TEAL)
    stripe(17, 2.6, TEAL_DEEP)

    s.decal(wordmark("PETRONAS", 24, BLACK, tracking=0.8), 410, 218)
    s.decal(text_decal("TeamViewer", F_SANS, 11, fill=BLACK), 410, 245)
    fender_marks(s)
    quarter_marks(s)
    return s.render()


def build():
    return w16_b.build(paint_sides)
