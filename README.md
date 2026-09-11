# AI 스마트 카트

카메라에 보여준 식재료를 인식해 장바구니에 자동으로 담고, 담은 재료를 바탕으로 요리와 부족한 재료를 안내하는 웹 프로젝트입니다.

현재는 직접 학습한 **YOLOv8n A 모델**을 로컬 백엔드에서 실행합니다. 데이터 증강, 학습률, 배치, 분류 손실, 모델 크기 등을 비교했고, 정밀도를 우선해 A 모델과 상품별 신뢰도 기준을 사용합니다.

## 주요 기능

- 카메라 프레임에서 식재료 10종을 탐지하고 영문 클래스를 한글 상품명으로 연결합니다.
- 상품별 신뢰도 기준 이상으로 1초간 확인되면 장바구니에 자동 추가합니다.
- 이미 담긴 상품은 화면에서 사라진 것이 확인된 뒤 다시 나타나야 재추가됩니다.
- 장바구니 수량 증가·감소·비우기·총액 확인을 지원합니다.
- 구매 완료 버튼으로 담은 재료 기반 요리 추천, 부족한 재료, 레시피를 확인합니다. 실제 결제 서비스와 연동한 기능은 아닙니다.
- 개발용 수동 상품 추가로 카메라 없이 장바구니와 추천 흐름을 확인할 수 있습니다.

현재 프로토타입은 하나의 SQLite DB에 장바구니를 저장합니다. 사용자별 로그인·장바구니 분리는 구현되어 있지 않습니다.

## 기술 구성

| 영역 | 사용 기술 / 역할 |
|---|---|
| 프런트엔드 | React 19, Vite, 브라우저 getUserMedia, Canvas |
| 백엔드 | Python, FastAPI, Uvicorn |
| AI | Ultralytics YOLOv8, PyTorch, 로컬 GPU 또는 CPU 추론 |
| DB | SQLite, SQLAlchemy — 상품·장바구니·레시피 저장 |
| 학습 환경 | Python 3.10, PyTorch 2.7.1+cu126, Ultralytics 8.4.142 |
| 사용 GPU | NVIDIA GeForce RTX 4060 Laptop GPU 8GB |
| 데이터 | Roboflow 내보내기 데이터, 증강·라벨 점검 Python 스크립트 |

```text
브라우저 카메라 → JPEG 프레임 → POST /detect → 로컬 YOLO
       ↓ 탐지 결과(영문 클래스·신뢰도)
한글 상품명 연결 → 상품별 기준·1초 확인 → POST /cart/add
       ↓
SQLite 저장 → 장바구니 갱신 → 구매 완료 → 요리 추천·레시피
```

영상 전체를 스트리밍하는 구조가 아니라 프레임을 캡처해 순차 요청합니다. 요청 처리 후 약 500ms 뒤 다음 캡처를 시도하므로 실제 인식 주기는 추론·통신 시간에 따라 달라집니다.

## 웹 실행하기 — Windows PowerShell

**백엔드와 프런트엔드를 각각 다른 터미널에서 실행합니다.** 아래 명령은 프로젝트 루트 기준입니다. PC마다 프로젝트 경로를 바꿔 주세요.

### 1. 처음 실행하는 PC에서 준비

필요 도구는 `uv`, Python 3.10, Node.js와 npm입니다. 설치된 Vite의 Node 요구 조건은 `^20.19.0 || >=22.12.0`입니다.

```powershell
cd C:\Users\Admin\workspace\gg_yolo_minipjt
uv --version
node --version
npm.cmd --version
```

로컬 AI 실행 환경을 만듭니다. **이미 `.venv-train`에 설치되어 있다면 아래 환경 생성·설치는 건너뜁니다.**

```powershell
uv venv .venv-train --python 3.10
uv pip install --python .venv-train/Scripts/python.exe -r requirements-training.txt
npm.cmd --prefix frontend ci
```

