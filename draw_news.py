#!/usr/bin/env python3
"""Draw the 25 November 2026 world-news page.

One page, one day. A masthead names WEDNESDAY 25 NOVEMBER 2026; four panels in
a 2x2 grid carry the day's four most consequential stories across regions and
fields, each with a pictogram built from PIL shapes, a place caption, an
all-caps headline and a summary of three lines; a strip below carries four more
stories of the day. Palette: dark ink on paper white, one red accent.

No network, no randomness, no external images: two runs write identical bytes.

Run:  python3 draw_news.py      ->  entry.png beside this file
"""

from __future__ import annotations

import math
import os
import sys

from PIL import Image, ImageDraw, ImageFont

# --- geometry ---------------------------------------------------------------
SS = 2                      # supersample factor: draw big, shrink once
W = H = 1024                # final size in pixels
M = 34                      # side margin

# --- palette (newsprint: dark ink on paper, one accent) ----------------------
PAPER = (252, 250, 245)
INK = (22, 23, 26)
MUTED = (95, 96, 101)
TINT = (242, 237, 226)
ACCENT = (161, 30, 36)
HAIR = (176, 172, 163)

FONT_DIRS = (
    "/usr/share/fonts/truetype/dejavu",
    "/usr/share/fonts/dejavu",
    "/usr/share/fonts/TTF",
)


def _face(name: str, size: int) -> ImageFont.FreeTypeFont:
    """Load a TrueType face at `size` device pixels, falling back safely."""
    for directory in FONT_DIRS:
        path = os.path.join(directory, name)
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    for directory in FONT_DIRS:
        path = os.path.join(directory, "DejaVuSans.ttf")
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default(size)


def bold(size: int) -> ImageFont.FreeTypeFont:
    return _face("DejaVuSans-Bold.ttf", size * SS)


def book(size: int) -> ImageFont.FreeTypeFont:
    return _face("DejaVuSans.ttf", size * SS)


# --- text helpers: every measurement is in 1024-space units ------------------
def tw(font: ImageFont.FreeTypeFont, s: str, tracking: float = 0.0) -> float:
    """Width of `s` in 1024-space units, with optional extra letter spacing."""
    if not tracking:
        return font.getlength(s) / SS
    return sum(font.getlength(c) for c in s) / SS + tracking * (len(s) - 1)


def wrap(text: str, font: ImageFont.FreeTypeFont, width: float) -> list[str]:
    """Greedy word wrap to `width` (1024-space units). Never splits a word."""
    lines: list[str] = []
    cur = ""
    for word in text.split():
        trial = word if not cur else cur + " " + word
        if tw(font, trial) <= width:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def asc(font: ImageFont.FreeTypeFont) -> float:
    return font.getmetrics()[0] / SS


def desc(font: ImageFont.FreeTypeFont) -> float:
    return font.getmetrics()[1] / SS


def pt(font: ImageFont.FreeTypeFont) -> float:
    """The point size a face was loaded at, in 1024-space units."""
    return font.size / SS


# Every string drawn is recorded here with its ink box, for the fit audit.
BOXES: list[tuple[str, tuple[float, float, float, float]]] = []


def put(d, x: float, baseline: float, s: str, font, fill,
        tracking: float = 0.0, label: str = "") -> None:
    """Draw one line, left edge at `x`, baseline at `baseline`."""
    if tracking:
        cx = x
        for ch in s:
            d.text((cx * SS, baseline * SS), ch, font=font, fill=fill,
                   anchor="ls")
            cx += (font.getlength(ch) + tracking * SS) / SS
    else:
        d.text((x * SS, baseline * SS), s, font=font, fill=fill, anchor="ls")
    box = d.textbbox((x * SS, baseline * SS), s, font=font, anchor="ls")
    BOXES.append((label or s, tuple(v / SS for v in box)))

