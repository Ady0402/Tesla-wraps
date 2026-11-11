"""B3 'Sidepod' - B's front and rear with a side after the W16's sidepod: the
body stays silver above the shoulder crease, everything below it is a black
'sidepod' from the front door's leading edge back, with one teal line on the
crease between them.  Stars fill the sidepod toward the tail.
"""
from __future__ import annotations

import numpy as np

from wrapkit import Canvas, smoothstep, text_decal
from designs.w16_common import *
from designs import w16_b
from designs.w16_b_side import QUARTER_KEEP, fender_marks, quarter_marks

NAME = "W16_B3_Sidepod"
TITLE = "B3 - Sidepod"
STAR_R = w16_b.STAR_R_B


def paint_sides() -> dict:
    s = Mirrored("side_L")
    c = s.art
    X, Y = c.grid()
    silver_side(c)
    black = c.gradient_field([(60, CARBON), (c.h, BLACK)], axis="y")
    f = door_edge("front_door_L", "front")
    front = f(Y) + 12                                    # parallel to the front door's leading edge
    pod = smoothstep(-1.5, 1.5, X - front) * smoothstep(-1.5, 1.5, Y - shoulder_y(X))
    c.paint(pod, black)
    # behind the rear door the whole quarter panel is black (split on the door gap)
    r = door_edge("rear_door_L", "rear")
    c.paint(smoothstep(-1.0, 1.0, X - r(Y) + 3), black)

    def fade(x, y):
        return float(np.interp(x, [420, 560, 700, 920], [0.0, 0.9, 1.0, 0.65]))
    xs, ys = np.arange(c.w), np.arange(c.h)[:, None]
    sy = shoulder_y(xs)[None, :]
    keep = keep_clear(c, rects=[(330, 196, 512, 236)] + QUARTER_KEEP["rects"],
                      circles=QUARTER_KEEP["circles"])
    pod_mask = (ys > sy + 8) | (xs[None, :] > 745)
    keep &= pod_mask
    star_field(c, 300, 990, 40, 290, 25, STAR_R, keep=keep, inner=0.19, colour=SILVER_HI, margin=1.2, opacity=fade)

    # one teal line on the shoulder crease, from the pod's front edge to the end of the rear door
    xa0 = float(f(shoulder_y(300))) + 12
    xa1 = float(r(shoulder_y(740))) - 6
    ya0, ya1 = float(shoulder_y(xa0)), float(shoulder_y(xa1))
    c.polygon([(xa0, ya0 - 3), (xa1, ya1 - 3), (xa1, ya1 + 4), (xa0, ya0 + 4)], TEAL)

    s.decal(wordmark("PETRONAS", 24, WHITE, tracking=0.8, stroke=1.0, stroke_fill="#2E3237"), 421, 216)
    s.decal(text_decal("TeamViewer", F_SANS, 10.5, fill=WHITE), 421, 178)
    fender_marks(s)
    quarter_marks(s)
    return s.render()


def build():
    return w16_b.build(paint_sides)
