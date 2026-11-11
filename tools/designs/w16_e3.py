"""E3 'Fade + Seam Line' - B's front and rear; silver front door with a big
black 63 and PETRONAS; a teal band marks the door gap where the gradient to
black begins, and the star field fills the rear door and quarter panel."""
from __future__ import annotations

import numpy as np

from wrapkit import block_digits, smoothstep, text_decal
from designs.w16_common import *
from designs import w16_b
from designs.w16_e_side import fade_side

NAME = "W16_E3_SeamLine"
TITLE = "E3 - Fade + Seam Line"


def paint_sides() -> dict:
    gap = door_edge("rear_door_L", "front")
    xs, ys = np.arange(976), np.arange(288)[:, None]
    band_keep = [(0, 0, 0, 0)]
    s, c, _ = fade_side(length=150.0, extra_keep=[(526, 40, 560, 290)])
    X, Y = c.grid()
    # teal band on the leading edge of the rear door, parallel to the gap
    c.paint(smoothstep(-0.8, 0.8, X - gap(Y) - 5) * (1 - smoothstep(-0.8, 0.8, X - gap(Y) - 15)), TEAL)
    s.decal(block_digits("63", 60, BLACK, weight=0.24, shear=0.1), 400, 178)
    s.decal(wordmark("PETRONAS", 22, BLACK, tracking=0.8), 404, 236)
    return s.render()


def build():
    return w16_b.build(paint_sides)
