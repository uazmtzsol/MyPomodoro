import time
from enum import Enum

from core.stats import StatsManager

# Descanso largo cada 4 pomodoros completados (regla fija del temporizador).
LONG_BREAK_INTERVAL = 4


class TimerState(Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"


class SessionType(Enum):
    WORK = "work"
    SHORT_BREAK = "short_break"
    LONG_BREAK = "long_break"


SESSION_NAMES = {
    SessionType.WORK: "Trabajo",
    SessionType.SHORT_BREAK: "Descanso corto",
    SessionType.LONG_BREAK: "Descanso largo",
}

DURATION_KEYS = {
    SessionType.WORK: "work_duration",
    SessionType.SHORT_BREAK: "short_break_duration",
    SessionType.LONG_BREAK: "long_break_duration",
}


class PomodoroTimer:
    """
    Máquina de estados del temporizador Pomodoro.

    Lógica pura (sin Qt): la UI se suscribe mediante callbacks para reflejar
    cambios de estado, iniciar/pausar el tictac y mostrar notificaciones.
    """

    def __init__(self, stats: StatsManager, durations: dict, consecutive_sessions: int = 1):
        self.stats = stats
        self.durations = dict(durations)          # minutos por tipo de sesión
        self.consecutive_sessions = int(consecutive_sessions)

        self.state = TimerState.IDLE
        self.session_type = SessionType.WORK
        self.total_seconds = self._duration_seconds(SessionType.WORK)
        self.remaining_seconds = self.total_seconds
        self._last_time = None

        # Callbacks (los asigna la UI)
        self.on_update = None             # cambio visible (tick o estado)
        self.on_counting_started = None   # arranca/reanuda el conteo
        self.on_paused = None             # se pausó
        self.on_resumed = None            # se reanudó
        self.on_stopped = None            # se detuvo
        self.on_session_complete = None   # recibe SessionType finalizada

    # ------------------------------------------------------------------ config
    def set_config(self, durations: dict, consecutive_sessions: int):
        self.durations = dict(durations)
        self.consecutive_sessions = int(consecutive_sessions)

    def _duration_seconds(self, kind: SessionType) -> int:
        return int(self.durations[kind.value] * 60)

    # ------------------------------------------------------------------- props
    @property
    def is_idle(self) -> bool:
        return self.state is TimerState.IDLE

    @property
    def is_running(self) -> bool:
        return self.state is TimerState.RUNNING

    @property
    def elapsed_ratio(self) -> float:
        if not self.total_seconds:
            return 0.0
        return 1 - (self.remaining_seconds / self.total_seconds)

    # ------------------------------------------------------------- transiciones
    def load_session(self, kind: SessionType):
        self.session_type = kind
        self.total_seconds = self._duration_seconds(kind)
        self.remaining_seconds = self.total_seconds

    def _begin(self):
        self.state = TimerState.RUNNING
        self._last_time = time.time()
        if self.on_counting_started:
            self.on_counting_started()

    def toggle(self):
        """Iniciar / pausar / reanudar según el estado actual."""
        if self.state is TimerState.IDLE:
            if self.session_type is SessionType.WORK:
                self.stats.reset_chain()
            self._begin()
        elif self.state is TimerState.RUNNING:
            self.state = TimerState.PAUSED
            if self.on_paused:
                self.on_paused()
        elif self.state is TimerState.PAUSED:
            self._begin()
            if self.on_resumed:
                self.on_resumed()
        self._notify_update()

    def stop(self):
        """Detiene y vuelve al estado inicial de trabajo."""
        if (self.session_type is SessionType.WORK
                and self.state is not TimerState.IDLE
                and self.remaining_seconds < self.total_seconds):
            self.stats.mark_incomplete()
        else:
            self.stats.reset_chain()

        self.state = TimerState.IDLE
        self._last_time = None
        self.load_session(SessionType.WORK)
        if self.on_stopped:
            self.on_stopped()
        self._notify_update()

    def restart(self):
        """Reinicia la sesión actual conservando su tipo y estado."""
        if (self.session_type is SessionType.WORK
                and self.state is not TimerState.IDLE
                and self.remaining_seconds < self.total_seconds):
            self.stats.mark_incomplete()

        was_running = self.state is TimerState.RUNNING
        was_paused = self.state is TimerState.PAUSED

        if self.on_stopped:
            self.on_stopped()
        self.load_session(self.session_type)

        if was_running:
            self._begin()
        elif was_paused:
            self.state = TimerState.PAUSED
        else:
            self.state = TimerState.IDLE
        self._notify_update()

    def update(self):
        """Avanza el conteo según el tiempo real transcurrido."""
        if self.state is not TimerState.RUNNING or self._last_time is None:
            return

        now = time.time()
        elapsed = now - self._last_time
        if elapsed < 1.0:
            return

        step = int(elapsed)
        self._last_time += step

        counted = min(step, self.remaining_seconds)
        if self.session_type is SessionType.WORK:
            self.stats.add_focus_seconds(counted)

        self.remaining_seconds -= step

        if self.remaining_seconds <= 0:
            self.remaining_seconds = 0
            self._on_session_complete()
            return

        self._notify_update()

    # --------------------------------------------------------------- completado
    def _on_session_complete(self):
        finished = self.session_type
        if self.on_session_complete:
            self.on_session_complete(finished)

        if finished is SessionType.WORK:
            self.stats.complete_work()
            if self.stats.completed % LONG_BREAK_INTERVAL == 0:
                self.load_session(SessionType.LONG_BREAK)
            else:
                self.load_session(SessionType.SHORT_BREAK)
            self._begin()
        else:
            is_long = finished is SessionType.LONG_BREAK
            if is_long:
                self.stats.reset_chain()

            should_continue = (
                not is_long
                and self.stats.chain < self.consecutive_sessions
                and self.stats.completed % LONG_BREAK_INTERVAL != 0
            )

            if should_continue:
                self.load_session(SessionType.WORK)
                self._begin()
            else:
                self.state = TimerState.IDLE
                self._last_time = None
                self.load_session(SessionType.WORK)

        self._notify_update()

    def _notify_update(self):
        if self.on_update:
            self.on_update()
