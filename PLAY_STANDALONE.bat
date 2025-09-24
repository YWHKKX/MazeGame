@echo off
chcp 65001 > nul
title War for the Overworld - 独立版本启动器
color 0A

echo.
echo ================================================
echo    War for the Overworld - 独立版本启动器
echo ================================================
echo.
echo 🎮 正在启动独立Python版本...
echo 🔧 版本: 独立版 v1.0.0
echo.

:: 检查Python是否可用
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 未检测到Python环境
    echo.
    echo 🔧 请先安装Python:
    echo    1. 访问 https://python.org
    echo    2. 下载并安装Python 3.8+
    echo    3. 重新运行此脚本
    echo.
    pause
    goto :end
)

echo ✅ 检测到Python环境

:: 检查pygame是否安装
python -c "import pygame" >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 未检测到pygame库
    echo.
    echo 🔧 正在自动安装pygame...
    python -m pip install pygame
    
    if %errorlevel% neq 0 (
        echo ❌ pygame安装失败
        echo.
        echo 🔧 请手动安装:
        echo    pip install pygame
        echo.
        pause
        goto :end
    )
    
    echo ✅ pygame安装成功
)

echo ✅ 检测到pygame库

:: 检查游戏文件
if not exist "standalone_game.py" (
    echo ❌ 游戏文件不存在: standalone_game.py
    pause
    goto :end
)

echo ✅ 游戏文件检查通过
echo.

echo 🚀 启动独立游戏...
echo.
echo ================================================
echo                  🎮 游戏控制说明
echo ================================================
echo.
echo 🖱️  鼠标控制:
echo    - 左键: 执行建造/召唤
echo    - 右键: 取消建造模式
echo.
echo ⌨️  键盘控制:
echo    - 数字键 1: 挖掘模式
echo    - 数字键 2: 建造金库
echo    - 数字键 3: 建造巢穴
echo    - 数字键 4: 召唤小恶魔
echo    - 数字键 5: 召唤哥布林苦工
echo    - WASD: 移动相机
echo    - ESC: 取消建造模式
echo.
echo 🎯 游戏目标:
echo    - 挖掘地下城
echo    - 建造房间
echo    - 召唤怪物
echo    - 抵御英雄入侵
echo.
echo ================================================
echo.

:: 启动游戏
python standalone_game.py

echo.
echo 🎮 游戏已结束
echo.

:end
pause
