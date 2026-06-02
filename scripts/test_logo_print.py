#!/usr/bin/env python3
"""Test script: generate or print the static ESC/POS logo.

Usage:
  python3 scripts/test_logo_print.py           # Generate .escpos from .pbm
  python3 scripts/test_logo_print.py --print   # Send to printer via lp
  python3 scripts/test_logo_print.py -o FILE   # Save to custom path
"""

import argparse
import os
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
PBM_PATH = os.path.join(PROJECT_ROOT, "images/pizzeria_logo.pbm")
ESC_PATH = os.path.join(PROJECT_ROOT, "images/pizzeria_logo.escpos")
RAW_PATH = os.path.join(PROJECT_ROOT, "images/pizzeria_logo_raw.escpos")

ESC = b"\x1b"


def build_escpos_from_pbm(pbm_path):
    """Convert PBM to ESC/POS bytes (8-dot bands, centered)."""
    with open(pbm_path, "rb") as f:
        magic = f.readline().strip()
        line = f.readline().strip()
        while line.startswith(b"#"):
            line = f.readline().strip()
        parts = line.split()
        if len(parts) == 1:
            parts += f.readline().strip().split()
        width, height = int(parts[0]), int(parts[1])
        data = f.read()

    row_bytes = (width + 7) // 8
    bands = height // 8
    PRINTABLE_WIDTH = 384
    margin = (PRINTABLE_WIDTH - width) // 2

    result = bytearray()
    result.extend(ESC + b"a\x01")  # center align

    for band in range(bands):
        band_y = band * 8
        result.extend(ESC + b"*\x00" + bytes([width & 0xFF, (width >> 8) & 0xFF]))
        for col in range(width):
            bt = 0
            for dy in range(8):
                y = band_y + dy
                if y < height and data[y * row_bytes + (col // 8)] & (1 << (7 - (col % 8))):
                    bt |= (1 << (7 - dy))
            result.append(bt)
        result.extend(ESC + b"J\x08")

    result.extend(ESC + b"d\x03" + ESC + b"i")
    return bytes(result)


def main():
    parser = argparse.ArgumentParser(description="Generate/print static ESC/POS logo")
    parser.add_argument("--print", action="store_true", help="Send to printer")
    parser.add_argument("--printer", default="XP-80", help="CUPS printer name")
    parser.add_argument("-o", "--output", default=None, help="Output .escpos path")
    args = parser.parse_args()

    # Check for pre-built ESC/POS file — use it directly if available
    esc_path = args.output or ESC_PATH
    raw_path = args.output.replace(".escpos", "_raw.escpos") if args.output else RAW_PATH

    if not os.path.exists(PBM_PATH):
        print("Error: PBM file not found: %s" % PBM_PATH, file=sys.stderr)
        print("Run: python3 scripts/process_logo.py first", file=sys.stderr)
        sys.exit(1)

    escpos = build_escpos_from_pbm(PBM_PATH)
    print("ESC/POS data: %d bytes" % len(escpos))

    with open(esc_path, "wb") as f:
        f.write(escpos)
    print("Saved: %s" % esc_path)

    raw = escpos[:-5] if escpos.endswith(ESC + b"d\x03" + ESC + b"i") else escpos
    with open(raw_path, "wb") as f:
        f.write(raw)
    print("Saved: %s (%d bytes, no cut/feed)" % (raw_path, len(raw)))

    if args.print:
        print("Sending to printer '%s'..." % args.printer)
        result = subprocess.run(
            ["lp", "-d", args.printer, "-o", "raw"],
            input=escpos,
            capture_output=True,
            timeout=10,
        )
        if result.returncode == 0:
            print("Print job submitted successfully.")
        else:
            print("Print failed (rc=%d): %s" % (
                result.returncode, result.stderr.decode(errors="replace")))


if __name__ == "__main__":
    main()
