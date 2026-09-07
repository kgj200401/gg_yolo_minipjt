# API 연동 규격서

## 1. 공통 규격

| 항목 | 규격 |
|---|---|
| 개발 Base URL | `http://127.0.0.1:8000` |
| 데이터 형식 | JSON |
| 문자 인코딩 | UTF-8 |
| 요청 헤더 | `Content-Type: application/json` |
| 인증 | 없음(MVP 범위) |
| API 문서 | `http://127.0.0.1:8000/docs` |

허용된 React 개발 서버 Origin:

- `http://localhost:5173`
- `http://127.0.0.1:5173`

## 2. API 요약

| Method | Endpoint | 기능 | React 호출 시점 |
|---|---|---|---|
| GET | `/` | 서버 상태 확인 | 최초 화면 진입 |
| GET | `/products` | 상품 목록 조회 | 최초 화면 및 개발용 테스트 준비 |
| GET | `/cart` | 장바구니 조회 | 최초 진입 및 2.5초 주기 갱신 |
| POST | `/cart/add` | 상품 수량 1 증가 | 테스트 인식 또는 향후 YOLO 탐지 |
| POST | `/cart/remove` | 상품 수량 1 감소 | 장바구니 `−` 버튼 |
| DELETE | `/cart` | 장바구니 전체 초기화 | 새 쇼핑 시작 |
| POST | `/purchase` | 구매 완료 및 요리 추천 | 구매 완료 버튼 |
| GET | `/recipes/{recipe_id}` | 상세 요리법 조회 | 요리법 보기 버튼 |

## 3. 공통 오류 응답

```json
{
  "detail": "오류 메시지"
}
```

| HTTP 상태 | 의미 |
|---:|---|
| 400 | 비어 있는 장바구니 등 잘못된 처리 상태 |
| 404 | 상품, 장바구니 항목 또는 레시피를 찾을 수 없음 |
| 422 | 요청 JSON 누락 또는 타입 오류 |
| 500 | 서버 내부 오류 |

---

## 4. 서버 상태 확인

### `GET /`

요청 Body는 없다.

성공 응답 `200 OK`:

```json
{
  "message": "Smart Cart API is running"
}
```

React 처리:

- 성공: `서버 연결됨` 표시
- 네트워크 오류: `서버 연결 실패` 표시

---

## 5. 상품 목록 조회

### `GET /products`

성공 응답 `200 OK`:

```json
[
  {
    "id": 1,
    "name": "마늘",
    "price": 3000
  },
  {
    "id": 2,
    "name": "사과",
    "price": 2500
  }
]
```

| 필드 | 타입 | 설명 |
|---|---|---|
| `id` | integer | 상품 DB ID |
| `name` | string | YOLO 클래스와 연결할 상품명 |
| `price` | integer | 상품 한 개 가격(원) |

---

## 6. 장바구니 조회

### `GET /cart`

성공 응답 `200 OK`:

```json
{
  "cart": [
    {
      "name": "식빵",
      "price": 3500,
      "quantity": 2
    }
  ],
  "total_price": 7000
}
```

| 필드 | 타입 | 설명 |
|---|---|---|
| `cart` | array | 현재 장바구니 항목 |
| `cart[].name` | string | 상품명 |
| `cart[].price` | integer | 상품 단가 |
| `cart[].quantity` | integer | 장바구니 수량 |
| `total_price` | integer | `가격 × 수량`의 전체 합계 |

빈 장바구니도 `200 OK`로 반환한다.

```json
{
  "cart": [],
  "total_price": 0
}
```

---

## 7. 장바구니 상품 추가

### `POST /cart/add`

요청:

```json
{
  "product_name": "사과"
}
```

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `product_name` | string | O | DB에 등록된 정확한 상품명 |

성공 응답 `200 OK`:

```json
{
  "message": "사과이(가) 장바구니에 추가되었습니다.",
  "cart": [
    {
      "name": "사과",
      "price": 2500,
      "quantity": 1
    }
  ],
  "total_price": 2500
}
```

처리 규칙:

- 장바구니에 상품이 없으면 수량 1로 생성한다.
- 이미 있으면 기존 수량을 1 증가시킨다.
- YOLO 연결 후에도 최종 탐지 상품명을 이 API에 전달한다.

상품이 없을 때 `404 Not Found`:

```json
{
  "detail": "상품을 찾을 수 없습니다."
}
```

---

## 8. 장바구니 수량 감소

### `POST /cart/remove`

요청:

```json
{
  "product_name": "사과"
}
```

성공 응답 `200 OK`:

```json
{
  "cart": [],
  "total_price": 0
}
```

처리 규칙:

- 수량이 2 이상이면 1 감소시킨다.
- 수량이 1이면 장바구니 항목을 삭제한다.
- 등록되지 않은 상품 또는 장바구니에 없는 상품은 `404`를 반환한다.

---

## 9. 장바구니 전체 초기화

### `DELETE /cart`

요청 Body는 없다.

