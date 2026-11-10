"""W16 'Race Livery' - the busy one, closest to the 3D-render reference and to
the real car: silver on top, black flanks, a teal flow line where they meet,
a halftone star field and a full set of partner decals.
"""
from __future__ import annotations

import numpy as np

from wrapkit import Canvas, box_decal, compose, layer, mix, ribbon, smoothstep, spline, text_decal
from designs.w16_common import *

NAME = "W16_Race_Livery"
TITLE = "B - Race Livery"
NUMBER = "63"


def diag_x(y):
    """Leading edge of the teal bar that slants down the front door."""
    return 296 + (y - 78) * 0.62


def band_y(x):
    """Centre line of the teal flow line as it runs aft."""
    return float(np.interp(x, [340, 514, 720, 884], [170, 163, 140, 112]))


def paint_sides() -> dict:
    s = Mirrored("side_L")
    c = s.art
    X, Y = c.grid()
    c.paint(np.ones_like(X), metallic(c))
    black = c.gradient_field([(0, CARBON), (c.h, BLACK)], axis="y")
    by = np.interp(X, [340, 514, 720, 884], [170, 163, 140, 112])

    # black "sidepod": everything behind the slanted bar and above the flow line
    pod = smoothstep(0, 3, X - (296 + (Y - 78) * 0.62) - 8) * smoothstep(0, 3, by - Y)
    c.paint(pod, black)
    # below the flow line the silver dissolves into black across the front door
    low = smoothstep(318, 500, X + (Y - 200) * 0.25) * smoothstep(-2, 2, Y - by)
    c.paint(low, black)

    # star field: behind the front door only, strongest above the flow line
    def radius(x, y):
        grow = min(1.0, max(0.0, (x - 500) / 30.0))
        fade = 1.0 - 0.62 * min(1.0, max(0.0, (x - 620) / 260.0))
        below = y - band_y(x)
        drop = 1.0 if below < 0 else max(0.0, 1.0 - below / 70.0)
        return 11.5 * grow * fade * drop
    stars = c.mask_polygons(star_lattice(500, 900, 12, 250, 28, radius, inner=0.15))
    keep = 1 - c.mask_ellipse(800, 66, 37, 26)                    # room for the number roundel
    c.paint(stars * keep, STAR)

    # teal: slanted bar, then the flow line tapering all the way to the tail
    c.polygon([(diag_x(80), 80), (diag_x(80) + 30, 80), (diag_x(178) + 34, 178), (diag_x(178) - 4, 178)], TEAL)
    xs = np.linspace(346, 884, 90)
    line = [(x, band_y(x)) for x in xs]
    c.polygon(ribbon(line, np.interp(xs, [346, 514, 640, 884], [17, 15, 6, 1.5])), TEAL)

    # four inlet bars in the corner of the flow line, white fading to grey
    for i in range(4):
        x0 = 372 + i * 22
        c.polygon([(x0 + 22, 104), (x0 + 36, 104), (x0 + 14, 152), (x0, 152)], mix(WHITE, "#7E858B", i / 3.4))

    s.decal(text_decal("TeamViewer", F_SANS, 10.5, fill=WHITE), 452, 91)
    s.decal(wordmark("PETRONAS", 24, WHITE, tracking=0.8, stroke=0.9, stroke_fill="#3A3F44"), 430, 206)
    s.decal(wordmark("AMG", 15, BLACK, font=F_BLACK_IT, tracking=0.4, squeeze=1.25), 228, 92)
    s.decal(text_decal("IWC", F_SERIF, 14, fill=BLACK, tracking=0.8), 150, 62)
    s.decal(text_decal("UBS", F_SERIF, 11, fill=BLACK, tracking=0.6), 232, 196)
    s.decal(text_decal("SAP", F_SANS, 10, fill=BLACK, tracking=0.4), 236, 214)
    s.decal(text_decal("Mercedes-Benz", "LiberationSerif-BoldItalic.ttf", 11.5, fill=WHITE), 596, 226)
    # race number roundel on the C-pillar part of the quarter panel
    s.decal(layer(box_decal(64, 42, BLACK, radius=21, outline=TEAL, outline_width=2.4),
                  text_decal(NUMBER, F_BLACK_IT, 25, fill=TEAL, tracking=-0.3)), 800, 66)
    s.decal(text_decal("Snapdragon", F_SANS, 9.5, fill=WHITE), 838, 142)
    s.decal(text_decal("CROWDSTRIKE", F_COND, 11, fill=WHITE, tracking=0.5), 840, 157)
    return s.render()


