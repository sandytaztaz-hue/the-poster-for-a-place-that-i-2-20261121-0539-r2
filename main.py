#!/usr/bin/env python3
"""ONDARA -- "The Falls That Rise".

A travel poster for a place that isn't there. Pure Python 3 stdlib
(no PIL, no numpy, no network, no external assets or fonts).

The poster: a coastal cliff bay at sunset. The mega-landmark is a
waterfall that falls UP -- a wide column of sea-water rises from the
bay at the foot of a tall dark cliff, arcs into the sky and dissolves
into spray and cloud. The invented name ONDARA is set huge across the
top in a hand-authored display serif (every letter drawn as vector
polygons in this file); the tagline THE FALLS THAT RISE sits beneath
it. A tiny fishing town, sailboats, walkers and one rowing boat give
the human scale. Retro halftone dots + film grain over everything,
thin cream frame.

Writes /output/entry.png (or $MAKEFUN_OUTPUT_DIR/entry.png),
exactly 1024x1024, <= 1 MiB. Deterministic: fixed seed, two runs are
byte-identical.
"""

import hashlib
import math
import os
import random
import struct
import sys
import zlib

W = H = 1024
SEED = 20261121
OUT_DIR = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")

# ---------------------------------------------------------------- canvas

buf = [bytearray(W * 3) for _ in range(H)]


def _clamp(v):
    return 0 if v < 0 else (255 if v > 255 else v)


def set_px(x, y, c):
    if 0 <= x < W and 0 <= y < H:
        row = buf[y]
        i = x * 3
        row[i] = c[0]
        row[i + 1] = c[1]
        row[i + 2] = c[2]


def blend_px(x, y, c, a):
    """Blend colour c (r,g,b) over pixel (x,y) with alpha a (0..255)."""
    if a <= 0 or not (0 <= x < W and 0 <= y < H):
        return
    row = buf[y]
    i = x * 3
    if a >= 255:
        row[i] = c[0]
        row[i + 1] = c[1]
        row[i + 2] = c[2]
        return
    ia = 255 - a
    row[i] = (c[0] * a + row[i] * ia) // 255
    row[i + 1] = (c[1] * a + row[i + 1] * ia) // 255
    row[i + 2] = (c[2] * a + row[i + 2] * ia) // 255


def fill_rect(x0, y0, x1, y1, c, a=255):
    x0 = max(0, int(x0))
    y0 = max(0, int(y0))
    x1 = min(W, int(math.ceil(x1)))
    y1 = min(H, int(math.ceil(y1)))
    if x1 <= x0 or y1 <= y0:
        return
    if a >= 255:
        chunk = bytes(c) * (x1 - x0)
        for y in range(y0, y1):
            row = buf[y]
            row[x0 * 3:x1 * 3] = chunk
    else:
        for y in range(y0, y1):
            for x in range(x0, x1):
                blend_px(x, y, c, a)


def fill_row_span(y, x0, x1, c, a=255):
    """Fill a horizontal span on one row (float coords, clipped)."""
    if not (0 <= y < H):
        return
    ix0 = max(0, int(math.ceil(x0)))
    ix1 = min(W, int(math.floor(x1)))
    if ix1 <= ix0:
        return
    row = buf[y]
    if a >= 255:
        row[ix0 * 3:ix1 * 3] = bytes(c) * (ix1 - ix0)
    else:
        ia = 255 - a
        for x in range(ix0, ix1):
            i = x * 3
            row[i] = (c[0] * a + row[i] * ia) // 255
            row[i + 1] = (c[1] * a + row[i + 1] * ia) // 255
            row[i + 2] = (c[2] * a + row[i + 2] * ia) // 255


# ---------------------------------------------------------------- polygons

def spans_at_y(polys, y):
    """Non-zero winding spans at scanline y. polys = [(pts, is_hole)]."""
    ev = []
    for pts, hole in polys:
        n = len(pts)
        for i in range(n):
            x1, y1 = pts[i]
            x2, y2 = pts[(i + 1) % n]
            if y1 == y2:
                continue
            if min(y1, y2) <= y < max(y1, y2):
                t = (y - y1) / (y2 - y1)
                x = x1 + t * (x2 - x1)
                d = 1 if y2 > y1 else -1
                if hole:
                    d = -d
                ev.append((x, d))
    ev.sort(key=lambda e: e[0])
    spans = []
    wind = 0
    start = None
    for x, d in ev:
        if start is None and wind == 0:
            start = x
        wind += d
        if wind == 0 and start is not None:
            if x > start:
                spans.append((start, x))
            start = None
    return spans


