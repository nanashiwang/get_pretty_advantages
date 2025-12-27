@echo off
echo 正在修复conda环境...
echo.

echo 步骤1: 删除不完整的环境...
conda env remove -n user_registration -y

echo.
echo 步骤2: 重新创建环境...
conda env create -f environment.yml

echo.
echo 环境修复完成！
echo 请执行以下命令激活环境：
echo   conda activate user_registration
echo   uvicorn app.main:app --reload
echo.
pause

