"""Side elements shared by the B variants (w16_b2, w16_b3, w16_b4): the
partner decals and the race-number roundel that B carries on its flanks."""
from __future__ import annotations

from wrapkit import block_digits, box_decal, layer, text_decal
from designs.w16_common import *

NUMBER = "63"


def fender_marks(s: Mirrored, colour=BLACK):
    """AMG and IWC on the flat of the front fender, clear of the side indicator."""
    s.decal(wordmark("AMG", 15, colour, font=F_BLACK_IT, tracking=0.4, squeeze=1.25), 212, 138)
    s.decal(text_decal("IWC", F_SERIF, 15, fill=colour, tracking=1.0), 158, 146)


def quarter_marks(s: Mirrored, roundel=True):
    """Race-number roundel and partner names on the rear quarter panel."""
    if roundel:
        s.decal(layer(box_decal(64, 40, BLACK, radius=20, outline=TEAL, outline_width=2.4),
                      block_digits(NUMBER, 22, TEAL, weight=0.23)), 806, 112, surface=True)
    s.decal(text_decal("Snapdragon", F_SANS, 10, fill=WHITE), 866, 159)
    s.decal(text_decal("CROWDSTRIKE", F_COND, 11.5, fill=WHITE, tracking=0.5), 866, 175)
    s.decal(wordmark("PETRONAS", 8.5, TEAL, font=F_WORD, tracking=0.8), 888, 214)
    s.decal(text_decal("PRIMAX", "Montserrat-BoldItalic.otf", 12, fill=WHITE, tracking=0.5), 888, 229)


QUARTER_KEEP = dict(rects=[(820, 148, 912, 184), (846, 200, 930, 246)], circles=[(806, 112, 40)])
