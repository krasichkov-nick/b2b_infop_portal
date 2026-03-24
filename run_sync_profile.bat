@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Не найден .venv\Scripts\python.exe
    echo Сначала создайте виртуальное окружение и установите зависимости.
    pause
    exit /b 1
)

set /p PROFILE_CODE=Введите код профиля интеграции: 
if "%PROFILE_CODE%"=="" (
    echo [ERROR] Код профиля не указан.
    pause
    exit /b 1
)

set /p LOOP_MODE=Запустить в цикле? (y/n): 
if /I "%LOOP_MODE%"=="y" (
    .venv\Scripts\python.exe manage.py run_sync_profile --code "%PROFILE_CODE%" --loop
) else (
    .venv\Scripts\python.exe manage.py run_sync_profile --code "%PROFILE_CODE%"
)

pause
