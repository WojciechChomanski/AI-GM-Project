@echo off
setlocal ENABLEDELAYEDEXPANSION
echo === Velvet Gallows: ENCOUNTER (social check -> maybe combat) ===
set ROOT=%~dp0
python tools\velvet_gallows_runner.py
echo.
echo Done. Press any key to close.
pause >nul
endlocal
