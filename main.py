#!/usr/bin/env python3
"""SOLMARA — a travel poster for a place that does not exist.

Deterministic, pure-stdlib procedural poster renderer. Writes one PNG to
/output/entry.png (or ./entry.png when /output is absent): a vintage travel
poster for SOLMARA, "the isle of the second sunset" — a great stone arch
with a lighthouse on top, a low banded sun, a crescent moon, layered
headlands, a shining sea and palm silhouettes, with the place's name set
into the picture in large deco lettering.
"""
import math
import os
import struct
import zlib

W = H = 1024
FB = bytearray(W * H * 3)

# ---------------------------------------------------------------- utilities
_state = 987654321


def rnd():
    global _state
    _state = (_state * 1103515245 + 12345) & 0x7FFFFFFF
    return _state / 0x7FFFFFFF


def put(x, y, r, g, b):
    if 0 <= x < W and 0 <= y < H:
        i = (y * W + x) * 3
        FB[i] = r
        FB[i + 1] = g
        FB[i + 2] = b


def blend(x, y, r, g, b, a):
    if 0 <= x < W and 0 <= y < H:
        i = (y * W + x) * 3
        FB[i] = int(FB[i] * (1 - a) + r * a)
        FB[i + 1] = int(FB[i + 1] * (1 - a) + g * a)
        FB[i + 2] = int(FB[i + 2] * (1 - a) + b * a)


def lerp(c1, c2, t):
    return (int(c1[0] + (c2[0] - c1[0]) * t),
            int(c1[1] + (c2[1] - c1[1]) * t),
            int(c1[2] + (c2[2] - c1[2]) * t))


def grad(stops, t):
    for k in range(len(stops) - 1):
        t0, c0 = stops[k]
        t1, c1 = stops[k + 1]
        if t0 <= t <= t1:
            return lerp(c0, c1, (t - t0) / (t1 - t0) if t1 > t0 else 0.0)
    return stops[-1][1]


BAYER = ((0, 8, 2, 10), (12, 4, 14, 6), (3, 11, 1, 9), (15, 7, 13, 5))


def disc(cx, cy, r, col):
    r2 = r * r
    for y in range(int(cy - r), int(cy + r) + 1):
        dy = y - cy
        dx = math.sqrt(max(0.0, r2 - dy * dy))
        for x in range(int(cx - dx), int(cx + dx) + 1):
            put(x, y, *col)


def thick_line(p0, p1, wdt, col):
    x0, y0 = p0
    x1, y1 = p1
    steps = max(2, int(math.hypot(x1 - x0, y1 - y0) / 2.5))
    r = wdt / 2.0
    for s in range(steps + 1):
        t = s / steps
        disc(x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, r, col)


def poly(points, col):
    ys = [p[1] for p in points]
    y0, y1 = int(min(ys)), int(max(ys))
    n = len(points)
    for y in range(y0, y1 + 1):
        xs = []
        for i in range(n):
            xa, ya = points[i]
            xb, yb = points[(i + 1) % n]
            if (ya <= y < yb) or (yb <= y < ya):
                xs.append(xa + (y - ya) * (xb - xa) / (yb - ya))
        xs.sort()
        for k in range(0, len(xs) - 1, 2):
            for x in range(int(xs[k]), int(xs[k + 1]) + 1):
                put(x, y, *col)


# ---------------------------------------------------------------- sky
HORIZON = 648
SKY_STOPS = [(0.0, (16, 24, 54)), (0.30, (43, 52, 94)), (0.55, (112, 66, 102)),
             (0.78, (214, 102, 84)), (1.0, (244, 190, 118))]


def sky_color(y):
    return grad(SKY_STOPS, y / HORIZON)


