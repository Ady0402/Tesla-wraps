"""W16 'Silver Arrow' - the clean version, closest to the touchscreen reference.

Silver nose and front doors, number plate + PETRONAS on the front door, a teal
sill line, and a three-pointed-star field that takes over as the body fades to
black toward the tail.
"""
from __future__ import annotations

import numpy as np

from wrapkit import Canvas, compose, ribbon, smoothstep, spline
from designs.w16_common import *

NAME = "W16_Silver_Arrow"
TITLE = "A - Silver Arrow"
NUMBER = "63"


def paint_sides() -> dict:
    s = Mirrored("side_L")
    c = s.art
    X, Y = c.grid()
    c.paint(np.ones_like(X), metallic(c))

    # silver front doors; the fade to black happens across the rear door,
    # leaning forward at the top like the engine-cover line of the F1 car
    edge = 508 + (Y - 150) * 0.22
    t = smoothstep(-6, 120, X - edge)
    black = c.gradient_field([(0, CARBON), (c.h, BLACK)], axis="y")
    c.paint(t, black)

    # star field over the rear half, thinning slightly toward the tail
    def radius(x, y):
        grow = float(smoothstep(498, 540, x - (y - 150) * 0.22))
        fade = 1.0 - 0.45 * float(smoothstep(740, 890, x))
        return 13.0 * grow * fade
    c.paint(c.mask_polygons(star_lattice(486, 900, 16, 250, 36, radius, inner=0.15)), WHITE)

    # teal: sill line under the front door, flash at the foot of the A-pillar
    c.paint(c.mask_rect(270, SILL_Y - 11, 512, SILL_Y - 5, radius=3), TEAL)
    c.polygon([(244, 50), (272, 46), (280, 74), (262, 78)], TEAL)

    s.decal(number_plate(NUMBER, 46, radius=4, font=F_TECH), 372, 128)
    s.decal(wordmark("PETRONAS", 22, BLACK), 392, 190)
    s.decal(text_decal("IWC", F_SERIF, 27, fill=BLACK, tracking=1.2), 176, 74)
    return s.render()


def paint_rails() -> dict:
    r = Mirrored("rail_L")
    c = r.art
    X, Y = c.grid()
    c.paint(np.ones_like(X), SILVER)
    c.paint(smoothstep(250, 380, X), BLACK)
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
        pts = spline([(cx + sgn * 128, 6), (cx + sgn * 92, 90), (cx + sgn * 52, 170), (cx + sgn * 26, 236)])
        c.line(pts, 3.2, TEAL)
    # keep clear of the Tesla badge that sits near the nose
    c.stamp(number_plate(NUMBER, 36, radius=4, font=F_TECH), cx, 132)
    return c.result()


def paint_front():
    c = Canvas("front", SILVER)
    X, Y = c.grid()
    c.paint(np.ones_like(X), metallic(c))
    cx = c.w / 2
    c.stamp(wordmark("PETRONAS", 15, BLACK), cx, 58)
    return c.result()


def paint_liftgate():
    c = Canvas("liftgate", BLACK)
    c.paint(c.mask_polygons(star_lattice(0, c.w, 150, c.h, 27, 9.5)), STAR, 0.9)
    c.stamp(wordmark("PETRONAS", 17, TEAL), c.w / 2, 262)
    return c.result()


def paint_rear():
    c = Canvas("rear", BLACK)
    # teal flashes low on the bumper corners (they show in side view behind the wheel)
    for x0, x1 in ((12, 92), (c.w - 92, c.w - 12)):
        c.paint(c.mask_rect(x0, 96, x1, 101, radius=2.5), TEAL)
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
