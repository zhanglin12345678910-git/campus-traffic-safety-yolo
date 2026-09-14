#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🚦 智能交通标志检测系统 - Web版本
基于Flask + SQLAlchemy + YOLO11的前后端分离架构
作者: project_user
版本: 2.0 (Web Edition)

多模型说明（新增）：
- 支持在 MODELS 配置多个权重文件，通过 model_id 选择使用哪个模型。
- 默认模型使用 DEFAULT_MODEL_ID（也可以通过 /api/models/active 切换）。
- 图片/视频/摄像头检测接口支持从 form-data 或 query 参数传入 model_id。
"""

import os
import time
import uuid
import cv2
import numpy as np
import threading
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import base64

# io / PIL.Image 目前未使用，先移除以减少告警；后续如果要做 base64->PIL 的图片解析再加回来
# import io
# from PIL import Image

# 尝试导入YOLO，处理可能的导入错误
try:
    import sys
    import os
    # 添加父目录到Python路径，以便导入本地ultralytics
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)

    from ultralytics import YOLO
    YOLO_AVAILABLE = True
    print("✅ ultralytics 导入成功")
except ImportError as e:
    print(f"❌ ultralytics 导入失败: {e}")
    print("💡 请确保在正确的Python环境中运行")
    YOLO_AVAILABLE = False
    YOLO = None


# ==================== 配置 ====================
app = Flask(__name__)
app.config['SECRET_KEY'] = 'yolo11-traffic-detection-2024'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///traffic_detection.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['RESULT_FOLDER'] = 'results'
app.config['MAX_CONTENT_LENGTH'] = None  # 取消文件大小限制

# 创建必要的文件夹
for folder in [app.config['UPLOAD_FOLDER'], app.config['RESULT_FOLDER']]:
    os.makedirs(folder, exist_ok=True)

# 初始化扩展
db = SQLAlchemy(app)
CORS(app)

# ==================== 修改的参数 ====================
# 1) 多模型权重配置：把你所有的 .pt 权重都登记到 MODELS 里
#    - key:  model_id（接口里传这个字符串来选择模型）
#    - value: 权重文件路径（支持绝对路径/相对路径）
#
#    例子：
#    MODELS = {
#        "best": r"<LOCAL_PATH>",
#        "yolo11n": r"<LOCAL_PATH>",
#        "ablation_v2": r"<LOCAL_PATH>",
#    }
MODELS = {
    # PSSM-YOLO（自研改进模型 - 最佳性能）
    "PSSM-YOLO": r"<LOCAL_PATH>",
    
    # YOLO系列知名模型
    "YOLOv11n": r"<LOCAL_PATH>",
    "YOLOv10n": r"<LOCAL_PATH>",
    "YOLOv9t": r"<LOCAL_PATH>",
    "YOLOv8n": r"<LOCAL_PATH>",
    "YOLOv7-tiny": r"<LOCAL_PATH>",
    "YOLOv5n": r"<LOCAL_PATH>",
    
    # 实时检测优化模型
    "YOLO-NAS-s": r"<LOCAL_PATH>",
    "RT-DETR": r"<LOCAL_PATH>",
    
    # 轻量级模型
    "YOLO-FastestV2": r"<LOCAL_PATH>",
    "PP-YOLOE+": r"<LOCAL_PATH>",
}

# 2) 默认模型：前端/接口不传 model_id 时，会使用这个模型（也可用 /api/models/active 切换）
DEFAULT_MODEL_ID = "PSSM-YOLO"  # ✅ 你可以改成 MODELS 里任意一个 key

# 3) 推理参数（图片/视频）—— 误检多就提高 conf；漏检多就降低 conf
#    imgsz 越大通常越准但越慢；conf/iou 会影响框的数量和质量
PREDICT_IMG_VIDEO = {
    "imgsz": 640,   # ✅ 常用：640 / 800 / 1024
    "conf": 0.60,   # ✅ 误检多：0.6->0.7；漏检多：0.6->0.5
    "iou": 0.50,    # ✅ 常用：0.45~0.7
}

# 4) 摄像头推理参数（为了速度通常会更小一些）
PREDICT_CAMERA = {
    "imgsz": 416,   # ✅ 常用：320 / 416 / 640
    "conf": 0.65,   # ✅ 摄像头场景误检多可以略高
    "iou": 0.50,
}

# 5) 视频抽帧设置：step=2 表示每2帧处理1帧（越大越快但越“跳”）
VIDEO_FRAME_STEP = 2  # ✅ 你可以改成 1（每帧都算）/2/3...

# 6) 摄像头/视频保存检测记录的最小间隔（秒）：避免数据库写入太频繁
VIDEO_DB_SAVE_INTERVAL_SEC = 3   # ✅ 视频：检测到目标时，至少间隔N秒才写一条记录
CAMERA_DB_SAVE_INTERVAL_SEC = 2  # ✅ 摄像头：检测到目标时，至少间隔N秒才写一条记录

# 7) 摄像头分辨率/FPS（不是所有摄像头都支持，设置失败时 OpenCV 可能会忽略）
CAMERA_CAPTURE_SETTINGS = {
    "width": 640,
    "height": 480,
    "fps": 30,
    "buffersize": 1,
}

# ==================== 多模型运行时变量（一般不需要改） ====================
# 模型缓存：model_id -> YOLO 实例（懒加载，第一次用才加载）
models = {}

# 当前激活模型（可通过接口切换），仅作为“默认”使用
active_model_id = DEFAULT_MODEL_ID

# 模型加载锁：避免并发请求导致重复加载同一个权重
models_lock = threading.Lock()


def resolve_model_id(req) -> str:
    """从请求中解析 model_id。

    支持来源：
    - form-data: model_id
    - query string: ?model_id=xxx
    - json body: {"model_id": "xxx"}

    若都没有则返回 active_model_id。
    """
    mid = None

    # form-data / x-www-form-urlencoded
    mid = req.form.get("model_id") or req.args.get("model_id")

    # json body
    if not mid:
        try:
            json_data = req.get_json(silent=True) or {}
            mid = json_data.get("model_id")
        except Exception:
            mid = None

    return (mid or active_model_id).strip() if isinstance(mid, str) else active_model_id


def get_model(model_id: str):
    """获取（并按需加载）指定 `model_id` 的 YOLO 模型。

    说明：
    - 支持多模型懒加载（第一次请求时才从磁盘加载权重）。
    - 使用 `models` 缓存已加载的模型实例，避免重复加载加速性能。
    - 使用 `models_lock` 保证并发请求不会同时重复加载同一权重文件。

    返回: (model, error_message)
    - 成功： (YOLO 实例, None)
    - 失败： (None, '错误原因字符串')
    """
    if not YOLO_AVAILABLE:
        return None, "ultralytics 包不可用，无法加载模型"

    if not model_id:
        model_id = active_model_id

    if model_id not in MODELS:
        return None, f"未知的 model_id: {model_id}"

    # 从配置表中取出权重路径并检查文件是否存在
    weight_path = MODELS[model_id]
    if not os.path.exists(weight_path):
        # 提示更明确的错误信息，便于前端/调用者诊断路径问题
        return None, f"模型文件未找到: {weight_path}"

    # 已缓存
    if model_id in models and models[model_id] is not None:
        return models[model_id], None

    # 懒加载 + 加锁防并发：仅在缓存中不存在或为 None 时才尝试加载
    with models_lock:
        if model_id in models and models[model_id] is not None:
            return models[model_id], None

        try:
            print(f"📂 正在加载模型[{model_id}]: {weight_path}")
            models[model_id] = YOLO(weight_path)
            print(f"🔥 模型[{model_id}]加载成功!")
            return models[model_id], None
        except Exception as e:
            models[model_id] = None
            return None, f"模型加载失败[{model_id}]: {e}"


# ==================== 数据库模型 ====================
class Detection(db.Model):
    """数据库模型：检测记录（Detection）

    字段说明：
    - `session_id`: 全局唯一会话ID，用于标识一次上传/检测会话。
    - 文件信息：`original_filename`, `file_path`, `result_path`, `file_type`, `file_size`。
    - 检测信息：`detection_time`(ms), `object_count`, `main_class`, `confidence`, bbox 坐标。
    - `created_at`: 记录创建时间（使用本地时间）。

    该模型主要用于保存前端上传文件或摄像头/视频检测的结果，以便查询历史与统计。
    """

    __tablename__ = 'detections'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(36), nullable=False, default=lambda: str(uuid.uuid4()))

    # 文件信息
    original_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    result_path = db.Column(db.String(500), nullable=True)
    file_type = db.Column(db.String(20), nullable=False)  # image/video
    file_size = db.Column(db.Integer, nullable=False)

    # 检测结果-+
    detection_time = db.Column(db.Float, nullable=False)  # 检测用时(ms)
    object_count = db.Column(db.Integer, default=0)
    main_class = db.Column(db.String(100), nullable=True)
    confidence = db.Column(db.Float, default=0.0)
    bbox_x1 = db.Column(db.Integer, nullable=True)
    bbox_y1 = db.Column(db.Integer, nullable=True)
    bbox_x2 = db.Column(db.Integer, nullable=True)
    bbox_y2 = db.Column(db.Integer, nullable=True)

    # 时间戳 - 使用本地时间
    created_at = db.Column(db.DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'session_id': self.session_id,
            'original_filename': self.original_filename,
            'file_type': self.file_type,
            'file_size': self.file_size,
            'detection_time': self.detection_time,
            'object_count': self.object_count,
            'main_class': self.main_class,
            'confidence': self.confidence,
            'bbox': {
                'x1': self.bbox_x1,
                'y1': self.bbox_y1,
                'x2': self.bbox_x2,
                'y2': self.bbox_y2
            } if self.bbox_x1 is not None else None,
            'created_at': self.created_at.isoformat()
        }

# ==================== 工具函数 ====================
def load_model():
    """兼容旧逻辑：加载默认/激活模型。

    说明：
    - 旧版本只加载一个全局 model；现在改为多模型。
    - 这里返回 True/False，用于 init_app 阶段预热默认模型。
    """
    global active_model_id
    try:
        # 如果配置里没有默认 id，则自动选择第一个
        if active_model_id not in MODELS and len(MODELS) > 0:
            active_model_id = list(MODELS.keys())[0]

        m, err = get_model(active_model_id)
        if err:
            print(f"⚠️ 警告: {err}")
            return False

        return True
    except Exception as e:
        print(f"❌ 模型加载失败: {e}")
        print(f"🔍 错误类型: {type(e).__name__}")
        return False


def allowed_file(filename):
    """检查文件类型"""
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'mp4', 'avi', 'mov', 'mkv'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_file_type(filename):
    """获取文件类型"""
    ext = filename.rsplit('.', 1)[1].lower()
    if ext in {'png', 'jpg', 'jpeg', 'gif', 'bmp'}:
        return 'image'
    elif ext in {'mp4', 'avi', 'mov', 'mkv'}:
        return 'video'
    return 'unknown'


def process_detection_result(results):
    """处理 YOLO 推理返回的结果并提取关键信息。

    输入 `results` 为 YOLO.predict() 返回的对象列表（通常长度为1）。
    返回值:
    - vis: 可直接用于保存/编码的可视化图像数组（BGR, numpy.ndarray），或 None。
    - info: 字典，包含以下键：
        - 'count': 检测到的目标数量
        - 'main': 置信度最高的目标类别名称或 '-'
        - 'conf': 最高目标的置信度（0-1 float）
        - 'xyxy': (x1, y1, x2, y2) 表示边界框（若无目标则为 None
    """
    if not results or len(results) == 0:
        return None, {
            "count": 0,
            "main": "-",
            "conf": 0,
            "xyxy": (None, None, None, None)
        }

    res = results[0]
    vis = res.plot()  # 绘制检测框

    info = {
        "count": len(res.boxes),
        "main": "-",
        "conf": 0,
        "xyxy": (None, None, None, None)
    }

    if len(res.boxes) > 0:
        confs = res.boxes.conf.cpu().numpy()
        idx = int(np.argmax(confs))
        cls_id = int(res.boxes.cls[idx])
        name = res.names.get(cls_id, str(cls_id))
        x1, y1, x2, y2 = res.boxes.xyxy[idx].cpu().numpy().astype(int)

        info.update({
            "main": name,
            "conf": float(confs[idx]),
            "xyxy": (int(x1), int(y1), int(x2), int(y2))
        })

    return vis, info


def save_result_image(vis_array, session_id):
    """将可视化数组保存为 JPEG 文件并返回文件路径。

    参数:
    - `vis_array`: BGR 格式的 numpy.ndarray，通常来自 `res.plot()` 或 OpenCV 处理后的帧。
    - `session_id`: 用于生成唯一保存文件名。

    返回: 保存的文件绝对路径或 None（失败时）。
    """
    try:
        result_filename = f"result_{session_id}_{int(time.time())}.jpg"
        result_path = os.path.join(app.config['RESULT_FOLDER'], result_filename)
        cv2.imwrite(result_path, vis_array)
        return result_path
    except Exception as e:
        print(f"保存结果图片失败: {e}")
        return None

# ==================== API路由 ====================
@app.route('/')
def index():
    """主页"""
    return render_template('index.html')


@app.route('/api/models', methods=['GET'])
def list_models():
    """列出当前可用的模型（model_id 列表 + 是否存在文件）。"""
    data = []
    for mid, path in MODELS.items():
        data.append({
            "model_id": mid,
            "path": path,
            "exists": os.path.exists(path),
            "is_active": (mid == active_model_id),
            "is_loaded": (mid in models and models[mid] is not None)
        })

    return jsonify({
        "success": True,
        "active_model_id": active_model_id,
        "models": data
    })


@app.route('/api/models/active', methods=['GET', 'POST'])
def set_active_model():
    """获取/设置默认使用的模型。

    - GET: 返回当前 active_model_id
    - POST: body/form 传 model_id，切换 active_model_id，并尝试预加载
    """
    global active_model_id

    if request.method == 'GET':
        return jsonify({
            "success": True,
            "active_model_id": active_model_id,
        })

    mid = resolve_model_id(request)
    if mid not in MODELS:
        return jsonify({"error": f"未知的 model_id: {mid}"}), 400

    active_model_id = mid
    m, err = get_model(active_model_id)
    if err:
        return jsonify({"error": err}), 500

    return jsonify({
        "success": True,
        "active_model_id": active_model_id
    })


@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查"""
    try:
        # 检查数据库连接
        detection_count = Detection.query.count()
        db_status = 'ok'
    except Exception as e:
        detection_count = -1
        db_status = f'error: {str(e)}'

    # 默认模型是否已加载（懒加载时可能还没）
    default_loaded = active_model_id in models and models.get(active_model_id) is not None

    return jsonify({
        'status': 'ok',
        'active_model_id': active_model_id,
        'active_model_loaded': default_loaded,
        'available_models': list(MODELS.keys()),
        'database_status': db_status,
        'detection_count': detection_count,
        'timestamp': datetime.now().isoformat()
    })


