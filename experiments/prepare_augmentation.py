"""Add clockwise 90-degree training copies, preserving original split membership."""
from pathlib import Path
import argparse
from PIL import Image
import yaml


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, default=root / 'dataset')
    parser.add_argument('--output', type=Path, default=root / 'dataset_augmented')
    args = parser.parse_args()
    source = args.source.resolve()
    output = args.output.resolve()
    if output.exists():
        raise SystemExit("Output exists; refusing to overwrite")
    images = sorted((source / "train/images").iterdir())
    prepared = []
    for image in images:
        lines = []
        for line in (source / "train/labels" / f"{image.stem}.txt").read_text().splitlines():
            cls, x, y, w, h = map(float, line.split())
            assert 0 <= cls < 10 and all(0 <= v <= 1 for v in (x, y, w, h))
            lines.append(f"{int(cls)} {1-y:.10g} {x:.10g} {h:.10g} {w:.10g}")
        prepared.append((image, "\n".join(lines)))
    (output / "train/images").mkdir(parents=True)
    (output / "train/labels").mkdir(parents=True)
    for image, labels in prepared:
        with Image.open(image) as im:
            im.transpose(Image.Transpose.ROTATE_270).save(output / "train/images" / image.name)
        (output / "train/labels" / f"{image.stem}.txt").write_text(labels, encoding="utf-8")
    config = yaml.safe_load((source / "data.yaml").read_text(encoding="utf-8"))
    config.update(path=str(root), train=[str(source / "train/images"), str(output / "train/images")],
                  val=str(source / "valid/images"), test=str(source / "test/images"))
    (output / "data.yaml").write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    print(f"Train: {len(images)} originals + {len(prepared)} rotated; validation/test unchanged")


if __name__ == "__main__":
    main()
