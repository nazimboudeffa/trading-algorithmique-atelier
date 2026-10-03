"""
Récupération des cours : yfinance + cache disque.

L'analyse se fait en **daily**, et l'entrée se joue en intraday. Deux unités
de temps, deux rôles, jamais mélangés :
C'est un choix de fond, et non une économie de moyens.

    D1   la structure — sommet, creux, tendance, niveaux. Un sommet du daily,
                       c'est des dizaines de séances de résistance ; comparer
                       deux de ces sommets, c'est comparer deux intentions du
                       marché, et non deux appuis sur le même clavier.

    M15  le déclencheur — ce que le prix fait maintenant. Le daily dit où se
                       placer ; le M15 dit si c'est le jour. Attendre la
                       confirmation daily pour entrer, c'est entrer une
                       relance plus tard, au prix que le daily ne justifiait
                       plus.

Le découpage n'est pas une cascade d'indicateurs : chaque unité ne répond
qu'à une question, et la question de l'autre unité ne la concerne pas. Le M15
ne dit jamais si la tendance est haussière — il n'a pas les distances pour le
voir. Le daily ne dit jamais si le moment d'entrer est venu — il n'a pas la
résolution pour le voir.

C'est aussi ce que les leçons enseignent, dans cet ordre : on dessine la
structure de l'unité qui la porte, puis on cherche le geste sur l'unité qui
agit. Faire l'inverse — décider sur du M15 — revient à baptiser du bruit
« analyse ».

Le téléchargement passe par `yfinance`, qui n'a besoin que d'une connexion
HTTP — pas de la lourdeur d'un agrégateur généraliste. Chaque série est mise
en cache sur disque : une fois téléchargée, l'atelier fonctionne hors ligne
pendant une heure.

Le réseau n'est jamais touché par les tests : `fetch` accepte un `fetcher`
injectable, et toutes les fonctions de calcul travaillent sur un DataFrame nu.
"""
from __future__ import annotations

import pickle
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

#: Les unités de temps proposées, et l'historique demandé à chacune.
#:
#: Une seule unité est analysée à la fois, de bout en bout : structure, niveaux,
#: déclencheur et plan sont lus sur la même série. C'est la condition pour que
#: l'image soit honnête — un niveau daily tracé sous des bougies de quinze
#: minutes est un dessin faux, et c'est ainsi qu'on apprend à mal lire.
#:
#: Les périodes sont celles que yfinance sert sans transpiration. Pas de
#:.resample : reconstruire du H4 en agrégeant du H1 introduirait des bougies
#: qui n'ont jamais existé, et nous n'avons que des clôtures.
TIMEFRAMES: dict[str, dict[str, str]] = {
    "D1": {"interval": "1d", "period": "5y", "label": "Daily"},
    "H1": {"interval": "1h", "period": "3mo", "label": "H1"},
    "M30": {"interval": "30m", "period": "1mo", "label": "M30"},
    "M15": {"interval": "15m", "period": "5d", "label": "M15"},
}

#: L'unité utilisée au démarrage, et celle que l'onglet propose en premier.
DEFAULT_TIMEFRAME = "D1"

#: Durée de validité d'une série en cache.
CACHE_TTL = timedelta(minutes=60)

#: Nombre de bougies minimum pour qu'une analyse ait du sens.
#:
#: Les planchers sont bas, et c'est volontaire. En daily, une année de
#: séances (environ 250) suffit déjà à lire une structure, et certaines paires
#: exotiques n'ont pas cinq ans d'histoire : les en priver reviendrait à
#: refuser de les analyser.
#:
#: Ce qui est refusé, c'est la série *trop courte pour être lue* : quelques
#: semaines de daily ne distinguent pas une tendance d'un rebond.
MIN_BARS = {"D1": 250, "H1": 500, "M30": 200, "M15": 200}

CACHE_DIR = Path(__file__).resolve().parent.parent.parent / "data_cache"

#: colonnes attendues, dans l'ordre
COLUMNS = ("Open", "High", "Low", "Close", "Volume")


class DataError(RuntimeError):
    """Le cours n'a pas pu être récupéré. Le message est affichable tel quel."""


# --------------------------------------------------------------------------- #
# Cache
# --------------------------------------------------------------------------- #


def _cache_file(symbol: str, timeframe: str) -> Path:
    return CACHE_DIR / f"{symbol}_{timeframe}.pkl"


def _read_cache(path: Path) -> pd.DataFrame | None:
    try:
        if not path.exists():
            return None
        age = datetime.now() - datetime.fromtimestamp(path.stat().st_mtime)
        if age > CACHE_TTL:
            return None
        with path.open("rb") as fh:
            return pickle.load(fh)
    except (OSError, pickle.PickleError, EOFError, AttributeError):
        return None


