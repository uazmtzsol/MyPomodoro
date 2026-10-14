import random

# Sugerencias para los descansos (ergonomia, vista, respiracion).
BREAK_TIPS = (
    "Estira el cuello y los hombros lentamente.",
    "Mira a lo lejos durante 20 segundos para descansar la vista.",
    "Respira profundo: inhala 4 s, retén 4 s y exhala 6 s.",
    "Ponte de pie y estira la espalda.",
    "Relaja las muñecas y los dedos.",
    "Bebe un vaso de agua.",
    "Camina unos pasos y sacude las piernas.",
    "Cierra los ojos y parpadea despacio.",
    "Estira los brazos por encima de la cabeza.",
    "Corrige la postura: espalda recta y hombros relajados.",
)


class BreakTips:
    """Devuelve consejos de descanso sin repetir el consecutivo."""

    def __init__(self, tips=None):
        self._tips = list(tips) if tips is not None else list(BREAK_TIPS)
        self._bag = []
        self._last = None

    def next(self):
        if not self._tips:
            return ""
        if not self._bag:
            self._bag = list(self._tips)
            random.shuffle(self._bag)
            if len(self._bag) > 1 and self._bag[-1] == self._last:
                self._bag[0], self._bag[-1] = self._bag[-1], self._bag[0]
        tip = self._bag.pop()
        self._last = tip
        return tip
