"""Evaluate the fixed frontend policy before matching; no training or label edits."""
import json
from evaluate_thresholds import counts
from evaluate_model import ROOT, YOLO, CaptureValidator

POLICY = json.loads((ROOT / 'frontend/src/confidencePolicy.json').read_text())


class PolicyValidator(CaptureValidator):
    def update_metrics(self, preds, batch):
        filtered = []
        for pred in preds:
            thresholds = pred['conf'].new_tensor([
                POLICY['classes'].get(self.names[int(c)], POLICY['default']) for c in pred['cls']])
            mask = pred['conf'] >= thresholds
            filtered.append({k: v[mask] for k, v in pred.items()})
        return super().update_metrics(filtered, batch)


def main():
    out = ROOT / 'runs/class_thresholds'
    out.mkdir(parents=True, exist_ok=True)
    results = {}
    for name, conf, validator in [('baseline', .65, CaptureValidator), ('per_class', .5, PolicyValidator)]:
        YOLO(str(ROOT/'runs/detect/ozm_augmented/weights/best.pt')).val(
            data=str(ROOT/'dataset_corrected_v3_review/data.yaml'), split='val', device=0,
            imgsz=640, batch=16, workers=0, conf=conf, iou=.7, plots=False,
            project=str(out), name=name, validator=validator)
        stats = validator.captured
        results[name] = counts(stats)
    (out/'report.json').write_text(json.dumps(dict(policy=POLICY, results=results), indent=2), encoding='utf-8')
    print(json.dumps(results), flush=True)


if __name__ == '__main__':
    main()
