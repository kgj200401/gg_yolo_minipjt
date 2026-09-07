"""Held-out test evaluation; fixed operating point is reported separately from AP."""
import json
import argparse
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.environ.setdefault("YOLO_CONFIG_DIR", str(ROOT / ".yolo-config"))
import numpy as np
from ultralytics import YOLO
from ultralytics.models.yolo.detect.val import DetectionValidator


class CaptureValidator(DetectionValidator):
    captured = None

    def get_stats(self):
        type(self).captured = {k: np.concatenate(v, 0) for k, v in self.metrics.stats.items()}
        return super().get_stats()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=str(ROOT / "runs/detect/ozm_baseline/weights/best.pt"))
    parser.add_argument("--output", type=Path, default=ROOT / "runs/evaluation")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    model = YOLO(args.model)
    common = dict(data=str(ROOT / "dataset/data.yaml"), split="test", device=0,
                  imgsz=640, batch=16, workers=0, iou=0.7,
                  project=str(args.output))
    metrics = model.val(**common, conf=0.001, name="test_ap", plots=True)
    report = {"split": "test", "map50": float(metrics.box.map50),
              "map50_95": float(metrics.box.map), "confidence": 0.7,
              "matching_iou": 0.5, "nms_iou": 0.7}
    model.val(**common, conf=0.7, name="test_conf70", plots=True, validator=CaptureValidator)
    stats = CaptureValidator.captured
    rows = []
    for cls, name in model.names.items():
        mask = stats["pred_cls"] == cls
        tp = int(stats["tp"][mask, 0].sum())
        fp = int(mask.sum()) - tp
        gt = int((stats["target_cls"] == cls).sum())
        rows.append(dict(name=name, tp=tp, fp=fp, fn=gt-tp,
                         precision=tp/(tp+fp) if tp+fp else None,
                         recall=tp/gt if gt else None,
                         ap50=float(metrics.box.ap50[cls]),
                         ap50_95=float(metrics.box.ap[cls])))
    tp, fp, fn = (sum(row[k] for row in rows) for k in ("tp", "fp", "fn"))
    report["overall"] = dict(tp=tp, fp=fp, fn=fn, precision=tp/(tp+fp),
                             recall=tp/(tp+fn), f1=2*tp/(2*tp+fp+fn))
    report["classes"] = rows
    output = args.output / "report.json"
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
