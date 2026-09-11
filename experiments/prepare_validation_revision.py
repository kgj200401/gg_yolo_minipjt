"""Build an evaluation-only, manually reviewed label revision; never train here."""
import hashlib
import json
import shutil
from pathlib import Path

import yaml
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "dataset_corrected_v2"
DEST = ROOT / "dataset_corrected_v3_review"
# Pixel coordinates selected from source images, not model predictions.
# Existing annotations remain unless replacement is explicitly specified.
EDITS = {
    "77d320dbf72508e3d14f7d502af40aba": dict(cls=1, boxes=[[270, 118, 533, 278], [274, 264, 538, 405]]),
    "bd95fbff4672f6d6e58d5fe8e1953328": dict(cls=1, replace=True, boxes=[[345, 610, 965, 1220]]),
    "apple_027": dict(cls=0, boxes=[[193, 41, 429, 256], [95, 157, 307, 287]]),
    "apple_055": dict(cls=0, boxes=[
        [147, 0, 247, 96], [0, 0, 88, 115], [48, 0, 124, 55],
        [88, 26, 156, 91], [345, 0, 480, 72], [0, 148, 47, 234],
        [19, 194, 143, 252], [339, 175, 474, 252], [0, 99, 31, 160],
        [177, 91, 242, 170]]),
    "apple_092": dict(cls=0, boxes=[
        [27, 0, 122, 87], [118, 27, 180, 130], [0, 57, 41, 146],
        [0, 164, 60, 250], [40, 198, 145, 285], [136, 126, 180, 203],
        [0, 246, 66, 320], [137, 228, 180, 320]]),
    "apple_097": dict(cls=0, boxes=[
        [69, 106, 181, 225], [0, 129, 76, 226], [174, 133, 241, 233],
        [0, 0, 74, 39], [203, 0, 241, 68], [0, 233, 30, 279],
        [0, 279, 63, 320], [83, 283, 147, 320], [185, 281, 241, 320]]),
    "pig_raw pork slices_044": dict(cls=7, boxes=[[96, 0, 214, 79]]),
}


def snapshot():
    return {str(p.relative_to(SOURCE)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in SOURCE.rglob("*") if p.is_file() and p.suffix != ".cache"}


def draw(image, labels):
    im = image.copy().convert("RGB")
    d = ImageDraw.Draw(im)
    w, h = im.size
    for n, row in enumerate(labels):
        c, x, y, bw, bh = map(float, row.split())
        box = [(x-bw/2)*w, (y-bh/2)*h, (x+bw/2)*w, (y+bh/2)*h]
        d.rectangle(box, outline="lime", width=max(1, w//300))
        d.text((box[0], box[1]), f"{n}:{int(c)}", fill="blue")
    im.thumbnail((700, 700))
    return im


def main():
    if DEST.exists():
        raise SystemExit(f"Refusing to overwrite {DEST}")
    before = snapshot()
    shutil.copytree(SOURCE / "valid", DEST / "valid", ignore=shutil.ignore_patterns("*.cache"))
    cfg = yaml.safe_load((SOURCE / "data.yaml").read_text(encoding="utf-8"))
    cfg.update(path=str(DEST), train=str(SOURCE / "train/images"), val="valid/images",
               test=str(SOURCE / "test/images"))
    (DEST / "data.yaml").write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")
    out = ROOT / "runs/validation_revision_review"
    out.mkdir(parents=True, exist_ok=True)
    manifest = []
    for prefix, edit in EDITS.items():
        matches = list((DEST / "valid/images").glob(prefix + "*"))
        assert len(matches) == 1, (prefix, matches)
        image = Image.open(matches[0])
        w, h = image.size
        label = DEST / "valid/labels" / (matches[0].stem + ".txt")
        old = label.read_text().strip().splitlines()
        new = [] if edit.get("replace") else old.copy()
        for x1, y1, x2, y2 in edit["boxes"]:
            assert 0 <= x1 < x2 <= w and 0 <= y1 < y2 <= h
            new.append(f"{edit['cls']} {(x1+x2)/2/w:.8f} {(y1+y2)/2/h:.8f} {(x2-x1)/w:.8f} {(y2-y1)/h:.8f}")
        label.write_text("\n".join(new) + "\n", encoding="utf-8")
        a, b = draw(image, old), draw(image, new)
        canvas = Image.new("RGB", (a.width+b.width, max(a.height,b.height)+25), "white")
        canvas.paste(a, (0, 25)); canvas.paste(b, (a.width, 25))
        d = ImageDraw.Draw(canvas); d.text((0,0), "BEFORE", fill="black"); d.text((a.width,0), "REVIEW REVISION", fill="black")
        canvas.save(out / (prefix + ".png"))
        manifest.append(dict(file=matches[0].name, before=len(old), after=len(new), **edit))
    assert before == snapshot(), "Source changed"
    total = 0
    for p in (DEST / "valid/labels").glob("*.txt"):
        for line in p.read_text().splitlines():
            c,x,y,w,h = map(float,line.split())
            assert c == int(c) and 0 <= c < 10 and w > 0 and h > 0
            assert min(x-w/2,y-h/2) >= -1e-6 and max(x+w/2,y+h/2) <= 1+1e-6
            total += 1
    images = list((DEST / "valid/images").iterdir())
    assert len(images) == 78
    for p in images:
        assert p.read_bytes() == (SOURCE / "valid/images" / p.name).read_bytes()
        assert (DEST / "valid/labels" / (p.stem+".txt")).exists()
    report = dict(source=str(SOURCE), output=str(DEST), images=78, annotations=total,
                  source_unchanged=True, edits=manifest)
    (out / "manifest.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
