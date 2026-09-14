import sys, time, os, cv2, numpy as np
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton, QFileDialog,
    QGridLayout, QVBoxLayout, QHBoxLayout, QProgressBar, QMessageBox, QSizePolicy
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QPixmap, QImage
from ultralytics import YOLO
from PyQt5.QtWidgets import QFrame, QComboBox
from traffic_api.config import get_settings

# ==================== 多模型配置 ====================
MODEL_PATH = r"<LOCAL_PATH>"

APP_SETTINGS = get_settings()
if APP_SETTINGS.model_path:
    MODEL_PATH = str(APP_SETTINGS.model_path)

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
INFER_DEVICE = APP_SETTINGS.infer_device
INFER_DEVICE = APP_SETTINGS.infer_device
INFER_IMGSZ = APP_SETTINGS.img_size
INFER_CONF = APP_SETTINGS.conf_threshold
INFER_IOU = APP_SETTINGS.iou_threshold

def bgr_to_qpix(bgr: np.ndarray) -> QPixmap:
    if bgr is None: return QPixmap()
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    h, w, ch = rgb.shape
    qimg = QImage(rgb.data, w, h, ch*w, QImage.Format_RGB888)
    return QPixmap.fromImage(qimg)

class VideoWorker(QThread):
    frame_ready = pyqtSignal(np.ndarray, float, dict)   # vis, used_ms, info
    finished = pyqtSignal()

    def __init__(self, model: YOLO, video_path: str, imgsz=INFER_IMGSZ, conf=INFER_CONF, iou=INFER_IOU, step=2):
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

            info = {
                "count": len(res.boxes),
                "main": "-",
                "conf": 0,
                "xyxy": ("-", "-", "-", "-")
            }
            if len(res.boxes):
                confs = res.boxes.conf.cpu().numpy()
                idx = int(np.argmax(confs))
                cls_id = int(res.boxes.cls[idx])
                name = res.names.get(cls_id, str(cls_id))
                x1, y1, x2, y2 = res.boxes.xyxy[idx].cpu().numpy().astype(int)
                info.update({"main": name, "conf": float(confs[idx]),
                             "xyxy": (int(x1), int(y1), int(x2), int(y2))})
            self.frame_ready.emit(vis, used, info)

        cap.release()
        self.finished.emit()
class CameraWorker(QThread):
    frame_ready = pyqtSignal(np.ndarray, float, dict)
    finished = pyqtSignal()

    def __init__(self, model: YOLO, cam_index=0, imgsz=INFER_IMGSZ, conf=INFER_CONF, iou=INFER_IOU, step=1):
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

            info = {
                "count": len(res.boxes),
                "main": "-",
                "conf": 0,
                "xyxy": ("-", "-", "-", "-")
            }
            if len(res.boxes):
                confs = res.boxes.conf.cpu().numpy()
                idx = int(np.argmax(confs))
                cls_id = int(res.boxes.cls[idx])
                name = res.names.get(cls_id, str(cls_id))
                x1, y1, x2, y2 = res.boxes.xyxy[idx].cpu().numpy().astype(int)
                info.update({"main": name, "conf": float(confs[idx]),
                             "xyxy": (int(x1), int(y1), int(x2), int(y2))})
            self.frame_ready.emit(vis, used, info)

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

        # 事件
        self.btnOpenImg.clicked.connect(self.on_open_img)
        self.btnOpenVid.clicked.connect(self.on_open_vid)
        self.btnStop.clicked.connect(self.on_stop_video)
        self.btnSave.clicked.connect(self.on_save)
        self.btnCamera.clicked.connect(self.on_open_cam)
        self.btnClear.clicked.connect(self.on_clear_display)

        # 懒加载模型（第一次使用时才加载）
        self.model = None
        
        # 设置状态栏
        self.statusBar().showMessage(f"🔥 多模型系统已就绪！当前: {MODEL_DISPLAY_NAMES[self.current_model_id]}")

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

        t0 = time.time()
        res = model.predict(path, device=INFER_DEVICE, imgsz=INFER_IMGSZ, conf=INFER_CONF, iou=INFER_IOU, verbose=False)[0]
        used = (time.time()-t0)*1000
        vis = res.plot()
        self.last_vis = vis
        self._show_vis(vis)
        self._fill_info(used, res)

    # ========== 视频 ==========
    def on_open_vid(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择视频", "", "Videos (*.mp4 *.avi *.mov *.mkv)")
        if not path: return
        self.on_stop_video()
        
        model = self.get_model()
        if model is None:
            return
        
        self.worker = VideoWorker(model, path, imgsz=INFER_IMGSZ, conf=INFER_CONF, iou=INFER_IOU, step=2)  # CPU 建议 step=2
        self.worker.frame_ready.connect(self._on_frame)
        self.worker.finished.connect(lambda: self.statusBar().showMessage("🎬 视频处理完成"))
        self.worker.start()
        self.statusBar().showMessage("🚀 正在处理视频，请稍候...")

    def _on_frame(self, vis, used_ms, info):
        self.last_vis = vis
        self._show_vis(vis)
        self.vTime.setText(f"{used_ms:.1f}")
        self.vCount.setText(str(info["count"]))
        self.vMain.setText(info["main"])
        self.bar.setValue(int(info["conf"]*100))
        x1,y1,x2,y2 = info["xyxy"]
        self.vX1.setText(str(x1)); self.vY1.setText(str(y1))
        self.vX2.setText(str(x2)); self.vY2.setText(str(y2))

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
        
        self.worker = CameraWorker(model, cam_index=0, imgsz=INFER_IMGSZ, conf=INFER_CONF, iou=INFER_IOU, step=1)
        self.worker.frame_ready.connect(self._on_frame)
        self.worker.finished.connect(lambda: self.statusBar().showMessage("📹 摄像头已停止"))
        self.worker.start()
        self.statusBar().showMessage("📷 摄像头已启动，实时检测中...")

    # ========== 通用 ==========
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
