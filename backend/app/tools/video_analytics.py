from __future__ import annotations

import math
import threading
import time
import uuid
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

import cv2

from app.config import Settings
from app.tools.yolo import TrafficSignDetectionTool, YOLOToolError


class VideoAnalyticsError(RuntimeError):
    pass


class VideoAnalyticsTool:
    """People/vehicle tracking with crowd and directional event rules."""

    DIRECTIONS = {
        "left_to_right": ((1.0, 0.0), "从左向右"),
        "right_to_left": ((-1.0, 0.0), "从右向左"),
        "top_to_bottom": ((0.0, 1.0), "从上向下"),
        "bottom_to_top": ((0.0, -1.0), "从下向上"),
    }
    VEHICLE_NAMES = {"bicycle", "car", "motorcycle", "bus", "truck"}

    def __init__(self, settings: Settings, yolo_tool: TrafficSignDetectionTool):
        self.settings = settings
        self.yolo_tool = yolo_tool
        self._lock = threading.Lock()
        self._model: Any | None = None
        self.load_count = 0

    @property
    def model_loaded(self) -> bool:
        return self._model is not None

    def analyze(self, video_path: str | Path, allowed_direction: str) -> dict[str, Any]:
        path = Path(video_path)
        if allowed_direction not in self.DIRECTIONS:
            raise VideoAnalyticsError("不支持的允许通行方向")
        if not path.exists():
            raise VideoAnalyticsError("待分析视频不存在")

        if not self._lock.acquire(blocking=False):
            raise VideoAnalyticsError("已有视频正在分析，请等待当前任务完成后再提交")
        try:
            return self._analyze_locked(self._tracking_model(), path, allowed_direction)
        finally:
            self._lock.release()

    def _tracking_model(self) -> Any:
        """Return the video-only model instance; the caller must hold ``self._lock``.

        Sharing the image-inference singleton is unsafe: ``model.track()`` leaves
        ByteTrack callbacks registered on the model, so later image predictions
        would pass through a stale tracker, and this path does not take the image
        tool's predict lock.
        """
        if self._model is None:
            try:
                self._model = self.yolo_tool.create_general_model()
            except YOLOToolError as exc:
                raise VideoAnalyticsError(str(exc)) from exc
            self.load_count += 1
        return self._model

    def _analyze_locked(self, model: Any, path: Path, allowed_direction: str) -> dict[str, Any]:
        capture = cv2.VideoCapture(str(path))
        if not capture.isOpened():
            raise VideoAnalyticsError("视频内容无法解码")

        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = float(capture.get(cv2.CAP_PROP_FPS) or 25.0)
        source_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        if width <= 0 or height <= 0:
            capture.release()
            raise VideoAnalyticsError("无法读取视频分辨率")

        analysis_width, analysis_height = self._analysis_dimensions(
            width,
            height,
            self.settings.video_max_dimension,
        )
        frame_stride = self._effective_frame_stride(fps)

        output_dir = self.settings.output_dir / "video-analytics"
        output_dir.mkdir(parents=True, exist_ok=True)
        # VP8/WebM is supported by Chromium and Firefox. OpenCV's common
        # mp4v writer produces files that many browsers cannot decode.
        output_name = f"{path.stem}-{uuid.uuid4().hex[:12]}.webm"
        output_path = output_dir / output_name
        output_fps = max(1.0, fps / frame_stride)
        writer = cv2.VideoWriter(
            str(output_path),
            cv2.VideoWriter_fourcc(*"VP80"),
            output_fps,
            (analysis_width, analysis_height),
        )
        if not writer.isOpened():
            capture.release()
            raise VideoAnalyticsError("检测结果视频编码器初始化失败")

        names = getattr(model, "names", {})
        allowed_ids = [
            int(class_id)
            for class_id, name in (names.items() if isinstance(names, dict) else enumerate(names))
            if str(name).lower() in self.settings.general_object_class_names
        ]
        self._reset_trackers(model)

        history: dict[int, deque[tuple[float, float]]] = defaultdict(
            lambda: deque(maxlen=max(30, self.settings.wrong_way_min_track_points * 2))
        )
        unique_people: set[int] = set()
        unique_vehicles: set[int] = set()
        wrong_way_tracks: dict[int, dict[str, Any]] = {}
        max_people = 0
        max_vehicles = 0
        frame_index = 0
        processed_frames = 0
        started = time.perf_counter()
        diagonal = math.hypot(analysis_width, analysis_height)

        try:
            while processed_frames < self.settings.video_max_frames:
                ok, frame = capture.read()
                if not ok:
                    break
                frame_index += 1
                if (frame_index - 1) % frame_stride:
                    continue
                if (analysis_width, analysis_height) != (width, height):
                    frame = cv2.resize(frame, (analysis_width, analysis_height), interpolation=cv2.INTER_AREA)

                try:
                    results = model.track(
                        frame,
                        persist=True,
                        tracker="bytetrack.yaml",
                        classes=allowed_ids,
                        conf=self.settings.general_yolo_default_conf,
                        iou=self.settings.yolo_default_iou,
                        imgsz=self.settings.yolo_default_imgsz,
                        device=self.settings.yolo_device,
                        verbose=False,
                    )
                except Exception as exc:
                    raise VideoAnalyticsError(f"视频跟踪失败：{exc}") from exc
                if not results:
                    writer.write(frame)
                    processed_frames += 1
                    continue

                result = results[0]
                boxes = getattr(result, "boxes", None)
                people_in_frame = 0
                vehicles_in_frame = 0
                if boxes is not None and getattr(boxes, "id", None) is not None:
                    coords = self._tolist(boxes.xyxy)
                    classes = self._tolist(boxes.cls)
                    confidences = self._tolist(boxes.conf)
                    track_ids = self._tolist(boxes.id)
                    result_names = getattr(result, "names", names)
                    for xyxy, class_value, confidence, track_value in zip(coords, classes, confidences, track_ids):
                        class_id = int(class_value)
                        track_id = int(track_value)
                        class_name = self._class_name(result_names, class_id).lower()
                        if class_name == "person":
                            people_in_frame += 1
                            unique_people.add(track_id)
                        elif class_name in self.VEHICLE_NAMES:
                            vehicles_in_frame += 1
                            unique_vehicles.add(track_id)
                        else:
                            continue
                        x1, y1, x2, y2 = (float(value) for value in xyxy)
                        center = ((x1 + x2) / 2, (y1 + y2) / 2)
                        history[track_id].append(center)
                        if track_id not in wrong_way_tracks and self._is_wrong_way(
                            history[track_id], allowed_direction, diagonal
                        ):
                            wrong_way_tracks[track_id] = {
                                "event_type": "wrong_way",
                                "label": "逆行事件",
                                "severity": "high",
                                "status": "confirmed_by_track",
                                "track_id": track_id,
                                "class_name": class_name,
                                "confidence": round(float(confidence), 6),
                                "frame_index": frame_index,
                                "allowed_direction": allowed_direction,
                                "allowed_direction_label": self.DIRECTIONS[allowed_direction][1],
                                "requires_manual_review": True,
                                "evidence": (
                                    f"目标 #{track_id} 的连续轨迹与允许方向"
                                    f"{self.DIRECTIONS[allowed_direction][1]}相反"
                                ),
                            }

                max_people = max(max_people, people_in_frame)
                max_vehicles = max(max_vehicles, vehicles_in_frame)
                annotated = result.plot()
                if people_in_frame >= self.settings.crowd_min_persons:
                    cv2.putText(
                        annotated,
                        f"CROWD CANDIDATE: {people_in_frame}",
                        (18, 36),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.9,
                        (0, 165, 255),
                        2,
                        cv2.LINE_AA,
                    )
                if wrong_way_tracks:
                    cv2.putText(
                        annotated,
                        f"WRONG WAY TRACKS: {len(wrong_way_tracks)}",
                        (18, 72),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.9,
                        (40, 40, 255),
                        2,
                        cv2.LINE_AA,
                    )
                writer.write(annotated)
                processed_frames += 1
        except Exception:
            capture.release()
            writer.release()
            output_path.unlink(missing_ok=True)
            raise
        finally:
            capture.release()
            writer.release()

        if processed_frames == 0:
            output_path.unlink(missing_ok=True)
            raise VideoAnalyticsError("视频没有可分析的有效帧")

        events: list[dict[str, Any]] = []
        if max_people >= self.settings.crowd_min_persons:
            events.append(
                {
                    "event_type": "personnel_gathering",
                    "label": "人员聚集",
                    "severity": "high" if max_people >= self.settings.crowd_min_persons * 2 else "medium",
                    "status": "confirmed_by_video",
                    "object_count": max_people,
                    "threshold": self.settings.crowd_min_persons,
                    "requires_manual_review": True,
                    "evidence": f"视频单帧最大检测到 {max_people} 人，达到阈值 {self.settings.crowd_min_persons} 人",
                }
            )
        events.extend(wrong_way_tracks.values())

        return {
            "success": True,
            "analysis_type": "video_tracking",
            "model_name": self.settings.general_yolo_model_path.name,
            "tracker": "ByteTrack",
            "allowed_direction": allowed_direction,
            "allowed_direction_label": self.DIRECTIONS[allowed_direction][1],
            "source_frames": source_frames,
            "source_width": width,
            "source_height": height,
            "analysis_width": analysis_width,
            "analysis_height": analysis_height,
            "processed_frames": processed_frames,
            "frame_stride": frame_stride,
            "configured_frame_stride": self.settings.video_frame_stride,
            "target_analysis_fps": self.settings.video_target_fps,
            "max_people_in_frame": max_people,
            "max_vehicles_in_frame": max_vehicles,
            "unique_people_tracks": len(unique_people),
            "unique_vehicle_tracks": len(unique_vehicles),
            "wrong_way_count": len(wrong_way_tracks),
            "events": events,
            "result_video_path": str(output_path),
            "result_video_url": f"/outputs/video-analytics/{output_name}",
            "duration_ms": round((time.perf_counter() - started) * 1000, 2),
            "limited_by_max_frames": processed_frames >= self.settings.video_max_frames,
        }

    def _effective_frame_stride(self, source_fps: float) -> int:
        """Keep high-frame-rate uploads bounded without thinning normal video."""
        target_stride = max(1, round(source_fps / self.settings.video_target_fps))
        return max(self.settings.video_frame_stride, target_stride)

    def _is_wrong_way(
        self,
        points: deque[tuple[float, float]],
        allowed_direction: str,
        diagonal: float,
    ) -> bool:
        if len(points) < self.settings.wrong_way_min_track_points:
            return False
        start_x, start_y = points[0]
        end_x, end_y = points[-1]
        dx, dy = end_x - start_x, end_y - start_y
        displacement = math.hypot(dx, dy)
        if displacement < diagonal * self.settings.wrong_way_min_displacement_ratio:
            return False
        allowed_vector = self.DIRECTIONS[allowed_direction][0]
        dot = (dx * allowed_vector[0] + dy * allowed_vector[1]) / displacement
        return dot < -0.7

    @staticmethod
    def _analysis_dimensions(width: int, height: int, max_dimension: int) -> tuple[int, int]:
        """Return even output dimensions bounded by ``max_dimension``."""
        longest = max(width, height)
        if longest <= max_dimension:
            return width, height
        scale = max_dimension / longest
        resized_width = max(2, int(round(width * scale / 2)) * 2)
        resized_height = max(2, int(round(height * scale / 2)) * 2)
        return resized_width, resized_height

    @staticmethod
    def _reset_trackers(model: Any) -> None:
        predictor = getattr(model, "predictor", None)
        for tracker in getattr(predictor, "trackers", []) or []:
            reset = getattr(tracker, "reset", None)
            if callable(reset):
                reset()

    @staticmethod
    def _tolist(value: Any) -> list[Any]:
        if hasattr(value, "cpu"):
            value = value.cpu()
        if hasattr(value, "tolist"):
            return value.tolist()
        return list(value)

    @staticmethod
    def _class_name(names: Any, class_id: int) -> str:
        if isinstance(names, dict):
            return str(names.get(class_id, class_id))
        if isinstance(names, (list, tuple)) and 0 <= class_id < len(names):
            return str(names[class_id])
        return str(class_id)
