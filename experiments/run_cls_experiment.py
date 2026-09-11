"""Experiment I: A configuration with classification loss weight 0.75."""
import csv
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CLS_WEIGHT = 0.75
RUN_NAME = "ozm_cls075"
RUN = ROOT / "runs/detect" / RUN_NAME
OUT = ROOT / "runs/validation_cls075"
REF = ROOT / "runs/reference_cls075"
DOC = ROOT / "docs/파인튜닝 진행.md"
DATA = ROOT / "dataset_corrected_v3_review/data.yaml"


def update(message):
    content = DOC.read_text(encoding="utf-8")
    start, end = "<!-- I_RESULT_START -->", "<!-- I_RESULT_END -->"
    assert content.count(start) == content.count(end) == 1
    before, tail = content.split(start)
    _, after = tail.split(end)
    DOC.write_text(before + start + "\n" + message + "\n" + end + after, encoding="utf-8")


def evaluate(weights, output):
    subprocess.run([sys.executable, "-u", "experiments/evaluate_thresholds.py", "--model", str(weights),
                    "--data", str(DATA), "--output", str(output)], cwd=ROOT, check=True)
    return json.loads((output / "report.json").read_text(encoding="utf-8"))


def pct(value):
    return "N/A" if value is None else f"{value*100:.2f}%"


def main():
    if any(p.exists() for p in (RUN, OUT, REF)):
        raise SystemExit("Output exists; refusing to overwrite. Use new run/output names.")
    assert DATA.is_file()
    started = datetime.now().isoformat(timespec="seconds")
    try:
        update(f"상태: A 기준 재평가 중. 시작: {started}")
        reference = evaluate(ROOT / "runs/detect/ozm_augmented/weights/best.pt", REF)
        update(f"상태: GPU 학습 진행 중. 시작: {started}\ncls 0.5 → {CLS_WEIGHT}. A의 데이터·나머지 설정 유지.")
        subprocess.run([sys.executable, "-u", "experiments/train_model.py", "--data", "dataset_augmented/data.yaml",
                        "--model", "yolov8n.pt", "--device", "0", "--epochs", "150", "--batch", "16",
                        "--imgsz", "640", "--lr0", "0.001", "--cls", str(CLS_WEIGHT),
                        "--optimizer", "AdamW", "--patience", "25", "--workers", "2",
                        "--cos-lr", "--degrees", "15", "--shear", "10", "--fliplr", "0.5",
                        "--name", RUN_NAME], cwd=ROOT, check=True)
        old = yaml.safe_load((ROOT / "runs/detect/ozm_augmented/args.yaml").read_text())
        new = yaml.safe_load((RUN / "args.yaml").read_text())
        differences = {k: [old.get(k), new.get(k)] for k in old.keys() | new.keys() if old.get(k) != new.get(k)}
        assert set(differences) <= {"cls", "name", "save_dir"}, differences
        assert differences["cls"] == [0.5, CLS_WEIGHT]
        update(f"상태: 학습 완료, 수정 검증본 평가 중. 시작: {started}")
        current = evaluate(RUN / "weights/best.pt", OUT)
        rows = list(csv.DictReader((RUN / "results.csv").open()))
        best = max(rows, key=lambda r: float(r["metrics/mAP50-95(B)"]))
        lines = ["### I 결과 — cls 학습 손실 비중 실험 완료", "",
                 f"시작: {started} / 완료: {datetime.now().isoformat(timespec='seconds')}",
                 f"학습 {len(rows)}에포크, 최고 mAP50-95 에포크 {best['epoch']}, 학습 시간 {float(rows[-1]['time'])/60:.1f}분.",
                 "두 모델 모두 v3_review 검증 78장. 미확정 라벨이 남은 검토용 데이터다.",
                 "Precision/Recall/F1은 매칭 IoU 0.50 micro 집계, mAP는 별도 conf 0.001 평가.", ""]
        for confidence in (0.65, 0.60):
            a = next(r for r in reference["results"] if r["confidence"] == confidence)
            b = next(r for r in current["results"] if r["confidence"] == confidence)
            lines += [f"**신뢰도 {confidence:.0%}**", "", "| 지표 | A cls 0.5 | I cls 0.75 | 변화(%p) |", "|---|---:|---:|---:|"]
            for key in ("precision", "recall", "f1", "map50", "map50_95"):
                x, y = (a[key], b[key]) if key in a else (reference[key], current[key])
                delta = "N/A" if x is None or y is None else f"{100*(y-x):+.2f}"
                lines.append(f"| {key} | {pct(x)} | {pct(y)} | {delta} |")
            lines += ["", f"TP/FP/FN: A {a['tp']}/{a['fp']}/{a['fn']} → I {b['tp']}/{b['fp']}/{b['fn']}", ""]
            if confidence == 0.65:
                lines += ["| 클래스 | A 정밀도 | I 정밀도 | A Recall | I Recall | A FP | I FP |", "|---|---:|---:|---:|---:|---:|---:|"]
                previous = {r['name']: r for r in a['classes']}
                for r in b['classes']:
                    q = previous[r['name']]
                    lines.append(f"| {r['name']} | {pct(q['precision'])} | {pct(r['precision'])} | {pct(q['recall'])} | {pct(r['recall'])} | {q['fp']} | {r['fp']} |")
                lines += [""]
        lines += ["단일 시드 실험. 정밀도 최우선으로 Recall 감소도 함께 검토한다. 웹 모델은 A·65%·1초 유지.",
                  "cls 가중치가 달라졌으므로 총 손실 크기만으로 A보다 좋다고 판단하지 않는다."]
        result = "\n".join(lines)
        (OUT / "comparison.md").write_text(result, encoding="utf-8")
        (OUT / "args_difference.json").write_text(json.dumps(differences, indent=2), encoding="utf-8")
        update(result)
        print("Experiment I completed.", flush=True)
    except Exception as exc:
        update(f"상태: 실행 실패 ({type(exc).__name__}). runs/logs/cls075_training.log 및 .err.log 확인.")
        raise


if __name__ == "__main__":
    main()