성공 응답 `200 OK`:

```json
{
  "message": "장바구니를 비웠습니다.",
  "cart": [],
  "total_price": 0
}
```

---

## 10. 구매 완료 및 요리 추천

### `POST /purchase`

요청 Body는 없다. 서버에 저장된 현재 장바구니를 사용한다.

성공 응답 `200 OK`:

```json
{
  "message": "구매가 완료되었습니다. 장바구니 재료로 요리를 추천합니다.",
  "purchased_items": [
    {
      "name": "사과",
      "price": 2500,
      "quantity": 1
    },
    {
      "name": "식빵",
      "price": 3500,
      "quantity": 1
    },
    {
      "name": "계란",
      "price": 5000,
      "quantity": 1
    }
  ],
  "total_price": 11000,
  "recommendations": {
    "can_make": [],
    "need_more_ingredients": [
      {
        "recipe_id": 2,
        "recipe_name": "사과파이",
        "required_ingredients": ["사과", "식빵", "계란"],
        "owned_ingredients": ["사과", "계란"],
        "missing_ingredients": ["식빵"],
        "missing_ingredient_details": [
          {
            "name": "식빵",
            "required_amount": 2.0,
            "required_unit": "장",
            "owned_quantity": 1,
            "missing_amount": 1.0,
            "missing_quantity_text": "1장"
          }
        ],
        "match_rate": 66.7,
        "can_make": false
      }
    ]
  }
}
```

추천 필드:

| 필드 | 타입 | 설명 |
|---|---|---|
| `recipe_id` | integer | 상세 레시피 조회에 사용할 ID |
| `recipe_name` | string | 요리 이름 |
| `required_ingredients` | string[] | 전체 필요 재료명 |
| `owned_ingredients` | string[] | 필요 수량까지 충족한 재료명 |
| `missing_ingredients` | string[] | 없거나 수량이 부족한 재료명 |
| `missing_ingredient_details` | object[] | 재료별 필요량, 보유량, 부족량 |
| `match_rate` | number | 수량을 충족한 재료 종류 기준 일치율 |
| `can_make` | boolean | 모든 재료 수량 충족 여부 |

빈 장바구니 응답 `400 Bad Request`:

```json
{
  "detail": "장바구니가 비어 있습니다. 상품을 먼저 추가해주세요."
}
```

구매 완료를 호출해도 장바구니는 자동 삭제되지 않는다. 사용자가 추천 결과에서 `새 쇼핑 시작`을 누르면 `DELETE /cart`를 호출한다.

---

## 11. 상세 레시피 조회

### `GET /recipes/{recipe_id}`

경로 변수:

| 변수 | 타입 | 설명 |
|---|---|---|
| `recipe_id` | integer | 추천 응답에 포함된 레시피 ID |

성공 응답 `200 OK`:

```json
{
  "id": 2,
  "name": "사과파이",
  "ingredients": [
    {
      "name": "사과",
      "amount": 1.0,
      "unit": "개",
      "quantity_text": "1개"
    },
    {
      "name": "식빵",
      "amount": 2.0,
      "unit": "장",
      "quantity_text": "2장"
    },
    {
      "name": "계란",
      "amount": 1.0,
      "unit": "개",
      "quantity_text": "1개"
    }
  ],
  "steps": [
    {
      "step_number": 1,
      "instruction": "사과를 작게 썰어 설탕과 함께 팬에서 부드럽게 볶습니다."
    },
    {
      "step_number": 2,
      "instruction": "식빵 가장자리를 자르고 밀대로 얇게 눌러줍니다."
    }
  ]
}
```

없는 레시피 응답 `404 Not Found`:

```json
{
  "detail": "레시피를 찾을 수 없습니다."
}
```

## 12. React 호출 코드 기준

```javascript
const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

await fetch(`${API_URL}/cart/add`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ product_name: "사과" }),
});
```

운영 주소가 달라지면 React 실행 환경에 다음 값을 설정한다.

```text
VITE_API_URL=https://backend.example.com
```

## 13. 향후 YOLO 연동 규격 제안

이 절은 아직 구현되지 않은 예정 규격이다.

YOLO 출력 클래스가 영문이라면 FastAPI 호출 전에 고정 매핑을 사용한다.

```javascript
const CLASS_NAME_MAP = {
  garlic: "마늘",
  apple: "사과",
  green_onion: "대파",
  meat: "고기",
  onion: "양파",
  ham: "햄",
  carrot: "당근",
  egg: "계란",
  shrimp: "새우",
  bread: "식빵",
};
```

연속 프레임 중복 추가 방지 기준:

- 설정된 신뢰도 이상인 탐지만 사용한다.
- 동일 상품은 일정 시간의 쿨다운을 둔다.
- 가능하면 화면에서 사라진 뒤 다시 나타났을 때 다음 상품으로 처리한다.
- 장바구니에 추가하기 직전에 최종 상품명을 `POST /cart/add`에 전달한다.
