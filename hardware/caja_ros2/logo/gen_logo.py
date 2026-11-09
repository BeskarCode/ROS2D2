# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""Split the ROS2D2 horizontal logo into the black and the blue inlay of the front panel.

    python -I hardware/caja_ros2/logo/gen_logo.py

Reads ROS2D2/docs/logo-horizontal.png, scales it to 80 mm wide at 0.1 mm per pixel, gives every
pixel the nearest of white / black / blue, drops islands thinner than 0.8 mm (a 0.4 nozzle
cannot print them) and writes logo_negro.svg and logo_azul.svg in mm. White is the panel itself.
"""
import pathlib
import sys

import numpy as np
from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
PNG = HERE.parents[2] / "docs" / "logo-horizontal.png"
WIDTH_MM = 80.0
MIN_MM = 0.8
PALETTE = np.array([[250, 250, 250], [5, 5, 20], [10, 55, 145]], float)   # 0 white, 1 black, 2 blue


def classify(rgba):
    """0 background / white / transparent, 1 black, 2 blue."""
    rgb = rgba[..., :3].astype(float)
    d = ((rgb[..., None, :] - PALETTE) ** 2).sum(-1)
    k = d.argmin(-1).astype(np.uint8)
    k[rgba[..., 3] < 128] = 0
    return k


def load_png(px_mm=0.1, path=PNG, width_mm=WIDTH_MM):
    im = Image.open(path).convert("RGBA")
    w = round(width_mm / px_mm)
    h = round(im.height * w / im.width)
    return np.array(im.resize((w, h), Image.LANCZOS))


def _label(mask):
    """4-connected islands: (labels, count). Plain union-find over row runs."""
    h, w = mask.shape
    labels = np.zeros((h, w), np.int32)
    parent = [0]

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    prev = []
    for y in range(h):
        row = mask[y]
        runs = []
        x = 0
        while x < w:
            if row[x]:
                x0 = x
                while x < w and row[x]:
                    x += 1
                lab = len(parent)
                parent.append(lab)
                for (p0, p1, pl) in prev:
                    if p0 < x and p1 > x0:
                        a, b = find(lab), find(pl)
                        if a != b:
                            parent[max(a, b)] = min(a, b)
                runs.append((x0, x, lab))
            else:
                x += 1
        for (x0, x1, lab) in runs:
            labels[y, x0:x1] = lab
        prev = runs
    roots = np.array([find(i) for i in range(len(parent))], np.int32)
    uniq, compact = np.unique(roots, return_inverse=True)
    return compact[labels].astype(np.int32), len(uniq) - 1


def _erode(m):
    e = m.copy()
    e[1:] &= m[:-1]; e[:-1] &= m[1:]; e[:, 1:] &= m[:, :-1]; e[:, :-1] &= m[:, 1:]
    e[0] = e[-1] = False; e[:, 0] = e[:, -1] = False
    return e


def island_thickness_mm(mask, px_mm):
    """Thickest part of each island (mm): twice the number of erosions it survives."""
    labels, n = _label(mask)
    survived = np.zeros(n + 1, int)
    m = mask.copy()
    k = 0
    while m.any():
        k += 1
        present = np.unique(labels[m])
        survived[present] = k
        m = _erode(m)
    return labels, survived[1:] * 2 * px_mm


def min_feature_mm(mask, px_mm=0.1):
    _, t = island_thickness_mm(mask, px_mm)
    return float(t.min()) if len(t) else float("inf")


def clean(mask, px_mm=0.1, min_mm=MIN_MM):
    labels, t = island_thickness_mm(mask, px_mm)
    keep = np.concatenate([[False], t >= min_mm])
    return keep[labels] & mask


def mask_to_svg(mask, px_mm, path):
    """One <path> of rectangles: runs per row, merged downwards while they repeat."""
    h, w = mask.shape
    open_rects = {}          # (x0, x1) -> y0
    rects = []
    for y in range(h + 1):
        runs = set()
        if y < h:
            row = np.concatenate([[False], mask[y], [False]])
            edges = np.flatnonzero(row[1:] != row[:-1])
            runs = set(zip(edges[::2], edges[1::2]))
        for r in list(open_rects):
            if r not in runs:
                rects.append((r[0], open_rects.pop(r), r[1], y))
        for r in runs:
            open_rects.setdefault(r, y)
    d = " ".join(f"M{x0 * px_mm:.2f} {y0 * px_mm:.2f}H{x1 * px_mm:.2f}V{y1 * px_mm:.2f}H{x0 * px_mm:.2f}Z"
                 for x0, y0, x1, y1 in rects)
    W, H = w * px_mm, h * px_mm
    pathlib.Path(path).write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.2f}mm" height="{H:.2f}mm" '
        f'viewBox="0 0 {W:.2f} {H:.2f}">\n<path fill="#000" d="{d}"/>\n</svg>\n', encoding="utf8")
    return len(rects)


def main(png=PNG, out_dir=HERE, width_mm=WIDTH_MM, px_mm=0.1):
    k = classify(load_png(px_mm, png, width_mm))
    for name, v in (("negro", 1), ("azul", 2)):
        n = mask_to_svg(clean(k == v, px_mm), px_mm, pathlib.Path(out_dir) / f"logo_{name}.svg")
        print(f"logo_{name}.svg: {n} rectangles")


if __name__ == "__main__":
    main(*sys.argv[1:2])
