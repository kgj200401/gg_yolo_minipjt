"""Experiment C: train with reduced shear and 90-degree copies, validate, update the progress document."""
import csv
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs/파인튜닝 진행.md"
RUN = ROOT / "runs/detect/ozm_shear3"
OUTPUT = ROOT / "runs/validation_shear3"


def update_document(result):
    text = DOC.read_text(encoding="utf-8")
    start, end = "<!-- C_RESULT_START -->", "<!-- C_RESULT_END -->"
    assert text.count(start) == text.count(end) == 1
    before, tail = text.split(start)
    _, after = tail.split(end)
    DOC.write_text(before + start + "\n" + result + "\n" + end + after, encoding="utf-8")


def percent(value):
    return "해당 없음" if value is None else f"{100*value:.2f}%"


def fixed(report, confidence=0.70):
    return next(row for row in report["results"] if row["confidence"] == confidence)


def main():
    if RUN.exists() or OUTPUT.exists():
        raise SystemExit("Experiment output exists; refusing to overwrite")
    reference = ROOT / "runs/threshold_validation/report.json"
    baseline = json.loads(reference.read_text(encoding="utf-8"))
    assert baseline["split"] == "val"
    started = datetime.now().isoformat(timespec="seconds")
    update_document(f"상태: 학습 진행 중. 시작 시각(PC 현지 시간): {started}\n\n앱 모델과 신뢰도 설정은 유지한다.")
    try:
        subprocess.run([sys.executable, "-u", "experiments/train_model.py", "--data", "dataset_augmented/data.yaml",
                        "--model", "yolov8n.pt", "--device", "0", "--epochs", "150",
                        "--batch", "16", "--lr0", "0.001", "--optimizer", "AdamW",
                        "--patience", "25", "--workers", "2", "--cos-lr", "--degrees", "15",
                        "--shear", "3", "--fliplr", "0.5", "--name", "ozm_shear3"],
                       cwd=ROOT, check=True)
        update_document(f"상태: 학습 완료, 검증 데이터 평가 중. 시작 시각: {started}")
        subprocess.run([sys.executable, "-u", "experiments/evaluate_thresholds.py", "--model",
                        str(RUN / "weights/best.pt"), "--output", str(OUTPUT)], cwd=ROOT, check=True)
        current = json.loads((OUTPUT / "report.json").read_text(encoding="utf-8"))
        assert current["split"] == baseline["split"] == "val"
        with (RUN / "results.csv").open() as stream:
            epochs = list(csv.DictReader(stream))
        best = max(epochs, key=lambda row: float(row["metrics/mAP50-95(B)"]))
        a, b = fixed(baseline), fixed(current)
        lines = ["### C 실험 결과 — 학습 및 평가 완료", "",
                 f"시작: {started} / 완료: {datetime.now().isoformat(timespec='seconds')}",
                 f"실제 학습: {len(epochs)}에포크 / 최고 검증 에포크: {best['epoch']}",
                 f"학습 CSV 기준 경과 시간: {float(epochs[-1]['time'])/60:.1f}분", "",
                 "**같은 valid 78장, 신뢰도 70%에서 비교** (mAP는 별도로 전체 신뢰도 구간 평가)", "",
                 "| 지표 | A: shear 10 | C: shear 3 | 변화(%p) |",
                 "|---|---:|---:|---:|"]
        for key in ("precision", "recall", "f1", "map50", "map50_95"):
            old = a[key] if key in a else baseline[key]
            new = b[key] if key in b else current[key]
            delta = f"{100*(new-old):+.2f}" if old is not None and new is not None else "해당 없음"
            lines.append(f"| {key} | {percent(old)} | {percent(new)} | {delta} |")
        lines += ["", f"TP/FP/FN: A {a['tp']}/{a['fp']}/{a['fn']} → C {b['tp']}/{b['fp']}/{b['fn']}",
                  "", "**각 모델에서 정밀도 90% 이상 중 최고 Recall 조건**", "",
                  "| 모델 | 신뢰도 | Precision | Recall | F1 |", "|---|---:|---:|---:|---:|"]
        for label, report in (("A", baseline), ("C", current)):
            threshold = report["selected_confidence"]
            if threshold is None:
                lines.append(f"| {label} | 목표 충족 없음 | - | - | - |")
            else:
                row = fixed(report, threshold)
                lines.append(f"| {label} | {percent(threshold)} | {percent(row['precision'])} | {percent(row['recall'])} | {percent(row['f1'])} |")
        lines += ["", "**C 신뢰도별 수치**", "", "| 신뢰도 | Precision | Recall | F1 |", "|---|---:|---:|---:|"]
        for row in current["results"]:
            lines.append(f"| {percent(row['confidence'])} | {percent(row['precision'])} | {percent(row['recall'])} | {percent(row['f1'])} |")
        lines += ["", "**클래스별 70% 기준 비교**", "",
                  "| 클래스 | A Precision | C Precision | A Recall | C Recall |", "|---|---:|---:|---:|---:|"]
        old_classes = {row["name"]: row for row in a["classes"]}
        for row in b["classes"]:
            old = old_classes[row["name"]]
            lines.append(f"| {row['name']} | {percent(old['precision'])} | {percent(row['precision'])} | {percent(old['recall'])} | {percent(row['recall'])} |")
        lines += ["", "test 재평가 및 앱 자동 적용은 하지 않았다. 검증 표본이 작으므로 개선 여부를 과대해석하지 않는다."]
        result = "\n".join(lines)
        (OUTPUT / "comparison.md").write_text(result, encoding="utf-8")
        update_document(result)
        print("Experiment C complete; progress document updated.", flush=True)
    except Exception as exc:
        update_document(f"상태: 학습 또는 평가 실패 ({type(exc).__name__}). 로그 `runs/logs/shear3_training.log`를 확인한다.\n시작: {started}")
        raise


if __name__ == "__main__":
    main()
