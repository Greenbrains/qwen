@echo off
chcp 65001 >nul
title miniB-Agent v1.0

REM ============================================================
REM  miniB-Agent — универсальный лаунчер
REM
REM  Варианты запуска:
REM    start.bat              меню выбора режима
REM    start.bat cli          консольный чат
REM    start.bat api          API-сервер (порт 8000)
REM    start.bat api 9000     API-сервер на порту 9000
REM    start.bat web          веб-интерфейс (откроет браузер)
REM    start.bat web 3000     веб-интерфейс на порту 3000
REM ============================================================

set PYTHON_PATH=C:\Users\igor.sobolev\AppData\Local\Programs\Python\Python313\python.exe

REM Если точный путь не найден — ищем python в PATH
if not exist "%PYTHON_PATH%" (
    where python >nul 2>&1
    if errorlevel 1 (
        echo ❌ Python не найден. Установи Python 3.13 или пропиши путь в start.bat
        pause
        exit /b 1
    )
    set PYTHON_PATH=python
)

REM Всегда работаем из папки скрипта (важно для .env и .agents)
cd /d "%~dp0"

REM ---------- Прямой запуск с аргументами ----------
if /i "%~1"=="cli" goto :run_cli
if /i "%~1"=="api" goto :run_api
if /i "%~1"=="web" goto :run_web

REM ---------- Интерактивное меню ----------
:menu
cls
echo ============================================================
echo  🧳 Tutu Travel Agent v1.0 (miniB)
echo ============================================================
echo.
echo   [1] CLI  — консольный чат (рекомендуется)
echo   [2] API  — FastAPI сервер   http://127.0.0.1:8001
echo   [3] WEB  — веб-интерфейс    (откроется браузер)
echo   [0] Выход
echo.
set /p choice="  Ваш выбор: "

if "%choice%"=="1" goto :run_cli
if "%choice%"=="2" goto :run_api
if "%choice%"=="3" goto :run_web
if "%choice%"=="0" exit /b 0
goto :menu

REM ---------- Режимы ----------
:run_cli
echo.
echo 🚀 Запуск консольного режима...
echo ------------------------------------------------------------
"%PYTHON_PATH%" main.py --mode cli
goto :end

:run_api
set PORT=%~2
if "%PORT%"=="" set PORT=8000
echo.
echo 🚀 Запуск API-сервера на порту %PORT%...
echo    Docs: http://127.0.0.1:%PORT%/docs
echo ------------------------------------------------------------
"%PYTHON_PATH%" main.py --mode api --port %PORT%
goto :end

:run_web
set PORT=%~2
if "%PORT%"=="" set PORT=8000
echo.
echo 🚀 Запуск веб-интерфейса на порту %PORT%...
timeout /t 2 /nobreak >nul
start "" "http://127.0.0.1:%PORT%"
"%PYTHON_PATH%" main.py --mode web --port %PORT%
goto :end

:end
if errorlevel 1 (
    echo.
    echo ❌ Ошибка выполнения (код %errorlevel%)
    pause
)