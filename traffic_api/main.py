from pathlib import Path
from typing import Any
from uuid import uuid4

from traffic_api.config import AppSettings, get_settings
from traffic_api.exceptions import InvalidImageError, TrafficAPIError
from traffic_api.image_quality import assess_image_quality
from traffic_api.image_utils import decode_image_bytes
from traffic_api.inference_service import TrafficSignDetector
from traffic_api.security import api_key_dependency
from traffic_api.serialization import result_to_contract_dict
from traffic_api.storage import save_result_image


def create_app(settings: AppSettings | None = None, detector: TrafficSignDetector | Any | None = None):
    from fastapi import Depends, FastAPI, File, Form, UploadFile
    from fastapi.responses import JSONResponse
    from fastapi.staticfiles import StaticFiles

    app_settings = settings or get_settings()
    app_detector = detector or TrafficSignDetector(settings=app_settings)
    app = FastAPI(title=app_settings.app_name, version="0.1.0")
    auth_dependency = api_key_dependency(app_settings)

    app_settings.save_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/outputs/detections", StaticFiles(directory=str(app_settings.save_dir)), name="detection_outputs")

    @app.exception_handler(TrafficAPIError)
    async def traffic_api_error_handler(_request, exc: TrafficAPIError):
        return JSONResponse(
            status_code=exc.status_code,
            content={"success": False, "message": exc.message, "error": {"code": exc.code}},
        )

    @app.get(f"{app_settings.api_prefix}/health")
    async def health():
        return {
            "status": "ok",
            "app_name": app_settings.app_name,
            "model_path": str(app_settings.model_path) if app_settings.model_path else None,
            "model_exists": bool(app_settings.model_path and app_settings.model_path.exists()),
            "device": app_settings.infer_device,
            "load_count": getattr(app_detector, "load_count", 0),
        }

    @app.get(f"{app_settings.api_prefix}/models/current")
    async def current_model():
        return {
            "success": True,
            "data": {
                "model_path": str(app_settings.model_path) if app_settings.model_path else None,
                "model_exists": bool(app_settings.model_path and app_settings.model_path.exists()),
                "device": app_settings.infer_device,
                "img_size": app_settings.img_size,
                "conf_threshold": app_settings.conf_threshold,
                "iou_threshold": app_settings.iou_threshold,
            },
        }

    @app.post(f"{app_settings.api_prefix}/detect/image", dependencies=[Depends(auth_dependency)])
    async def detect_image(
        file: UploadFile = File(description="Image file"),
        location: str | None = Form(default=None),
        description: str | None = Form(default=None),
    ):
        task_id = uuid4().hex
        data = await file.read()
        try:
            image = decode_image_bytes(data)
        except RuntimeError as exc:
            raise InvalidImageError(str(exc)) from exc
        except ValueError as exc:
            raise InvalidImageError(f"Invalid image upload: {exc}") from exc

        quality = assess_image_quality(image)
        if not quality.ok:
            raise InvalidImageError(quality.message)

        output = app_detector.detect_image(image)
        result_image = _save_visual_image(
            output.visual_image,
            app_settings.save_dir,
            file.filename,
        )
        return result_to_contract_dict(
            output.detection_result,
            task_id=task_id,
            model_path=app_settings.model_path,
            device=app_settings.infer_device,
            img_size=app_settings.img_size,
            conf_threshold=app_settings.conf_threshold,
            iou_threshold=app_settings.iou_threshold,
            result_image_url=result_image["url"] if result_image else None,
            filename=file.filename,
            location=location,
            description=description,
        )

    return app


def _save_visual_image(visual_image: Any | None, save_dir: Path, original_filename: str | None) -> dict[str, str] | None:
    if visual_image is None:
        return None
    output_path = save_result_image(visual_image, save_dir, original_filename)
    return {
        "path": str(output_path),
        "url": f"/outputs/detections/{output_path.name}",
    }


app = create_app()
