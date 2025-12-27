@echo off
echo 激活conda环境并启动应用...
call conda activate user_registration
if errorlevel 1 (
    echo 错误：无法激活conda环境，请先创建环境
    echo 执行: conda env create -f environment.yml
    pause
    exit /b 1
)

echo 启动FastAPI应用...
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
pause

