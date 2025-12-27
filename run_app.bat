@echo off
echo 启动FastAPI应用...
echo 注意：当前使用base环境运行
echo.
echo 使用uvicorn启动（推荐方式）...
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
pause

