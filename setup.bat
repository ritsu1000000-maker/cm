@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Discord Bot Virtual CMD Setup

where docker >nul 2>nul
if errorlevel 1 (
  echo Docker が見つかりません。
  echo Docker Desktop をインストールしてから再実行してください。
  pause
  exit /b 1
)

docker compose version >nul 2>nul
if errorlevel 1 (
  echo docker compose が利用できません。
  pause
  exit /b 1
)

if not exist "console.env" (
  for /f %%P in ('powershell -NoProfile -Command "[guid]::NewGuid().ToString('N')"') do set "GENPASS=%%P"
  >"console.env" echo WEB_USER=admin
  >>"console.env" echo WEB_PASSWORD=%GENPASS%
  echo.
  echo Web CMD ログインを生成しました。
  echo ユーザー名: admin
  echo パスワード: %GENPASS%
  echo console.env に保存されています。
  echo.
)

if not exist "workspace\.env" copy /y "workspace\.env.example" "workspace\.env" >nul
if not exist "workspace\bot.config" copy /y "workspace\bot.config.example" "workspace\bot.config" >nul

echo Dockerイメージを構築します...
docker compose build
if errorlevel 1 (
  echo ビルドに失敗しました。
  pause
  exit /b 1
)

echo.
echo セットアップ完了。
echo 次は start.bat を実行してください。
pause
