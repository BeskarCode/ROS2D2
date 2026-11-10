# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""Split the ROS2D2 logo (media/ros2d2-logo.png, the one on GitHub) into the inlays of the front.

    python -I hardware/caja_ros2/logo/gen_logo.py

The PNG is drawn with partial transparency (the grey frame is black at ~65 % alpha), so it is
first laid over white. Every pixel then becomes white (the panel itself), navy ("ROS"), blue
("2D2" and the 12 dots) or grey (the frame round the dots: only there, so the anti-aliased edges
of the letters do not turn grey). The tagline "R2-D2 COME TO LIFE" is ~1 mm tall at this size,
too small for a 0.4 nozzle: it is left out. Strokes thinner than 0.8 mm are thickened (into
white) or given to the colour around them, then logo_marino/azul/gris.svg are written in mm.
"""
import pathlib
import sys

import numpy as np
from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
PNG = HERE.parents[2] / "media" / "ros2d2-logo.png"
WIDTH_MM = 92.0
MIN_MM = 0.8
COLOURS = ["marino", "azul", "gris"]                  # classes 1, 2, 3 (0 = white panel)
NAVY, BLUE, GREY = 1, 2, 3
FRAME_X = 0.225          # the dot panel's frame ends at this fraction of the width
TAGLINE = (0.83, 0.6)    # tagline: below this fraction of the height, right of this of the width


def over_white(rgba):
    a = rgba[..., 3:4].astype(float) / 255
    return rgba[..., :3].astype(float) * a + 255 * (1 - a)


def classify(rgba, frame_cols=None):
    """0 white, 1 navy, 2 blue, 3 grey (grey only in columns < frame_cols)."""
    c = over_white(rgba)
    r, g, b = c[..., 0], c[..., 1], c[..., 2]
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    k = np.zeros(rgba.shape[:2], np.uint8)
    blue = (b > 110) & (b - r > 60)
    navy = ~blue & (lum < 75)
    grey = ~blue & ~navy & (np.max(c, -1) - np.min(c, -1) < 40) & (lum < 200)
    if frame_cols is not None:
        cols = np.arange(rgba.shape[1])[None, :]
        grey &= cols < frame_cols
    k[navy] = NAVY
    k[blue] = BLUE
    k[grey] = GREY
    return k


def load_png(px_mm=0.1, path=PNG, width_mm=WIDTH_MM):
    im = Image.open(path).convert("RGBA")
    w = round(width_mm / px_mm)
    h = round(im.height * w / im.width)
    a = np.array(im.resize((w, h), Image.LANCZOS))
    a[int(h * TAGLINE[0]):, int(w * TAGLINE[1]):, 3] = 0          # drop the tagline
    return a


# --- morphology on boolean masks -------------------------------------------------------------
def _label(mask):
    """4-connected islands: (labels, count). Union-find over row runs."""
    h, w = mask.shape
    labels = np.zeros((h, w), np.int32)
    parent = [0]

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    prev = []
    for y in range(h):
        row = np.concatenate([[False], mask[y], [False]])
        edges = np.flatnonzero(row[1:] != row[:-1])
        runs = []
        for x0, x1 in zip(edges[::2], edges[1::2]):
            lab = len(parent)
            parent.append(lab)
            for (p0, p1, pl) in prev:
                if p0 < x1 and p1 > x0:
                    a, b = find(lab), find(pl)
                    if a != b:
                        parent[max(a, b)] = min(a, b)
            runs.append((x0, x1, lab))
        for (x0, x1, lab) in runs:
            labels[y, x0:x1] = lab
        prev = runs
    roots = np.array([find(i) for i in range(len(parent))], np.int32)
    _, compact = np.unique(roots, return_inverse=True)
    return compact[labels].astype(np.int32), int(compact.max())


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
    labels, _ = _label(thin)
    sizes = np.bincount(labels.ravel())
    sizes[0] = 0
    return (sizes > keep_px)[labels], int(sizes.max())


def thin_parts(m, px_mm=0.1, min_mm=MIN_MM):
    """Size (px) of the largest cluster thinner than min_mm."""
    return _thin_clusters(m, px_mm, min_mm)[1]


def island_thickness_mm(mask, px_mm):
    labels, n = _label(mask)
    survived = np.zeros(n + 1, int)
    m = mask.copy()
    k = 0
    four = [(0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)]
    while m.any():
        k += 1
        survived[np.unique(labels[m])] = k
        m = _shift_all(m, four, np.logical_and)
    return labels, survived[1:] * 2 * px_mm


def min_feature_mm(mask, px_mm=0.1):
    _, t = island_thickness_mm(mask, px_mm)
    return float(t.min()) if len(t) else float("inf")


def clean(mask, px_mm=0.1, min_mm=MIN_MM):
    """Drop islands too small to print."""
    labels, t = island_thickness_mm(mask, px_mm)
    return np.concatenate([[False], t >= min_mm])[labels] & mask


def thicken(ms, px_mm=0.1, min_mm=MIN_MM):
    """Thin strokes grow into white; what still cannot grow goes to the colour around it."""
    ms = [m.copy() for m in ms]
    grow = _disk(0.5, px_mm)
    for _ in range(8):
        thin = [_thin_clusters(m, px_mm, min_mm)[0] for m in ms]
        if not any(t.any() for t in thin):
            return ms
        white = ~np.logical_or.reduce(ms)
        for i, t in enumerate(thin):
            ms[i] |= _shift_all(t, grow, np.logical_or) & white
            white &= ~ms[i]
    # still thin (e.g. rings inside the dots): give those pixels to the neighbour with most contact
    near = _disk(0.6, px_mm)
    for i in range(len(ms)):
        t = _thin_clusters(ms[i], px_mm, min_mm)[0]
        if not t.any():
            continue
        ms[i] &= ~t
        counts = [(_shift_all(m, near, np.logical_or) & t) for m in ms]
        for y, x in zip(*np.nonzero(t)):
            best = max(range(len(ms)), key=lambda j: counts[j][y, x] and j != i)
            if counts[best][y, x] and best != i:
                ms[best][y, x] = True
    return ms


def _pinch_sites(m):
    a, b, c, d = m[:-1, :-1], m[:-1, 1:], m[1:, :-1], m[1:, 1:]
    return (a & d & ~b & ~c), (b & c & ~a & ~d)


def fix_pinches(m):
    """Fill one pixel of every corner-only contact so the extruded mesh stays closed."""
    m = m.copy()
    for _ in range(50):
        p1, p2 = _pinch_sites(m)
        if not (p1.any() or p2.any()):
            return m
        m[:-1, 1:] |= p1
        m[:-1, :-1] |= p2
    raise RuntimeError("pinches do not converge")


def masks(px_mm=0.1, png=PNG, width_mm=WIDTH_MM):
    """[navy, blue, grey]: disjoint, printable, no corner-only contacts in each or in all of them."""
    rgba = load_png(px_mm, png, width_mm)
    fx = int(rgba.shape[1] * FRAME_X)
    k = classify(rgba, frame_cols=fx)
    # the 12 dots print as plain blue discs: small non-blue specks inside the dot panel turn blue
    # (the white between the dots is one big area and stays)
    inner = np.zeros_like(k, bool)
    inner[:, :fx] = (k[:, :fx] != BLUE) & (k[:, :fx] != GREY)
    labels, _ = _label(inner)
    sizes = np.bincount(labels.ravel())
    sizes[0] = 0
    k[(sizes < 400)[labels] & inner] = BLUE
    ms = thicken([clean(k == c, px_mm) for c in (NAVY, BLUE, GREY)], px_mm)
    for _ in range(50):
        taken = np.zeros_like(ms[0])
        for i in range(len(ms)):
            ms[i] = fix_pinches(ms[i]) & ~taken
            taken |= ms[i]
        p1, p2 = _pinch_sites(taken)
        if not (p1.any() or p2.any()) and all(not any(x.any() for x in _pinch_sites(m)) for m in ms):
            return ms
        # close the union's pinches with the colour of the pixel that made them
        for i in range(len(ms)):
            src = np.zeros_like(taken)
            src[:-1, 1:] |= p1 & ms[i][:-1, :-1]
            src[:-1, :-1] |= p2 & ms[i][:-1, 1:]
            ms[i] |= src
    raise RuntimeError("inlay pinches do not converge")


def mask_to_svg(mask, px_mm, path):
    """One <path> of rectangles: runs per row, merged downwards while they repeat."""
    h, w = mask.shape
    open_rects, rects = {}, []
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
    for name, m in zip(COLOURS, masks(px_mm, png, width_mm)):
        n = mask_to_svg(m, px_mm, pathlib.Path(out_dir) / f"logo_{name}.svg")
        print(f"logo_{name}.svg: {n} rectangles, {m.sum()} px")
    for old in ("negro",):
        (pathlib.Path(out_dir) / f"logo_{old}.svg").unlink(missing_ok=True)


if __name__ == "__main__":
    main(*sys.argv[1:2])
