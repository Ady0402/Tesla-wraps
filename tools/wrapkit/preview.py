"""Flat preview sheet built from a *saved* wrap file.

The sheet un-maps the texture onto the orthographic canvases (carmap.py), so it
shows what the file puts on each side of the car - without lighting, glass or
wheels.  For a shaded 3D picture use tools/render_visualizer.js.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .canvas import find_font
from .compose import decompose

BG = (22, 24, 28)
TEAL = (0, 210, 190)
GREY = (150, 156, 164)


def _font(size, name="Inter-SemiBold.otf"):
    try:
        return ImageFont.truetype(find_font(name), size)
    except FileNotFoundError:
        return ImageFont.truetype(find_font("DejaVuSans-Bold.ttf"), size)


def sheet(wrap_path, title: str = "", subtitle: str = "") -> Image.Image:
    with Image.open(wrap_path) as im:
        tex = np.asarray(im.convert("RGBA"))
    dv = {k: Image.fromarray(v) for k, v in decompose(tex, scale=2).items()}
    uv = Image.new("RGBA", (1024, 1024), (40, 42, 48, 255))
    uv.alpha_composite(Image.fromarray(tex))
    uv = uv.resize((512, 512), Image.LANCZOS)

    pad = 28
    left, right = dv["side_L"], dv["side_R"]
    col2 = max(dv["front"].width, dv["rear"].width, dv["hood"].width)
    w = pad * 3 + left.width + col2
    lab = _font(17)
    rows_left = [("LEFT SIDE  (front of car on the left)", left), ("RIGHT SIDE  (front of car on the right)", right),
                 ("LEFT A-PILLAR + ROOF RAIL  (front of car on the left)", dv["rail_L"])]
    rows_right = [("HOOD  (seen from in front of the car, windscreen at the top)", dv["hood"]),
                  ("FRONT", dv["front"]), ("REAR", dv["rear"]),
                  ("LIFTGATE FROM ABOVE  (tail at the bottom)", dv["deck"])]
    h_left = 104 + sum(26 + im.height + 14 for _, im in rows_left) + 26 + uv.height + pad
    h_right = 104 + sum(26 + im.height + 14 for _, im in rows_right) + pad
    out = Image.new("RGBA", (w, max(h_left, h_right)), BG + (255,))
    d = ImageDraw.Draw(out)
    d.text((pad, 22), title, font=_font(40, "Inter-Bold.otf"), fill=(240, 240, 240))
    d.text((pad, 70), subtitle, font=_font(18), fill=GREY)
    y = 104
    for text, im in rows_left:
        d.text((pad, y), text, font=lab, fill=TEAL); y += 26
        out.alpha_composite(im, (pad, y)); y += im.height + 14
    d.text((pad, y), "THE FILE ITSELF  (1024 x 1024 texture)", font=lab, fill=TEAL); y += 26
    out.alpha_composite(uv, (pad, y))
    d.text((pad + uv.width + 20, y + 4), "LEFT MIRROR CAP", font=lab, fill=TEAL)
    out.alpha_composite(dv["mirror_L"], (pad + uv.width + 20, y + 32))
    x2 = pad * 2 + left.width
    y = 104
    for text, im in rows_right:
        d.text((x2, y), text, font=lab, fill=TEAL); y += 26
        out.alpha_composite(im, (x2 + (col2 - im.width) // 2, y)); y += im.height + 14
    return out.convert("RGB")


def save_sheet(wrap_path, out_path, title: str = "", subtitle: str = ""):
    im = sheet(wrap_path, title, subtitle)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    im.save(out_path, optimize=True)
    return im.size
