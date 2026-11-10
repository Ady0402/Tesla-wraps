"""Geometry of the legacy Model Y wrap template (modely/template.png).

The 1024x1024 template holds 16 paintable UV islands ("panels").  This module
segments them, and defines *views*: small canvases in a natural viewing
orientation (side elevation, plan view of the hood, rear view ...) together
with the exact 90-degree rotation + integer translation that places each view
onto its panel(s) in the texture.  Designing in views instead of raw UV space
keeps graphics continuous across door seams and text upright on the car.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

REPO = Path(__file__).resolve().parents[2]
TEMPLATE_PATH = REPO / "modely" / "template.png"
SIZE = 1024

# Panel ids are assigned by sorting the islands by (top, left) of their bounding
# box; the order is stable for modely/template.png and asserted in _segment().
PANELS = {
    "front_bumper": 1,
    "fender_R": 2,
    "fender_L": 3,
    "rail_L": 4,
    "rail_R": 5,
    "hood": 6,
    "front_door_L": 7,
    "front_door_R": 8,
    "mirror_R": 9,
    "mirror_L": 10,
    "rear_door_L": 11,
    "rear_door_R": 12,
    "liftgate": 13,
    "quarter_L": 14,
    "quarter_R": 15,
    "rear_bumper": 16,
}
_EXPECTED_CENTROIDS = {  # (cx, cy) sanity check for the id assignment above
    1: (512, 75), 2: (847, 179), 3: (174, 178), 4: (334, 383), 5: (689, 383),
    6: (512, 275), 7: (116, 409), 8: (909, 409), 9: (765, 427), 10: (262, 427),
    11: (127, 641), 12: (899, 641), 13: (512, 823), 14: (179, 860),
    15: (849, 860), 16: (511, 959),
}


@lru_cache(maxsize=1)
def _segment():
    """Return (alpha uint8, labels int32, near int32).

    labels: panel id for every pixel that is opaque in the template (outline
    strokes are assigned to the nearest panel), 0 elsewhere.
    near:   nearest panel id for *every* pixel (used for colour bleed).
    """
    rgba = np.asarray(Image.open(TEMPLATE_PATH).convert("RGBA")).astype(np.int32)
    alpha = rgba[..., 3].astype(np.uint8)
    lum = rgba[..., :3].mean(-1)
    interior, n = ndi.label((alpha > 127) & (lum > 160))
    # drop specks, renumber by (top, left) of bounding box
    boxes = ndi.find_objects(interior)
    keep = []
    for i, sl in enumerate(boxes, 1):
        if (interior[sl] == i).sum() >= 40:
            keep.append((sl[0].start, sl[1].start, i))
    keep.sort()
    remap = np.zeros(n + 1, dtype=np.int32)
    for new, (_, _, old) in enumerate(keep, 1):
        remap[old] = new
    interior = remap[interior]
    assert len(keep) == 16, f"expected 16 panels, found {len(keep)}"
    _, idx = ndi.distance_transform_edt(interior == 0, return_indices=True)
    near = interior[idx[0], idx[1]]
    labels = np.where(alpha > 0, near, 0).astype(np.int32)
    for pid, (cx, cy) in _EXPECTED_CENTROIDS.items():
        my, mx = ndi.center_of_mass(interior == pid)
        assert abs(mx - cx) < 6 and abs(my - cy) < 6, f"panel {pid} moved: {(mx, my)}"
    return alpha, labels, near.astype(np.int32)


def template_alpha() -> np.ndarray:
    return _segment()[0]


def panel_labels() -> np.ndarray:
    return _segment()[1]


def nearest_panel() -> np.ndarray:
    return _segment()[2]


def panel_mask(name_or_id) -> np.ndarray:
    pid = PANELS[name_or_id] if isinstance(name_or_id, str) else int(name_or_id)
    return panel_labels() == pid


def panel_bbox(name_or_id):
    m = panel_mask(name_or_id)
    ys, xs = np.nonzero(m)
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


# --------------------------------------------------------------------------
# Views
# --------------------------------------------------------------------------
# Calibration of the body-side islands against Tesla's example wraps.
SEAM_OVERLAP = 12                      # px of view-space overlap at each door gap
V_SHIFT = {"fender": -5, "front_door": 0, "rear_door": 0, "quarter": 4}
# Width of the unseen edge wrap inside each side island, in view pixels.
EDGE_WRAP = {"lead": 5, "trail": 7, "top": 6, "bottom": 5}


@dataclass(frozen=True)
class Placement:
    """How one panel is cut out of a view.

    The view (h, w, ...) is turned into texture orientation with
    ``np.rot90(view, k)`` (k counter-clockwise quarter turns) and then pasted so
    that rotated pixel (0, 0) lands on texture pixel (ox, oy).
    """
    panel: str
    ox: int
    oy: int


@dataclass(frozen=True)
class View:
    name: str
    w: int          # view width in texture pixels
    h: int          # view height in texture pixels
    k: int          # np.rot90 quarter turns (CCW) from view to texture orientation
    placements: tuple
    describe: str

    def rotated_shape(self):
        return (self.h, self.w) if self.k % 2 == 0 else (self.w, self.h)

    # -- view <-> texture for one placement ---------------------------------
    def to_texture(self, view_arr: np.ndarray) -> np.ndarray:
        return np.rot90(view_arr, self.k)

    def from_texture(self, tex_arr: np.ndarray) -> np.ndarray:
        return np.rot90(tex_arr, -self.k)

    def mask(self) -> np.ndarray:
        """Boolean (h, w) mask of the panel area in view orientation."""
        out = np.zeros(self.rotated_shape(), dtype=bool)
        lab = panel_labels()
        rh, rw = out.shape
        for p in self.placements:
            pid = PANELS[p.panel]
            y0, y1, x0, x1 = p.oy, p.oy + rh, p.ox, p.ox + rw
            sy0, sx0 = max(0, -y0), max(0, -x0)
            y0c, x0c = max(0, y0), max(0, x0)
            y1c, x1c = min(SIZE, y1), min(SIZE, x1)
            sub = lab[y0c:y1c, x0c:x1c] == pid
            out[sy0:sy0 + sub.shape[0], sx0:sx0 + sub.shape[1]] |= sub
        return self.from_texture(out)

    def panel_masks(self) -> dict:
        """Per-panel boolean masks in view orientation."""
        res = {}
        lab = panel_labels()
        rh, rw = self.rotated_shape()
        for p in self.placements:
            out = np.zeros((rh, rw), dtype=bool)
            pid = PANELS[p.panel]
            y0, x0 = p.oy, p.ox
            sy0, sx0 = max(0, -y0), max(0, -x0)
            y0c, x0c = max(0, y0), max(0, x0)
            y1c, x1c = min(SIZE, y0 + rh), min(SIZE, x0 + rw)
            sub = lab[y0c:y1c, x0c:x1c] == pid
            out[sy0:sy0 + sub.shape[0], sx0:sx0 + sub.shape[1]] = sub
            res[p.panel] = self.from_texture(out)
        return res


def _best_shift(ref: np.ndarray, mov: np.ndarray, search: int = 8):
    """Integer (dx, dy) that maximises the overlap of two boolean masks."""
    best, arg = -1, (0, 0)
    for dy in range(-search, search + 1):
        for dx in range(-search, search + 1):
            s = np.roll(np.roll(mov, dy, 0), dx, 1)
            v = (ref & s).sum()
            if v > best:
                best, arg = v, (dx, dy)
    return arg


@lru_cache(maxsize=1)
def views() -> dict:
    """Build all views.  Units are texture pixels."""
    lab = panel_labels()

    def bbox(name):
        return panel_bbox(name)

    def col_extent(name, fn):
        m = panel_mask(name)
        out = {}
        for x in np.nonzero(m.any(0))[0]:
            ys = np.nonzero(m[:, x])[0]
            out[int(x)] = int(fn(ys))
        return out

    def seam_gap(a, b):
        bot, top = col_extent(a, max), col_extent(b, min)
        g = [top[x] - bot[x] for x in sorted(set(bot) & set(top))]
        g = [v for v in g if v < 30]
        return int(np.median(g))

    out = {}

    # ---- body sides -------------------------------------------------------
    # The four side islands of each flank are stacked front-to-rear down the
    # texture with 6-10 px of padding between them.  Two calibrations, both
    # measured on Tesla's own example wraps (see docs in tools/README.md):
    #   * the outer few pixels of every island are edge wrap / bleed that is
    #     not seen on the car (about 5 px at an island's leading edge and 7 px
    #     at its trailing edge), so for artwork to run straight across a door
    #     gap neighbouring islands must OVERLAP in view space by SEAM_OVERLAP;
    #   * neighbouring islands are a few pixels out of register vertically
    #     (V_SHIFT, positive = island content sits lower in the view).
    L = ["fender_L", "front_door_L", "rear_door_L", "quarter_L"]
    R = ["fender_R", "front_door_R", "rear_door_R", "quarter_R"]
    top_pad, bot_pad = 8, 6
    x0L = min(bbox(p)[0] for p in L) - bot_pad
    x1L = max(bbox(p)[2] for p in L) + top_pad
    H = x1L - x0L
    y_top = bbox("fender_L")[1] - 2
    offs, acc = {}, 0
    for a, b in zip(L[:-1], L[1:]):
        offs[a] = acc
        acc += seam_gap(a, b) - 1 + SEAM_OVERLAP
    offs[L[-1]] = acc
    W = bbox("quarter_L")[3] + 2 - acc - y_top
    # view (front to the left, roof up) -> texture: rotate 90 deg clockwise.
    # texture x = ox + (H-1-Y): raising ox moves the island DOWN in the view.
    plL = tuple(Placement(p, x0L + V_SHIFT[p[:-2]], y_top + offs[p]) for p in L)
    side_L = View("side_L", W, H, -1, plL,
                  "left flank seen from outside: front of car on the LEFT, roof up")
    out["side_L"] = side_L

    # right flank: mirror image.  view (front to the right) -> texture: 90 deg CCW.
    # Each right island is registered to the mirrored left island so both
    # flanks share one design coordinate system.
    maskL = side_L.panel_masks()
    plR = []
    gapsR = [seam_gap(a, b) - 1 + SEAM_OVERLAP for a, b in zip(R[:-1], R[1:])]
    offR = dict(zip(R, np.concatenate([[0], np.cumsum(gapsR)]).astype(int)))
    x1R = max(bbox(p)[2] for p in R) + bot_pad
    for pl, pr in zip(L, R):
        # texture x = ox + Y for k=+1: lowering ox moves the island DOWN.
        guess = Placement(pr, x1R - H - V_SHIFT[pr[:-2]], y_top + int(offR[pr]))
        v = View("tmp", W, H, 1, (guess,), "")
        mR = v.panel_masks()[pr]
        dx, dy = _best_shift(maskL[pl][:, ::-1], mR, 8)
        # moving the mask by (dx, dy) in the view == moving the placement by
        # (-dy, +dx) in the texture for k=+1.
        plR.append(Placement(pr, guess.ox - dy, guess.oy + dx))
    side_R = View("side_R", W, H, 1, tuple(plR),
                  "right flank seen from outside: front of car on the RIGHT, roof up")
    out["side_R"] = side_R

    # ---- single-island views ---------------------------------------------
    def single(view_name, panel, k, describe, pad=3):
        bx0, by0, bx1, by1 = bbox(panel)
        bx0, by0, bx1, by1 = bx0 - pad, by0 - pad, bx1 + pad, by1 + pad
        rw, rh = bx1 - bx0, by1 - by0
        w, h = (rw, rh) if k % 2 == 0 else (rh, rw)
        out[view_name] = View(view_name, w, h, k, (Placement(panel, bx0, by0),), describe)

    single("hood", "hood", 2,
           "hood seen by someone standing in FRONT of the car looking back at it: "
           "nose edge at the bottom, windscreen edge at the top, car's left on the viewer's right")
    single("front", "front_bumper", 2,
           "front bumper seen from the front, upright: car's left on the viewer's right")
    single("liftgate", "liftgate", 0,
           "liftgate seen from behind, upright: car's left on the viewer's left")
    single("rear", "rear_bumper", 0,
           "rear bumper seen from behind, upright: car's left on the viewer's left")
    single("rail_L", "rail_L", -1,
           "left roof rail strip, front of car on the LEFT")
    single("rail_R", "rail_R", 1,
           "right roof rail strip, front of car on the RIGHT")
    single("mirror_L", "mirror_L", -1, "left mirror cap, front of car on the LEFT")
    single("mirror_R", "mirror_R", 1, "right mirror cap, front of car on the RIGHT")
    return out


def view(name: str) -> View:
    return views()[name]


if __name__ == "__main__":
    for v in views().values():
        print(f"{v.name:9s} {v.w:4d}x{v.h:<4d} k={v.k:+d}  {v.describe}")
        for p in v.placements:
            print(f"            {p.panel:13s} ox={p.ox:4d} oy={p.oy:4d}")
