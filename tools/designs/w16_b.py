"""W16 'Race Livery' - the busy one, closest to the 3D-render reference and to
the real car: silver on top, black flanks, a teal bar and one straight flow
line where they meet, a star field and a full set of partner decals.
"""
from __future__ import annotations

import numpy as np

from wrapkit import Canvas, box_decal, compose, layer, mix, ribbon, smoothstep, text_decal
from designs.w16_common import *

NAME = "W16_Race_Livery"
TITLE = "B - Race Livery"
NUMBER = "63"

LINE_X0, LINE_Y0, LINE_SLOPE = 346.0, 170.0, CREASE_SLOPE   # the flow line: straight, parallel to the door crease
LINE_X1 = 716.0


def diag_x(y):
    """Leading edge of the teal bar that slants down the front door."""
    return 296 + (y - 78) * 0.62


def line_y(x):
    """Centre of the teal flow line (parallel to the shoulder of the rear door)."""
    return LINE_Y0 + LINE_SLOPE * (np.asarray(x, dtype=np.float64) - LINE_X0)


def paint_sides() -> dict:
    s = Mirrored("side_L")
    c = s.art
    X, Y = c.grid()
    c.paint(np.ones_like(X), metallic(c))
    nose_fade_side(c)
    black = c.gradient_field([(0, CARBON), (c.h, BLACK)], axis="y")
    ly = line_y(X)

    # black "sidepod": everything behind the slanted bar and above the flow line
    pod = smoothstep(0, 3, X - (296 + (Y - 78) * 0.62) - 8) * smoothstep(0, 3, ly - Y)
    c.paint(pod, black)
    # below the flow line the silver dissolves into black across the front door
    low = smoothstep(318, 500, X + (Y - 200) * 0.25) * smoothstep(-2, 2, Y - ly)
    c.paint(low, black)

    # star field: behind the front door only, strongest above the flow line
    def radius(x, y):
        grow = min(1.0, max(0.0, (x - 506) / 24.0))
        fade = 1.0 - 0.62 * min(1.0, max(0.0, (x - 620) / 260.0))
        below = y - float(line_y(x))
        drop = 1.0 if below < 0 else max(0.0, 1.0 - below / 70.0)
        r = 11.5 * grow * fade * drop
        return r if r >= 3.5 else 0.0
    stars = c.mask_polygons(star_lattice(506, 900, 12, 250, 28, radius, inner=0.15))
    keep = 1 - c.mask_ellipse(800, 62, 38, 26)                    # room for the number roundel
    c.paint(stars * keep, STAR)

    # teal: slanted bar, then one straight line tapering evenly to the tail
    c.polygon([(diag_x(80), 80), (diag_x(80) + 30, 80), (diag_x(178) + 34, 178), (diag_x(178) - 4, 178)], TEAL)
    # (it ends with the rear door, before the wheel arch bends the panel)
    xs = np.linspace(LINE_X0, LINE_X1, 60)
    c.polygon(ribbon([(x, float(line_y(x))) for x in xs], np.interp(xs, [LINE_X0, LINE_X1], [17, 1.5])), TEAL)

    # four inlet bars in the corner of the flow line, white fading to grey;
    # they stop short of the door handle (X 458-497)
    for i in range(4):
        x0 = 358 + i * 21
        c.polygon([(x0 + 22, 104), (x0 + 36, 104), (x0 + 14, 150), (x0, 150)], mix(WHITE, "#7E858B", i / 3.4))

    s.decal(text_decal("TeamViewer", F_SANS, 10.5, fill=WHITE), 404, 93)
    s.decal(wordmark("PETRONAS", 24, WHITE, tracking=0.8, stroke=0.9, stroke_fill="#3A3F44"), 430, 207)
    s.decal(wordmark("AMG", 15, BLACK, font=F_BLACK_IT, tracking=0.4, squeeze=1.25), 218, 92)
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
    X, Y = c.grid()
    c.paint(1 - smoothstep(30, 110, X), SILVER)
    for txt, x, font in (("CROWDSTRIKE", 236, F_COND), ("SOLERA", 336, F_SANS), ("WhatsApp", 428, F_SANS)):
        r.decal(text_decal(txt, font, 11 if font == F_COND else 9.5, fill=WHITE, tracking=0.5), x, c.h / 2 + 1)
    return r.render()


def paint_mirrors() -> dict:
    return Mirrored("mirror_L", base=TEAL).render()


def paint_hood():
    c = Canvas("hood", SILVER)
    hood_base(c)
    # teal on the hood's side edges with a fine dark keyline inside it
    c.paint(hood_edge_bands(c, 7, lambda y: float(np.interp(y, [8, 60, 236], [7, 7, 1.5]))), TEAL)
    c.paint(hood_edge_bands(c, 19, 1.6, y0=10, y1=200), BLACK)
    c.stamp(text_decal(NUMBER, F_BLACK_IT, 30, fill=BLACK, tracking=-0.5), c.w / 2, 136)
    return c.result()


def paint_front():
    c = Canvas("front", SILVER)
    bumper_base(c)
    cx = c.w / 2
    c.stamp(wordmark("PETRONAS", 13, WHITE, font=F_WORD, tracking=1.6), cx, 52)
    c.stamp(text_decal("Syntium", "Montserrat-BoldItalic.otf", 18, fill=WHITE), cx, 72)
    for sgn in (-1, 1):   # low outer corners, clear of the fog lamps
        c.stamp(text_decal("INEOS", F_SANS, 10, fill=WHITE, tracking=0.8), cx + sgn * 222, 114)
    return c.result()


def paint_liftgate():
    c = Canvas("liftgate", BLACK)
    c.paint(c.mask_polygons(star_lattice(0, c.w, 6, c.h, 28, 9.0, inner=0.15)), STAR, 0.9)
    liftgate_marks(c, NUMBER)
    return c.result()


def paint_rear():
    c = Canvas("rear", BLACK)
    cx = c.w / 2
    c.paint(c.mask_rect(160, 78, c.w - 160, 82, radius=2), TEAL)
    for sgn in (-1, 1):
        c.stamp(text_decal("Snapdragon", F_SANS, 10.5, fill=WHITE), cx + sgn * 208, 72)
        c.stamp(text_decal("CROWDSTRIKE", F_COND, 12.5, fill=WHITE, tracking=0.5), cx + sgn * 208, 89)
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
