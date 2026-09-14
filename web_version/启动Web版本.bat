@echo off
chcp 65001 >nul
echo 🚦 智能交通标志检测系统 - Web版本启动器
echo ================================================
echo.

:: 检查是否在正确的目录
if not exist "web_app.py" (
    echo ❌ 错误: 未找到 web_app.py 文件
    echo 💡 请确保在 web_version 文件夹内运行此脚本
    echo.
    pause
    exit /b 1
)

echo 📍 当前目录: %CD%
echo 🔍 检测到 Web 版本文件...
echo.

:: 启动 Python 脚本
echo 🚀 启动 Web 应用...
python start_web.py

echo.
echo 👋 程序已退出
pause
