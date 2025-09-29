@echo off
echo === AI_GM_Project: Install Requirements ===
python -m pip install fastapi uvicorn openai python-dotenv pydantic
echo.
echo Done. Press any key to close this window.
pause >nul
