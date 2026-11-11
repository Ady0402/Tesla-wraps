"""B4 'Door Split' - B's front and rear with a two-tone side split exactly on
the gap between the front and rear doors: silver front door with a big
black 63, black rear door and quarter with stars, and a teal band along the
rear door's leading edge, parallel to the gap.
"""
from __future__ import annotations

import numpy as np

from wrapkit import Canvas, block_digits, smoothstep, text_decal
from designs.w16_common import *
from designs import w16_b
from designs.w16_b_side import QUARTER_KEEP, fender_marks, quarter_marks

NAME = "W16_B4_Split"
TITLE = "B4 - Door Split"
STAR_R = w16_b.STAR_R_B
NUMBER = "63"


def paint_sides() -> dict:
    s = Mirrored("side_L")
    c = s.art
    X, Y = c.grid()
    silver_side(c)
    black = c.gradient_field([(60, CARBON), (c.h, BLACK)], axis="y")
    gap = door_edge("rear_door_L", "front")              # the front/rear door gap
    c.paint(smoothstep(-1.0, 1.0, X - gap(Y) + 2), black)

    # teal band on the rear door, parallel to the gap
    c.paint(smoothstep(-1.0, 1.0, X - gap(Y) - 6) * (1 - smoothstep(-1.0, 1.0, X - gap(Y) - 18)), TEAL)
    # thin teal line on the lower crease of the black side
    c.paint(crease_band(c, float(gap(232)) + 24, 700, 3.0, offset=-1.5), TEAL)

    def fade(x, y):
        return float(np.interp(x, [560, 600, 760, 920], [0.6, 1.0, 1.0, 0.7]))
    keep = keep_clear(c, rects=[(554, 164, 704, 192), (560, 252, 650, 272)] + QUARTER_KEEP["rects"],
                      circles=QUARTER_KEEP["circles"])
    xs, ys = np.arange(c.w), np.arange(c.h)[:, None]
    keep &= xs[None, :] > gap(ys) + 22
    keep &= ys < crease_y(xs)[None, :] - 8
    star_field(c, 560, 990, 48, 290, 25, STAR_R, keep=keep, inner=0.19, colour=SILVER_HI, margin=1.2, opacity=fade)

    s.decal(block_digits(NUMBER, 62, BLACK, weight=0.24, shear=0.1), 400, 176)
    s.decal(wordmark("PETRONAS", 22, BLACK, tracking=0.8), 404, 236)
    s.decal(text_decal("TeamViewer", F_SANS, 10.5, fill=BLACK), 404, 140)
    s.decal(wordmark("PETRONAS", 16, WHITE, tracking=0.8), 628, 178)
    s.decal(text_decal("Mercedes-Benz", "LiberationSerif-BoldItalic.ttf", 11.5, fill=WHITE), 604, 262)
    fender_marks(s)
    quarter_marks(s, roundel=True)
    return s.render()


def build():
    return w16_b.build(paint_sides)
