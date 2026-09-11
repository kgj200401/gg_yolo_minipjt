"""Experiment J: combine shear=0 and cls=0.75; compare A/H/I/J."""
import csv
import json
import subprocess
import sys
from datetime import datetime

import yaml
from run_cls_experiment import ROOT, DOC, DATA, evaluate, pct

CLS_WEIGHT = 0.75
SHEAR = 0.0
RUN_NAME = "ozm_shear0_cls075"
RUN = ROOT / "runs/detect" / RUN_NAME
OUTPUT = ROOT / "runs/combined_experiment"
MODELS = {"A": "ozm_augmented", "H": "ozm_shear0", "I": "ozm_cls075", "J": RUN_NAME}


def update(message):
    text = DOC.read_text(encoding="utf-8")
    start, end = "<!-- J_RESULT_START -->", "<!-- J_RESULT_END -->"
    assert text.count(start) == text.count(end) == 1
    before, tail = text.split(start)
    _, after = tail.split(end)
    DOC.write_text(before + start + "\n" + message + "\n" + end + after, encoding="utf-8")


def main():
    if RUN.exists() or OUTPUT.exists():
        raise SystemExit("Output exists; refusing to overwrite.")
    assert DATA.is_file()
    for name in ("A", "H", "I"):
        assert (ROOT / "runs/detect" / MODELS[name] / "weights/best.pt").is_file()
    started = datetime.now().isoformat(timespec="seconds")
    OUTPUT.mkdir(parents=True)
    try:
        update(f"상태: GPU 학습 진행 중。시작: {started}\nA 기준 shear=0, cls=0.75 조합. 나머지 설정 유지.")
        subprocess.run([sys.executable, "-u", "experiments/train_model.py", "--data", "dataset_augmented/data.yaml",
                        "--model", "yolov8n.pt", "--device", "0", "--epochs", "150", "--batch", "16",
                        "--imgsz", "640", "--lr0", "0.001", "--cls", str(CLS_WEIGHT),
                        "--optimizer", "AdamW", "--patience", "25", "--workers", "2",
                        "--cos-lr", "--degrees", "15", "--shear", str(SHEAR), "--fliplr", "0.5",
                        "--name", RUN_NAME], cwd=ROOT, check=True)
        old = yaml.safe_load((ROOT / "runs/detect/ozm_augmented/args.yaml").read_text())
        new = yaml.safe_load((RUN / "args.yaml").read_text())
        diff = {k: [old.get(k), new.get(k)] for k in old.keys() | new.keys() if old.get(k) != new.get(k)}
        assert set(diff) <= {"cls", "shear", "name", "save_dir"}, diff
        assert diff["cls"] == [0.5, CLS_WEIGHT] and diff["shear"] == [10.0, SHEAR]
        (OUTPUT / "args_difference.json").write_text(json.dumps(diff, indent=2), encoding="utf-8")
        reports = {}
        for key, model in MODELS.items():
            update(f"상태: 학습 완료, {key} 모델 재평가 중. 시작: {started}")
            reports[key] = evaluate(ROOT / "runs/detect" / model / "weights/best.pt", OUTPUT / key)
        with (RUN / "results.csv").open() as handle:
            epochs = list(csv.DictReader(handle))
        best = max(epochs, key=lambda r: float(r["metrics/mAP50-95(B)"]))
        lines = ["### J 결과 — shear 0 + cls 0.75 조합", "",
                 f"시작 {started} / 완료 {datetime.now().isoformat(timespec='seconds')}",
                 f"학습 {len(epochs)}에포크, 최고 mAP50-95 에포크 {best['epoch']}, 학습 시간 {float(epochs[-1]['time'])/60:.1f}분.",
                 "모두 같은 v3_review valid 78장. P/R/F1은 매칭 IoU 0.50 micro 집계. mAP는 별도로 conf 0.001에서 측정.", ""]
        for conf in (0.65, 0.60):
            lines += [f"**신뢰도 {conf:.0%} 비교**", "",
                      "| 모델 | Precision | Recall | F1 | mAP50 | mAP50-95 | TP / FP / FN |", "|---|---:|---:|---:|---:|---:|---|"]
            for key, report in reports.items():
                row = next(r for r in report['results'] if r['confidence'] == conf)
                vals = [pct(row[k]) for k in ('precision','recall','f1')] + [pct(report[k]) for k in ('map50','map50_95')]
                lines.append(f"| {key} | {' | '.join(vals)} | {row['tp']} / {row['fp']} / {row['fn']} |")
            lines += [""]
        baseline = next(r for r in reports['A']['results'] if r['confidence'] == .65)
        lines += ["**A의 65% 정밀도 이상에서 Recall 비교(신뢰도 50~90%, 5% 간격)**", "",
                  "| 모델 | 선택 신뢰도 | Precision | Recall |", "|---|---:|---:|---:|"]
        for key, report in reports.items():
            eligible = [r for r in report['results'] if r['precision'] is not None and r['precision'] >= baseline['precision']]
            r = max(eligible, key=lambda x: (x['recall'], x['precision'])) if eligible else None
            lines.append(f"| {key} | {pct(r['confidence'])} | {pct(r['precision'])} | {pct(r['recall'])} |" if r else f"| {key} | 조건 충족 없음 | — | — |")
        lines += ["", "**클래스별 결과(65%)**", "", "| 모델 | 클래스 | Precision | Recall | FP |", "|---|---|---:|---:|---:|"]
        for key, report in reports.items():
            for r in next(r for r in report['results'] if r['confidence'] == .65)['classes']:
                lines.append(f"| {key} | {r['name']} | {pct(r['precision'])} | {pct(r['recall'])} | {r['fp']} |")
        lines += ["", "단일 시드, 미확정 라벨이 남은 검토용 검증 세트다. 정밀도 우선으로 H 대비 오탐 개선과 A 수준 정밀도에서 Recall을 함께 판단한다.",
                  "총 손실 크기는 cls 비중이 달라 직접 비교하지 않는다. 웹은 A·65%·1초 유지. 모델 자동 교체 없음."]
        result = "\n".join(lines)
        (OUTPUT / "comparison.md").write_text(result, encoding="utf-8")
        update(result)
        print("Experiment J completed.", flush=True)
    except Exception as exc:
        update(f"상태: 실행 실패 ({type(exc).__name__}). runs/logs/combined_training.log 및 .err.log 확인.")
        raise


if __name__ == "__main__":
    main()
