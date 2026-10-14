# Mejoras posibles / Backlog

Registro vivo de ideas de mejora. Se revisa y prioriza antes de implementar.
Cada item se prueba y se marca si se mantiene, cambia o mejora.

Última actualización: 2026-10-14
Versión base: refactor modular de `MyPomodoro.py` v5 (entry point: `main.py`).

## Cómo usar este documento

- Cada idea pasa por: Idea -> En análisis -> Propuesta -> Implementada.
- Al implementar, anotar en "Notas/resultado" si se mantuvo, cambió o mejoró.
- No implementar nada sin antes validar que no rompe el comportamiento de v5
  (transiciones de sesión, tic-tac, estadísticas, bandeja).

Leyenda de estado: `[ ]` idea · `[~]` en análisis · `[P]` propuesta · `[x]` hecha · `[-]` descartada

---

## 1. Registro de sugerencias

### A. Ya implementadas en el refactor (esta sesión)

| # | Sugerencia | Estado | Notas/resultado |
|---|------------|--------|-----------------|
| A1 | Modularizar el proyecto (core/ui/services/resources) | [x] | Se mantiene; comportamiento idéntico a v5 |
| A2 | Mantener `MyPomodoro.py` intacto como respaldo | [x] | Se mantiene |
| A3 | Persistir estadísticas en `stats.json` | [x] | Se mantiene; `serie` queda efímera |
| A4 | Endurecer `ConfigManager` ante esquemas viejos | [x] | Mejora: evita crash con `tick_volume` float |
| A5 | Asignar icono de bandeja antes de mostrarla | [x] | Mejora: sin warning `No Icon set` |
| A6 | Actualizar `instalador.bat` a `main.py` | [x] | Se mantiene |

### B. Candidatas del intento previo (`02-PrimerRefactor`)

Evidencia: carpeta `02-PrimerRefactor` (no versionada). Sirve como fuente de ideas,
no como referencia de arquitectura.

| # | Sugerencia | Estado | Notas/resultado |
|---|------------|--------|-----------------|
| B1 | Estadísticas diarias (registro por día) | [ ] | Falta definir si aporta valor |
| B2 | Racha actual y racha más larga (días consecutivos) | [ ] | Depende de B1 |
| B3 | Vista de últimos 7 días | [ ] | Depende de B1 |
| B4 | Descanso largo configurable (hoy fijo en 4) | [ ] | Analizar; v5 lo fija en 4 |
| B5 | `start_minimized` / `minimize_to_tray` configurables | [ ] | Analizar |
| B6 | `/duraciones` del timer con estado más explícito (enum) | [x] | Ya aplicado en `core/timer.py` |
| B7 | Audio con QtMultimedia en vez de pygame | [-] | Descartado: mantenemos pygame por paridad con v5 |
| B8 | Duraciones en segundos y volúmenes 0..1 | [-] | Descartado: mantenemos esquema de v5 (min, 0..100) |

### C. Sugerencias del otro chat (pendiente de transcribir)

> PEGAR AQUÍ la lista de mejoras del otro chat. Luego se clasifican y priorizan.

- (pendiente)

### D. Observaciones mías / deuda técnica

| # | Observación | Estado | Notas |
|---|-------------|--------|-------|
| D1 | `DURATION_KEYS` quedó exportado sin uso real | [ ] | Limpiar o documentar |
| D2 | `ComentariosMac.md` referencia `MyPomodoro.py` y rutas viejas | [ ] | Actualizar a `main.py` + `resources/` |
| D3 | Falta `instalar_mac.sh` real (solo descrito) | [ ] | Crear al retomar mac |
| D4 | Sin pruebas automatizadas de `core/` | [ ] | Añadir tests básicos de timer/stats |
| D5 | `logCompilacion.log` no está ignorado por git | [ ] | Añadir a `.gitignore` |
| D6 | Revisar comillas/example de `ComentariosMac` con separador `:` | [ ] | Empaquetado mac |

---

## 2. Siguiente mejora propuesta: Audio relajante de fondo

### 2.1 Requisitos del usuario