# --- the day: four main stories, plus a strip of four more ------------------
STORIES = (
    {
        "num": "01",
        "tag": "UNITED STATES  \u00b7  CYBER",
        "place": "WASHINGTON",
        "head": ("CYBERATTACK HITS", "CIA AND ODNI"),
        "body": "CNN: a cyberattack on the CIA and the Office of the "
                "Director of National Intelligence affected unclassified "
                "data.",
        "icon": "shield",
    },
    {
        "num": "02",
        "tag": "LIBYA  \u00b7  UKRAINE WAR",
        "place": "BENGHAZI, LIBYA",
        "head": ("SEA DRONES SINK", "RUSSIAN CORVETTE"),
        "body": "Ukrainian sea drones sank Russia's corvette Merkury at "
                "Benghazi, Libya, and hit the cargo ship MV Angara.",
        "icon": "ship",
    },
    {
        "num": "03",
        "tag": "DR CONGO  \u00b7  HEALTH",
        "place": "ITURI, DR CONGO",
        "head": ("WHO EVACUATED", "ITURI HOSPITAL"),
        "body": "WHO staff left a hospital in Akwe, Ituri, after sheltering "
                "three days amid fierce fighting in Congo's Ebola zone.",
        "icon": "heli",
    },
    {
        "num": "04",
        "tag": "ANTALYA  \u00b7  CLIMATE",
        "place": "ANTALYA, T\u00dcRKIYE",
        "head": ("COP31 ENDS", "WITHOUT A DEAL"),
        "body": "COP31 in Antalya ended with no deal as oil and gas "
                "producers blocked fossil-fuel phaseout wording.",
        "icon": "globe",
    },
)

# The day's other consequential stories, one plain clause each.
TICKER = (
    "New York jury finds Huawei guilty of stealing US trade secrets",
    "Iran's Guards say mines hit three tankers in the Strait of Hormuz",
    "NATO to send early-warning aircraft to Poland",
    "Gaza: death toll put at 74,746 by WAFA",
)


# --- pictograms -------------------------------------------------------------
# Each icon fills a square box (x, y, s) in 1024-space units and draws only
# polygons, ellipses, arcs and lines, in ink, accent and paper.

def _poly(d, pts, fill) -> None:
    d.polygon([(px * SS, py * SS) for px, py in pts], fill=fill)


def _ln(d, pts, fill, width) -> None:
    d.line([(px * SS, py * SS) for px, py in pts], fill=fill,
           width=max(1, int(width * SS)), joint="curve")


def _ell(d, x0, y0, x1, y1, fill=None, outline=None, width=1) -> None:
    d.ellipse([x0 * SS, y0 * SS, x1 * SS, y1 * SS], fill=fill,
              outline=outline, width=max(1, int(width * SS)))


def icon_shield(d, x: float, y: float, s: float) -> None:
    """A shield with a keyhole: a cyberattack on intelligence systems."""
    cx, half = x + 0.50 * s, 0.34 * s
    _poly(d, [(cx - half, y + 0.12 * s), (cx + half, y + 0.12 * s),
              (cx + half, y + 0.46 * s), (cx, y + 0.92 * s),
              (cx - half, y + 0.46 * s)], ACCENT)
    _ell(d, cx - 0.085 * s, y + 0.34 * s, cx + 0.085 * s, y + 0.51 * s, PAPER)
    _poly(d, [(cx - 0.042 * s, y + 0.46 * s), (cx + 0.042 * s, y + 0.46 * s),
              (cx + 0.070 * s, y + 0.68 * s), (cx - 0.070 * s, y + 0.68 * s)],
          PAPER)
    for r in (0.13, 0.22):
        d.arc([(cx + 0.08 * s - r * s) * SS, (y + 0.08 * s - r * s) * SS,
               (cx + 0.08 * s + r * s) * SS, (y + 0.08 * s + r * s) * SS],
              start=268, end=352, fill=INK, width=max(1, int(0.028 * s * SS)))


