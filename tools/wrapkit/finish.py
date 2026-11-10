"""Paint finishes baked into the texture.

The car (and the Tesla app) render a wrap as matte vinyl: whatever colour the
texture has is lit like a flat, rough surface.  A metallic look therefore has to
be painted in.  ``metallic`` does that from the surface normal of every texel
(measured on the 3D model, see carmap.py): it works out which part of a simple
photo-studio surrounding each point of the body would mirror - floor, a dark
horizon band, a bright horizon line, open sky, an overhead light box - for a
viewer standing beside the car with eyes a little above the body, and shades
the paint with it.  Because the reflection follows the surface, the light and
dark edges land on the body lines: the shoulder above the door handles, the
lower door crease, the hood edges and the curve of the wheel arches.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .carmap import normals, on_car
from .template import PANELS, panel_labels

# panels a viewer usually sees from the front / from behind rather than face-on
_FRONT = ("hood", "front_bumper", "fender_L", "fender_R")
_REAR = ("liftgate", "rear_bumper", "quarter_L", "quarter_R")


@dataclass(frozen=True)
class Metallic:
    """Studio reflection baked into the paint.

    strength      0 = flat paint, 1 = full effect
    eye_deg       height of the assumed viewer above the panel, in degrees
    floor         brightness mirrored from the floor (0..1)
    horizon       brightness of the dark band just below the horizon
    sky           brightness of the open sky above the horizon
    box           brightness of the overhead light box
    line_gain     extra white added along the bright horizon line (the "light on the body line")
    """
    strength: float = 1.0
    eye_deg: float = 18.0
    floor: float = 0.40
    horizon: float = 0.20
    sky: float = 0.72
    box: float = 1.0
    line_gain: float = 62.0
    crease_gain: float = 0.0

    def environment(self, elev_deg: np.ndarray):
        """Brightness (0..1) and highlight (0..1) mirrored from a direction at
        the given elevation."""
        e = np.asarray(elev_deg, dtype=np.float32)

        def s(a, b):
            t = np.clip((e - a) / (b - a), 0.0, 1.0)
            return t * t * (3 - 2 * t)
        val = self.floor + (self.horizon - self.floor) * s(-35.0, -4.0)          # floor, darkening toward the horizon
        val = val + (1.0 - val) * s(-4.0, 1.5)                                 # step up to the horizon line
        val = val + (self.sky - val) * s(3.0, 12.0)                            # the line fades into the sky
        val = val + (self.box - val) * s(28.0, 40.0)                           # overhead light box
        val = val + (self.sky - val) * s(58.0, 74.0)
        line = np.exp(-0.5 * ((e - 1.0) / 2.6) ** 2)                           # the bright horizon line itself
        box_edge = np.exp(-0.5 * ((e - 34.0) / 3.0) ** 2) * 0.55               # the edges of the light box
        box_edge = np.maximum(box_edge, np.exp(-0.5 * ((e - 66.0) / 3.0) ** 2) * 0.35)
        return val.astype(np.float32), np.maximum(line, box_edge).astype(np.float32)

    def __call__(self, rgb: np.ndarray, mask: np.ndarray | None = None) -> np.ndarray:
        """Shade an (1024, 1024, 3) float texture; texels outside `mask` (default:
        everything the car shows) are left alone."""
        if self.strength <= 0:
            return rgb
        n = normals()
        on = on_car() if mask is None else (mask & on_car())
        lab = panel_labels()
        # horizontal direction the viewer looks from: along the panel's own normal,
        # pulled toward the front or the back for panels mostly seen from there
        bias = np.zeros(lab.shape + (3,), np.float32)
        for name in _FRONT:
            bias[lab == PANELS[name], 2] = 0.35
        for name in _REAR:
            bias[lab == PANELS[name], 2] = -0.35
        h = n * np.array([1, 0, 1], np.float32) + bias
        h /= np.maximum(np.linalg.norm(h, axis=-1, keepdims=True), 1e-6)
        a = np.radians(self.eye_deg)
        eye = h * np.cos(a) + np.array([0, 1, 0], np.float32) * np.sin(a)
        ndote = (n * eye).sum(-1, keepdims=True)
        r = 2 * ndote * n - eye                                               # mirrored direction
        elev = np.degrees(np.arcsin(np.clip(r[..., 1], -1, 1)))
        val, hi = self.environment(elev)
        k = self.strength
        shade = 1.0 + k * (0.56 + 0.62 * val - 1.0)                             # 0.68 .. 1.18 of the paint colour
        add = self.line_gain * hi
        if self.crease_gain:
            add = add + self.crease_gain * creases()
        out = rgb.copy()
        o = on
        out[o] = rgb[o] * shade[o][:, None] + (k * add[o])[:, None]
        return np.clip(out, 0, 255)


def creases() -> np.ndarray:
    """0..1 per texel: how sharply the body bends there (the body lines)."""
    from functools import lru_cache  # noqa: F401  (cached below)
    return _creases()


def _crease_map():
    from scipy import ndimage as ndi
    n = normals()
    on = on_car()
    lab = panel_labels()
    bend = np.zeros(on.shape, np.float32)
    for axis in (0, 1):
        a = np.roll(n, 1, axis=axis)
        b = np.roll(n, -1, axis=axis)
        same = (np.roll(lab, 1, axis=axis) == lab) & (np.roll(lab, -1, axis=axis) == lab) & on
        same &= np.roll(on, 1, axis=axis) & np.roll(on, -1, axis=axis)
        d = np.linalg.norm(a - b, axis=-1) * same           # change of the normal over 2 texels
        bend = np.maximum(bend, d)
    bend = ndi.gaussian_filter(bend, 1.2)
    t = np.clip((bend - 0.035) / (0.09 - 0.035), 0, 1)
    return (t * t * (3 - 2 * t)).astype(np.float32)


_CREASES = None


def _creases():
    global _CREASES
    if _CREASES is None:
        _CREASES = _crease_map()
    return _CREASES


def metallic(strength: float = 1.0, **kw) -> Metallic:
    return Metallic(strength=strength, **kw)
