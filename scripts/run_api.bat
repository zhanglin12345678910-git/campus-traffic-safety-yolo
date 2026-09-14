@echo off
setlocal

if "%API_HOST%"=="" set API_HOST=127.0.0.1
if "%API_PORT%"=="" set API_PORT=8000
if "%PYTHON_EXE%"=="" set PYTHON_EXE=python

%PYTHON_EXE% -m uvicorn traffic_api.main:app --host %API_HOST% --port %API_PORT%