def icon_ship(d, x: float, y: float, s: float) -> None:
    """A warship struck by drones: hull, mast, impact burst, wake."""
    _ln(d, [(x + 0.03 * s, y + 0.87 * s), (x + 0.97 * s, y + 0.87 * s)], HAIR,
        0.020)
    _poly(d, [(x + 0.09 * s, y + 0.57 * s), (x + 0.91 * s, y + 0.57 * s),
              (x + 0.76 * s, y + 0.82 * s), (x + 0.21 * s, y + 0.82 * s)], INK)
    _poly(d, [(x + 0.38 * s, y + 0.40 * s), (x + 0.63 * s, y + 0.40 * s),
              (x + 0.63 * s, y + 0.58 * s), (x + 0.38 * s, y + 0.58 * s)], INK)
    _ln(d, [(x + 0.505 * s, y + 0.40 * s), (x + 0.505 * s, y + 0.16 * s)], INK,
        0.024)
    _ln(d, [(x + 0.505 * s, y + 0.16 * s), (x + 0.70 * s, y + 0.09 * s)], INK,
        0.018)
    bx, by, r = x + 0.29 * s, y + 0.49 * s, 0.15 * s
    star = []
    for i in range(12):
        rad = r if i % 2 == 0 else r * 0.38
        ang = math.radians(i * 30.0)
        star.append((bx + rad * math.cos(ang), by + rad * math.sin(ang)))
    _poly(d, star, ACCENT)
    _ln(d, [(x + 0.18 * s, y + 0.93 * s), (x + 0.38 * s, y + 0.93 * s)], MUTED,
        0.022)
    _ln(d, [(x + 0.56 * s, y + 0.93 * s), (x + 0.76 * s, y + 0.93 * s)], MUTED,
        0.022)


def icon_heli(d, x: float, y: float, s: float) -> None:
    """A medevac helicopter: aid staff pulled out of a war zone."""
    _ln(d, [(x + 0.12 * s, y + 0.15 * s), (x + 0.86 * s, y + 0.15 * s)], INK,
        0.028)
    _ln(d, [(x + 0.47 * s, y + 0.15 * s), (x + 0.47 * s, y + 0.32 * s)], INK,
        0.028)
    _ell(d, x + 0.15 * s, y + 0.29 * s, x + 0.63 * s, y + 0.63 * s, INK)
    _poly(d, [(x + 0.57 * s, y + 0.35 * s), (x + 0.93 * s, y + 0.33 * s),
              (x + 0.93 * s, y + 0.43 * s), (x + 0.57 * s, y + 0.47 * s)], INK)
    _poly(d, [(x + 0.85 * s, y + 0.19 * s), (x + 0.94 * s, y + 0.21 * s),
              (x + 0.93 * s, y + 0.43 * s)], INK)
    ccx, ccy, arm, th = x + 0.39 * s, y + 0.46 * s, 0.078 * s, 0.025 * s
    _poly(d, [(ccx - th, ccy - arm), (ccx + th, ccy - arm),
              (ccx + th, ccy + arm), (ccx - th, ccy + arm)], PAPER)
    _poly(d, [(ccx - arm, ccy - th), (ccx + arm, ccy - th),
              (ccx + arm, ccy + th), (ccx - arm, ccy + th)], PAPER)
    _ln(d, [(x + 0.18 * s, y + 0.75 * s), (x + 0.60 * s, y + 0.75 * s)], INK,
        0.024)
    _ln(d, [(x + 0.27 * s, y + 0.63 * s), (x + 0.27 * s, y + 0.75 * s)], INK,
        0.020)
    _ln(d, [(x + 0.51 * s, y + 0.63 * s), (x + 0.51 * s, y + 0.75 * s)], INK,
        0.020)


def icon_globe(d, x: float, y: float, s: float) -> None:
    """A globe with a flame: climate talks that ended without a deal."""
    cx, cy, r = x + 0.40 * s, y + 0.39 * s, 0.33 * s
    _ell(d, cx - r, cy - r, cx + r, cy + r, outline=INK, width=0.026)
    _ln(d, [(cx - r, cy), (cx + r, cy)], INK, 0.018)
    for f in (0.55, 0.92):
        hw = r * math.sqrt(max(0.0, 1 - f * f))
        _ln(d, [(cx - hw, cy - r * f), (cx + hw, cy - r * f)], HAIR, 0.014)
        _ln(d, [(cx - hw, cy + r * f), (cx + hw, cy + r * f)], HAIR, 0.014)
    _ell(d, cx - r * 0.42, cy - r, cx + r * 0.42, cy + r, outline=INK,
         width=0.016)
    fx = x + 0.80 * s
    _poly(d, [(fx, y + 0.52 * s), (fx + 0.11 * s, y + 0.71 * s),
              (fx + 0.08 * s, y + 0.86 * s), (fx - 0.01 * s, y + 0.93 * s),
              (fx - 0.09 * s, y + 0.85 * s), (fx - 0.08 * s, y + 0.72 * s),
              (fx - 0.02 * s, y + 0.61 * s)], ACCENT)


