import hashlib
import json
import os
from pathlib import Path
from typing import Union

from PIL import Image, UnidentifiedImageError
from tqdm import tqdm
from signwriting_images import signwriting_to_sized_image

SIZE = 256

TRAIN_DIR = Path(__file__).parent.parent / "train"
TRAIN_A_DIR = TRAIN_DIR / "A"
TRAIN_B_DIR = TRAIN_DIR / "B"

os.makedirs(TRAIN_DIR, exist_ok=True)
os.makedirs(TRAIN_A_DIR, exist_ok=True)
os.makedirs(TRAIN_B_DIR, exist_ok=True)

DATASETS_DIR = Path(__file__).parent.parent / "datasets"


def signwriting_file_to_image(fsw_file: Path, output: Union[str, Path], size=256):
    # Open signwriting image
    signwriting = Image.open(fsw_file)
    w, h = signwriting.size
    signwriting = signwriting.resize((w * 2, h * 2), Image.NEAREST)

    if signwriting.width > size or signwriting.height > size:
        # resize to fit 256x256
        scale = size / max(signwriting.width, signwriting.height)
        signwriting = signwriting.resize((int(signwriting.width * scale), int(signwriting.height * scale)), Image.NEAREST)

    # then paste it on a white background SIZExSIZE RGB image
    background = Image.new('RGB', (size, size), (255, 255, 255))
    x_offset = (size - signwriting.width) // 2
    y_offset = (size - signwriting.height) // 2
    offset = (x_offset, y_offset)
    mask = signwriting if signwriting.mode == 'RGBA' else None
    background.paste(signwriting, offset, mask)

    background.save(output)


for dataset in DATASETS_DIR.iterdir():
    if not dataset.is_dir():
        continue

    print(f"Processing {dataset}...")
    WRITING_FILE = dataset / "writing.json"
    if not WRITING_FILE.exists():
        continue

    with open(WRITING_FILE, 'r') as f:
        writings = json.load(f)

    for writing in tqdm(writings):
        illustration_path = dataset / writing["file"]
        if not illustration_path.exists():
            raise Exception(f"Illustration {illustration_path} does not exist")

        illustration_hash = hashlib.md5(illustration_path.read_bytes()).hexdigest()
        a_path = TRAIN_A_DIR / f"{illustration_hash}.png"
        b_path = TRAIN_B_DIR / f"{illustration_hash}.png"

        if not a_path.exists():
            try:
                illustration = Image.open(illustration_path)
                if illustration.width < SIZE or illustration.height < SIZE:
                    continue
            except UnidentifiedImageError:
                print(f"\tCould not open {illustration_path}")
                continue

            # resize illustration (not square) such that the larger side is SIZE
            larger_side = max(illustration.width, illustration.height)
            scale = SIZE / larger_side
            illustration = illustration.resize((int(illustration.width * scale), int(illustration.height * scale)))

            # then paste it on a white background SIZExSIZE RGB image
            background = Image.new('RGB', (SIZE, SIZE), (255, 255, 255))
            x = (SIZE - illustration.width) // 2
            y = (SIZE - illustration.height) // 2
            background.paste(illustration, (x, y), illustration if illustration.mode == 'RGBA' else None)

            # save illustration with name hash of illustration_path
            background.save(a_path)

        if a_path.exists() and not b_path.exists():
            if "fsw" in writing:
                signwriting_to_sized_image(writing["fsw"], b_path, size=SIZE)
            elif "fsw_file" in writing:
                # FYI: These images are not the same as the ones generated by signwriting_to_image.
                # They are not anti-aliased.
                signwriting_file_to_image(dataset / writing["fsw_file"], b_path, size=SIZE)
            else:
                raise Exception("Neither fsw nor fsw_file in writing")
