# 직접 학습하기

데이터셋은 프로젝트의 `dataset/`에 준비되어 있습니다.
ZIP 안의 동일한 `data.yaml` 중복 항목은 하나로 정리했고,
이미지 경로를 실제 압축 해제 위치에 맞게 수정했습니다.
일부 라벨의 다각형 좌표는 객체 탐지용 외접 사각형 좌표로 변환했습니다.
다운로드 폴더의 원본 ZIP은 수정하지 않았습니다.
프로젝트 위치를 옮긴 경우 `dataset/data.yaml`의 `path`도 변경하세요.

프로젝트 폴더의 PowerShell에서 실행합니다.

```powershell
.\.venv-train\Scripts\python.exe train_model.py --epochs 100 --batch 8 --lr0 0.001 --device 0
```

GPU 학습 환경은 `.venv-train`에 설치합니다. 기존 백엔드는 `.venv`를 사용합니다.
PyTorch 2.7.1+cu126, torchvision 0.22.1+cu126, Ultralytics 8.4.142를 사용합니다.
RTX 4060 Laptop GPU를 사용하려면 `--device 0`, CPU는 `--device cpu`로 지정합니다.
첫 학습 시 기본 YOLOv8n 가중치를 다운로드합니다.

다른 PC에서 학습 환경을 재설치할 때:

```powershell
uv venv .venv-train --python 3.10
uv pip install --python .venv-train/Scripts/python.exe -r requirements-training.txt
```

1에포크 시험 학습:

```powershell
.\.venv-train\Scripts\python.exe train_model.py --device 0 --epochs 1 --batch 8 --name gpu_smoke
```

설정 예시이며 최적 파라미터를 의미하지 않습니다.

## 본 학습 설정

```powershell
.\.venv-train\Scripts\python.exe train_model.py --device 0 --epochs 150 --batch 16 --lr0 0.001 --optimizer AdamW --patience 25 --workers 2 --cos-lr --name ozm_baseline
```

YOLOv8n, 이미지 크기 640, AdamW, 초기 학습률 0.001을 사용합니다.
코사인 학습률 감소를 적용하고 검증 성능이 25에포크 동안 개선되지 않으면
조기 종료합니다. 최적 설정을 입증한 것은 아니며 첫 본 학습의 기준 설정입니다.
결과는 `runs/detect/ozm_baseline`에 저장됩니다(기존 폴더가 있으면 번호 추가).
현재 실행 로그는 프로젝트 루트 `training-run.log`에서 확인할 수 있습니다.

```powershell
Get-Content training-run.log -Tail 20 -Wait
```

| 옵션 | 의미 | 기본값 |
| --- | --- | --- |
| --epochs | 최대 학습 반복 횟수 | 100 |
| --batch | 한 번에 학습하는 이미지 수 | 8 |
| --lr0 | 초기 학습률 | 0.001 |
| --optimizer | 최적화 알고리즘 | AdamW |
| --imgsz | 입력 이미지 크기 | 640 |
| --patience | 검증 성능 개선 없이 기다리는 에포크 수 | 20 |
| --model | 학습 시작 가중치 | yolov8n.pt |
| --name | 결과 폴더 이름 | ozm |

결과는 `runs/detect/ozm/`에 저장됩니다. 같은 이름의 폴더가 있으면
새 이름으로 저장되며, 실행 마지막에 실제 `best.pt` 경로가 표시됩니다.
학습 중에는 valid 분할로 성능을 확인하고, test 분할은 최종 평가용으로 보관하세요.

이 작업은 Roboflow 모델을 이어서 학습하는 것이 아니라 기본 YOLOv8n 가중치에서
우리 데이터로 새로 학습합니다. 현재 웹앱은 계속 Roboflow를 호출합니다.
학습 완료 후 로컬 `best.pt`를 사용하려면 `detection.py`에 로컬 추론 연결이 필요합니다.
데이터 클래스에 `l_onion`이 있으므로 로컬 모델 연결 시 대파 클래스 여부를 확인하고
한국어 상품명 매핑도 맞춰야 합니다.

공식 학습 설정: https://docs.ultralytics.com/modes/train/