ICONS = {"shield": icon_shield, "ship": icon_ship,
         "heli": icon_heli, "globe": icon_globe}


# --- layout (all in 1024-space units) ---------------------------------------
GRID_TOP = 132
GRID_BOTTOM = 898
GUTTER = 18
PAD = 18
BAND_H = 136
H_SIZE = 37
H_LEAD = 1.10
B_SIZE = 22
B_LEAD = 1.34
TAG_SIZE = 12
NUM_SIZE = 16
ICON_SIZE = 122


def _panel(d, story, px: float, py: float, pw: float, ph: float,
           faces) -> dict:
    """Draw one panel and return what was measured about it."""
    f_head, f_body, f_tag, f_num, f_cap = faces
    pr, pb = px + pw, py + ph
    d.rectangle([px * SS, py * SS, pr * SS, pb * SS], outline=HAIR,
                width=max(1, int(1.3 * SS)))

    # picture band across the panel head: pictogram left, place right
    d.rectangle([(px + 1) * SS, (py + 1) * SS, (pr - 1) * SS,
                 (py + BAND_H) * SS], fill=TINT)
    d.line([(px + 1) * SS, (py + BAND_H) * SS, (pr - 1) * SS,
            (py + BAND_H) * SS], fill=HAIR, width=max(1, int(1 * SS)))
    ix = px + PAD
    iy = py + (BAND_H - ICON_SIZE) / 2
    ICONS[story["icon"]](d, ix, iy, ICON_SIZE)

    cx = ix + ICON_SIZE + 16
    cw = pr - PAD - cx
    put(d, cx, py + 40, "STORY " + story["num"], f_tag, MUTED, 2.0,
        f"{story['num']}-label")
    put(d, cx, py + 78, story["place"], f_cap, INK, label=f"{story['num']}-place")
    assert tw(f_cap, story["place"]) <= cw, (
        "place caption too wide", story["num"], tw(f_cap, story["place"]), cw)

    tx = px + PAD
    twidth = pw - 2 * PAD
    ty = py + BAND_H + 14

    # section tag on its own line, over a hairline
    put(d, tx, ty + asc(f_tag), story["tag"], f_tag, ACCENT, 1.6,
        f"{story['num']}-tag")
    assert tw(f_tag, story["tag"], 1.6) <= twidth, ("tag too wide", story["num"])
    y = ty + asc(f_tag) + 7.0
    d.line([tx * SS, y * SS, (tx + twidth) * SS, y * SS], fill=HAIR,
           width=max(1, int(1 * SS)))

    # headline: two hand-broken lines, each measured against the column
    base = y + 7.0 + asc(f_head)
    for line in story["head"]:
        assert tw(f_head, line) <= twidth, (
            "headline overflows", story["num"], line, tw(f_head, line), twidth)
        put(d, tx, base, line, f_head, INK, label=f"{story['num']}-head")
        base += H_SIZE * H_LEAD
    h_bottom = base - H_SIZE * H_LEAD + desc(f_head)

    # summary: exactly three wrapped lines ending in a period
    lines = wrap(story["body"], f_body, twidth)
    assert len(lines) == 3, ("summary must set in three lines",
                             story["num"], lines)
    assert story["body"].endswith("."), story["num"]
    bbase = h_bottom + 7.0 + asc(f_body)
    for line in lines:
        put(d, tx, bbase, line, f_body, INK, label=f"{story['num']}-body")
        bbase += B_SIZE * B_LEAD
    bottom = bbase - B_SIZE * B_LEAD + desc(f_body)
    assert bottom + 6 <= pb, ("summary runs past the panel", story["num"],
                              bottom, pb)
    return {"num": story["num"], "head": " / ".join(story["head"]),
            "lines": lines, "bottom": round(bottom, 1),
            "panel": (round(px), round(py), round(pr), round(pb))}


