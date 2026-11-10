
@echo off
title Battle Arena - Inicio del servidor

cd /d "%~dp0"
echo       BATTLE ARENA - INICIANDO
echo.

echo [1/4] Cerrando el servidor Docker anterior...
docker compose down

if errorlevel 1 (
    echo ERROR: No se pudo detener Docker.
    pause
    exit /b 1
)

echo.
echo [2/4] Cerrando descubrimientos anteriores...

powershell -NoProfile -ExecutionPolicy Bypass -Command "$ruta = [regex]::Escape('%~dp0Servidor\descubrimiento_servidor.py'); Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^python(w)?\.exe$' -and $_.CommandLine -match $ruta } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
echo.
echo [3/4] Iniciando descubrimiento...
start "Battle Arena - Descubrimiento" /min py -3 "%~dp0Servidor\descubrimiento_servidor.py"

timeout /t 2 /nobreak >nul

echo.
echo [4/4] Construyendo e iniciando Docker...
docker compose up -d --build

if errorlevel 1 (
    echo ERROR: No se pudo iniciar Docker.
    pause
    exit /b 1
)

echo.
echo       SERVIDOR INICIADO CORRECTAMENTE
echo.
pause