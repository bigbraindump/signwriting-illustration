import re
from xml.etree import ElementTree

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from signwriting.formats.fsw_to_sign import fsw_to_sign
from signwriting.visualizer.visualize import signwriting_to_image
from signwriting_evaluation.metrics.clip import SignWritingCLIPScore, signwriting_to_clip_image
from tqdm import tqdm


def convert_to_fsw(layout_txt_content):
    # Fixing img tags to be self-closing for XML parsing
    layout_txt_content = re.sub(r'<img([^>]+)/?>', r'<img\1/>', layout_txt_content)
    layout_txt_content = layout_txt_content.replace('&size=.7', '')

    root = ElementTree.fromstring(layout_txt_content)
    max_x, max_y = int(root.get('max_x')), int(root.get('max_y'))
    fsw = f'M{max_x + 500}x{max_y + 500}'

    for sym in root.findall('sym'):
        key = sym.find('img').get('src').split('key=')[1]
        left, top = int(sym.get('left')), int(sym.get('top'))
        fsw += f'S{key}{left + 500}x{top + 500}'
    return fsw


def signwriting_directory_to_image(directory: Path) -> Image:
    layout_path = directory / 'layout.txt'
    if not layout_path.exists():
        print(f"{directory} missing {layout_path}")
        return None, None

    with open(layout_path, 'r') as file:
        content = file.read()

    fsw = convert_to_fsw(content)

    return fsw, signwriting_to_image(fsw)
    # sign = fsw_to_sign(fsw)
    #
    # positions = [s["position"] for s in sign['symbols']]
    # min_x = min(positions, key=lambda p: p[0])[0]
    # min_y = min(positions, key=lambda p: p[1])[1]
    # max_x, max_y, = sign["box"]["position"]
    # img = Image.new('RGBA', (max_x - min_x, max_y - min_y), (255, 255, 255, 0))
    #
    # for symbol in sign['symbols']:
    #     symbol_id = symbol["symbol"][1:]
    #     try:
    #         symbol_img = Image.open(directory / f'{symbol_id}.png')
    #     except Exception as e:
    #         symbol_img = Image.open(directory / f'{symbol_id[:-1]}.png')
    #
    #     # resize symbol by 1.42
    #     scale = 1.42
    #     symbol_img = symbol_img.resize((int(symbol_img.width * scale), int(symbol_img.height * scale)))
    #
    #     # make symbol black or white, no grey
    #     # symbol_img = symbol_img.point(lambda x: 0 if x < 128 else 255, '1')
    #     array = np.array(symbol_img)
    #     array[array < 170] = 0
    #     array[array >= 170] = 255
    #     symbol_img = Image.fromarray(array)
    #
    #     x, y = symbol["position"]
    #     x, y = x - min_x, y - min_y
    #     img.paste(symbol_img, (x, y), symbol_img)
    #
    # return fsw, img


def create_images_from_layouts(directory: Path):
    images = {}

    for sub_dir in tqdm(list(directory.iterdir())):
        if not sub_dir.is_dir():
            continue

        fsw, image = signwriting_directory_to_image(sub_dir)
        if image is None:
            continue

        images[(fsw, sub_dir)] = image

        # layout_path = sub_dir / 'layout.txt'
        # if not layout_path.exists():
        #     print(f"{sub_dir} missing {layout_path}")
        #     continue
        #
        # with open(layout_path, 'r') as file:
        #     content = file.read()
        #     fsw = convert_to_fsw(content)
        #     sw_image = signwriting_to_image(fsw, antialiasing=True)
        #     new_img = Image.new('RGB', (sw_image.width, sw_image.height), (255, 255, 255))
        #     new_img.paste(sw_image, (0, 0), sw_image)
        #     images[(fsw, sub_dir)] = new_img.convert('L')

    return images


def load_gold_images(directory: Path):
    images = {}
    for image in tqdm(list(directory.glob('*.png'))):
        try:
            images[image.stem] = Image.open(image)
        except:
            pass
    return images


if __name__ == "__main__":
    glosses_directory = Path("SW_signs_glosses")

    candidates = create_images_from_layouts(glosses_directory)
    reference_directory = Path("glossen")
    references = load_gold_images(reference_directory)

    print("Candidates:", len(candidates))
    print("References:", len(references))

    clip_score = SignWritingCLIPScore()
    candidate_keys, candidate_images = zip(*candidates.items())
    reference_images = list(references.values())
    all_scores = clip_score.score_all(reference_images, candidate_images)

    matches_dir = Path("score_matches")
    matches_dir.mkdir(parents=True, exist_ok=True)

    for i, (stem, scores) in tqdm(list(enumerate(zip(references.keys(), all_scores)))):
        argmax = np.argmax(scores)

        # We can't have a perfect match since the drawing algorithms are different. a score of 1 indicates empty image
        if scores[argmax] > 0.99:
            # check if the reference image is white
            if np.all(np.array(signwriting_to_clip_image(reference_images[i])) == 255):
                continue
        # Low scores are not interesting
        # if scores[argmax] < 0.98:
        #     continue
        # for testing purposes, we

        # for testing, we only keep
        if scores[argmax] < 0.97 or scores[argmax] > 0.98:
            continue

        reference_image = reference_images[i]
        best_candidate = candidate_images[argmax]
        side_by_side = Image.new('RGB', (224 * 2, 224))
        side_by_side.paste(signwriting_to_clip_image(reference_image), (0, 0))
        side_by_side.paste(signwriting_to_clip_image(best_candidate), (224, 0))
        # draw score
        draw = ImageDraw.Draw(side_by_side)
        draw.text((0, 0), f"{scores[argmax]:.3f}", fill=(255, 0, 0))
        # draw fsw
        draw.text((0, 180), candidate_keys[argmax][0], fill=(255, 0, 0))

        side_by_side.save(matches_dir / f"{stem}.png")

    matches_dir = Path("matches")
    matches_dir.mkdir(parents=True, exist_ok=True)

    # Reverse loop
    has_matches = 0
    for i, (stem, reference) in enumerate(tqdm(list(references.items()))):
        matching_candidates = [(fsw, cand) for fsw, cand in candidates.items() if cand.size == reference.size]
        similarity = [all_scores[i][candidate_keys.index(fsw)] for fsw, _ in matching_candidates]
        if len(matching_candidates) > 0:
            has_matches += 1
            max_similarity = max(similarity)
            if max_similarity > 0.93:
                best_match = matching_candidates[np.argmax(similarity)]
                # save best match in directory
                side_by_side = Image.new('RGB', (reference.width * 2, reference.height))
                side_by_side.paste(reference, (0, 0))
                side_by_side.paste(best_match[1], (reference.width, 0))
                draw = ImageDraw.Draw(side_by_side)
                draw.text((0, 0), f"{max(similarity):.3f}", fill=(255, 0, 0))
                side_by_side.save(matches_dir / f"{stem}.png")

    print(has_matches)
