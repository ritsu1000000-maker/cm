@echo off
chcp 65001 >nul
cd /d "%~dp0"
if exist "console.env" (
  type console.env
) else (
  echo console.env がありません。setup.bat を実行してください。
)
pause
