#!/usr/bin/env python3
"""Process pizzeria logo for thermal printer ESC/POS output.

For RGBA images: extract alpha channel, threshold → black logo on white.
For regular images: grayscale → optional invert → threshold → b/w.
Always trims whitespace, pads to 24-dot boundaries, saves as P4 PBM.
"""

import argparse
import os
import sys

from PIL import Image, ImageOps

DEFAULT_WIDTH = 320
PRINTER_WIDTHS = {
    "58mm": 288,
    "80mm": 384,
    "112mm": 544,
}


def process_logo(
    input_path,
    output_path,
    width=DEFAULT_WIDTH,
    threshold=128,
    invert=False,
):
    img = Image.open(input_path)

    if img.mode == "RGBA":
        alpha = img.split()[3]
        img = alpha.point(lambda x: 0 if x > threshold else 255, "1")
    else:
        img = img.convert("L")
        if invert:
            img = ImageOps.invert(img)
        img = img.point(lambda x: 0 if x < threshold else 255, "1")

    ratio = width / img.width
    new_height = int(img.height * ratio)
    img = img.resize((width, new_height), Image.NEAREST)

    # Build P4 PBM manually for maximum control
    # Trim empty rows (all white) from top and bottom, keeping padding
    top_padding = 0
    bottom_padding = 0
    pixels = list(img.getdata())
    w, h = img.size

    # Find first row with any black pixel
    first_content = 0
    for y in range(h):
        row = pixels[y * w : (y + 1) * w]
        if any(p == 0 for p in row):
            first_content = y
            break
    else:
        first_content = h

    # Find last row with any black pixel
    last_content = h - 1
    for y in range(h - 1, -1, -1):
        row = pixels[y * w : (y + 1) * w]
        if any(p == 0 for p in row):
            last_content = y
            break

    trim_top = max(0, first_content - top_padding)
    trim_bottom = min(h - 1, last_content + bottom_padding)

    # Round trim_top down to multiple of 24, trim_bottom up to multiple of 24
    trim_top = (trim_top // 8) * 8
    trim_bottom = ((trim_bottom // 8) + 1) * 8
    trim_bottom = min(h, trim_bottom)

    trimmed_h = trim_bottom - trim_top
    # Extract trimmed rows
    trimmed_pixels = pixels[trim_top * w : trim_bottom * w]

    # Rebuild trimmed image
    trimmed = Image.new("1", (w, trimmed_h))
    trimmed.putdata(trimmed_pixels)

    # PIL mode "1": 0 = black, 1 = white, MSB-first, padded to byte boundary
    # PBM P4 format:  1 = black, 0 = white, MSB-first, padded to byte boundary
    # → Need to invert all bits
    raw = trimmed.tobytes("raw", "1")
    inverted = bytes(b ^ 0xFF for b in raw)

    with open(output_path, "wb") as f:
        f.write(f"P4\n{trimmed.width} {trimmed.height}\n".encode("ascii"))
        f.write(inverted)

    # Also save a PNG preview for visual inspection
    preview_path = os.path.splitext(output_path)[0] + "_preview.png"
    trimmed.save(preview_path)
    print(f"Saved preview: {preview_path}")

    row_bytes = (trimmed.width + 7) // 8
    bands = trimmed.height // 24
    file_size = os.path.getsize(output_path)
    print(f"Logo PBM: {trimmed.width}x{trimmed.height} pixels, {row_bytes}x{bands} bands")
    print(f"File size: {file_size} bytes")
    print(f"Vertical bands (24-dot): {bands}")
    print(f"Bytes per band: {trimmed.width * 3}")
    print(f"Total ESC/POS data (approx): {bands * trimmed.width * 3} bytes")
    print(f"Threshold: {threshold}, Invert: {invert}")
    print(f"Trimmed: rows {trim_top}-{trim_bottom} of {h}")

    return output_path


def main():
    parser = argparse.ArgumentParser(description="Process pizzeria logo for thermal printer")
    parser.add_argument("input", nargs="?", default="images/pizzeria_logo.png",
                        help="Input PNG path")
    parser.add_argument("-o", "--output", default="images/pizzeria_logo.pbm",
                        help="Output PBM path")
    parser.add_argument("-w", "--width", type=int, default=DEFAULT_WIDTH,
                        help=f"Printer width in dots (default: {DEFAULT_WIDTH})")
    parser.add_argument("-t", "--threshold", type=int, default=128,
                        help="Threshold 0-255 (default: 128)")
    parser.add_argument("--invert", action="store_true",
                        help="Force image inversion (only for non-RGBA images)")
    parser.add_argument("-p", "--printer", choices=PRINTER_WIDTHS.keys(),
                        help="Printer paper width preset")

    args = parser.parse_args()

    if args.printer:
        args.width = PRINTER_WIDTHS[args.printer]

    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)

    input_path = os.path.join(project_root, args.input)
    output_path = os.path.join(project_root, args.output)

    if not os.path.exists(input_path):
        print(f"Error: input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    process_logo(
        input_path=input_path,
        output_path=output_path,
        width=args.width,
        threshold=args.threshold,
        invert=args.invert,
    )


if __name__ == "__main__":
    main()
