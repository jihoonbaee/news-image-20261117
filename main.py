#!/usr/bin/env python3
"""news-image-20261117: draw one infographic PNG summing up the world news
of Tuesday 17 November 2026.

Pure Python 3 standard library, no network, no fonts on disk: the picture is
drawn programmatically on a raster canvas with an embedded 5x7 bitmap font,
then encoded as a PNG by hand (zlib + CRC32). Running the program twice
produces byte-identical output.
"""

import math
import os
import struct
import sys
import zlib
from binascii import crc32

# ---------------------------------------------------------------------------
# 5x7 bitmap font. Each glyph is 7 rows of 5 bits, '1' = ink.
# ---------------------------------------------------------------------------
FONT = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "11011", "10001"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    "3": ("11111", "00010", "00100", "00010", "00001", "10001", "01110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
}
FONT.update({
    "a": ("00000", "00000", "01110", "00001", "01111", "10001", "01111"),
    "b": ("10000", "10000", "11110", "10001", "10001", "10001", "11110"),
    "c": ("00000", "00000", "01110", "10000", "10000", "10001", "01110"),
    "d": ("00001", "00001", "01111", "10001", "10001", "10001", "01111"),
    "e": ("00000", "00000", "01110", "10001", "11111", "10000", "01110"),
    "f": ("00110", "01001", "01000", "11110", "01000", "01000", "01000"),
    "g": ("00000", "01111", "10001", "10001", "01111", "00001", "01110"),
    "h": ("10000", "10000", "11110", "10001", "10001", "10001", "10001"),
    "i": ("00100", "00000", "01100", "00100", "00100", "00100", "01110"),
    "j": ("00010", "00000", "00110", "00010", "00010", "10010", "01100"),
    "k": ("10000", "10000", "10010", "10100", "11000", "10100", "10010"),
    "l": ("01100", "00100", "00100", "00100", "00100", "00100", "01110"),
    "m": ("00000", "00000", "11010", "10101", "10101", "10101", "10101"),
    "n": ("00000", "00000", "11110", "10001", "10001", "10001", "10001"),
    "o": ("00000", "00000", "01110", "10001", "10001", "10001", "01110"),
    "p": ("00000", "00000", "11110", "10001", "11110", "10000", "10000"),
    "q": ("00000", "00000", "01111", "10001", "01111", "00001", "00001"),
    "r": ("00000", "00000", "10110", "11001", "10000", "10000", "10000"),
    "s": ("00000", "00000", "01111", "10000", "01110", "00001", "11110"),
    "t": ("00100", "00100", "11110", "00100", "00100", "00100", "00010"),
    "u": ("00000", "00000", "10001", "10001", "10001", "10011", "01101"),
    "v": ("00000", "00000", "10001", "10001", "10001", "01010", "00100"),
    "w": ("00000", "00000", "10001", "10101", "10101", "10101", "01010"),
    "x": ("00000", "00000", "10001", "01010", "00100", "01010", "10001"),
    "y": ("00000", "00000", "10001", "10001", "01111", "00001", "01110"),
    "z": ("00000", "00000", "11111", "00010", "00100", "01000", "11111"),
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ",": ("00000", "00000", "00000", "00000", "01100", "00100", "01000"),
    ":": ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    ";": ("00000", "01100", "01100", "00000", "01100", "00100", "01000"),
    "!": ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    "?": ("01110", "10001", "00001", "00110", "00100", "00000", "00100"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    "-": ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    "/": ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    "(": ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ")": ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    "%": ("11001", "11010", "00010", "00100", "01000", "01011", "10011"),
    "+": ("00000", "00100", "00100", "11111", "00100", "00100", "00000"),
    "&": ("01100", "10010", "10100", "01000", "10101", "10010", "01101"),
    "=": ("00000", "00000", "11111", "00000", "11111", "00000", "00000"),
    '"': ("01010", "01010", "00000", "00000", "00000", "00000", "00000"),
    "$": ("00100", "01111", "10100", "01110", "00101", "11110", "00100"),
    "[": ("01110", "01000", "01000", "01000", "01000", "01000", "01110"),
    "]": ("01110", "00010", "00010", "00010", "00010", "00010", "01110"),
    "_": ("00000", "00000", "00000", "00000", "00000", "00000", "11111"),
    "*": ("00000", "10101", "01110", "11111", "01110", "10101", "00000"),
})

# Every glyph must be exactly 7 rows of 5 bits; fail loudly if one is not.
for _ch, _rows in FONT.items():
    assert len(_rows) == 7 and all(len(_r) == 5 for _r in _rows), _ch

# ---------------------------------------------------------------------------
# Raster canvas + drawing primitives
# ---------------------------------------------------------------------------
W, H = 1024, 1024

PAPER = (250, 248, 242)
INK = (16, 24, 40)
NAVY = (13, 42, 74)
NAVY2 = (24, 64, 106)
RED = (178, 34, 34)
GREY = (110, 116, 124)
LINEGREY = (203, 206, 210)
WHITE = (255, 255, 255)
SKY = (186, 214, 235)
SEA = (46, 111, 164)
SEA_DARK = (28, 84, 130)
STEEL = (70, 84, 100)
STEEL_DARK = (48, 60, 74)
ORANGE = (232, 116, 24)
GOLD = (214, 164, 32)
GREEN = (46, 125, 70)


class Canvas:
    def __init__(self, w, h, bg):
        self.w, self.h = w, h
        self.pix = bytearray(bg) * (w * h)

    def set(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.pix[i], self.pix[i + 1], self.pix[i + 2] = c

    def fill_rect(self, x, y, w, h, c):
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(self.w, x + w), min(self.h, y + h)
        for yy in range(y0, y1):
            base = (yy * self.w + x0) * 3
            for xx in range(x0, x1):
                i = base + (xx - x0) * 3
                self.pix[i], self.pix[i + 1], self.pix[i + 2] = c

    def hline(self, x0, x1, y, c):
        self.fill_rect(min(x0, x1), y, abs(x1 - x0) + 1, 1, c)

    def vline(self, x, y0, y1, c):
        self.fill_rect(x, min(y0, y1), 1, abs(y1 - y0) + 1, c)

    def line(self, x0, y0, x1, y1, c):
        dx, dy = abs(x1 - x0), abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        while True:
            self.set(x0, y0, c)
            if x0 == x1 and y0 == y1:
                return
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy

    def thick_line(self, x0, y0, x1, y1, t, c):
        # A thick line as a stack of offset thin lines (good enough, no AA).
        for k in range(-(t // 2), t // 2 + 1):
            self.line(x0, y0 + k, x1, y1 + k, c)

    def fill_circle(self, cx, cy, r, c):
        for dy in range(-r, r + 1):
            dx = int((r * r - dy * dy) ** 0.5)
            self.hline(cx - dx, cx + dx, cy + dy, c)

    def circle_outline(self, cx, cy, r, c):
        x, y, d = 0, r, 3 - 2 * r
        while x <= y:
            for px, py in ((x, y), (y, x), (-x, y), (-y, x),
                           (x, -y), (y, -x), (-x, -y), (-y, -x)):
                self.set(cx + px, cy + py, c)
            if d < 0:
                d += 4 * x + 6
            else:
                d += 4 * (x - y) + 10
                y -= 1
            x += 1

    def fill_poly(self, pts, c):
        # Scanline fill for a simple polygon (convex or concave).
        ys = [p[1] for p in pts]
        for y in range(min(ys), max(ys) + 1):
            xs = []
            n = len(pts)
            for i in range(n):
                x0, y0 = pts[i]
                x1, y1 = pts[(i + 1) % n]
                if (y0 <= y < y1) or (y1 <= y < y0):
                    xs.append(x0 + (y - y0) * (x1 - x0) / (y1 - y0))
            xs.sort()
            for i in range(0, len(xs) - 1, 2):
                self.hline(int(round(xs[i])), int(round(xs[i + 1])), y, c)

    def rect_outline(self, x, y, w, h, t, c):
        self.fill_rect(x, y, w, t, c)
        self.fill_rect(x, y + h - t, w, t, c)
        self.fill_rect(x, y, t, h, c)
        self.fill_rect(x + w - t, y, t, h, c)


# ---------------------------------------------------------------------------
# Text: glyph width is 5*scale, advance 6*scale; line height 8*scale.
# ---------------------------------------------------------------------------
def text_width(text, scale):
    return sum(6 * scale for ch in text if ch in FONT) - scale


def draw_text(cv, x, y, text, scale, color, align="left"):
    w = text_width(text, scale)
    if align == "center":
        x -= w // 2
    elif align == "right":
        x -= w
    cx = x
    for ch in text:
        glyph = FONT.get(ch)
        if glyph is None:
            cx += 6 * scale
            continue
        for r, row in enumerate(glyph):
            for col, bit in enumerate(row):
                if bit == "1":
                    cv.fill_rect(cx + col * scale, y + r * scale,
                                 scale, scale, color)
        cx += 6 * scale
    return w


def wrap_text(text, scale, max_w):
    """Greedy word wrap; returns a list of lines that fit max_w."""
    words = text.split(" ")
    lines, cur = [], ""
    for word in words:
        trial = word if not cur else cur + " " + word
        if text_width(trial, scale) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines

# ---------------------------------------------------------------------------
# Pictograms: flat, simple scenes drawn from rectangles, lines and circles.
# ---------------------------------------------------------------------------
def scene_bridge(cv, x, y, w, h):
    """Kerch Strait: a bridge with its middle span dropped into the sea."""
    cv.fill_rect(x, y, w, h, (198, 220, 236))
    sea_y = y + h - 62
    cv.fill_rect(x, sea_y, w, h - (sea_y - y), SEA)
    # waves (one row, clear of the caption below)
    for wx in range(x + 14, x + w - 14, 46):
        cv.circle_outline(wx, sea_y + 16, 9, WHITE)
    deck_y = sea_y - 34
    # towers
    for tx in (x + 78, x + w - 92):
        cv.fill_rect(tx, deck_y - 96, 12, 96, STEEL_DARK)
        cv.fill_rect(tx - 8, deck_y - 96, 28, 8, STEEL_DARK)
    # cables
    cv.line(x + 84, deck_y - 92, x + 150, deck_y, STEEL)
    cv.line(x + 84, deck_y - 92, x + 30, deck_y, STEEL)
    cv.line(x + w - 86, deck_y - 92, x + w - 156, deck_y, STEEL)
    cv.line(x + w - 86, deck_y - 92, x + w - 36, deck_y, STEEL)
    # deck: left and right segments, gap in the middle
    cv.fill_rect(x + 8, deck_y, 148, 10, STEEL_DARK)
    cv.fill_rect(x + w - 156, deck_y, 148, 10, STEEL_DARK)
    # fallen span: a beam knocked off the deck, tilted down into the water
    cv.fill_poly([(x + 166, deck_y + 2), (x + 214, deck_y + 8),
                  (x + 188, sea_y + 30), (x + 140, sea_y + 24)], STEEL)
    cv.fill_rect(x + 140, sea_y + 24, 48, 4, STEEL_DARK)
    # blast puff where the span broke
    cv.fill_circle(x + 192, deck_y - 8, 12, ORANGE)
    cv.fill_circle(x + 192, deck_y - 8, 6, GOLD)
    # splash where the span went in
    cv.fill_circle(x + 164, sea_y + 26, 7, WHITE)
    cv.fill_circle(x + 176, sea_y + 32, 5, WHITE)
    draw_text(cv, x + w // 2, sea_y + 42, "KERCH STRAIT", 2, WHITE,
              align="center")


def scene_tanker(cv, x, y, w, h):
    """Strait of Hormuz: a tanker on fire."""
    cv.fill_rect(x, y, w, h, SKY)
    cv.fill_circle(x + w - 46, y + 18, 12, GOLD)
    sea_y = y + 44
    cv.fill_rect(x, sea_y, w, h - 44, SEA)
    cv.hline(x + 20, x + w - 20, sea_y + 22, WHITE)
    # tanker hull
    hx, hy = x + 56, sea_y + 8
    cv.fill_rect(hx, hy, 260, 18, (24, 28, 36))
    cv.fill_poly([(hx + 260, hy), (hx + 300, hy + 6),
                  (hx + 260, hy + 18)], (24, 28, 36))
    # containers + superstructure
    cv.fill_rect(hx + 20, hy - 16, 44, 16, RED)
    cv.fill_rect(hx + 72, hy - 16, 44, 16, GOLD)
    cv.fill_rect(hx + 124, hy - 16, 44, 16, GREEN)
    cv.fill_rect(hx + 196, hy - 26, 34, 26, WHITE)
    # flame and smoke above the deck
    cv.fill_poly([(hx + 238, hy - 4), (hx + 252, hy - 38),
                  (hx + 266, hy - 4)], ORANGE)
    cv.fill_poly([(hx + 245, hy - 4), (hx + 252, hy - 24),
                  (hx + 259, hy - 4)], GOLD)
    cv.fill_circle(hx + 252, hy - 42, 8, GREY)
    cv.fill_circle(hx + 264, hy - 54, 7, GREY)


def scene_plane(cv, x, y, w, h):
    """Manila: a plane arriving under the sun."""
    cv.fill_rect(x, y, w, h, SKY)
    cv.fill_circle(x + 52, y + 20, 13, GOLD)
    for cx, cy in ((x + 330, y + 16), (x + 360, y + 22), (x + 420, y + 14)):
        cv.fill_circle(cx, cy, 9, WHITE)
        cv.fill_circle(cx + 12, cy + 3, 7, WHITE)
    # plane, nose to the right
    px, py = x + 110, y + 52
    cv.fill_poly([(px, py - 6), (px + 200, py - 6), (px + 228, py),
                  (px + 200, py + 6), (px, py + 6)], NAVY)
    cv.fill_poly([(px + 60, py - 6), (px + 110, py - 30),
                  (px + 128, py - 6)], NAVY)
    cv.fill_poly([(px + 90, py + 6), (px + 130, py + 26),
                  (px + 146, py + 6)], NAVY)
    cv.fill_poly([(px + 6, py - 6), (px + 6, py - 26),
                  (px + 30, py - 6)], NAVY)
    cv.fill_rect(px + 150, py - 3, 66, 3, WHITE)


def scene_virus(cv, x, y, w, h):
    """Measles: a virus, drawn large and red."""
    cv.fill_rect(x, y, w, h, (244, 226, 226))
    cx, cy = x + 110, y + h // 2
    for k in range(10):
        ang = k * 0.6283185307179586
        x1 = cx + int(24 * math.cos(ang))
        y1 = cy + int(24 * math.sin(ang))
        x2 = cx + int(38 * math.cos(ang))
        y2 = cy + int(38 * math.sin(ang))
        cv.thick_line(x1, y1, x2, y2, 3, RED)
        cv.fill_circle(x2, y2, 4, RED)
    cv.fill_circle(cx, cy, 24, RED)
    cv.fill_circle(cx - 8, cy - 7, 5, (255, 120, 120))
    cv.fill_circle(cx + 9, cy + 8, 4, (255, 120, 120))
    for sx, sy, sr in ((x + 330, y + 22, 12), (x + 390, y + 52, 8),
                       (x + 300, y + 58, 6)):
        cv.fill_circle(sx, sy, sr, RED)
        cv.fill_circle(sx - 3, sy - 3, 2, (255, 120, 120))


def scene_rocket(cv, x, y, w, h):
    """Vulcan failure: a rocket under a dark sky, flame below."""
    cv.fill_rect(x, y, w, h, NAVY)
    for sx, sy in ((x + 30, y + 14), (x + 90, y + 30), (x + 420, y + 12),
                   (x + 460, y + 34), (x + 370, y + 58), (x + 60, y + 60)):
        cv.fill_rect(sx, sy, 3, 3, WHITE)
    cx = x + 220
    # flame and smoke
    cv.fill_poly([(cx - 12, y + h - 6), (cx, y + h - 34),
                  (cx + 12, y + h - 6)], ORANGE)
    cv.fill_poly([(cx - 6, y + h - 6), (cx, y + h - 24),
                  (cx + 6, y + h - 6)], GOLD)
    cv.fill_circle(cx - 26, y + h - 10, 7, GREY)
    cv.fill_circle(cx + 28, y + h - 8, 6, GREY)
    # body
    cv.fill_rect(cx - 13, y + 22, 26, 44, WHITE)
    cv.fill_poly([(cx - 13, y + 22), (cx + 13, y + 22), (cx, y + 4)], RED)
    cv.fill_rect(cx - 13, y + 58, 26, 8, RED)
    cv.fill_poly([(cx - 13, y + 58), (cx - 26, y + 70), (cx - 13, y + 66)],
                 RED)
    cv.fill_poly([(cx + 13, y + 58), (cx + 26, y + 70), (cx + 13, y + 66)],
                 RED)
    cv.fill_rect(cx - 13, y + 34, 26, 4, NAVY2)
    # two lost satellites drifting away
    for sx, sy in ((x + 330, y + 26), (x + 380, y + 46)):
        cv.fill_rect(sx, sy, 10, 10, GOLD)
        cv.fill_rect(sx - 8, sy + 3, 7, 4, GOLD)
        cv.fill_rect(sx + 11, sy + 3, 7, 4, GOLD)

# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------
def story_panel(cv, x, y, w, h, scene, kicker_color, kicker, headline,
                summary):
    cv.fill_rect(x, y, w, h, WHITE)
    scene(cv, x + 2, y + 2, w - 4, 76)
    cv.rect_outline(x, y, w, h, 2, LINEGREY)
    draw_text(cv, x + 16, y + 86, kicker, 2, kicker_color)
    lines = wrap_text(headline, 4, w - 32)
    hy = y + 108
    for ln in lines:
        draw_text(cv, x + 16, hy, ln, 4, INK)
        hy += 32
    slines = wrap_text(summary, 3, w - 32)
    sy = hy + 6
    for ln in slines:
        draw_text(cv, x + 16, sy, ln, 3, (58, 64, 74))
        sy += 23


def draw(cv):
    cv.fill_rect(0, 0, W, H, PAPER)

    # ---- header: the day, named large ----
    cv.fill_rect(0, 0, W, 128, NAVY)
    draw_text(cv, W // 2, 20, "THE WORLD IN ONE DAY", 2, (198, 212, 228),
              align="center")
    draw_text(cv, W // 2, 46, "TUESDAY 17 NOVEMBER 2026", 5, WHITE,
              align="center")
    cv.fill_rect(32, 104, 960, 5, RED)

    # ---- lead story: the Crimean Bridge ----
    lx, ly, lw, lh = 16, 140, 992, 256
    cv.fill_rect(lx, ly, lw, lh, (233, 239, 246))
    scene_bridge(cv, lx + 2, ly + 2, 380, lh - 4)
    cv.rect_outline(lx, ly, lw, lh, 2, LINEGREY)
    tx = lx + 404
    draw_text(cv, tx, ly + 20, "EUROPE - WAR IN UKRAINE", 2, RED)
    lines = wrap_text("CRIMEA BRIDGE COLLAPSES", 5, lw - 404 - 24)
    hy = ly + 46
    for ln in lines:
        draw_text(cv, tx, hy, ln, 5, INK)
        hy += 42
    slines = wrap_text(
        "Second strike in two days; video shows a road span down in "
        "the Kerch Strait. Kyiv says the hit took weeks to plan.", 3,
        lw - 404 - 24)
    sy = hy + 8
    for ln in slines:
        draw_text(cv, tx, sy, ln, 3, (58, 64, 74))
        sy += 23

    # ---- four more stories, two by two ----
    story_panel(cv, 16, 408, 488, 280, scene_tanker, RED,
                "MIDDLE EAST - ENERGY", "TANKER HIT IN HORMUZ",
                "A tanker is struck; Iran says more hit mines, as a "
                "third US carrier reaches the Gulf.")
    story_panel(cv, 520, 408, 488, 280, scene_plane, NAVY2,
                "ASIA - DIPLOMACY", "TRUMP LANDS IN MANILA",
                "Asia trip opens in Manila with Quad talks; then APEC "
                "in Shenzhen and a planned Xi-Putin meeting.")
    story_panel(cv, 16, 696, 488, 280, scene_virus, RED,
                "AMERICAS - HEALTH", "US LOSES MEASLES FREE STATUS",
                "PAHO ends the status held since 2000 after 5,412 US "
                "cases; Mexico and Bolivia too.")
    story_panel(cv, 520, 696, 488, 280, scene_rocket, NAVY2,
                "SPACE - TECHNOLOGY", "VULCAN ROCKET FAILS",
                "ULA blames its first stage for losing 40 Amazon "
                "satellites, its first total failure.")

    # ---- footer: sources ----
    draw_text(cv, W // 2, 992, "Sources: Reuters, AP, PAHO, ULA, Al Jazeera",
              2, GREY, align="center")


# ---------------------------------------------------------------------------
# PNG encoder (RGB, no filtering, zlib level 9): deterministic bytes.
# ---------------------------------------------------------------------------
def _chunk(kind, data):
    out = struct.pack(">I", len(data)) + kind + data
    return out + struct.pack(">I", crc32(kind + data) & 0xFFFFFFFF)


def encode_png(cv):
    ihdr = struct.pack(">IIBBBBB", cv.w, cv.h, 8, 2, 0, 0, 0)
    raw = bytearray()
    for yy in range(cv.h):
        raw.append(0)
        raw += cv.pix[yy * cv.w * 3:(yy + 1) * cv.w * 3]
    png = b"\x89PNG\r\n\x1a\n"
    png += _chunk(b"IHDR", ihdr)
    png += _chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += _chunk(b"IEND", b"")
    return png


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR") or "out"
    os.makedirs(out_dir, exist_ok=True)
    cv = Canvas(W, H, PAPER)
    draw(cv)
    data = encode_png(cv)
    path = os.path.join(out_dir, "entry.png")
    with open(path, "wb") as f:
        f.write(data)
    print(path, len(data), "bytes")


if __name__ == "__main__":
    sys.exit(main())