학습용 요구사항에는 PyTorch·Ultralytics와 웹 백엔드 패키지가 포함됩니다. 현재 로컬 인식은 **`.venv-train`의 Python으로 서버를 실행**해야 합니다. `uv sync`만으로 로컬 YOLO 의존성이 모두 설치되지는 않습니다. PowerShell 실행 정책의 `npm.ps1` 오류를 피하도록 예시에서는 `npm.cmd`를 사용합니다.

### 2. 학습된 모델 준비

백엔드가 읽는 파일은 `runs/detect/ozm_augmented/weights/best.pt`입니다.

```powershell
Test-Path .\runs\detect\ozm_augmented\weights\best.pt
```

`True`여야 로컬 상품 인식을 실행할 수 있습니다. **`runs/`, 데이터셋, `.pt`, 가상환경, DB는 Git 제외 대상이므로 clone만 해서는 준비되지 않습니다.** 팀에서 공유받은 A 모델의 `best.pt`를 위 위치에 넣으세요. 단순 웹 실행에는 학습 데이터셋 전체가 필요하지 않습니다.

루트 `yolov8n.pt`는 새 학습의 출발점인 사전학습 가중치입니다. 우리 상품을 학습한 `best.pt`를 대신하지 못합니다. 모델이 없어도 일부 웹·DB 화면은 열리지만 인식 요청은 실패합니다.

### 3. 터미널 1 — 백엔드 실행

현재 GPU PC의 실행 명령입니다.

```powershell
cd C:\Users\Admin\workspace\gg_yolo_minipjt
$env:DETECTION_BACKEND = "local"
$env:YOLO_DEVICE = "0"
.\.venv-train\Scripts\python.exe -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

GPU가 없거나 CPU로 확인하려면 다음과 같이 실행합니다. CPU에서는 인식 속도가 느릴 수 있습니다.

```powershell
$env:DETECTION_BACKEND = "local"
$env:YOLO_DEVICE = "cpu"
.\.venv-train\Scripts\python.exe -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

환경변수는 **서버를 실행하는 같은 터미널**에서 설정합니다. `.env` 자동 로딩은 구현되어 있지 않아 파일에 적기만 해서는 적용되지 않습니다. 로컬 모드에는 Roboflow API 키가 필요 없습니다.

- API 상태: <http://127.0.0.1:8000/> — `Smart Cart API is running` 응답
- API 문서: <http://127.0.0.1:8000/docs>
- 상품 목록: <http://127.0.0.1:8000/products>

서버 시작 시 테이블을 준비하고 기본 상품·레시피를 등록합니다. DB는 루트의 `smart_cart.db`이며 별도 DB 서버 설치는 필요 없습니다. 터미널은 실행 상태로 유지하세요.

### 4. 터미널 2 — 프런트엔드 실행

새 PowerShell 창에서 실행합니다.

```powershell
cd C:\Users\Admin\workspace\gg_yolo_minipjt
$env:VITE_API_URL = "http://127.0.0.1:8000"
npm.cmd --prefix frontend run dev -- --host localhost --port 5173 --strictPort
```

브라우저에서 **<http://localhost:5173/>**에 접속합니다. `--strictPort`는 Vite가 포트 충돌 시 다른 포트로 자동 변경되는 것을 방지합니다. 현재 백엔드 CORS는 `localhost:5173`, `127.0.0.1:5173`을 허용합니다.

`VITE_API_URL`을 생략하면 기본 API 주소는 `http://127.0.0.1:8000`입니다. 변경했다면 Vite를 재시작하세요. 프런트엔드 환경변수는 브라우저에 공개되므로 비밀 API 키를 넣지 않습니다.

### 5. 카메라 사용

1. 웹의 **카메라 시작** 버튼을 누르고 카메라 권한을 허용합니다.
2. 상품을 보여주고 해당 신뢰도 이상으로 1초간 확인될 때까지 기다립니다.
3. 자동 추가를 확인합니다. 같은 상품을 더 담으려면 화면에서 치운 뒤 다시 보여줍니다.
4. 수량·금액을 확인하고 **구매 완료 · 요리 추천 보기**를 누릅니다.

