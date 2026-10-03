"""
Mesures de base : True Range et ATR.

Un module pour deux fonctions, sans dépendance hors de pandas. C'est
volontairement isolé : `structure` s'en sert pour filtrer les swings, `plan`
pour dimensionner le stop, et aucun des deux n'a besoin de l'autre.

L'ATR est ici à la main plutôt qu'importé d'une bibliothèque d'indicateurs.
Trois raisons, dans l'ordre d'importance :

  * le Price Action s'apprend sur des faits observables, pas sur des formules ;
  * une dépendance de moins est une source de moins de bogues ;
  * on peut expliquer ce que fait le code, ligne par ligne, à un apprenant.
"""
from __future__ import annotations

import pandas as pd

#: Nombre de bougies de l'ATR par défaut (14 est la convention du métier).
ATR_PERIOD = 14


def true_range(df: pd.DataFrame) -> pd.Series:
    """L'amplitude réelle de chaque bougie.

    Ce n'est pas « haut moins bas » : c'est le plus grand des trois écarts

        haut - bas                  l'amplitude de la bougie
        |haut - clôture veille|      le trou d'ouverture
        |bas - clôture veille|       le trou de clôture

    Les deux derniers sont nuls ou presque toujours, et c'est précisément
    pour ça qu'on les prend : un gap n'a pas de mèche, mais il fait mal.
    """
    high = df["High"].to_numpy()
    low = df["Low"].to_numpy()
    close = df["Close"].to_numpy()

    if len(df) == 0:
        return pd.Series(dtype="float64", index=df.index)
    if len(df) == 1:
        return pd.Series([float(high[0] - low[0])], index=df.index)

    prev = close[:-1]
    values = [
        max(
            float(high[i] - low[i]),
            abs(float(high[i] - prev[i - 1])),
            abs(float(low[i] - prev[i - 1])),
        )
        for i in range(1, len(df))
    ]
    # la première bougie n'a pas de veille : son True Range est son amplitude
    return pd.Series([float(high[0] - low[0]), *values], index=df.index)


def atr(df: pd.DataFrame, period: int = ATR_PERIOD) -> float:
    """Average True Range, moyenne simple des `period` dernières amplitudes.

    Moyenne simple et non lissée : on préfère une valeur qui réagit tout de
    suite après un gros mouvement à une valeur lisse mais en retard. Pour
    dimensionner un stop, mieux vaut être réactionnel.
    """
    if len(df) == 0:
        return 0.0
    values = true_range(df)
    if len(values) == 0:
        return 0.0
    window = values.iloc[-period:]
    return float(window.mean())


def span(df: pd.DataFrame) -> float:
    """L'amplitude totale de la fenêtre : le haut du plus haut, moins le bas du plus bas."""
    if len(df) == 0:
        return 0.0
    return float(df["High"].max() - df["Low"].min())


def median_range(df: pd.DataFrame) -> float:
    """L'amplitude *typique* sur toute la fenêtre, pas sur les derniers instants.

    Un ATR recent se replie dès que le marché se calme, et un seuil de swing
    construit dessus s'effondre avec lui : le même marché donne alors deux
    lectures selon l'heure du jour, ce qui est inacceptable. La médiane du
    True Range sur l'ensemble des bougies, elle, ne bouge pas d'une heure à
    l'autre.

    C'est pourquoi elle sert au filtrage des swings, et non l'ATR : l'ATR
    dimensionne un stop (auquel la volatilité récente importe), la médiane
    qualifie une structure (à laquelle seule la volatilité typique importe).
    """
    values = true_range(df)
    if len(values) == 0:
        return 0.0
    return float(values.median())
