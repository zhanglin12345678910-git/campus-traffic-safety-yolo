# API Migration Plan: Minimal SF-FastGPT Detection Tool

Plan date: 2026-07-07

Goal: expose the existing traffic sign detection capability as a stable HTTP tool callable by SF-FastGPT, without replacing the desktop app, retraining models, changing weights, or changing class IDs.

## 1. Recommended Approach

Use the minimal shared-core approach:

1. Extract image inference into a small reusable service.
2. Update the desktop app only if needed to call that service.
3. Add a new FastAPI app that calls the same service.
4. Keep first-phase API image-only.
5. Add focused API tests and desktop smoke/regression checks.

This avoids a rewrite and prevents divergence between desktop and API behavior.

## 2. Proposed New Files

Suggested structure:

```text
traffic_api/
  __init__.py
  main.py                 # FastAPI app entry
  config.py               # environment/config parsing
  schemas.py              # response/request models
  exceptions.py           # business exceptions and error codes
  inference_service.py    # TrafficSignDetector / YOLOInferenceService
  image_quality.py        # blur/dark/size/decode checks
  storage.py              # upload/result file saving
  security.py             # X-API-Key validation
  logging_config.py       # safe logging setup

scripts/
  run_api.bat             # Windows API startup helper
  smoke_api_request.py    # simple manual request example

docs/
  API_README.md
  API_CONTRACT.md
  SF_FASTGPT_INTEGRATION.md
  TEST_REPORT.md
  CHANGELOG.md

.env.example
```

If the project owner prefers a flatter layout, `traffic_api/` can be renamed to `api/` or `agent_api/`.

## 3. Existing Files Likely to Change

Minimum likely changes:

- `app.py`
  - Ideally only replace direct image inference internals with a call to the shared service.
  - Preserve UI, startup command, labels, and current behavior.
- `pyproject.toml` or a new API requirements file
  - Add `fastapi`, `uvicorn`, `python-multipart`, and possibly `pydantic-settings`.
- `.gitignore`
  - Only adjust if new output folders such as `outputs/` are not already ignored.

Possible but avoid unless needed:

- `app_iter*.py`: do not change unless they become official desktop entries.
- `web_version/`: do not change in first phase.
- `ultralytics/`: do not change for API wrapping.

## 4. Files Not Recommended for Modification

- Original Word documents in `agent/`
- Model weights (`*.pt`, `*.onnx`, etc.)
- Training scripts unless a later training task is explicitly requested
- `runs/`, `results/`, `uploads/`, generated images
- `web_version/` Flask app in the first FastAPI phase
- Local Ultralytics internals unless a confirmed model-loading bug requires it

## 5. Shared Inference Service Design

Recommended class name: `TrafficSignDetector`

Responsibilities:

- Read model path, device, default `conf`, `imgsz`, and `iou` from config.
- Validate model path exists.
- Lazy-load or startup-load YOLO once per process.
- Keep `model_loaded` and `load_count`.
- Protect model loading with a lock.
- Protect inference with a lock in the first version for GPU stability.
- Accept image path, bytes, PIL image, or OpenCV array.
- Run current Ultralytics `model.predict` call.
- Convert every detection into structured fields:
  - `class_id`
  - `class_name`
  - `confidence`
  - `bbox_xyxy`
- Return original image width/height.
- Return `object_count`.
- Return timing:
  - wall-clock `total_ms`
  - Ultralytics `speed` fields when available: preprocess, inference, postprocess
- Generate an annotated result image via `res.plot()`.
- Save the result image through `storage.py`.
- Raise typed business exceptions for load, inference, conversion, or save failures.

The service must not generate risk conclusions or整改建议.

## 6. Desktop Migration Method

First safe option:

- Keep `app.py` direct behavior for the first API implementation.
- Build `TrafficSignDetector` independently using the same `YOLO(...).predict(...)` semantics.
- After API tests pass, optionally adapt `app.py` to call the shared service.

Lower-duplication option:

- Refactor `app.py` image detection to call the shared service immediately.
- This reduces duplicated inference logic but raises desktop regression risk.

Recommendation:

- Start with the first safe option if schedule is tight.
- Then migrate desktop image detection in a small second commit after service/API behavior is stable.
- Video/camera can continue using existing worker logic until a later refactor.

## 7. FastAPI Interface Design

### GET /health

No authentication required.

Response fields:

- `status`
- `model_loaded`
- `model_name`
- `model_version`
- `device`
- `api_version`
- `load_count`

### POST /api/v1/detect/image

Authentication:

- Header: `X-API-Key`
- Compare against configured `API_KEY`.

Request:

- `multipart/form-data`
- Required:
  - `file`
- Optional:
  - `conf`
  - `imgsz`
  - `location`
  - `description`

Supported extensions:

- `jpg`
- `jpeg`
- `png`
- `bmp`
- `webp`

Response follows the user-provided contract:

- `success`
- `task_id`
- `image`
- `model`
- `detections`
- `object_count`
- `review_required`
- `review_reasons`
- `result_image_url`
- `timing`
- `location`
- `description`
- `error`

Important:

- `model.weights` must be the filename only, not a full path.
- All detections must come from actual inference.
- No mock detections.

## 8. Configuration Plan

Use environment variables with safe defaults where appropriate:

