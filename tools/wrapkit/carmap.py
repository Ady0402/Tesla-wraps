"""Where every texel of the wrap texture sits on the car.

Calibration data (wrapkit/data/), measured once on a 3D model of the legacy
Model Y that carries Tesla's own wrap UVs (tools/calibrate/ describes how):

* modely_viewmap.png      for each texel of the 1024x1024 texture: 0 if the car
                          never shows it (about 18 % of the white template area
                          is hidden margin), otherwise the id of the region it
                          belongs to
* modely_projection.json  for each (panel, canvas) region a polynomial that
                          turns texel coordinates into canvas coordinates

Canvas coordinates are pixels of an orthographic view of the car at
``pixels_per_metre`` (174 px/m, about one texel per pixel on the doors):

    side_L   X runs from the nose back, Y from the roof down (car seen from its left)
    side_R   mirror image of side_L (car seen from its right, nose on the right)
    hood     plan view seen from the front: X to the car's left, Y from windscreen to nose
    front    front elevation: X to the car's left, Y down
    rear     rear elevation: X to the car's right, Y down
    deck     the liftgate's upward faces in plan, seen from behind: X to the car's right, Y toward the tail
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

from .template import PANELS, SIZE, panel_labels

DATA = Path(__file__).resolve().parent / "data"
STRIP_IDS = {"rail_L": 6, "rail_R": 7, "mirror_L": 8, "mirror_R": 9}


@lru_cache(maxsize=1)
def _cal():
    cal = json.loads((DATA / "modely_projection.json").read_text())
    viewmap = np.asarray(Image.open(DATA / "modely_viewmap.png"))
    assert viewmap.shape == (SIZE, SIZE)
    return cal, viewmap


def canvas_sizes() -> dict:
    return {k: tuple(v) for k, v in _cal()[0]["canvases"].items()}


def pixels_per_metre() -> float:
    return float(_cal()[0]["pixels_per_metre"])


def viewmap() -> np.ndarray:
    return _cal()[1]


def on_car() -> np.ndarray:
    """Boolean (1024, 1024): texels the car really shows."""
    return _cal()[1] > 0


def _basis(px, py, reg, degree):
    u, v = (px - reg["cx"]) / reg["scale"], (py - reg["cy"]) / reg["scale"]
    return np.stack([u ** i * v ** j for i in range(degree + 1) for j in range(degree + 1 - i)], -1)


@lru_cache(maxsize=4)
def texel_coords(sub: int = 2) -> dict:
    """{canvas: (ys, xs, X, Y)} - for every texel that belongs to a projection
    canvas, its canvas coordinates at sub x sub sample points (X, Y: (n, sub*sub))."""
    cal, vm = _cal()
    lab = panel_labels()
    offs = (np.arange(sub) + 0.5) / sub
    out = {}
    for reg in cal["regions"]:
        m = (lab == PANELS[reg["panel"]]) & (vm == reg["id"])
        ys, xs = np.nonzero(m)
        cx_, cy_ = np.asarray(reg["x"]), np.asarray(reg["y"])
        X = np.empty((len(ys), sub * sub)); Y = np.empty_like(X)
        k = 0
        for oy in offs:
            for ox in offs:
                A = _basis(xs + ox, ys + oy, reg, cal["degree"])
                X[:, k], Y[:, k] = A @ cx_, A @ cy_
                k += 1
        prev = out.get(reg["view"])
        out[reg["view"]] = (ys, xs, X, Y) if prev is None else tuple(
            np.concatenate([a, b]) for a, b in zip(prev, (ys, xs, X, Y)))
    return out


@lru_cache(maxsize=8)
def panel_image(view: str) -> np.ndarray:
    """(h, w) int array: which panel a canvas pixel shows (0 = no paintable body there)."""
    w, h = canvas_sizes()[view]
    ys, xs, X, Y = texel_coords(2)[view]
    lab = panel_labels()[ys, xs]
    img = np.zeros((h, w), dtype=np.int32)
    for k in range(X.shape[1]):
        ix, iy = np.floor(X[:, k]).astype(int), np.floor(Y[:, k]).astype(int)
        ok = (ix >= 0) & (ix < w) & (iy >= 0) & (iy < h)
        img[iy[ok], ix[ok]] = lab[ok]
    # close pin-holes left by the splat without growing the outline
    filled = ndi.binary_closing(img > 0, structure=np.ones((3, 3)), iterations=1)
    holes = filled & (img == 0)
    if holes.any():
        _, idx = ndi.distance_transform_edt(img == 0, return_indices=True)
        img[holes] = img[idx[0][holes], idx[1][holes]]
    return img


def silhouette(view: str) -> np.ndarray:
    return panel_image(view) > 0


def panel_box(view: str, panel: str):
    """Bounding box (x0, y0, x1, y1) of a panel in a projection canvas."""
    ys, xs = np.nonzero(panel_image(view) == PANELS[panel])
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


# --------------------------------------------------------------------------
# Surface normals
# --------------------------------------------------------------------------
# canvas axes in world terms: (+X direction, +Y direction, toward the viewer)
_AXES = {
    "side_L": ((0, 0, -1), (0, -1, 0), (1, 0, 0)),
    "side_R": ((0, 0, 1), (0, -1, 0), (-1, 0, 0)),
    "hood": ((1, 0, 0), (0, 0, 1), (0, 1, 0)),
    "front": ((1, 0, 0), (0, -1, 0), (0, 0, 1)),
    "rear": ((-1, 0, 0), (0, -1, 0), (0, 0, -1)),
    "deck": ((-1, 0, 0), (0, 0, -1), (0, 1, 0)),
}


@lru_cache(maxsize=1)
def normals() -> np.ndarray:
    """(1024, 1024, 3) float32 unit surface normal of every texel the car shows
    (+x = the car's left, +y = up, +z = toward the nose); zero elsewhere."""
    enc = np.asarray(Image.open(DATA / "modely_normals.png").convert("RGB")).astype(np.float32)
    n = enc / 127.5 - 1.0
    on = on_car()
    n[~on] = 0.0
    # the file stores 8 bits per component; smooth within each panel so the
    # quantisation steps (and the model's facets) do not show in reflections
    lab = panel_labels()
    out = np.zeros_like(n)
    for pid in np.unique(lab[on]):
        m = (lab == pid) & on
        w = ndi.gaussian_filter(m.astype(np.float32), 2.0)
        for c in range(3):
            out[..., c] = np.where(m, ndi.gaussian_filter(n[..., c] * m, 2.0) / np.maximum(w, 1e-6), out[..., c])
    length = np.linalg.norm(out, axis=-1, keepdims=True)
    return np.where(length > 0, out / np.maximum(length, 1e-6), 0.0).astype(np.float32)


@lru_cache(maxsize=8)
def normal_image(view: str) -> np.ndarray:
    """(h, w, 3) normal of the surface under each pixel of a projection canvas,
    in canvas terms: (component along +X, component along +Y, component toward
    the viewer).  The last one is the cosine of the surface's tilt away from
    the view, i.e. how much a shape drawn here is foreshortened on the car."""
    w, h = canvas_sizes()[view]
    ys, xs, X, Y = texel_coords(2)[view]
    ax = np.asarray(_AXES[view], dtype=np.float32)
    n = normals()[ys, xs] @ ax.T
    img = np.zeros((h, w, 3), dtype=np.float32)
    hit = np.zeros((h, w), dtype=bool)
    for k in range(X.shape[1]):
        ix, iy = np.floor(X[:, k]).astype(int), np.floor(Y[:, k]).astype(int)
        ok = (ix >= 0) & (ix < w) & (iy >= 0) & (iy < h)
        img[iy[ok], ix[ok]] = n[ok]
        hit[iy[ok], ix[ok]] = True
    _, idx = ndi.distance_transform_edt(~hit, return_indices=True)
    return img[idx[0], idx[1]]


@lru_cache(maxsize=1)
def height() -> np.ndarray:
    """(1024, 1024) float32 height above the ground in metres of every texel the
    car shows (0 elsewhere).  Handy for graphics that must stay level on the
    car, such as a stripe round a mirror cap."""
    h = np.asarray(Image.open(DATA / "modely_height.png")).astype(np.float32) / 1000.0
    h[~on_car()] = 0.0
    return h
