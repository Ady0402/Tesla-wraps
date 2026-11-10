"""Three-quarter mock-up: drape a saved wrap over Tesla's own render of the
legacy Model Y (modely/vehicle_image.png).

Hand-placed landmark pairs tie each upright view (side, hood, front bumper) to
the render; a thin-plate spline fills in between and the render's own shading
is multiplied back on top.  It is an illustration to help compare designs -
the car's real UV mapping will differ by a few centimetres here and there.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage as ndi
from scipy.interpolate import RBFInterpolator

from .compose import decompose
from .template import REPO, views

RENDER = REPO / "modely" / "vehicle_image.png"

# (view x, view y) -> (render x, render y)
LANDMARKS = {
    "side_L": [
        # front fender
        ((8, 20), (207, 636)), ((40, 30), (236, 615)), ((100, 44), (284, 591)),
        ((180, 50), (350, 557)), ((258, 48), (420, 524)), ((112, 86), (340, 599)),
        ((62, 108), (306, 648)), ((120, 131), (372, 641)), ((165, 124), (404, 620)),
        ((222, 146), (440, 630)), ((245, 172), (455, 648)), ((262, 222), (470, 680)),
        ((272, 62), (452, 514)), ((200, 90), (392, 578)), ((240, 110), (428, 585)),
        # front door
        ((268, 80), (466, 521)), ((508, 74), (636, 446)), ((508, 240), (630, 602)),
        ((270, 238), (474, 690)), ((390, 77), (548, 487)), ((390, 240), (552, 646)),
        ((390, 160), (552, 566)), ((300, 160), (490, 600)), ((480, 160), (616, 530)),
        # rear door
        ((716, 56), (742, 384)), ((612, 66), (694, 417)), ((650, 241), (722, 563)),
        ((580, 241), (680, 581)), ((712, 146), (764, 478)), ((676, 164), (745, 500)),
        ((600, 160), (692, 497)), ((690, 100), (748, 430)),
        # rear quarter
        ((740, 143), (790, 449)), ((780, 152), (814, 446)), ((820, 168), (832, 462)),
        ((878, 120), (843, 418)), ((860, 56), (822, 368)), ((800, 20), (786, 346)),
        ((745, 50), (750, 380)), ((800, 90), (806, 400)), ((850, 150), (840, 446)),
    ],
    "hood": [
        ((305, 3), (418, 522)), ((5, 3), (232, 430)), ((155, 30), (322, 500)),
        ((80, 20), (268, 478)), ((235, 20), (378, 516)),
        ((295, 100), (330, 566)), ((17, 100), (168, 462)),
        ((262, 200), (238, 613)), ((50, 200), (98, 516)),
        ((232, 236), (200, 632)), ((80, 236), (84, 566)), ((155, 250), (124, 618)),
        ((155, 130), (232, 538)), ((155, 200), (158, 584)), ((220, 130), (286, 566)),
        ((90, 130), (182, 506)),
    ],
    "front": [
        ((264, 22), (133, 623)), ((356, 12), (200, 637)), ((395, 32), (256, 663)),
        ((440, 18), (306, 650)), ((522, 3), (372, 641)), ((492, 60), (350, 670)),
        ((492, 125), (320, 750)), ((400, 136), (268, 760)), ((264, 148), (160, 727)),
        ((330, 80), (196, 690)), ((420, 80), (286, 712)), ((264, 80), (146, 676)),
        ((172, 12), (86, 576)), ((130, 32), (78, 594)), ((35, 60), (68, 612)),
        ((38, 125), (76, 652)), ((120, 136), (100, 690)), ((180, 80), (96, 640)),
    ],
}


# outline of the left door mirror in the render
MIRROR_POLY = [(499, 513), (497, 490), (505, 474), (520, 470), (538, 479), (554, 498),
               (541, 506), (520, 509)]


def _poly_mask(size, pts):
    from PIL import ImageDraw
    im = Image.new("1", size, 0)
    ImageDraw.Draw(im).polygon(pts, fill=1)
    return im


@lru_cache(maxsize=1)
def _maps():
    """For each view: (ys, xs, view_x, view_y) of render pixels it covers."""
    with Image.open(RENDER) as im:
        base = np.asarray(im.convert("RGB"), dtype=np.float32)
    lum = base.mean(-1)
    # anything brighter than the studio floor; the panel masks do the real clipping
    body = ndi.binary_opening(lum > 34, iterations=1)
    H, W = lum.shape
    out = {}
    from .compose import visible_masks
    for name, pairs in LANDMARKS.items():
        v = views()[name]
        src = np.array([p[1] for p in pairs], dtype=np.float64)   # render
        dst = np.array([p[0] for p in pairs], dtype=np.float64)   # view
        # heavy smoothing: hand-placed landmarks are only good to a few pixels, and
        # an exact fit would make straight stripes wobble
        rbf = RBFInterpolator(src, dst, kernel="thin_plate_spline", smoothing=400.0)
        x0, y0 = np.floor(src.min(0)).astype(int) - 12
        x1, y1 = np.ceil(src.max(0)).astype(int) + 12
        x0, y0, x1, y1 = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
        gy, gx = np.mgrid[y0:y1, x0:x1]
        pts = np.stack([gx.ravel(), gy.ravel()], 1).astype(np.float64)
        uv = rbf(pts)
        vx, vy = uv[:, 0], uv[:, 1]
        m = np.any(list(visible_masks(v).values()), axis=0) if name.startswith("side") else v.mask()
        m = ndi.binary_dilation(m, iterations=2)
        ix, iy = np.rint(vx).astype(int), np.rint(vy).astype(int)
        ok = (ix >= 0) & (ix < v.w) & (iy >= 0) & (iy < v.h)
        inside = np.zeros(len(pts), dtype=bool)
        inside[ok] = m[iy[ok], ix[ok]]
        inside &= body[gy.ravel(), gx.ravel()]
        out[name] = (gy.ravel()[inside], gx.ravel()[inside], vx[inside], vy[inside])
    return base, lum, body, out


def mockup(wrap_path, scale: float = 1.0) -> Image.Image:
    base, lum, body, maps = _maps()
    with Image.open(wrap_path) as im:
        tex = np.asarray(im.convert("RGBA"))
    dv = decompose(tex, trim=False)
    out = base.copy()
    shade_ref = 178.0
    painted = np.zeros(lum.shape, dtype=bool)
    for name in ("front", "hood", "side_L"):
        ys, xs, vx, vy = maps[name]
        src = dv[name].astype(np.float32)
        a = src[..., 3] > 0
        # fill holes so bilinear sampling never grabs empty texels
        _, idx = ndi.distance_transform_edt(~a, return_indices=True)
        rgbv = src[..., :3][idx[0], idx[1]]
        cols = np.stack([ndi.map_coordinates(rgbv[..., c], [vy, vx], order=1, mode="nearest")
                         for c in range(3)], 1)
        # soften the render's deep side shadow so the lower doors stay readable
        shade = np.clip((lum[ys, xs] / shade_ref) ** 0.6, 0.3, 1.35)[:, None]
        # keep a little of the render's highlight so dark paint still reads as glossy
        lit = cols * shade + np.clip(lum[ys, xs] - 205, 0, 50)[:, None] * 0.6
        out[ys, xs] = np.clip(lit, 0, 255)
        painted[ys, xs] = True
    H, W = lum.shape
    yy, xx = np.mgrid[0:H, 0:W]
    shade_all = np.clip((lum / shade_ref) ** 0.6, 0.3, 1.35)[..., None]

    def mean_rgb(view, x0=None, x1=None):
        a = view[:, x0:x1]
        m = a[..., 3] > 200
        return a[m][:, :3].astype(np.float32).mean(0) if m.any() else np.array([128.0] * 3)

    # door mirror: its own little island in the texture
    mirror = np.asarray(_poly_mask((W, H), MIRROR_POLY)) & (lum > 60)
    out[mirror] = np.clip(mean_rgb(dv["mirror_L"]) * shade_all[mirror], 0, 255)
    painted |= mirror
    # A-pillar + roof rail.  The near rail follows a known arc in the render;
    # bright roof-edge pixels away from it belong to the far rail.
    strip = dv["rail_L"]
    cols = np.stack([mean_rgb(strip, x, x + 8) for x in range(0, strip.shape[1] - 8, 8)])
    above = (lum > 95) & ~painted & (xx > 225) & (yy < 524 - (xx - 462) * 0.47)
    arc_y = np.interp(xx, [455, 470, 530, 630, 730, 810, 845], [520, 510, 400, 340, 320, 350, 378])
    near = above & (xx >= 455) & (np.abs(yy - arc_y) < 20)
    far = above & ~near
    for region, x0, span in ((near, 440.0, 400.0), (far, 240.0, 560.0)):
        idx = np.clip(((xx[region] - x0) / span * len(cols)).astype(int), 0, len(cols) - 1)
        out[region] = np.clip(cols[idx] * shade_all[region], 0, 255)
        painted |= region
    # corner of the rear bumper behind the wheel
    tail = (lum > 70) & ~painted & (xx > 826) & (yy > 384) & (yy < 500)
    out[tail] = np.clip(mean_rgb(dv["rear"], 6, 70) * shade_all[tail], 0, 255)
    painted |= tail
    # whatever body is left (panel gaps, far side): tint with the nearest paint
    rest = body & ~painted & (lum > 95)
    if rest.any():
        d, idx2 = ndi.distance_transform_edt(~painted, return_indices=True)
        near = out[idx2[0], idx2[1]]
        take = rest & (d < 14)
        out[take] = near[take]
    img = Image.fromarray(out.astype(np.uint8))
    if scale != 1.0:
        img = img.resize((int(img.width * scale), int(img.height * scale)), Image.LANCZOS)
    return img


def save_mockup(wrap_path, out_path, crop=(20, 250, 880, 800)):
    im = mockup(wrap_path).crop(crop)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    im.save(out_path, optimize=True)
    return im.size
