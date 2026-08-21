@echo off
chcp 65001 >nul
setlocal

REM ============================================================
REM  수능 국어 프롬프트 생성기 - 실행
REM  소스를 그대로 복사해 받은 경우 이 파일을 더블클릭하세요.
REM  처음 한 번만 준비 과정을 거치고, 이후에는 바로 실행됩니다.
REM ============================================================

cd /d "%~dp0"

REM --- 파이썬 확인 ---
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo  [안내] 파이썬이 설치되어 있지 않습니다.
    echo.
    echo   https://www.python.org/downloads/ 에서 파이썬을 내려받아 설치해 주세요.
    echo   설치 화면에서 "Add python.exe to PATH" 를 반드시 체크해야 합니다.
    echo   설치가 끝나면 이 창을 닫고 다시 더블클릭하세요.
    echo.
    pause
    exit /b 1
)

REM --- 최초 1회 준비 ---
if not exist ".venv\Scripts\pythonw.exe" (
    echo.
    echo  처음 실행이라 준비가 필요합니다. 몇 분 걸립니다...
    echo  ^(이 과정은 처음 한 번만 합니다^)
    echo.
    python -m venv .venv
    if errorlevel 1 goto failed
    ".venv\Scripts\python.exe" -m pip install --upgrade pip --quiet
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt --quiet
    if errorlevel 1 goto failed
    echo  준비 완료.
)

REM --- 실행 (pythonw: 검은 콘솔 창 없이 앱만 뜬다) ---
start "" ".venv\Scripts\pythonw.exe" main.py
exit /b 0

:failed
echo.
echo  [실패] 준비 중 문제가 발생했습니다. 위 메시지를 확인해 주세요.
echo  인터넷 연결을 확인하고 다시 시도해 주세요.
echo.
pause
exit /b 1
