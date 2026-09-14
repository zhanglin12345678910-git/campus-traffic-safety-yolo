# Document Conflicts and Resolution Rules

Audit date: 2026-07-07

Sources reviewed:

- `agent/校园交通安全智能巡检智能体设计方案书_最终完整版.docx`
- `agent/校园交通安全智能巡检智能体_ClaudeCode与SF-FastGPT开发指南.docx`
- `agent/TT100K公开数据集与YOLO26训练及校园应用验证方案.docx`
- User-provided migration prompt in the Codex attachment
- Current codebase, especially `app.py`, `web_version/`, and TT100K training args

Priority rule for conflicts:

1. Current working code and verified repository facts
2. User's latest migration requirements
3. The three Word reference documents
4. Default implementation preferences

## 1. Model Version Conflict

Conflict:

- Reference documents mention YOLO26, YOLO26m, and YOLO26l.
- Current repository and code evidence points to YOLO11-family work:
  - `app.py` exposes `YOLO11n` and `PSSM-YOLO-Lite-KD`.
  - Local Ultralytics version is `8.3.9`.
  - TT100K training args use `yolo11-CSP-PMSFA.yaml`.
  - Repository name includes `ultralytics-yolo11-main`.

Resolution:

- Do not claim YOLO26 in API docs, reports, or UI unless a verified YOLO26 weight/config is later introduced.
- Use factual wording such as "current Ultralytics YOLO/PSSM-YOLO-Lite-KD model" or "YOLO11-based experiment" where supported.
- Record model version as `unknown` in the API if checkpoint metadata cannot be read reliably.

## 2. Dataset Route Conflict

Conflict:

- The design方案书 includes a broad intelligent inspection system, and older project narratives mention campus data and broader scenario validation.
- The TT100K document and user prompt clarify the current route:
  - TT100K is the training/testing data source.
  - Campus images are for later real-scene validation only.
  - No new campus training dataset in this phase.

Resolution:

- The API phase must not retrain or alter datasets.
- Campus images may be used as manual demo/test samples, not training data.
- Any report should separate TT100K metrics from campus demo observations.

## 3. From-Scratch Project vs Existing Project Reuse

Conflict:

- `校园交通安全智能巡检智能体_ClaudeCode与SF-FastGPT开发指南.docx` recommends creating a new `campus-traffic-agent/` project.
- User's latest prompt explicitly says this is an existing project and must not be replaced or rebuilt from scratch.
- Current desktop app already exists and runs through `app.py`.

Resolution:

- Do not create an unrelated new project as the main implementation.
- Add minimal modules in the existing repository.
- Preserve the desktop entry and behavior.
- Only create new files needed for shared inference and FastAPI.

## 4. Desktop App vs Web/FastAPI Scope

Conflict:

- Design方案书 includes Web management pages, dashboards, reports, hidden-danger ledger, review workflow, and database.
- Current prompt says preserve desktop and add an API tool for SF-FastGPT; do not replace desktop.
- `web_version/` already exists as Flask web UI, but the requested interface is FastAPI.

Resolution:

- First implementation phase should be image detection API only.
- Do not build Vue, login, MySQL, dashboards, or report UI now.
- Do not replace desktop with `web_version/`.
- Treat `web_version/` as reference only.

## 5. API Path Conflict

Conflict:

- Developer guide gives example `POST /api/v1/detect`.
- User prompt requires `POST /api/v1/detect/image`.
- Design方案书 lists broader future endpoints:
  - `/api/v1/detect/image`
  - `/api/v1/detect/video`
  - `/api/v1/risk/evaluate`
  - `/api/v1/reports/generate`
  - `/api/v1/cases`

Resolution:

- First phase implements:
  - `GET /health`
  - `POST /api/v1/detect/image`
- Do not implement video/risk/report/case endpoints in the first phase.
- If compatibility is desired later, `/api/v1/detect` can become an alias, but it is not required now.

## 6. Visual Evidence vs Risk Conclusion Conflict

Conflict:

- Design方案书 describes risk scoring,整改建议,巡检报告,隐患台账.
- User prompt clearly limits YOLO/API responsibility:
  - YOLO only returns visual evidence.
  - Large model/SF-FastGPT handles knowledge retrieval, risk explanation,整改建议, report generation.
  - API must not fabricate risk conclusions.

