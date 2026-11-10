#!/usr/bin/env python3
"""Build wrapkit's projection calibration for the legacy Model Y from a model dump.

    python3 tools/calibrate/calibrate.py <mesh.json> [out-dir]

Writes modely_viewmap.png and modely_projection.json (default: tools/wrapkit/data/).
See posmap.py for the input format.  The calibration in this repository was
measured on the 3D model that the Tesla Wrap Gallery visualizer shows for the
"Model Y (Pre-2025)"; the model itself is not part of this repository.
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
from posmap import load, rasterise  # noqa: E402
from wrapkit.template import PANELS, panel_labels  # noqa: E402

N = 1024
S = 174.0                      # canvas pixels per metre (about one texel per pixel on the doors)
ZF, YT = 2.75, 1.90            # side canvases: X = (ZF - z) * S from the nose back, Y = (YT - y) * S from the top
SIDE_W, SIDE_H = 976, 288
HOOD = dict(xl=0.95, z0=1.20, w=332, h=256)       # plan view seen from the front: nose at the bottom
FRONT = dict(xl=1.16, yt=0.95, w=404, h=124)      # front elevation
REAR = dict(xl=1.16, yt=1.80, w=404, h=252)       # rear elevation
DECK = dict(xl=1.16, z0=-1.50, w=404, h=232)      # plan view of the liftgate's upward faces, seen from behind
STRIP_IDS = {"rail_L": 6, "rail_R": 7, "mirror_L": 8, "mirror_R": 9}
REGION_VIEW = {1: "side_L", 2: "side_R", 3: "hood", 4: "front", 5: "rear", 10: "deck"}   # texel id -> canvas
DEG = 7


def project(view, P):
    x, y, z = P[..., 0], P[..., 1], P[..., 2]
    if view == "side_L": return (ZF - z) * S, (YT - y) * S
    if view == "side_R": return SIDE_W - (ZF - z) * S, (YT - y) * S
    if view == "hood":   return (HOOD["xl"] + x) * S, (z - HOOD["z0"]) * S
    if view == "front":  return (FRONT["xl"] + x) * S, (FRONT["yt"] - y) * S
    if view == "rear":   return (REAR["xl"] - x) * S, (REAR["yt"] - y) * S
    if view == "deck":   return (DECK["xl"] - x) * S, (DECK["z0"] - z) * S
    raise KeyError(view)


def basis(px, py, cx, cy, sc):
    u, v = (px - cx) / sc, (py - cy) / sc
    return np.stack([u ** i * v ** j for i in range(DEG + 1) for j in range(DEG + 1 - i)], -1)


def main(mesh_json, out_dir):
    pos, nrm, part = rasterise(load(mesh_json), N)
    cov = part >= 0
    lab = panel_labels()
    inv = {v: k for k, v in PANELS.items()}
    # which way a surface faces decides its canvas where a panel turns a corner
    # (smoothed so each split is one clean line)
    side_facing = ndi.median_filter((np.abs(nrm[..., 0]) > np.abs(nrm[..., 2])).astype(np.uint8), size=9) > 0
    up_facing = ndi.median_filter((nrm[..., 1] > np.abs(nrm[..., 2])).astype(np.uint8), size=9) > 0
    view = np.zeros((N, N), np.uint8)
    for pid, name in inv.items():
        m = (lab == pid) & cov
        if name in ("fender_L", "front_door_L", "rear_door_L", "quarter_L"): view[m] = 1
        elif name in ("fender_R", "front_door_R", "rear_door_R", "quarter_R"): view[m] = 2
        elif name == "hood": view[m] = 3
        elif name == "liftgate":
            view[m] = 5
            view[m & up_facing] = 10          # glass frame and spoiler: seen from above, not from behind
        elif name in ("front_bumper", "rear_bumper"):
            left = pos[..., 0] > 0
            view[m & side_facing & left] = 1
            view[m & side_facing & ~left] = 2
            view[m & ~side_facing] = 4 if name == "front_bumper" else 5
        else: view[m] = STRIP_IDS[name]
    yy, xx = np.mgrid[0:N, 0:N]
    regions = []
    for pid, pname in inv.items():
        for vid, vname in REGION_VIEW.items():
            m = (lab == pid) & (view == vid)
            n = int(m.sum())
            if n == 0:
                continue
            if n < 400:      # too small to fit: treated as hidden margin and filled from neighbours
                view[m] = 0
                print(f"{pname:13s} {vname:7s} n={n:6d}  dropped (too small)")
                continue
            px, py = xx[m] + 0.5, yy[m] + 0.5
            cx, cy, sc = float(px.mean()), float(py.mean()), float(max(np.ptp(px), np.ptp(py)) / 2 + 1)
            A = basis(px, py, cx, cy, sc)
            X, Y = project(vname, pos[m].astype(np.float64))
            cX, *_ = np.linalg.lstsq(A, X, rcond=None)
            cY, *_ = np.linalg.lstsq(A, Y, rcond=None)
            r = np.hypot(A @ cX - X, A @ cY - Y)
            regions.append(dict(panel=pname, view=vname, id=vid, cx=cx, cy=cy, scale=sc,
                                x=[float(v) for v in cX], y=[float(v) for v in cY]))
            print(f"{pname:13s} {vname:7s} n={n:6d}  fit error px: rms {np.sqrt((r ** 2).mean()):.2f}  "
                  f"p99 {np.percentile(r, 99):.2f}  max {r.max():.2f}")
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    Image.fromarray(view, "L").save(out / "modely_viewmap.png", optimize=True)
    canvases = {"side_L": [SIDE_W, SIDE_H], "side_R": [SIDE_W, SIDE_H], "hood": [HOOD["w"], HOOD["h"]],
                "front": [FRONT["w"], FRONT["h"]], "rear": [REAR["w"], REAR["h"]], "deck": [DECK["w"], DECK["h"]]}
    json.dump(dict(pixels_per_metre=S, degree=DEG, canvases=canvases, regions=regions),
              open(out / "modely_projection.json", "w"))
    print(f"template area the car really shows: {int((view > 0).sum())} of {int((lab > 0).sum())} texels")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else str(HERE.parent / "wrapkit" / "data"))
