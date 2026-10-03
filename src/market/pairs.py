"""
Catalogue des paires de forex et sélection persistée.

Deux responsabilités :

  * le catalogue (`CATALOGUE`) : les paires que l'on peut analyser, avec leur
    convention d'affichage (nombre de décimales, taille d'un pip) ;
  * la sélection : la liste des paires cochées par l'utilisateur, conservée
    d'une session à l'autre dans un petit fichier JSON.

La taille du pip dépend de la devise de cotation : 0.0001 pour tout ce qui
n'est pas en yens, 0.01 pour les paires en JPY. C'est ce qui permet d'afficher
« 25 pips » et non « 0.0025 » sans que le lecteur ait à faire la conversion.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

# --- conventions de cotation ------------------------------------------------
PIP_STD = 0.0001
PIP_JPY = 0.01
DIGITS_STD = 5
DIGITS_JPY = 3


@dataclass(frozen=True)
class Pair:
    """Une paire analysable."""

    symbol: str  # "EURUSD" — la façon dont on l'écrit dans l'atelier
    name: str  # "Euro / Dollar"
    group: str  # "Majeures", "Croisees", "Exotiques"

    @property
    def jpy(self) -> bool:
        return "JPY" in self.symbol

    @property
    def digits(self) -> int:
        return DIGITS_JPY if self.jpy else DIGITS_STD

    @property
    def pip(self) -> float:
        return PIP_JPY if self.jpy else PIP_STD

    def yf(self) -> str:
        """Symbole attendu par yfinance ("EURUSD=X")."""
        return f"{self.symbol}=X"

    def pips(self, price_diff: float) -> float:
        """Convertit un écart de prix en nombre de pips."""
        return round(price_diff / self.pip, 1)

    def __str__(self) -> str:
        return self.symbol


def _p(symbol: str, name: str, group: str = "Majeures") -> Pair:
    return Pair(symbol=symbol, name=name, group=group)


#: Toutes les paires proposées, par famille. L'ordre est celui du menu.
CATALOGUE: tuple[Pair, ...] = (
    # --- majeures : les plus liquidées, les plus fiables à analyser
    _p("EURUSD", "Euro / Dollar"),
    _p("GBPUSD", "Livre / Dollar"),
    _p("USDJPY", "Dollar / Yen"),
    _p("USDCHF", "Dollar / Franc suisse"),
    _p("AUDUSD", "Dollar australien / Dollar"),
    _p("USDCAD", "Dollar / Dollar canadien"),
    _p("NZDUSD", "Dollar neo-zelandais / Dollar"),
    # --- croisées : pas de dollar, donc des mouvements plus francs
    _p("EURGBP", "Euro / Livre", "Croisees"),
    _p("EURJPY", "Euro / Yen", "Croisees"),
    _p("GBPJPY", "Livre / Yen", "Croisees"),
    _p("EURCHF", "Euro / Franc suisse", "Croisees"),
    _p("AUDJPY", "Dollar australien / Yen", "Croisees"),
    _p("EURAUD", "Euro / Dollar australien", "Croisees"),
    _p("EURCAD", "Euro / Dollar canadien", "Croisees"),
    _p("GBPAUD", "Livre / Dollar australien", "Croisees"),
    _p("GBPCAD", "Livre / Dollar canadien", "Croisees"),
    _p("AUDCAD", "Dollar australien / Dollar canadien", "Croisees"),
    _p("AUDNZD", "Dollar australien / Dollar neo-zelandais", "Croisees"),
    _p("CADJPY", "Dollar canadien / Yen", "Croisees"),
    _p("CHFJPY", "Franc suisse / Yen", "Croisees"),
    _p("EURNZD", "Euro / Dollar neo-zelandais", "Croisees"),
    # --- exotiques : spreads larges, à manier avec prudence
    _p("USDTRY", "Dollar / Livre turque", "Exotiques"),
    _p("USDSGD", "Dollar / Dollar singapourien", "Exotiques"),
    _p("USDZAR", "Dollar / Rand sud-africain", "Exotiques"),
    _p("USDMXN", "Dollar / Peso mexicain", "Exotiques"),
    _p("USDSEK", "Dollar / Couronne suédoise", "Exotiques"),
    _p("USDNOK", "Dollar / Couronne norvégienne", "Exotiques"),
    _p("USDHKD", "Dollar / Dollar de Hong Kong", "Exotiques"),
    _p("USDCNH", "Dollar / Yuan chinois", "Exotiques"),
)

#: Libellés affichés pour les groupes.
GROUPS: tuple[str, ...] = ("Majeures", "Croisees", "Exotiques")

#: Sélection par défaut quand aucune préférence n'est encore enregistrée.
DEFAULT_SELECTION: tuple[str, ...] = ("EURUSD", "GBPUSD", "USDJPY")

_BY_SYMBOL: dict[str, Pair] = {p.symbol: p for p in CATALOGUE}


def get(symbol: str) -> Pair:
    """Renvoie la paire connue de ce symbole. Lève `KeyError` sinon."""
    return _BY_SYMBOL[symbol]


def find(symbol: str) -> Pair | None:
    """Comme `get`, mais renvoie `None` au lieu de lever."""
    return _BY_SYMBOL.get(symbol)


def by_group() -> dict[str, list[Pair]]:
    """Le catalogue regroupé, dans l'ordre de `GROUPS`."""
    out: dict[str, list[Pair]] = {g: [] for g in GROUPS}
    for p in CATALOGUE:
        out.setdefault(p.group, []).append(p)
    return out


# --------------------------------------------------------------------------- #
# Sélection persistée
# --------------------------------------------------------------------------- #


def selection_path(root: Path | None = None) -> Path:
    """Fichier qui mémorise les paires cochées."""
    base = Path(root) if root is not None else Path(__file__).resolve().parent.parent.parent
    return base / "data_cache" / "selection.json"


def load_selection(root: Path | None = None) -> list[str]:
    """Rétablit la sélection enregistrée, en ignorant les paires retirées du catalogue."""
    path = selection_path(root)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return list(DEFAULT_SELECTION)
    if not isinstance(raw, list):
        return list(DEFAULT_SELECTION)
    kept = [s for s in raw if isinstance(s, str) and s in _BY_SYMBOL]
    return kept or list(DEFAULT_SELECTION)


def save_selection(symbols, root: Path | None = None) -> list[str]:
    """Enregistre la sélection et renvoie la version normalisée qui a été écrite."""
    kept = [s for s in symbols if s in _BY_SYMBOL]
    path = selection_path(root)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(kept, indent=2, ensure_ascii=False), encoding="utf-8")
    except OSError:
        # une sélection non enregistrable ne doit pas casser l'atelier
        return kept
    return kept
