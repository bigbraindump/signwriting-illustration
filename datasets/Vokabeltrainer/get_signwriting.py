import os
import json
import re
import csv

from PIL import Image, UnidentifiedImageError

from signwriting_matcher import convert_to_fsw


def ascii_gloss(gloss: str):
    return gloss.replace('ä', '').replace('ö', '').replace('ü', '')


def parse_lexicon_tsv(name: str):
    res = {}
    with open(name + '.tsv', 'r', encoding='utf-8') as file:
        dict_reader = csv.DictReader(file, delimiter='\t')

        for row in dict_reader:
            gloss = row['Glosse']
            nr = row['Nr']
            # Happens that some of the entries are swapped
            try:
                int(nr)
            except:
                gloss, nr = nr, gloss

            gloss = gloss.lower()
            res[gloss] = int(nr)
            res[ascii_gloss(gloss)] = int(nr)

    return res


def parse_gloss_map():
    res = {}
    with open('Vokabeltrainer-Glossen.txt', 'r') as f:
        for line in f.readlines():
            gloss, nr = line.split('\t')
            gloss = gloss.lower()
            res[gloss] = int(nr)
            res[ascii_gloss(gloss)] = int(nr)
    return res


lexicon = parse_lexicon_tsv('lexicon')
wortschatz = parse_lexicon_tsv('wortschatz')
gloss_map = parse_gloss_map()

lexicon.update(wortschatz)
lexicon.update(gloss_map)





def get_gloss_ids(gloss: str):
    # Option 1: Id is a 3-5 digit number within the gloss, Return all matches
    matches = re.findall(r'\d{3,5}', gloss)
    if len(matches) > 0:
        for match in matches:
            yield int(match)

    # Option 2: gloss is in the lexicon, return the id
    lower_goss = gloss.lower()
    if lower_goss in lexicon:
        yield lexicon[lower_goss]
    elif ascii_gloss(lower_goss) in lexicon:
        yield lexicon[ascii_gloss(lower_goss)]

    # Try adding "A" to the end
    new_gloss = lower_goss.replace('-', '_') + 'a'
    if new_gloss in lexicon:
        yield lexicon[new_gloss]
    elif ascii_gloss(new_gloss) in lexicon:
        yield lexicon[ascii_gloss(new_gloss)]


def process_directory(directory):
    done_files = set()

    results = []
    for dir_name, _, _ in os.walk(directory):
        layout_path = os.path.join(dir_name, 'layout.txt')
        if os.path.isfile(layout_path):
            with open(layout_path, 'r') as file:
                content = file.read()
                fsw = convert_to_fsw(content)
                name = os.path.basename(dir_name)
                gloss_ids = list(get_gloss_ids(name))
                if len(gloss_ids) == 0:
                    # print(f"Missing {name}")
                    continue

                for _id in gloss_ids:
                    file_path = f"illustrations/{str(_id).zfill(5)}.png"
                    done_files.add(file_path)
                    if os.path.isfile(file_path):
                        results.append({
                            "file": file_path,
                            "fsw": fsw,
                            # "meta": lexicon[name]
                        })

    print('Found', len(results))

    illustration_files = set([file[:-len('.png')] for file in os.listdir('illustrations') if file.endswith('.png')])
    signwriting_files = set([file[:-len('.png')] for file in os.listdir('glossen') if file.endswith('.png')])

    intersection = illustration_files.intersection(signwriting_files)
    print('Intersection', len(intersection))
    for file in intersection:
        illustration_path = f"illustrations/{file}.png"
        if illustration_path not in done_files:
            fsw_path = f"glossen/{file}.png"
            try:
                Image.open(fsw_path)
            except UnidentifiedImageError:
                continue

            results.append({
                "file": illustration_path,
                "fsw_file": fsw_path
            })

    print('Total', len(results))

    with open('writing.json', 'w') as json_file:
        json.dump(results, json_file, indent=2)


if __name__ == "__main__":
    # lexicon = parse_lexicon_tsv()
    process_directory('SW_signs_glosses')