def run(out_path: str) -> dict:
    """Draw the page, assert that everything fits, save it, return a report."""
    img = Image.new("RGB", (W * SS, H * SS), PAPER)
    d = ImageDraw.Draw(img)

    f_kick = bold(12)
    f_mast = bold(48)
    f_sub = book(14)
    f_head = bold(H_SIZE)
    f_body = book(B_SIZE)
    f_tag = bold(TAG_SIZE)
    f_num = bold(NUM_SIZE)
    f_cap = bold(20)
    f_also = bold(11)
    f_tick = book(14)
    f_foot = book(13)

    # ---- masthead -----------------------------------------------------
    put(d, M, 13 + asc(f_kick), "THE DAY IN FOUR STORIES", f_kick, ACCENT, 2.8,
        "kicker")
    mast = "WEDNESDAY 25 NOVEMBER 2026"
    assert tw(f_mast, mast) <= W - 2 * M, ("masthead too wide", tw(f_mast, mast))
    put(d, M, 86, mast, f_mast, INK, label="masthead")
    d.rectangle([M * SS, 94 * SS, (W - M) * SS, 98 * SS], fill=ACCENT)
    put(d, M, 118, "UNITED STATES  \u00b7  LIBYA  \u00b7  DR CONGO  \u00b7  "
        "T\u00dcRKIYE", f_sub, MUTED, 0.8, "dateline")

    # ---- four panels --------------------------------------------------
    pw = (W - 2 * M - GUTTER) / 2
    ph = (GRID_BOTTOM - GRID_TOP - GUTTER) / 2
    faces = (f_head, f_body, f_tag, f_num, f_cap)
    report = []
    for i, story in enumerate(STORIES):
        px = M + (i % 2) * (pw + GUTTER)
        py = GRID_TOP + (i // 2) * (ph + GUTTER)
        report.append(_panel(d, story, px, py, pw, ph, faces))

    # ---- also on the day ----------------------------------------------
    d.line([M * SS, 906 * SS, (W - M) * SS, 906 * SS], fill=HAIR,
           width=max(1, int(1 * SS)))
    put(d, M, 924, "ALSO ON THE DAY", f_also, ACCENT, 2.4, "also")
    for j, pair in enumerate((TICKER[0:2], TICKER[2:4])):
        line = "   \u00b7   ".join(pair)
        assert tw(f_tick, line) <= W - 2 * M, ("ticker too wide", line)
        put(d, M, 946 + 19 * j, line, f_tick, INK, label=f"ticker-{j}")

    # ---- footer -------------------------------------------------------
    d.line([M * SS, 974 * SS, (W - M) * SS, 974 * SS], fill=HAIR,
           width=max(1, int(1 * SS)))
    put(d, M, 997, "One page, one day \u00b7 Wednesday 25 November 2026",
        f_foot, MUTED, label="footer-left")
    right = "WORLD NEWS"
    put(d, W - M - tw(f_foot, right, 1.6) - 1, 997, right, f_foot, ACCENT, 1.6,
        "footer-right")

    # ---- fit audit ----------------------------------------------------
    for label, (x0, y0, x1, y1) in BOXES:
        assert x0 >= 0 and y0 >= 0 and x1 <= W and y1 <= H, (
            "text outside the canvas", label, x0, y0, x1, y1)
    for i, story in enumerate(STORIES):
        px = M + (i % 2) * (pw + GUTTER)
        py = GRID_TOP + (i // 2) * (ph + GUTTER)
        for label, (x0, y0, x1, y1) in BOXES:
            if not label.startswith(story["num"] + "-"):
                continue
            assert px + 3 <= x0 and x1 <= px + pw - 3, (label, x0, x1, px, pw)
            assert py + 3 <= y0 and y1 <= py + ph - 3, (label, y0, y1, py, ph)

    img = img.resize((W, H), Image.LANCZOS)
    img.save(out_path, format="PNG", optimize=True)
    return {"path": out_path, "stories": report, "boxes": len(BOXES)}


def main() -> int:
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "entry.png")
    rep = run(out)
    size = os.path.getsize(out)
    assert size <= 1024 * 1024, ("image too large", size)
    print(f"wrote {rep['path']}  {size} bytes  {W}x{H}  "
          f"{rep['boxes']} text runs")
    for s in rep["stories"]:
        print(f"  {s['num']} {s['head']}")
        print(f"      {len(s['lines'])}-line summary, ends y={s['bottom']}, "
              f"panel bottom {s['panel'][3]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
