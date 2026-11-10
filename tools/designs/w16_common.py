"""Shared building blocks for the Mercedes-AMG F1 W16 tribute wraps."""
from __future__ import annotations

import numpy as np

from wrapkit import (Canvas, box_decal, layer, mix, rgb, smoothstep, star3, text_decal)

# ---- palette --------------------------------------------------------------
SILVER = "#C6CACE"
SILVER_HI = "#DADDE0"
SILVER_LO = "#AAB0B6"
BLACK = "#0B0C0E"
CARBON = "#17191C"
TEAL = "#00D2BE"        # the turquoise the team is known for on screen
TEAL_DEEP = "#00A19B"   # PETRONAS corporate green
WHITE = "#F4F5F6"
STAR = "#D3D7DB"
RED = "#E1002A"

# ---- fonts ----------------------------------------------------------------
F_WORD = "Montserrat-ExtraBold.otf"       # PETRONAS-style wide bold caps
F_WORD_IT = "Montserrat-ExtraBoldItalic.otf"
F_BLACK_IT = "Montserrat-BlackItalic.otf"
F_NUM = "Montserrat-Black.otf"
F_COND = "BebasNeue-Bold.otf"
F_SERIF = "LiberationSerif-Bold.ttf"
F_SANS = "Inter-Bold.otf"
F_TECH = "Play-Bold.ttf"

# ---- side-view landmarks (texture px; front of car at X = 0) ---------------
SIDE_W, SIDE_H = 891, 255
SILL_Y = 236          # lowest visible line of the doors
BELT_Y = 80           # top of the front door (beltline) near the A-pillar
FENDER = (7, 277)
FRONT_DOOR = (261, 514)
REAR_DOOR = (495, 722)
QUARTER = (704, 881)


def star_lattice(x0, x1, y0, y1, pitch, radius, rot=0.0, inner=0.17, stagger=True):
    """List of star polygons on a triangular lattice.  radius: number or
    callable (x, y) -> radius in px (<= 0 skips the star)."""
    polys = []
    row = 0
    y = y0
    while y <= y1:
        x = x0 + (pitch / 2 if (stagger and row % 2) else 0.0)
        while x <= x1:
            r = radius(x, y) if callable(radius) else radius
            if r > 0.7:
                polys.append(star3(x, y, r, rot, inner))
            x += pitch
        y += pitch * 0.866
        row += 1
    return polys


def number_plate(number="63", size=44.0, plate=BLACK, digits=WHITE, radius=7.0, shear=0.0, font=F_NUM):
    """Race number on a rounded plate (as on the touchscreen reference)."""
    txt = text_decal(number, font, size * 0.62, fill=digits, tracking=-0.5, shear=shear)
    w = txt.width / 4 + size * 0.42
    return layer(box_decal(w, size, plate, radius=radius, shear=shear), txt)


def wordmark(text, size, fill, font=F_WORD_IT, tracking=0.6, **kw):
    return text_decal(text, font, size, fill=fill, tracking=tracking, **kw)


class Mirrored:
    """A pair of mirror-image views (both flanks, both roof rails, both mirror
    caps).  Paint geometry once on ``art`` (drawn for the LEFT side, front of
    the car at X = 0); add text and logos with ``decal`` so they read correctly
    on both sides instead of being mirror-written on the right."""

    def __init__(self, left_view: str, base=SILVER):
        self.left_name = left_view
        self.right_name = left_view[:-1] + "R"
        self.art = Canvas(left_view, base)
        self._decals = []

    def decal(self, img, x, y, rot=0.0, sides="LR", opacity=1.0):
        self._decals.append((img, x, y, rot, sides, opacity))

    def render(self) -> dict:
        left = self.art
        right = self.art.mirrored()
        for img, x, y, rot, sides, op in self._decals:
            if "L" in sides:
                left.stamp(img, x, y, rot, op)
            if "R" in sides:
                right.stamp(img, right.w - x, y, -rot, op)
        return {self.left_name: left.result(), self.right_name: right.result()}


def metallic(c: Canvas, top=SILVER_HI, mid=SILVER, bottom=SILVER_LO):
    """Soft top-to-bottom sheen so flat silver does not look like grey primer."""
    return c.gradient_field([(0, top), (c.h * 0.45, mid), (c.h, bottom)], axis="y")
