@echo off
setlocal ENABLEDELAYEDEXPANSION
echo === Velvet Gallows: FORCED COMBAT (no code changes) ===
set ROOT=%~dp0
set CHAR_DIR=%ROOT%rules\characters
if exist "%CHAR_DIR%\gorthak.json" (
  copy /Y "%CHAR_DIR%\gorthak.json" "%CHAR_DIR%\gorthak.json.bak" >nul
)
if not exist "%CHAR_DIR%\bandit_leader.json" (
  echo [!] Missing rules\characters\bandit_leader.json
  pause
  exit /b 1
)
copy /Y "%CHAR_DIR%\bandit_leader.json" "%CHAR_DIR%\gorthak.json" >nul
python scripts\battle_simulation.py
if exist "%CHAR_DIR%\gorthak.json.bak" (
  move /Y "%CHAR_DIR%\gorthak.json.bak" "%CHAR_DIR%\gorthak.json" >nul
)
echo.
echo Done. Press any key to close.
pause >nul
endlocal
