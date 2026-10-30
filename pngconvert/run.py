#!/usr/bin/env python3
"""Batch-convert DDS textures to PNG (sRGB, 8-bit RGBA) using texconv.

Usage:
    python run_1.py                    # input_dds/ -> output_png/
    python run_1.py -i tex -o out -r   # custom folders, include subfolders
    python run_1.py --no-srgb          # treat images as linear instead of sRGB
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

DEFAULT_INPUT = Path("input_dds")
DEFAULT_OUTPUT = Path("output_png")


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Convert DDS files to PNG using texconv.")
    p.add_argument("-i", "--input", type=Path, default=DEFAULT_INPUT,
                   help=f"folder with DDS files (default: {DEFAULT_INPUT})")
    p.add_argument("-o", "--output", type=Path, default=DEFAULT_OUTPUT,
                   help=f"folder for PNG files (default: {DEFAULT_OUTPUT})")
    p.add_argument("-r", "--recursive", action="store_true",
                   help="also search subfolders (structure is preserved)")
    p.add_argument("--no-srgb", action="store_true",
                   help="don't apply sRGB handling (use linear R8G8B8A8_UNORM)")
    return p.parse_args()


def scan(input_dir: Path, recursive: bool) -> list[Path]:
    """Return all .dds files in input_dir (case-insensitive)."""
    pattern = "**/*" if recursive else "*"
    return sorted(
        p for p in input_dir.glob(pattern)
        if p.is_file() and p.suffix.lower() == ".dds"
    )


def convert(path: Path, args: argparse.Namespace) -> bool:
    """Run texconv on a single DDS file. Returns True on success."""
    relative_parent = path.parent.relative_to(args.input)
    out_dir = args.output / relative_parent
    out_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        "texconv",
        "-ft", "png",           # output file type: PNG
        "-y",                   # overwrite existing files
        "-o", str(out_dir),
    ]
    if args.no_srgb:
        cmd += ["-f", "R8G8B8A8_UNORM"]
    else:
        cmd += [
            "-f", "R8G8B8A8_UNORM_SRGB",  # standard sRGB-encoded 8-bit RGBA
            "-srgbi",                     # treat input as sRGB
            "-srgbo",                     # write output as sRGB
        ]
    cmd.append(str(path))

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  x Failed: {path}")
        detail = (result.stderr or result.stdout).strip()
        if detail:
            print("    " + detail.replace("\n", "\n    "))
        return False
    return True


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #

def main() -> int:
    args = parse_args()

    if shutil.which("texconv") is None:
        print("Error: 'texconv' was not found on your PATH.")
        print("Get it from https://github.com/microsoft/DirectXTex/releases")
        return 1

    args.input.mkdir(parents=True, exist_ok=True)
    args.output.mkdir(parents=True, exist_ok=True)

    files = scan(args.input, args.recursive)
    if not files:
        print(f"No DDS files to convert. Put some in '{args.input}/' and run again.")
        return 0

    print(f"Converting {len(files)} file(s) to PNG...\n")
    succeeded = 0
    failed = 0
    for i, path in enumerate(files, start=1):
        print(f"[{i}/{len(files)}] {path.name}")
        if convert(path, args):
            succeeded += 1
        else:
            failed += 1

    print(f"\nDone! {succeeded} converted, {failed} failed.")
    print(f"Output folder: {args.output.resolve()}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
