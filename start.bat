@echo off
chcp 65001 >nul
title Multi-Agent v2.3

echo ==========
echo  🚀 Запуск Multi-Agent v2.3
echo ==========

set PYTHON_PATH=C:\Users\igor.sobolev\AppData\Local\Programs\Python\Python313\python.exe
%PYTHON_PATH% main.py %*