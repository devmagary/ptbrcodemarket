@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul
cd /d "%~dp0"

set "PYTHON_BIN=python"
if exist "C:\Python314\python.exe" set "PYTHON_BIN=C:\Python314\python.exe"

if "%~1"=="--help" (
    echo Instalador da Traducao PT-BR - Code Market
    echo.
    echo Uso sem argumentos: abre o menu interativo.
    echo Uso por linha de comando:
    echo   instalar_ptbr.bat --apply   [--game-dir "CAMINHO"]
    echo   instalar_ptbr.bat --restore [--game-dir "CAMINHO"]
    echo   instalar_ptbr.bat --status  [--game-dir "CAMINHO"]
    echo   instalar_ptbr.bat --help
    exit /b 0
)

if "%~1"=="--apply" (
    shift
    "%PYTHON_BIN%" pipeline.py apply %1 %2 %3 %4
    exit /b %ERRORLEVEL%
)
if "%~1"=="--restore" (
    shift
    "%PYTHON_BIN%" pipeline.py restore %1 %2 %3 %4
    exit /b %ERRORLEVEL%
)
if "%~1"=="--status" (
    shift
    "%PYTHON_BIN%" pipeline.py status %1 %2 %3 %4
    exit /b %ERRORLEVEL%
)

set "GAME_DIR="
if exist "C:\Program Files (x86)\Steam\steamapps\common\Code Market\Code Market_Data" (
    set "GAME_DIR=C:\Program Files (x86)\Steam\steamapps\common\Code Market"
)

if not defined GAME_DIR (
    for %%D in (C D E F G H) do (
        if exist "%%D:\SteamLibrary\steamapps\common\Code Market\Code Market_Data" (
            set "GAME_DIR=%%D:\SteamLibrary\steamapps\common\Code Market"
        )
    )
)

if not defined GAME_DIR (
    echo Nao foi possivel detectar automaticamente a pasta do jogo Code Market.
    set /p "GAME_DIR=Informe o caminho completo da pasta Code Market: "
)

:MENU
cls
echo ============================================================
echo   CODE MARKET - TRADUCAO PT-BR (INSTALADOR)
echo ============================================================
echo Pasta detectada: "%GAME_DIR%"
echo.
echo   [1] Instalar Traducao PT-BR (cria backup automatico)
echo   [2] Restaurar Jogo Original (Ingles)
echo   [3] Verificar Status da Instalacao e Integridade
echo   [0] Sair
echo.
set /p "OPCAO=Escolha uma opcao: "

if "%OPCAO%"=="1" (
    echo.
    "%PYTHON_BIN%" pipeline.py --game-dir "%GAME_DIR%" apply
    pause
    goto MENU
)
if "%OPCAO%"=="2" (
    echo.
    "%PYTHON_BIN%" pipeline.py --game-dir "%GAME_DIR%" restore
    pause
    goto MENU
)
if "%OPCAO%"=="3" (
    echo.
    "%PYTHON_BIN%" pipeline.py --game-dir "%GAME_DIR%" status
    pause
    goto MENU
)
if "%OPCAO%"=="0" (
    exit /b 0
)

echo Opcao invalida.
pause
goto MENU
