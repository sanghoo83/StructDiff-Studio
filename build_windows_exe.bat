@echo off
setlocal

REM StructDiff Studio Windows build.
REM Optional native diff acceleration files:
REM   tools\diff.exe
REM   tools\msys-2.0.dll

python -m PyInstaller ^
  --onefile ^
  --windowed ^
  --name StructDiffStudio ^
  --add-binary "tools\diff.exe;tools" ^
  --add-binary "tools\msys-2.0.dll;tools" ^
  src\structdiff_studio.py

echo.
echo Build complete. Check dist\StructDiffStudio.exe.
pause
