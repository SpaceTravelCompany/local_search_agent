@echo off

set LLAMA_SERVER=F:/llama/llama-server
set MODEL_PATH=./models/qwen2.5-3b-instruct-q4_k_m.gguf

if not exist "%MODEL_PATH%" (
    echo Error: Model file not found: %MODEL_PATH%
    echo Please download the GGUF and set MODEL_PATH in this script.
    pause
    exit /b 1
)

echo Starting llama.cpp server...
echo Model: %MODEL_PATH%
echo URL: http://localhost:8080
echo.

%LLAMA_SERVER% -m "%MODEL_PATH%" -ngl -1 -c 16384 --host 127.0.0.1 --port 8080

pause