def paint_rails() -> dict:
    r = Mirrored("rail_L", base=BLACK)
    c = r.art
    X, Y = c.grid()
    c.paint(1 - smoothstep(60, 190, X), SILVER)
    for txt, x, font in (("CROWDSTRIKE", 250, F_COND), ("SOLERA", 345, F_SANS), ("WhatsApp", 432, F_SANS)):
        r.decal(text_decal(txt, font, 10 if font == F_COND else 8.5, fill=WHITE, tracking=0.5), x, c.h / 2 + 1)
    return r.render()


def paint_mirrors() -> dict:
    m = Mirrored("mirror_L", base=TEAL)
    return m.render()


def paint_hood():
    c = Canvas("hood", SILVER)
    X, Y = c.grid()
    c.paint(np.ones_like(X), metallic(c, SILVER_LO, SILVER, SILVER_HI))
    cx = c.w / 2
    for sgn in (-1, 1):
        outer = spline([(cx + sgn * 140, 4), (cx + sgn * 104, 86), (cx + sgn * 62, 168), (cx + sgn * 30, 240)])
        c.polygon(ribbon(outer, np.interp(np.linspace(0, 1, len(outer)), [0, 0.5, 1], [2.0, 5.5, 2.0])), TEAL)
        inner = spline([(cx + sgn * 120, 10), (cx + sgn * 88, 90), (cx + sgn * 50, 170), (cx + sgn * 22, 240)])
        c.line(inner, 1.6, BLACK)
    c.stamp(text_decal(NUMBER, F_BLACK_IT, 30, fill=BLACK, tracking=-0.5), cx, 150)
    return c.result()


def paint_front():
    c = Canvas("front", SILVER)
    X, Y = c.grid()
    c.paint(np.ones_like(X), metallic(c))
    cx = c.w / 2
    # black aero corners low on both sides
    for sgn in (-1, 1):
        c.polygon([(cx + sgn * 150, 152), (cx + sgn * 196, 84), (cx + sgn * 270, 62), (cx + sgn * 270, 152)], BLACK)
        c.stamp(text_decal("IWC", F_SERIF, 10, fill=WHITE, tracking=0.6), cx + sgn * 216, 92)
    c.stamp(wordmark("PETRONAS", 12, BLACK, font=F_WORD, tracking=1.6), cx, 50)
    c.stamp(text_decal("Syntium", "Montserrat-BoldItalic.otf", 17, fill=BLACK), cx, 70)
    return c.result()


def paint_liftgate():
    c = Canvas("liftgate", BLACK)
    c.paint(c.mask_polygons(star_lattice(0, c.w, 150, c.h, 28, 8.5)), STAR, 0.85)
    c.paint(c.mask_rect(110, 222, c.w - 110, 226, radius=2), TEAL)
    c.stamp(wordmark("PETRONAS", 16, TEAL), c.w / 2, 268)
    return c.result()


def paint_rear():
    c = Canvas("rear", BLACK)
    cx = c.w / 2
    c.paint(c.mask_rect(140, 78, c.w - 140, 82, radius=2), TEAL)
    for sgn in (-1, 1):
        c.stamp(text_decal("Snapdragon", F_SANS, 10, fill=WHITE), cx + sgn * 208, 62)
        c.stamp(text_decal("CROWDSTRIKE", F_COND, 12, fill=WHITE, tracking=0.5), cx + sgn * 208, 80)
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
