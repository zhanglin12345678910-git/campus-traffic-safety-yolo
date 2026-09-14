@echo off
chcp 65001 >nul
echo ========================================
echo 🚀 启动多模型检测系统
echo ========================================
echo.

cd /d "%~dp0"

echo 📂 当前目录: %CD%
echo.

echo 🔍 检查Python环境...
python --version
if errorlevel 1 (
    echo ❌ 未找到Python，请先安装Python 3.8+
    pause
    exit /b 1
)
echo.

echo 📦 检查必要的依赖包...
pip show flask >nul 2>&1
if errorlevel 1 (
    echo ⚠️ Flask未安装，正在安装依赖...
    pip install -r requirements_web.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
) else (
    echo ✅ 依赖包已安装
)
echo.

echo 🎯 配置的模型列表:
echo   1. 🏆 PSSM-YOLO (自研改进) - 默认
echo   2. ⚡ YOLOv11n (超轻量)
echo   3. 🎯 YOLOv10n (实时检测)
echo   4. 🚀 YOLOv9t (高精度)
echo   5. 💎 YOLOv8n (经典)
echo   6. ⚙️ YOLOv7-tiny (紧凑)
echo   7. 🔧 YOLOv5n (稳定)
echo   8. 🤖 YOLO-NAS-s (神经架构搜索)
echo   9. 🎪 RT-DETR (实时检测器)
echo  10. 💨 YOLO-FastestV2 (极速)
echo  11. 🐼 PP-YOLOE+ (PaddlePaddle)
echo.

echo 🌐 启动Web服务器...
echo 📱 访问地址: http://localhost:5000
echo 💡 提示: 在浏览器中打开上述地址即可使用
echo ⚠️ 按 Ctrl+C 可停止服务
echo.
echo ========================================
echo.

python web_app.py

pause
