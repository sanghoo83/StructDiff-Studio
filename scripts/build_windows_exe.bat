@echo off
setlocal
cd /d "%~dp0.."

REM StructDiff Studio Windows build.
REM Optional native diff acceleration files:
REM   tools\windows\diff.exe
REM   tools\windows\msys-2.0.dll

python -m PyInstaller ^
  --onefile ^
  --windowed ^
  --name StructDiffStudio ^
  --add-data "assets\code_by_noah_logo.png;assets" ^
  --add-binary "tools\windows\diff.exe;tools\windows" ^
  --add-binary "tools\windows\msys-2.0.dll;tools\windows" ^
  src\structdiff_studio.py

echo.
echo Build complete. Check dist\StructDiffStudio.exe.
pause
