# Roboflow 모델 연결

현재 기본 모델은 로컬 `best.pt`입니다. 현재 실행 방법은 [로컬 모델 연결 및 결과](08-local-model-results.md)를 참고하세요.
아래는 `DETECTION_BACKEND=roboflow`로 선택하는 기존 클라우드 방식의 안내입니다.

프로젝트 루트의 PowerShell에서 실행합니다.

```powershell
uv sync
$env:ROBOFLOW_API_KEY = "새로 발급한 API 키"
uv run uvicorn main:app --reload
```

다른 터미널에서 프런트엔드를 실행합니다.

```powershell
cd frontend
npm install
npm run dev
```

웹앱에서 **카메라 시작**을 누르고 상품을 보여줍니다.
같은 상품이 신뢰도 70% 이상으로 1초 이상 연속 확인되면 자동으로 1개 담습니다.
같은 상품의 중복 탐지는 신뢰도가 가장 높은 결과 하나로 묶습니다.
담은 상품은 계속 보이는 동안 다시 담지 않습니다. 성공한 인식 결과에서 해당 상품이
한 번이라도 사라지면 재등록이 가능하며, 다시 나타나면 새로 1초 확인하고 추가합니다.
신뢰도가 낮아져도 상품이 탐지되고 있다면 재등록 잠금은 유지합니다.

Roboflow Cloud API 응답을 받은 뒤 0.5초 후 다음 사진을 보냅니다.
요청은 겹치지 않으며 실제 간격은 네트워크와 추론 시간에 따라 달라집니다.
1초는 촬영 시각 기준이며, 샘플 사이 모든 영상 프레임을 검사하는 것은 아닙니다.
확인 도중 70% 미만이 되거나 상품이 사라지면 확인 시간을 초기화합니다.
샘플 간격이 4초를 초과해도 확인 시간을 초기화합니다.
카메라 끄기 및 구매 완료 시 자동 인식을 중지합니다.
API 오류가 나면 카메라를 멈춥니다. 장바구니 추가 요청 중 오류가 났다면
장바구니 수량을 확인한 뒤 다시 시작하세요.

서버는 환경변수 `ROBOFLOW_API_KEY`를 사용합니다. `.env` 파일을 자동으로 읽지는 않습니다.
키를 소스 코드나 프런트엔드 환경변수에 넣지 마세요. 채팅에 공유한 키는 폐기 후 재발급하세요.

워크스페이스: `sang-rqj4u`

워크플로: `ozm-vozm-4-yolov8n-t1-logic`

영문 상품 클래스는 `frontend/src/App.jsx`의 `MODEL_PRODUCT_NAMES`에서 한국어 상품명과 연결합니다.

| 모델 클래스 | DB 상품명 |
| --- | --- |
| apple | 사과 |
| bread | 식빵 |
| carrot | 당근 |
| egg | 계란 |
| galic | 마늘 |
| large green onion | 대파 |
| onion | 양파 |
| raw_pork | 고기 |
| shrimp | 새우 |
| sliced_ham | 햄 |

`galic`은 모델의 실제 클래스 철자를 따릅니다. 기존 `garlic` 등의 별칭도 지원합니다.
클래스명의 앞뒤 공백과 대소문자는 정규화합니다.
등록되지 않은 클래스는 화면에 표시되지만 장바구니에는 추가되지 않습니다.
워크플로 출력에는 `class`, `confidence`를 포함한 탐지 결과가 있어야 합니다.
이미지 출력만 있는 워크플로는 Roboflow 편집기에서 예측 결과 출력도 추가해야 합니다.

공식 SDK 문서: https://inference.roboflow.com/workflows/modes_of_running/
