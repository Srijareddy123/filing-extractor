"""Render part of the `make demo` output as a PNG for the README (terminal-style image)."""

from __future__ import annotations

import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FONT = "/System/Library/Fonts/Menlo.ttc"
KEEP = ("1.", "3.", "4.", "5.", "6.")
WIDTH_CHARS = 112


def main() -> None:
    text = Path("outputs/demo/demo_output.txt").read_text(encoding="utf-8")
    sections = text.split("\n=== ")
    lines = ["$ make demo", ""]
    for block in sections:
        block = block.removeprefix("=== ")
        if block.startswith(KEEP):
            title, _, body = block.partition("\n")
            lines.append(f"=== {title}")
            for raw in body.strip("\n").splitlines():
                lines.extend(textwrap.wrap(raw, WIDTH_CHARS, subsequent_indent="    ") or [""])
            lines.append("")
    font = ImageFont.truetype(FONT, 15)
    line_h = 21
    pad = 22
    width = int(font.getlength("M" * WIDTH_CHARS)) + 2 * pad
    height = line_h * len(lines) + 2 * pad
    img = Image.new("RGB", (width, height), (22, 27, 34))
    draw = ImageDraw.Draw(img)
    for i, line in enumerate(lines):
        color = (121, 192, 255) if line.startswith("===") else (201, 209, 217)
        if line.startswith("$"):
            color = (126, 231, 135)
        draw.text((pad, pad + i * line_h), line, font=font, fill=color)
    out = Path("docs/demo.png")
    out.parent.mkdir(exist_ok=True)
    img.save(out)
    print(f"wrote {out} ({width}x{height})")


if __name__ == "__main__":
    main()
