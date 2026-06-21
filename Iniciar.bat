@echo off
REM Duplo-clique para usar o macro (modo automatico, sem calibracao).
REM   Iniciar.bat            -> roda (F8 liga/desliga, F9 sai)
REM   Iniciar.bat --once     -> testa o "Guardar Tudo" uma vez
REM   Iniciar.bat --debug    -> so mostra a confianca do INVEN FULL (nao clica)
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo Python nao encontrado no PATH. Instale o Python 3.10+ e tente de novo.
    pause
    exit /b 1
)

python -c "import mss, cv2, pyautogui, pynput, pystray, PIL" >nul 2>nul
if errorlevel 1 (
    echo Instalando dependencias (so na primeira vez)...
    python -m pip install -r requirements.txt
)

python src\main.py %*

echo.
pause