Resolution:

- FastAPI must return detections, image quality, result image URL, model metadata, timing, and review flags.
- It must not return campus management risk conclusions.
- `review_required` and `review_reasons` are allowed as uncertainty/quality flags, not risk judgments.

## 7. Video and Camera Scope Conflict

Conflict:

- `app.py` supports video and camera detection.
- Design方案书 includes video and future camera/monitoring expansion.
- User prompt says first API phase should not develop video API, camera API, real-time monitoring, mobile app, or multi-agent collaboration.

Resolution:

- Preserve desktop video/camera features.
- Do not expose video/camera HTTP APIs in the first phase.
- Mention them as future work only.

## 8. Existing Web Version vs Requested FastAPI

Conflict:

- `web_version/web_app.py` is a Flask + SQLAlchemy app with upload/history behavior.
- User prompt requests FastAPI, JSON error handling, API key auth, and an SF-FastGPT contract.

Resolution:

- Do not mutate the Flask app into the requested API in the first pass.
- Implement a separate FastAPI entry while sharing the inference core.
- Use Flask app ideas only where helpful: model cache, model lock, upload/result folders.

## 9. Model Path and Weight Conflict

Conflict:

- Current desktop default points to an external `<LOCAL_PATH>` CCTSDB-style path.
- TT100K document says current model training data is mainly TT100K.
- Repository contains TT100K YOLO11 training output under `runs/train/TT100K-增强-yolo11-第一个实验-newt100k2`.

Resolution:

- Do not silently change the desktop model path.
- Before implementation, user must confirm the default API checkpoint.
- API config should support `YOLO_MODEL_PATH` so the chosen weight can be changed without code edits.

## 10. Target Metrics vs Real Results Conflict

Conflict:

- Design方案书 includes many target thresholds such as workflow completion rate, tool-call success rate, report success rate, and satisfaction.
- Those are recommended targets, not verified current results.

Resolution:

- Do not present target values as achieved test results.
- Only write actual executed test outcomes into `docs/TEST_REPORT.md` after implementation.
- For now, keep metrics as planned acceptance criteria.

## 11. Environment Conflict

Conflict:

- The repository has local Ultralytics source and PyQt5/Flask are installed in the probed base environment.
- The same base environment lacks `torch`, `cv2`, `ultralytics` package installation, `fastapi`, and `uvicorn`.
- Current desktop app likely depends on another VS Code/interpreter environment or needs dependencies installed.

Resolution:

- Do not assume current base Anaconda environment is the working app environment.
- Before running regression or API tests, confirm VS Code interpreter and dependency installation.
- Document all commands actually run; do not fabricate passing tests.

## 12. Security and Git Conflict

Conflict:

- Current `.gitignore` excludes weights, runs, `.env`, uploads, results, and many generated files.
- There are many generated outputs and weights in the working tree.
- The user prompt requires not committing weights, passwords, API keys, or sensitive paths to public repositories.

Resolution:

- Add `.env.example`, not `.env`.
- API responses should return only weight filenames, not full local paths.
- Logs should avoid API keys and full sensitive paths where possible.
- Future Git commit must be reviewed carefully because the worktree is dirty and has untracked files.

## 13. MVP vs Long-Term System Conflict

Conflict:

- Design方案书 describes the full target product:
  - knowledge base
  - workflows
  - reports
  - ledger
  - review/rectification
  - Web pages
  - database
  - deployment
- User prompt defines the current target:
  - safely expose current traffic-sign detection as an HTTP tool callable by SF-FastGPT.

Resolution:

- First-phase MVP is only the visual detection tool API plus docs/tests.
- SF-FastGPT knowledge-base configuration and report generation remain external/manual for now.
- Long-term items should be listed in docs as next phases, not implemented now.

## 14. Final Conflict Summary

The implementation should follow this single rule:

Build a minimal FastAPI wrapper around the existing verified YOLO detection capability, while preserving the PyQt5 desktop app and avoiding unverified claims.

Anything beyond visual evidence, image quality checks, API auth, stable error handling, and result-image generation belongs to a later phase.
