"""图片上云前的隐私处理：人脸模糊 + 长边归一 + JPEG 重编码。

设计边界（诚实记录，见 docs/VLM_INTEGRATION_PROPOSAL.md 评审第 7 节 V-2）：
- 人脸模糊使用 OpenCV haar 级联（无新模型依赖），对侧脸/遮挡人脸可能漏检，
  属「尽力而为」；**真正可靠的防线是检测侧的人员闸门**：
  凡 YOLO 检出 person 的图片一律不上送（见 graph.evaluate_risk）。
- 车牌不模糊：车牌检测在无专用模型时误漏率高，且违停研判需要看清车辆与
  标线的空间关系；车牌出境属已记录的残余风险（当前供应商与文字研判为同一家）。

失败策略：解码或编码失败抛异常，由调用方降级为纯文本研判（不允许不打码直接上送）。
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

_FACE_CASCADE_PATH = str(Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml")


def mask_and_resize(image_path: str | Path, max_side: int = 1024, jpeg_quality: int = 85) -> bytes:
    """读取图片，模糊人脸区域，等比缩放到长边 max_side，返回 JPEG 字节。"""
    raw = np.fromfile(str(image_path), dtype=np.uint8)
    img = cv2.imdecode(raw, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError(f"无法解码图片：{image_path}")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    cascade = cv2.CascadeClassifier(_FACE_CASCADE_PATH)
    faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(24, 24))
    for x, y, w, h in faces:
        # 适当外扩，避免只糊住五官中心
        pad_x, pad_y = int(w * 0.15), int(h * 0.2)
        x0, y0 = max(0, x - pad_x), max(0, y - pad_y)
        x1, y1 = min(img.shape[1], x + w + pad_x), min(img.shape[0], y + h + pad_y)
        roi = img[y0:y1, x0:x1]
        img[y0:y1, x0:x1] = cv2.GaussianBlur(roi, (51, 51), 30)

    height, width = img.shape[:2]
    scale = min(1.0, max_side / max(height, width))
    if scale < 1.0:
        img = cv2.resize(img, (round(width * scale), round(height * scale)), interpolation=cv2.INTER_AREA)

    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, jpeg_quality])
    if not ok:
        raise ValueError("JPEG 编码失败")
    return buf.tobytes()