for y in range(HORIZON):
    base = sky_color(y)
    row = FB[y * W * 3:(y + 1) * W * 3]
    brow = BAYER[y & 3]
    for x in range(W):
        d = (brow[x & 3] - 7.5) * 0.55
        i = x * 3
        row[i] = max(0, min(255, int(base[0] + d)))
        row[i + 1] = max(0, min(255, int(base[1] + d)))
        row[i + 2] = max(0, min(255, int(base[2] + d)))
    FB[y * W * 3:(y + 1) * W * 3] = row

# stars in the upper sky
for _ in range(150):
    sx = int(rnd() * W)
    sy = int(rnd() * 300)
    a = max(0.0, 1.0 - sy / 300.0) * (0.35 + 0.65 * rnd())
    blend(sx, sy, 255, 244, 214, a)
    if rnd() > 0.8:
        blend(sx + 1, sy, 255, 244, 214, a * 0.6)

# crescent moon, mid right sky (clear of the lettering)
MCX, MCY, MR = 906, 330, 40
for y in range(MCY - MR, MCY + MR + 1):
    for x in range(MCX - MR, MCX + MR + 1):
        d1 = (x - MCX) ** 2 + (y - MCY) ** 2
        d2 = (x - (MCX + 17)) ** 2 + (y - (MCY - 10)) ** 2
        if d1 <= MR * MR and d2 > 33 * 33:
            put(x, y, 247, 234, 209)

# ---------------------------------------------------------------- sun
SCX, SCY, SR = 428, HORIZON, 172
for y in range(SCY - SR, HORIZON):
    dy = y - SCY
    dx = math.sqrt(max(0.0, SR * SR - dy * dy))
    # retro banding: gaps widen below the sun's centre line
    rel = (y - (SCY - SR)) / (2 * SR)
    if rel > 0.52:
        band = int((rel - 0.52) * 46)
        if band % 9 < 2:
            continue
    col = grad([(0.0, (255, 222, 130)), (0.6, (255, 166, 88)),
                (1.0, (255, 116, 76))], rel)
    for x in range(int(SCX - dx), int(SCX + dx) + 1):
        put(x, y, *col)
# sun glow on the horizon line
for x in range(SCX - SR - 30, SCX + SR + 30):
    blend(x, HORIZON - 2, 255, 214, 140, 0.5)
    blend(x, HORIZON - 1, 255, 214, 140, 0.5)

# ---------------------------------------------------------------- headlands
far = [(560, HORIZON), (600, 540), (660, 585), (720, 492), (790, 560),
       (850, 505), (920, 575), (980, 530), (1024, 570), (1024, HORIZON)]
poly(far, (86, 62, 104))
near = [(700, HORIZON), (760, 575), (830, 610), (900, 560), (960, 605),
        (1024, 585), (1024, HORIZON)]
poly(near, (58, 48, 84))

# ---------------------------------------------------------------- the arch
def arch_poly(cx, base, rxo, ryo, rxi, ryi):
    pts = []
    for k in range(41):
        a = math.pi - (k / 40.0) * math.pi
        pts.append((cx + rxo * math.cos(a), base - ryo * math.sin(a)))
    for k in range(41):
        a = (k / 40.0) * math.pi
        pts.append((cx + rxi * math.cos(a), base - ryi * math.sin(a)))
    return pts


# warm rim light copy, nudged toward the sun
poly(arch_poly(330, 706, 238, 306, 152, 208), (226, 132, 92))
# rock body with a vertical shade gradient faked by two overlapping fills
poly(arch_poly(322, 706, 238, 306, 152, 208), (64, 58, 86))
poly(arch_poly(322, 706, 196, 262, 152, 208), (74, 66, 98))
# rock texture: faint short strokes blended into the legs
for _ in range(150):
    side = 1 if rnd() > 0.5 else -1
    tx = 322 + side * (172 + rnd() * 52)
    ty = 480 + rnd() * 210
    ln = 3 + rnd() * 8
    for k in range(int(ln)):
        blend(int(tx + k), int(ty), 30, 27, 44, 0.35)

