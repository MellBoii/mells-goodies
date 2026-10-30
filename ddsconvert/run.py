import os
import subprocess
from PIL import Image

INPUT_DIR = "input_png"
OUTPUT_DIR = "output_dds"

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(INPUT_DIR, exist_ok=True)

def is_power_of_two(n):
    return (n != 0) and (n & (n-1) == 0)

files = []
incorrect_files = []
for file in os.listdir(INPUT_DIR):
    if not file.lower().endswith(".png"):
        continue
    image = Image.open(file)
    iw, ih = image.size
    if not is_power_of_two(iw) or not is_power_of_two(ih):
        incorrect_files.append(file)
    else:
        files.append(file)

if incorrect_files:
    answer = input(
        (
            "HANG ON THERE BUSTER!\nSome of your image files' "
            "dimensions are not in a power of 2 (meaning, they "
            "likely will error on most games).\n"
            f"{', '.join(incorrect_files)}\n"
            "If you wish to continue either way, type in Y, otherwise N (will skip incorrect files)"
        )
    )
    if answer.upper() == 'Y':
        files.extend(incorrect_files)
    else:
        pass

if not files:
    print('No files found...\nA input_png folder has been generated incase it doesn\'t exist; paste your files there.')
    exit()

for file in files:
    src = os.path.join(INPUT_DIR, file)
    dst = os.path.join(OUTPUT_DIR, file.replace(".png", ".dds"))

    cmd = [
        "texconv",
        "-f", "DXT5",      # BC3 / DXT5
        "-m", "0",             # generate full mip chain
        "-srgb",            # maintain srgb
        "-y",            # replace if exists
        "-o", OUTPUT_DIR,
        src
    ]

    subprocess.run(cmd, check=True)
