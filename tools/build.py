#!/usr/bin/env python3
"""Build the W16 tribute wraps for the legacy Model Y.

    python3 tools/build.py                 # all designs
    python3 tools/build.py w16_a           # one design (w16_a .. w16_d)
    python3 tools/build.py --render        # also render them in 3D (see render_visualizer.js)

Each design module in tools/designs/ exposes NAME, TITLE and build() -> RGBA
texture.  Wraps are written to modely/w16/<NAME>.png, a flat sheet of every
side to modely/w16/preview/<NAME>_sheet.png and, with --render, 3D pictures to
modely/w16/preview/<NAME>_3d.jpg plus preview/compare.jpg.
"""
from __future__ import annotations

import importlib
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from wrapkit import save_sheet, save_wrap  # noqa: E402

REPO = HERE.parent
OUT = REPO / "modely" / "w16"
DESIGNS = ["w16_a", "w16_b", "w16_c", "w16_d"]
BG = (228, 229, 233)


def build_one(mod_name: str, out_dir: Path = OUT) -> dict:
    t0 = time.time()
    mod = importlib.import_module(f"designs.{mod_name}")
    tex = mod.build()
    path = out_dir / f"{mod.NAME}.png"
    report = save_wrap(tex, path)
    save_sheet(path, out_dir / "preview" / f"{mod.NAME}_sheet.png", title=f"{mod.TITLE}",
               subtitle=f"{path.name}  -  {report['bytes'] / 1000:.0f} kB  -  flat projections of the saved file")
    report["seconds"] = round(time.time() - t0, 1)
    return report


def _car(path: Path):
    """A render cropped to the car (the visualizer's backdrop is a plain light grey)."""
    import numpy as np
    from PIL import Image
    im = Image.open(path).convert("RGB")
    a = np.asarray(im).astype(int)
    diff = np.abs(a - a[:, 5:6, :]).sum(-1) > 45
    ys, xs = np.nonzero(diff)
    pad = 24
    return im.crop((max(0, xs.min() - pad), max(0, ys.min() - pad),
                    min(im.width, xs.max() + pad), min(im.height, ys.max() + pad)))


def render_3d(out_dir: Path, names) -> bool:
    """Render the built wraps with the Tesla Wrap Gallery visualizer and make
    the 3D preview pictures.  Returns False if node / Playwright / the site is
    not available."""
    from PIL import Image, ImageDraw, ImageFont
    from wrapkit import find_font

    mods = [importlib.import_module(f"designs.{n}") for n in names]
    wraps = [str(out_dir / f"{m.NAME}.png") for m in mods]
    if not shutil.which("node"):
        print("render: node is not installed")
        return False
    with tempfile.TemporaryDirectory() as td:
        env = dict(__import__("os").environ, VIEWS="left,right,fl,rl,front,rear")
        r = subprocess.run(["node", str(HERE / "render_visualizer.js"), td, *wraps], env=env,
                           capture_output=True, text=True, timeout=900)
        if r.returncode != 0:
            print("render:", (r.stderr or r.stdout).strip().splitlines()[-1:] or "failed")
            return False
        big = ImageFont.truetype(find_font("Inter-Bold.otf"), 40)
        small = ImageFont.truetype(find_font("Inter-SemiBold.otf"), 20)
        cells = []
        for m in mods:
            v = {k: _car(Path(td) / f"{m.NAME}_{k}.png") for k in ("left", "right", "fl", "rl", "front", "rear")}
            w = 1100
            fit = lambda im, width: im.resize((width, int(im.height * width / im.width)), Image.LANCZOS)
            rows = [[fit(v["left"], w), fit(v["right"], w)], [fit(v["fl"], w), fit(v["rl"], w)],
                    [fit(v["front"], w), fit(v["rear"], w)]]
            h = sum(max(i.height for i in row) for row in rows)
            sheet = Image.new("RGB", (2 * w, h + 70), BG)
            d = ImageDraw.Draw(sheet)
            d.text((24, 14), m.TITLE, font=big, fill=(20, 22, 26))
            d.text((2 * w - 24, 28), f"{m.NAME}.png", font=small, fill=(0, 130, 120), anchor="ra")
            y = 70
            for row in rows:
                for j, im in enumerate(row):
                    sheet.paste(im, (j * w, y))
                y += max(i.height for i in row)
            sheet.save(out_dir / "preview" / f"{m.NAME}_3d.jpg", quality=90, optimize=True)
            cells.append((m, fit(v["fl"], 760), fit(v["left"], 760)))
        cw = 760
        ch = 84 + max(c[1].height for c in cells) + max(c[2].height for c in cells)
        comp = Image.new("RGB", (cw * len(cells), ch), BG)
        d = ImageDraw.Draw(comp)
        for i, (m, q, side) in enumerate(cells):
            x = i * cw
            d.text((x + 20, 12), m.TITLE, font=big, fill=(20, 22, 26))
            d.text((x + 22, 60), f"{m.NAME}.png", font=small, fill=(0, 130, 120))
            comp.paste(q, (x, 84))
            comp.paste(side, (x, 84 + max(c[1].height for c in cells)))
        comp.save(out_dir / "preview" / "compare.jpg", quality=90, optimize=True)
    return True


def main(argv):
    out_dir = OUT
    for a in argv:
        if a.startswith("--out="):
            out_dir = Path(a.split("=", 1)[1])
    names = [a for a in argv if not a.startswith("--")] or DESIGNS
    built = []
    for name in names:
        if not (HERE / "designs" / f"{name}.py").exists():
            print(f"skip {name}: no such design")
            continue
        r = build_one(name, out_dir)
        built.append(name)
        print(f"{r['name']:28s} {r['bytes']:>8d} bytes  {r['method']}  ({r['seconds']} s)")
    if "--render" in argv and built:
        ok = render_3d(out_dir, built)
        print("3D previews written" if ok else "3D previews skipped")


if __name__ == "__main__":
    main(sys.argv[1:])
