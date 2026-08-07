@echo off
chcp 65001 >nul
cd /d "%~dp0"
docker compose stop
echo 停止しました。
pause
