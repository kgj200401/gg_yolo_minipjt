"""Experiment F: A's data and settings, changing only initial learning rate."""
import csv
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT/'runs/detect/ozm_lr00075'
OUT = ROOT/'runs/validation_lr00075'
REF = ROOT/'runs/reference_lr00075'
DOC = ROOT/'docs/파인튜닝 진행.md'


def update(result):
    text = DOC.read_text(encoding='utf-8')
    start, end = '<!-- F_RESULT_START -->', '<!-- F_RESULT_END -->'
    assert text.count(start) == text.count(end) == 1
    before, tail = text.split(start)
    _, after = tail.split(end)
    DOC.write_text(before+start+'\n'+result+'\n'+end+after, encoding='utf-8')


def evaluate(weights, output):
    subprocess.run([sys.executable, '-u', 'experiments/evaluate_thresholds.py', '--model', str(weights),
                    '--data', 'dataset_corrected_v2/data.yaml', '--output', str(output)], cwd=ROOT, check=True)
    return json.loads((output/'report.json').read_text(encoding='utf-8'))


def fixed(report, confidence):
    return next(r for r in report['results'] if r['confidence'] == confidence)


def pct(value):
    return '해당 없음' if value is None else f'{value*100:.2f}%'


def main():
    if any(p.exists() for p in [RUN, OUT, REF]):
        raise SystemExit('Experiment output exists; refusing to overwrite.')
    started = datetime.now().isoformat(timespec='seconds')
    try:
        update(f'상태: A 비교 기준 재평가 중. 시작: {started}')
        reference = evaluate(ROOT/'runs/detect/ozm_augmented/weights/best.pt', REF)
        update(f'상태: 학습 진행 중. 시작: {started}\nA와 같은 데이터에서 lr0만 0.00075로 변경.')
        subprocess.run([sys.executable, '-u', 'experiments/train_model.py', '--data', 'dataset_augmented/data.yaml',
                        '--model', 'yolov8n.pt', '--device', '0', '--epochs', '150', '--batch', '16',
                        '--lr0', '0.00075', '--optimizer', 'AdamW', '--patience', '25', '--workers', '2',
                        '--cos-lr', '--degrees', '15', '--shear', '10', '--fliplr', '0.5',
                        '--name', 'ozm_lr00075'], cwd=ROOT, check=True)
        old = yaml.safe_load((ROOT/'runs/detect/ozm_augmented/args.yaml').read_text())
        new = yaml.safe_load((RUN/'args.yaml').read_text())
        differences = {k:[old.get(k),new.get(k)] for k in old.keys()|new.keys() if old.get(k)!=new.get(k)}
        assert set(differences) <= {'lr0','name','save_dir'}, differences
        assert differences['lr0'] == [0.001,0.00075]
        update(f'상태: 학습 완료, 평가 중. 시작: {started}')
        current = evaluate(RUN/'weights/best.pt', OUT)
        with (RUN/'results.csv').open() as handle:
            epochs = list(csv.DictReader(handle))
        best = max(epochs, key=lambda r:float(r['metrics/mAP50-95(B)']))
        lines = ['### F 결과 — A 기준 학습률 실험 완료', '',
                 f'시작 {started} / 완료 {datetime.now().isoformat(timespec="seconds")}',
                 f'학습 {len(epochs)}에포크, 최고 검증 에포크 {best["epoch"]}, 시간 {float(epochs[-1]["time"])/60:.1f}분.',
                 '학습은 A의 원래 데이터, 최종 비교는 두 모델 모두 같은 수정 valid 78장이다.',
                 'Precision·Recall·F1은 매칭 IoU 0.5의 micro 평균. mAP는 별도 전체 신뢰도 구간 평가.', '']
        for conf in [.65,.60]:
            a,b = fixed(reference,conf),fixed(current,conf)
            lines += [f'**신뢰도 {conf*100:.0f}% 비교**', '',
                      '| 지표 | A: 0.001 | F: 0.00075 | 변화(%p) |', '|---|---:|---:|---:|']
            for key in ['precision','recall','f1','map50','map50_95']:
                x,y = (a[key],b[key]) if key in a else (reference[key],current[key])
                delta = '해당 없음' if x is None or y is None else f'{100*(y-x):+.2f}'
                lines.append(f'| {key} | {pct(x)} | {pct(y)} | {delta} |')
            lines += ['',f'TP/FP/FN: A {a["tp"]}/{a["fp"]}/{a["fn"]} → F {b["tp"]}/{b["fp"]}/{b["fn"]}', '']
        a,b = fixed(reference,.65),fixed(current,.65)
        lines += ['| 클래스(65%) | A 정밀도 | F 정밀도 | A Recall | F Recall |','|---|---:|---:|---:|---:|']
        old_classes = {r['name']:r for r in a['classes']}
        for r in b['classes']:
            old = old_classes[r['name']]
            lines.append(f'| {r["name"]} | {pct(old["precision"])} | {pct(r["precision"])} | {pct(old["recall"])} | {pct(r["recall"])} |')
        lines += ['', '단일 시드 실험이며 65% 정밀도를 우선 판단한다. 최고 가중치는 기존과 같은 검증 mAP50-95 기준이다.',
                  '서비스 A 모델·65%·1초 조건은 자동 변경하지 않았다.']
        result = '\n'.join(lines)
        (OUT/'comparison.md').write_text(result, encoding='utf-8')
        (OUT/'args_difference.json').write_text(json.dumps(differences,indent=2),encoding='utf-8')
        update(result)
        print('Experiment F complete.',flush=True)
    except Exception as exc:
        update(f'상태: 실행 실패 ({type(exc).__name__}). runs/logs/lr00075_training.log 및 .err.log 확인.')
        raise


if __name__ == '__main__':
    main()