| 모델 클래스 | 상품 | 자동 담기 기준 |
|---|---|---:|
| apple | 사과 | 50% |
| galic | 마늘 | 60% |
| l_onion | 대파 | 60% |
| shrimp | 새우 | 60% |
| bread | 식빵 | 65% |
| carrot | 당근 | 65% |
| egg | 계란 | 65% |
| onion | 양파 | 65% |
| raw_pork | 고기 | 65% |
| sliced_ham | 햄 | 65% |

`galic`은 학습 클래스의 실제 철자입니다. `frontend/src/confidencePolicy.json`에서 기준을 관리하고 `detectionTracker.js`에서 1초 확인과 재등장을 처리합니다. 같은 상품 여러 개의 수량을 한 프레임에서 자동 계산하지 않으며 상품별 대표 신뢰도를 사용합니다.

카메라는 로컬에서는 `localhost`로 확인하세요. 다른 PC·휴대폰에서 접속하려면 브라우저 카메라의 보안 컨텍스트(HTTPS 등), 서버 바인딩·방화벽, API 주소와 CORS를 함께 설정해야 합니다. 다른 장치의 `127.0.0.1`은 서버 PC가 아닙니다. 위 명령은 같은 PC에서의 로컬 실행 기준입니다.

### 6. 종료·다음 실행

각 서버 터미널에서 `Ctrl+C`로 종료합니다. 다음에는 설치를 반복하지 않고 **3번과 4번**만 실행하면 됩니다. 모델은 프로세스에 캐시되므로 가중치를 바꿨다면 백엔드를 재시작하세요.

## 자주 발생하는 문제

| 증상 | 확인 방법 |
|---|---|
| uv 또는 node 명령을 찾을 수 없음 | 설치와 PATH를 확인하고 터미널을 새로 엽니다. |
| 학습 환경의 Python으로 실행하라는 오류 | `.venv-train\Scripts\python.exe -m uvicorn ...`으로 실행했는지 확인합니다. |
| 로컬 모델 실행 실패 | A best.pt 존재, GPU 인식, YOLO_DEVICE를 확인합니다. |
| ROBOFLOW_API_KEY 설정 요청 | 서버 터미널에서 DETECTION_BACKEND를 local로 설정하고 재시작합니다. |
| 카메라 화면이 안 보임 | 사이트·Windows 카메라 권한, 다른 앱의 카메라 점유, localhost 접속을 확인합니다. |
| 상품·장바구니를 못 불러옴 | API 상태 주소, VITE_API_URL, 두 서버 실행 여부를 확인합니다. |
| 상품명 연결 필요 | `/products`의 한글 이름과 App.jsx의 MODEL_PRODUCT_NAMES를 확인합니다. |
| Vite 포트 충돌 / CORS 오류 | 기존 서버 실행 여부를 확인합니다. 프런트 포트를 바꾸면 main.py의 허용 출처도 맞춰야 합니다. |
| GET /cart 200 OK 반복 | 장바구니 조회 성공 로그이며 그 자체로 오류는 아닙니다. |
| WinError 10013 / 8000 사용 불가 | 포트 점유·Windows 예약 포트·보안 프로그램 제한 가능성. 다른 포트로 실행하고 API 주소도 맞춥니다. |

8001 포트로 실행하는 예시:

```powershell
# 백엔드 터미널: 기존 서버 종료 후
$env:DETECTION_BACKEND = "local"
$env:YOLO_DEVICE = "0"
.\.venv-train\Scripts\python.exe -m uvicorn main:app --reload --host 127.0.0.1 --port 8001

# 프런트 터미널: 기존 Vite 종료 후
$env:VITE_API_URL = "http://127.0.0.1:8001"
npm.cmd --prefix frontend run dev -- --host localhost --port 5173 --strictPort
```

