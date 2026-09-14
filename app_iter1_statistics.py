import sys, time, os, csv, cv2, numpy as np
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton, QFileDialog,
    QGridLayout, QVBoxLayout, QHBoxLayout, QProgressBar, QMessageBox, QSizePolicy
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QPixmap, QImage
from ultralytics import YOLO
from PyQt5.QtWidgets import QFrame, QComboBox

# ==================== 多模型配置 ====================
MODEL_PATH = r"<LOCAL_PATH>"

MODELS = {
    "PSSM-YOLO-Lite-KD": MODEL_PATH,
    "YOLO11n": r"<LOCAL_PATH>",
    "YOLOv10n":r"<LOCAL_PATH>",
    "YOLOv8n": r"<LOCAL_PATH>",
    "YOLOv7-tiny": r"<LOCAL_PATH>",
    "YOLOv10s": r"<LOCAL_PATH>",
    "RT-DETR": r"<LOCAL_PATH>",
}

MODEL_DISPLAY_NAMES = {
    'PSSM-YOLO-Lite-KD': '🏆 PSSM-YOLO-Lite-KD (自研最终)',
    'YOLO11n': '⚡ YOLO11n (超轻量)',
    'YOLOv10n': '🎯 YOLOv10n (实时检测)',
    'YOLOv8n': '💎 YOLOv8n (经典)',
    'YOLOv7-tiny': '⚙️ YOLOv7-tiny (紧凑)',
    'YOLOv10s': '🚀 YOLOv10s (小型)',
    'RT-DETR': '🎪 RT-DETR (实时检测器)'
}

# 选中后显示的简短名称（不含括号内容）
MODEL_SHORT_NAMES = {
    'PSSM-YOLO-Lite-KD': '🏆 PSSM-YOLO-Lite-KD',
    'YOLO11n': '⚡ YOLO11n',
    'YOLOv10n': '🎯 YOLOv10n',
    'YOLOv8n': '💎 YOLOv8n',
    'YOLOv7-tiny': '⚙️ YOLOv7-tiny',
    'YOLOv10s': '🚀 YOLOv10s',
    'RT-DETR': '🎪 RT-DETR'
}

DEFAULT_MODEL_ID = "PSSM-YOLO-Lite-KD"

# 推理设备："0" 表示使用第 1 块 GPU；如需切回 CPU，改成 "cpu" 即可。
INFER_DEVICE = "0"

def bgr_to_qpix(bgr: np.ndarray) -> QPixmap:
    if bgr is None: return QPixmap()
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    h, w, ch = rgb.shape
    qimg = QImage(rgb.data, w, h, ch*w, QImage.Format_RGB888)
    return QPixmap.fromImage(qimg)


def _name_from_names(names, cls_id):
    """兼容 Ultralytics 的 dict/list 两种类别名称结构。"""
    if isinstance(names, dict):
        return names.get(cls_id, str(cls_id))
    if isinstance(names, (list, tuple)) and 0 <= cls_id < len(names):
        return names[cls_id]
    return str(cls_id)


def result_to_info(res):
    """从单帧检测结果中提取界面显示和统计所需信息。"""
    info = {
        "count": 0,
        "main": "-",
        "conf": 0.0,
        "xyxy": ("-", "-", "-", "-"),
        "detections": []
    }
    boxes = getattr(res, "boxes", None)
    if boxes is None or len(boxes) == 0:
        return info

    confs = boxes.conf.cpu().numpy()
    classes = boxes.cls.cpu().numpy().astype(int)
    xyxys = boxes.xyxy.cpu().numpy().astype(int)
    names = getattr(res, "names", {})
    info["count"] = len(boxes)

    best_idx = int(np.argmax(confs))
    info["main"] = _name_from_names(names, int(classes[best_idx]))
    info["conf"] = float(confs[best_idx])
    info["xyxy"] = tuple(int(v) for v in xyxys[best_idx])

    for cls_id, conf, xyxy in zip(classes, confs, xyxys):
        x1, y1, x2, y2 = (int(v) for v in xyxy)
        info["detections"].append({
            "class_name": _name_from_names(names, int(cls_id)),
            "confidence": float(conf),
            "x1": x1,
            "y1": y1,
            "x2": x2,
            "y2": y2
        })
    return info


