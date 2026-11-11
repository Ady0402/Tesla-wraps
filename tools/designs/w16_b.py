"""W16 'Race Livery' - the owner's pick: the body of the 3D-render reference
(teal bar and flow line, black sidepod, inlet bars, big PETRONAS, star mesh,
partner decals) with the front of the number-plate reference (double teal
stripes on the hood edges, a 63 plate, a bumper that fades from silver to
near-black).
"""
from __future__ import annotations

import numpy as np

from wrapkit import Canvas, block_digits, box_decal, compose, layer, mix, smoothstep, text_decal
from designs.w16_common import *

NAME = "W16_Race_Livery"
TITLE = "B - Race Livery"
NUMBER = "63"
STAR_R_B = 9.0             # one star size everywhere on this design

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
    """One straight taper: full width at the foot of the bar, a point at the tail."""
    x0 = diag_x(BAR_Y1) + 34
    return np.interp(x, [LINE_X0, x0, LINE_X1], [16, 16, 1.5])


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

    # star mesh behind the front door: every star the same size; the field is
    # brightest above the flow line and dims below it and toward the tail
    def fade(x, y):
        tail = 1.0 - 0.35 * min(1.0, max(0.0, (x - 670) / 250.0))
        below = y - float(line_top(x)) - 4
        drop = 1.0 if below < 0 else max(0.25, 1.0 - below / 60.0)
        return tail * drop
    keep = keep_clear(c, rects=[(820, 148, 912, 184), (846, 200, 930, 246)],
                      circles=[(806, 112, 40)])                   # roundel, partner names
    xs, ys = np.arange(c.w), np.arange(c.h)[:, None]
    top_, thick = line_top(xs)[None, :], line_thickness(xs)[None, :]
    keep &= ~((ys >= top_ - 2) & (ys <= top_ + thick + 2))                   # clear of the flow line
    star_field(c, 548, 990, 48, 290, 25, STAR_R_B, keep=keep, inner=0.19, colour=SILVER_HI, margin=1.2,
               opacity=fade)

    # teal: the slanted bar and the flow line
    # (its front end is cut on the same slant as the bar, so the corner of the L is one clean edge)
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
    # on the flat of the fender, clear of the side indicator (X 238-282, Y 152-163);
    # no car-brand lettering (owner's request), partners only
    s.decal(text_decal("IWC", F_SERIF, 16, fill=BLACK, tracking=1.0), 186, 144)
    # race number roundel on the rear quarter panel
    s.decal(layer(box_decal(64, 40, BLACK, radius=20, outline=TEAL, outline_width=2.4),
                  block_digits(NUMBER, 22, TEAL, weight=0.23)), 806, 112, surface=True)
    s.decal(text_decal("Snapdragon", F_SANS, 10, fill=WHITE), 866, 159)
    s.decal(text_decal("CROWDSTRIKE", F_COND, 11.5, fill=WHITE, tracking=0.5), 866, 175)
    s.decal(wordmark("PETRONAS", 8.5, TEAL, font=F_WORD, tracking=0.8), 888, 214)
    s.decal(text_decal("PRIMAX", "Montserrat-BoldItalic.otf", 12, fill=WHITE, tracking=0.5), 888, 229)
    return s.render()


def paint_rails() -> dict:
    # plain black A-pillars and roof rails: no lettering up there (owner's request)
    return black_rails().render()


def paint_mirrors() -> dict:
    return striped_mirrors()


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
    rear_marks(c)
    keep = keep_clear(c, **REAR_KEEP)
    star_field(c, 0, c.w, 30, 240, 25, STAR_R_B, keep=keep, inner=0.19, colour=SILVER_HI, opacity=0.7, margin=1.5)
    return c.out()


def build(sides=None):
    """sides: optional function returning the two side canvases, so the
    variants (w16_b2..b4) can reuse this design's front, rear, rails and mirrors."""
    painted = {}
    painted.update((sides or paint_sides)())
    painted.update(paint_rails())
    painted.update(paint_mirrors())
    painted["hood"] = paint_hood()
    painted["front"] = paint_front()
    painted["rear"] = paint_rear()
    painted["deck"] = paint_deck(25, STAR_R_B, colour=SILVER_HI, opacity=0.7, inner=0.19)
    return compose(painted, finish=FINISH)
