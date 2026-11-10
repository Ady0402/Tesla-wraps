"""Save a wrap texture so that it satisfies Tesla's custom-wrap rules.

Rules (README.md of teslamotors/custom-wraps):
  * PNG, 512x512 .. 1024x1024 pixels (template size recommended)
  * at most 1 MB
  * file name: alphanumerics, underscores, dashes and spaces only, <= 30 chars
"""
from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

from .template import SIZE, template_alpha

MAX_BYTES = 1_000_000          # the stricter reading of "1 MB"
# Tesla does not say which "1 MB" it means and oversized files are silently
# ignored by the car, so stay under the largest file Tesla itself ships (933 kB).
TARGET_BYTES = 900_000
NAME_RE = re.compile(r"^[A-Za-z0-9_\- ]+$")
MAX_NAME = 30


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


def validate(path) -> dict:
    """Check a saved wrap against every rule.  Returns {'ok': bool, 'problems': [...], ...}."""
    path = Path(path)
    problems = check_name(path)
    size = path.stat().st_size
    if size > MAX_BYTES:
        problems.append(f"{size} bytes exceeds {MAX_BYTES}")
    with Image.open(path) as im:
        fmt, mode, dims = im.format, im.mode, im.size
        interlaced = bool(im.info.get("interlace"))
        rgba = np.asarray(im.convert("RGBA"))
    if fmt != "PNG":
        problems.append(f"format is {fmt}, not PNG")
    if dims[0] != dims[1] or not (512 <= dims[0] <= 1024):
        problems.append(f"size {dims} is not a square between 512 and 1024")
    if interlaced:
        problems.append("PNG is interlaced")
    alpha = rgba[..., 3]
    coverage = None
    if dims == (SIZE, SIZE):
        ref = template_alpha()
        coverage = float(((alpha > 127) == (ref > 127)).mean())
        unpainted = int(((ref == 255) & (alpha < 255)).sum())
        if unpainted:
            problems.append(f"{unpainted} panel pixels are not fully opaque")
        stray = int(((ref == 0) & (alpha > 0)).sum())
        if stray:
            problems.append(f"{stray} pixels painted outside the template islands")
    return {"ok": not problems, "problems": problems, "bytes": size, "mode": mode,
            "size": dims, "alpha_match": coverage, "name": path.name}


def _write(arr: np.ndarray, path: Path):
    Image.fromarray(arr, "RGBA").save(path, format="PNG", optimize=True, compress_level=9)


def save_wrap(texture: np.ndarray, path, max_bytes: int = TARGET_BYTES) -> dict:
    """Write the texture as a rule-compliant PNG.  Tries lossless first, then
    palette quantisation (pngquant, falling back to Pillow) only if needed."""
    path = Path(path)
    problems = check_name(path)
    if problems:
        raise ValueError("; ".join(problems))
    assert texture.shape == (SIZE, SIZE, 4) and texture.dtype == np.uint8
    path.parent.mkdir(parents=True, exist_ok=True)
    _write(texture, path)
    method = "lossless RGBA"
    if path.stat().st_size > max_bytes and shutil.which("pngquant"):
        for quality in ("90-100", "80-98", "65-95", "45-90"):
            with tempfile.TemporaryDirectory() as td:
                src = Path(td) / "in.png"
                dst = Path(td) / "out.png"
                _write(texture, src)
                r = subprocess.run(["pngquant", "--force", "--strip", "--speed", "1",
                                    "--quality", quality, "--output", str(dst), "256", str(src)],
                                   capture_output=True)
                if r.returncode == 0 and dst.exists() and dst.stat().st_size <= max_bytes:
                    shutil.copyfile(dst, path)
                    method = f"pngquant 256 colours (quality {quality})"
                    break
    if path.stat().st_size > max_bytes:
        q = Image.fromarray(texture, "RGBA").quantize(colors=255, method=Image.Quantize.FASTOCTREE,
                                                      dither=Image.Dither.FLOYDSTEINBERG)
        q.save(path, format="PNG", optimize=True)
        method = "Pillow 255-colour palette"
    if method != "lossless RGBA":
        # quantisers may nudge alpha; restore the exact template footprint
        with Image.open(path) as im:
            arr = np.asarray(im.convert("RGBA")).copy()
        arr[..., 3] = texture[..., 3]
        arr[texture[..., 3] == 0, :3] = 0
        pal = Image.fromarray(arr, "RGBA")
        if len(pal.getcolors(maxcolors=1 << 24) or []) <= 256:
            pal = pal.quantize(colors=256, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE)
        pal.save(path, format="PNG", optimize=True)
    if shutil.which("optipng"):
        subprocess.run(["optipng", "-quiet", "-o2", "-strip", "all", str(path)], capture_output=True)
    report = validate(path)
    report["method"] = method
    if not report["ok"]:
        raise RuntimeError(f"{path.name}: " + "; ".join(report["problems"]))
    return report
