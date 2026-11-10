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


def _disk(min_mm, px_mm):
    r = min_mm / (2 * px_mm) - 0.5
    ri = int(np.ceil(r))
    return [(dy, dx) for dy in range(-ri, ri + 1) for dx in range(-ri, ri + 1) if dy * dy + dx * dx <= r * r]


def _shift_all(m, offs, combine):
    h, w = m.shape
    p = max(max(abs(a), abs(b)) for a, b in offs)
    pad = np.pad(m, p, constant_values=False)
    out = None
    for dy, dx in offs:
        s = pad[p + dy:p + dy + h, p + dx:p + dx + w]
        out = s.copy() if out is None else combine(out, s)
    return out


def opening(m, min_mm, px_mm):
    """Morphological opening with a disk of diameter min_mm: what a min_mm pen could draw."""
    offs = _disk(min_mm, px_mm)
    return _shift_all(_shift_all(m, offs, np.logical_and), offs, np.logical_or)


def _thin_clusters(m, px_mm, min_mm, keep_px=20):
    """Pixels a min_mm pen cannot reach, in clusters bigger than keep_px (corners stay)."""
    thin = m & ~opening(m, min_mm, px_mm)
    if not thin.any():
        return thin, 0
    labels, n = _label(thin)
    sizes = np.bincount(labels.ravel())
    sizes[0] = 0
    big = sizes > keep_px
    return big[labels], int(sizes.max())


def thin_parts(m, px_mm=0.1, min_mm=MIN_MM):
    """Size (px) of the largest cluster thinner than min_mm."""
    return _thin_clusters(m, px_mm, min_mm)[1]


def thicken(neg, azu, px_mm=0.1, min_mm=MIN_MM):
    """Thin blue goes black; thin black grows (into white first, then blue) until a 0.8 mm pen fits."""
    grow = _disk(0.5, px_mm)
    for _ in range(8):
        tb, _ = _thin_clusters(azu, px_mm, min_mm)
        neg = neg | tb
        azu = azu & ~tb
        tk, _ = _thin_clusters(neg, px_mm, min_mm)
        if not tk.any() and not _thin_clusters(azu, px_mm, min_mm)[0].any():
            return neg, azu
        neg = neg | _shift_all(tk, grow, np.logical_or)
        azu = azu & ~neg
    return neg, azu


def _pinch_sites(m):
    """2x2 blocks touching only at a corner: (rows, cols, which) — which 0: a&d, 1: b&c."""
    a, b, c, d = m[:-1, :-1], m[:-1, 1:], m[1:, :-1], m[1:, 1:]
    return (a & d & ~b & ~c), (b & c & ~a & ~d)


def fix_pinches(m):
    """Fill one pixel of every corner-only contact so the extruded mesh stays closed."""
    m = m.copy()
    for _ in range(50):
        p1, p2 = _pinch_sites(m)
        if not (p1.any() or p2.any()):
            return m
        m[:-1, 1:] |= p1          # a&d -> fill b
        m[:-1, :-1] |= p2         # b&c -> fill a
    raise RuntimeError("pinches do not converge")


def masks(px_mm=0.1, png=PNG, width_mm=WIDTH_MM):
    """Black and blue inlays: clean, disjoint, no corner-only contacts in either or in both."""
    k = classify(load_png(px_mm, png, width_mm))
    neg, azu = thicken(clean(k == 1, px_mm), clean(k == 2, px_mm) & ~clean(k == 1, px_mm), px_mm)
    neg = fix_pinches(neg)
    azu = azu & ~neg
    for _ in range(50):
        azu = fix_pinches(azu) & ~neg
        both = neg | azu
        p1, p2 = _pinch_sites(both)
        if not (p1.any() or p2.any()) and not _pinch_sites(azu)[0].any() and not _pinch_sites(azu)[1].any():
            return neg, azu
        # close the union's pinch with the colour of the pixel that made it
        fill_b = np.zeros_like(neg); fill_b[:-1, 1:] = p1
        fill_a = np.zeros_like(neg); fill_a[:-1, :-1] = p2
        src_b = np.zeros_like(neg); src_b[:-1, 1:] = p1 & neg[:-1, :-1]
        src_a = np.zeros_like(neg); src_a[:-1, :-1] = p2 & neg[:-1, 1:]
        neg = fix_pinches(neg | src_b | src_a)
        azu = azu | ((fill_b | fill_a) & ~neg)
    raise RuntimeError("inlay pinches do not converge")


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
    for name, m in zip(("negro", "azul"), masks(px_mm, png, width_mm)):
        n = mask_to_svg(m, px_mm, pathlib.Path(out_dir) / f"logo_{name}.svg")
        print(f"logo_{name}.svg: {n} rectangles")


if __name__ == "__main__":
    main(*sys.argv[1:2])
