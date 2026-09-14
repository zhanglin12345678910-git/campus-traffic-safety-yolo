# Project Audit: Agent Detection API Migration

Audit date: 2026-07-07

Scope: read-only audit of the current repository before any business-code change. This audit covers the desktop application, model references, inference chain, project documents in `agent/`, dependency signals, and migration risks for an SF-FastGPT-callable traffic sign detection HTTP tool.

## 1. Basic Project Information

- Repository root: `<PROJECT_ROOT>`
- Git repository: yes
- Current branch observed: `master`
- Current worktree status:
  - Modified: `claude-修改/generate_dataset.py`
  - Untracked: `.git_commit_msg.txt`, `.ultralytics_tmp/`, `agent/`, `detect copy.py`
- Latest observed commits:
  - `d601f28` Add traffic sign dataset analysis script and documentation updates
  - `7cfee48` Add SPPF/ASPP/MSConv multi-scale comparison modules and utility tools
  - `417ff13` Update: Modify documentation and add test file x
  - `594e3f4` Add web_version_02 and update documentation

Important: the worktree is not clean. Implementation should not start until a development branch is created and the current dirty state is intentionally preserved.

## 2. Current Directory Structure

Top-level folders relevant to this task:

- `agent/`: three reference Word documents for the campus traffic safety intelligent inspection agent.
- `app.py`: current active PyQt5 desktop application.
- `app_iter1_statistics.py`, `app_iter2_compare.py`, `app_iter3_batch.py`: desktop iterations with statistics, comparison, and batch detection features.
- `web_version/`: existing Flask + SQLAlchemy web version. It is useful as reference but is not the requested FastAPI/SF-FastGPT tool.
- `ultralytics/`: local Ultralytics source tree, `__version__ = "8.3.9"`.
- `runs/`: many training/validation outputs and weights, including TT100K and CCTSDB experiments.
- `dataset/`, `tessss1/`: sample dataset/config folders.
- `tests/`, `test_*.py`, `validate_*.py`: upstream Ultralytics tests and local validation scripts.
- `uploads/`, `results/`, `generated_results_png/`: generated or user-output data.

## 3. Current Startup Methods

Confirmed desktop entry:

- `python app.py`
- Entry point: `if __name__ == "__main__"` creates `QApplication`, instantiates `Main`, shows the window, then runs `app.exec_()`.

Other available but non-primary entries:

- `python app_iter1_statistics.py`
- `python app_iter2_compare.py`
- `python app_iter3_batch.py`
- `web_version/启动多模型系统.bat` runs `python web_app.py` in `web_version/`.
- `web_version/启动Web版本.bat` calls `python start_web.py`, but `start_web.py` was not observed in the listed files.

## 4. Desktop Application Entry and GUI Framework

Active desktop entry: `app.py`

GUI framework:

- PyQt5
- Main window class: `Main(QMainWindow)`
- Worker classes:
  - `VideoWorker(QThread)`
  - `CameraWorker(QThread)`

The current desktop app supports:

- Image detection
- Video detection
- Camera detection
- Model selection
- Result preview
- Manual result-image saving

`app_iter3_batch.py` additionally contains batch-image detection, but `app.py` does not expose batch detection.

## 5. Actual Model Version and Weights

The current code and repository evidence point to YOLO11-family work, not YOLO26.

Evidence:

