"""Supersampled drawing surface for one canvas (see template.py), in canvas-pixel units."""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .template import view as get_view

SS = 4  # every canvas is drawn at SS x the texture resolution, then box-filtered

FONT_DIRS = [Path("/usr/share/fonts"), Path("/usr/local/share/fonts")]
_FONT_CACHE: dict = {}


def rgb(c):
    """'#rrggbb' | (r, g, b) -> float32 array of 3 values in 0..255."""
    if isinstance(c, str):
        c = c.lstrip("#")
        c = tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))
    return np.asarray(c, dtype=np.float32)


def mix(a, b, t):
    return rgb(a) * (1 - t) + rgb(b) * t


def smoothstep(e0, e1, x):
    t = np.clip((np.asarray(x, dtype=np.float32) - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def find_font(name: str) -> str:
    """Resolve a font file name such as 'Montserrat-ExtraBoldItalic.otf'."""
    if name in _FONT_CACHE:
        return _FONT_CACHE[name]
    if Path(name).is_file():
        _FONT_CACHE[name] = name
        return name
    for d in FONT_DIRS:
        hits = list(d.rglob(name)) if d.exists() else []
        if hits:
            _FONT_CACHE[name] = str(hits[0])
            return _FONT_CACHE[name]
    raise FileNotFoundError(f"font {name!r} not installed (see tools/setup.sh)")


def spline(points, per_segment: int = 24):
    """Catmull-Rom spline through points -> dense list of (x, y)."""
    p = np.asarray(points, dtype=np.float64)
    if len(p) < 3:
        return [tuple(q) for q in p]
    ext = np.vstack([2 * p[0] - p[1], p, 2 * p[-1] - p[-2]])
    out = []
    for i in range(1, len(ext) - 2):
        p0, p1, p2, p3 = ext[i - 1], ext[i], ext[i + 1], ext[i + 2]
        for t in np.linspace(0, 1, per_segment, endpoint=False):
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t
                              + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(p[-1])
    return [tuple(q) for q in out]


def ribbon(center, widths):
    """Closed polygon for a stroke of varying width along a centre line.
    widths: one number, or one number per centre point."""
    c = np.asarray(center, dtype=np.float64)
    w = np.broadcast_to(np.asarray(widths, dtype=np.float64), (len(c),))
    d = np.gradient(c, axis=0)
    n = np.stack([-d[:, 1], d[:, 0]], axis=1)
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-9)
    left = c + n * (w[:, None] / 2)
    right = c - n * (w[:, None] / 2)
    return [tuple(q) for q in left] + [tuple(q) for q in right[::-1]]


def star3(cx, cy, r, rot_deg: float = 0.0, inner: float = 0.17):
    """Three-pointed star (one arm pointing up when rot_deg == 0)."""
    pts = []
    for i in range(6):
        ang = math.radians(-90 + rot_deg + i * 60)
        rad = r if i % 2 == 0 else r * inner
        pts.append((cx + rad * math.cos(ang), cy + rad * math.sin(ang)))
    return pts


class Canvas:
    """Float RGB image for one view.  All coordinates are texture pixels with
    the origin at the top-left corner of the view."""

    def __init__(self, view_name: str, base="#000000"):
        self.view = get_view(view_name)
        self.w, self.h = self.view.w, self.view.h
        self.W, self.H = self.w * SS, self.h * SS
        self.px = np.empty((self.H, self.W, 3), dtype=np.float32)
        self.px[:] = rgb(base)
        self.lit = None          # (H, W) 1 = the finish shades this pixel; None = everywhere

    # ---- coordinate grids -------------------------------------------------
    def grid(self):
        """(X, Y) arrays of texture-pixel coordinates for every sub-pixel."""
        xs = (np.arange(self.W, dtype=np.float32) + 0.5) / SS
        ys = (np.arange(self.H, dtype=np.float32) + 0.5) / SS
        return np.meshgrid(xs, ys)

    def panel_mask(self):
        """Float mask (sub-pixel resolution) of the paintable body in this canvas."""
        m = self.view.mask()
        return np.repeat(np.repeat(m, SS, 0), SS, 1).astype(np.float32)

    # ---- masks ------------------------------------------------------------
    def _blank(self):
        return Image.new("L", (self.W, self.H), 0)

    def mask_polygon(self, pts):
        im = self._blank()
        ImageDraw.Draw(im).polygon([(x * SS, y * SS) for x, y in pts], fill=255)
        return np.asarray(im, dtype=np.float32) / 255.0

    def mask_polygons(self, polys):
        im = self._blank()
        d = ImageDraw.Draw(im)
        for pts in polys:
            d.polygon([(x * SS, y * SS) for x, y in pts], fill=255)
        return np.asarray(im, dtype=np.float32) / 255.0

    def mask_line(self, pts, width):
        im = self._blank()
        d = ImageDraw.Draw(im)
        p = [(x * SS, y * SS) for x, y in pts]
        d.line(p, fill=255, width=max(1, int(round(width * SS))), joint="curve")
        r = width * SS / 2
        for x, y in (p[0], p[-1]):
            d.ellipse([x - r, y - r, x + r, y + r], fill=255)
        return np.asarray(im, dtype=np.float32) / 255.0

    def mask_rect(self, x0, y0, x1, y1, radius: float = 0.0):
        im = self._blank()
        ImageDraw.Draw(im).rounded_rectangle(
            [x0 * SS, y0 * SS, x1 * SS, y1 * SS], radius=radius * SS, fill=255)
        return np.asarray(im, dtype=np.float32) / 255.0

    def mask_ellipse(self, cx, cy, rx, ry):
        im = self._blank()
        ImageDraw.Draw(im).ellipse(
            [(cx - rx) * SS, (cy - ry) * SS, (cx + rx) * SS, (cy + ry) * SS], fill=255)
        return np.asarray(im, dtype=np.float32) / 255.0

    # ---- painting ---------------------------------------------------------
    def fill(self, color):
        self.px[:] = rgb(color)
        self.lit = None

    def paint(self, mask, color, opacity: float = 1.0, lit: bool = True):
        """Blend a colour (or an (H, W, 3) colour field) through a 0..1 mask.
        lit=False marks the paint as exempt from the finish's light and shade
        (compose keeps its colour exactly), e.g. stars that must look the same
        brightness everywhere on the body."""
        a = (np.asarray(mask, dtype=np.float32) * opacity)[..., None]
        col = color if isinstance(color, np.ndarray) and color.ndim == 3 else rgb(color)
        self.px += (col - self.px) * a
        if not lit:
            if self.lit is None:
                self.lit = np.ones((self.H, self.W), dtype=np.float32)
            self.lit -= self.lit * a[..., 0]
        elif self.lit is not None:
            self.lit += (1.0 - self.lit) * a[..., 0]

    def polygon(self, pts, color, opacity: float = 1.0):
        self.paint(self.mask_polygon(pts), color, opacity)

    def line(self, pts, width, color, opacity: float = 1.0):
        self.paint(self.mask_line(pts, width), color, opacity)

    def gradient_field(self, stops, axis: str = "x", angle_deg: float | None = None):
        """Colour field from [(position_px, colour), ...] along x, y, or a
        direction given by angle_deg (0 = +x, 90 = +y)."""
        X, Y = self.grid()
        if angle_deg is not None:
            a = math.radians(angle_deg)
            t = X * math.cos(a) + Y * math.sin(a)
        else:
            t = X if axis == "x" else Y
        pos = np.array([s[0] for s in stops], dtype=np.float32)
        cols = np.stack([rgb(s[1]) for s in stops])
        out = np.empty(t.shape + (3,), dtype=np.float32)
        for ch in range(3):
            out[..., ch] = np.interp(t, pos, cols[:, ch])
        return out

    # ---- decals -----------------------------------------------------------
    def stamp(self, decal: Image.Image, cx, cy, rot_deg: float = 0.0, opacity: float = 1.0):
        """Alpha-composite an RGBA decal (already at SS scale) centred on
        (cx, cy).  rot_deg is counter-clockwise."""
        d = decal
        if rot_deg:
            d = d.rotate(rot_deg, resample=Image.BICUBIC, expand=True)
        arr = np.asarray(d, dtype=np.float32)
        dh, dw = arr.shape[:2]
        x0 = int(round(cx * SS - dw / 2))
        y0 = int(round(cy * SS - dh / 2))
        sx0, sy0 = max(0, -x0), max(0, -y0)
        tx0, ty0 = max(0, x0), max(0, y0)
        tx1, ty1 = min(self.W, x0 + dw), min(self.H, y0 + dh)
        if tx1 <= tx0 or ty1 <= ty0:
            return
        src = arr[sy0:sy0 + ty1 - ty0, sx0:sx0 + tx1 - tx0]
        a = src[..., 3:4] / 255.0 * opacity
        dst = self.px[ty0:ty1, tx0:tx1]
        dst += (src[..., :3] - dst) * a
        if self.lit is not None:
            dl = self.lit[ty0:ty1, tx0:tx1]
            dl += (1.0 - dl) * a[..., 0]

    # ---- output -----------------------------------------------------------
    def result(self) -> np.ndarray:
        """Box-filter down to canvas resolution -> float32 (h, w, 3)."""
        return self.px.reshape(self.h, SS, self.w, SS, 3).mean(axis=(1, 3))

    def out(self) -> np.ndarray:
        """The supersampled image, as compose() wants it: RGB, plus a fourth
        channel (1 = shaded by the finish) when some paint is exempt."""
        if self.lit is None:
            return self.px
        return np.concatenate([self.px, self.lit[..., None]], axis=-1)

    def mirrored(self) -> "Canvas":
        """Left-right mirror image as a canvas for the opposite flank."""
        other = {"side_L": "side_R", "side_R": "side_L", "rail_L": "rail_R",
                 "rail_R": "rail_L", "mirror_L": "mirror_R", "mirror_R": "mirror_L"}[self.view.name]
        c = Canvas.__new__(Canvas)
        c.view = get_view(other)
        c.w, c.h = c.view.w, c.view.h
        c.W, c.H = c.w * SS, c.h * SS
        src = self.px[:, ::-1]
        c.lit = None
        if (c.H, c.W) == src.shape[:2]:
            c.px = src.copy()
            if self.lit is not None:
                c.lit = self.lit[:, ::-1].copy()
        else:  # mirror caps / rail strips differ by a pixel or two between the two sides
            c.px = np.asarray(
                Image.fromarray(np.clip(src, 0, 255).astype(np.uint8)).resize((c.W, c.H), Image.BILINEAR),
                dtype=np.float32)
            if self.lit is not None:
                c.lit = np.asarray(Image.fromarray(self.lit[:, ::-1].astype(np.float32), "F").resize(
                    (c.W, c.H), Image.BILINEAR), dtype=np.float32)
        return c


# --------------------------------------------------------------------------
# Decal builders (return RGBA PIL images at SS scale)
# --------------------------------------------------------------------------
def _shear(im: Image.Image, shear: float) -> Image.Image:
    """Lean an RGBA image: positive shear pushes the top edge to the right."""
    pad = int(math.ceil(abs(shear) * im.height)) + 2
    wide = Image.new("RGBA", (im.width + pad, im.height), (0, 0, 0, 0))
    wide.paste(im, (0, 0))
    # output (x, y) samples input (x + shear * y - shift, y)
    shift = shear * im.height if shear > 0 else 0.0
    return wide.transform(wide.size, Image.AFFINE, (1, shear, -shift, 0, 1, 0),
                          resample=Image.BICUBIC)


def text_decal(text: str, font: str, size: float, fill="#000000", tracking: float = 0.0,
               shear: float = 0.0, stroke: float = 0.0, stroke_fill="#000000",
               squeeze: float = 1.0) -> Image.Image:
    """Render one line of text.

    size      cap-ish height in texture pixels (font size = size * SS)
    tracking  extra letter spacing in texture pixels
    shear     horizontal shear (0.2 leans the text like an italic)
    squeeze   horizontal scale (0.8 = condensed, 1.2 = extended)
    """
    f = ImageFont.truetype(find_font(font), max(4, int(round(size * SS))))
    sw = int(round(stroke * SS))
    adv = [f.getlength(ch) + tracking * SS for ch in text]
    asc, desc = f.getmetrics()
    w = int(math.ceil(sum(adv))) + 2 * sw + 8
    h = asc + desc + 2 * sw + 8
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x = sw + 4
    fc = tuple(int(v) for v in rgb(fill)) + (255,)
    sc = tuple(int(v) for v in rgb(stroke_fill)) + (255,)
    for ch, a in zip(text, adv):
        d.text((x, sw + 4), ch, font=f, fill=fc, stroke_width=sw, stroke_fill=sc)
        x += a
    if squeeze != 1.0:
        im = im.resize((max(1, int(round(im.width * squeeze))), im.height), Image.LANCZOS)
    if shear:
        im = _shear(im, shear)
    bbox = im.getbbox()
    return im.crop(bbox) if bbox else im


def box_decal(w: float, h: float, fill, radius: float = 0.0, outline=None,
              outline_width: float = 0.0, shear: float = 0.0) -> Image.Image:
    """Rounded rectangle, optionally sheared into a parallelogram."""
    W, H = int(round(w * SS)), int(round(h * SS))
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    fc = tuple(int(v) for v in rgb(fill)) + (255,)
    kw = {}
    if outline is not None and outline_width > 0:
        kw = dict(outline=tuple(int(v) for v in rgb(outline)) + (255,),
                  width=max(1, int(round(outline_width * SS))))
    d.rounded_rectangle([0, 0, W - 1, H - 1], radius=radius * SS, fill=fc, **kw)
    if shear:
        im = _shear(im, shear)
    return im


_SEGMENTS = {  # seven-segment map: a top, b top-right, c bottom-right, d bottom,
    "0": "abcdef", "1": "bc", "2": "abged", "3": "abgcd", "4": "fgbc",   # e bottom-left, f top-left, g middle
    "5": "afgcd", "6": "afgedc", "7": "abc", "8": "abcdefg", "9": "abfgcd",
}


def block_digits(text: str, height: float, fill="#000000", weight: float = 0.2,
                 aspect: float = 0.62, gap: float = 0.16, shear: float = 0.0,
                 chamfer: float = 0.5) -> Image.Image:
    """Race number in squared, blocky digits (the look of an F1 number panel).

    height   digit height in texture pixels
    weight   stroke thickness as a fraction of the height
    aspect   digit width / height
    gap      space between digits as a fraction of the height
    chamfer  size of the cut on the outer corners, in stroke widths
    """
    H = height * SS
    t = weight * H
    w = aspect * H
    g = gap * H
    n = len(text)
    im = Image.new("L", (int(math.ceil(n * w + (n - 1) * g)) + 2, int(math.ceil(H)) + 2), 0)
    d = ImageDraw.Draw(im)
    for i, ch in enumerate(text):
        x0 = 1 + i * (w + g)
        y0, y1, ym = 1, 1 + H, 1 + H / 2
        x1 = x0 + w
        if ch == "1":                      # a lone right-hand stroke looks lost: centre it
            x0, x1 = x0 + w * 0.2, x1 - w * 0.2
        rects = {
            "a": (x0, y0, x1, y0 + t), "d": (x0, y1 - t, x1, y1), "g": (x0, ym - t / 2, x1, ym + t / 2),
            "f": (x0, y0, x0 + t, ym + t / 2), "e": (x0, ym - t / 2, x0 + t, y1),
            "b": (x1 - t, y0, x1, ym + t / 2), "c": (x1 - t, ym - t / 2, x1, y1),
        }
        segs = _SEGMENTS.get(ch, "")
        for k in segs:
            d.rectangle(rects[k], fill=255)
        c = chamfer * t
        if c > 0:  # cut the outer corners that the digit actually uses
            if "a" in segs and "f" in segs:
                d.polygon([(x0 - 1, y0 - 1), (x0 + c, y0 - 1), (x0 - 1, y0 + c)], fill=0)
            if "a" in segs and "b" in segs:
                d.polygon([(x1 + 1, y0 - 1), (x1 - c, y0 - 1), (x1 + 1, y0 + c)], fill=0)
            if "d" in segs and "e" in segs:
                d.polygon([(x0 - 1, y1 + 1), (x0 + c, y1 + 1), (x0 - 1, y1 - c)], fill=0)
            if "d" in segs and "c" in segs:
                d.polygon([(x1 + 1, y1 + 1), (x1 - c, y1 + 1), (x1 + 1, y1 - c)], fill=0)
    col = tuple(int(v) for v in rgb(fill))
    out = Image.new("RGBA", im.size, col + (0,))
    out.putalpha(im)
    if shear:
        out = _shear(out, shear)
    bbox = out.getbbox()
    return out.crop(bbox) if bbox else out


def layer(*parts) -> Image.Image:
    """Stack decals centred on each other.  parts: decal or (decal, dx, dy)
    with offsets in texture pixels."""
    items = [(p, 0.0, 0.0) if isinstance(p, Image.Image) else p for p in parts]
    w = max(int(im.width + 2 * abs(dx) * SS) for im, dx, dy in items)
    h = max(int(im.height + 2 * abs(dy) * SS) for im, dx, dy in items)
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    for im, dx, dy in items:
        out.alpha_composite(im, (int(round((w - im.width) / 2 + dx * SS)),
                                 int(round((h - im.height) / 2 + dy * SS))))
    return out