# ---------------------------------------------------------------- lighthouse
LX = 322
# beam of light toward the upper right
beam = [(LX + 6, 372), (LX + 330, 268), (LX + 330, 330)]
for yy in range(268, 380):
    for xx in range(LX, LX + 332):
        t = (xx - LX) / 332.0
        top = 372 - 104 * t
        bot = 372 - 42 * t
        if top <= yy <= bot:
            blend(xx, yy, 255, 226, 150, 0.30 * (1 - t) + 0.04)
# tower: tapered, cream with a coral band
poly([(LX - 15, 402), (LX + 15, 402), (LX + 10, 356), (LX - 10, 356)],
     (243, 231, 205))
poly([(LX - 13, 384), (LX + 13, 384), (LX + 12, 372), (LX - 12, 372)],
     (214, 102, 84))
# lamp room + roof
poly([(LX - 11, 356), (LX + 11, 356), (LX + 11, 342), (LX - 11, 342)],
     (30, 32, 52))
disc(LX, 349, 5, (255, 214, 120))
poly([(LX - 15, 342), (LX + 15, 342), (LX, 326)], (30, 32, 52))
# rock the lighthouse stands on
poly([(LX - 34, 408), (LX + 34, 408), (LX + 20, 392), (LX - 20, 392)],
     (64, 58, 86))

# ---------------------------------------------------------------- sea
SEA_STOPS = [(0.0, (52, 124, 128)), (0.35, (26, 92, 110)),
             (1.0, (9, 44, 74))]
for y in range(HORIZON, H):
    base = grad(SEA_STOPS, (y - HORIZON) / (H - HORIZON))
    brow = BAYER[y & 3]
    for x in range(W):
        d = (brow[x & 3] - 7.5) * 0.5
        i = (y * W + x) * 3
        FB[i] = max(0, min(255, int(base[0] + d)))
        FB[i + 1] = max(0, min(255, int(base[1] + d)))
        FB[i + 2] = max(0, min(255, int(base[2] + d)))
# sun glitter path
for y in range(HORIZON + 6, 950):
    t = (y - HORIZON) / 320.0
    half = 26 + t * 120
    n = 3 + int(t * 5)
    for _ in range(n):
        gx = SCX + (rnd() * 2 - 1) * half
        ln = 8 + rnd() * (20 + t * 42)
        a = 0.75 * (1 - t * 0.72)
        for x in range(int(gx - ln / 2), int(gx + ln / 2)):
            blend(x, y, 255, 196, 110, a)
# soft wave lines
for _ in range(46):
    wy = HORIZON + 26 + int(rnd() * 330)
    wx = int(rnd() * (W - 90))
    ln = 22 + rnd() * 60
    for x in range(wx, wx + int(ln)):
        blend(x, wy, 214, 240, 238, 0.20)

# ---------------------------------------------------------------- foreground
dune_l = [(0, 1024), (0, 918), (90, 892), (210, 906), (330, 952),
          (430, 1024)]
poly(dune_l, (17, 22, 44))
dune_r = [(1024, 1024), (1024, 900), (940, 884), (830, 902), (730, 950),
          (660, 1024)]
poly(dune_r, (17, 22, 44))


def palm(bx, by, s, flip):
    pts = []
    for k in range(13):
        t = k / 12.0
        pts.append((bx + flip * 30 * s * t * t, by - 148 * s * t))
    for a, b in zip(pts, pts[1:]):
        thick_line(a, b, 9 * s, (13, 17, 34))
    tx, ty = pts[-1]
    for da in (-82, -55, -28, 0, 28, 55, 82):
        ex = tx + math.sin(math.radians(da)) * 84 * s
        ey = ty - math.cos(math.radians(da)) * 30 * s + 44 * s
        frond = []
        for k in range(10):
            t = k / 9.0
            frond.append((tx + (ex - tx) * t,
                          ty + (ey - ty) * t + 26 * s * t * t
                          - 16 * s * math.sin(math.pi * t)))
        for a, b in zip(frond, frond[1:]):
            thick_line(a, b, 4.6 * s, (13, 17, 34))
    disc(tx, ty + 4, 6 * s, (13, 17, 34))