- `YOLO_MODEL_PATH`
- `YOLO_DEVICE`
- `YOLO_DEFAULT_CONF`
- `YOLO_DEFAULT_IOU`
- `YOLO_DEFAULT_IMGSZ`
- `MAX_UPLOAD_MB`
- `RESULT_DIR`
- `UPLOAD_DIR`
- `API_KEY`
- `BLUR_THRESHOLD`
- `DARK_THRESHOLD`
- `BRIGHT_THRESHOLD`
- `MIN_IMAGE_WIDTH`
- `MIN_IMAGE_HEIGHT`
- `LOG_LEVEL`

Create `.env.example` only. Do not create a real `.env`.

## 9. Model Singleton and Concurrency

First version behavior:

- One model instance per process.
- Desktop process and API process may each load their own model if run separately.
- Within the API process:
  - model load lock prevents duplicate loads
  - inference lock serializes GPU inference for stability
  - `load_count` verifies singleton behavior

This is conservative but appropriate for a first SF-FastGPT tool.

## 10. File Storage Plan

Recommended local folders:

- uploads: `outputs/api_uploads/`
- results: `outputs/api_results/`

For each request:

- Generate a UUID task ID.
- Save the uploaded file with a sanitized filename.
- Save the annotated result image as `<task_id>_result.jpg`.
- Expose result images through a static route such as `/files/results/{filename}`.

Do not expose arbitrary file paths.

## 11. Image Quality and Review Rules

Implement lightweight checks only:

- Decode validity
- Width/height minimum
- Laplacian variance blur check
- Mean brightness dark/bright check

Set `review_required = true` if:

- image is severely blurred
- image is too dark or too bright
- image dimensions are too small
- no detections are returned
- all detections are below a low-confidence review threshold
- inference fails
- `location` is empty
- quality cannot be judged

Review flags are uncertainty signals, not risk conclusions.

## 12. Error Handling Plan

Return JSON for all handled errors.

Required error cases:

- missing file
- empty file
- unsupported extension
- suspicious MIME type
- too large
- image decode failure
- abnormal width/height
- missing model path
- model load failure
- unavailable CUDA/device mismatch
- inference failure
- result conversion failure
- result image save failure
- missing/invalid config
- wrong API key
- concurrency/lock timeout if implemented

Do not return full Python stack traces to clients.

## 13. Test Plan

API tests:

1. `GET /health`
2. valid JPG detection
3. valid PNG detection
4. missing file
5. empty file
6. txt file
7. corrupted image
8. file too large
9. wrong API key
10. correct API key
11. bad model path
12. no-target image
13. low-confidence result path
14. blurred image
15. dark image
16. three consecutive calls
17. model load count does not increase after repeated calls
18. result image is actually generated
19. bbox coordinates are within image bounds
20. class IDs are within model class range

Desktop regression:

- `python app.py` starts.
- Image detection still works with the confirmed model.
- Result display updates.
- Result image can be saved.

If UI automation is not feasible, document which desktop checks were manual.

## 14. Rollback Plan

Before implementation:

- Create branch `feat/agent-detection-api`.
- Confirm dirty working tree and preserve current user changes.

Rollback methods:

- If only new API files are added, remove `traffic_api/`, API docs, scripts, and `.env.example`.
- If `app.py` is changed, revert only the hunks introduced for shared-service integration.
- Keep original desktop command `python app.py` working throughout.
- Do not delete or rewrite existing weights/results.

## 15. Impact on Existing Desktop App

Target impact:

- No UI redesign.
- No change to default startup command.
- No change to class IDs or class names.
- No change to current video/camera behavior.
- Image detection should produce the same model predictions as before if the same model, device, `imgsz`, `conf`, and `iou` are used.

Known possible behavior changes if desktop is migrated to shared service:

- Result saving location may become service-managed unless the UI keeps manual `on_save()`.
- Timing values may include more detailed fields.
- All detections may become available internally even if UI still shows the highest-confidence one.

## 16. Acceptance Criteria for This Migration

First-phase completion requires:

- Desktop app still starts.
- Desktop image detection still works.
- FastAPI starts.
- `/docs` opens.
- `/health` returns real model status.
- `/api/v1/detect/image` accepts upload and returns actual detections.
- Result image is generated.
- API key auth works.
- Errors return JSON and do not crash the service.
- Model load count proves no reload per request in the same process.
- Docs are generated:
  - `API_README.md`
  - `API_CONTRACT.md`
  - `SF_FASTGPT_INTEGRATION.md`
  - `TEST_REPORT.md`
  - `CHANGELOG.md`

## 17. Not in First Phase

Do not implement now:

- YOLO retraining
- new campus training dataset
- Vue frontend
- MySQL
- login/roles
- video detection API
- camera detection API
- real-time monitoring
- mobile app or mini program
- multi-agent collaboration
- risk scoring
-整改建议 generation
- report generation
- hidden-danger ledger
- historical review workflow
- actual SF-FastGPT platform configuration
- Docker/server deployment

These belong to later phases after the visual detection API is stable.

## 18. Immediate Next Step Before Coding

Confirm these two items with the project owner:

1. Which checkpoint should `YOLO_MODEL_PATH` use for the API by default?
2. Which Python environment should be used for running tests, given the probed base Anaconda environment lacks `torch` and `cv2`?

After confirmation, create the implementation plan and start the branch.
