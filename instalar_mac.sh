#!/bin/bash
#
# Compila Pomodoro Timer para macOS (incluido Big Sur / macOS 11).
#
# Uso:
#   chmod +x instalar_mac.sh
#   ./instalar_mac.sh
#
# Requisitos: Python 3.9 - 3.11 (recomendado) disponible como `python3`.
# El script crea un entorno virtual aislado en .venv-mac/ para no depender
# de la instalacion global de Python ni del PATH.
#
# NOTA: no se puede compilar para Mac desde Windows. Ejecuta esto EN la Mac.
#
set -eo pipefail
cd "$(dirname "$0")"

echo "==> Sistema: $(sw_vers -productName 2>/dev/null || echo macOS) $(sw_vers -productVersion 2>/dev/null) / $(uname -m)"

echo "==> Limpiando compilaciones anteriores..."
rm -rf build dist PomodoroTimer.spec logCompilacion.log

echo "==> Creando entorno virtual (.venv-mac)..."
if [ ! -d ".venv-mac" ]; then
    python3 -m venv .venv-mac
fi
# shellcheck disable=SC1091
source .venv-mac/bin/activate

echo "==> Instalando dependencias (PyQt6 compatible con Big Sur)..."
python -m pip install --upgrade pip
python -m pip install -r requirements-mac.txt

ICON_ARGS=()
if [ -f "resources/ModernPomodoro.icns" ]; then
    ICON_ARGS+=(--icon "resources/ModernPomodoro.icns")
    ICON_ARGS+=(--add-data "resources/ModernPomodoro.icns:.")
else
    echo "AVISO: no se encontro resources/ModernPomodoro.icns (el icono del .app puede verse generico)."
fi

echo "==> Empaquetando aplicacion para macOS..."
# En macOS el separador de --add-data es DOS PUNTOS (:) y no punto y coma (;).
python -m PyInstaller --windowed --onefile --name "PomodoroTimer" \
    --osx-bundle-identifier "com.pomodorotimer.app" \
    "${ICON_ARGS[@]}" \
    --add-data "resources/ModernPomodoro.ico:." \
    --add-data "resources/tick_normal.wav:." \
    --add-data "resources/tick_slow.wav:." \
    --add-data "resources/notification.wav:." \
    --add-data "resources/rain.ogg:." \
    --add-data "resources/ambience.ogg:." \
    main.py 2>&1 | tee logCompilacion.log

# La barra de menu de macOS toma el nombre del Info.plist del bundle (CFBundleName),
# NO de QApplication.setApplicationName(). PyInstaller lo deja como "PomodoroTimer";
# aqui lo cambiamos a "Pomodoro Timer" (<=15 caracteres) para que se vea con espacio.
PLIST="dist/PomodoroTimer.app/Contents/Info.plist"
if [ -f "$PLIST" ]; then
    echo "==> Ajustando nombre visible en la barra de menu (CFBundleName)..."
    for KEY in CFBundleName CFBundleDisplayName; do
        /usr/libexec/PlistBuddy -c "Set :$KEY 'Pomodoro Timer'" "$PLIST" 2>/dev/null \
            || /usr/libexec/PlistBuddy -c "Add :$KEY string 'Pomodoro Timer'" "$PLIST"
    done
else
    echo "AVISO: no se encontro $PLIST; no se pudo ajustar el nombre de la barra de menu."
fi

echo ""
echo "==> Compilacion completada."
echo "    App: dist/PomodoroTimer.app"
echo "    Revisa logCompilacion.log si hubo advertencias."
echo ""
echo "    Si la app tarda en abrir o el icono del Dock falla, prueba --onedir:"
echo "    cambia '--onefile' por '--onedir' en este script."
