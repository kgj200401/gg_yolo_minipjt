"""Apply reviewed label corrections to a separate, immutable-source dataset."""
import hashlib
import argparse
import json
import shutil
from collections import Counter
from pathlib import Path

import yaml
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / 'dataset'
OUTPUT = ROOT / 'dataset_corrected_v1'
REVIEW = ROOT / 'runs/sale_unit_review'

# Pixel coordinates manually reviewed against the original images, not predictions.
EDITS = {
    ('train', 'large green onion_091_jpg.rf.2Q5OOFAdYcGxwfvGtcFl'): {
        'reason': 'Two separately tied sale bundles; replace fragmented leaf/stem boxes.',
        'class_id': 5, 'size': (320, 320),
        'boxes': [(26, 12, 181, 310), (155, 14, 287, 310)],
    },
    ('valid', 'galic17_webp.rf.c6Z63seaxIIywPcl3yoH'): {
        'reason': 'Two garlic mesh bags; replace tiny incomplete box with two sale units.',
        'class_id': 4, 'size': (730, 730),
        'boxes': [(94, 130, 445, 500), (324, 181, 729, 572)],
    },
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalized(cls, boxes, size):
    width, height = size
    return [[cls, (x1+x2)/2/width, (y1+y2)/2/height,
             (x2-x1)/width, (y2-y1)/height] for x1,y1,x2,y2 in boxes]


def draw_comparison(image, old, new, target):
    with Image.open(image) as source:
        im = source.convert('RGB')
    im.thumbnail((650, 650))
    canvas = Image.new('RGB', (im.width*2, im.height+30), 'white')
    draw = ImageDraw.Draw(canvas)
    for column, rows in enumerate([old,new]):
        x = column*im.width
        canvas.paste(im, (x,30))
        draw.text((x+5,5), 'BEFORE' if column == 0 else 'AFTER', fill='black')
        for cls,cx,cy,w,h in rows:
            draw.rectangle([x+(cx-w/2)*im.width,30+(cy-h/2)*im.height,
                            x+(cx+w/2)*im.width,30+(cy+h/2)*im.height],
                           outline='red' if column == 0 else 'lime', width=2)
    canvas.save(target)


def main():
    global OUTPUT, REVIEW
    parser = argparse.ArgumentParser()
    parser.add_argument('--version', choices=['v1', 'v2'], default='v1')
    args = parser.parse_args()
    edits = dict(EDITS)
    if args.version == 'v2':
        OUTPUT = ROOT / 'dataset_corrected_v2'
        REVIEW = ROOT / 'runs/sale_unit_review_v2'
        batch = json.loads((ROOT/'docs/label_corrections_v2.json').read_text(encoding='utf-8'))
        for edit in batch['edits']:
            edits[(edit['split'],edit['stem'])] = edit
    if OUTPUT.exists():
        raise SystemExit('Output already exists; refusing to overwrite reviewed dataset.')
    manifest, source_hashes = [], {}
    image_counts = {}
    # Read and validate every original label before creating output.
    prepared = []
    for split in ['train','valid','test']:
        images = sorted((SOURCE/split/'images').iterdir())
        image_counts[split] = len(images)
        for image in images:
            label = SOURCE/split/'labels'/(image.stem+'.txt')
            source_hashes[str(image.relative_to(SOURCE))] = digest(image)
            source_hashes[str(label.relative_to(SOURCE))] = digest(label)
            old = [list(map(float, line.split())) for line in label.read_text().splitlines()]
            rows, reasons = [], []
            for row in old:
                assert len(row) == 5 and row[0].is_integer() and 0 <= row[0] < 10
                if row in rows and split != 'test':
                    reasons.append('Remove identical duplicate label row.')
                    continue
                rows.append(row.copy())
            edit = edits.get((split,image.stem))
            if edit:
                with Image.open(image) as im:
                    assert im.size == tuple(edit['size'])
                replacement = normalized(edit['class_id'],edit['boxes'],edit['size'])
                rows = rows + replacement if edit.get('action') == 'append' else replacement
                reasons.append(edit['reason'])
            # Only the explicitly identified numerical boundary error is clamped.
            if split == 'valid' and image.stem == 'ham_085_jpg.rf.rmt8JEJlYcu9unKNi0OA':
                fixed = []
                for c,x,y,w,h in rows:
                    x1,y1,x2,y2 = max(0,x-w/2),max(0,y-h/2),min(1,x+w/2),min(1,y+h/2)
                    fixed.append([c,(x1+x2)/2,(y1+y2)/2,x2-x1,y2-y1])
                rows = fixed
                reasons.append('Clip tiny negative top boundary (rounding error) to image.')
            for c,x,y,w,h in rows:
                assert 0 < w <= 1 and 0 < h <= 1
                assert min(x-w/2,y-h/2) >= -1e-5 and max(x+w/2,y+h/2) <= 1+1e-5
            prepared.append((split,image,label,old,rows,reasons))
    assert image_counts == {'train':622,'valid':78,'test':78}
    REVIEW.mkdir(parents=True,exist_ok=True)
    for split,image,label,old,rows,reasons in prepared:
        image_dest = OUTPUT/split/'images'/image.name
        label_dest = OUTPUT/split/'labels'/label.name
        image_dest.parent.mkdir(parents=True,exist_ok=True)
        label_dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(image,image_dest)
        if reasons:
            label_dest.write_text('\n'.join(' '.join([str(int(r[0]))]+[f'{v:.12g}' for v in r[1:]]) for r in rows)+'\n',encoding='utf-8')
            entry = dict(split=split,image=image.name,label=label.name,reasons=reasons,before=old,after=rows,
                         source_sha256=digest(label),corrected_sha256=digest(label_dest))
            manifest.append(entry)
            draw_comparison(image,old,rows,REVIEW/f'corrected_{len(manifest):02}.png')
        else:
            shutil.copy2(label,label_dest)
    config = yaml.safe_load((SOURCE/'data.yaml').read_text(encoding='utf-8'))
    config.update(path=str(OUTPUT),train='train/images',val='valid/images',test='test/images')
    (OUTPUT/'data.yaml').write_text(yaml.safe_dump(config,sort_keys=False),encoding='utf-8')
    for relative, expected in source_hashes.items():
        assert digest(SOURCE/relative) == expected, 'Source was modified: '+relative
    assert len(manifest) == len(edits)+3, manifest
    report = dict(scope=f'Reviewed correction batch {args.version}; not a complete semantic relabeling.',
                  source=str(SOURCE),output=str(OUTPUT),image_counts=image_counts,
                  edits=manifest,source_hashes=source_hashes)
    (OUTPUT/'changes.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    (REVIEW/'changes.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('Prepared:',OUTPUT)
    print('Changed label files:',dict(Counter(e['split'] for e in manifest)))
    print('Original source hashes verified; all image bytes and split membership preserved.')


if __name__ == '__main__':
    main()
