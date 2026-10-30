import os
import subprocess

INPUT_DIR = "input_dds"
OUTPUT_DIR = "output_png"

os.makedirs(INPUT_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

for file in os.listdir(INPUT_DIR):
    if not file.lower().endswith(".dds"):
        continue

    src = os.path.join(INPUT_DIR, file)
    dst = os.path.join(OUTPUT_DIR, file.replace(".dds", ".png"))

    cmd = [
        "texconv",
        "-ft", "png",                 # Force output file type to PNG
        "-f", "R8G8B8A8_UNORM_SRGB",  # Save with standard non-linear sRGB gamma encoding
        "-y",                         # Overwrite existing files
        "-o", OUTPUT_DIR,             # Output directory destination
        "-srgbi",
        "-srgbo",
        src                           # Source DDS file path
    ]

    subprocess.run(cmd, check=True)