palm(96, 1000, 1.15, 1)
palm(946, 986, 0.95, -1)

# birds
for bx, by, s in ((618, 268, 1.0), (668, 238, 0.8), (576, 224, 0.7),
                  (716, 292, 0.9)):
    thick_line((bx - 13 * s, by), (bx - 2 * s, by - 7 * s), 3.0, (20, 24, 48))
    thick_line((bx + 2 * s, by - 7 * s), (bx + 13 * s, by), 3.0, (20, 24, 48))

# ---------------------------------------------------------------- the name
LETTERS = {
    "S": [[(8.5, 1.6), (6.0, 0.2), (3.4, 0.2), (1.2, 1.9), (1.2, 4.7),
           (3.0, 6.7), (7.0, 7.7), (8.8, 9.7), (8.8, 12.2), (6.8, 13.8),
           (3.2, 13.8), (1.0, 12.3)]],
    "O": [[(5.0 + 4.6 * math.cos(a), 7.0 + 6.7 * math.sin(a))
           for a in [math.radians(d) for d in range(0, 361, 12)]]],
    "L": [[(1.2, 0.0), (1.2, 14.0), (8.8, 14.0)]],
    "M": [[(1.0, 14.0), (1.0, 0.0), (5.0, 6.6), (9.0, 0.0), (9.0, 14.0)]],
    "A": [[(0.8, 14.0), (5.0, 0.0), (9.2, 14.0)],
          [(2.9, 9.3), (7.1, 9.3)]],
    "R": [[(1.0, 14.0), (1.0, 0.0), (5.8, 0.0), (8.6, 1.9), (8.6, 5.2),
           (5.8, 7.0), (1.0, 7.0)],
          [(4.8, 7.0), (9.0, 14.0)]],
}
NAME = "SOLMARA"
SCALE = 8.6
ADV = 10 * SCALE + 27
TOTAL = ADV * len(NAME) - 27
X0 = (W - TOTAL) / 2.0
Y0 = 58.0
for layer, col, ox, oy in ((0, (18, 22, 46), 5, 6), (1, (247, 234, 209), 0, 0)):
    for i, ch in enumerate(NAME):
        lx = X0 + i * ADV + ox
        for stroke in LETTERS[ch]:
            pts = [(lx + px * SCALE, Y0 + oy + py * SCALE) for px, py in stroke]
            for a, b in zip(pts, pts[1:]):
                thick_line(a, b, 15.5, col)
# small diamond ornaments under the name
for cx in (W / 2 - 130, W / 2, W / 2 + 130):
    poly([(cx, 218), (cx + 9, 227), (cx, 236), (cx - 9, 227)],
         (247, 234, 209))

# ---------------------------------------------------------------- frame
for inset, wdt in ((22, 5), (36, 2)):
    c = (247, 234, 209)
    thick_line((inset, inset), (W - inset, inset), wdt, c)
    thick_line((inset, H - inset), (W - inset, H - inset), wdt, c)
    thick_line((inset, inset), (inset, H - inset), wdt, c)
    thick_line((W - inset, inset), (W - inset, H - inset), wdt, c)

# ---------------------------------------------------------------- write PNG
def chunk(tag, data):
    c = struct.pack(">I", len(data)) + tag + data
    return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)


raw = b"".join(b"\x00" + bytes(FB[y * W * 3:(y + 1) * W * 3])
               for y in range(H))
png = (b"\x89PNG\r\n\x1a\n"
       + chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0))
       + chunk(b"IDAT", zlib.compress(raw, 6))
       + chunk(b"IEND", b""))
out = "/output/entry.png" if os.path.isdir("/output") else os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "entry.png")
with open(out, "wb") as f:
    f.write(png)
print("wrote", out, len(png), "bytes")