def fill_polys(polys, c, a=255):
    ys = [p[1] for pts, _ in polys for p in pts]
    if not ys:
        return
    y0 = max(0, int(math.floor(min(ys))))
    y1 = min(H - 1, int(math.ceil(max(ys))))
    for y in range(y0, y1 + 1):
        for x0, x1 in spans_at_y(polys, y + 0.5):
            fill_row_span(y, x0, x1, c, a)


def fill_poly(pts, c, a=255):
    fill_polys([(pts, False)], c, a)


def fill_ellipse(cx, cy, rx, ry, c, a=255):
    if rx <= 0 or ry <= 0:
        return
    y0 = max(0, int(math.floor(cy - ry)))
    y1 = min(H - 1, int(math.ceil(cy + ry)))
    for y in range(y0, y1 + 1):
        t = (y + 0.5 - cy) / ry
        if abs(t) >= 1:
            continue
        dx = rx * math.sqrt(1.0 - t * t)
        fill_row_span(y, cx - dx, cx + dx, c, a)


def fill_circle(cx, cy, r, c, a=255):
    fill_ellipse(cx, cy, r, r, c, a)


def thick_line(x0, y0, x1, y1, w, c, a=255):
    dx, dy = x1 - x0, y1 - y0
    L = math.hypot(dx, dy) or 1.0
    nx, ny = -dy / L * w / 2.0, dx / L * w / 2.0
    fill_poly([(x0 + nx, y0 + ny), (x1 + nx, y1 + ny),
               (x1 - nx, y1 - ny), (x0 - nx, y0 - ny)], c, a)


# ---------------------------------------------------------------- gradients

def lerp_col(c0, c1, t):
    return (int(c0[0] + (c1[0] - c0[0]) * t),
            int(c0[1] + (c1[1] - c0[1]) * t),
            int(c0[2] + (c1[2] - c0[2]) * t))


def grad_color(stops, t):
    """stops = [(pos, (r,g,b)), ...] sorted by pos."""
    if t <= stops[0][0]:
        return stops[0][1]
    for i in range(1, len(stops)):
        if t <= stops[i][0]:
            p0, c0 = stops[i - 1]
            p1, c1 = stops[i]
            return lerp_col(c0, c1, (t - p0) / (p1 - p0))
    return stops[-1][1]


SKY_STOPS = [
    (0.00, (199, 104, 66)),    # terracotta top (cream name reads on it)
    (0.30, (224, 138, 90)),
    (0.55, (242, 165, 107)),   # peach
    (0.78, (248, 196, 142)),
    (1.00, (251, 227, 184)),   # pale cream at the horizon
]
SEA_STOPS = [
    (0.00, (46, 127, 123)),    # teal at the horizon
    (0.50, (31, 95, 102)),
    (1.00, (23, 69, 79)),      # deep teal at the bottom
]

FRAME = 24          # cream frame width
HORIZON = 700       # sea level


def paint_sky_and_sea():
    for y in range(FRAME, HORIZON):
        t = (y - FRAME) / (HORIZON - FRAME)
        col = grad_color(SKY_STOPS, t)
        row = buf[y]
        row[FRAME * 3:1000 * 3] = bytes(col) * (1000 - FRAME)
    for y in range(HORIZON, 1000):
        t = (y - HORIZON) / (1000 - HORIZON)
        col = grad_color(SEA_STOPS, t)
        row = buf[y]
        row[FRAME * 3:1000 * 3] = bytes(col) * (1000 - FRAME)


# ---------------------------------------------------------------- hand font

def _rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def _stem_left():
    return [('fill', _rect(0, 0, 2.2, 14)),
            ('fill', _rect(-0.9, 0, 3.1, 1.1)),
            ('fill', _rect(-0.9, 12.9, 3.1, 14))]


def _stem_right():
    return [('fill', _rect(9.8, 0, 12, 14)),
            ('fill', _rect(8.9, 0, 12.9, 1.1)),
            ('fill', _rect(8.9, 12.9, 12.9, 14))]


