@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Discord Bot Virtual CMD

if not exist "console.env" (
  echo 初回は setup.bat を実行してください。
  pause
  exit /b 1
)

docker compose up -d
if errorlevel 1 (
  echo 起動に失敗しました。
  pause
  exit /b 1
)

echo.
echo Virtual CMD:
echo   http://127.0.0.1:7681
echo Bot Upload:
echo   http://127.0.0.1:7682
echo.
start "" "http://127.0.0.1:7682"
start "" "http://127.0.0.1:7681"
