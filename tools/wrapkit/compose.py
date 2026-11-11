"""Turn painted canvases into a wrap texture, and a wrap texture back into canvases."""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi
from scipy.spatial import cKDTree

from .carmap import STRIP_IDS, canvas_sizes, on_car, texel_coords, viewmap
from .template import PANELS, SIZE, nearest_panel, panel_labels, template_alpha, views

BLEED = 6  # px of colour bleed painted outside each island (under alpha 0)
SAMPLES = 4      # each texel averages SAMPLES x SAMPLES points spread over its footprint on the canvas
SHARPEN = 0.35   # unsharp-mask amount on the finished texture: offsets the blur the car's texture
                 # filtering adds, so lettering and edges stay crisp at 1024 x 1024


def _sharpen(rgb: np.ndarray, amount: float, sigma: float = 0.7) -> np.ndarray:
    """Unsharp mask, kept inside each island (the margin was filled with the
    island's own colours just before, so no neighbouring island bleeds in)."""
    if amount <= 0:
        return rgb
    blur = np.stack([ndi.gaussian_filter(rgb[..., c], sigma) for c in range(3)], -1)
    return np.clip(rgb + amount * (rgb - blur), 0, 255)


def compose(painted: dict, finish=None, sharpen: float = SHARPEN) -> np.ndarray:
    """painted: {canvas: array (h * r, w * r, 3)} -> uint8 RGBA texture.

    finish: optional callable (rgb float texture) -> rgb, applied to the texels
    the car shows before the hidden margin is filled (e.g. finish.metallic()).
    If it also has ``opacity(rgb)``, the wrap's alpha becomes the template
    alpha times that opacity (computed from the unshaded design colours).

    Projection canvases may be handed over at r times their nominal size (the
    drawing surface's supersampling); each texel averages SAMPLES x SAMPLES
    samples that together cover its footprint on the canvas, and the result is
    lightly sharpened (``sharpen``) to offset the car's texture filtering.  Texels the car never shows, the template's hidden
    margin and a few pixels of bleed around every island are filled with the
    nearest visible colour of the same panel.  Alpha is Tesla's template alpha.
    """
    vs = views()
    rgb = np.zeros((SIZE, SIZE, 3), dtype=np.float32)
    done = np.zeros((SIZE, SIZE), dtype=bool)
    vm = viewmap()
    for name, (ys, xs, X, Y) in texel_coords(SAMPLES).items():
        arr = np.asarray(painted[name], dtype=np.float32)
        w, h = canvas_sizes()[name]
        r = arr.shape[1] // w
        assert arr.shape[:2] == (h * r, w * r), f"{name}: canvas must be a multiple of {(h, w)}"
        # sample the full-resolution (supersampled) canvas directly: SAMPLES x SAMPLES
        # points per texel = an exact box filter over the texel's footprint
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
    skin = np.ones((SIZE, SIZE), dtype=np.float32)
    if finish is not None:
        if hasattr(finish, "opacity"):
            skin = np.where(done, finish.opacity(rgb), 1.0).astype(np.float32)
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
        skin[want] = skin[idx[0][want], idx[1][want]]
    rgb = np.where(reach[..., None], _sharpen(rgb, sharpen), rgb)
    out = np.zeros((SIZE, SIZE, 4), dtype=np.uint8)
    out[..., :3] = np.clip(np.rint(rgb), 0, 255).astype(np.uint8)
    out[..., :3][~reach] = 0
    out[..., 3] = np.clip(np.rint(alpha.astype(np.float32) * skin), 0, 255).astype(np.uint8)
    out[..., 3][alpha == 0] = 0
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


def compose_hires(painted: dict, finish=None, scale: int = 2, sharpen: float = SHARPEN) -> np.ndarray:
    """Like compose(), but at ``scale`` x 1024 pixels (e.g. 2048 x 2048): every
    1024 texel is split into scale x scale pixels, each sampled from the canvas
    over its own footprint, so the extra pixels carry real detail.  Tesla's
    README allows 512..1024 px only - this is for testing whether a car accepts
    a larger file."""
    assert scale in (2, 4)
    N = SIZE * scale
    sub = 2 * scale                                   # samples per 1024 texel along each axis
    vs = views()
    vm = viewmap()
    rgb = np.zeros((N, N, 3), dtype=np.float32)
    done = np.zeros((N, N), dtype=bool)
    for name, (ys, xs, X, Y) in texel_coords(sub).items():
        arr = np.asarray(painted[name], dtype=np.float32)
        w, h = canvas_sizes()[name]
        r = arr.shape[1] // w
        cy, cx = Y * r - 0.5, X * r - 0.5             # (n, sub*sub), row-major over (oy, ox)
        vals = np.stack([ndi.map_coordinates(arr[..., c], [cy, cx], order=1, mode="nearest")
                         for c in range(3)], -1).reshape(len(ys), sub, sub, 3)
        k = sub // scale
        for dy in range(scale):
            for dx in range(scale):
                block = vals[:, dy * k:(dy + 1) * k, dx * k:(dx + 1) * k].mean(axis=(1, 2))
                rgb[ys * scale + dy, xs * scale + dx] = block
                done[ys * scale + dy, xs * scale + dx] = True
    for name, vid in STRIP_IDS.items():
        v = vs[name]
        arr = np.asarray(painted[name], dtype=np.float32)
        r = arr.shape[1] // v.w
        f = max(1, r // scale)
        arr = arr.reshape(v.h * scale, f, v.w * scale, f, 3).mean(axis=(1, 3)) if r > scale else \
            np.repeat(np.repeat(arr, scale // r, 0), scale // r, 1)
        rot = v.to_texture(arr[..., :3])
        rh, rw = v.rotated_shape()
        m = np.kron(vm[v.oy:v.oy + rh, v.ox:v.ox + rw] == vid, np.ones((scale, scale), bool))
        sl = (slice(v.oy * scale, (v.oy + rh) * scale), slice(v.ox * scale, (v.ox + rw) * scale))
        rgb[sl][m] = rot[m]
        done[sl] |= m
    if finish is not None and hasattr(finish, "shading") and finish.strength > 0:
        shade, add = finish.shading()
        shade2 = ndi.zoom(shade, scale, order=1)
        add2 = ndi.zoom(add, scale, order=1)
        rgb = np.where(done[..., None], rgb * shade2[..., None] + add2[..., None], rgb)
        rgb = np.clip(rgb, 0, 255)
    from PIL import Image
    alpha = np.asarray(Image.fromarray(template_alpha()).resize((N, N), Image.BILINEAR))
    lab = np.kron(panel_labels(), np.ones((scale, scale), np.int32))
    near = np.kron(nearest_panel(), np.ones((scale, scale), np.int32))
    reach = ndi.distance_transform_edt(alpha == 0) <= BLEED * scale
    for pid in PANELS.values():
        src = done & (lab == pid)
        want = (near == pid) & reach & ~done
        if not want.any() or not src.any():
            continue
        _, idx = ndi.distance_transform_edt(~src, return_indices=True)
        rgb[want] = rgb[idx[0][want], idx[1][want]]
    rgb = np.where(reach[..., None], _sharpen(rgb, sharpen, sigma=0.7 * scale), rgb)
    out = np.zeros((N, N, 4), dtype=np.uint8)
    out[..., :3] = np.clip(np.rint(rgb), 0, 255).astype(np.uint8)
    out[..., :3][~reach] = 0
    out[..., 3] = alpha
    return out
