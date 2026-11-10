#!/usr/bin/env python3
"""Build the W16 tribute wraps for the legacy Model Y.

    python3 tools/build.py            # all designs
    python3 tools/build.py w16_a      # one design

Each design module in tools/designs/ exposes NAME, TITLE and build() -> RGBA
texture.  Wraps are written to modely/w16/<NAME>.png; a flat preview sheet and
a three-quarter mock-up go to modely/w16/preview/<NAME>_sheet.png / _3q.png.
"""
from __future__ import annotations

import importlib
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from wrapkit import save_sheet, save_wrap  # noqa: E402
from wrapkit.mock import save_mockup  # noqa: E402

REPO = HERE.parent
OUT = REPO / "modely" / "w16"
DESIGNS = ["w16_a", "w16_b", "w16_c"]


def build_one(mod_name: str, out_dir: Path = OUT) -> dict:
    t0 = time.time()
    mod = importlib.import_module(f"designs.{mod_name}")
    tex = mod.build()
    path = out_dir / f"{mod.NAME}.png"
    report = save_wrap(tex, path)
    save_sheet(path, out_dir / "preview" / f"{mod.NAME}_sheet.png", title=f"{mod.TITLE}",
               subtitle=f"{path.name}  -  {report['bytes'] / 1000:.0f} kB  -  flat preview, not Tesla's 3D render")
    save_mockup(path, out_dir / "preview" / f"{mod.NAME}_3q.png")
    report["seconds"] = round(time.time() - t0, 1)
    return report


def compare_sheet(out_dir: Path, names) -> Path:
    """Side-by-side picture of all designs: mock-up on top, left flank below."""
    from PIL import Image, ImageDraw, ImageFont
    from wrapkit import decompose, find_font, side_elevation
    import numpy as np

    cells = []
    for mod_name in names:
        mod = importlib.import_module(f"designs.{mod_name}")
        wrap = out_dir / f"{mod.NAME}.png"
        if not wrap.exists():
            continue
        mock = Image.open(out_dir / "preview" / f"{mod.NAME}_3q.png").convert("RGB")
        side = side_elevation(decompose(np.asarray(Image.open(wrap).convert("RGBA"))), "L", scale=1.0)
        side = side.convert("RGB").resize((mock.width, int(side.height * mock.width / side.width)), Image.LANCZOS)
        cells.append((mod.TITLE, f"{mod.NAME}.png", mock, side))
    if not cells:
        return None
    w = cells[0][2].width
    h = 86 + cells[0][2].height + cells[0][3].height
    sheet = Image.new("RGB", (w * len(cells) + 16 * (len(cells) + 1), h + 32), (22, 24, 28))
    d = ImageDraw.Draw(sheet)
    big = ImageFont.truetype(find_font("Inter-Bold.otf"), 40)
    small = ImageFont.truetype(find_font("Inter-SemiBold.otf"), 20)
    for i, (title, fname, mock, side) in enumerate(cells):
        x = 16 + i * (w + 16)
        d.text((x + 6, 14), title, font=big, fill=(240, 240, 240))
        d.text((x + 8, 62), fname, font=small, fill=(0, 210, 190))
        sheet.paste(mock, (x, 92))
        sheet.paste(side, (x, 92 + mock.height))
    path = out_dir / "preview" / "compare.png"
    sheet.save(path, optimize=True)
    return path


def main(argv):
    out_dir = OUT
    names = [a for a in argv if not a.startswith("--")]
    for a in argv:
        if a.startswith("--out="):
            out_dir = Path(a.split("=", 1)[1])
    for name in names or DESIGNS:
        if not (HERE / "designs" / f"{name}.py").exists():
            print(f"skip {name}: no such design")
            continue
        r = build_one(name, out_dir)
        print(f"{r['name']:28s} {r['bytes']:>8d} bytes  {r['method']}  ({r['seconds']} s)")
    compare_sheet(out_dir, DESIGNS)


if __name__ == "__main__":
    main(sys.argv[1:])
