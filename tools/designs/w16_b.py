"""W16 'Race Livery' - the owner's pick: the body of the 3D-render reference
(teal bar and flow line, black sidepod, inlet bars, big PETRONAS, star mesh,
partner decals) with the front of the number-plate reference (double teal
stripes on the hood edges, a 63 plate, a bumper that fades from silver to
near-black).
"""
from __future__ import annotations

import numpy as np

from wrapkit import Canvas, box_decal, compose, layer, mix, smoothstep, text_decal
from designs.w16_common import *

NAME = "W16_Race_Livery"
TITLE = "B - Race Livery"
NUMBER = "63"

# The flow line: its top edge is one straight line, parallel to the lower door crease.
LINE_X0, LINE_X1 = 371.0, 730.0
LINE_TOP0 = 203.0
BAR_Y0, BAR_Y1 = 122.0, 219.0      # the slanted bar runs from the window line down to the flow line


def diag_x(y):
    """Leading edge of the teal bar that slants down the front of the door."""
    return 321 + (y - 120) * 0.63


def line_top(x):
    return LINE_TOP0 + CREASE_SLOPE * (np.asarray(x, dtype=np.float64) - LINE_X0)


def line_thickness(x):
    """Full width under the inlet bars, a fine blade across the rear door."""
    return np.interp(x, [LINE_X0, 503, 553, LINE_X1], [16, 16, 5, 1.5])


def paint_sides() -> dict:
    s = Mirrored("side_L")
    c = s.art
    X, Y = c.grid()
    silver_side(c)
    black = c.gradient_field([(60, CARBON), (c.h, BLACK)], axis="y")
    top = line_top(X)

    # black "sidepod": everything behind the slanted bar and above the flow line
    # (the two black areas overlap under the teal line so no silver sliver is left between them)
    pod = smoothstep(0, 3, X - (321 + (Y - 120) * 0.63) - 8) * smoothstep(0, 3, top + 10 - Y)
    c.paint(pod, black)
    # below the flow line the silver dissolves into black across the front door
    low = smoothstep(318, 450, X + (Y - 240) * 0.25) * smoothstep(-2, 2, Y - top - 3)
    c.paint(low, black)

    # star mesh behind the front door: nearly touching above the flow line,
    # thinning out below it and toward the tail
    def radius(x, y):
        grow = min(1.0, max(0.0, (x - 540) / 22.0))
        fade = 1.0 - 0.55 * min(1.0, max(0.0, (x - 670) / 250.0))
        below = y - float(line_top(x)) - 4
        drop = 1.0 if below < 0 else max(0.0, 1.0 - below / 64.0)
        r = 10.5 * grow * fade * drop
        return r if r >= 3.5 else 0.0
    stars = c.mask_polygons(star_lattice(540, 990, 48, 290, 25, radius, inner=0.19))
    keep = 1 - c.mask_ellipse(806, 112, 39, 27)                    # room for the number roundel
    keep = keep * (1 - c.mask_rect(820, 148, 912, 184, radius=6))  # and for the partner names below it
    keep = keep * (1 - c.mask_rect(846, 200, 930, 246, radius=6))  # and on the bumper corner
    c.paint(stars * keep, SILVER_HI)

    # teal: flash at the foot of the A-pillar, the slanted bar, and the flow line
    # (its front end is cut on the same slant as the bar, so the corner of the L is one clean edge)
    c.polygon(A_PILLAR_FLASH, TEAL)
    c.polygon([(diag_x(BAR_Y0), BAR_Y0), (diag_x(BAR_Y0) + 30, BAR_Y0),
               (diag_x(BAR_Y1) + 34, BAR_Y1), (diag_x(BAR_Y1) - 4, BAR_Y1)], TEAL)
    xs = np.linspace(LINE_X0, LINE_X1, 80)
    upper = [(x, float(line_top(x))) for x in xs]
    lower = [(x, float(line_top(x) + line_thickness(x))) for x in xs if x >= diag_x(BAR_Y1) - 4]
    c.polygon(upper + lower[::-1], TEAL)

    # four inlet bars in the corner of the flow line, white fading to grey;
    # they sit below and ahead of the door handle (X 473-513, Y 139)
    for i in range(4):
        x0 = 380 + i * 21
        c.polygon([(x0 + 22, 147), (x0 + 36, 147), (x0 + 14, 191), (x0, 191)], mix(WHITE, "#7E858B", i / 3.4))

    s.decal(text_decal("TeamViewer", F_SANS, 10.5, fill=WHITE), 426, 135)
    s.decal(wordmark("PETRONAS", 23.5, WHITE, tracking=0.8, stroke=1.0, stroke_fill="#2E3237"), 443, 248)
    s.decal(wordmark("AMG", 15, BLACK, font=F_BLACK_IT, tracking=0.4, squeeze=1.25), 243, 150)
    s.decal(text_decal("IWC", F_SERIF, 14, fill=BLACK, tracking=0.8), 176, 143)
    s.decal(text_decal("Mercedes-Benz", "LiberationSerif-BoldItalic.ttf", 11.5, fill=WHITE), 604, 262)
    # race number roundel on the rear quarter panel
    s.decal(layer(box_decal(64, 40, BLACK, radius=20, outline=TEAL, outline_width=2.4),
                  text_decal(NUMBER, F_BLACK_IT, 25, fill=TEAL, tracking=-0.3)), 806, 112)
    s.decal(text_decal("Snapdragon", F_SANS, 10, fill=WHITE), 866, 159)
    s.decal(text_decal("CROWDSTRIKE", F_COND, 11.5, fill=WHITE, tracking=0.5), 866, 175)
    s.decal(wordmark("PETRONAS", 8.5, TEAL, font=F_WORD, tracking=0.8), 888, 214)
    s.decal(text_decal("PRIMAX", "Montserrat-BoldItalic.otf", 12, fill=WHITE, tracking=0.5), 888, 229)
    return s.render()


def paint_rails() -> dict:
    r = black_rails()
    for txt, side_x, font in (("CROWDSTRIKE", 500, F_COND), ("SOLERA", 596, F_SANS), ("WhatsApp", 686, F_SANS)):
        x = float(rail_x(side_x))
        r.decal(text_decal(txt, font, 10.5 if font == F_COND else 9, fill=WHITE, tracking=0.5), x, float(rail_mid(x)) + 0.5)
    return r.render()


def paint_mirrors() -> dict:
    return Mirrored("mirror_L", base=TEAL).render()


def paint_hood():
    c = Canvas("hood", SILVER)
    race_hood(c, NUMBER)
    return c.out()


def paint_front():
    c = Canvas("front", SILVER)
    race_bumper(c)
    return c.out()


def paint_rear():
    c = Canvas("rear", BLACK)
    c.paint(c.mask_polygons(star_lattice(0, c.w, 80, 186, 25, 8.0, inner=0.19)), SILVER_HI, 0.85)
    rear_marks(c)
    return c.out()


def build():
    painted = {}
    painted.update(paint_sides())
    painted.update(paint_rails())
    painted.update(paint_mirrors())
    painted["hood"] = paint_hood()
    painted["front"] = paint_front()
    painted["rear"] = paint_rear()
    painted["deck"] = paint_deck(NUMBER, stars=(25, 7.0, SILVER_HI, 0.85))
    return compose(painted)
