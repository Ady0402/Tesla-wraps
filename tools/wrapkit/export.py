"""Save a wrap texture so that it satisfies Tesla's custom-wrap rules.

Rules (README.md of teslamotors/custom-wraps):
  * PNG, 512x512 .. 1024x1024 pixels (template size recommended)
  * at most 1 MB
  * file name: alphanumerics, underscores, dashes and spaces only, <= 30 chars
"""
from __future__ import annotations

import os
import re
import shutil
import struct
import subprocess
import tempfile
import zlib
from pathlib import Path

import numpy as np
from PIL import Image

from .template import SIZE, TEMPLATE_PATH, template_alpha

MAX_BYTES = 1_000_000          # the stricter reading of "1 MB"
# Tesla does not say which "1 MB" it means and oversized files are silently
# ignored by the car, so stay under the largest file Tesla itself ships (933 kB).
TARGET_BYTES = 900_000
NAME_RE = re.compile(r"^[A-Za-z0-9_\- ]+$")
MAX_NAME = 30
MAX_METADATA = 16_384          # bytes of ancillary chunks we tolerate
COLOUR_TYPES = {0: "grey", 2: "RGB", 3: "palette", 4: "grey+alpha", 6: "RGBA"}


def check_name(path: Path) -> list:
    problems = []
    stem = path.stem
    if path.suffix != ".png":
        problems.append(f"extension must be .png, got {path.suffix!r}")
    if not NAME_RE.match(stem):
        problems.append(f"name {stem!r} has characters other than A-Z a-z 0-9 _ - space")
    if len(path.name) > MAX_NAME:
        problems.append(f"file name {path.name!r} is {len(path.name)} chars (max {MAX_NAME} incl. extension)")
    return problems


def png_structure(path) -> dict:
    """Read the PNG container directly (no decoder): IHDR fields, chunk
    names, size of ancillary chunks, bytes after IEND, CRC errors."""
    data = Path(path).read_bytes()
    info = {"signature": data[:8] == b"\x89PNG\r\n\x1a\n", "chunks": [], "ancillary_bytes": 0,
            "trailing_bytes": 0, "crc_errors": 0}
    if not info["signature"]:
        return info
    pos = 8
    while pos + 8 <= len(data):
        length, ctype = struct.unpack(">I4s", data[pos:pos + 8])
        body = data[pos + 8:pos + 8 + length]
        crc = data[pos + 8 + length:pos + 12 + length]
        if len(crc) < 4 or struct.unpack(">I", crc)[0] != (zlib.crc32(ctype + body) & 0xFFFFFFFF):
            info["crc_errors"] += 1
        name = ctype.decode("latin-1")
        info["chunks"].append(name)
        if name == "IHDR" and length == 13:
            w, h, depth, colour, _comp, _filt, interlace = struct.unpack(">IIBBBBB", body)
            info.update(width=w, height=h, bit_depth=depth, colour_type=colour, interlace=interlace)
        elif name not in ("IDAT", "IEND", "PLTE", "tRNS"):
            info["ancillary_bytes"] += length
        pos += 12 + length
        if name == "IEND":
            break
    info["trailing_bytes"] = len(data) - pos
    return info


