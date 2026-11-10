"""Rasterise a car model's wrap UVs: for every texel of the wrap texture, the 3D
position and face normal of the surface that samples it.

Input is a JSON list of meshes, one object per mesh that takes the wrap:
    {"isWrap": true, "path": "ROOT/Door_LF/mesh", "pos": [x, y, z, ...] (world, metres),
     "nrm": [nx, ny, nz, ...] (world vertex normals, optional),
     "uv": [u, v, ...] (the UV set the wrap is sampled with, v = 0 at the top), "idx": [i, j, k, ...]}
Axes: +x = the car's left, +y = up, +z = toward the nose.
"""
import json

import numpy as np


def load(path):
    out = []
    for m in json.load(open(path)):
        if not m.get("isWrap"):
            continue
        P = np.array(m["pos"], dtype=np.float64).reshape(-1, 3)
        U = np.array(m["uv"], dtype=np.float64).reshape(-1, 2)
        I = np.array(m["idx"], dtype=np.int64).reshape(-1, 3)
        Nv = np.array(m["nrm"], dtype=np.float64).reshape(-1, 3) if m.get("nrm") else None
        if Nv is not None:
            Nv /= np.linalg.norm(Nv, axis=1, keepdims=True) + 1e-12
        out.append((m.get("path", ""), P, U, I, Nv))
    return out


def rasterise(meshes, N):
    pos = np.full((N, N, 3), np.nan, dtype=np.float32)
    nrm = np.zeros((N, N, 3), dtype=np.float32)
    part = np.full((N, N), -1, dtype=np.int16)
    for k, (_, P, U, I, Nv) in enumerate(meshes):
        uv = U * N                                   # texel coordinates, pixel centres at +0.5
        for tri in I:
            a, b, c = uv[tri]
            x0, x1 = int(np.floor(min(a[0], b[0], c[0]))), int(np.ceil(max(a[0], b[0], c[0])))
            y0, y1 = int(np.floor(min(a[1], b[1], c[1]))), int(np.ceil(max(a[1], b[1], c[1])))
            x0, y0, x1, y1 = max(x0, 0), max(y0, 0), min(x1, N - 1), min(y1, N - 1)
            if x1 < x0 or y1 < y0:
                continue
            den = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
            if abs(den) < 1e-12:
                continue
            X, Y = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
            w0 = ((b[1] - c[1]) * (X - c[0]) + (c[0] - b[0]) * (Y - c[1])) / den
            w1 = ((c[1] - a[1]) * (X - c[0]) + (a[0] - c[0]) * (Y - c[1])) / den
            w2 = 1 - w0 - w1
            inside = (w0 >= -1e-4) & (w1 >= -1e-4) & (w2 >= -1e-4)
            if not inside.any():
                continue
            pa, pb, pc = P[tri]
            p = w0[..., None] * pa + w1[..., None] * pb + w2[..., None] * pc
            if Nv is not None:              # smooth shading normal, as the renderer uses
                na, nb, nc = Nv[tri]
                n = w0[..., None] * na + w1[..., None] * nb + w2[..., None] * nc
                n = n / (np.linalg.norm(n, axis=-1, keepdims=True) + 1e-12)
            else:                           # flat face normal
                n = np.cross(pb - pa, pc - pa)
                n = np.broadcast_to(n / (np.linalg.norm(n) + 1e-12), p.shape)
            sl = (slice(y0, y1 + 1), slice(x0, x1 + 1))
            pos[sl][inside] = p[inside]
            nrm[sl][inside] = n[inside]
            part[sl][inside] = k
    return pos, nrm, part
