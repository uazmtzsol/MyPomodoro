# Mejoras posibles / Backlog

Registro vivo de ideas de mejora. Se revisa y prioriza antes de implementar.
Cada item se prueba y se marca si se mantiene, cambia o mejora.

Ultima actualizacion: 2026-10-14
Version base: refactor modular de `MyPomodoro.py` v5 (entry point: `main.py`).

## Como usar este documento

- Cada idea pasa por: Idea -> En analisis -> Propuesta -> Implementada.
- Al implementar, anotar en "Notas/resultado" si se mantuvo, cambio o mejoro.
- No implementar nada sin antes validar que no rompe el comportamiento de v5
  (transiciones de sesion, tic-tac, estadisticas, bandeja).

Leyenda: `[ ]` idea · `[~]` en analisis/curso · `[P]` propuesta · `[x]` hecha · `[-]` descartada

---

## 1. Registro de sugerencias

### A. Ya implementadas en el refactor (esta sesion)

| # | Sugerencia | Estado | Notas/resultado |
|---|------------|--------|-----------------|
| A1 | Modularizar el proyecto (core/ui/services/resources) | [x] | Se mantiene; comportamiento identico a v5 |
| A2 | Mantener `MyPomodoro.py` intacto como respaldo | [x] | Se mantiene |
| A3 | Persistir estadisticas en `stats.json` | [x] | Se mantiene; `serie` queda efimera |
| A4 | Endurecer `ConfigManager` ante esquemas viejos | [x] | Mejora: evita crash con `tick_volume` float |
| A5 | Asignar icono de bandeja antes de mostrarla | [x] | Mejora: sin warning `No Icon set` |
| A6 | Actualizar `instalador.bat` a `main.py` | [x] | Se mantiene |
| A7 | Sonidos ambientales: subir, nombrar, elegir y volumen propio | [x] | Implementado (ver seccion 3) |

### B. Del otro chat (10 categorias) - consolidadas

Valoraciones originales: dificultad y valor. La columna "Prioridad" es una
propuesta de orden de implementacion (1 = antes).

| # | Categoria | Que incluye | Dificultad | Valor | Estado | Prioridad |
|---|-----------|-------------|-----------|-------|--------|-----------|
| C1 | Gestion de tareas | Lista de tareas con estimacion de pomodoros, tarea activa, historial diario | Media | Muy alto | [x] | 1 (hecha) |
| C2 | Estadisticas visuales | Graficos semanal, heatmap, tiempo por categoria, exportar CSV | Media | Alto | [ ] | 4 |
| C3 | Sonidos ambientales | Subida de audios propios, nombre, seleccion, volumen propio | Baja | Alto | [x] | 2 (hecha) |
| C4 | Descansos activos | Sugerencias de ejercicios en el descanso + temporizador | Muy baja | Medio-Alto | [ ] | 3 |
| C5 | Modo No Molestar | Activar DND del SO, bloquear sitios, pausar notificaciones | Alta | Alto (power users) | [ ] | 6 |
| C6 | Temas y personalizacion | Claro/oscuro automatico, paletas, fuentes, tamano del circulo | Media | Medio | [ ] | 5 |
| C7 | Recordatorios inteligentes | "Listo para empezar?", hidratacion, postura, resumen diario | Baja | Medio | [ ] | 7 |
| C8 | Sincronizacion entre dispositivos | Stats/config/tareas en la nube | Alta | Alto (avanzados) | [ ] | 9 |
| C9 | Logros / gamificacion | Insignias (primer pomodoro, racha 7 dias, 100 pomodoros...) | Baja-Media | Medio | [ ] | 8 |
| C10 | Integracion con calendario | Google/Outlook, bloquear espacios, Todoist/Notion | Alta | Alto | [ ] | 10 |

### C. Candidatas del intento previo (`02-PrimerRefactor`)

Evidencia: carpeta `02-PrimerRefactor` (no versionada). Fuente de ideas, no de arquitectura.

