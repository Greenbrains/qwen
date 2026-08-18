@echo off
chcp 65001 >nul
title Multi-Agent v2.3
echo ==========
echo   Запуск Multi-Agent
echo ==========

:: Переходим в директорию скрипта, чтобы контекст был верным
cd /d "%~dp0"

set PYTHON_PATH=C:\Users\igor.sobolev\AppData\Local\Programs\Python\Python313\python.exe

:: Устанавливаем PYTHONPATH для гарантии корректных импортов
set PYTHONPATH=%~dp0;%PYTHONPATH%

:: Запуск через -m гарантирует, что корневая папка будет в sys.path
:: и импорты вида "from config import ..." сработают корректно
"%PYTHON_PATH%" -m interfaces.cli %*

echo.
echo ==========
echo  Завершено. Нажмите любую клавишу...
pause >nul