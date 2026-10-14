import os
import shutil
import warnings
import wave
from pathlib import Path

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
warnings.filterwarnings("ignore", category=UserWarning, module="pkg_resources")
warnings.filterwarnings("ignore", message="pkg_resources is deprecated.*")
warnings.filterwarnings("ignore", category=DeprecationWarning)

import numpy as np
import pygame

from services.config_manager import ConfigManager
from services.resource_manager import get_resource_path

SOUND_FILES = ("tick_normal.wav", "tick_slow.wav", "notification.wav")


# ============================================================================
# GENERACIÓN DE SONIDOS DE RESPALDO
# ============================================================================
class SoundGenerator:
    @staticmethod
    def _write_wav(filename, samples, sample_rate=44100):
        peak = np.max(np.abs(samples))
        if peak > 0:
            samples = samples / peak
        pcm = (samples * 32767).astype(np.int16)
        stereo = np.column_stack((pcm, pcm))
        with wave.open(str(filename), "w") as w:
            w.setnchannels(2)
            w.setsampwidth(2)
            w.setframerate(sample_rate)
            w.writeframes(stereo.tobytes())

    @classmethod
    def tick(cls, filename, frequency=800, duration=0.05, decay=0.02):
        sr = 44100
        t = np.linspace(0, duration, int(sr * duration), False)
        sound = np.sin(2 * np.pi * frequency * t) * np.exp(-t / decay)
        cls._write_wav(filename, sound, sr)

    @classmethod
    def notification(cls, filename):
        sr = 44100
        half = 0.15
        t1 = np.linspace(0, half, int(sr * half), False)
        b1 = np.sin(2 * np.pi * 1000 * t1) * np.exp(-t1 / 0.1)
        pause = np.zeros(int(sr * 0.1))
        t2 = np.linspace(0, half, int(sr * half), False)
        b2 = np.sin(2 * np.pi * 1200 * t2) * np.exp(-t2 / 0.1)
        cls._write_wav(filename, np.concatenate([b1, pause, b2]), sr)


def install_sounds(config: ConfigManager):
    """Copia los sonidos empaquetados a la carpeta del usuario o los genera."""
    sd = config.sounds_dir

    for name in SOUND_FILES:
        origin = get_resource_path(name)
        dest = sd / name
        if origin.exists() and not dest.exists():
            try:
                shutil.copy2(origin, dest)
            except Exception as e:
                print(f"No se pudo copiar {name}: {e}")

    if not (sd / "tick_normal.wav").exists():
        SoundGenerator.tick(sd / "tick_normal.wav")
    if not (sd / "tick_slow.wav").exists():
        SoundGenerator.tick(sd / "tick_slow.wav", 600, 0.08, 0.03)
    if not (sd / "notification.wav").exists():
        SoundGenerator.notification(sd / "notification.wav")


# ============================================================================
# AUDIO
# ============================================================================
class AudioManager:
    def __init__(self, config: ConfigManager):
        self.config = config
        self.initialized = False
        self.tick_sound = None
        self.notification_sound = None
        self._channel = None
        self._mixer_paused = False
        self.error = None
        self._initialize()

    def _initialize(self):
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            self.initialized = True
        except Exception as e:
            self.error = str(e)
            return

        install_sounds(self.config)
        self._load_sounds()

    def _pause_mixer(self):
        if self.initialized and not self._mixer_paused:
            pygame.mixer.pause()
            self._mixer_paused = True

    def _unpause_mixer(self):
        if self.initialized and self._mixer_paused:
            pygame.mixer.unpause()
            self._mixer_paused = False

    def _load_sounds(self):
        if not self.initialized:
            return
        self.stop_tick()
        sd = self.config.sounds_dir

        name = self.config.get("tick_sound")
        path = sd / f"tick_{name}.wav"
        if not path.exists():
            path = sd / "tick_normal.wav"

        try:
            self.tick_sound = pygame.mixer.Sound(str(path))
        except Exception as e:
            self.tick_sound = None
            self.error = str(e)

        try:
            self.notification_sound = pygame.mixer.Sound(str(sd / "notification.wav"))
        except Exception as e:
            self.notification_sound = None

        self._apply_tick_volume()
        if self.notification_sound:
            self.notification_sound.set_volume(self.config.get("notification_volume") / 100.0)

    def _apply_tick_volume(self):
        volume = max(0.0, min(1.0, self.config.get("tick_volume") / 100.0))
        if self.tick_sound:
            self.tick_sound.set_volume(volume)
        if self._channel is not None:
            self._channel.set_volume(volume, volume)

    def start_tick(self):
        if not self.initialized or self.tick_sound is None or not self.config.get("tick_enabled"):
            return
        if self._channel is not None and self._channel.get_busy():
            return

        self._unpause_mixer()
        try:
            channel = pygame.mixer.Channel(0)
            volume = self.config.get("tick_volume") / 100.0
            channel.set_volume(volume, volume)
            channel.play(self.tick_sound, loops=-1)
            self._channel = channel
        except Exception as e:
            self.error = str(e)

    def stop_tick(self):
        self._unpause_mixer()
        if self._channel is not None:
            self._channel.stop()
            self._channel = None

    def pause_tick(self):
        if self._channel is not None and self._channel.get_busy():
            self._pause_mixer()

    def resume_tick(self):
        self._unpause_mixer()
        if self._channel is None or not self._channel.get_busy():
            self.start_tick()

    def play_notification(self):
        self._unpause_mixer()
        if self.initialized and self.notification_sound:
            self.notification_sound.play()

    def set_tick_volume(self, value):
        self.config.set("tick_volume", int(value))
        self._apply_tick_volume()

    def set_notification_volume(self, value):
        self.config.set("notification_volume", int(value))
        if self.notification_sound:
            self.notification_sound.set_volume(value / 100.0)

    def set_tick_sound(self, name):
        was_playing = self._channel is not None and self._channel.get_busy()
        was_paused = self._mixer_paused
        self.stop_tick()
        self.config.set("tick_sound", name)
        self._load_sounds()
        if was_playing:
            self.start_tick()
            if was_paused:
                self.pause_tick()

    def set_tick_enabled(self, enabled):
        self.config.set("tick_enabled", enabled)
        if not enabled:
            self.stop_tick()

    def cleanup(self):
        self.stop_tick()
        if self.initialized:
            pygame.mixer.quit()
            self.initialized = False
