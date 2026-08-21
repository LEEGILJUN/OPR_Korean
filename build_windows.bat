@echo off
chcp 65001 >nul
setlocal

REM ============================================================
REM  수능 국어 프롬프트 생성기 - 윈도우 배포본 만들기
REM  이 파일을 더블클릭하면 dist\CSATPromptGenerator\ 가 만들어집니다.
REM ============================================================

cd /d "%~dp0"
echo.
echo  수능 국어 프롬프트 생성기 - 윈도우 빌드
echo  ============================================
echo.

REM --- 파이썬 확인 ---
python --version >nul 2>&1
if errorlevel 1 (
    echo  [오류] 파이썬을 찾을 수 없습니다.
    echo.
    echo   https://www.python.org/downloads/ 에서 파이썬을 설치해 주세요.
    echo   설치 화면에서 "Add python.exe to PATH" 를 반드시 체크해야 합니다.
    echo   설치 후 이 창을 닫고 다시 실행하세요.
    echo.
    pause
    exit /b 1
)
for /f "tokens=*" %%v in ('python --version') do echo  파이썬 확인: %%v

REM --- 가상환경 ---
if not exist ".venv\Scripts\python.exe" (
    echo  가상환경을 만드는 중...
    python -m venv .venv
    if errorlevel 1 goto failed
)

REM --- 의존성 ---
echo  필요한 패키지를 설치하는 중... ^(몇 분 걸릴 수 있습니다^)
".venv\Scripts\python.exe" -m pip install --upgrade pip --quiet
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m pip install -r requirements.txt pyinstaller --quiet
if errorlevel 1 goto failed

REM --- 동작 확인 ---
echo  동작을 확인하는 중...
set QT_QPA_PLATFORM=offscreen
".venv\Scripts\python.exe" tools\smoke_test.py
if errorlevel 1 goto failed
set QT_QPA_PLATFORM=

REM --- 빌드 ---
echo  실행 파일을 만드는 중... ^(3~5분 걸립니다^)
".venv\Scripts\pyinstaller.exe" --noconfirm CSATPromptGenerator.spec
if errorlevel 1 goto failed

if not exist "dist\CSATPromptGenerator\CSATPromptGenerator.exe" goto failed

echo.
echo  ============================================
echo   빌드 성공
echo  ============================================
echo.
echo   만들어진 위치:  %CD%\dist\CSATPromptGenerator\
echo.
echo   이 폴더를 통째로 USB에 담아 전달하세요.
echo   exe 파일 하나만 빼내면 실행되지 않습니다.
echo.
explorer "dist\CSATPromptGenerator"
pause
exit /b 0

:failed
echo.
echo  [실패] 빌드 중 문제가 발생했습니다. 위 메시지를 확인해 주세요.
echo.
pause
exit /b 1
