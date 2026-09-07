# 시퀀스 다이어그램

다이어그램은 Mermaid를 지원하는 Markdown 뷰어에서 렌더링할 수 있습니다.

## 1. 현재 개발용 상품 인식 및 장바구니 추가

```mermaid
sequenceDiagram
    autonumber
    actor User as 사용자
    participant Camera as 브라우저 카메라
    participant React as React
    participant API as FastAPI
    participant DB as SQLite

    User->>React: 카메라 시작 클릭
    React->>Camera: getUserMedia() 요청
    Camera-->>React: 실시간 영상 스트림
    React-->>User: 카메라 미리보기 표시

    Note over User,React: YOLO 미연동 개발 단계
    User->>React: 테스트 상품 선택 및 인식 클릭
    React->>API: POST /cart/add<br/>{product_name}
    API->>DB: 상품명 조회

    alt 등록된 상품
        API->>DB: 장바구니 생성 또는 수량 +1
        DB-->>API: 변경된 장바구니
        API-->>React: cart, total_price
        React-->>User: 장바구니 및 성공 토스트 갱신
    else 등록되지 않은 상품
        API-->>React: 404 오류
        React-->>User: 오류 토스트 표시
    end
```

## 2. 장바구니 수량 변경

```mermaid
sequenceDiagram
    autonumber
    actor User as 사용자
    participant React as React
    participant API as FastAPI
    participant DB as SQLite

    alt 수량 증가
        User->>React: + 버튼 클릭
        React->>API: POST /cart/add
        API->>DB: quantity + 1
    else 수량 감소
        User->>React: - 버튼 클릭
        React->>API: POST /cart/remove
        alt 기존 수량이 2 이상
            API->>DB: quantity - 1
        else 기존 수량이 1
            API->>DB: 장바구니 항목 삭제
        end
    end

    DB-->>API: 변경 완료
    API-->>React: cart, total_price
    React-->>User: 장바구니 화면 갱신
```

## 3. 구매 완료 및 요리 추천

```mermaid
sequenceDiagram
    autonumber
    actor User as 사용자
    participant React as React
    participant API as FastAPI
    participant DB as SQLite

    User->>React: 구매 완료 · 요리 추천 보기
    React->>API: POST /purchase
    API->>DB: 장바구니 상품과 수량 조회

    alt 장바구니가 비어 있음
        API-->>React: 400 오류
        React-->>User: 상품 추가 안내 토스트
    else 장바구니에 상품 존재
        API->>DB: 레시피와 필요 재료·수량 조회
        DB-->>API: 레시피 5종 데이터
        loop 각 레시피
            API->>API: 보유 수량과 필요 수량 비교
            API->>API: 부족량과 일치율 계산
            API->>API: 제작 가능 여부 분류
        end
        API->>API: 부족 종류 오름차순,<br/>일치율 내림차순 정렬
        API-->>React: 구매 내역, 총액, 추천 목록
        React-->>User: 요리 추천 결과 표시
    end
```

## 4. 상세 요리법 조회

```mermaid
sequenceDiagram
    autonumber
    actor User as 사용자
    participant React as React
    participant API as FastAPI
    participant DB as SQLite

    User->>React: 요리법 보기 클릭
    React->>API: GET /recipes/{recipe_id}
    API->>DB: 요리 이름 조회
    API->>DB: 재료명·수량·단위 조회
    API->>DB: 단계별 요리 방법 조회

    alt 레시피 존재
        DB-->>API: 상세 레시피
        API-->>React: name, ingredients, steps
        React-->>User: 레시피 상세 모달 표시
        User->>React: 닫기 버튼, 배경 또는 Esc
        React-->>User: 모달 닫기
    else 레시피 없음
        API-->>React: 404 오류
        React-->>User: 오류 토스트 표시
    end
```

## 5. 새 쇼핑 시작

```mermaid
sequenceDiagram
    autonumber
    actor User as 사용자
    participant React as React
    participant API as FastAPI
    participant DB as SQLite

    User->>React: 새 쇼핑 시작 클릭
    React->>API: DELETE /cart
    API->>DB: 모든 cart_items 삭제
    DB-->>API: 삭제 완료
    API-->>React: 빈 장바구니, 총액 0원
    React->>React: 추천 결과와 모달 초기화
    React-->>User: 쇼핑 메인 화면 표시
```

## 6. 향후 YOLO 연결 흐름

아래 흐름은 모델 학습 완료 후 구현할 예정입니다.

```mermaid
sequenceDiagram
    autonumber
    actor User as 사용자
    participant Camera as 카메라
    participant Detector as YOLO 탐지 모듈
    participant Guard as 중복 탐지 방지
    participant API as FastAPI
    participant DB as SQLite
    participant React as React

    loop 카메라 프레임 처리
        Camera->>Detector: 영상 프레임
        Detector->>Detector: 객체 탐지 및 신뢰도 필터

        alt 등록 상품 탐지
            Detector->>Guard: class_name, confidence
            alt 신규 탐지 또는 쿨다운 종료
                Guard->>API: POST /cart/add<br/>{product_name}
                API->>DB: 장바구니 수량 반영
                DB-->>API: 변경된 장바구니
                API-->>Guard: 추가 결과
                React->>API: GET /cart (2.5초 주기)
                API-->>React: 최신 장바구니
                React-->>User: 인식 상품 및 장바구니 표시
            else 중복 탐지
                Guard->>Guard: 추가 요청 생략
            end
        end
    end
```

## 7. 시스템 구성 관계

```mermaid
flowchart LR
    U[사용자] --> C[카메라]
    C --> R[React UI]
    C -. 향후 프레임 전달 .-> Y[YOLO 모델]
    Y -. 상품명 .-> A[FastAPI]
    R -->|REST API| A
    A --> S[(SQLite)]
    S --> A
    A -->|장바구니·추천·레시피| R
    R --> U
```
