"""Turn painted views into a wrap texture, and a wrap texture back into views."""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi

from .template import (EDGE_WRAP, PANELS, SIZE, View, nearest_panel,
                       panel_labels, template_alpha, views)

BLEED = 6  # px of colour bleed painted outside each island (under alpha 0)


def _paste_region(view: View, placement):
    """Slices mapping the rotated view onto the texture for one placement."""
    rh, rw = view.rotated_shape()
    y0, x0 = placement.oy, placement.ox
    ty0, tx0 = max(0, y0), max(0, x0)
    ty1, tx1 = min(SIZE, y0 + rh), min(SIZE, x0 + rw)
    sy0, sx0 = ty0 - y0, tx0 - x0
    tex = (slice(ty0, ty1), slice(tx0, tx1))
    src = (slice(sy0, sy0 + (ty1 - ty0)), slice(sx0, sx0 + (tx1 - tx0)))
    return tex, src


def compose(painted: dict) -> np.ndarray:
    """painted: {view_name: float/uint8 array (h, w, 3)} -> uint8 RGBA texture.

    Every panel must be covered by a view.  Alpha is copied from Tesla's
    template so the file has exactly the same footprint as the official
    examples; colour is bled a few pixels past each island so texture
    filtering never pulls in a dark fringe.
    """
    vs = views()
    rgb = np.zeros((SIZE, SIZE, 3), dtype=np.float32)
    done = np.zeros((SIZE, SIZE), dtype=bool)
    near = nearest_panel()
    alpha = template_alpha()
    dist = ndi.distance_transform_edt(alpha == 0)
    reach = dist <= BLEED
    for name, arr in painted.items():
        v = vs[name]
        arr = np.asarray(arr, dtype=np.float32)
        assert arr.shape[:2] == (v.h, v.w), f"{name}: expected {(v.h, v.w)}, got {arr.shape[:2]}"
        rot = v.to_texture(arr[..., :3])
        for p in v.placements:
            pid = PANELS[p.panel]
            tex, src = _paste_region(v, p)
            m = (near[tex] == pid) & reach[tex]
            rgb[tex][m] = rot[src][m]
            done[tex] |= m
    missing = (alpha > 0) & ~done
    assert not missing.any(), f"{int(missing.sum())} opaque template pixels were not painted"
    out = np.zeros((SIZE, SIZE, 4), dtype=np.uint8)
    out[..., :3] = np.clip(np.rint(rgb), 0, 255).astype(np.uint8)
    out[..., :3][~done] = 0
    out[..., 3] = alpha
    return out


def visible_masks(view: View) -> dict:
    """Per-panel masks in view orientation with the unseen edge wrap removed
    (only the body-side views have calibrated wrap widths)."""
    pm = view.panel_masks()
    if not view.name.startswith("side_"):
        return pm
    lead, trail = EDGE_WRAP["lead"], EDGE_WRAP["trail"]
    if view.name == "side_R":       # front is on the right in this view
        lead, trail = trail, lead
    out = {}
    for name, m in pm.items():
        vis = m.copy()
        vis[:, lead:] &= m[:, :-lead]            # trim the left edge
        vis[:, :lead] = False
        vis[:, :-trail] &= m[:, trail:]          # trim the right edge
        vis[:, -trail:] = False
        t, b = EDGE_WRAP["top"], EDGE_WRAP["bottom"]
        vis[t:, :] &= m[:-t, :]
        vis[:-b, :] &= m[b:, :]
        out[name] = vis
    return out


def decompose(texture: np.ndarray, trim: bool = True) -> dict:
    """uint8 RGBA texture -> {view_name: uint8 RGBA view}.  Inverse of compose();
    used to build previews from the *saved file* so they show what the car gets."""
    res = {}
    lab = panel_labels()
    for name, v in views().items():
        rh, rw = v.rotated_shape()
        out = np.zeros((v.h, v.w, 4), dtype=np.uint8)
        keep = visible_masks(v) if trim else v.panel_masks()
        for p in v.placements:
            pid = PANELS[p.panel]
            tex, src = _paste_region(v, p)
            rot = np.zeros((rh, rw, 4), dtype=np.uint8)
            sub = texture[tex].copy()
            sub[lab[tex] != pid] = 0
            rot[src] = sub
            back = v.from_texture(rot)
            m = keep[p.panel] & (back[..., 3] > 0)
            out[m] = back[m]
        res[name] = out
    return res