class DetectionStats:
    """集中管理图片、视频和摄像头检测过程中的统计分析数据。"""

    def __init__(self):
        self.reset()

    def reset(self):
        self.model_name = "-"
        self.source_type = "-"
        self.source_name = "-"
        self.total_frames = 0
        self.detection_frames = 0
        self.total_objects = 0
        self.class_counts = {}
        self.conf_sum = 0.0
        self.conf_count = 0
        self.max_confidence = 0.0
        self.inference_sum_ms = 0.0
        self.inference_count = 0
        self.current_frame_objects = 0
        self.records = []

    def update_from_result(self, res, used_ms, model_name, source_type, frame_index=None, source_name=""):
        self.model_name = model_name or self.model_name
        self.source_type = source_type or self.source_type
        self.source_name = source_name or self.source_name
        self.total_frames += 1
        self.inference_sum_ms += float(used_ms)
        self.inference_count += 1

        frame_no = int(frame_index) if frame_index is not None else self.total_frames
        image_name = os.path.basename(self.source_name) if self.source_name else "-"
        info = result_to_info(res)
        detections = info["detections"]
        self.current_frame_objects = len(detections)

        if detections:
            self.detection_frames += 1
            self.total_objects += len(detections)

        for det in detections:
            cls_name = det["class_name"]
            conf = float(det["confidence"])
            self.class_counts[cls_name] = self.class_counts.get(cls_name, 0) + 1
            self.conf_sum += conf
            self.conf_count += 1
            self.max_confidence = max(self.max_confidence, conf)
            self.records.append({
                "frame_index": frame_no,
                "image_name": image_name,
                "source_name": self.source_name or image_name,
                "model_name": self.model_name,
                "class_name": cls_name,
                "confidence": conf,
                "x1": det["x1"],
                "y1": det["y1"],
                "x2": det["x2"],
                "y2": det["y2"],
                "inference_ms": float(used_ms)
            })

    def get_summary(self):
        avg_ms = self.inference_sum_ms / self.inference_count if self.inference_count else 0.0
        avg_fps = 1000.0 / avg_ms if avg_ms > 0 else 0.0
        avg_conf = self.conf_sum / self.conf_count if self.conf_count else 0.0
        items = sorted(self.class_counts.items(), key=lambda item: item[1], reverse=True)
        top_items = items[:5]
        class_summary = "\n".join(f"{name}: {count}" for name, count in top_items) if top_items else "暂无目标"
        if len(items) > 5:
            class_summary += "\n更多类别见导出报告"
        return {
            "model_name": self.model_name,
            "source_type": self.source_type,
            "total_frames": self.total_frames,
            "detection_frames": self.detection_frames,
            "total_objects": self.total_objects,
            "current_frame_objects": self.current_frame_objects,
            "avg_confidence": avg_conf,
            "max_confidence": self.max_confidence,
            "avg_inference_ms": avg_ms,
            "avg_fps": avg_fps,
            "class_summary": class_summary
        }

    def export_csv(self, path):
        summary = self.get_summary()
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["overall_statistics"])
            writer.writerow([
                "model_name", "source_type", "total_frames", "detection_frames",
                "total_objects", "avg_confidence", "max_confidence",
                "avg_inference_ms", "avg_fps"
            ])
            writer.writerow([
                summary["model_name"], summary["source_type"], summary["total_frames"],
                summary["detection_frames"], summary["total_objects"],
                f"{summary['avg_confidence']:.6f}", f"{summary['max_confidence']:.6f}",
                f"{summary['avg_inference_ms']:.3f}", f"{summary['avg_fps']:.3f}"
            ])
            writer.writerow([])
            writer.writerow(["object_details"])
            writer.writerow([
                "frame_index", "image_name", "source_name", "model_name", "class_name",
                "confidence", "x1", "y1", "x2", "y2", "inference_ms"
            ])
            for record in self.records:
                writer.writerow([
                    record["frame_index"], record["image_name"], record["source_name"],
                    record["model_name"], record["class_name"], f"{record['confidence']:.6f}",
                    record["x1"], record["y1"], record["x2"], record["y2"],
                    f"{record['inference_ms']:.3f}"
                ])

class VideoWorker(QThread):
    frame_ready = pyqtSignal(np.ndarray, float, dict, object)   # vis, used_ms, info, raw result
    finished = pyqtSignal()

    def __init__(self, model: YOLO, video_path: str, imgsz=640, conf=0.3, iou=0.5, step=2):
        super().__init__()
        self.model = model
        self.video_path = video_path
        self.imgsz = imgsz
        self.conf = conf
        self.iou = iou
        self.step = step
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        cap = cv2.VideoCapture(self.video_path)
        i = 0
        processed = 0
        while not self._stop:
            ok, frame = cap.read()
            if not ok:
                break
            if i % self.step != 0:   # 抽帧提速（CPU 推荐 step=2或3）
                i += 1
                continue
            i += 1
            t0 = time.time()
            results = self.model.predict(
                frame, device=INFER_DEVICE, imgsz=self.imgsz, conf=self.conf, iou=self.iou, verbose=False
            )
            used = (time.time() - t0) * 1000
            res = results[0]
            vis = res.plot()  # 带框BGR
            processed += 1

            info = result_to_info(res)
            info.update({"frame_index": processed, "source_name": self.video_path})
            self.frame_ready.emit(vis, used, info, res)

        cap.release()
        self.finished.emit()