def stroke_outline(pts, w, closed=False):
    """Ribbon outline of a centreline polyline (miter-ish joins)."""
    n = len(pts)

    def _norm(p, q):
        dx, dy = q[0] - p[0], q[1] - p[1]
        L = math.hypot(dx, dy) or 1.0
        return (-dy / L, dx / L)

    left, right = [], []
    for i in range(n):
        if closed:
            p_prev, p, p_next = pts[i - 1], pts[i], pts[(i + 1) % n]
        else:
            p_prev = pts[i - 1] if i > 0 else pts[i]
            p = pts[i]
            p_next = pts[i + 1] if i < n - 1 else pts[i]
        n1 = _norm(p_prev, p)
        n2 = _norm(p, p_next)
        nx, ny = n1[0] + n2[0], n1[1] + n2[1]
        L = math.hypot(nx, ny) or 1.0
        nx, ny = nx / L, ny / L
        left.append((p[0] + nx * w / 2.0, p[1] + ny * w / 2.0))
        right.append((p[0] - nx * w / 2.0, p[1] - ny * w / 2.0))
    if closed:
        return left + right[::-1]
    # square caps: extend the end offsets along the end directions
    d0 = _norm(pts[0], pts[1])
    d1 = _norm(pts[-2], pts[-1])
    cap_a = (left[0][0] - d0[0] * w / 2.0, left[0][1] - d0[1] * w / 2.0)
    cap_b = (right[0][0] - d0[0] * w / 2.0, right[0][1] - d0[1] * w / 2.0)
    cap_c = (right[-1][0] + d1[0] * w / 2.0, right[-1][1] + d1[1] * w / 2.0)
    cap_d = (left[-1][0] + d1[0] * w / 2.0, left[-1][1] + d1[1] * w / 2.0)
    return [cap_a] + left + [cap_d, cap_c] + right[::-1] + [cap_b]


def _ellipse_poly(cx, cy, rx, ry, n=28):
    return [(cx + rx * math.cos(2.0 * math.pi * i / n),
             cy + ry * math.sin(2.0 * math.pi * i / n)) for i in range(n)]


_OCT = None  # (kept out: a pointed octagon reads as "C" at poster size)
_S = [(9.6, 2.0), (7.2, 0.9), (4.2, 0.9), (2.5, 2.4), (2.5, 4.8),
      (4.2, 6.5), (7.8, 7.5), (9.7, 9.3), (9.7, 11.7), (7.9, 13.1),
      (4.6, 13.1), (2.7, 12.0)]

# Each glyph: list of (kind, polygon) in a 12 x 14 unit grid.
# kind 'fill' adds winding, 'hole' subtracts it (counters).
GLYPHS = {
    'O': [('fill', _ellipse_poly(6.0, 7.0, 6.0, 7.0)),
          ('hole', _ellipse_poly(6.0, 7.0, 3.5, 4.4))],
    'N': _stem_left() + _stem_right() + [
        ('fill', [(2.2, 1.2), (4.3, 1.2), (9.8, 12.8), (7.7, 12.8)])],
    'D': _stem_left() + [
        ('fill', [(2.2, 0), (7.6, 0), (10.4, 1.9), (12, 4.6), (12, 9.4),
                  (10.4, 12.1), (7.6, 14), (2.2, 14)]),
        ('hole', [(4.4, 2.4), (7.2, 2.4), (8.9, 3.9), (9.6, 5.6),
                  (9.6, 8.4), (8.9, 10.1), (7.2, 11.6), (4.4, 11.6)])],
    'A': [('fill', [(0, 14), (4.5, 0), (7.5, 0), (12, 14), (9.5, 14),
                    (8.1, 10.6), (3.9, 10.6), (2.5, 14)]),
          ('hole', [(6, 3.4), (7.8, 9.0), (4.2, 9.0)])],
    'R': _stem_left() + [
        ('fill', [(2.2, 0), (7.0, 0), (9.7, 1.5), (10.6, 3.5), (10.6, 5.2),
                  (9.7, 6.9), (7.0, 8.0), (2.2, 8.0)]),
        ('hole', [(4.4, 2.2), (6.6, 2.2), (8.0, 3.3), (8.4, 4.5),
                  (8.0, 5.7), (6.6, 6.4), (4.4, 6.4)]),
        ('fill', [(7.2, 6.6), (9.8, 6.6), (12, 14), (9.6, 14),
                  (7.6, 9.4), (6.4, 8.4)])],
    'T': [('fill', _rect(0, 0, 12, 1.7)),
          ('fill', _rect(0, 1.7, 1.1, 2.8)),
          ('fill', _rect(10.9, 1.7, 12, 2.8)),
          ('fill', _rect(5, 1.7, 7, 14)),
          ('fill', _rect(4.1, 12.9, 7.9, 14))],
    'H': _stem_left() + _stem_right() + [
        ('fill', _rect(2.2, 6.2, 9.8, 7.8))],
    'E': _stem_left() + [
        ('fill', _rect(2.2, 0, 10.9, 1.6)),
        ('fill', _rect(2.2, 6.2, 9.2, 7.8)),
        ('fill', _rect(2.2, 12.4, 10.9, 14))],
    'F': _stem_left() + [
        ('fill', _rect(2.2, 0, 10.9, 1.6)),
        ('fill', _rect(2.2, 6.2, 9.2, 7.8))],
    'L': _stem_left() + [
        ('fill', _rect(2.2, 12.4, 11.4, 14))],
    'I': [('fill', _rect(5, 0, 7, 14)),
          ('fill', _rect(3.9, 0, 8.1, 1.1)),
          ('fill', _rect(3.9, 12.9, 8.1, 14))],
    'S': [('fill', stroke_outline(_S, 2.4, closed=False))],
}