GPU 확인 명령:

```powershell
nvidia-smi
.\.venv-train\Scripts\python.exe -c "import torch; print('CUDA:', torch.cuda.is_available())"
```

## API 요약

| 요청 | 역할 |
|---|---|
| GET / | 서버 상태 |
| GET /products | 상품 목록 |
| POST /detect | JPEG data URL 이미지 인식 |
| GET /cart | 장바구니·총액 조회 |
| POST /cart/add, POST /cart/remove | 수량 증가·감소 |
| DELETE /cart | 장바구니 비우기 |
| POST /purchase | 담은 재료 기반 요리 추천 |
| GET /recipes/{recipe_id} | 레시피 상세 |

정확한 요청·응답은 실행 중인 백엔드의 `/docs`를 참고하세요. Roboflow 호출 코드도 남아 있지만 기본 실행은 로컬 모델입니다. 클라우드 모드는 별도 SDK·서버 API 키·워크플로 구성이 필요합니다.

## 프로젝트 구조

| 위치 | 용도 |
|---|---|
| `main.py`, `database.py`, `models.py`, `detection.py` | 서비스 백엔드 |
| `frontend/` | 카메라·자동 담기·장바구니 화면 |
| [experiments/](experiments/README.md) | 학습·평가·데이터 점검 스크립트 |
| [docs/](docs/README.md) | 설계 문서와 실험 기록 |
| `dataset*/` | 원본·증강·수정 데이터(로컬 보관) |
| `runs/` | 학습 가중치·평가 결과, `logs/` 아래 실행 로그 |

현재 모델: `runs/detect/ozm_augmented/weights/best.pt`(A).
자동 담기: 사과 50%, 마늘·대파·새우 60%, 나머지 65% 이상으로 1초 확인. 같은 상품은 사라진 후 다시 나타나야 재추가됩니다.

실험 스크립트는 프로젝트 루트에서 `python experiments/파일명.py` 형식으로 실행합니다. 자세한 명령과 결과는 [실험 안내](experiments/README.md) 및 [파인튜닝 진행](docs/파인튜닝%20진행.md)을 참고하세요.

## 실험·테스트·빌드

```powershell
.\.venv-train\Scripts\python.exe experiments/train_model.py --help
.\.venv-train\Scripts\python.exe experiments/evaluate_class_thresholds.py
node --test frontend/src/detectionTracker.test.js
npm.cmd --prefix frontend run build
```

평가에는 로컬 모델과 데이터가 필요합니다. 기존 실험 러너는 덮어쓰기를 방지하므로 결과 확인 목적으로 학습을 다시 실행하지 마세요.

현재 검토용 검증 78장에서 상품별 기준 적용 후 Precision **94.70%**, Recall **57.66%**, F1 **71.68%**, TP/FP/FN **143/8/105**를 확인했습니다. 이는 같은 검증 자료에서 선택한 기준을 재평가한 객체 탐지 수치이며 실제 자동 담기 성공률이나 새 촬영 환경의 성능을 뜻하지 않습니다. 미확정 라벨이 남아 있어 후속 검증이 필요합니다.

빌드는 정적 파일을 생성합니다. HTTPS·인증·사용자별 DB 분리를 포함한 외부 운영 배포는 이 로컬 실행 안내에 포함하지 않습니다.

## 관련 문서

- [문서 목록](docs/README.md)
- [실험 스크립트 안내](experiments/README.md)
- [파인튜닝 진행·성능 비교](docs/파인튜닝%20진행.md)
- [검증 라벨 재검토](docs/검증라벨_재검토.md)
- [파일 정리 내역](docs/파일정리.md)
- [학습 환경·기본 명령](docs/07-local-training.md) — 최초 학습 당시 기록이 포함되어 있습니다. 현재 웹 실행은 이 README를 기준으로 합니다.
