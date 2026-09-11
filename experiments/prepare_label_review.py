"""Create numbered image/label contact sheets for human review."""
import json
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'runs/sale_unit_review'

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    records = []
    for split in ['train', 'valid', 'test']:
        for path in sorted((ROOT / 'dataset' / split / 'images').iterdir()):
            records.append(dict(index=len(records), split=split, file=path.name))
    (OUT / 'index.json').write_text(json.dumps(records, indent=2), encoding='utf-8')
    for start in range(0, len(records), 64):
        canvas = Image.new('RGB', (1600, 1440), 'white')
        draw = ImageDraw.Draw(canvas)
        for slot, row in enumerate(records[start:start+64]):
            x, y = (slot % 8)*200, (slot//8)*180
            path = ROOT / 'dataset' / row['split'] / 'images' / row['file']
            with Image.open(path) as src:
                im = src.convert('RGB')
            im.thumbnail((198, 155))
            canvas.paste(im, (x, y+22))
            draw.text((x+2, y+2), f"{row['index']} {row['split']} {row['file'][:18]}", fill='black')
            label = ROOT / 'dataset' / row['split'] / 'labels' / (path.stem+'.txt')
            for line in label.read_text().splitlines():
                c,cx,cy,w,h = map(float,line.split())
                draw.rectangle([x+(cx-w/2)*im.width, y+22+(cy-h/2)*im.height,
                                x+(cx+w/2)*im.width, y+22+(cy+h/2)*im.height], outline='red',width=1)
        canvas.save(OUT / f"sheet_{start//64:02}.jpg", quality=90)
    print(len(records), 'images indexed in', OUT)

    selected = [153,156,161,171,231,234,237,238,241,242,248,250,266,
                371,378,395,399,405,408,416,424,425,426,430,436,440,441,445,650,654]
    for start in range(0, len(selected), 6):
        canvas = Image.new('RGB', (1000, 1140), 'white')
        draw = ImageDraw.Draw(canvas)
        for slot, index in enumerate(selected[start:start+6]):
            row = records[index]
            x, y = slot%2*500, slot//2*380
            path = ROOT / 'dataset' / row['split'] / 'images' / row['file']
            with Image.open(path) as src:
                im = src.convert('RGB')
            im.thumbnail((490, 350))
            canvas.paste(im, (x, y+25))
            draw.text((x+2,y+2), f"{index} {row['split']} {row['file'][:40]}",fill='black')
            label = ROOT / 'dataset' / row['split'] / 'labels' / (path.stem+'.txt')
            for line in label.read_text().splitlines():
                c,cx,cy,w,h = map(float,line.split())
                box = [x+(cx-w/2)*im.width,y+25+(cy-h/2)*im.height,
                       x+(cx+w/2)*im.width,y+25+(cy+h/2)*im.height]
                draw.rectangle(box,outline='red',width=2)
        canvas.save(OUT / f'selected_{start//6:02}.jpg',quality=95)


if __name__ == "__main__":
    main()
