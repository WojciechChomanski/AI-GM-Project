@echo off
echo === AI_GM_Project: Security Fix (ANY Folder) ===
python -m pip install python-dotenv
python fix_security_anyfolder.py
echo.
echo Done. Press any key to close this window.
pause >nul
