"""Turn painted canvases into a wrap texture, and a wrap texture back into canvases."""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi
from scipy.spatial import cKDTree

from .carmap import STRIP_IDS, canvas_sizes, on_car, texel_coords, viewmap
from .template import PANELS, SIZE, nearest_panel, panel_labels, template_alpha, views

BLEED = 6  # px of colour bleed painted outside each island (under alpha 0)


def compose(painted: dict, finish=None) -> np.ndarray:
    """painted: {canvas: array (h * r, w * r, 3)} -> uint8 RGBA texture.

    finish: optional callable (rgb float texture) -> rgb, applied to the texels
    the car shows before the hidden margin is filled (e.g. finish.metallic()).

    Projection canvases may be handed over at r times their nominal size (the
    drawing surface's supersampling); each texel averages 2 x 2 samples that
    together cover its footprint on the canvas.  Texels the car never shows, the template's hidden
    margin and a few pixels of bleed around every island are filled with the
    nearest visible colour of the same panel.  Alpha is Tesla's template alpha.
    """
    vs = views()
    rgb = np.zeros((SIZE, SIZE, 3), dtype=np.float32)
    done = np.zeros((SIZE, SIZE), dtype=bool)
    vm = viewmap()
    for name, (ys, xs, X, Y) in texel_coords(2).items():
        arr = np.asarray(painted[name], dtype=np.float32)
        w, h = canvas_sizes()[name]
        r = arr.shape[1] // w
        assert arr.shape[:2] == (h * r, w * r), f"{name}: canvas must be a multiple of {(h, w)}"
        if r >= 4 and r % 2 == 0:
            # box-filter to half a canvas pixel per sample, so the 2 x 2 samples
            # of a texel cover its whole footprint (clean edges, no stair-steps)
            f = r // 2
            arr = arr.reshape(h * 2, f, w * 2, f, 3).mean(axis=(1, 3))
            r = 2
        cy, cx = Y * r - 0.5, X * r - 0.5
        acc = np.zeros((len(ys), 3), dtype=np.float32)
        for c in range(3):
            acc[:, c] = ndi.map_coordinates(arr[..., c], [cy, cx], order=1, mode="nearest").mean(axis=1)
        rgb[ys, xs] = acc
        done[ys, xs] = True
    for name, vid in STRIP_IDS.items():
        v = vs[name]
        arr = np.asarray(painted[name], dtype=np.float32)
        if arr.shape[:2] != (v.h, v.w):      # supersampled: box-filter down
            r = arr.shape[1] // v.w
            arr = arr.reshape(v.h, r, v.w, r, 3).mean(axis=(1, 3))
        rot = v.to_texture(arr[..., :3])
        rh, rw = v.rotated_shape()
        m = vm[v.oy:v.oy + rh, v.ox:v.ox + rw] == vid
        rgb[v.oy:v.oy + rh, v.ox:v.ox + rw][m] = rot[m]
        done[v.oy:v.oy + rh, v.ox:v.ox + rw] |= m
    assert (done == on_car()).all()
    if finish is not None:
        rgb = np.asarray(finish(rgb), dtype=np.float32)
    # hidden margin + bleed: nearest visible colour of the same panel
    alpha = template_alpha()
    near = nearest_panel()
    reach = ndi.distance_transform_edt(alpha == 0) <= BLEED
    for pid in PANELS.values():
        src = done & (panel_labels() == pid)
        want = (near == pid) & reach & ~done
        if not want.any():
            continue
        _, idx = ndi.distance_transform_edt(~src, return_indices=True)
        rgb[want] = rgb[idx[0][want], idx[1][want]]
    out = np.zeros((SIZE, SIZE, 4), dtype=np.uint8)
    out[..., :3] = np.clip(np.rint(rgb), 0, 255).astype(np.uint8)
    out[..., :3][~reach] = 0
    out[..., 3] = alpha
    assert not ((alpha > 0) & ~reach).any()
    return out


def decompose(texture: np.ndarray, scale: int = 2) -> dict:
    """uint8 RGBA texture -> {canvas: uint8 RGBA image at `scale` x the canvas size}.
    Shows what a saved file puts on each side of the car (flat, no shading)."""
    res = {}
    for name, (ys, xs, X, Y) in texel_coords(2).items():
        w, h = canvas_sizes()[name]
        pts = np.stack([X.mean(1), Y.mean(1)], 1)
        tree = cKDTree(pts)
        gy, gx = np.mgrid[0:h * scale, 0:w * scale]
        q = np.stack([(gx.ravel() + 0.5) / scale, (gy.ravel() + 0.5) / scale], 1)
        d, i = tree.query(q, k=1, distance_upper_bound=1.5)
        ok = np.isfinite(d)
        img = np.zeros((h * scale * w * scale, 4), dtype=np.uint8)
        img[ok, :3] = texture[ys[i[ok]], xs[i[ok]], :3]
        img[ok, 3] = 255
        res[name] = img.reshape(h * scale, w * scale, 4)
    vs = views()
    for name, vid in STRIP_IDS.items():
        v = vs[name]
        rh, rw = v.rotated_shape()
        sub = texture[v.oy:v.oy + rh, v.ox:v.ox + rw].copy()
        sub[viewmap()[v.oy:v.oy + rh, v.ox:v.ox + rw] != vid] = 0
        img = np.ascontiguousarray(v.from_texture(sub))
        res[name] = np.repeat(np.repeat(img, scale, 0), scale, 1)
    return res
