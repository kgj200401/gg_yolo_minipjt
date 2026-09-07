# 증강 학습

- 학습 원본 622장 + 시계 방향 90도 회전본 622장 = 1,244장
- 검증 78장·테스트 78장은 기존 파일을 그대로 사용
- 회전 시 라벨도 `(x,y,w,h) → (1-y,x,h,w)`로 변환, 622쌍 검증 완료
- 실시간 학습 증강: 수평 반전 확률 0.5, 회전 ±15도, x/y shear 각각 ±10도
- 기존 YOLO 기본 증강(색상·크기·이동·mosaic 등)은 유지
- 기본 수평 반전은 이전 학습에도 확률 0.5로 적용됨
- YOLOv8n 사전학습 가중치에서 새로 시작하며 이전 best.pt/optimizer는 사용하지 않음
- 최대 150에포크, batch 16, AdamW lr0=0.001, cosine LR, patience 25

데이터 생성: `prepare_augmentation.py`

학습 및 자동 평가: `run_augmented_training.py`

진행 로그:

```powershell
Get-Content augmentation-run.log -Tail 10 -Wait
```

결과 모델: `runs/detect/ozm_augmented/weights/best.pt`

자동 평가 수치: `runs/evaluation_augmented/report.json`

이전 모델과의 비교표: `runs/evaluation_augmented/comparison.md`

평가는 기존과 동일하게 테스트 분할에서 confidence 0.70, 매칭 IoU 0.50의
micro Precision/Recall/F1, 별도 낮은 임계값에서 전체 mAP를 계산합니다.
테스트 분할을 반복 비교에 사용하므로 최종 성능 주장에는 추가 독립 데이터가 권장됩니다.
증강으로 성능이 반드시 좋아지는 것은 아닙니다. 새 모델은 웹앱에 자동 적용하지 않습니다.
