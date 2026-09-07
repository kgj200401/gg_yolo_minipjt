"""Roboflow workflow adapter. Credentials stay on the server."""
import base64
import binascii
import os
import io
from pathlib import Path
from threading import Lock

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter()
_model = None
_model_lock = Lock()


def local_detect(body):
    global _model
    from PIL import Image, UnidentifiedImageError
    try:
        prefix, encoded = body.image.split(",", 1)
        if prefix != "data:image/jpeg;base64":
            raise ValueError()
        raw = base64.b64decode(encoded, validate=True)
        image = Image.open(io.BytesIO(raw))
        if image.format != "JPEG" or image.width * image.height > 16_000_000:
            raise ValueError()
        image = image.convert("RGB")
    except (ValueError, binascii.Error, UnidentifiedImageError, OSError):
        raise HTTPException(400, "올바른 JPEG 이미지가 필요합니다.") from None
    try:
        with _model_lock:
            if _model is None:
                root = Path(__file__).resolve().parent
                config_dir = root / ".yolo-config"
                config_dir.mkdir(exist_ok=True)
                os.environ.setdefault("YOLO_CONFIG_DIR", str(config_dir))
                from ultralytics import YOLO
                _model = YOLO(str(root / "runs/detect/ozm_augmented/weights/best.pt"))
            result = _model.predict(image, device=os.environ.get("YOLO_DEVICE", "0"),
                                    imgsz=640, conf=0.25, iou=0.7, verbose=False)[0]
            predictions = [{"class_name": result.names[int(cls)], "confidence": float(conf)}
                           for cls, conf in zip(result.boxes.cls.tolist(), result.boxes.conf.tolist())]
        return {"predictions": predictions, "backend": "local", "model": "ozm_augmented/best.pt"}
    except ImportError:
        raise HTTPException(503, "학습 환경의 Python으로 서버를 실행해주세요.") from None
    except Exception:
        raise HTTPException(503, "로컬 모델 실행 실패: 모델 파일과 GPU 설정을 확인해주세요.") from None


class DetectionRequest(BaseModel):
    image: str = Field(min_length=1, max_length=8_000_000)


def extract_predictions(value):
    """Accept named workflow outputs containing detection prediction lists."""
    if isinstance(value, list):
        for item in value:
            yield from extract_predictions(item)
    elif isinstance(value, dict):
        if isinstance(value.get("class"), str) and isinstance(value.get("confidence"), (int, float)):
            yield {"class_name": value["class"], "confidence": value["confidence"]}
        else:
            for item in value.values():
                if isinstance(item, (dict, list)):
                    yield from extract_predictions(item)


@router.post("/detect")
def detect_image(body: DetectionRequest):
    if os.environ.get("DETECTION_BACKEND", "local") == "local":
        return local_detect(body)
    key = os.environ.get("ROBOFLOW_API_KEY", "").strip()
    if not key:
        raise HTTPException(503, "서버에 ROBOFLOW_API_KEY를 설정한 뒤 재시작해주세요.")
    prefix = "data:image/jpeg;base64,"
    if not body.image.startswith(prefix):
        raise HTTPException(400, "JPEG 이미지가 필요합니다.")
    encoded = body.image[len(prefix):]
    try:
        raw = base64.b64decode(encoded, validate=True)
        if not raw.startswith(b"\xff\xd8\xff"):
            raise ValueError("Not JPEG")
    except (ValueError, binascii.Error):
        raise HTTPException(400, "올바른 JPEG 이미지가 아닙니다.") from None
    try:
        from inference_sdk import InferenceHTTPClient, InferenceConfiguration

        client = InferenceHTTPClient(
            api_url="https://serverless.roboflow.com",
            api_key=key,
        ).configure(InferenceConfiguration(api_key_transport="header"))
        result = client.run_workflow(
            workspace_name="sang-rqj4u",
            workflow_id="ozm-vozm-4-yolov8n-t1-logic",
            images={"image": encoded},
            use_cache=True,
        )
    except ImportError:
        raise HTTPException(503, "서버에서 uv sync를 실행해주세요.") from None
    except Exception:
        # SDK exception messages can contain credentials or request contents.
        raise HTTPException(502, "모델 호출에 실패했습니다. API 키, 워크플로 배포 상태와 네트워크를 확인해주세요.") from None
    predictions = list(extract_predictions(result))
    return {"predictions": predictions}
