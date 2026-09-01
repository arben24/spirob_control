@echo off
rem ---------------------------------------------------------------------------
rem  SpiRob Control unter Windows starten.
rem
rem  Beim ersten Aufruf wird eine virtuelle Umgebung in .venv angelegt und die
rem  Abhaengigkeiten werden installiert; danach startet das Skript die GUI
rem  direkt. Doppelklick auf diese Datei genuegt.
rem ---------------------------------------------------------------------------
setlocal
cd /d "%~dp0"

set PYEXE=.venv\Scripts\python.exe

if not exist "%PYEXE%" (
    echo [1/3] Lege virtuelle Umgebung an ...
    py -3 -m venv .venv
    if errorlevel 1 python -m venv .venv
    if errorlevel 1 (
        echo.
        echo FEHLER: Python 3 wurde nicht gefunden.
        echo Bitte Python 3.10 oder neuer von https://www.python.org/downloads/
        echo installieren und dabei "Add python.exe to PATH" ankreuzen.
        pause
        exit /b 1
    )
)

if not exist ".venv\.installed" (
    echo [2/3] Installiere Abhaengigkeiten ...
    "%PYEXE%" -m pip install --upgrade pip
    "%PYEXE%" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo FEHLER: Die Abhaengigkeiten konnten nicht installiert werden.
        pause
        exit /b 1
    )
    echo ok> .venv\.installed
)

echo [3/3] Starte SpiRob Control ...
"%PYEXE%" -m spirob_control
if errorlevel 1 pause
endlocal
