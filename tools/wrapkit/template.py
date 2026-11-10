"""Geometry of the legacy Model Y wrap template (modely/template.png).

The 1024x1024 template holds 16 paintable UV islands ("panels").  Wraps are not
painted on the unfolded template but on *canvases*:

* projection canvases - true orthographic views of the car (``side_L``,
  ``side_R``, ``hood``, ``front``, ``rear``, ``deck``).  Which canvas pixel every texel
  of the texture shows was measured on a 3D model of the car (see carmap.py),
  so what you draw on a canvas is what you see from that side of the car, and
  graphics run straight across door gaps.
* strip canvases - the roof rails and mirror caps, which are simply their own
  island turned upright (``rail_L``, ``rail_R``, ``mirror_L``, ``mirror_R``).
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
# Canvases
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class StripView:
    """One island turned upright: ``np.rot90(canvas, k)`` (k counter-clockwise
    quarter turns) pasted with its top-left corner on texture pixel (ox, oy)."""
    name: str
    panel: str
    w: int
    h: int
    k: int
    ox: int
    oy: int
    describe: str
    projected = False

    def rotated_shape(self):
        return (self.h, self.w) if self.k % 2 == 0 else (self.w, self.h)

    def to_texture(self, arr: np.ndarray) -> np.ndarray:
        return np.rot90(arr, self.k)

    def from_texture(self, arr: np.ndarray) -> np.ndarray:
        return np.rot90(arr, -self.k)

    def _cut(self, tex_bool: np.ndarray) -> np.ndarray:
        rh, rw = self.rotated_shape()
        return self.from_texture(tex_bool[self.oy:self.oy + rh, self.ox:self.ox + rw])

    def mask(self) -> np.ndarray:
        """(h, w) mask of the part of the island the car really shows."""
        from .carmap import on_car
        return self._cut(on_car() & panel_mask(self.panel))

    def island(self) -> np.ndarray:
        """(h, w) mask of the whole island, hidden margin included."""
        return self._cut(panel_mask(self.panel))


@dataclass(frozen=True)
class ProjView:
    """An orthographic view of the car; see carmap.py for the mapping."""
    name: str
    w: int
    h: int
    describe: str
    projected = True

    def mask(self) -> np.ndarray:
        """(h, w) silhouette of the paintable body in this view."""
        from .carmap import silhouette
        return silhouette(self.name)

    def panels(self) -> np.ndarray:
        """(h, w) panel id shown at each canvas pixel (0 = none)."""
        from .carmap import panel_image
        return panel_image(self.name)


_DESCRIBE = {
    "side_L": "left side elevation: front of the car on the LEFT, roof up",
    "side_R": "right side elevation: front of the car on the RIGHT, roof up",
    "hood": "hood in plan view, seen by someone standing in FRONT of the car: windscreen at the top, "
            "nose at the bottom, car's left on the viewer's right",
    "front": "front elevation (front bumper): car's left on the viewer's right",
    "rear": "rear elevation (upright faces of the liftgate, rear bumper): car's left on the viewer's left",
    "deck": "liftgate seen from above by someone standing BEHIND the car (frame of the rear glass, top of "
            "the spoiler): tail at the bottom, car's left on the viewer's left",
}


@lru_cache(maxsize=1)
def views() -> dict:
    from .carmap import canvas_sizes
    out = {name: ProjView(name, w, h, _DESCRIBE[name]) for name, (w, h) in canvas_sizes().items()}

    def strip(name, panel, k, describe, pad=3):
        x0, y0, x1, y1 = panel_bbox(panel)
        x0, y0, x1, y1 = x0 - pad, y0 - pad, x1 + pad, y1 + pad
        rw, rh = x1 - x0, y1 - y0
        w, h = (rw, rh) if k % 2 == 0 else (rh, rw)
        out[name] = StripView(name, panel, w, h, k, x0, y0, describe)

    strip("rail_L", "rail_L", -1, "left A-pillar and roof rail as a strip: front of the car on the LEFT, roof side up")
    strip("rail_R", "rail_R", 1, "right A-pillar and roof rail as a strip: front of the car on the RIGHT, roof side up")
    strip("mirror_L", "mirror_L", -1, "left mirror cap: front of the car on the LEFT")
    strip("mirror_R", "mirror_R", 1, "right mirror cap: front of the car on the RIGHT")
    return out


def view(name: str):
    return views()[name]


if __name__ == "__main__":
    for v in views().values():
        print(f"{v.name:9s} {v.w:4d}x{v.h:<4d}  {v.describe}")
