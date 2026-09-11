# 학습·평가·데이터 실험

모든 명령은 **프로젝트 루트**에서 실행한다. 스크립트는 `experiments/`로 이동했고 데이터·가중치·결과 경로는 유지했다.

| 용도 | 파일 |
|---|---|
| 학습 공통 진입점 | `train_model.py` |
| 평가 | `evaluate_model.py`, `evaluate_thresholds.py`, `evaluate_class_thresholds.py` |
| 증강·라벨 수정본 생성 | `prepare_augmentation.py`, `prepare_corrected_dataset.py`, `prepare_validation_revision.py` |
| 라벨·오탐·학습 곡선 검토 | `audit_dataset.py`, `prepare_label_review.py`, `audit_shear_errors.py`, `analyze_training_curves.py` |
| A 증강 학습 | `run_augmented_training.py` |
| B/C 증강 비교 | `run_no_rotation_experiment.py`, `run_shear_experiment.py` |
| D 수정 데이터 | `run_corrected_experiment.py` |
| E/F 학습률 | `run_lr_experiment.py`, `run_lr00075_experiment.py` |
| G 배치 | `run_batch_experiment.py` |
| H 왜곡 제거 | `run_shear0_experiment.py` |
| I 분류 손실 | `run_cls_experiment.py` |
| J 조합 | `run_combined_experiment.py` |
| K 모델 크기 | `run_capacity_experiment.py` |

```powershell
.\.venv-train\Scripts\python.exe experiments/train_model.py --help
.\.venv-train\Scripts\python.exe experiments/evaluate_class_thresholds.py
Get-Content runs/logs/capacity_training.log -Encoding UTF8 -Tail 10
```

기존 실험 러너는 결과 덮어쓰기를 방지한다. 단순 확인을 위해 학습 러너를 다시 실행하지 말고 결과 문서와 JSON을 읽는다. 직접 실행하는 `.py` 방식이 공식 실행 방법이다(`python -m experiments...` 방식은 지원 대상으로 구성하지 않았다).

## 데이터·결과 위치

- `dataset/`: 원본 데이터.
- `dataset_augmented/`: A 및 주요 비교 실험의 90도 증강 데이터.
- `dataset_corrected_v*/`, `dataset_corrected_augmented_v*/`: 단계별 수정본. v3_review는 검토용 검증 라벨 수정본.
- `runs/detect/`: 실험별 학습 결과와 `weights/best.pt`.
- `runs/*/report.json`, `comparison.md`: 평가·비교 산출물.
- `runs/logs/`: 실행 로그와 과거 PID 기록. PID 파일은 현재 프로세스 실행 여부의 증거가 아니다.
- 루트 `yolov8n.pt`, `yolov8s.pt`: 새 학습의 출발점인 사전학습 가중치.

데이터 YAML과 과거 args.yaml에 절대경로가 있으며 서비스는 `runs/detect/ozm_augmented/weights/best.pt`를 읽는다. 재현성과 서비스 연속성을 위해 데이터·가중치·학습 결과를 이번에는 이동하지 않았다. 과거 결과 안의 실행 명령은 당시 기록이며, 현재 실행 명령은 이 안내와 docs를 따른다.

실험 과정·수치: [파인튜닝 진행](../docs/파인튜닝%20진행.md). 현재 동작은 A 모델 + 상품별 신뢰도 + 1초 확인이다.
