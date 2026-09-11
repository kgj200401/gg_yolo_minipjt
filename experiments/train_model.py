"""Run with: uv run --with ultralytics experiments/train_model.py --help"""
import argparse
import os
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Train a YOLO model on the OZM dataset")
    parser.add_argument("--data", type=Path, default=root / "dataset/data.yaml")
    parser.add_argument("--model", default="yolov8n.pt")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--batch", type=int, default=8)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--lr0", type=float, default=0.001)
    parser.add_argument("--cls", type=float, default=0.5, help="Classification loss weight")
    parser.add_argument("--optimizer", default="AdamW")
    parser.add_argument("--patience", type=int, default=20)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--cos-lr", action="store_true")
    parser.add_argument("--degrees", type=float, default=0)
    parser.add_argument("--shear", type=float, default=0)
    parser.add_argument("--fliplr", type=float, default=0.5)
    parser.add_argument("--device", default="cpu", help="cpu, or 0 for a CUDA GPU")
    parser.add_argument("--name", default="ozm")
    args = parser.parse_args()
    if not args.data.is_file():
        parser.error(f"Dataset configuration not found: {args.data}")
    if min(args.epochs, args.batch, args.imgsz) <= 0 or args.lr0 <= 0 or not 0 < args.cls < float("inf"):
        parser.error("epochs, batch, imgsz, lr0 and cls must be positive and cls finite")

    os.environ.setdefault("YOLO_CONFIG_DIR", str(root / ".yolo-config"))
    Path(os.environ["YOLO_CONFIG_DIR"]).mkdir(parents=True, exist_ok=True)
    from ultralytics import YOLO

    model = YOLO(args.model)
    model.train(
        data=str(args.data.resolve()),
        epochs=args.epochs,
        batch=args.batch,
        imgsz=args.imgsz,
        optimizer=args.optimizer,
        lr0=args.lr0,
        cls=args.cls,
        patience=args.patience,
        device=args.device,
        project=str(root / "runs/detect"),
        name=args.name,
        workers=args.workers,
        cos_lr=args.cos_lr,
        degrees=args.degrees,
        shear=args.shear,
        fliplr=args.fliplr,
        seed=42,
    )
    print(f"Best weights: {model.trainer.best}")


if __name__ == "__main__":
    # Windows multiprocessing requires this guard.
    main()
