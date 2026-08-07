@echo off
chcp 65001 >nul
cd /d "%~dp0"
docker compose restart
echo 再起動しました。
pause
