"""Palette et constantes de rendu du canevas pédagogique."""

from PySide6.QtGui import QColor

# --- fonds et texte
BG = QColor(13, 17, 23)
PANEL = QColor(18, 23, 32)
GRID = QColor(26, 31, 42)
AXIS = QColor(60, 70, 88)
TEXT = QColor(226, 232, 240)
MUTED = QColor(138, 148, 166)

# --- bougies
UP = QColor(38, 166, 91)
DOWN = QColor(239, 83, 80)
UP_FILL = QColor(31, 122, 68)
DOWN_FILL = QColor(176, 58, 56)

# --- couleurs sémantiques (S/R, zones, markers)
SUPPORT = QColor(38, 166, 154)
RESISTANCE = QColor(239, 83, 80)
ENTRY = QColor(66, 165, 245)
STOP = QColor(239, 83, 80)
TARGET = QColor(102, 187, 106)
LIQUIDITY = QColor(171, 71, 188)
OB = QColor(255, 152, 0)
FVG = QColor(94, 176, 255)
INFO = QColor(126, 168, 255)
WARN = QColor(255, 167, 38)
GOOD = QColor(38, 166, 91)
BAD = QColor(239, 83, 80)

# --- association kind -> couleur
KIND_COLORS = {
    "support": SUPPORT,
    "resistance": RESISTANCE,
    "liquidity": LIQUIDITY,
    "entry": ENTRY,
    "stop": STOP,
    "target": TARGET,
    "orderblock": OB,
    "fvg": FVG,
    "info": INFO,
    "warn": WARN,
    "good": GOOD,
    "bad": BAD,
    "neutral": MUTED,
}


def color_of(kind: str) -> QColor:
    """Couleur associée à un `kind` d'annotation."""
    return KIND_COLORS.get(kind, MUTED)


def alpha(color: QColor, value: int) -> QColor:
    """Copie d'une couleur avec un canal alpha explicite."""
    out = QColor(color)
    out.setAlpha(value)
    return out
