#!/usr/bin/env python3
"""Batch-convert PNG textures to DDS (BC3/DXT5 + full mip chain) using texconv.

Usage:
    python run.py                      # input_png/ -> output_dds/
    python run.py -i art -o out -r     # custom folders, include subfolders
    python run.py --yes                # convert non-power-of-two images too
    python run.py --skip-invalid       # silently skip non-power-of-two images
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, UnidentifiedImageError

DEFAULT_INPUT = Path("input_png")
DEFAULT_OUTPUT = Path("output_dds")


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def is_power_of_two(n: int) -> bool:
    return n > 0 and (n & (n - 1)) == 0


@dataclass
class Texture:
    path: Path
    width: int
    height: int

    @property
    def valid(self) -> bool:
        return is_power_of_two(self.width) and is_power_of_two(self.height)

    @property
    def label(self) -> str:
        return f"{self.path}  ({self.width}x{self.height})"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Convert PNG files to DDS using texconv.")
    p.add_argument("-i", "--input", type=Path, default=DEFAULT_INPUT,
                   help=f"folder with PNG files (default: {DEFAULT_INPUT})")
    p.add_argument("-o", "--output", type=Path, default=DEFAULT_OUTPUT,
                   help=f"folder for DDS files (default: {DEFAULT_OUTPUT})")
    p.add_argument("-f", "--format", default="DXT5",
                   help="texconv compression format (default: DXT5 / BC3)")
    p.add_argument("-r", "--recursive", action="store_true",
                   help="also search subfolders (structure is preserved)")
    p.add_argument("--no-srgb", action="store_true",
                   help="don't treat the images as sRGB")
    group = p.add_mutually_exclusive_group()
    group.add_argument("-y", "--yes", action="store_true",
                       help="convert non-power-of-two images without asking")
    group.add_argument("--skip-invalid", action="store_true",
                       help="skip non-power-of-two images without asking")
    return p.parse_args()


def scan(input_dir: Path, recursive: bool) -> tuple[list[Texture], list[Texture]]:
    """Return (valid, invalid) textures found in input_dir."""
    pattern = "**/*" if recursive else "*"
    valid: list[Texture] = []
    invalid: list[Texture] = []

    for path in sorted(input_dir.glob(pattern)):
        if not path.is_file() or path.suffix.lower() != ".png":
            continue
        try:
            with Image.open(path) as img:
                tex = Texture(path, *img.size)
        except (UnidentifiedImageError, OSError) as exc:
            print(f"  ! Couldn't read {path}: {exc}")
            continue
        (valid if tex.valid else invalid).append(tex)

    return valid, invalid


def ask_about_invalid(invalid: list[Texture]) -> bool:
    """Ask whether non-power-of-two textures should still be converted."""
    print("\nSome images don't have power-of-two dimensions.")
    print("Many games will fail to load these textures:\n")
    for tex in invalid:
        print(f"  - {tex.label}")
    print()
    try:
        answer = input("Convert them anyway? [y/N] ").strip().lower()
    except EOFError:
        return False
    return answer in ("y", "yes")


def convert(tex: Texture, args: argparse.Namespace) -> bool:
    """Run texconv on a single texture. Returns True on success."""
    relative_parent = tex.path.parent.relative_to(args.input)
    out_dir = args.output / relative_parent
    out_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        "texconv",
        "-f", args.format,
        "-m", "0",              # full mip chain
        "-y",                   # overwrite existing files
        "-o", str(out_dir),
    ]
    if not args.no_srgb:
        cmd.append("-srgb")
    cmd.append(str(tex.path))

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  x Failed: {tex.path}")
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

    valid, invalid = scan(args.input, args.recursive)

    if invalid:
        if args.yes:
            convert_invalid = True
        elif args.skip_invalid:
            convert_invalid = False
        else:
            convert_invalid = ask_about_invalid(invalid)

        if convert_invalid:
            valid.extend(invalid)
        else:
            print(f"Skipping {len(invalid)} non-power-of-two image(s).")

    if not valid:
        print(f"\nNo PNG files to convert. Put some in '{args.input}/' and run again.")
        return 0

    print(f"\nConverting {len(valid)} file(s) to {args.format}...\n")
    succeeded = 0
    failed = 0
    for i, tex in enumerate(valid, start=1):
        print(f"[{i}/{len(valid)}] {tex.path.name}")
        if convert(tex, args):
            succeeded += 1
        else:
            failed += 1

    print(f"\nDone! {succeeded} converted, {failed} failed.")
    print(f"Output folder: {args.output.resolve()}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
