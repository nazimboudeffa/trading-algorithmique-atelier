"""
Point d'entrée de l'atelier Price Action.

    python src/main.py
"""
from __future__ import annotations

import sys
from pathlib import Path

# rend le dossier src importable (core, lessons, ui) quel que soit le cwd
sys.path.insert(0, str(Path(__file__).resolve().parent))

from ui.main_window import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
