@echo off
echo === AI_GM_Project: Security Fix ===
python -m pip install python-dotenv
python tools\fix_security.py
echo.
echo Done. Press any key to close this window.
pause >nul
