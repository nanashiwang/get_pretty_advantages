@echo off
cd /d "%~dp0"
echo 当前目录: %CD%
echo.
echo 启动FastAPI应用...
echo.
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
pause

