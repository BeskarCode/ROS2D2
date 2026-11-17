# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""The grey frame of the LED face without AMS, thick enough to print as a loose inlay.

    python -I hardware/ros2_box_rack_v3/logo/gen_na_grey.py

On the box the logo is 80 mm wide, so the frame round the 12 dots (logo_grey.svg) is only ~0.6 mm:
too thin to print and handle alone. Here it grows inwards to FRAME_MM (4 lines of a 0.4 nozzle),
its outline unchanged, and keeps GAP_MM off the blue dots: where a dot is near the edge the frame
stays narrower there (at least MIN_MM: 1.22 mm under the bottom row of dots; checked in
tests/test_no_ams.py). Writes logo_grey_na.svg;
the face with AMS keeps logo_grey.svg.
"""
import pathlib
import re

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
SVG_W, SVG_H = 92.0, 15.4          # the SVGs' size (units)
PX = 0.1                           # their grid
MM_PER_UNIT = 80.0 / 92.0          # logo_w / LOGO_SVG_W in params.scad
FRAME_MM = 1.7
GAP_MM = 0.17
MIN_MM = 1.2                       # under the bottom row of dots: they are 1.30 mm from the edge (3 lines, narrower)

RECT = re.compile(r"M([\d.]+) ([\d.]+)H([\d.]+)V([\d.]+)H[\d.]+Z")


def load(name):
    """The SVG's rectangles as a boolean grid [row (y), column (x)]."""
    a = np.zeros((round(SVG_H / PX), round(SVG_W / PX)), bool)
    for x0, y0, x1, y1 in RECT.findall((HERE / name).read_text()):
        a[round(float(y0) / PX):round(float(y1) / PX), round(float(x0) / PX):round(float(x1) / PX)] = True
    return a


def disk(r):
    k = int(np.ceil(r))
    return [(dy, dx) for dy in range(-k, k + 1) for dx in range(-k, k + 1) if dy * dy + dx * dx <= r * r]


def shift(a, dy, dx, fill):
    out = np.full_like(a, fill)
    h, w = a.shape
    out[max(dy, 0):h + min(dy, 0), max(dx, 0):w + min(dx, 0)] = a[max(-dy, 0):h + min(-dy, 0), max(-dx, 0):w + min(-dx, 0)]
    return out


def dilate(a, r):
    out = a.copy()
    for dy, dx in disk(r):
        out |= shift(a, dy, dx, False)
    return out


def erode(a, r):
    out = a.copy()
    for dy, dx in disk(r):
        out &= shift(a, dy, dx, False)
    return out


def fill_holes(a):
    """a plus everything it encloses (background not reachable from the border)."""
    outside = np.zeros_like(a)
    h, w = a.shape
    stack = [(y, x) for y in range(h) for x in (0, w - 1)] + [(y, x) for x in range(w) for y in (0, h - 1)]
    while stack:
        y, x = stack.pop()
        if 0 <= y < h and 0 <= x < w and not a[y, x] and not outside[y, x]:
            outside[y, x] = True
            stack += [(y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)]
    return ~outside


def px(mm):
    return mm / MM_PER_UNIT / PX


def frame(grey, blue):
    filled = fill_holes(grey)
    band = filled & ~erode(filled, px(FRAME_MM))
    return band & ~dilate(blue, px(GAP_MM))


def to_svg(a):
    runs = []
    for y in range(a.shape[0]):
        row = np.concatenate([[False], a[y], [False]]).astype(int)
        d = np.diff(row)
        for x0, x1 in zip(np.where(d == 1)[0], np.where(d == -1)[0]):
            runs.append(f"M{x0 * PX:.2f} {y * PX:.2f}H{x1 * PX:.2f}V{(y + 1) * PX:.2f}H{x0 * PX:.2f}Z")
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{SVG_W:.2f}mm" height="{SVG_H:.2f}mm" '
            f'viewBox="0 0 {SVG_W:.2f} {SVG_H:.2f}">\n<path fill="#000" d="{" ".join(runs)}"/>\n</svg>\n')


def main():
    g = frame(load("logo_grey.svg"), load("logo_blue.svg"))
    (HERE / "logo_grey_na.svg").write_text(to_svg(g))
    print("logo_grey_na.svg:", int(g.sum()), "px")


if __name__ == "__main__":
    main()
