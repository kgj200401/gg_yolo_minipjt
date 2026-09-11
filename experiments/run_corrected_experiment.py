"""Train on corrected v2 labels, evaluate both models at 60%, save comparison."""
import csv
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / 'runs/detect/ozm_corrected_v2'
OUTPUT = ROOT / 'runs/validation_corrected_v2'
REFERENCE = ROOT / 'runs/reference_corrected_v2'
DOC = ROOT / 'docs/파인튜닝 진행.md'
DATA = ROOT / 'dataset_corrected_v2/data.yaml'


def update(text):
    content = DOC.read_text(encoding='utf-8')
    start, end = '<!-- D_RESULT_START -->', '<!-- D_RESULT_END -->'
    assert content.count(start) == content.count(end) == 1
    before, tail = content.split(start)
    _, after = tail.split(end)
    DOC.write_text(before+start+'\n'+text+'\n'+end+after, encoding='utf-8')


def evaluate(model, output):
    subprocess.run([sys.executable, '-u', 'experiments/evaluate_thresholds.py', '--model', str(model),
                    '--data', str(DATA), '--output', str(output)], cwd=ROOT, check=True)
    return json.loads((output/'report.json').read_text(encoding='utf-8'))


def fixed(report):
    return next(row for row in report['results'] if row['confidence'] == 0.60)


def pct(value):
    return '해당 없음' if value is None else f'{value*100:.2f}%'


def main():
    if any(p.exists() for p in [RUN, OUTPUT, REFERENCE]):
        raise SystemExit('Experiment exists; refusing to overwrite.')
    started = datetime.now().isoformat(timespec='seconds')
    try:
        update(f'상태: 기존 A 모델을 동일한 v2 검증 데이터로 재평가 중. 시작: {started}')
        baseline = evaluate(ROOT/'runs/detect/ozm_augmented/weights/best.pt', REFERENCE)
        update(f'상태: 학습 진행 중. 시작: {started}\n\n학습 후 신뢰도 60%에서 기존 A와 비교한다.')
        subprocess.run([sys.executable, '-u', 'experiments/train_model.py', '--data', 'dataset_corrected_augmented_v2/data.yaml',
                        '--model', 'yolov8n.pt', '--device', '0', '--epochs', '150', '--batch', '16',
                        '--lr0', '0.001', '--optimizer', 'AdamW', '--patience', '25', '--workers', '2',
                        '--cos-lr', '--degrees', '15', '--shear', '10', '--fliplr', '0.5',
                        '--name', 'ozm_corrected_v2'], cwd=ROOT, check=True)
        # Detect accidental configuration drift before publishing a comparison.
        old_args = yaml.safe_load((ROOT/'runs/detect/ozm_augmented/args.yaml').read_text())
        new_args = yaml.safe_load((RUN/'args.yaml').read_text())
        differences = {key: [old_args.get(key), new_args.get(key)] for key in old_args.keys() | new_args.keys()
                       if old_args.get(key) != new_args.get(key)}
        assert set(differences) <= {'data', 'name', 'save_dir'}, differences
        update(f'상태: 학습 완료, 새 모델 평가 중. 시작: {started}')
        current = evaluate(RUN/'weights/best.pt', OUTPUT)
        a, b = fixed(baseline), fixed(current)
        with (RUN/'results.csv').open() as handle:
            epochs = list(csv.DictReader(handle))
        best = max(epochs, key=lambda row: float(row['metrics/mAP50-95(B)']))
        lines = ['### D 실험 결과 — 수정 데이터 학습 및 평가 완료', '',
                 f'시작: {started} / 완료: {datetime.now().isoformat(timespec="seconds")}',
                 f'학습 {len(epochs)}에포크, 최고 검증 에포크 {best["epoch"]}, 학습 시간 {float(epochs[-1]["time"])/60:.1f}분.',
                 '', '**동일한 v2 valid 78장, 신뢰도 60%, 매칭 IoU 0.5에서 비교.**',
                 'Precision·Recall·F1은 micro 평균. mAP는 별도로 낮은 신뢰도부터 평가.', '',
                 '| 지표 | 기존 A | 수정 데이터 D | 변화(%p) |', '|---|---:|---:|---:|']
        for key in ['precision', 'recall', 'f1', 'map50', 'map50_95']:
            old = a[key] if key in a else baseline[key]
            new = b[key] if key in b else current[key]
            delta = '해당 없음' if old is None or new is None else f'{100*(new-old):+.2f}'
            lines.append(f'| {key} | {pct(old)} | {pct(new)} | {delta} |')
        lines += ['', f'TP/FP/FN: A {a["tp"]}/{a["fp"]}/{a["fn"]} → D {b["tp"]}/{b["fp"]}/{b["fn"]}', '',
                  '| 클래스 | A 정밀도 | D 정밀도 | A Recall | D Recall |', '|---|---:|---:|---:|---:|']
        old_classes = {row['name']: row for row in a['classes']}
        for row in b['classes']:
            old = old_classes[row['name']]
            lines.append(f'| {row["name"]} | {pct(old["precision"])} | {pct(row["precision"])} | {pct(old["recall"])} | {pct(row["recall"])} |')
        lines += ['', f'60%에서 정밀도 90% 목표 충족: {"예" if b["precision"] is not None and b["precision"] >= .9 else "아니오"}',
                  '최고 체크포인트는 기존 학습과 동일하게 검증 mAP50-95 기준으로 선택했다. 정밀도 최적 체크포인트라는 뜻은 아니다.',
                  '수정 valid는 v1과 같으며, test와 실제 웹 장바구니 평가는 별도다.',
                  '표본과 수정량이 작고 단일 시드 실험이므로 일반적인 성능 향상을 단정하지 않는다.',
                  '서비스 모델·임계값은 자동 변경하지 않았다.']
        text = '\n'.join(lines)
        (OUTPUT/'comparison.md').write_text(text, encoding='utf-8')
        (OUTPUT/'args_difference.json').write_text(json.dumps(differences, indent=2), encoding='utf-8')
        update(text)
        print('Experiment D complete; progress document updated.', flush=True)
    except Exception as exc:
        update(f'상태: 학습 또는 평가 실패 ({type(exc).__name__}).\n로그: runs/logs/corrected_v2_training.log 및 runs/logs/corrected_v2_training.err.log')
        raise


if __name__ == '__main__':
    main()
