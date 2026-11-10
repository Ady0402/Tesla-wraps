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
LINE_X0, LINE_X1 = 346.0, 716.0
LINE_TOP0 = 162.0


def diag_x(y):
    """Leading edge of the teal bar that slants down the front of the door."""
    return 296 + (y - 78) * 0.62


def line_top(x):
    return LINE_TOP0 + CREASE_SLOPE * (np.asarray(x, dtype=np.float64) - LINE_X0)


def line_thickness(x):
    """Full width under the inlet bars, a fine blade across the rear door."""
    return np.interp(x, [LINE_X0, 478, 528, LINE_X1], [16, 16, 5, 1.5])


def paint_sides() -> dict:
    s = Mirrored("side_L")
    c = s.art
    X, Y = c.grid()
    c.paint(np.ones_like(X), metallic(c))
    nose_fade_side(c)
    black = c.gradient_field([(0, CARBON), (c.h, BLACK)], axis="y")
    top = line_top(X)

    # black "sidepod": everything behind the slanted bar and above the flow line
    # (the two black areas overlap under the teal line so no silver sliver is left between them)
    pod = smoothstep(0, 3, X - (296 + (Y - 78) * 0.62) - 8) * smoothstep(0, 3, top + 10 - Y)
    c.paint(pod, black)
    # below the flow line the silver dissolves into black across the front door
    low = smoothstep(292, 424, X + (Y - 200) * 0.25) * smoothstep(-2, 2, Y - top - 3)
    c.paint(low, black)

    # star mesh behind the front door: nearly touching above the flow line,
    # thinning out below it and toward the tail
    def radius(x, y):
        grow = min(1.0, max(0.0, (x - 506) / 22.0))
        fade = 1.0 - 0.55 * min(1.0, max(0.0, (x - 640) / 250.0))
        below = y - float(line_top(x)) - 4
        drop = 1.0 if below < 0 else max(0.0, 1.0 - below / 64.0)
        r = 10.5 * grow * fade * drop
        return r if r >= 3.5 else 0.0
    stars = c.mask_polygons(star_lattice(506, 900, 10, 250, 25, radius, inner=0.19))
    keep = 1 - c.mask_ellipse(800, 62, 38, 26)                    # room for the number roundel
    keep = keep * (1 - c.mask_rect(786, 132, 884, 166, radius=6))  # and for the partner names below it
    c.paint(stars * keep, SILVER_HI)

    # teal: flash at the foot of the A-pillar, the slanted bar, and the flow line
    c.polygon([(244, 50), (272, 46), (280, 74), (262, 78)], TEAL)
    c.polygon([(diag_x(80), 80), (diag_x(80) + 30, 80), (diag_x(178) + 34, 178), (diag_x(178) - 4, 178)], TEAL)
    # (its front end is cut on the same slant as the bar, so the corner of the L is one clean edge)
    xs = np.linspace(LINE_X0, LINE_X1, 80)
    upper = [(x, float(line_top(x))) for x in xs]
    lower = [(x, float(line_top(x) + line_thickness(x))) for x in xs if x >= diag_x(178) - 4]
    c.polygon(upper + lower[::-1], TEAL)

    # four inlet bars in the corner of the flow line, white fading to grey;
    # they stop short of the door handle (X 458-497)
    for i in range(4):
        x0 = 358 + i * 21
        c.polygon([(x0 + 22, 104), (x0 + 36, 104), (x0 + 14, 150), (x0, 150)], mix(WHITE, "#7E858B", i / 3.4))

    s.decal(text_decal("TeamViewer", F_SANS, 10.5, fill=WHITE), 404, 93)
    s.decal(wordmark("PETRONAS", 23.5, WHITE, tracking=0.8, stroke=1.0, stroke_fill="#2E3237"), 422, 208)
    s.decal(wordmark("AMG", 15, BLACK, font=F_BLACK_IT, tracking=0.4, squeeze=1.25), 214, 96)
    s.decal(text_decal("IWC", F_SERIF, 14, fill=BLACK, tracking=0.8), 150, 62)
    s.decal(text_decal("Mercedes-Benz", "LiberationSerif-BoldItalic.ttf", 11.5, fill=WHITE), 596, 226)
    # race number roundel on the C-pillar part of the quarter panel
    s.decal(layer(box_decal(64, 40, BLACK, radius=20, outline=TEAL, outline_width=2.4),
                  text_decal(NUMBER, F_BLACK_IT, 25, fill=TEAL, tracking=-0.3)), 800, 62)
    s.decal(text_decal("Snapdragon", F_SANS, 10, fill=WHITE), 838, 141)
    s.decal(text_decal("CROWDSTRIKE", F_COND, 11.5, fill=WHITE, tracking=0.5), 840, 157)
    return s.render()


def paint_rails() -> dict:
    r = Mirrored("rail_L", base=BLACK)
    c = r.art
    c.paint(c.mask_rect(-2, -2, 11, c.h + 2), TEAL)      # foot of the A-pillar
    for txt, x, font in (("CROWDSTRIKE", 236, F_COND), ("SOLERA", 336, F_SANS), ("WhatsApp", 428, F_SANS)):
        r.decal(text_decal(txt, font, 11 if font == F_COND else 9.5, fill=WHITE, tracking=0.5), x, c.h / 2 + 1)
    return r.render()


def paint_mirrors() -> dict:
    return Mirrored("mirror_L", base=TEAL).render()


def paint_hood():
    c = Canvas("hood", SILVER)
    race_hood(c, NUMBER)
    return c.result()


def paint_front():
    c = Canvas("front", SILVER)
    race_bumper(c)
    return c.result()


def paint_liftgate():
    c = Canvas("liftgate", BLACK)
    c.paint(c.mask_polygons(star_lattice(0, c.w, 6, c.h, 25, 8.0, inner=0.19)), SILVER_HI, 0.85)
    liftgate_marks(c, NUMBER)
    return c.result()


def paint_rear():
    c = Canvas("rear", BLACK)
    cx = c.w / 2
    c.paint(c.mask_rect(160, 78, c.w - 160, 82, radius=2), TEAL)
    for sgn in (-1, 1):
        c.stamp(wordmark("PETRONAS", 9.5, TEAL, font=F_WORD, tracking=1.0), cx + sgn * 208, 72)
        c.stamp(text_decal("PRIMAX", "Montserrat-BoldItalic.otf", 13, fill=WHITE, tracking=0.6), cx + sgn * 208, 88)
    return c.result()


def build():
    painted = {}
    painted.update(paint_sides())
    painted.update(paint_rails())
    painted.update(paint_mirrors())
    painted["hood"] = paint_hood()
    painted["front"] = paint_front()
    painted["liftgate"] = paint_liftgate()
    painted["rear"] = paint_rear()
    return compose(painted)