SS = 4  # text supersampling


def draw_glyph(ch, ox, oy, scale, color, alpha=255):
    """Draw one glyph with top-left at (ox, oy) in canvas px."""
    polys = []
    for kind, pts in GLYPHS[ch]:
        polys.append(([(ox + x * scale, oy + y * scale) for x, y in pts],
                      kind == 'hole'))
    xs = [p[0] for pts, _ in polys for p in pts]
    ys = [p[1] for pts, _ in polys for p in pts]
    bx0 = max(0, int(math.floor(min(xs))) - 1)
    by0 = max(0, int(math.floor(min(ys))) - 1)
    bx1 = min(W, int(math.ceil(max(xs))) + 1)
    by1 = min(H, int(math.ceil(max(ys))) + 1)
    gw = bx1 - bx0
    gh = by1 - by0
    if gw <= 0 or gh <= 0:
        return
    cov = bytearray(gw * gh)
    for sy in range(gh * SS):
        y_sub = by0 + (sy + 0.5) / SS
        row = sy // SS
        for x0, x1 in spans_at_y(polys, y_sub):
            i0 = int((x0 - bx0) * SS)
            i1 = int(math.ceil((x1 - bx0) * SS))
            i0 = max(0, i0)
            i1 = min(gw * SS, i1)
            base = row * gw
            for i in range(i0, i1):
                cov[base + i // SS] += 1
    for py in range(gh):
        y = by0 + py
        row = buf[y]
        for px in range(gw):
            c = cov[py * gw + px]
            if c:
                a = (c * alpha) // 16
                if a:
                    x = bx0 + px
                    i = x * 3
                    if a >= 255:
                        row[i] = color[0]
                        row[i + 1] = color[1]
                        row[i + 2] = color[2]
                    else:
                        ia = 255 - a
                        row[i] = (color[0] * a + row[i] * ia) // 255
                        row[i + 1] = (color[1] * a + row[i + 1] * ia) // 255
                        row[i + 2] = (color[2] * a + row[i + 2] * ia) // 255


def draw_text(text, x_center, y_top, cap_h, tracking, color,
              shadow=None, shadow_off=(5, 6)):
    """Letterspaced caps text, centred on x_center."""
    scale = cap_h / 14.0
    advs = []
    for ch in text:
        advs.append(6.0 if ch == ' ' else 12.0)
    total = (sum(advs) + tracking * (len(text) - 1)) * scale
    x = x_center - total / 2.0
    for ch, adv in zip(text, advs):
        if ch != ' ':
            if shadow is not None:
                draw_glyph(ch, x + shadow_off[0], y_top + shadow_off[1],
                           scale, shadow, alpha=95)
            draw_glyph(ch, x, y_top, scale, color)
        x += (adv + tracking) * scale

# ---------------------------------------------------------------- scene

CREAM = (255, 243, 220)   # name / frame
CREAM_DK = (247, 232, 200)
INK_SHADOW = (107, 58, 31)
SLATE = (46, 58, 68)      # cliff
SLATE_LT = (84, 100, 114)
GOLD = (255, 196, 107)    # lit windows / glitter
SUN_CORE = (255, 223, 158)
SUN_MID = (247, 158, 60)
SUN_EDGE = (240, 125, 46)


def draw_sun(rng):
    cx, cy, r = 718, 612, 82
    for rr, col, a in ((205, (247, 158, 60), 14),
                       (180, (247, 158, 60), 18),
                       (155, (247, 158, 60), 22),
                       (132, (248, 168, 72), 30),
                       (114, (250, 178, 84), 44),
                       (100, (251, 190, 96), 62)):
        fill_circle(cx, cy, rr, col, a)
    for y in range(cy - r, cy + r + 1):
        t = (y + 0.5 - cy) / r
        if abs(t) >= 1:
            continue
        dx = r * math.sqrt(1.0 - t * t)
        tt = abs(t)
        col = lerp_col(SUN_MID, SUN_CORE, max(0.0, 1.0 - tt * 1.6))
        if tt > 0.86:
            col = lerp_col(col, SUN_EDGE, (tt - 0.86) / 0.14)
        fill_row_span(y, cx - dx, cx + dx, col)


def draw_cloud(cx, cy, w, h, col, a, rng):
    # soft band made of overlapping ellipses
    for dx, dw, dh in ((-0.36, 0.42, 0.62), (0.0, 0.56, 1.0),
                       (0.38, 0.40, 0.58), (-0.62, 0.24, 0.45),
                       (0.64, 0.22, 0.42)):
        fill_ellipse(cx + dx * w, cy, dw * w, dh * h, col, a)


def draw_cliff(rng):
    pts = [(24, 470), (140, 398), (245, 418), (330, 468), (356, 700),
           (24, 700)]
    fill_poly(pts, (54, 68, 80))
    # sunlit top edge
    for (x0, y0), (x1, y1) in zip(pts, pts[1:4]):
        thick_line(x0, y0, x1, y1, 4, (244, 180, 120), 150)
    # warm rim light on the cliff's sun-facing right edge
    thick_line(330, 468, 356, 700, 5, (248, 190, 130), 110)
    # strata: short light dashes across the face
    for y in range(486, 692, 15):
        xr = 330 + (y - 468) * (26.0 / 232.0)
        x = 30
        while x < xr - 14:
            ln = 8 + rng.randint(0, 10)
            fill_rect(x, y, min(x + ln, xr - 6), y + 2, (104, 122, 138), 110)
            x += ln + 12 + rng.randint(0, 10)
    # pale rock facets
    for _ in range(9):
        x = rng.randint(36, 300)
        y = rng.randint(470, 660)
        s = rng.randint(10, 26)
        fill_poly([(x, y), (x + s, y + s // 3), (x + s // 2, y + s // 2)],
                  SLATE_LT, 80)
    # bushes on the crest
    for x, y in ((70, 452), (120, 418), (180, 408), (235, 424), (300, 452)):
        for dx, dy, r in ((0, 0, 7), (6, 3, 5), (-6, 3, 5)):
            fill_circle(x + dx, y + dy, r, (38, 74, 60), 200)
    # cliff path + walkers
    path = [(92, 692), (150, 620), (205, 560), (255, 505), (300, 470)]
    for (x0, y0), (x1, y1) in zip(path, path[1:]):
        thick_line(x0, y0, x1, y1, 3, (232, 196, 150), 170)
    for x, y, col in ((150, 620, (240, 120, 80)), (205, 560, (90, 170, 160)),
                      (255, 505, (240, 200, 90))):
        fill_rect(x - 1, y - 7, x + 2, y - 1, col)      # body
        fill_circle(x, y - 9, 2, (40, 34, 28))          # head


# The rising falls: control points (y, centre-x, half-width).
_FALLS = [(700, 398, 50), (620, 392, 46), (540, 380, 42),
          (460, 364, 38), (400, 348, 33), (350, 336, 29)]


def _falls_cx_hw(y):
    for (y0, x0, w0), (y1, x1, w1) in zip(_FALLS, _FALLS[1:]):
        if y0 >= y >= y1:
            t = (y0 - y) / (y0 - y1)
            t = t * t * (3 - 2 * t)
            return x0 + (x1 - x0) * t, w0 + (w1 - w0) * t
    return _FALLS[-1][1], _FALLS[-1][2]


def draw_falls(rng):
    # base foam rings in the bay
    for rx, ry, a in ((132, 26, 34), (100, 20, 55), (72, 14, 80)):
        fill_ellipse(398, 702, rx, ry, (240, 248, 242), a)
    # splash fan where the water leaves the sea, rising
    for _ in range(30):
        t = rng.random()
        x = 398 + (rng.random() - 0.5) * 130 * (0.4 + t)
        y = 700 - t * 46
        fill_circle(x, y, 1 + rng.random() * 1.6, (255, 255, 250),
                    130 + rng.randint(0, 90))
    # the rising column, row by row
    for y in range(350, 701):
        cx, hw = _falls_cx_hw(y)
        # teal edges -> pale core
        fill_row_span(y, cx - hw, cx + hw, (90, 175, 170))
        fill_row_span(y, cx - hw * 0.62, cx + hw * 0.62, (178, 222, 210))
        fill_row_span(y, cx - hw * 0.30, cx + hw * 0.30, (232, 245, 238))
        # darker teal outline so the column reads against the pale sky
        for ex in (cx - hw, cx + hw):
            fill_row_span(y, ex - 1, ex + 1, (30, 95, 105), 200)
    # upward foam streaks inside the column
    for f in (-0.7, -0.35, 0.0, 0.35, 0.7):
        for y in range(360, 696, 3):
            if (y * 7 + int(f * 100)) % 11 < 6:
                cx, hw = _falls_cx_hw(y)
                x = cx + f * hw + 5 * math.sin(y / 19.0 + f * 7.0)
                fill_rect(int(x) - 1, y, int(x) + 1, y + 2,
                          (255, 255, 250), 170)
    # droplets streaking upward
    for _ in range(46):
        y = rng.randint(380, 680)
        cx, hw = _falls_cx_hw(y)
        x = cx + rng.uniform(-0.8, 0.8) * hw
        fill_rect(int(x), y - 3, int(x) + 2, y, (255, 255, 250), 150)
    # spray burst + mist where the column dissolves into cloud
    for _ in range(170):
        t = rng.random()
        y = 350 - t * 112
        spread = 18 + t * 74
        x = 336 + (rng.random() - 0.5) * 2 * spread
        r = 1 + rng.random() * 1.8
        fill_circle(x, y, r, (255, 253, 246), 120 + rng.randint(0, 100))
    for (mx, my, mr) in ((300, 300, 34), (352, 288, 40), (392, 306, 30),
                         (268, 318, 26), (330, 262, 30), (376, 262, 24)):
        fill_circle(mx, my, mr, (244, 236, 222), 46)
    # reflection of the falls in the bay
    for _ in range(22):
        x = rng.randint(356, 440)
        y0 = 706 + rng.randint(0, 40)
        ln = rng.randint(14, 60)
        fill_rect(x, y0, x + 2, y0 + ln, (220, 240, 232),
                  28 + rng.randint(0, 34))


def draw_sea_detail(rng):
    # sun glitter path under the sun
    for _ in range(260):
        x = 640 + rng.random() * 170
        y = 706 + rng.random() * 284
        ln = 6 + rng.random() * 30
        fill_rect(int(x - ln / 2), int(y), int(x + ln / 2), int(y) + 2,
                  (255, 190, 90), 40 + rng.randint(0, 110))
    # wave dashes
    for _ in range(190):
        x = rng.randint(30, 990)
        y = rng.randint(710, 990)
        ln = 8 + rng.randint(0, 26)
        fill_rect(x, y, x + ln, y + 1, (130, 200, 190), 30 + rng.randint(0, 50))
    # birds
    for bx, by in ((600, 250), (652, 282), (580, 312), (722, 240),
                   (764, 302), (690, 336)):
        thick_line(bx - 6, by, bx, by - 4, 2, (60, 50, 44), 170)
        thick_line(bx, by - 4, bx + 6, by, 2, (60, 50, 44), 170)


def draw_town(rng):
    # sandy shore strip at the cliff foot
    fill_poly([(24, 700), (620, 700), (600, 712), (24, 712)],
              (238, 205, 160))
    walls = [(247, 232, 200), (238, 180, 130), (214, 120, 80),
             (200, 90, 70), (232, 210, 170)]
    x = 44
    while x < 545:
        w = rng.randint(16, 30)
        h = rng.randint(13, 22)
        yb = 700 + rng.randint(0, 8)
        wall = walls[rng.randrange(len(walls))]
        fill_rect(x, yb - h, x + w, yb, wall)
        roof = (40, 50, 60) if rng.random() < 0.6 else (176, 92, 52)
        fill_poly([(x - 1, yb - h), (x + w // 2, yb - h - 7),
                   (x + w + 1, yb - h)], roof)
        nw = 1 if w < 22 else 2
        for i in range(nw):
            wx = x + 3 + i * (w - 8)
            fill_rect(wx, yb - h + 5, wx + 3, yb - h + 9, GOLD, 235)
        x += w + rng.randint(2, 9)
    # two cottages on the cliff ledge
    for cx, cy, s in ((150, 468, 0.7), (228, 452, 0.6)):
        w, h = int(24 * s), int(16 * s)
        fill_rect(cx, cy - h, cx + w, cy, (247, 232, 200))
        fill_poly([(cx - 1, cy - h), (cx + w // 2, cy - h - 6),
                   (cx + w + 1, cy - h)], (40, 50, 60))
        fill_rect(cx + 4, cy - h + 4, cx + 7, cy - h + 8, GOLD, 235)
    # pier
    for px in range(520, 566, 9):
        fill_rect(px, 700, px + 3, 726, (70, 52, 38))
    fill_rect(516, 700, 570, 705, (120, 92, 62))


def draw_boat(x, y, s, rng, sail_col=(250, 244, 226)):
    fill_poly([(x - 13 * s, y), (x + 13 * s, y), (x + 8 * s, y + 6 * s),
               (x - 8 * s, y + 6 * s)], (52, 44, 38))
    thick_line(x, y - 22 * s, x, y, 2, (52, 44, 38))
    fill_poly([(x + 1, y - 21 * s), (x + 1, y - 2), (x + 15 * s, y - 2)],
              sail_col)
    fill_poly([(x - 1, y - 17 * s), (x - 1, y - 2), (x - 10 * s, y - 2)],
              (238, 180, 130))


def draw_boats(rng):
    draw_boat(660, 772, 1.0, rng)
    draw_boat(862, 818, 0.75, rng)
    # rowing boat near the foot of the falls
    fill_poly([(470, 738), (492, 738), (488, 744), (474, 744)], (52, 44, 38))
    fill_circle(481, 734, 2, (40, 34, 28))
    thick_line(486, 736, 494, 728, 2, (90, 70, 50))


# ---------------------------------------------------------------- texture

def halftone(rng):
    # retro dots in the dark areas: sea, cliff, upper sky corners
    for y in range(722, 992, 11):
        off = 5 if (y // 11) % 2 else 0
        for x in range(30 + off, 996, 11):
            fill_circle(x, y, 1.7, (16, 50, 56), 70)
    for y in range(420, 696, 10):
        xr = 330 + (y - 468) * (26.0 / 232.0) if y > 468 else 330
        off = 5 if (y // 10) % 2 else 0
        for x in range(30 + off, int(xr), 10):
            fill_circle(x, y, 1.6, (20, 28, 36), 90)
    for y in range(30, 190, 12):
        off = 6 if (y // 12) % 2 else 0
        for x in range(30 + off, 996, 12):
            if x < 120 or x > 900:  # corners only, keep the name clean
                fill_circle(x, y, 1.5, (160, 80, 50), 50)


def grain(rng, amp, block=1):
    """Film grain. One noise value per block x block pixels (block>1
    compresses far better, so real grain can fit under 1 MiB).
    Clamped, never wrapping (a wrap turns bright cream dark)."""
    if amp <= 0:
        return
    tw = (W + block - 1) // block
    rows = []
    for _ in range(256):
        rows.append(bytes(rng.randint(0, 2 * amp) for _ in range(tw * 3)))
    for y in range(H):
        trow = rows[(y // block) % 256]
        if block == 1:
            n = trow
        else:
            n = bytes(v for v in trow for _ in range(block))[:W * 3]
        row = buf[y]
        buf[y] = bytearray(
            0 if (v := a + b - amp) < 0 else (255 if v > 255 else v)
            for a, b in zip(row, n))


def vignette():
    # nested translucent outlines, darkest at the very edge
    for i in range(10):
        a = 34 - i * 3
        x0 = FRAME + 2 + i * 3
        x1 = 1000 - 2 - i * 3
        if x1 <= x0:
            break
        fill_rect(x0, x0, x1, x0 + 2, (40, 24, 16), a)
        fill_rect(x0, x1 - 2, x1, x1, (40, 24, 16), a)
        fill_rect(x0, x0, x0 + 2, x1, (40, 24, 16), a)
        fill_rect(x1 - 2, x0, x1, x1, (40, 24, 16), a)


# ---------------------------------------------------------------- render

def render(grain_amp, grain_block=1):
    global buf
    buf = [bytearray(W * 3) for _ in range(H)]
    rng = random.Random(SEED)
    # cream frame first
    for y in range(H):
        buf[y][:] = bytes(CREAM_DK) * W
    paint_sky_and_sea()
    draw_sun(rng)
    draw_cloud(150, 252, 260, 24, (251, 214, 168), 190, rng)
    draw_cloud(560, 282, 300, 28, (250, 200, 150), 180, rng)
    draw_cloud(700, 382, 260, 22, (248, 190, 138), 170, rng)
    draw_cloud(120, 432, 220, 20, (246, 196, 150), 160, rng)
    draw_cloud(300, 296, 250, 46, (251, 236, 214), 130, rng)
    draw_cloud(396, 320, 200, 38, (250, 228, 200), 120, rng)
    draw_cliff(rng)
    draw_sea_detail(rng)
    draw_falls(rng)
    draw_town(rng)
    draw_boats(rng)
    halftone(rng)
    # thin inner rule around the scene
    fill_rect(FRAME, FRAME, 1000, FRAME + 3, (120, 60, 35), 170)
    fill_rect(FRAME, 997, 1000, 1000, (120, 60, 35), 170)
    fill_rect(FRAME, FRAME, FRAME + 3, 1000, (120, 60, 35), 170)
    fill_rect(997, FRAME, 1000, 1000, (120, 60, 35), 170)
    # name + tagline (top, over the terracotta sky)
    draw_text("ONDARA", 512, 46, 118, 6.5, CREAM, shadow=INK_SHADOW)
    draw_text("THE FALLS THAT RISE", 512, 182, 26, 7.0,
              (250, 226, 178), shadow=INK_SHADOW, shadow_off=(2, 3))
    grain(rng, grain_amp, grain_block)
    vignette()
    return buf


# ---------------------------------------------------------------- PNG writer

def _png_chunk(typ, data):
    out = struct.pack(">I", len(data)) + typ + data
    out += struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)
    return out


def encode_png(image, quant_step=1):
    rows = []
    for y in range(H):
        row = bytes(image[y])
        if quant_step > 1:
            tbl = bytes((v // quant_step) * quant_step for v in range(256))
            row = row.translate(tbl)
        rows.append(row)
    best = None
    for mode in (0, 1, 2):
        parts = []
        prev = bytes(W * 3)
        for row in rows:
            if mode == 0:
                parts.append(b"\x00" + row)
            elif mode == 1:
                f = bytes((a - b) & 255 for a, b in
                          zip(row[3:], row[:-3]))
                parts.append(b"\x01" + row[:3] + f)
            else:
                f = bytes((a - b) & 255 for a, b in zip(row, prev))
                parts.append(b"\x02" + f)
            prev = row
        data = b"".join(parts)
        comp = zlib.compress(data, 1)
        if best is None or len(comp) < len(best[0]):
            best = (comp, data)
    data = best[1]
    comp = zlib.compress(data, 9)
    png = b"\x89PNG\r\n\x1a\n"
    png += _png_chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0))
    png += _png_chunk(b"IDAT", comp)
    png += _png_chunk(b"IEND", b"")
    return png


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, "entry.png")
    for grain_amp, grain_block, quant in ((3, 2, 1), (2, 2, 1),
                                          (1, 1, 2), (0, 1, 3)):
        image = render(grain_amp, grain_block)
        png = encode_png(image, quant)
        if len(png) <= 1_048_576:
            break
    with open(path, "wb") as f:
        f.write(png)
    print("wrote %s %dx%d %d bytes sha256=%s" %
          (path, W, H, len(png), hashlib.sha256(png).hexdigest()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
