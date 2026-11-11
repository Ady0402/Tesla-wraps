"""Shared side for the E designs: the owner's favourite look - silver front
door, then a silver-to-black gradient that starts exactly on the gap between
the front and rear doors and carries a field of three-pointed stars - with
B's front (hood double stripes, 63 plate, gradient bumper) and rear."""
from __future__ import annotations

import numpy as np

from wrapkit import Canvas, smoothstep
from designs.w16_common import *
from designs.w16_b_side import QUARTER_KEEP, fender_marks, quarter_marks

STAR_R = 9.0


def fade_side(length=180.0, extra_keep=(), pitch=25, stars=True) -> tuple:
    """(Mirrored, Canvas, fade function): silver body, black from the door gap
    back over ``length`` px, star field on the dark part, B's fender and
    quarter-panel decals.  The caller adds the front-door graphics."""
    s = Mirrored("side_L")
    c = s.art
    silver_side(c)
    black = c.gradient_field([(60, CARBON), (c.h, BLACK)], axis="y")
    t = seam_fade(c, length)
    c.paint(t, black)
    gap = door_edge("rear_door_L", "front")

    def fade(x, y):
        return min(1.0, seam_darkness(x, y, length) * 1.25) * (1.0 - 0.3 * float(smoothstep(780, 920, x)))
    if stars:
        keep = keep_clear(c, rects=list(QUARTER_KEEP["rects"]) + list(extra_keep),
                          circles=QUARTER_KEEP["circles"])
        star_field(c, float(gap(150)) + 14, 990, 46, 290, pitch, STAR_R, keep=keep, inner=0.19,
                   colour=SILVER_HI, margin=1.2, opacity=fade)
    fender_marks(s)
    quarter_marks(s)
    return s, c, fade
