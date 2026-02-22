@echo off

REM 가상환경이 있는지 확인
if exist "venv\Scripts\activate.bat" (
    echo 가상환경 활성화 중...
    call venv\Scripts\activate.bat
) else (
    echo 경고: 가상환경이 없습니다.
    echo 가상환경을 생성하려면: python -m venv venv
    echo.
)


REM Python 스크립트 실행
python main.py