@echo off
echo 正在重置代理和DNS缓存...
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings" /v ProxyEnable /t REG_DWORD /d 0 /f
ipconfig /flushdns
echo 操作完成！请关闭所有浏览器再重新打开。
paused