- Repository name includes `ultralytics-yolo11-main`.
- `ultralytics/__init__.py` reports local Ultralytics version `8.3.9`.
- `pyproject.toml` keywords include `YOLO11`.
- `app.py` display model names include `YOLO11n` and the default `PSSM-YOLO-Lite-KD`.
- TT100K training args at `runs/train/TT100K-增强-yolo11-第一个实验-newt100k2/args.yaml` record:
  - `task: detect`
  - `model: ...\yolo11-CSP-PMSFA.yaml`
  - `data: <LOCAL_PATH>
  - `imgsz: 640`
  - `epochs: 200`

Current desktop default model:

- `DEFAULT_MODEL_ID = "PSSM-YOLO-Lite-KD"`
- Default weight path in `app.py`:
  - `<LOCAL_PATH>`

Risk:

- The default weight is an absolute `<LOCAL_PATH>` path outside the repository.
- The audit environment could not reliably verify this external `F:` weight path.
- The repository contains many `.pt` files under `runs/`, including TT100K and CCTSDB experiments, but the active desktop app does not currently point to the TT100K weight in `runs/train/TT100K-增强-yolo11-第一个实验-newt100k2/weights/best.pt`.

Do not claim YOLO26 unless a future verified weight/config actually proves YOLO26 usage.

## 6. Model Loading Flow

In `app.py`:

- `Main.__init__` initializes `self.model_cache = {}`.
- `get_model()` checks `self.current_model_id`.
- If the model is already in `model_cache`, it returns the cached model.
- Otherwise it resolves the path from `MODELS`, checks `os.path.exists`, then calls `YOLO(model_path)`.

This is lazy loading, not eager loading.

Within the desktop process, each selected model is intended to load once and be reused. However, there is no lock around `model_cache`; the GUI mostly calls from the main thread, while video/camera workers receive already-loaded model objects.

## 7. Image Inference Call Chain

Image path:

1. User clicks "选择图片".
2. `on_open_img()` opens a PyQt file picker.
3. It stops any active video/camera worker with `on_stop_video()`.
4. It calls `get_model()`.
5. It runs:
   - `model.predict(path, device=INFER_DEVICE, imgsz=640, conf=0.3, iou=0.5, verbose=False)[0]`
6. It calls `res.plot()` to generate an annotated BGR result image.
7. It saves the annotated image in memory as `self.last_vis`.
8. It updates the preview and summary fields through `_show_vis()` and `_fill_info()`.

Returned/displayed summary:

- Detection count: `len(res.boxes)`
- Main class: highest-confidence box only
- Confidence: highest-confidence box only
- BBox: highest-confidence box only

The desktop UI does not currently expose all detections in a structured object.

## 8. Video and Camera Inference

Video:

- `on_open_vid()` opens a video path and starts `VideoWorker`.
- `VideoWorker` uses `cv2.VideoCapture(video_path)`.
- Every `step` frames, it calls `self.model.predict(frame, device=INFER_DEVICE, imgsz=self.imgsz, conf=self.conf, iou=self.iou, verbose=False)`.
- Default video settings in `app.py`: `imgsz=640`, `conf=0.3`, `iou=0.5`, `step=2`.

Camera:

- `on_open_cam()` starts `CameraWorker`.
- `CameraWorker` uses `cv2.VideoCapture(self.cam_index, cv2.CAP_DSHOW)`.
- `CAP_DSHOW` is Windows-specific.
- Default camera settings in `app.py`: `imgsz=640`, `conf=0.3`, `iou=0.5`, `step=1`, `cam_index=0`.

The current requested API migration should not implement video/camera APIs in the first phase.

## 9. Result Drawing and Saving

Drawing:

- Desktop app uses Ultralytics `res.plot()` to generate annotated BGR images.
- PyQt preview converts BGR to RGB QPixmap through `bgr_to_qpix()`.

Saving:

- `on_save()` writes `self.last_vis` with `cv2.imwrite(path, self.last_vis)`.
- The save path is chosen manually through a PyQt file picker.

Batch variant:

- `app_iter3_batch.py` writes batch result images into an output directory named like `batch_results_YYYYMMDD_HHMMSS`.

## 10. Class Names Source

Runtime class names come from Ultralytics result metadata:

- `res.names.get(cls_id, str(cls_id))`

This means category IDs and names are determined by the loaded model checkpoint/config. The migration must not reorder or remap class IDs manually.

Dataset YAML observations:

- `dataset/data.yaml` is only a sample with `nc: 1`, `names: ['ship']`, not the traffic-sign model class list.
- TT100K training args point to an external `<LOCAL_PATH>`.

## 11. Thresholds, Image Size, and Device

In `app.py`:

- Image `imgsz`: hard-coded `640`
- Image `conf`: hard-coded `0.3`
- Image `iou`: hard-coded `0.5`
- Video/camera default values are passed through worker constructor defaults.
- Device: `INFER_DEVICE = "0"`, meaning GPU index 0 in Ultralytics calls.

In `web_version/config.py`:

- `YOLO_IMGSZ`, `YOLO_CONF`, `YOLO_IOU`, `YOLO_DEVICE` can be read from environment variables.
- But `web_version` is Flask-based and separate from `app.py`.

The FastAPI migration should move these values to a unified config module and environment variables.

## 12. Current Environment Signals

Observed machine/GPU:

- GPU: NVIDIA GeForce RTX 4060 Ti
- GPU memory: 16380 MiB
- NVIDIA driver: 591.86
- NVIDIA-SMI CUDA display: 13.1

Observed Python/package signals:

- Direct Anaconda executable exists at `<LOCAL_PATH>`.
- `<LOCAL_PATH>` reported:
  - `PyQt5 5.15.10`
  - `Flask 3.0.3`
  - no installed `torch`, `torchvision`, `opencv-python`, `ultralytics`, `fastapi`, or `uvicorn` in that base environment.
- Importing local `ultralytics` with the base Anaconda Python failed because `cv2` was missing.
- Importing `torch` with the base Anaconda Python failed because `torch` was missing.

Conclusion:

- The currently audited base Python environment is not sufficient to run the YOLO desktop app or future FastAPI service.
- The user may be using another environment not visible through the probed `python` command. Before implementation/testing, confirm the actual interpreter selected by VS Code.

## 13. Existing Web Version

`web_version/web_app.py` is a Flask + SQLAlchemy web application.

Useful ideas:

- Multi-model dictionary
- Lazy model cache
- `models_lock` for concurrent model loading
- Upload/result folders
- SQLite detection history

Risks and reasons not to directly reuse it as the first FastAPI tool:

- It is Flask, not FastAPI.
- It uses hard-coded local model paths.
- `SECRET_KEY` has a hard-coded fallback.
- `MAX_CONTENT_LENGTH = None` in `web_app.py`, so file size is not limited there.
- It focuses on web UI/history, not a clean SF-FastGPT contract.
- It does not match the requested `/health` and `/api/v1/detect/image` FastAPI contract.

Recommendation: reuse concepts only, not the Flask app itself.

## 14. Existing Tests

The repository contains:

- Upstream Ultralytics tests in `tests/`.
- Local scripts:
  - `test_model_loading.py`
  - `test_ablation_classes.py`
  - `validate_ablation_models.py`
  - `test_yaml.py`
  - others

Current tests are not yet suitable for the requested FastAPI tool. They do not verify:

- `/health`
- image upload API
- API key authentication
- model singleton behavior in the API
- image quality review rules
- JSON error contract
- result image URL generation
- desktop regression after migration

Also note: `.gitignore` contains `tests/`, so test tracking status should be checked before committing future test files.

## 15. Reusable Code

Directly reusable:

- Model path/model ID constants from `app.py`, after moving to config.
- `YOLO(model_path)` loading pattern.
- `model.predict(...)[0]` inference pattern.
- `res.plot()` annotated result generation.
- `res.names`, `res.boxes.cls`, `res.boxes.conf`, `res.boxes.xyxy` result extraction.
- `cv2.imwrite()` result image saving.

Potentially reusable with care:

- `app_iter3_batch.py` helper ideas such as result conversion and batch output.
- `web_version` lazy model cache and lock concept.

Not recommended for direct reuse:

- Hard-coded absolute paths.
- PyQt UI methods as service-layer logic.
- Flask routes as the FastAPI target.
- Web version database/history features in the first API phase.

## 16. Current Technical Debt

- Model paths are hard-coded absolute Windows paths.
- Device is hard-coded as `"0"`.
- Inference parameters are scattered/hard-coded.
- Desktop UI and inference logic are tightly coupled.
- Image result conversion exists only inside UI event handlers.
- No stable shared result schema exists.
- No first-class API error model exists.
- Current active desktop only summarizes the highest-confidence detection, while API needs all detections.
- Camera code uses Windows-only `cv2.CAP_DSHOW`.
- `web_version` contains duplicated model/inference logic.
- Base Python environment lacks critical packages.
- Existing `.gitignore` excludes `tests/`, which may surprise future test additions.
- Generated results/uploads/weights are present in the workspace and must not leak into public commits.

## 17. Potential Risks

- The active default external weight path may not exist on other machines.
- The actual class list cannot be confirmed without successfully loading the active checkpoint.
- The current environment may not run the app because `torch`/`cv2` are missing in the probed Anaconda base environment.
- Dirty Git worktree can mix user changes with migration work.
- If the API independently loads a model while the desktop app also runs in another process, each process will load one model copy. This is acceptable but must be documented.
- If desktop and API are later run in the same process, a shared service/singleton should prevent repeated loads.
- `app.py` has no lock around model cache; API should add an inference/load lock for first-version stability.
- YOLO should return visual evidence only. Risk conclusions belong to SF-FastGPT/knowledge workflow.

## 18. User Confirmations Needed Before Implementation

1. Which checkpoint should the new API use by default?
   - Current desktop `<LOCAL_PATH>`
   - Repository TT100K weight `runs/train/TT100K-增强-yolo11-第一个实验-newt100k2/weights/best.pt`
   - Another explicit path
2. Which Python environment in VS Code currently runs the desktop app successfully?
3. Should `app.py` remain the active desktop entry, or should `app_iter3_batch.py` become the preferred desktop entry later?
4. Is the first API phase strictly image-only?
5. Should API result files go under a new isolated folder such as `outputs/api_results/`, or reuse `results/`?
6. What API key value should be used locally? The repo should only receive `.env.example`, not a real `.env`.
7. Should future tests be placed under a new trackable folder such as `api_tests/` if `tests/` remains ignored?

## 19. Audit Conclusion

The safest next implementation direction is:

- Keep `app.py` desktop behavior intact.
- Extract shared image inference into a small service module.
- Keep class IDs and names directly from the loaded model.
- Add a FastAPI image-detection service that calls the same shared service.
- Do not add database, Vue, video API, camera API, risk scoring, report generation, or SF-FastGPT platform configuration in the first phase.
- Do not claim YOLO26. The audited code and training artifacts indicate YOLO11/PSSM-YOLO work.
