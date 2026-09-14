@echo off
chcp 65001 >nul
echo 🔧 配置pip国内镜像源
echo ================================

:: 创建pip配置目录
if not exist "%APPDATA%\pip" mkdir "%APPDATA%\pip"

:: 创建pip.ini配置文件
echo [global] > "%APPDATA%\pip\pip.ini"
echo index-url = https://pypi.tuna.tsinghua.edu.cn/simple >> "%APPDATA%\pip\pip.ini"
echo trusted-host = pypi.tuna.tsinghua.edu.cn >> "%APPDATA%\pip\pip.ini"
echo timeout = 300 >> "%APPDATA%\pip\pip.ini"
echo retries = 5 >> "%APPDATA%\pip\pip.ini"

echo ✅ pip镜像源配置完成！
echo 📍 配置文件位置: %APPDATA%\pip\pip.ini
echo 🌐 使用清华大学镜像源
echo.
echo 现在可以正常使用 pip install 命令了
pause
