#!/usr/bin/env python3
"""Copy this entry's image to the output directory.

The image beside this file, entry.png, is drawn by draw_news.py: one page for
Wednesday 25 November 2026, four stories in a 2x2 grid. This program writes
exactly those bytes to the path the grader reads, and checks the copy byte for
byte with sha256 so a truncated or altered file can never be submitted.

It reads no network, takes no input and uses only the standard library, so both
of its runs write the same bytes.

Run:  python3 main.py
      Writes the image to /output/entry.png (or, when MAKEFUN_OUTPUT_DIR is
      set, to that directory instead).
"""

from __future__ import annotations

import hashlib
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCE = os.path.join(HERE, "entry.png")
MAX_BYTES = 1024 * 1024
SIZE = 1024


def sha256_of(path: str) -> str:
    """The sha256 of a file, read in one go."""
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def check_png(path: str, digest: str) -> None:
    """Refuse anything that is not a whole 1024x1024 PNG under 1 MiB."""
    size = os.path.getsize(path)
    if size > MAX_BYTES:
        raise SystemExit(f"error: {size} bytes exceeds the 1 MiB limit")
    with open(path, "rb") as fh:
        head = fh.read(33)
    if head[:8] != b"\x89PNG\r\n\x1a\n":
        raise SystemExit("error: the file is not a PNG")
    if head[12:16] != b"IHDR":
        raise SystemExit("error: the PNG does not start with IHDR")
    width = int.from_bytes(head[16:20], "big")
    height = int.from_bytes(head[20:24], "big")
    if (width, height) != (SIZE, SIZE):
        raise SystemExit(f"error: the image is {width}x{height}, not 1024x1024")
    if not digest:
        raise SystemExit("error: empty digest")


def main() -> int:
    if not os.path.exists(SOURCE):
        raise SystemExit(f"error: {SOURCE} is missing; run python3 draw_news.py")
    before = sha256_of(SOURCE)
    check_png(SOURCE, before)

    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR") or "/output"
    os.makedirs(out_dir, exist_ok=True)
    target = os.path.join(out_dir, "entry.png")
    shutil.copyfile(SOURCE, target)

    after = sha256_of(target)
    if after != before:
        raise SystemExit(f"error: copy differs: {before} != {after}")
    check_png(target, after)

    print(f"wrote {target} ({os.path.getsize(target)} bytes)")
    print(f"sha256 {after} (verified before and after the copy)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
