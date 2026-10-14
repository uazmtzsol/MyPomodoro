@echo off
echo Limpiando compilaciones anteriores...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "PomodoroTimer.spec" del /q "PomodoroTimer.spec"

echo Empaquetando aplicacion modular desde la carpeta resources...
pyinstaller --noconsole --onefile --name "PomodoroTimer" --icon="resources/ModernPomodoro.ico" --add-data "resources/ModernPomodoro.ico;." --add-data "resources/tick_normal.wav;." --add-data "resources/tick_slow.wav;." --add-data "resources/notification.wav;." --add-data "resources/rain.ogg;." --add-data "resources/ambience.ogg;." main.py > logCompilacion.log

echo.
echo ¡Compilacion completada! Revisa logCompilacion.log si hubo errores.
echo El ejecutable esta en la carpeta 'dist'.
pause