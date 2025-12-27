@echo off
echo 正在创建conda虚拟环境...
conda env create -f environment.yml

echo.
echo 环境创建完成！请执行以下命令激活环境并运行程序：
echo.
echo conda activate user_registration
echo uvicorn app.main:app --reload
echo.
pause

