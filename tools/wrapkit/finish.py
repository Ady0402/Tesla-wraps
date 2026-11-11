"""Paint finishes baked into the texture.

The car (and the Tesla app) render an opaque wrap as matte vinyl.  Their
shader blends the wrap over the car's own paint by the wrap's alpha:

    colour    = mix(paint colour, wrap colour, alpha)
    roughness = mix(paint roughness ~0.1, 0.9, alpha)
    metallic  = mix(paint metallic ~0.7, 0.0, alpha)

so the only way to get a real glossy metallic surface is to let some of the
car's paint through: ``Metallic.opacity`` makes the silver (and, a little, the
black) parts of a design translucent while text, numbers and coloured
graphics stay fully opaque.  The silver then takes the colour of the car's
paint, so it is meant for a silver / grey car (or a silver colour chosen in
Paint Shop).  On top of that, a metallic look is also painted in:  ``metallic`` does that from the surface normal of every texel
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
    shade_lo: float = 0.56         # paint brightness where the darkest part of the studio is mirrored
    shade_hi: float = 1.18         # ... and where the brightest part is
    silver_alpha: float = 1.0      # wrap opacity on silver / grey paint (1 = opaque, matte)
    black_alpha: float = 1.0       # wrap opacity on black paint
    compensate: float = 3.0        # on translucent texels, amplify the painted light and shade by
                                   # up to this factor (1/alpha), since only alpha of it shows on the car
    shade_alpha: float = 0.0       # also put the light and shade into the opacity of translucent silver:
                                   # where the studio mirrors dark floor the wrap covers more (darker,
                                   # duller), on highlights and body lines it covers less (the car's
                                   # glossy paint shows through); 0 = off, 1 = full
    alpha_range: tuple = (0.08, 0.8)   # opacity limits for silver when shade_alpha is on

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

    def opacity(self, rgb: np.ndarray, shaded: bool = True) -> np.ndarray:
        """Wrap opacity (0..1) per texel from the design colour: neutral greys
        and silvers get silver_alpha, near-black black_alpha, white and any
        clearly coloured pixel stay opaque.  Smooth in colour, so anti-aliased
        edges get in-between values."""
        rgb = np.asarray(rgb, dtype=np.float32)
        mx, mn = rgb.max(-1), rgb.min(-1)
        sat = (mx - mn) / np.maximum(mx, 80.0)        # floor: dark colours have noisy ratios
        lum = rgb @ np.array([0.2126, 0.7152, 0.0722], np.float32)
        t = np.clip((sat - 0.06) / 0.10, 0, 1)
        neutral = 1.0 - t * t * (3 - 2 * t)
        a = np.interp(lum, [0, 45, 150, 226, 240, 256],
                      [self.black_alpha, self.black_alpha, self.silver_alpha, self.silver_alpha, 1.0, 1.0])
        a = 1.0 - neutral * (1.0 - a)
        if shaded and self.shade_alpha > 0 and self.silver_alpha < 1.0 and self.strength > 0 \
                and rgb.shape[:2] == on_car().shape:
            shade, add = self.shading()
            light = (shade - 1.0) + add / 200.0                    # < 0 in shade, > 0 on highlights
            lo, hi = self.alpha_range
            dark_part = np.clip(-light / 0.32, 0, 1)
            bright_part = np.clip(light / 0.35, 0, 1)
            a_s = self.silver_alpha + (hi - self.silver_alpha) * dark_part - (self.silver_alpha - lo) * bright_part
            how_silver = np.clip((1.0 - a) / max(1.0 - self.silver_alpha, 1e-3), 0, 1)
            a = a + self.shade_alpha * how_silver * (a_s - self.silver_alpha)
        return np.clip(a, 0, 1).astype(np.float32)

    def shading(self):
        """(shade factor, additive light) per texel - see __call__."""
        if getattr(self, "_shading", None) is not None:
            return self._shading
        n = normals()
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
        shade = 1.0 + k * (self.shade_lo + (self.shade_hi - self.shade_lo) * val - 1.0)
        add = self.line_gain * hi
        if self.crease_gain:
            add = add + self.crease_gain * creases()
        object.__setattr__(self, "_shading", (shade.astype(np.float32), (k * add).astype(np.float32)))
        return self._shading

    def __call__(self, rgb: np.ndarray, mask: np.ndarray | None = None) -> np.ndarray:
        """Shade an (1024, 1024, 3) float texture; texels outside `mask` (default:
        everything the car shows) are left alone."""
        if self.strength <= 0:
            return rgb
        on = on_car() if mask is None else (mask & on_car())
        shade, add = self.shading()
        out = rgb.copy()
        o = on
        out[o] = rgb[o] * shade[o][:, None] + add[o][:, None]
        if self.compensate > 1.0 and (self.silver_alpha < 1.0 or self.black_alpha < 1.0):
            # the car shows only alpha of the wrap over its own paint (whose colour is close to the
            # design's silver), so push the shading out by 1/alpha to keep the same light and shade
            a = self.opacity(rgb, shaded=False)
            g = np.minimum(1.0 / np.maximum(a, 1e-3), self.compensate)[..., None]
            out[o] = rgb[o] + (out[o] - rgb[o]) * g[o]
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