| # | Sugerencia | Estado | Notas/resultado |
|---|------------|--------|-----------------|
| B1 | Estadisticas diarias (registro por dia) | [ ] | Encaja con C2 |
| B2 | Racha actual y racha mas larga | [ ] | Encaja con C2/C9 |
| B3 | Vista de ultimos 7 dias | [ ] | Encaja con C2 |
| B4 | Descanso largo configurable (hoy fijo en 4) | [ ] | Analizar; v5 lo fija en 4 |
| B5 | `start_minimized` / `minimize_to_tray` configurables | [ ] | Analizar |
| B6 | Transiciones del timer con estado explicito (enum) | [x] | Ya aplicado en `core/timer.py` |
| B7 | Audio con QtMultimedia en vez de pygame | [-] | Descartado: mantenemos pygame por paridad con v5 |
| B8 | Duraciones en segundos y volumenes 0..1 | [-] | Descartado: mantenemos esquema de v5 (min, 0..100) |

### D. Observaciones mias / deuda tecnica

| # | Observacion | Estado | Notas |
|---|-------------|--------|-------|
| D1 | `DURATION_KEYS` exportado sin uso real | [ ] | Limpiar o documentar |
| D2 | `ComentariosMac.md` referencia `MyPomodoro.py` y rutas viejas | [ ] | Actualizar a `main.py` + `resources/` |
| D3 | Falta `instalar_mac.sh` real (solo descrito) | [ ] | Crear al retomar mac |
| D4 | Sin pruebas automatizadas de `core/` | [ ] | Anadir tests basicos de timer/stats |
| D5 | `logCompilacion.log` no ignorado por git | [ ] | Anadir a `.gitignore` |
| D6 | Comillas/separador `:` en empaquetado mac | [ ] | Ver `ComentariosMac.md` |

---

## 2. Roadmap priorizado (propuesta)

1. **C1 - Gestion de tareas** (corazon del metodo). Hecha.
2. **C3 - Sonidos ambientales** (hecha).
3. **C4 - Descansos activos** (bienestar, trivial).
4. **C2 - Estadisticas visuales** (motivacion; encaja con B1/B2/B3).
5. **C6 - Temas/personalizacion**.
6. C5, C7, C9, C8, C10 segun interes.

---

## 3. Implementado: C3 - Sonidos ambientales de fondo

Resultado: se mantiene el diseno previsto. El tictac y el ambiente son
independientes (checkboxes y volumenes separados) y pueden sonar a la vez.
La "mezcla de varios sonidos" que mencionaba el otro chat queda pendiente:
hoy se reproduce una pista a la vez (podria ser una mejora futura).

### 3.1 Requisitos del usuario

1. El usuario puede **subir** sus propios archivos de audio ambiental.
2. A cada sonido subido se le asigna un **nombre** legible
   (ej.: `sonido_001.wav` -> "Lluvia calmada").
3. En la configuracion puede **elegir** cual de los sonidos subidos usar.
4. El tic-tac del reloj es **independiente** del ambiente; pueden sonar **ambos**
   si el usuario lo desea.

### 3.2 Decisiones tomadas

- Reproduccion con `pygame.mixer.music` (streaming, bucle, un tema a la vez).
- Volumen propio (`ambient_volume`), separado de tic-tac y notificacion.
- Modo independiente: no se elimina el tic-tac; hay checkbox "Ambiente" y el tic
  sigue con su propio checkbox. Ambos pueden estar activos.
- Los archivos del usuario se guardan en `%APPDATA%/PomodoroTimer/ambient/`
  (nunca en `resources/`, que es del bundle).
- Metadatos de nombres en `ambient/library.json` (mapa archivo -> nombre).
- El ambiente suena mientras el temporizador esta en marcha; se pausa al pausar
  y se detiene al detener/finalizar sin continuar.

### 3.3 Plan incremental y pruebas

1. `services/ambient_library.py`: listar/anadir/quitar/renombrar (filesystem; testeable).
2. `ConfigManager`: claves `ambient_enabled`, `ambient_volume`, `ambient_track`
   + carpeta `ambient/`.
3. `AudioManager`: start/stop/pause/resume + volumen + fade (no toca tick).
4. UI: dialogo de gestion (subir/quitar/renombrar/probar) + selector y volumen.
5. Integracion con el estado del timer y pruebas (libreria en carpeta temporal,
   smoke GUI, import).

Prueba de no-regresion: con el ambiente desactivado, el comportamiento debe ser
identico a v5 (tic-tac + notificacion).

### 3.4 Formatos y tamano

- Formatos admitidos y reproducibles: **wav, ogg, mp3, flac** (via pygame/SDL_mixer).
  No soportados nativamente: m4a/aac, wma, opus, aiff, mid (requeririan conversion).
