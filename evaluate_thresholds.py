"""Compare fixed confidence thresholds on validation data only; no training."""
import json
import argparse
from pathlib import Path

from evaluate_model import CaptureValidator, ROOT, YOLO


def counts(stats, mask=None, cls=None):
    tp = int(stats["tp"][:, 0].sum() if mask is None else stats["tp"][mask, 0].sum())
    predicted = len(stats["pred_cls"]) if mask is None else int(mask.sum())
    gt = len(stats["target_cls"]) if cls is None else int((stats["target_cls"] == cls).sum())
    fp, fn = predicted - tp, gt - tp
    return dict(tp=tp, fp=fp, fn=fn, precision=tp/predicted if predicted else None,
                recall=tp/gt if gt else None, f1=2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else None)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, default=ROOT / "runs/detect/ozm_augmented/weights/best.pt")
    parser.add_argument("--output", type=Path, default=ROOT / "runs/threshold_validation")
    parser.add_argument("--data", type=Path, default=ROOT / "dataset/data.yaml")
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    weights = args.model.resolve()
    model = YOLO(str(weights))
    common = dict(data=str(args.data.resolve()), split="val", device=0,
                  imgsz=640, batch=16, workers=0, iou=0.7, plots=False,
                  project=str(output), verbose=False)
    ap = model.val(**common, conf=0.001, name="ap")
    rows = []
    for step in range(50, 91, 5):
        threshold = step / 100
        model.val(**common, conf=threshold, name=f"conf{step}", validator=CaptureValidator)
        stats = CaptureValidator.captured
        row = dict(confidence=threshold, **counts(stats))
        row["classes"] = [dict(name=name, **counts(stats, stats["pred_cls"] == cls, cls))
                          for cls, name in model.names.items()]
        rows.append(row)
        print("THRESHOLD", json.dumps({k:v for k,v in row.items() if k != "classes"}), flush=True)
    eligible = [r for r in rows if r["precision"] is not None and r["precision"] >= 0.90]
    selected = max(eligible, key=lambda r: (r["recall"], r["precision"])) if eligible else None
    report = dict(model=str(weights), data=str(args.data.resolve()), split="val", images=78, matching_iou=0.5, nms_iou=0.7,
                  map50=float(ap.box.map50), map50_95=float(ap.box.map),
                  selected_confidence=selected["confidence"] if selected else None, results=rows)
    (output / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    lines = ["# Confidence comparison (validation only)", "",
             "Precision/Recall are micro averages at matching IoU 0.50, NMS IoU 0.70.",
             "No retraining, no test-set evaluation, no application threshold changes.", "",
             "| Confidence | Precision | Recall | F1 | TP | FP | FN |",
             "|---|---:|---:|---:|---:|---:|---:|"]
    for r in rows:
        values = [f"{r[k]*100:.2f}%" if r[k] is not None else "N/A" for k in ("precision","recall","f1")]
        lines.append(f"| {r['confidence']:.2f} | {' | '.join(values)} | {r['tp']} | {r['fp']} | {r['fn']} |")
    lines += ["", f"Selected confidence for precision >=90%: {report['selected_confidence']}",
              f"Validation mAP50: {ap.box.map50:.4f}; mAP50-95: {ap.box.map:.4f}"]
    (output / "comparison.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines), flush=True)


if __name__ == "__main__":
    main()
