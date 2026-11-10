"""Flat preview sheets built from a *saved* wrap file.

The preview un-maps the texture back into upright views (see template.py), so
it shows what the file really contains - but it is a flattened approximation,
not Tesla's 3D render.  Always confirm the final look in the car / app.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .canvas import find_font
from .compose import decompose
from .template import views

BG = (22, 24, 28)
GLASS = (10, 12, 15)
TYRE = (14, 14, 16)
RIM = (58, 60, 66)

# Approximate wheel positions in side-view pixels (front of car at X = 0).
WHEELS = ((167, 208, 71), (757, 216, 71))


def _load(path):
    with Image.open(path) as im:
        return np.asarray(im.convert("RGBA"))


def _font(size):
    return ImageFont.truetype(find_font("Inter-SemiBold.otf") if _has("Inter-SemiBold.otf")
                              else find_font("DejaVuSans-Bold.ttf"), size)


def _has(name):
    try:
        find_font(name)
        return True
    except FileNotFoundError:
        return False


def side_elevation(dv: dict, side: str, scale: float = 2.0) -> Image.Image:
    """Body side with glasshouse, wheels and bumper ends sketched in."""
    v = views()[f"side_{side}"]
    W, H = v.w, v.h
    top_extra, bottom_extra, lr = 70, 55, 40
    cw, ch = W + 2 * lr, H + top_extra + bottom_extra
    S = 4
    art = Image.new("RGBA", (cw * S, ch * S), BG + (255,))
    d = ImageDraw.Draw(art)

    def P(x, y):  # view px (front-left convention) -> canvas px
        if side == "R":
            x = W - x
        return ((x + lr) * S, (y + top_extra) * S)

    def poly(pts, fill):
        d.polygon([P(x, y) for x, y in pts], fill=fill)

    front_view = dv["front"]
    rear_view = dv["rear"]

    def avg(view, x0, x1):
        a = view[:, x0:x1]
        m = a[..., 3] > 200
        return tuple(int(c) for c in a[m][:, :3].mean(0)) if m.any() else (128, 128, 128)

    # bumper ends: the car's left end is on the viewer's right in the front
    # view and on the viewer's left in the rear view.
    fw, rw = front_view.shape[1], rear_view.shape[1]
    f_col = avg(front_view, fw - 70, fw - 10) if side == "L" else avg(front_view, 10, 70)
    r_col = avg(rear_view, 10, 70) if side == "L" else avg(rear_view, rw - 70, rw - 10)
    # glasshouse + roof
    poly([(262, 76), (318, 30), (420, -22), (540, -40), (660, -30), (760, 2), (812, 26), (700, 58), (500, 76)], GLASS)
    # headlight in the fender notch, tail-lamp behind the quarter panel
    poly([(14, 34), (112, 86), (62, 108), (4, 74)], (30, 33, 38))
    poly([(866, 58), (890, 100), (884, 122), (868, 110)], (70, 12, 16))
    # bumper ends (flat colour sampled from the texture)
    poly([(-26, 96), (0, 72), (62, 108), (80, 122), (74, 160), (70, 236), (-10, 232), (-28, 176)], f_col)
    poly([(842, 168), (884, 122), (902, 150), (906, 214), (888, 246), (846, 250)], r_col)
    # sill shadow
    poly([(230, 243), (700, 246), (700, 256), (230, 254)], (8, 8, 9))
    for cx, cy, r in WHEELS:
        x, y = P(cx, cy)
        for rad, col in ((r, TYRE), (r * 0.72, RIM), (r * 0.62, (36, 37, 41)), (r * 0.16, RIM)):
            d.ellipse([x - rad * S, y - rad * S, x + rad * S, y + rad * S], fill=col)
        for k in range(5):
            import math
            a = math.radians(k * 72 - 90)
            d.line([x, y, x + math.cos(a) * r * 0.62 * S, y + math.sin(a) * r * 0.62 * S], fill=RIM, width=int(5 * S))
    art = art.resize((cw * 2, ch * 2), Image.LANCZOS)   # S=4 -> 2x
    body = Image.fromarray(dv[f"side_{side}"]).resize((W * 2, H * 2), Image.LANCZOS)
    art.alpha_composite(body, (lr * 2, top_extra * 2))
    if scale != 2.0:
        art = art.resize((int(cw * scale), int(ch * scale)), Image.LANCZOS)
    return art


def _on_bg(arr, scale):
    """Scale a view; it stays transparent outside the panel so neighbouring
    views (liftgate over rear bumper) can interlock like they do on the car."""
    im = Image.fromarray(arr)
    return im.resize((int(im.width * scale), int(im.height * scale)), Image.LANCZOS)


def sheet(wrap_path, title: str = "", subtitle: str = "") -> Image.Image:
    """One preview sheet: both flanks, hood + front bumper, liftgate + rear
    bumper, roof rails and mirror caps, and the raw texture."""
    tex = _load(wrap_path)
    dv = decompose(tex)
    left = side_elevation(dv, "L")
    right = side_elevation(dv, "R")
    hood = _on_bg(dv["hood"], 1.6)
    front = _on_bg(dv["front"], 1.6)
    lift = _on_bg(dv["liftgate"], 1.45)
    rear = _on_bg(dv["rear"], 1.45)
    rail = _on_bg(dv["rail_L"], 1.6)
    mirror = _on_bg(dv["mirror_L"], 1.6)
    uv = Image.new("RGBA", (1024, 1024), (40, 42, 48, 255))
    uv.alpha_composite(Image.fromarray(tex))
    uv = uv.resize((520, 520), Image.LANCZOS)

    pad = 28
    col_w = left.width
    lab = _font(17)
    teal = (0, 210, 190)
    grey = (150, 156, 164)
    w = pad * 3 + col_w + max(front.width, rear.width)
    left_h = 104 + 2 * 26 + left.height + 12 + right.height + pad
    right_h = (104 + 26 + hood.height - 26 + front.height + 16 + 26 + lift.height - 96 + rear.height
               + 22 + 26 + rail.height + 26 + uv.height + 30 + pad)
    out = Image.new("RGBA", (w, max(left_h, right_h)), BG + (255,))
    d = ImageDraw.Draw(out)
    d.text((pad, 22), title, font=_font(40), fill=(240, 240, 240))
    d.text((pad, 70), subtitle, font=_font(18), fill=grey)

    y = 104
    d.text((pad, y), "LEFT SIDE  (front of car on the left)", font=lab, fill=teal); y += 26
    out.alpha_composite(left, (pad, y)); y += left.height + 12
    d.text((pad, y), "RIGHT SIDE  (front of car on the right)", font=lab, fill=teal); y += 26
    out.alpha_composite(right, (pad, y))

    x2 = pad * 2 + col_w
    y = 104
    d.text((x2, y), "FRONT  (seen from in front of the car)", font=lab, fill=teal); y += 26
    out.alpha_composite(hood, (x2 + (front.width - hood.width) // 2, y)); y += hood.height - 26
    out.alpha_composite(front, (x2, y)); y += front.height + 16
    d.text((x2, y), "REAR  (seen from behind the car)", font=lab, fill=teal); y += 26
    out.alpha_composite(lift, (x2 + (rear.width - lift.width) // 2, y)); y += lift.height - 96
    out.alpha_composite(rear, (x2, y)); y += rear.height + 22
    d.text((x2, y), "LEFT ROOF RAIL  (front of car on the left)", font=lab, fill=teal); y += 26
    out.alpha_composite(rail, (x2, y)); y += rail.height + 26
    out.alpha_composite(uv, (x2, y))
    xt = x2 + uv.width + 18
    d.text((xt, y + 4), "the file itself", font=lab, fill=grey)
    d.text((xt, y + 28), "1024 x 1024 texture", font=lab, fill=grey)
    d.text((xt, y + 96), "LEFT MIRROR CAP", font=lab, fill=teal)
    out.alpha_composite(mirror, (xt, y + 124))
    return out.convert("RGB")


def save_sheet(wrap_path, out_path, title: str = "", subtitle: str = ""):
    im = sheet(wrap_path, title, subtitle)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    im.save(out_path, optimize=True)
    return im.size