1. Debe **sustituir** el tic-tac del reloj.
2. Reproducción **en bucle** con **volumen propio**, independiente del resto.
3. Opción para **gestionar** los audios (añadir archivos, quitar archivos).

### 2.2 Opinión / análisis

1. **Sustituir el tic-tac**: de acuerdo como comportamiento por defecto, pero conviene
   no eliminarlo. Mejor exponer un **modo de sonido**: `Tic-tac` / `Ambiente` /
   `Ambos` / `Silencio`. Motivo: hay usuarios que dependen del tic-tac; mantenerlo
   no cuesta y evita perder funcionalidad. Por defecto: `Ambiente` reemplaza al
   tic-tac cuando hay una pista seleccionada.

2. **Bucle y volumen independiente**: correcto, pero técnicamente conviene usar
   `pygame.mixer.music` en lugar de `pygame.mixer.Sound`:
   - `music.play(-1)` reproduce en bucle **un** tema a la vez.
   - Streaming: no carga minutos de audio en RAM (a diferencia de `Sound`).
   - `music.set_volume()` es **independiente** de los canales de tic-tac y
     notificación (cada uno ya tiene su slider).
   - Aclaración: SDL_mixer sigue sujeto al volumen del sistema operativo; lo que
     sí se logra es un control de volumen **propio de la app** (slider dedicado).
   - Añadir **fade in/out** (`music.fadeout(ms)` y subida gradual) para evitar cortes.
   - El tic-tac y la notificación permanecen con `Sound`/canales (sin cambios).

3. **Gestión de audios**: de acuerdo. Propuesta:
   - Guardar las pistas del usuario en `%APPDATA%/PomodoroTimer/ambient/`
     (o equivalente por SO, vía `resource_manager`). **No** tocar `resources/`,
     que es del bundle.
   - Diálogo con lista (`QListWidget`) + botones: Añadir (importar/copiar),
     Quitar, y Probar/reproducir.
   - Importar con `QFileDialog`; validar formato y manejar colisión de nombres.
   - Formatos recomendados: `OGG` y `WAV`. `MP3` depende de `SDL_mixer` (2.6 suele
     soportarlo); validar en Windows y Mac.

### 2.3 Decisiones abiertas (a resolver antes de codificar)

- ¿La música suena solo en "Trabajo", también en descansos, o siempre? (propongo configurable)
- ¿Se pausa al pausar el temporizador? (propongo sí: `music.pause()` / `unpause()`)
- ¿Autoplay al iniciar sesión o arranque manual?
- ¿"Ducking" (bajar música) mientras suena la notificación? (opcional)
- ¿Se detiene al completar el ciclo o sigue hasta que el usuario pare?

### 2.4 Riesgos / advertencias

- `pygame.mixer.music` y `Sound` comparten el mixer: si `mixer.init()` falla, cae
  todo el audio (ya contemplado con el flag `initialized`).
- Dependencia de códecs del audio entregado (validar OGG/MP3 por SO).
- Archivos grandes o pistas eliminadas fuera de la app -> manejar errores.
- Migración de config: nuevas claves -> ya cubierto por el merge robusto de `ConfigManager`.

### 2.5 Plan incremental y pruebas

1. `services/audio_manager.py`: añadir música de fondo (`pygame.mixer.music`) con
   volumen propio, fade y pause/unpause. No tocar tick/notificación.
2. Servicio de biblioteca de pistas (lógica de filesystem, testeable sin GUI):
   listar / añadir / quitar archivos de `ambient/`.
3. Config: `sound_mode`, `ambient_enabled`, `ambient_volume`, `ambient_track`.
4. UI: slider de volumen ambiente y selector de pista; diálogo de gestión.
5. Integración con el estado del timer (iniciar/pausar/detener/completar).
6. Pruebas: lógica de biblioteca con carpeta temporal; smoke test de audio;
   verificar empaquetado (`instalador.bat`) sin copiar audios del usuario al bundle.

Prueba de que se mantiene: al desactivar el ambiente, el comportamiento debe ser
idéntico a v5 (tic-tac + notificación).