class CameraWorker(QThread):
    frame_ready = pyqtSignal(np.ndarray, float, dict, object)
    finished = pyqtSignal()

    def __init__(self, model: YOLO, cam_index=0, imgsz=640, conf=0.3, iou=0.5, step=1):
        super().__init__()
        self.model = model
        self.cam_index = cam_index
        self.imgsz = imgsz
        self.conf = conf
        self.iou = iou
        self.step = step
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        cap = cv2.VideoCapture(self.cam_index, cv2.CAP_DSHOW)  # 0是默认摄像头
        i = 0
        processed = 0
        while not self._stop:
            ok, frame = cap.read()
            if not ok:
                break
            if i % self.step != 0:
                i += 1
                continue
            i += 1

            t0 = time.time()
            results = self.model.predict(frame, device=INFER_DEVICE, imgsz=self.imgsz,
                                         conf=self.conf, iou=self.iou, verbose=False)
            used = (time.time() - t0) * 1000
            res = results[0]
            vis = res.plot()
            processed += 1

            info = result_to_info(res)
            info.update({"frame_index": processed, "source_name": f"camera_{self.cam_index}"})
            self.frame_ready.emit(vis, used, info, res)

        cap.release()
        self.finished.emit()


class Main(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🚦 交通标志检测系统")
        self.resize(1400, 850)
        self.setMinimumSize(1200, 700)

        # ===== 中心 UI =====
        root = QWidget(); self.setCentralWidget(root)
        main = QHBoxLayout(root)
        main.setContentsMargins(20, 20, 20, 20)
        main.setSpacing(24)

        # 左：预览区域 - 直接占据整个左侧
        left = QVBoxLayout()
        left.setSpacing(16)
        
        # 预览区域直接作为主要显示区域
        self.lblPreview = QLabel("📸 点击按钮开始检测")
        self.lblPreview.setObjectName("mainPreview")
        self.lblPreview.setAlignment(Qt.AlignCenter)
        self.lblPreview.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.lblPreview.setScaledContents(True)
        self.lblPreview.setMinimumHeight(500)
        
        left.addWidget(self.lblPreview, 1)

        # 下方操作按钮区域
        btnContainer = QFrame()
        btnContainer.setObjectName("btnContainer")
        btnContainer.setStyleSheet("""
            #btnContainer {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                           stop:0 rgba(30, 41, 59, 0.95), 
                           stop:1 rgba(15, 23, 42, 0.95));
                border: 2px solid rgba(59, 130, 246, 0.3);
                border-radius: 16px;
            }
        """)
        # 使用网格布局
        from PyQt5.QtWidgets import QGridLayout
        btnGridLayout = QGridLayout(btnContainer)
        btnGridLayout.setContentsMargins(16, 16, 16, 16)
        btnGridLayout.setSpacing(10)
        
        # 创建按钮 - 简洁设计
        self.btnCamera = QPushButton("📹 摄像头")
        self.btnOpenImg = QPushButton("📷 选择图片")
        self.btnOpenVid = QPushButton("🎬 选择视频")
        self.btnSave = QPushButton("💾 保存结果")
        self.btnStop = QPushButton("⏹️ 停止")
        self.btnClear = QPushButton("🧹 清除显示")
        
        # 设置按钮样式
        self.btnCamera.setObjectName("btnPrimary")
        self.btnOpenImg.setObjectName("btnPrimary")
        self.btnOpenVid.setObjectName("btnPrimary")
        self.btnSave.setObjectName("btnSuccess")
        self.btnStop.setObjectName("btnDanger")
        self.btnClear.setObjectName("btnSecondary")
        
        # 设置按钮高度
        BUTTON_HEIGHT = 56
        for btn in [self.btnCamera, self.btnOpenImg, self.btnOpenVid, self.btnSave, self.btnStop, self.btnClear]:
            btn.setFixedHeight(BUTTON_HEIGHT)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            btn.setCursor(Qt.PointingHandCursor)
        
        # 2行3列网格布局
        btnGridLayout.addWidget(self.btnCamera, 0, 0)
        btnGridLayout.addWidget(self.btnOpenImg, 0, 1)
        btnGridLayout.addWidget(self.btnOpenVid, 0, 2)
        btnGridLayout.addWidget(self.btnSave, 1, 0)
        btnGridLayout.addWidget(self.btnStop, 1, 1)
        btnGridLayout.addWidget(self.btnClear, 1, 2)
        
        # 设置列拉伸
        btnGridLayout.setColumnStretch(0, 1)
        btnGridLayout.setColumnStretch(1, 1)
        btnGridLayout.setColumnStretch(2, 1)
        
        btnContainer.setFixedHeight(150)
        
        left.addWidget(btnContainer)

        # 右：信息面板
        def lab(txt):
            l = QLabel(txt)
            l.setObjectName("infoLabel")
            l.setMinimumWidth(80)
            return l
        def val():
            l = QLabel("")
            l.setObjectName("valueLabel")
            l.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            return l

        rwrap = QFrame()
        rwrap.setObjectName("card")
        rbox = QVBoxLayout(rwrap)
        rbox.setContentsMargins(24, 24, 24, 24)
        rbox.setSpacing(20)
        
        # 信息面板标题
        infoTitle = QLabel("📊 检测信息")
        infoTitle.setStyleSheet("""
            color: #ffffff;
            font-size: 17px;
            font-weight: 700;
            font-family: 'Microsoft YaHei UI', 'Segoe UI', Arial, sans-serif;
            padding: 10px 0px;
            border-bottom: 2px solid rgba(59, 130, 246, 0.5);
            margin-bottom: 15px;
        """)
        rbox.addWidget(infoTitle)
        
        # 模型选择区域
        modelFrame = QFrame()
        modelFrame.setStyleSheet("""
            background: rgba(16, 185, 129, 0.08);
            border: 2px solid rgba(16, 185, 129, 0.3);
            border-radius: 10px;
            padding: 12px;
        """)
        modelLayout = QVBoxLayout(modelFrame)
        modelLayout.setSpacing(8)
        
        modelLabel = QLabel("🎯 选择检测模型")
        modelLabel.setStyleSheet("""
            color: #10b981;
            font-size: 14px;
            font-weight: 600;
            margin-bottom: 5px;
        """)
        modelLayout.addWidget(modelLabel)
        
        self.cmbModel = QComboBox()
        # 使用简短名称显示，存储model_id
        for model_id in MODELS.keys():
            self.cmbModel.addItem(MODEL_SHORT_NAMES[model_id], model_id)
        self.cmbModel.setCurrentIndex(0)  # 默认选中第一个
        self.cmbModel.currentIndexChanged.connect(self.on_model_changed)
        self.cmbModel.setStyleSheet("""
            QComboBox {
                background: rgba(30, 41, 59, 0.9);
                color: #ffffff;
                border: 2px solid rgba(16, 185, 129, 0.4);
                border-radius: 8px;
                padding: 8px 35px 8px 12px;
                font-size: 13px;
                font-weight: 500;
                min-height: 30px;
            }
            QComboBox:hover {
                border-color: rgba(16, 185, 129, 0.7);
                background: rgba(30, 41, 59, 1.0);
            }
            QComboBox QAbstractItemView {
                background: #1e293b;
                color: #ffffff;
                border: 2px solid rgba(16, 185, 129, 0.5);
                selection-background-color: rgba(16, 185, 129, 0.3);
                padding: 4px;
                outline: none;
            }
            QComboBox QAbstractItemView::item {
                padding: 6px 10px;
                min-height: 25px;
            }
            QComboBox QAbstractItemView::item:hover {
                background: rgba(16, 185, 129, 0.2);
            }
        """)
        modelLayout.addWidget(self.cmbModel)
        
        rbox.addWidget(modelFrame)
        
        # 主要信息区域
        mainInfoFrame = QFrame()
        mainInfoFrame.setStyleSheet("""
            background: rgba(59, 130, 246, 0.05);
            border: 1px solid rgba(59, 130, 246, 0.2);
            border-radius: 8px;
            padding: 12px;
        """)
        mainInfoLayout = QGridLayout(mainInfoFrame)
        mainInfoLayout.setVerticalSpacing(10)
        mainInfoLayout.setHorizontalSpacing(12)
        mainInfoLayout.setContentsMargins(8, 8, 8, 8)

        mainInfoLayout.addWidget(lab("⏱️ 用时"), 0, 0)
        self.vTime = val()
        mainInfoLayout.addWidget(self.vTime, 0, 1)
        
        mainInfoLayout.addWidget(lab("🎯 目标数"), 1, 0)
        self.vCount = val()
        mainInfoLayout.addWidget(self.vCount, 1, 1)
        
        mainInfoLayout.addWidget(lab("🏷️ 主类别"), 2, 0)
        self.vMain = val()
        mainInfoLayout.addWidget(self.vMain, 2, 1)
        
        # 置信度进度条
        mainInfoLayout.addWidget(lab("📈 置信度"), 3, 0)
        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setMinimumHeight(20)
        mainInfoLayout.addWidget(self.bar, 3, 1)
        
        # 设置列宽比例
        mainInfoLayout.setColumnStretch(0, 0)
        mainInfoLayout.setColumnStretch(1, 1)
        
        rbox.addWidget(mainInfoFrame)
        
        # 坐标信息区域
        coordInfoFrame = QFrame()
        coordInfoFrame.setStyleSheet("""
            background: rgba(16, 185, 129, 0.05);
            border: 1px solid rgba(16, 185, 129, 0.2);
            border-radius: 8px;
            padding: 12px;
        """)
        coordInfoBox = QVBoxLayout(coordInfoFrame)
        coordInfoBox.setSpacing(10)
        coordInfoBox.setContentsMargins(8, 8, 8, 8)
        
        coordTitle = QLabel("📐 边界框坐标")
        coordTitle.setStyleSheet("""
            color: #10b981;
            font-size: 14px;
            font-weight: 600;
            padding-bottom: 6px;
            border-bottom: 1px solid rgba(16, 185, 129, 0.3);
        """)
        coordInfoBox.addWidget(coordTitle)
        
        # 坐标网格
        coordGrid = QGridLayout()
        coordGrid.setVerticalSpacing(6)
        coordGrid.setHorizontalSpacing(10)
        coordGrid.setContentsMargins(0, 6, 0, 0)
        
        # 创建坐标标签的辅助函数
        def coordLab(txt):
            l = QLabel(txt)
            l.setStyleSheet("""
                color: #94a3b8;
                font-size: 13px;
                font-weight: 500;
                padding: 4px 0;
            """)
            l.setMinimumWidth(30)
            return l
        
        def coordVal():
            l = QLabel("")
            l.setStyleSheet("""
                color: #ffffff;
                font-size: 13px;
                font-weight: 600;
                padding: 4px 8px;
                background: rgba(16, 185, 129, 0.15);
                border-radius: 4px;
                border: 1px solid rgba(16, 185, 129, 0.3);
            """)
            l.setAlignment(Qt.AlignCenter)
            return l
        
        coordGrid.addWidget(coordLab("X1"), 0, 0)
        self.vX1 = coordVal()
        coordGrid.addWidget(self.vX1, 0, 1)
        
        coordGrid.addWidget(coordLab("Y1"), 1, 0)
        self.vY1 = coordVal()
        coordGrid.addWidget(self.vY1, 1, 1)
        
        coordGrid.addWidget(coordLab("X2"), 2, 0)
        self.vX2 = coordVal()
        coordGrid.addWidget(self.vX2, 2, 1)
        
        coordGrid.addWidget(coordLab("Y2"), 3, 0)
        self.vY2 = coordVal()
        coordGrid.addWidget(self.vY2, 3, 1)
        
        coordGrid.setColumnStretch(0, 0)
        coordGrid.setColumnStretch(1, 1)
        
        coordInfoBox.addLayout(coordGrid)
        
        rbox.addWidget(coordInfoFrame)

        # 检测统计分析区域
        statsInfoFrame = QFrame()
        statsInfoFrame.setStyleSheet("""
            background: rgba(245, 158, 11, 0.05);
            border: 1px solid rgba(245, 158, 11, 0.25);
            border-radius: 8px;
            padding: 12px;
        """)
        statsInfoBox = QVBoxLayout(statsInfoFrame)
        statsInfoBox.setSpacing(10)
        statsInfoBox.setContentsMargins(8, 8, 8, 8)

        statsTitle = QLabel("📊 检测统计分析")
        statsTitle.setStyleSheet("""
            color: #f59e0b;
            font-size: 14px;
            font-weight: 600;
            padding-bottom: 6px;
            border-bottom: 1px solid rgba(245, 158, 11, 0.35);
        """)
        statsInfoBox.addWidget(statsTitle)

        statsGrid = QGridLayout()
        statsGrid.setVerticalSpacing(7)
        statsGrid.setHorizontalSpacing(10)
        statsGrid.setContentsMargins(0, 6, 0, 0)

        statsGrid.addWidget(lab("平均用时"), 0, 0)
        self.vAvgTime = val()
        statsGrid.addWidget(self.vAvgTime, 0, 1)

        statsGrid.addWidget(lab("FPS"), 1, 0)
        self.vFPS = val()
        statsGrid.addWidget(self.vFPS, 1, 1)

        statsGrid.addWidget(lab("累计目标"), 2, 0)
        self.vTotalObjects = val()
        statsGrid.addWidget(self.vTotalObjects, 2, 1)

        statsGrid.addWidget(lab("检测帧数"), 3, 0)
        self.vDetectionFrames = val()
        statsGrid.addWidget(self.vDetectionFrames, 3, 1)

        statsGrid.addWidget(lab("平均置信度"), 4, 0)
        self.vAvgConf = val()
        statsGrid.addWidget(self.vAvgConf, 4, 1)
        statsGrid.setColumnStretch(0, 0)
        statsGrid.setColumnStretch(1, 1)
        statsInfoBox.addLayout(statsGrid)

        self.vClassSummary = QLabel("暂无目标")
        self.vClassSummary.setWordWrap(True)
        self.vClassSummary.setStyleSheet("""
            color: #ffffff;
            font-size: 12px;
            line-height: 1.35;
            padding: 8px;
            background: rgba(245, 158, 11, 0.12);
            border-radius: 6px;
            border: 1px solid rgba(245, 158, 11, 0.25);
        """)
        statsInfoBox.addWidget(self.vClassSummary)

        self.btnExportStats = QPushButton("📊 导出统计报告")
        self.btnExportStats.setObjectName("btnSuccess")
        self.btnExportStats.setFixedHeight(42)
        self.btnExportStats.setCursor(Qt.PointingHandCursor)
        statsInfoBox.addWidget(self.btnExportStats)

        rbox.addWidget(statsInfoFrame)
        rbox.addStretch(1)
        
        rwrap.setMinimumWidth(300)
        rwrap.setMaximumWidth(360)

        main.addLayout(left, 4)
        main.addWidget(rwrap, 1)

        # 状态
        self.last_vis = None
        self.worker = None
        self.current_model_id = DEFAULT_MODEL_ID
        self.model_cache = {}  # 模型缓存
        self.stats = DetectionStats()
        self.current_source_type = "-"
        self.current_source_name = ""

        # 事件
        self.btnOpenImg.clicked.connect(self.on_open_img)
        self.btnOpenVid.clicked.connect(self.on_open_vid)
        self.btnStop.clicked.connect(self.on_stop_video)
        self.btnSave.clicked.connect(self.on_save)
        self.btnCamera.clicked.connect(self.on_open_cam)
        self.btnClear.clicked.connect(self.on_clear_display)
        self.btnExportStats.clicked.connect(self.on_export_stats)

        # 懒加载模型（第一次使用时才加载）
        self.model = None
        
        # 设置状态栏
        self.statusBar().showMessage(f"🔥 多模型系统已就绪！当前: {MODEL_DISPLAY_NAMES[self.current_model_id]}")
        self._update_stats_panel()

        # 现代化主题样式
        self.setStyleSheet("""
        /* ===== 全局样式 ===== */
        QMainWindow { 
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                       stop:0 #0f1419, stop:0.5 #1a1f2e, stop:1 #0f1419);
            font-family: 'Microsoft YaHei UI', 'Segoe UI', Arial, sans-serif;
        }
        
        QLabel { 
            color: #e2e8f0; 
            font-size: 14px;
            font-weight: 500;
        }
        
        QStatusBar { 
            color: #94a3b8; 
            background: rgba(15, 23, 42, 0.8);
            border-top: 1px solid #334155;
        }

        /* ===== 现代卡片设计 ===== */
        #card {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                       stop:0 rgba(30, 41, 59, 0.9), 
                       stop:1 rgba(15, 23, 42, 0.9));
            border: 2px solid transparent;
            border-radius: 16px;
            backdrop-filter: blur(10px);
        }
        
        #card:hover {
            border: 2px solid rgba(59, 130, 246, 0.3);
            box-shadow: 0 8px 32px rgba(59, 130, 246, 0.1);
        }
        
        #mainPreview {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                       stop:0 rgba(15, 23, 42, 0.95), 
                       stop:0.5 rgba(30, 41, 59, 0.8),
                       stop:1 rgba(15, 23, 42, 0.95));
            color: #64748b;
            border: 3px dashed rgba(100, 116, 139, 0.4);
            border-radius: 16px;
            font-size: 18px;
            font-weight: 600;
        }
        
        #mainPreview:hover {
            border-color: rgba(59, 130, 246, 0.5);
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                       stop:0 rgba(15, 23, 42, 0.98), 
                       stop:0.5 rgba(30, 41, 59, 0.9),
                       stop:1 rgba(15, 23, 42, 0.98));
        }

        /* ===== 现代按钮设计 ===== */
        QPushButton {
            border-radius: 10px;
            padding: 10px 16px;
            font-weight: 600;
            font-size: 14px;
            border: none;
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                       stop:0 #374151, stop:1 #1f2937);
            color: #f1f5f9;
        }
        
        QPushButton:hover {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                       stop:0 #4b5563, stop:1 #374151);
        }
        
        QPushButton:pressed {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                       stop:0 #1f2937, stop:1 #111827);
        }

        /* ===== 语义色彩 - 现代渐变 ===== */
        #btnPrimary { 
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                       stop:0 #3b82f6, stop:1 #1d4ed8);
            color: white;
            font-size: 14px;
        }
        #btnPrimary:hover { 
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                       stop:0 #60a5fa, stop:1 #2563eb);
        }
        #btnPrimary:pressed { 
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                       stop:0 #1d4ed8, stop:1 #1e3a8a);
        }

        #btnSuccess { 
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                       stop:0 #10b981, stop:1 #047857);
            box-shadow: 0 4px 14px rgba(16, 185, 129, 0.3);
        }
        #btnSuccess:hover { 
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                       stop:0 #34d399, stop:1 #059669);
            box-shadow: 0 6px 20px rgba(16, 185, 129, 0.4);
        }
        #btnSuccess:pressed { 
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                       stop:0 #047857, stop:1 #065f46);
        }

        #btnDanger { 
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                       stop:0 #ef4444, stop:1 #dc2626);
            box-shadow: 0 4px 14px rgba(239, 68, 68, 0.3);
        }
        #btnDanger:hover { 
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                       stop:0 #f87171, stop:1 #ef4444);
            box-shadow: 0 6px 20px rgba(239, 68, 68, 0.4);
        }
        #btnDanger:pressed { 
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                       stop:0 #dc2626, stop:1 #b91c1c);
        }

        #btnSecondary { 
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                       stop:0 #6b7280, stop:1 #4b5563);
            box-shadow: 0 4px 14px rgba(107, 114, 128, 0.3);
        }
        #btnSecondary:hover { 
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                       stop:0 #9ca3af, stop:1 #6b7280);
            box-shadow: 0 6px 20px rgba(107, 114, 128, 0.4);
        }
        #btnSecondary:pressed { 
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                       stop:0 #4b5563, stop:1 #374151);
        }

        /* ===== 现代进度条 ===== */
        QProgressBar {
            background: rgba(15, 23, 42, 0.9);
            color: #ffffff;
            border: 1px solid rgba(6, 182, 212, 0.4);
            border-radius: 8px;
            height: 20px;
            text-align: center;
            font-weight: 600;
            font-size: 11px;
        }
        
        QProgressBar::chunk {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                       stop:0 #06b6d4, stop:0.5 #0891b2, stop:1 #0e7490);
            border-radius: 7px;
            margin: 1px;
        }

        /* ===== 信息标签美化 ===== */
        #infoLabel {
            color: #94a3b8;
            font-size: 13px;
            font-weight: 500;
            padding: 6px 0;
            min-width: 70px;
        }
        
        #valueLabel {
            color: #ffffff;
            font-size: 13px;
            font-weight: 600;
            padding: 6px 10px;
            background: rgba(59, 130, 246, 0.15);
            border-radius: 6px;
            border: 1px solid rgba(59, 130, 246, 0.3);
            min-width: 60px;
        }

        /* ===== 窗口美化 ===== */
        QMainWindow::separator {
            background: rgba(71, 85, 105, 0.3);
            width: 2px;
        }
        """)

    # ========== 模型管理 ==========
    def get_model(self):
        """获取当前选中的模型（懒加载）"""
        if self.current_model_id in self.model_cache:
            return self.model_cache[self.current_model_id]
        
        # 加载模型
        model_path = MODELS[self.current_model_id]
        if not os.path.exists(model_path):
            QMessageBox.warning(self, "⚠️ 模型文件未找到", f"未找到权重文件：{model_path}")
            return None
        
        try:
            self.statusBar().showMessage(f"⏳ 正在加载模型: {MODEL_DISPLAY_NAMES[self.current_model_id]}...")
            model = YOLO(model_path)
            self.model_cache[self.current_model_id] = model
            self.statusBar().showMessage(f"🔥 {MODEL_DISPLAY_NAMES[self.current_model_id]} 加载成功！")
            return model
        except Exception as e:
            QMessageBox.critical(self, "❌ 模型加载失败", f"加载失败: {str(e)}")
            return None
    
    def on_model_changed(self, index):
        """模型切换事件"""
        new_model_id = self.cmbModel.itemData(index)
        if new_model_id == self.current_model_id:
            return
        
        self.current_model_id = new_model_id
        self.statusBar().showMessage(f"🔄 已切换到: {MODEL_SHORT_NAMES[self.current_model_id]}")
        
        # 如果有正在运行的检测任务，停止它
        if self.worker and self.worker.isRunning():
            self.on_stop_video()
            QMessageBox.information(self, "✅ 模型已切换", 
                f"已切换到 {MODEL_SHORT_NAMES[self.current_model_id]}\n视频/摄像头检测已停止，请重新开始。")

    # ========== 图片 ==========
    def on_open_img(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择图片", "", "Images (*.jpg *.jpeg *.png *.bmp)")
        if not path: return
        self.on_stop_video()

        model = self.get_model()
        if model is None:
            return

        self._reset_stats("图片", path)
        t0 = time.time()
        res = model.predict(path, device=INFER_DEVICE, imgsz=640, conf=0.3, iou=0.5, verbose=False)[0]
        used = (time.time()-t0)*1000
        vis = res.plot()
        self.last_vis = vis
        self._show_vis(vis)
        self._fill_info(used, res)
        self.stats.update_from_result(
            res, used, MODEL_SHORT_NAMES.get(self.current_model_id, self.current_model_id),
            "图片", frame_index=1, source_name=path
        )
        self._update_stats_panel()

    # ========== 视频 ==========
    def on_open_vid(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择视频", "", "Videos (*.mp4 *.avi *.mov *.mkv)")
        if not path: return
        self.on_stop_video()
        
        model = self.get_model()
        if model is None:
            return
        
        self._reset_stats("视频", path)
        self.worker = VideoWorker(model, path, imgsz=640, conf=0.3, iou=0.5, step=2)  # CPU 建议 step=2
        self.worker.frame_ready.connect(self._on_frame)
        self.worker.finished.connect(lambda: self.statusBar().showMessage("🎬 视频处理完成"))
        self.worker.start()
        self.statusBar().showMessage("🚀 正在处理视频，请稍候...")

    def _on_frame(self, vis, used_ms, info, res=None):
        self.last_vis = vis
        self._show_vis(vis)
        self.vTime.setText(f"{used_ms:.1f}")
        self.vCount.setText(str(info["count"]))
        self.vMain.setText(info["main"])
        self.bar.setValue(int(info["conf"]*100))
        x1,y1,x2,y2 = info["xyxy"]
        self.vX1.setText(str(x1)); self.vY1.setText(str(y1))
        self.vX2.setText(str(x2)); self.vY2.setText(str(y2))
        if res is not None:
            self.stats.update_from_result(
                res, used_ms, MODEL_SHORT_NAMES.get(self.current_model_id, self.current_model_id),
                self.current_source_type, frame_index=info.get("frame_index"),
                source_name=info.get("source_name", self.current_source_name)
            )
            self._update_stats_panel()

    def on_stop_video(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()
            self.worker = None

    def on_open_cam(self):
        self.on_stop_video()  # 停掉可能正在跑的视频
        
        model = self.get_model()
        if model is None:
            return
        
        self._reset_stats("摄像头", "camera_0")
        self.worker = CameraWorker(model, cam_index=0, imgsz=640, conf=0.3, iou=0.5, step=1)
        self.worker.frame_ready.connect(self._on_frame)
        self.worker.finished.connect(lambda: self.statusBar().showMessage("📹 摄像头已停止"))
        self.worker.start()
        self.statusBar().showMessage("📷 摄像头已启动，实时检测中...")

    # ========== 通用 ==========
    def _reset_stats(self, source_type="-", source_name=""):
        self.current_source_type = source_type
        self.current_source_name = source_name
        self.stats.reset()
        self.stats.source_type = source_type
        self.stats.source_name = source_name
        self.stats.model_name = MODEL_SHORT_NAMES.get(self.current_model_id, self.current_model_id)
        self._update_stats_panel()

    def _update_stats_panel(self):
        summary = self.stats.get_summary()
        self.vAvgTime.setText(f"{summary['avg_inference_ms']:.1f} ms")
        self.vFPS.setText(f"{summary['avg_fps']:.2f}")
        self.vTotalObjects.setText(str(summary["total_objects"]))
        self.vDetectionFrames.setText(f"{summary['detection_frames']}/{summary['total_frames']}")
        self.vAvgConf.setText(f"{summary['avg_confidence']:.3f}" if summary["total_objects"] else "-")
        self.vClassSummary.setText(summary["class_summary"])

    def _show_vis(self, vis):
        self.lblPreview.setPixmap(bgr_to_qpix(vis))

    def _fill_info(self, used_ms, res):
        self.vTime.setText(f"{used_ms:.1f}")
        self.vCount.setText(str(len(res.boxes)))
        if len(res.boxes):
            confs = res.boxes.conf.cpu().numpy()
            idx = int(np.argmax(confs))
            cls_id = int(res.boxes.cls[idx])
            name = res.names.get(cls_id, str(cls_id))
            self.vMain.setText(name)
            self.bar.setValue(int(confs[idx]*100))
            x1, y1, x2, y2 = res.boxes.xyxy[idx].cpu().numpy().astype(int)
            self.vX1.setText(str(x1))
            self.vY1.setText(str(y1))
            self.vX2.setText(str(x2))
            self.vY2.setText(str(y2))
        else:
            self.vMain.setText("-")
            self.bar.setValue(0)
            for w in (self.vX1, self.vY1, self.vX2, self.vY2):
                w.setText("-")

    def on_export_stats(self):
        if self.stats.total_frames == 0:
            QMessageBox.information(self, "💡 提示", "暂无统计数据可导出")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "导出统计报告", "detection_statistics.csv", "CSV Files (*.csv)"
        )
        if not path:
            return
        if not path.lower().endswith(".csv"):
            path += ".csv"
        try:
            self.stats.export_csv(path)
            self.statusBar().showMessage(f"✅ 统计报告已导出：{path}")
            QMessageBox.information(self, "✅ 导出成功", f"统计报告已保存到：\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "❌ 导出失败", f"CSV 写入失败：{str(e)}")

    def on_save(self):
        if self.last_vis is None:
            QMessageBox.information(self, "💡 提示", "暂无检测结果可保存"); return
        path, _ = QFileDialog.getSaveFileName(self, "保存检测结果", "detection_result.jpg", "Images (*.jpg *.png)")
        if not path: return
        cv2.imwrite(path, self.last_vis)
        self.statusBar().showMessage(f"✅ 检测结果已保存：{path}")

    def on_clear_display(self):
        """清除显示内容"""
        self.lblPreview.setText("📸 点击按钮开始检测")
        self.last_vis = None
        # 重置信息显示
        self.vTime.setText("-")
        self.vCount.setText("-")
        self.vMain.setText("-")
        self.bar.setValue(0)
        for w in (self.vX1, self.vY1, self.vX2, self.vY2):
            w.setText("-")
        self._reset_stats()
        self.statusBar().showMessage("🧹 显示内容已清除")


    def resizeEvent(self, e):
        if self.last_vis is not None:
            self._show_vis(self.last_vis)
        super().resizeEvent(e)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = Main()
    w.show()
    sys.exit(app.exec_())