def validate(path, name: str | None = None) -> dict:
    """Check a saved wrap against every rule.  Returns {'ok': bool, 'problems': [...], ...}.
    name: file name to judge instead of path's own (used while a file is still staged)."""
    path = Path(path)
    shown = name or path.name
    problems = check_name(Path(shown))
    size = path.stat().st_size
    if size > MAX_BYTES:
        problems.append(f"{size} bytes exceeds {MAX_BYTES}")
    st = png_structure(path)
    report = {"name": shown, "bytes": size, "size": (st.get("width"), st.get("height")),
              "bit_depth": st.get("bit_depth"), "colour_type": COLOUR_TYPES.get(st.get("colour_type"), "?"),
              "alpha_identical": None, "alpha_diff_pixels": None}
    if not st["signature"] or "IHDR" not in st["chunks"]:
        problems.append("not a PNG file")
        report.update(ok=False, problems=problems)
        return report
    w, h = st["width"], st["height"]
    if w != h or not (512 <= w <= 1024):
        problems.append(f"size {w}x{h} is not a square between 512 and 1024")
    if st["bit_depth"] != 8:
        problems.append(f"bit depth is {st['bit_depth']}, expected 8")
    if st["interlace"]:
        problems.append("PNG is interlaced")
    if st["crc_errors"]:
        problems.append(f"{st['crc_errors']} chunk(s) with a bad CRC")
    if st["trailing_bytes"]:
        problems.append(f"{st['trailing_bytes']} stray bytes after the end of the PNG")
    if st["ancillary_bytes"] > MAX_METADATA:
        problems.append(f"{st['ancillary_bytes']} bytes of metadata chunks")
    with Image.open(path) as im:
        rgba = np.asarray(im.convert("RGBA"))
    alpha = rgba[..., 3]
    if (w, h) == (SIZE, SIZE):
        ref = template_alpha()
        diff = int((alpha != ref).sum())
        report["alpha_identical"] = diff == 0
        report["alpha_diff_pixels"] = diff
        unpainted = int(((ref == 255) & (alpha < 255)).sum())
        if unpainted:
            problems.append(f"{unpainted} panel pixels are not fully opaque")
        stray = int(((ref == 0) & (alpha > 0)).sum())
        if stray:
            problems.append(f"{stray} pixels painted outside the template islands")
        # still Tesla's blank template?  (white fill and black outline untouched)
        with Image.open(TEMPLATE_PATH) as t:
            tpl = np.asarray(t.convert("RGBA"))
        solid = ref == 255
        same = (rgba[..., :3] == tpl[..., :3]).all(-1) & solid
        outline = solid & (tpl[..., :3].max(-1) < 100)
        fill = solid & ~outline
        if same[outline].mean() > 0.5 and same[fill].mean() > 0.3:
            problems.append("panels still look like the blank template (white fill / black outline)")
    report.update(ok=not problems, problems=problems)
    return report


def _encode(arr: np.ndarray, path: Path):
    """Plain 8-bit RGBA PNG: IHDR + IDAT + IEND, no metadata."""
    Image.fromarray(arr, "RGBA").save(path, format="PNG", optimize=True, compress_level=9)
    if shutil.which("optipng"):
        subprocess.run(["optipng", "-quiet", "-o2", "-strip", "all", str(path)], capture_output=True)


def _reduce_colours(texture: np.ndarray, colours: int) -> np.ndarray:
    """Quantise the COLOUR only.  The texture is made fully opaque first so the
    edge pixels and the bleed keep their paint colour; the exact template alpha
    is put back afterwards."""
    opaque = texture.copy()
    opaque[..., 3] = 255
    rgb = None
    if shutil.which("pngquant"):
        with tempfile.TemporaryDirectory() as td:
            src, dst = Path(td) / "in.png", Path(td) / "out.png"
            Image.fromarray(opaque, "RGBA").save(src)
            r = subprocess.run(["pngquant", "--force", "--strip", "--speed", "1", "--output", str(dst),
                                str(colours), str(src)], capture_output=True)
            if r.returncode == 0 and dst.exists():
                with Image.open(dst) as im:
                    rgb = np.asarray(im.convert("RGB"))
    if rgb is None:
        q = Image.fromarray(opaque[..., :3], "RGB").quantize(colors=colours, method=Image.Quantize.MEDIANCUT)
        rgb = np.asarray(q.convert("RGB"))
    out = texture.copy()
    out[..., :3] = rgb
    return out


def save_wrap(texture: np.ndarray, path, max_bytes: int = TARGET_BYTES) -> dict:
    """Write the texture as a rule-compliant PNG.  Lossless if it fits in
    max_bytes; otherwise the number of colours is reduced step by step until
    it does.  The destination is only replaced once the file validates."""
    path = Path(path)
    problems = check_name(path)
    if problems:
        raise ValueError("; ".join(problems))
    assert texture.shape == (SIZE, SIZE, 4) and texture.dtype == np.uint8
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(suffix=".png", dir=path.parent)
    os.close(fd)
    tmp = Path(tmp_name)
    try:
        _encode(texture, tmp)
        method = "lossless RGBA"
        if tmp.stat().st_size > max_bytes:
            for colours in (256, 192, 128, 96, 64, 48, 32, 24, 16):
                _encode(_reduce_colours(texture, colours), tmp)
                method = f"RGBA reduced to {colours} colours"
                if tmp.stat().st_size <= max_bytes:
                    break
            else:
                raise RuntimeError(f"{path.name}: cannot get under {max_bytes} bytes; simplify the artwork")
        report = validate(tmp, name=path.name)
        if not report["ok"]:
            raise RuntimeError(f"{path.name}: " + "; ".join(report["problems"]))
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()
    report["method"] = method
    return report
