#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🚦 智能交通标志检测系统 - Web版本配置文件
集中管理所有配置选项
"""

import os
from pathlib import Path

class Config:
    """基础配置类"""
    
    # ==================== 应用配置 ====================
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'yolo11-traffic-detection-2024'
    
    # ==================== 数据库配置 ====================
    # SQLite (默认)
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///traffic_detection.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # 数据库连接池配置
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'pool_recycle': 120,
        'pool_pre_ping': True,
        'pool_timeout': 20
    }
    
    # ==================== 文件上传配置 ====================
    # 上传文件夹
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or 'uploads'
    RESULT_FOLDER = os.environ.get('RESULT_FOLDER') or 'results'
    
    # 文件大小限制 (50MB)
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_FILE_SIZE', 50 * 1024 * 1024))
    
    # 允许的文件类型
    ALLOWED_EXTENSIONS = {
        'image': {'png', 'jpg', 'jpeg', 'gif', 'bmp'},
        'video': {'mp4', 'avi', 'mov', 'mkv', 'wmv', 'flv'}
    }
    
    # ==================== YOLO模型配置 ====================
    # 模型文件路径 - 请修改为您的实际路径
    MODEL_PATH = os.environ.get('MODEL_PATH') or r"<LOCAL_PATH>"
    
    # 检测参数
    DETECTION_CONFIG = {
        'imgsz': int(os.environ.get('YOLO_IMGSZ', 640)),      # 输入图像尺寸
        'conf': float(os.environ.get('YOLO_CONF', 0.3)),      # 置信度阈值
        'iou': float(os.environ.get('YOLO_IOU', 0.5)),        # NMS IoU阈值
        'device': os.environ.get('YOLO_DEVICE', 'cpu'),       # 设备: cpu/cuda
        'verbose': False                                       # 是否显示详细信息
    }
    
    # ==================== 服务器配置 ====================
    # Flask服务器配置
    HOST = os.environ.get('FLASK_HOST', '0.0.0.0')
    PORT = int(os.environ.get('FLASK_PORT', 5000))
    DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    
    # ==================== 安全配置 ====================
    # CORS配置
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*').split(',')
    
    # 请求限制
    RATELIMIT_STORAGE_URL = os.environ.get('RATELIMIT_STORAGE_URL', 'memory://')
    
    # ==================== 日志配置 ====================
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = os.environ.get('LOG_FILE', 'app.log')
    
    # ==================== 缓存配置 ====================
    CACHE_TYPE = os.environ.get('CACHE_TYPE', 'simple')
    CACHE_DEFAULT_TIMEOUT = int(os.environ.get('CACHE_TIMEOUT', 300))

class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///dev_traffic_detection.db'

class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False
    
    # 生产环境建议使用PostgreSQL或MySQL
    # SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
    #     'postgresql://user:password@localhost/traffic_detection'
    
    # 安全配置
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        raise ValueError("生产环境必须设置SECRET_KEY环境变量")
    
    # 文件存储 (生产环境建议使用云存储)
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', '/var/www/uploads')
    RESULT_FOLDER = os.environ.get('RESULT_FOLDER', '/var/www/results')

class TestingConfig(Config):
    """测试环境配置"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False

# 配置字典
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

def get_config():
    """获取当前配置"""
    env = os.environ.get('FLASK_ENV', 'development')
    return config.get(env, config['default'])

# ==================== 配置验证函数 ====================
def validate_config(config_obj):
    """验证配置的有效性"""
    errors = []
    
    # 检查模型文件
    if not os.path.exists(config_obj.MODEL_PATH):
        errors.append(f"模型文件不存在: {config_obj.MODEL_PATH}")
    
    # 检查上传文件夹
    for folder in [config_obj.UPLOAD_FOLDER, config_obj.RESULT_FOLDER]:
        if not os.path.exists(folder):
            try:
                os.makedirs(folder, exist_ok=True)
            except Exception as e:
                errors.append(f"无法创建文件夹 {folder}: {e}")
    
    # 检查检测参数
    detection_config = config_obj.DETECTION_CONFIG
    if not (0 < detection_config['conf'] < 1):
        errors.append("置信度阈值必须在0-1之间")
    
    if not (0 < detection_config['iou'] < 1):
        errors.append("IoU阈值必须在0-1之间")
    
    if detection_config['imgsz'] <= 0:
        errors.append("图像尺寸必须大于0")
    
    return errors

# ==================== 环境变量示例 ====================
"""
# 创建 .env 文件来设置环境变量

# 基础配置
FLASK_ENV=development
SECRET_KEY=your-secret-key-here

# 数据库配置
DATABASE_URL=sqlite:///traffic_detection.db

# 模型配置
MODEL_PATH=/path/to/your/best.pt
YOLO_DEVICE=cuda
YOLO_CONF=0.3
YOLO_IOU=0.5
YOLO_IMGSZ=640

# 服务器配置
FLASK_HOST=0.0.0.0
FLASK_PORT=5000
FLASK_DEBUG=True

# 文件配置
UPLOAD_FOLDER=uploads
RESULT_FOLDER=results
MAX_FILE_SIZE=52428800

# 安全配置
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=app.log
"""
