@echo off
chcp 65001 >nul
echo 🔧 手动安装Web版本依赖包
echo ================================
echo.

echo 📦 正在安装Flask...
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple Flask
if %errorlevel% neq 0 (
    echo ❌ Flask安装失败
    pause
    exit /b 1
)

echo 📦 正在安装Flask-SQLAlchemy...
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple Flask-SQLAlchemy
if %errorlevel% neq 0 (
    echo ❌ Flask-SQLAlchemy安装失败
    pause
    exit /b 1
)

echo 📦 正在安装Flask-CORS...
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple Flask-CORS
if %errorlevel% neq 0 (
    echo ❌ Flask-CORS安装失败
    pause
    exit /b 1
)

echo 📦 正在安装SQLAlchemy...
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple SQLAlchemy
if %errorlevel% neq 0 (
    echo ❌ SQLAlchemy安装失败
    pause
    exit /b 1
)

echo 📦 正在安装Werkzeug...
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple Werkzeug
if %errorlevel% neq 0 (
    echo ❌ Werkzeug安装失败
    pause
    exit /b 1
)

echo 📦 正在安装python-dotenv...
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple python-dotenv
if %errorlevel% neq 0 (
    echo ❌ python-dotenv安装失败
    pause
    exit /b 1
)

echo.
echo ✅ 所有依赖包安装完成！
echo 🚀 现在可以运行 python start_web.py 启动Web应用了
echo.
pause
