# 🚦 智能交通标志检测系统 - Web版本

基于YOLO11的现代化Web应用，提供高精度、实时的交通标志识别服务。

## ✨ 特性

- 🎯 **高精度检测**: 基于YOLO11算法，智能识别精准检测
- 🚀 **实时处理**: 毫秒级响应速度，支持图片和视频检测
- 💾 **数据管理**: 完整的检测历史记录和统计分析
- 🎨 **现代UI**: 响应式设计，支持桌面和移动设备
- 📊 **可视化**: 丰富的图表和统计数据展示
- 🔒 **安全可靠**: 文件类型验证，大小限制，错误处理

## 🏗️ 技术架构

### 后端
- **框架**: Flask + SQLAlchemy
- **数据库**: SQLite (可扩展到MySQL/PostgreSQL)
- **AI引擎**: YOLO11 (Ultralytics)
- **图像处理**: OpenCV + PIL

### 前端
- **技术**: HTML5 + CSS3 + JavaScript (原生)
- **设计**: 现代化渐变UI，响应式布局
- **交互**: 拖拽上传，实时预览，动画效果

## 📦 安装部署

### 1. 环境要求
```bash
Python >= 3.8
pip >= 21.0
```

### 2. 克隆项目
```bash
git clone <your-repo-url>
cd ultralytics-yolo11-main
```

### 3. 安装依赖
```bash
# 安装Web版本依赖
pip install -r requirements_web.txt

# 如果需要GPU支持，额外安装
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

### 4. 配置模型路径
编辑 `web_app.py` 文件，修改模型路径：
```python
MODEL_PATH = r"your/path/to/best.pt"  # 修改为您的权重文件路径
```

### 5. 启动应用
```bash
# 开发模式
python web_app.py

# 生产模式 (推荐)
gunicorn -w 4 -b 0.0.0.0:5000 web_app:app
```

### 6. 访问应用
打开浏览器访问: http://localhost:5000

## 🚀 快速开始

### 1. 上传文件
- 支持拖拽上传或点击选择
- 支持格式: JPG, PNG, GIF, BMP, MP4, AVI, MOV, MKV
- 文件大小限制: 50MB

### 2. 开始检测
- 选择文件后点击"开始检测"
- AI会自动分析并返回结果
- 实时显示检测进度

### 3. 查看结果
- 检测用时和置信度
- 目标数量和主要类别
- 边界框坐标信息
- 可下载结果图片

### 4. 历史记录
- 查看所有检测历史
- 分页浏览和搜索
- 详细的检测信息

### 5. 统计分析
- 系统使用统计
- 热门检测类别
- 趋势分析图表

## 📁 项目结构

```
ultralytics-yolo11-main/
├── web_app.py              # Flask主应用
├── app.py                  # PyQt5桌面版本(保持不变)
├── requirements_web.txt    # Web版本依赖
├── README_Web.md          # Web版本说明
├── templates/             # HTML模板
│   └── index.html        # 主页面
├── static/               # 静态资源
│   ├── css/
│   │   └── style.css    # 样式文件
│   ├── js/
│   │   └── app.js       # JavaScript逻辑
│   └── images/          # 图片资源
├── uploads/              # 上传文件存储(自动创建)
├── results/              # 检测结果存储(自动创建)
└── traffic_detection.db  # SQLite数据库(自动创建)
```

## 🔧 配置选项

### 数据库配置
```python
# SQLite (默认)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///traffic_detection.db'

# MySQL
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://user:password@localhost/dbname'

# PostgreSQL
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://user:password@localhost/dbname'
```

### 文件上传配置
```python
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['RESULT_FOLDER'] = 'results'
```

### YOLO模型配置
```python
# 检测参数
imgsz = 640      # 输入图像尺寸
conf = 0.3       # 置信度阈值
iou = 0.5        # NMS IoU阈值
device = "cpu"   # 设备选择: "cpu" 或 "cuda"
```

## 🌐 API文档

### 健康检查
```http
GET /api/health
```

### 图片检测
```http
POST /api/detect/image
Content-Type: multipart/form-data

参数:
- file: 图片文件

返回:
{
  "success": true,
  "session_id": "uuid",
  "detection_time": 123.45,
  "results": {
    "object_count": 2,
    "main_class": "stop_sign",
    "confidence": 0.95,
    "bbox": {"x1": 100, "y1": 50, "x2": 200, "y2": 150}
  },
  "result_image": "base64_encoded_image"
}
```

### 检测历史
```http
GET /api/history?page=1&per_page=10
```

### 统计信息
```http
GET /api/stats
```

## 🔍 故障排除

### 常见问题

1. **模型加载失败**
   - 检查模型文件路径是否正确
   - 确认模型文件存在且可读
   - 检查ultralytics版本兼容性

2. **文件上传失败**
   - 检查文件格式是否支持
   - 确认文件大小不超过50MB
   - 检查uploads文件夹权限

3. **检测速度慢**
   - 考虑使用GPU加速
   - 调整图像输入尺寸(imgsz)
   - 优化服务器配置

4. **数据库错误**
   - 检查数据库文件权限
   - 确认SQLAlchemy版本兼容
   - 重新初始化数据库

### 性能优化

1. **GPU加速**
```python
# 修改web_app.py中的device参数
device = "cuda"  # 需要NVIDIA GPU和CUDA
```

2. **生产部署**
```bash
# 使用Gunicorn
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 web_app:app

# 使用Nginx反向代理
# 配置nginx.conf
```

3. **数据库优化**
```python
# 使用连接池
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_size': 10,
    'pool_recycle': 120,
    'pool_pre_ping': True
}
```

## 📊 系统监控

### 日志记录
```python
import logging
logging.basicConfig(level=logging.INFO)
```

### 性能指标
- 检测用时统计
- 文件上传速度
- 数据库查询性能
- 内存使用情况

## 🤝 贡献指南

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🙏 致谢

- [Ultralytics YOLO](https://github.com/ultralytics/ultralytics) - 强大的目标检测框架
- [Flask](https://flask.palletsprojects.com/) - 轻量级Web框架
- [OpenCV](https://opencv.org/) - 计算机视觉库

## 📞 联系方式

如有问题或建议，请通过以下方式联系：

- 📧 Email: your-email@example.com
- 🐛 Issues: [GitHub Issues](https://github.com/your-repo/issues)
- 💬 Discussions: [GitHub Discussions](https://github.com/your-repo/discussions)

---

⭐ 如果这个项目对您有帮助，请给它一个星标！