@app.route('/api/test/create_sample', methods=['POST'])
def create_sample_detection():
    """创建示例检测记录 - 用于测试历史记录"""
    try:
        sample_detection = Detection(
            session_id=str(uuid.uuid4()),
            original_filename="test_sample.jpg",
            file_path="/test/path",
            file_type="image",
            file_size=12345,
            detection_time=25.5,
            object_count=2,
            main_class="traffic_sign",
            confidence=0.85,
            bbox_x1=100,
            bbox_y1=100,
            bbox_x2=200,
            bbox_y2=200
        )
        db.session.add(sample_detection)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': '示例记录已创建',
            'session_id': sample_detection.session_id
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'创建示例记录失败: {str(e)}'}), 500


@app.route('/api/detect/image', methods=['POST'])
def detect_image():
    """图片检测接口（POST）

    支持 multipart/form-data 上传文件字段名 `file`，可选传入 `model_id` 来指定使用的模型。
    处理流程：
    1. 校验上传文件及扩展名
    2. 保存临时文件到 `UPLOAD_FOLDER`
    3. 使用指定或默认模型执行推理
    4. 解析结果、保存可视化图片并将记录写入数据库（若可用）
    5. 将检测统计和结果图像（base64）一并返回
    """
    try:
        if 'file' not in request.files:
            return jsonify({'error': '没有上传文件'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': '没有选择文件'}), 400

        if not allowed_file(file.filename):
            return jsonify({'error': '不支持的文件格式'}), 400

        # 选择模型（不传则用 active_model_id）
        model_id = resolve_model_id(request)
        model, err = get_model(model_id)
        if err:
            return jsonify({'error': err}), 500

        # 保存上传的文件
        session_id = str(uuid.uuid4())
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{session_id}_{filename}")
        file.save(file_path)

        # 获取文件信息
        file_size = os.path.getsize(file_path)
        file_type = get_file_type(filename)

        # 执行检测 - 自动选择设备，减少误检
        t0 = time.time()
        device = "cuda" if hasattr(model, 'device') and 'cuda' in str(model.device) else "cpu"

        # ✅ 关键可调：图片/视频推理参数（见顶部 PREDICT_IMG_VIDEO）
        results = model.predict(
            file_path,
            device=device,
            imgsz=PREDICT_IMG_VIDEO["imgsz"],
            conf=PREDICT_IMG_VIDEO["conf"],
            iou=PREDICT_IMG_VIDEO["iou"],
            verbose=False
        )
        detection_time = (time.time() - t0) * 1000

        # 处理结果
        vis, info = process_detection_result(results)
        result_path = save_result_image(vis, session_id) if vis is not None else None

        # 保存到数据库 - 增强错误处理
        try:
            print(f"📝 准备保存检测记录: {filename}, 对象数: {info['count']}")
            detection = Detection(
                session_id=session_id,
                original_filename=filename,
                file_path=file_path,
                result_path=result_path,
                file_type=file_type,
                file_size=file_size,
                detection_time=detection_time,
                object_count=info["count"],
                main_class=info["main"] if info["main"] != "-" else None,
                confidence=info["conf"],
                bbox_x1=info["xyxy"][0],
                bbox_y1=info["xyxy"][1],
                bbox_x2=info["xyxy"][2],
                bbox_y2=info["xyxy"][3]
            )
            db.session.add(detection)
            db.session.commit()
            print(f"✅ 检测记录已保存到数据库: ID={detection.id}, Session={session_id}")
            print(f"📊 数据库总记录数: {Detection.query.count()}")
        except Exception as db_error:
            print(f"❌ 保存到数据库失败: {db_error}")
            import traceback
            traceback.print_exc()
            try:
                db.session.rollback()
            except:
                pass
            # 继续执行，不影响检测结果返回

        # 将结果图片转换为base64返回
        result_image_b64 = None
        if vis is not None:
            _, buffer = cv2.imencode('.jpg', vis)
            result_image_b64 = base64.b64encode(buffer).decode('utf-8')

        return jsonify({
            'success': True,
            'session_id': session_id,
            'model_id': model_id,
            'detection_time': round(detection_time, 2),
            'results': {
                'object_count': info["count"],
                'main_class': info["main"],
                'confidence': round(info["conf"], 3),
                'bbox': {
                    'x1': info["xyxy"][0],
                    'y1': info["xyxy"][1],
                    'x2': info["xyxy"][2],
                    'y2': info["xyxy"][3]
                } if info["xyxy"][0] is not None else None
            },
            'result_image': result_image_b64
        })
    except Exception as e:
        return jsonify({'error': f'检测失败: {str(e)}'}), 500

# 全局视频处理状态
video_processor = None
video_processing = False

class VideoProcessor:
    """视频处理器：在后台线程中对视频文件逐帧执行检测并保存/提供实时帧信息。

    设计说明：
    - 每个 `VideoProcessor` 持有一个 `YOLO` 模型实例和视频路径。
    - 使用独立线程运行 `_process_video`，并通过 `frame_lock` 保护当前帧信息 `current_frame_info` 的读写。
    - 在需要将检测结果写入数据库时，使用 `with app.app_context():` 以确保在后台线程中也有 Flask 应用上下文。
    - `start()` 启动线程，`stop()` 设置 `running=False` 并等待线程退出。
    """
    def __init__(self, model, video_path, session_id, model_id: str):
        self.model = model
        self.model_id = model_id
        self.video_path = video_path
        self.session_id = session_id
        self.cap = None
        self.running = False
        self.thread = None
        self.current_frame_info = None
        self.frame_lock = threading.Lock()
        self.last_save_time = 0  # 上次保存时间
        self.original_filename = os.path.basename(video_path)  # 原始文件名
        self.file_size = os.path.getsize(video_path) if os.path.exists(video_path) else 0  # 文件大小

    def start(self):
        """启动视频处理"""
        try:
            self.cap = cv2.VideoCapture(self.video_path)
            if not self.cap.isOpened():
                return False, "无法打开视频文件"

            self.running = True
            self.thread = threading.Thread(target=self._process_video, daemon=True)
            self.thread.start()

            return True, "视频处理已启动"
        except Exception as e:
            return False, f"启动失败: {str(e)}"

    def stop(self):
        """停止视频处理"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=3)
        if self.cap:
            self.cap.release()
            self.cap = None

    def _process_video(self):
        """视频处理循环"""
        frame_count = 0
        step = VIDEO_FRAME_STEP  # ✅ 关键可调：视频抽帧间隔（见顶部 VIDEO_FRAME_STEP）

        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                break

            if frame_count % step != 0:
                frame_count += 1
                continue

            frame_count += 1

            # 执行检测 - 减少误检
            t0 = time.time()
            device = "cuda" if hasattr(self.model, 'device') and 'cuda' in str(self.model.device) else "cpu"

            # ✅ 关键可调：图片/视频推理参数（见顶部 PREDICT_IMG_VIDEO）
            results = self.model.predict(
                frame,
                device=device,
                imgsz=PREDICT_IMG_VIDEO["imgsz"],
                conf=PREDICT_IMG_VIDEO["conf"],
                iou=PREDICT_IMG_VIDEO["iou"],
                verbose=False
            )
            detection_time = (time.time() - t0) * 1000

            # 处理结果
            vis, info = process_detection_result(results)

            # 🔍 调试日志：每帧都输出检测结果
            print(f"🎬 视频帧 {frame_count}[{self.model_id}]: 检测到 {info['count']} 个对象, 置信度: {info['conf']:.2f}")

            # === 保存检测到对象的记录到数据库（至少间隔N秒）===
            current_time = time.time()
            if info["count"] > 0 and current_time - self.last_save_time >= VIDEO_DB_SAVE_INTERVAL_SEC:
                try:
                    # 🎯 在后台线程中需要使用应用上下文
                    with app.app_context():
                        detection = Detection(
                            session_id=str(uuid.uuid4()),  # 每条记录生成新ID
                            original_filename=self.original_filename,
                            file_path=self.video_path,
                            result_path=None,
                            file_type='video',
                            file_size=self.file_size,
                            detection_time=detection_time,
                            object_count=info["count"],
                            main_class=info["main"] if info["main"] != "-" else None,
                            confidence=info["conf"],
                            bbox_x1=info["xyxy"][0],
                            bbox_y1=info["xyxy"][1],
                            bbox_x2=info["xyxy"][2],
                            bbox_y2=info["xyxy"][3]
                        )
                        db.session.add(detection)
                        db.session.commit()

                        self.last_save_time = current_time
                        print(f"✅ 视频检测已保存[{self.model_id}]: 帧{frame_count}, 对象数: {info['count']}")
                except Exception as db_error:
                    print(f"❌ 保存视频检测记录失败: {db_error}")
                    with app.app_context():
                        try:
                            db.session.rollback()
                        except:
                            pass

            # 编码图像
            result_image_b64 = None
            if vis is not None:
                _, buffer = cv2.imencode('.jpg', vis, [cv2.IMWRITE_JPEG_QUALITY, 80])
                result_image_b64 = base64.b64encode(buffer).decode('utf-8')

            # 更新当前帧信息
            with self.frame_lock:
                self.current_frame_info = {
                    'success': True,
                    'model_id': self.model_id,
                    'frame_number': frame_count,
                    'detection_time': round(detection_time, 2),
                    'results': {
                        'object_count': info["count"],
                        'main_class': info["main"],
                        'confidence': round(info["conf"], 3),
                        'bbox': {
                            'x1': info["xyxy"][0],
                            'y1': info["xyxy"][1],
                            'x2': info["xyxy"][2],
                            'y2': info["xyxy"][3]
                        } if info["xyxy"][0] is not None else None
                    },
                    'result_image': result_image_b64
                }

            time.sleep(0.05)  # 控制处理速度

        self.cap.release()

    def get_current_frame(self):
        """获取当前帧信息"""
        with self.frame_lock:
            return self.current_frame_info

@app.route('/api/detect/video', methods=['POST'])
def detect_video():
    """视频检测API - 实时处理版本"""
    global video_processor, video_processing

    try:
        if 'file' not in request.files:
            return jsonify({'error': '没有上传文件'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': '没有选择文件'}), 400

        if not allowed_file(file.filename):
            return jsonify({'error': '不支持的文件格式'}), 400

        # 选择模型
        model_id = resolve_model_id(request)
        model, err = get_model(model_id)
        if err:
            return jsonify({'error': err}), 500

        # 停止之前的视频处理
        if video_processor:
            video_processor.stop()
            video_processor = None

        # 保存上传的视频文件
        session_id = str(uuid.uuid4())
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{session_id}_{filename}")
        file.save(file_path)

        # 获取视频信息
        cap = cv2.VideoCapture(file_path)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        duration = frame_count / fps if fps > 0 else 0
        cap.release()

        # 启动视频处理器
        video_processor = VideoProcessor(model, file_path, session_id, model_id=model_id)
        success, message = video_processor.start()

        if not success:
            return jsonify({'error': message}), 500

        video_processing = True

        return jsonify({
            'success': True,
            'session_id': session_id,
            'model_id': model_id,
            'video_info': {
                'frame_count': frame_count,
                'fps': fps,
                'duration': duration,
                'filename': filename
            },
            'message': '视频处理已启动，可通过 /api/video/frame 获取实时帧'
        })

    except Exception as e:
        return jsonify({'error': f'视频检测失败: {str(e)}'}), 500

@app.route('/api/video/frame', methods=['GET'])
def get_video_frame():
    """获取视频检测帧 - 实时显示"""
    global video_processor, video_processing

    try:
        if not video_processing or not video_processor:
            return jsonify({'error': '视频未在处理中'}), 400

        # 获取当前帧
        frame_info = video_processor.get_current_frame()

        if frame_info:
            return jsonify(frame_info)
        else:
            return jsonify({
                'success': True,
                'message': '等待视频帧...',
                'result_image': None
            })

    except Exception as e:
        return jsonify({'error': f'获取视频帧失败: {str(e)}'}), 500

@app.route('/api/video/stop', methods=['POST'])
def stop_video():
    """停止视频处理"""
    global video_processor, video_processing

    try:
        video_processing = False

        if video_processor:
            video_processor.stop()
            video_processor = None

        return jsonify({
            'success': True,
            'message': '视频处理已停止'
        })

    except Exception as e:
        return jsonify({'error': f'停止视频失败: {str(e)}'}), 500

# 全局变量存储摄像头状态
camera_active = False
camera_thread = None
camera_capture = None
camera_lock = threading.Lock()  # 添加线程锁防止并发问题
camera_last_save_time = 0  # 上次保存检测记录的时间
CAMERA_SAVE_INTERVAL = 5  # 摄像头检测保存间隔（秒）

@app.route('/api/camera/start', methods=['POST'])
def start_camera():
    """启动摄像头检测并初始化摄像头资源。

    行为概述：
    - 可通过 `model_id` 指定使用的模型（同时会把该模型设为 `active_model_id`，便于后续调用）。
    - 初始化 OpenCV `VideoCapture(0)` 并尝试设置分辨率/FPS。
    - 采用 `camera_lock` 防止并发启动/停止操作冲突。
    - 仅初始化摄像头资源；实际的帧获取/检测发生在 `GET /api/camera/frame` 请求中。
    """
    global camera_active, camera_thread, camera_capture

    with camera_lock:  # 使用锁防止并发问题
        try:
            print("🚀 正在启动摄像头...")

            # 摄像头模式也允许选择模型：如果传了 model_id，就切换 active_model_id
            model_id = resolve_model_id(request)
            model, err = get_model(model_id)
            if err:
                return jsonify({'error': err}), 500

            # 可选：把摄像头模式选择的模型设为默认（更符合直觉）
            global active_model_id
            active_model_id = model_id

            if camera_active:
                print("⚠️ 摄像头已在运行中")
                return jsonify({'error': '摄像头已在运行中'}), 400

            # 确保之前的资源已清理
            if camera_capture is not None:
                camera_capture.release()
                camera_capture = None

            # 初始化摄像头
            print("📷 正在初始化摄像头...")
            camera_capture = cv2.VideoCapture(0)
            if not camera_capture.isOpened():
                print("❌ 无法打开摄像头")
                return jsonify({'error': '无法打开摄像头，请检查摄像头连接'}), 500

            # 设置摄像头参数（见顶部 CAMERA_CAPTURE_SETTINGS）
            camera_capture.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_CAPTURE_SETTINGS["width"])
            camera_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_CAPTURE_SETTINGS["height"])
            camera_capture.set(cv2.CAP_PROP_FPS, CAMERA_CAPTURE_SETTINGS["fps"])
            camera_capture.set(cv2.CAP_PROP_BUFFERSIZE, CAMERA_CAPTURE_SETTINGS["buffersize"])

            camera_active = True
            print("✅ 摄像头启动成功")

            return jsonify({
                'success': True,
                'message': '摄像头已启动',
                'session_id': str(uuid.uuid4()),
                'model_id': model_id
            })

        except Exception as e:
            print(f"❌ 启动摄像头失败: {e}")
            # 确保出错时清理状态
            camera_active = False
            if camera_capture is not None:
                camera_capture.release()
                camera_capture = None
            return jsonify({'error': f'启动摄像头失败: {str(e)}'}), 500

@app.route('/api/camera/stop', methods=['POST'])
def stop_camera():
    """停止摄像头并释放所有相关资源（线程、capture、回收内存等）。

    该函数按步骤执行：
    1) 标记 `camera_active=False`，立即阻断新请求进入检测流程；
    2) 等待短暂时间以让正在运行的检测请求自然结束；
    3) 释放摄像头硬件句柄 `camera_capture`；
    4) 停止并 join 摄像头线程（如果存在）；
    5) 触发垃圾回收并清理 OpenCV 窗口资源。

    通过这些步骤尽量确保在各种异常情况下也能正确释放资源，避免摄像头被占用。
    """
    global camera_active, camera_thread, camera_capture, camera_last_save_time

    print("=" * 60)
    print("🛑 [停止摄像头] 开始执行停止流程...")
    print("=" * 60)

    with camera_lock:  # 使用锁防止并发问题
        try:
            # 第一步：立即设置停止标志（最高优先级）
            camera_active = False
            print("✅ [步骤1] 摄像头停止标志已设置: camera_active = False")

            # 第二步：等待短暂时间，让正在处理的请求完成
            time.sleep(0.3)
            print("⏱️ [步骤2] 等待飞行中的请求完成...")

            # 第三步：强制释放摄像头硬件资源
            if camera_capture is not None:
                try:
                    if camera_capture.isOpened():
                        camera_capture.release()
                        print("✅ [步骤3] 摄像头硬件已释放")
                    else:
                        print("ℹ️ [步骤3] 摄像头已经是关闭状态")
                except Exception as e:
                    print(f"⚠️ [步骤3] 释放摄像头时出错: {e}")
                finally:
                    camera_capture = None
                    print("✅ [步骤3] camera_capture 已设置为 None")
            else:
                print("ℹ️ [步骤3] camera_capture 已经是 None")

            # 第四步：停止并清理线程
            if camera_thread is not None:
                try:
                    if camera_thread.is_alive():
                        print("⏳ [步骤4] 等待摄像头线程结束...")
                        camera_thread.join(timeout=5)  # 给予足够的时间

                        if camera_thread.is_alive():
                            print("⚠️ [步骤4] 线程仍在运行，强制标记为None")
                        else:
                            print("✅ [步骤4] 线程已正常结束")
                    else:
                        print("ℹ️ [步骤4] 线程已经结束")

                    camera_thread = None
                    print("✅ [步骤4] camera_thread 已设置为 None")
                except Exception as e:
                    print(f"⚠️ [步骤4] 停止线程时出错: {e}")
                    camera_thread = None
            else:
                print("ℹ️ [步骤4] camera_thread 已经是 None")

            # 第五步：强制垃圾回收，释放所有相关资源
            try:
                import gc
                collected = gc.collect()
                print(f"✅ [步骤5] 垃圾回收完成，清理了 {collected} 个对象")
            except Exception as e:
                print(f"⚠️ [步骤5] 垃圾回收出错: {e}")

            # 第六步：OpenCV额外清理
            try:
                cv2.destroyAllWindows()
                print("✅ [步骤6] OpenCV窗口已清理")
            except:
                pass

            # === 步骤7: 重置保存时间 ===
            camera_last_save_time = 0

            print("=" * 60)
            print("✅ [完成] 摄像头已完全停止，所有资源已释放")
            print("=" * 60)

            return jsonify({
                'success': True,
                'message': '摄像头已停止'
            })

        except Exception as e:
            print(f"❌ [错误] 停止摄像头失败: {e}")
            import traceback
            traceback.print_exc()

            # 即使出错也要强制重置所有状态
            camera_active = False
            camera_capture = None
            camera_thread = None
            camera_last_save_time = 0  # 重置保存时间
            print("⚠️ [恢复] 已强制重置所有状态")

            return jsonify({'error': f'停止摄像头失败: {str(e)}'}), 500

@app.route('/api/camera/frame', methods=['GET'])
def get_camera_frame():
    """读取当前摄像头帧、执行推理并返回检测结果与压缩后的图像（base64）。

    注意：该接口同步执行一次推理（阻塞请求），因此应在前端控制调用频率或使用队列/流式处理。
    返回结构包含 `detection_time`, `results` 和 `result_image`（base64 jpg）。
    """
    global camera_active, camera_capture, camera_last_save_time

    try:
        if not camera_active:
            return jsonify({'error': '摄像头未启动'}), 400

        # 使用当前 active_model_id（和启动摄像头时选择一致）
        model, err = get_model(active_model_id)
        if err:
            return jsonify({'error': err}), 500

        if camera_capture is None or not camera_capture.isOpened():
            return jsonify({'error': '摄像头连接已断开'}), 500

        ret, frame = camera_capture.read()

        if not ret:
            return jsonify({'error': '无法读取摄像头画面'}), 500

        # 执行检测 - 自动选择设备，优化参数减少误检
        t0 = time.time()
        device = "cuda" if hasattr(model, 'device') and 'cuda' in str(model.device) else "cpu"
        # ✅ 关键可调：摄像头推理参数（见顶部 PREDICT_CAMERA）
        results = model.predict(
            frame,
            device=device,
            imgsz=PREDICT_CAMERA["imgsz"],
            conf=PREDICT_CAMERA["conf"],
            iou=PREDICT_CAMERA["iou"],
            verbose=False
        )
        detection_time = (time.time() - t0) * 1000

        # 处理结果
        vis, info = process_detection_result(results)

        # === 仅保存检测到对象的记录（避免无用数据）===
        current_time = time.time()
        should_save = False

        # 🎯 只在检测到对象时保存（至少间隔N秒，避免重复保存）
        if info["count"] > 0 and current_time - camera_last_save_time >= CAMERA_DB_SAVE_INTERVAL_SEC:
            should_save = True

        if should_save:
            try:
                # 生成唯一session_id
                session_id = str(uuid.uuid4())

                # 保存到数据库（摄像头API运行在Flask请求上下文中，无需app_context）
                detection = Detection(
                    session_id=session_id,
                    original_filename="camera_capture.jpg",
                    file_path=f"camera_{session_id}.jpg",  # 虚拟路径
                    result_path=None,
                    file_type='camera',
                    file_size=0,  # 摄像头画面不计算大小
                    detection_time=detection_time,
                    object_count=info["count"],
                    main_class=info["main"] if info["main"] != "-" else None,
                    confidence=info["conf"],
                    bbox_x1=info["xyxy"][0],
                    bbox_y1=info["xyxy"][1],
                    bbox_x2=info["xyxy"][2],
                    bbox_y2=info["xyxy"][3]
                )
                db.session.add(detection)
                db.session.commit()

                # 更新上次保存时间
                camera_last_save_time = current_time
                print(f"✅ 摄像头检测已保存[{active_model_id}]: {session_id}, 对象数: {info['count']}")
            except Exception as db_error:
                print(f"❌ 保存摄像头检测记录失败: {db_error}")
                try:
                    db.session.rollback()
                except:
                    pass
                # 继续执行，不影响检测

        # 优化图像编码 - 降低质量以减少传输时间
        result_image_b64 = None
        if vis is not None:
            # 调整图像大小以减少传输数据量
            height, width = vis.shape[:2]
            if width > 640:
                scale = 640 / width
                new_width = 640
                new_height = int(height * scale)
                vis = cv2.resize(vis, (new_width, new_height))

            # 使用更高压缩率
            encode_params = [cv2.IMWRITE_JPEG_QUALITY, 75]
            _, buffer = cv2.imencode('.jpg', vis, encode_params)
            result_image_b64 = base64.b64encode(buffer).decode('utf-8')

        return jsonify({
            'success': True,
            'model_id': active_model_id,
            'detection_time': round(detection_time, 2),
            'results': {
                'object_count': info["count"],
                'main_class': info["main"],
                'confidence': round(info["conf"], 3),
                'bbox': {
                    'x1': info["xyxy"][0],
                    'y1': info["xyxy"][1],
                    'x2': info["xyxy"][2],
                    'y2': info["xyxy"][3]
                } if info["xyxy"][0] is not None else None
            },
            'result_image': result_image_b64
        })

    except Exception as e:
        return jsonify({'error': f'获取摄像头画面失败: {str(e)}'}), 500

@app.route('/api/history', methods=['GET'])
def get_history():
    """获取检测历史 - 修复版本"""
    try:
        print("\n" + "="*60)
        print("📋 [API] 开始获取历史记录...")
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)

        print(f"📄 [API] 请求参数: page={page}, per_page={per_page}")

        # 检查数据库连接
        try:
            total_count = Detection.query.count()
            print(f"📊 数据库中总记录数: {total_count}")
        except Exception as db_error:
            print(f"❌ 数据库连接错误: {db_error}")
            return jsonify({'error': f'数据库连接失败: {str(db_error)}'}), 500

        # 如果没有记录，直接返回空结果
        if total_count == 0:
            print("📭 没有历史记录")
            return jsonify({
                'success': True,
                'data': [],
                'pagination': {
                    'page': 1,
                    'per_page': per_page,
                    'total': 0,
                    'pages': 0
                }
            })

        # 查询分页数据
        try:
            detections = Detection.query.order_by(Detection.created_at.desc()).paginate(
                page=page, per_page=per_page, error_out=False
            )

            print(f"📋 查询到 {len(detections.items)} 条记录")

            # 转换为字典格式
            data = []
            for d in detections.items:
                try:
                    data.append(d.to_dict())
                except Exception as convert_error:
                    print(f"⚠️ 转换记录时出错: {convert_error}")
                    continue

            result = {
                'success': True,
                'data': data,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': detections.total,
                    'pages': detections.pages
                }
            }

            print(f"✅ 历史记录获取成功: {len(data)} 条记录")
            return jsonify(result)

        except Exception as query_error:
            print(f"❌ 查询数据时出错: {query_error}")
            return jsonify({'error': f'查询数据失败: {str(query_error)}'}), 500

    except Exception as e:
        print(f"❌ 获取历史记录失败: {e}")
        return jsonify({'error': f'获取历史失败: {str(e)}'}), 500

@app.route('/api/detection/<session_id>', methods=['GET'])
def get_detection(session_id):
    """获取单个检测记录"""
    try:
        detection = Detection.query.filter_by(session_id=session_id).first()
        if not detection:
            return jsonify({'error': '检测记录不存在'}), 404

        return jsonify({
            'success': True,
            'data': detection.to_dict()
        })
    except Exception as e:
        return jsonify({'error': f'获取检测记录失败: {str(e)}'}), 500

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """获取增强版统计信息"""
    try:
        from datetime import timedelta, date
        from sqlalchemy import func

        # ========== 基础统计 ==========
        total_detections = Detection.query.count()

        # 今日检测数量
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_detections = Detection.query.filter(Detection.created_at >= today_start).count()

        # 最近7天的检测数量
        week_ago = datetime.now() - timedelta(days=7)
        recent_detections = Detection.query.filter(Detection.created_at >= week_ago).count()

        # ========== 类型统计 ==========
        # 图片检测数量
        image_detections = Detection.query.filter(Detection.file_type == 'image').count()
        # 视频检测数量
        video_detections = Detection.query.filter(Detection.file_type == 'video').count()
        # 摄像头检测数量
        camera_detections = Detection.query.filter(Detection.file_type == 'camera').count()

        # ========== 成功率统计 ==========
        # 检测成功数（有检测到对象的）
        success_detections = Detection.query.filter(Detection.object_count > 0).count()
        success_rate = round((success_detections / total_detections * 100), 1) if total_detections > 0 else 0

        # ========== 类别排行 ==========
        top_classes = db.session.query(
            Detection.main_class,
            func.count(Detection.main_class).label('count')
        ).filter(Detection.main_class.isnot(None)).group_by(Detection.main_class).order_by(
            func.count(Detection.main_class).desc()
        ).limit(5).all()

        # ========== 每日趋势（最近7天） ==========
        daily_stats = []
        for i in range(6, -1, -1):  # 倒序，从7天前到今天
            day_start = today_start - timedelta(days=i)
            day_end = day_start + timedelta(days=1)
            day_count = Detection.query.filter(
                Detection.created_at >= day_start,
                Detection.created_at < day_end
            ).count()
            daily_stats.append({
                'date': day_start.strftime('%m-%d'),
                'count': day_count
            })

        # ========== 最高置信度检测 ==========
        highest_conf_detection = Detection.query.filter(
            Detection.confidence > 0
        ).order_by(Detection.confidence.desc()).first()

        highest_confidence = {
            'class': highest_conf_detection.main_class if highest_conf_detection else '-',
            'confidence': round(highest_conf_detection.confidence * 100, 1) if highest_conf_detection else 0
        }

        return jsonify({
            'success': True,
            'stats': {
                # 基础数据
                'total_detections': total_detections,
                'today_detections': today_detections,
                'recent_detections': recent_detections,

                # 类型分布
                'image_detections': image_detections,
                'video_detections': video_detections,
                'camera_detections': camera_detections,

                # 成功率
                'success_detections': success_detections,
                'success_rate': success_rate,

                # 排行榜
                'top_classes': [{'class': cls, 'count': count} for cls, count in top_classes],
                'highest_confidence': highest_confidence,

                # 趋势数据
                'daily_trend': daily_stats
            }
        })
    except Exception as e:
        return jsonify({'error': f'获取统计信息失败: {str(e)}'}), 500

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """提供上传文件访问"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/results/<filename>')
def result_file(filename):
    """提供结果文件访问"""
    return send_from_directory(app.config['RESULT_FOLDER'], filename)

# ==================== 错误处理 ====================
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': '页面未找到'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': '服务器内部错误'}), 500

@app.errorhandler(413)
def too_large(error):
    return jsonify({'error': '文件处理失败，请检查文件格式'}), 413

# ==================== 初始化 ====================
def init_app():
    """初始化应用"""
    with app.app_context():
        # 创建数据库表
        db.create_all()

        # 加载默认模型（预热，可选）
        if not load_model():
            print("⚠️ 警告: 模型加载失败，请检查 MODELS 配置中的路径")

        print("🚀 Web应用初始化完成!")

if __name__ == '__main__':
    init_app()
    print("🌐 启动Web服务器...")
    print("📱 访问地址: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
