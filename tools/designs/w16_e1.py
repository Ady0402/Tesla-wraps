"""E1 'Seam Fade' - B's front and rear; silver front door with a black 63 plate,
PETRONAS and a teal band along the bottom of the door; the gradient to black
starts on the door gap and runs across the whole rear door under a star field."""
from __future__ import annotations

from wrapkit import text_decal
from designs.w16_common import *
from designs import w16_b
from designs.w16_e_side import fade_side

NAME = "W16_E1_Fade"
TITLE = "E1 - Seam Fade"


def paint_sides() -> dict:
    s, c, _ = fade_side(length=190.0, extra_keep=[])
    # teal band along the bottom edge of the front door, ending at the door gap
    gap = door_edge("front_door_L", "rear")
    x1a, x1b = float(gap(SILL_Y - 17)) - 6, float(gap(SILL_Y - 4)) - 6
    c.polygon([(302, SILL_Y - 17), (x1a, SILL_Y - 17), (x1b, SILL_Y - 4), (302, SILL_Y - 4)], TEAL)
    s.decal(block_plate("63", 50), 398, 168)
    s.decal(wordmark("PETRONAS", 25, BLACK), 414, 224)
    return s.render()


def build():
    return w16_b.build(paint_sides)
