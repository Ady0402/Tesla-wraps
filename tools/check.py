#!/usr/bin/env python3
"""Check wrap PNGs against Tesla's custom-wrap rules.

    python3 tools/check.py modely/w16/*.png
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from wrapkit import validate  # noqa: E402


def main(paths):
    bad = 0
    for p in paths:
        r = validate(p)
        status = "OK  " if r["ok"] else "FAIL"
        alpha = {True: "alpha = template", False: f"alpha <= template, {100 * r.get('translucent_share', 0):.0f}% translucent",
                 None: "alpha not compared"}[r["alpha_identical"]]
        print(f"{status} {r['name']:30s} {r['size'][0]}x{r['size'][1]}  {r['bit_depth']}-bit {r['colour_type']:5s} "
              f"{r['bytes']:>8d} bytes  {alpha}")
        for msg in r["problems"]:
            print(f"       - {msg}")
        bad += not r["ok"]
    return 1 if bad else 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1:]))