- El dialogo de gestion muestra el **tamano** de cada pista (`format_size()` en
  `services/ambient_library.py`; `entries()` incluye `size`).
- Recomendacion al usuario: preferir **ogg/mp3** (un wav pesa ~10x mas). Se evaluo
  conversion automatica a flac/ogg y se descarto (dependencia externa + sorpresa);
  la conversion queda como mejora futura opcional (ver C3 pendiente de mezcla).

### 3.5 Sonidos incluidos (bundled)

- Se incluyen dos pistas por defecto en `resources/`: **`rain.ogg`** ("Lluvia") y
  **`ambience.ogg`** ("Ambiente"). Son las versiones comprimidas de sus `.wav`.
- Se empaquetan con PyInstaller (`instalador.bat` y notas de macOS con `--add-data`).
- `AmbientLibrary` los expone como `builtin=True`: aparecen primero en las listas,
  **siempre existen** y **no se pueden renombrar ni eliminar** (el dialogo los marca
  con 🔒 y deshabilita Renombrar/Quitar; si se pueden **Probar** y usar).
- Resolucion de rutas: `resource_manager.get_resources_dir()` (dev: `resources/`;
  bundle: `_MEIPASS`). `AudioManager` recibe la libreria y resuelve pistas incluidas
  o del usuario con `library.path()`.
- Los subidos por el usuario siguen viviendo en `%APPDATA%/PomodoroTimer/ambient/`
  y son los unicos gestionables. Un nombre de archivo que colisione con un incluido
  se renombra automaticamente (sufijo `_1`, `_2`...).

### 3.6 Previsualizacion play/stop

- En la ventana principal (expandida) hay un boton **▶/⏹** junto al selector de
  ambiente: reproduce el seleccionado en bucle y lo detiene. Si el ambiente del
  temporizador estaba sonando, se reanuda al parar la previsualizacion.
- En el dialogo de gestion, "Probar" se reemplazo por **▶ Probar / ⏹ Detener**
  (del elemento seleccionado).
- Se elimino el boton "Probar sonido" de Ajustes (probaba la notificacion); el
  volumen de notificacion se sigue pudiendo ajustar, pero sin boton de prueba.

---

## 4. Implementado: C1 - Gestion de tareas

Resultado: se mantiene el diseno previsto. Solo una tarea activa a la vez; al
completar una sesion de Trabajo se suma 1 al avance de la tarea activa y, al
alcanzar la estimacion, se marca como hecha automaticamente (y deja de estar
activa). El **historial diario** quedo diferido a C2 (ya tenemos `completed_at`).

### 4.1 Requisitos del usuario

1. Crear tareas con **titulo** y **estimacion en pomodoros**.
2. Elegir una **tarea activa** (una sola).
3. Ver la **tarea activa y su avance** (completados/estimados) en la ventana.
4. Al alcanzar el estimado, **marcar la tarea como hecha automaticamente**.

### 4.2 Decisiones tomadas

- Persistencia en `%APPDATA%/PomodoroTimer/tasks.json` (fuente unica del estado,
  incluida la tarea activa); no se duplica en `config.json`.
- `core/tasks.py` (`TaskManager`) es logica pura y testeable (acepta una ruta).
- La tarea **no altera** las transiciones del temporizador: solo registra avance.
- Al completar o marcar hecha la tarea activa, el slot activo se limpia.
- Modelo: `{id, title, estimated, completed, done, created, completed_at}`.

### 4.3 Plan incremental y pruebas

1. `services/resource_manager.py`: `get_tasks_path()`.
2. `core/tasks.py`: `TaskManager` (`add`/`update`/`remove`/`select_active`/
   `record_pomodoro`/`set_done`/`list_pending`/`list_done`). Exportado en
   `core/__init__.py`.
3. `ui/tasks_dialog.py`: crear/editar/marcar hecha/eliminar/usar como activa/
   limpiar completadas; senal `changed`.
4. `ui/main_window.py`: boton "Tareas", etiqueta de tarea activa (modo expandido),
   enganche en `_on_session_complete` (solo sesiones de Trabajo) y tooltip de
   bandeja con la tarea activa.
5. Pruebas: `TaskManager` en carpeta temporal (alta/avance/auto-done/persistencia/
   archivo corrupto) y smoke GUI (crear -> activar -> completar trabajos -> auto-done).

Prueba de no-regresion: sin tarea activa, el comportamiento del temporizador es
identico al actual.
