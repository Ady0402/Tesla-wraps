"""E2 'Fade + Shoulder' - B's front and rear; silver front door with a big
PETRONAS and two teal pinstripes on the shoulder crease that stop at the door
gap, where a shorter gradient to black with stars takes over."""
from __future__ import annotations

from wrapkit import text_decal
from designs.w16_common import *
from designs import w16_b
from designs.w16_e_side import fade_side

NAME = "W16_E2_Shoulder"
TITLE = "E2 - Fade + Shoulder"


def paint_sides() -> dict:
    s, c, _ = fade_side(length=120.0, extra_keep=[])
    f = door_edge("front_door_L", "front")
    r = door_edge("front_door_L", "rear")

    def stripe(off, thick, colour):
        ya = float(shoulder_y(300)) + off
        xa0, xa1 = float(f(ya)) + 10, float(r(ya)) - 6
        y0a, y1a = float(shoulder_y(xa0)) + off, float(shoulder_y(xa1)) + off
        xb1 = float(r(y1a + thick)) - 6
        c.polygon([(xa0, y0a), (xa1, y1a), (xb1, y1a + thick), (xa0, y0a + thick)], colour)
    stripe(6, 6.5, TEAL)
    stripe(17, 2.6, TEAL_DEEP)
    s.decal(wordmark("PETRONAS", 26, BLACK, tracking=0.8), 410, 220)
    s.decal(text_decal("TeamViewer", F_SANS, 11, fill=BLACK), 410, 248)
    return s.render()


def build():
    return w16_b.build(paint_sides)