def _write_cache(path: Path, df: pd.DataFrame) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as fh:
            pickle.dump(df, fh)
    except OSError:
        pass  # un cache non inscriptible n'empêche pas l'analyse


# --------------------------------------------------------------------------- #
# Normalisation
# --------------------------------------------------------------------------- #


def normalize(df: pd.DataFrame) -> pd.DataFrame:
    """Ramène un DataFrame brut à la forme attendue par le moteur.

    On normalise à la main plutôt que de supposer un schéma : yfinance ne
    renvoie pas exactement les mêmes colonnes selon la période demandée.
    """
    if df is None or len(df) == 0:
        raise DataError("Aucune donnée renvoyée pour cette paire.")

    out = pd.DataFrame(index=pd.Index(df.index))
    for col in COLUMNS:
        if col in df.columns:
            out[col] = pd.to_numeric(df[col], errors="coerce")
        elif col == "Volume":
            out[col] = 0.0
        else:
            raise DataError(f"Colonne '{col}' absente de la réponse du fournisseur.")

    out = out.dropna(subset=["Open", "High", "Low", "Close"])

    # yfinance renvoie un index horodaté avec fuseau ; on travaille en heures
    # locales, ce qui est ce que voit l'écran du broker.
    if isinstance(out.index, pd.DatetimeIndex) and out.index.tz is not None:
        out.index = out.index.tz_convert(None)

    out = out[~out.index.duplicated(keep="last")].sort_index()
    if len(out) == 0:
        raise DataError("Toutes les bougies reçues étaient vides.")
    return out


# --------------------------------------------------------------------------- #
# Téléchargement
# --------------------------------------------------------------------------- #


def yf_fetch(symbol: str, interval: str, period: str) -> pd.DataFrame:
    """Téléchargement via yfinance. Import différé : chargé seulement si besoin."""
    try:
        import yfinance
    except ImportError as exc:  # pragma: no cover - dépend de l'installation
        raise DataError(
            "Le paquet 'yfinance' est absent. Lancez : pip install yfinance"
        ) from exc
    try:
        raw = yfinance.download(
            symbol, interval=interval, period=period, progress=False, auto_adjust=True
        )
    except Exception as exc:  # noqa: BLE001 - la lib lève des exceptions libres
        raise DataError(f"Téléchargement impossible pour {symbol} : {exc}") from exc
    if raw is None or len(raw) == 0:
        raise DataError(f"Aucune bougie reçue pour {symbol} sur {interval}.")
    # yfinance peut renvoyer des colonnes dupliquées (une par action) quand
    # la requête porte sur un symbole ambigu : on ne garde que la première.
    if isinstance(raw.columns, pd.MultiIndex):
        raw = raw.droplevel(-1, axis=1)
    return raw


def fetch(
    pair_symbol: str,
    timeframe: str,
    fetcher=None,
    use_cache: bool = True,
) -> pd.DataFrame:
    """Renvoie l'historique OHLC d'une paire, en cache si possible.

    `fetcher(symbol_yf, interval, period) -> DataFrame` permet d'injecter une
    autre source — et aux tests de ne jamais toucher au réseau.
    """
    if timeframe not in TIMEFRAMES:
        raise KeyError(
            f"Unité de temps inconnue : {timeframe} "
            f"(disponibles : {', '.join(TIMEFRAMES)})"
        )
    spec = TIMEFRAMES[timeframe]
    path = _cache_file(pair_symbol, timeframe)

    if use_cache:
        cached = _read_cache(path)
        if cached is not None and len(cached) >= MIN_BARS.get(timeframe, 0):
            return cached

    fetcher = fetcher or yf_fetch
    df = normalize(fetcher(f"{pair_symbol}=X", spec["interval"], spec["period"]))

    minimum = MIN_BARS.get(timeframe, 0)
    if len(df) < minimum:
        raise DataError(
            f"{pair_symbol} {timeframe} : seulement {len(df)} bougies reçues, "
            f"{minimum} nécessaires. L'historique est peut-être indisponible "
            f"sur cette unité de temps (marché fermé, week-end, données "
            f"manquantes)."
        )
    _write_cache(path, df)
    return df


def clear_cache() -> int:
    """Supprime les séries en cache. Renvoie le nombre de fichiers retirés."""
    if not CACHE_DIR.exists():
        return 0
    n = 0
    for timeframe in TIMEFRAMES:
        for f in CACHE_DIR.glob(f"*_{timeframe}.pkl"):
            f.unlink(missing_ok=True)
            n += 1
    return n
