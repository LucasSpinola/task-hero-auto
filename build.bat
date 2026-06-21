@echo off
REM Gera TaskHeroAutoStash.exe na raiz (1 arquivo, templates embutidos).
cd /d "%~dp0"

python -m pip install -r requirements-dev.txt
if errorlevel 1 goto :erro

python -m PyInstaller --noconfirm --onefile --windowed --name TaskHeroAutoStash ^
  --icon "docs\icone.ico" ^
  --add-data "templates\ui;templates\ui" ^
  --add-data "docs\icone.ico;docs" ^
  --hidden-import pystray._win32 ^
  --distpath . ^
  src\main.py
if errorlevel 1 goto :erro

echo.
echo ============================================================
echo  Pronto: TaskHeroAutoStash.exe (na raiz, executavel unico)
echo  Rode com o jogo aberto. F8 liga/desliga, F9 sai.
echo ============================================================
goto :fim

:erro
echo.
echo FALHOU. Veja o erro acima.
exit /b 1

:fim
