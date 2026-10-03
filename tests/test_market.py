"""Tests du moteur d'analyse : données, structure, niveaux, plan."""
from __future__ import annotations

import pandas as pd
import pytest

from market import analysis as an
from market import data as md
from market import levels as lv
from market import pairs as mp
from market import plan as pl
from market import structure as stx

# --------------------------------------------------------------------------- #
# Données de test : on construit des séries lisibles
# --------------------------------------------------------------------------- #


def make_df(rows: list[tuple[float, float, float, float]]) -> pd.DataFrame:
    """Construit un DataFrame OHLC à partir de tuples (O, H, L, C)."""
    idx = pd.date_range("2026-01-05 08:00", periods=len(rows), freq="15min")
    return pd.DataFrame(rows, columns=["Open", "High", "Low", "Close"], index=idx)


def zigzag(closes: list[float], wick: float = 0.0004) -> pd.DataFrame:
    """Série de bougies cohérentes à partir d'une suite de clôtures."""
    rows = []
    prev = closes[0]
    for c in closes:
        o = prev
        h = max(o, c) + wick
        low = min(o, c) - wick
        rows.append((o, h, low, c))
        prev = c
    return make_df(rows)


EURUSD = mp.get("EURUSD")
USDJPY = mp.get("USDJPY")


# --------------------------------------------------------------------------- #
# Paires
# --------------------------------------------------------------------------- #


def test_les_paires_ne_se_ressemblent_pas_toutes():
    assert EURUSD.digits == 5
    assert USDJPY.digits == 3
    assert EURUSD.pip == 0.0001
    assert USDJPY.pip == 0.01


def test_symbole_yfinance():
    assert EURUSD.yf() == "EURUSD=X"
    assert USDJPY.yf() == "USDJPY=X"


def test_conversion_en_pips():
    # 25 pips sur une paire à 4 décimales
    assert EURUSD.pips(0.0025) == 25.0
    # le même écart vaut 0.25 pip sur du JPY
    assert USDJPY.pips(0.025) == 2.5


def test_catalogue_sans_doublon():
    symbols = [p.symbol for p in mp.CATALOGUE]
    assert len(symbols) == len(set(symbols))


def test_recherche_inconnue_renvoie_none():
    assert mp.find("XXXXXX") is None
    with pytest.raises(KeyError):
        mp.get("XXXXXX")


def test_selection_par_defaut():
    assert mp.load_selection() == list(mp.DEFAULT_SELECTION)


def test_selection_enregistree_et_relu(tmp_path):
    saved = mp.save_selection(["USDJPY", "EURUSD"], root=tmp_path)
    assert saved == ["USDJPY", "EURUSD"]
    assert mp.load_selection(tmp_path) == ["USDJPY", "EURUSD"]


def test_selection_ignore_les_paires_inconnues(tmp_path):
    saved = mp.save_selection(["EURUSD", "PASUNEPAIRE"], root=tmp_path)
    assert saved == ["EURUSD"]
    assert mp.load_selection(tmp_path) == ["EURUSD"]


def test_selection_vide_retombe_sur_le_defaut(tmp_path):
    mp.save_selection([], root=tmp_path)
    assert mp.load_selection(tmp_path) == list(mp.DEFAULT_SELECTION)


def test_selection_corrompue_retombe_sur_le_defaut(tmp_path):
    (tmp_path / "data_cache").mkdir(parents=True)
    (tmp_path / "data_cache" / "selection.json").write_text("{pas du json", encoding="utf-8")
    assert mp.load_selection(tmp_path) == list(mp.DEFAULT_SELECTION)


# --------------------------------------------------------------------------- #
# Données
# --------------------------------------------------------------------------- #


def test_normalize_ordonne_et_dedoublonne():
    idx = pd.to_datetime(["2026-01-02 10:00", "2026-01-02 09:00", "2026-01-02 10:00"])
    raw = pd.DataFrame(
        {"Open": [1.0, 0.9, 0.8], "High": [1.1, 1.0, 1.2],
         "Low": [0.9, 0.8, 0.7], "Close": [1.05, 0.95, 0.85]},
        index=idx,
    )
    out = md.normalize(raw)
    assert len(out) == 2
    assert out.index.is_monotonic_increasing
    assert not out.index.duplicated().any()


def test_normalize_ajoute_volume_absent():
    raw = pd.DataFrame(
        {"Open": [1.0], "High": [1.1], "Low": [0.9], "Close": [1.0]},
        index=[pd.Timestamp("2026-01-02")],
    )
    out = md.normalize(raw)
    assert "Volume" in out.columns
    assert out["Volume"].iloc[0] == 0.0


def test_normalize_refuse_une_colonne_manquante():
    raw = pd.DataFrame(
        {"Open": [1.0], "Close": [1.0]},
        index=[pd.Timestamp("2026-01-02")],
    )
    with pytest.raises(md.DataError, match="High"):
        md.normalize(raw)


def test_normalize_refuse_une_serie_vide():
    with pytest.raises(md.DataError):
        md.normalize(pd.DataFrame(columns=["Open", "High", "Low", "Close"]))


def test_normalize_retire_le_fuseau():
    idx = pd.to_datetime(["2026-01-02 10:00"]).tz_localize("UTC")
    raw = pd.DataFrame(
        {"Open": [1.0], "High": [1.1], "Low": [0.9], "Close": [1.0]}, index=idx
    )
    assert md.normalize(raw).index.tz is None


def test_fetch_utilise_le_fournisseur_injecte():
    """Le test ne touche jamais le réseau : le fetcher est fourni."""
    calls = []

    def fake(symbol, interval, period):
        calls.append((symbol, interval, period))
        n = 100
        return make_df([(1.0, 1.01, 0.99, 1.005)] * n)

    df = md.fetch("EURUSD", "H1", fetcher=fake, use_cache=False)
    assert len(df) == 100
    assert calls == [("EURUSD=X", "1h", "3mo")]


def test_fetch_refuse_un_timeframe_inconnu():
    with pytest.raises(KeyError):
        md.fetch("EURUSD", "M4", fetcher=lambda *a: make_df([]), use_cache=False)


def test_fetch_explique_une_serie_trop_courte():
    def fake(symbol, interval, period):
        return make_df([(1.0, 1.01, 0.99, 1.005)] * 10)

    with pytest.raises(md.DataError, match="10 bougies"):
        md.fetch("EURUSD", "H1", fetcher=fake, use_cache=False)


# --------------------------------------------------------------------------- #
# Structure
# --------------------------------------------------------------------------- #


def test_swing_haut_reconnu():
    # un sommet isolé au milieu d'une série
    closes = [1.0, 1.0, 1.0, 1.1, 1.0, 1.0, 1.0]
    df = zigzag(closes)
    highs = [s for s in stx.find_swings(df) if s.is_high]
    assert len(highs) == 1
    assert highs[0].index == 3


def test_swing_bas_reconnu():
    closes = [1.0, 1.0, 1.0, 0.9, 1.0, 1.0, 1.0]
    df = zigzag(closes)
    lows = [s for s in stx.find_swings(df) if not s.is_high]
    assert len(lows) == 1
    assert lows[0].index == 3


def test_aucun_swing_sur_une_serie_plate():
    df = zigzag([1.0] * 10)
    # une série plate a des « sommets » partout ; c'est un cas dégénéré, mais
    # on vérifie surtout que la fonction ne plante pas
    assert isinstance(stx.find_swings(df), list)


def test_serie_trop_courte_pas_de_swing():
    df = zigzag([1.0, 1.1])
    assert stx.find_swings(df) == []


# Une vague = 5 bougies entre deux sommets. C'est la longueur minimale pour
# que la fractale (2 bougies à gauche, 2 à droite) confirme un swing : avec
# des vagues plus courtes, aucun swing n'est détecté et la structure reste
# indéterminée — ce qui est le comportement correct, pas un bug.
WAVE_UP = [
    1.00, 1.03, 1.06, 1.09, 1.12,
    1.05, 1.02, 1.08, 1.14, 1.20,
    1.13, 1.10, 1.16, 1.22, 1.28,
    1.21, 1.18, 1.24, 1.30, 1.36,
]


def _invert(closes: list[float], mid: float) -> list[float]:
    """Miroir d'une série : transforme une tendance haussière en baissière."""
    return [2 * mid - c for c in closes]


def test_structure_haussiere():
    df = zigzag(WAVE_UP)
    st = stx.read_structure(df)
    assert st.trend == stx.UP
    assert st.has_enough
    assert "HH + HL" in st.label


def test_structure_baissiere():
    df = zigzag(_invert(WAVE_UP, 1.18))
    st = stx.read_structure(df)
    assert st.trend == stx.DOWN
    assert "LH + LL" in st.label


def test_structure_indeterminee_sans_assez_de_swings():
    df = zigzag([1.0, 1.05, 1.02])
    st = stx.read_structure(df)
    assert st.trend == stx.RANGE
    assert not st.has_enough
    assert "indéterminée" in st.describe()


def test_range_quand_les_swings_se_cheauchent():
    """Sommets plus bas mais creux plus hauts : ni tendance, ni son inverse.

    C'est la configuration qui invalide le plus de gens dans l'ancien moteur :
    son vote à 7 facteurs y trouvait toujours un gagnant et un perdant.
    """
    closes = [
        1.05, 1.10, 1.15, 1.18, 1.20,  # sommet A
        1.10, 1.06, 1.04,              # creux A
        1.10, 1.14,                    # sommet B, plus bas que A
        1.10, 1.08, 1.07,              # creux B, plus haut que A
        1.12, 1.16,
    ]
    df = zigzag(closes)
    st = stx.read_structure(df)
    assert st.has_enough
    assert st.last_high.price < st.prev_high.price  # sommet plus bas
    assert st.last_low.price > st.prev_low.price    # creux plus haut
    assert st.trend == stx.RANGE


def test_position_dans_le_range():
    st = stx.Structure(
        trend=stx.UP,
        last_high=stx.Swing(10, 1.20, "high"),
        last_low=stx.Swing(5, 1.00, "low"),
        prev_high=stx.Swing(2, 1.15, "high"),
        prev_low=stx.Swing(0, 0.95, "low"),
    )
    bottom = stx.read_position(zigzag([1.0, 1.02, 1.01]), st)
    assert bottom.where == stx.BOTTOM
    assert bottom.is_favourable_for(stx.UP)

    top = stx.read_position(zigzag([1.0, 1.18, 1.19]), st)
    assert top.where == stx.TOP
    assert not top.is_favourable_for(stx.UP)

    mid = stx.read_position(zigzag([1.0, 1.10, 1.10]), st)
    assert mid.where == stx.MIDDLE
    assert not mid.is_favourable_for(stx.UP)


def test_position_au_dessus_de_l_enveloppe():
    st = stx.Structure(
        trend=stx.UP,
        last_high=stx.Swing(10, 1.20, "high"),
        last_low=stx.Swing(5, 1.00, "low"),
    )
    pos = stx.read_position(zigzag([1.0, 1.25]), st)
    assert pos.where == stx.ABOVE
    assert pos.ratio > 1.0


def test_position_avec_enveloppe_degeneree():
    st = stx.Structure()  # aucun swing : enveloppe plate
    pos = stx.read_position(zigzag([1.0, 1.0]), st)
    assert pos.span >= 0


# --------------------------------------------------------------------------- #
# Niveaux et déclencheur
# --------------------------------------------------------------------------- #


def test_niveaux_viennent_de_la_structure():
    st = stx.Structure(
        trend=stx.UP,
        last_high=stx.Swing(10, 1.20, "high"),
        last_low=stx.Swing(5, 1.00, "low"),
    )
    df = zigzag([1.0, 1.05, 1.0, 1.1, 1.05, 1.2, 1.15, 1.2])
    levels = lv.sr_levels(df, st)
    kinds = {lv_.kind for lv_ in levels}
    assert kinds == {"support", "resistance"}
    assert all(lv_.touches >= 1 for lv_ in levels)


def test_niveau_fort_est_marque():
    st = stx.Structure(last_high=stx.Swing(10, 1.20, "high"), last_low=stx.Swing(5, 1.00, "low"))
    # le prix repasse souvent à 1.00
    closes = [1.0, 1.02, 1.0, 1.02, 1.0, 1.02, 1.0, 1.02, 1.0, 1.05]
    df = zigzag(closes)
    levels = lv.sr_levels(df, st)
    support = lv.nearest(levels, 1.01, "support")
    assert support is not None
    assert support.touches >= 3
    assert support.strong
    assert f"({support.touches}x)" in support.label()


def test_rejet_acheteur_detecte():
    # la bougie pique le support et clôture au-dessus
    rows = [
        (1.10, 1.11, 1.09, 1.10),
        (1.10, 1.11, 0.995, 1.105),  # mèche basse sur 1.00, clôture 1.105
    ]
    df = make_df(rows)
    found = lv._rejection(1, df.iloc[1], 1.00)
    assert found is not None
    assert found[0] == lv.LONG


def test_rejet_vendeur_detecte():
    rows = [
        (1.10, 1.11, 1.09, 1.10),
        (1.10, 1.205, 1.095, 1.098),  # mèche haute sur 1.20, clôture en dessous
    ]
    df = make_df(rows)
    found = lv._rejection(1, df.iloc[1], 1.20)
    assert found is not None
    assert found[0] == lv.SHORT


def test_miche_qui_perce_le_niveau_est_un_rejet():
    """La mèche qui traverse le niveau et la clôture qui revient : c'est le
    schéma de rejet classique. Le corps, lui, reste du bon côté."""
    rows = [
        (1.10, 1.11, 1.09, 1.10),
        (1.10, 1.11, 0.98, 1.09),  # mèche sous 1.00, corps et clôture dessus
    ]
    df = make_df(rows)
    found = lv._rejection(1, df.iloc[1], 1.00)
    assert found is not None
    assert found[0] == lv.LONG


def test_corps_qui_traverse_le_niveau_pas_un_rejet():
    # la clôture passe sous le support : le niveau a cédé, ce n'est plus un rejet
    rows = [
        (1.10, 1.11, 1.09, 1.10),
        (1.10, 1.11, 0.98, 0.99),
    ]
    df = make_df(rows)
    assert lv._rejection(1, df.iloc[1], 1.00) is None


def test_miche_trop_courte_pas_un_rejet():
    # gros corps, mèche minuscule : le niveau est effleuré, pas rejeté
    rows = [
        (1.10, 1.11, 1.09, 1.10),
        (1.10, 1.1102, 1.0998, 1.11),
    ]
    df = make_df(rows)
    assert lv._rejection(1, df.iloc[1], 1.10) is None


def test_bougie_plate_pas_de_rejet():
    rows = [(1.0, 1.0, 1.0, 1.0)]
    df = make_df(rows)
    assert lv._rejection(0, df.iloc[0], 1.0) is None


def test_find_trigger_sans_niveau():
    assert lv.find_trigger(zigzag([1.0, 1.1]), []) is None


def test_find_trigger_trouve_le_rejet_recent():
    levels = [lv.SRLevel(price=1.00, kind="support", touches=3)]
    rows = [
        (1.10, 1.11, 1.09, 1.10),
        (1.10, 1.11, 0.995, 1.105),
    ]
    df = make_df(rows)
    tr = lv.find_trigger(df, levels)
    assert tr is not None
    assert tr.is_long
    assert tr.price == 1.00
    assert "mèche" in tr.describe()


def test_find_trigger_ignore_les_vieux_rejets():
    levels = [lv.SRLevel(price=1.00, kind="support", touches=3)]
    rows = [
        (1.10, 1.11, 0.995, 1.105),  # rejet ancien, il y a 6 bougies
        (1.10, 1.12, 1.09, 1.11),
        (1.11, 1.12, 1.10, 1.115),
        (1.12, 1.13, 1.11, 1.125),
        (1.13, 1.14, 1.12, 1.135),
        (1.14, 1.15, 1.13, 1.145),
        (1.15, 1.16, 1.14, 1.155),
    ]
    df = make_df(rows)
    assert lv.find_trigger(df, levels) is None  # hors de la fenêtre de 5


def test_find_trigger_avec_lookback_elargi():
    levels = [lv.SRLevel(price=1.00, kind="support", touches=3)]
    # 8 bougies, rejet à la bougie 1 : hors de la fenêtre par défaut (5),
    # mais visible si on élargit la recherche.
    rows = [
        (1.20, 1.21, 1.19, 1.20),
        (1.10, 1.11, 0.995, 1.105),  # rejet ancien
        (1.10, 1.12, 1.09, 1.11),
        (1.11, 1.12, 1.10, 1.115),
        (1.12, 1.13, 1.11, 1.125),
        (1.13, 1.14, 1.12, 1.135),
        (1.14, 1.15, 1.13, 1.145),
        (1.15, 1.16, 1.14, 1.155),
    ]
    df = make_df(rows)
    assert lv.find_trigger(df, levels) is None
    assert lv.find_trigger(df, levels, lookback=8) is not None


def test_balayage_de_sommet_detecte():
    st = stx.Structure(prev_high=stx.Swing(0, 1.20, "high"))
    rows = [
        (1.19, 1.20, 1.18, 1.19),
        (1.19, 1.25, 1.18, 1.195),  # dépasse 1.20 puis clôture dessous
    ]
    df = make_df(rows)
    sweep = lv.sweep_of_liquidity(df, st)
    assert sweep is not None
    assert sweep["kind"] == "sweep_high"


def test_balayage_de_creux_detecte():
    st = stx.Structure(prev_low=stx.Swing(0, 1.00, "low"))
    rows = [
        (1.01, 1.02, 1.00, 1.01),
        (1.01, 1.02, 0.95, 1.005),  # perce 1.00 puis clôture dessus
    ]
    df = make_df(rows)
    sweep = lv.sweep_of_liquidity(df, st)
    assert sweep is not None
    assert sweep["kind"] == "sweep_low"


def test_pas_de_balayage_si_pas_de_percement():
    st = stx.Structure(prev_high=stx.Swing(0, 1.20, "high"))
    df = zigzag([1.19, 1.19, 1.19])
    assert lv.sweep_of_liquidity(df, st) is None


# --------------------------------------------------------------------------- #
# Biais
# --------------------------------------------------------------------------- #


def _ctx(trend: str, where: str, direction: str) -> tuple:
    tr = lv.Trigger(direction=direction, index=0, price=1.0, close=1.0, wick_ratio=0.6)
    pos = stx.Position(where=where, low=1.0, high=1.2, price=1.05)
    st = stx.Structure(trend=trend)
    return tr, pos, st


def test_biais_inexistant_sans_declencheur():
    _, pos, st = _ctx(stx.UP, stx.BOTTOM, lv.LONG)
    bias, why = lv.bias_of(None, pos, st)
    assert bias == "aucun"
    assert "déclencheur" in why


def test_biais_inexistant_en_range():
    tr, pos, st = _ctx(stx.RANGE, stx.BOTTOM, lv.LONG)
    bias, why = lv.bias_of(tr, pos, st)
    assert bias == "aucun"
    assert "range" in why


def test_biais_inexistant_si_declencheur_contredit():
    tr, pos, st = _ctx(stx.UP, stx.BOTTOM, lv.SHORT)
    bias, why = lv.bias_of(tr, pos, st)
    assert bias == "aucun"
    assert "structure" in why


def test_biais_inexistant_si_position_mauvaise():
    tr, pos, st = _ctx(stx.UP, stx.TOP, lv.LONG)
    bias, why = lv.bias_of(tr, pos, st)
    assert bias == "aucun"
    assert "mauvais prix" in why


def test_biais_achat():
    tr, pos, st = _ctx(stx.UP, stx.BOTTOM, lv.LONG)
    bias, _ = lv.bias_of(tr, pos, st)
    assert bias == lv.LONG


def test_biais_vente():
    tr, pos, st = _ctx(stx.DOWN, stx.TOP, lv.SHORT)
    bias, _ = lv.bias_of(tr, pos, st)
    assert bias == lv.SHORT


# --------------------------------------------------------------------------- #
# Plan
# --------------------------------------------------------------------------- #


def test_atr_positif():
    df = zigzag([1.0, 1.01, 1.005, 1.015, 1.01])
    assert pl.atr(df) > 0


def test_atr_nul_sur_serie_plate():
    df = make_df([(1.0, 1.0, 1.0, 1.0)] * 5)
    assert pl.atr(df) == 0.0


def test_atr_sur_serie_d_une_bougie():
    assert pl.atr(make_df([(1.0, 1.1, 0.9, 1.0)])) == 0.0


#: Vague de rebond sur support, à l'échelle d'une vraie paire : amplitude
#: d'environ 25 pips, ce qui donne un stop tenable (le seuil est à 90 pips).
BOUNCE = [1.1000, 1.1040, 1.1080, 1.1100, 1.1060, 1.1020, 1.1000, 1.1020]


def test_plan_achat_complet():
    df = zigzag(BOUNCE)
    levels = [
        lv.SRLevel(price=1.1000, kind="support", touches=3),
        lv.SRLevel(price=1.1150, kind="resistance", touches=3),
    ]
    tr = lv.Trigger(direction=lv.LONG, index=len(df) - 1, price=1.1000,
                    close=1.1020, wick_ratio=0.6)
    plan = pl.build_plan(df, EURUSD, tr, levels, lv.LONG)
    assert plan.decision == pl.BUY
    assert plan.stop < plan.entry < plan.target
    assert plan.rr >= pl.MIN_RR
    assert 0 < plan.stop_pips <= pl.MAX_STOP_PIPS
    assert plan.to_dict()["decision"] == pl.BUY


def test_plan_achat_stop_sous_le_niveau():
    df = zigzag(BOUNCE)
    levels = [
        lv.SRLevel(price=1.1000, kind="support", touches=3),
        lv.SRLevel(price=1.1200, kind="resistance", touches=3),
    ]
    tr = lv.Trigger(direction=lv.LONG, index=len(df) - 1, price=1.1000,
                    close=1.1020, wick_ratio=0.6)
    plan = pl.build_plan(df, EURUSD, tr, levels, lv.LONG)
    assert plan.actionable
    assert plan.stop < 1.1000  # au-delà du niveau invalidé


def test_plan_vente_stop_au_dessus():
    df = zigzag(_invert(BOUNCE, 1.1050))
    levels = [
        lv.SRLevel(price=1.0900, kind="support", touches=3),
        lv.SRLevel(price=1.1100, kind="resistance", touches=3),
    ]
    tr = lv.Trigger(direction=lv.SHORT, index=len(df) - 1, price=1.1100,
                    close=1.1080, wick_ratio=0.6)
    plan = pl.build_plan(df, EURUSD, tr, levels, lv.SHORT)
    assert plan.decision == pl.SELL
    assert plan.target < plan.entry < plan.stop
    assert plan.stop > 1.1100


def test_plan_refuse_si_ratio_insuffisant():
    # résistance à 1.1010, collée à l'entrée : le ratio ne peut pas être bon
    df = zigzag(BOUNCE)
    levels = [lv.SRLevel(price=1.1010, kind="resistance", touches=3)]
    tr = lv.Trigger(direction=lv.LONG, index=len(df) - 1, price=1.1000,
                    close=1.1020, wick_ratio=0.6)
    plan = pl.build_plan(df, EURUSD, tr, levels, lv.LONG)
    assert plan.decision == pl.WAIT
    assert not plan.actionable
    assert plan.entry is None  # le plan refusé ne laisse pas de prix à moitié
    assert any("ratio" in b for b in plan.blocks)


def test_plan_refuse_si_stop_trop_large():
    df = zigzag(BOUNCE)
    # niveau à 300 pips du prix : aucun stop raisonnable
    tr = lv.Trigger(direction=lv.LONG, index=len(df) - 1, price=1.0700,
                    close=1.1020, wick_ratio=0.6)
    levels = [lv.SRLevel(price=1.0700, kind="support", touches=3)]
    plan = pl.build_plan(df, EURUSD, tr, levels, lv.LONG)
    assert plan.decision == pl.WAIT
    assert any("pips" in b for b in plan.blocks)


def test_plan_refuse_sans_obstacle():
    df = zigzag(BOUNCE)
    # aucune résistance au-dessus : pas de cible, donc pas de ratio
    levels = [lv.SRLevel(price=1.1000, kind="support", touches=3)]
    tr = lv.Trigger(direction=lv.LONG, index=len(df) - 1, price=1.1000,
                    close=1.1020, wick_ratio=0.6)
    plan = pl.build_plan(df, EURUSD, tr, levels, lv.LONG)
    assert plan.decision == pl.WAIT
    assert any("obstacle" in b for b in plan.blocks)


def test_plan_refuse_sur_obstacle_dans_le_mauvais_sens():
    """Une résistance SOUS le prix n'est pas une cible d'achat."""
    df = zigzag(BOUNCE)
    levels = [lv.SRLevel(price=1.0500, kind="resistance", touches=3)]
    tr = lv.Trigger(direction=lv.LONG, index=len(df) - 1, price=1.1000,
                    close=1.1020, wick_ratio=0.6)
    plan = pl.build_plan(df, EURUSD, tr, levels, lv.LONG)
    assert plan.decision == pl.WAIT


def test_plan_refuse_atr_nul():
    df = make_df([(1.0, 1.0, 1.0, 1.0)] * 5)
    levels = [lv.SRLevel(price=1.0, kind="support", touches=3)]
    tr = lv.Trigger(direction=lv.LONG, index=4, price=1.0, close=1.0, wick_ratio=0.6)
    plan = pl.build_plan(df, EURUSD, tr, levels, lv.LONG)
    assert plan.decision == pl.WAIT
    assert any("ATR" in b for b in plan.blocks)


def test_plan_refuse_direction_inconnue():
    df = zigzag([1.0, 1.1])
    tr = lv.Trigger(direction=lv.LONG, index=1, price=1.0, close=1.1, wick_ratio=0.6)
    plan = pl.build_plan(df, EURUSD, tr, [], "aucun")
    assert plan.decision == pl.WAIT
    assert not plan.actionable


def test_entree_dans_la_zone_pas_au_prix_du_moment():
    """L'entrée est le niveau, pas le prix du moment.

    C'est la correction principale : l'ancien moteur entrait au prix courant,
    donc en dehors de la zone qu'il venait d'identifier.
    """
    # rebond sur 1.1000, puis le prix remonte de 5 pips
    df = zigzag([1.1000, 1.1002, 1.1005, 1.1004, 1.1003, 1.1005])
    levels = [
        lv.SRLevel(price=1.1000, kind="support", touches=3),
        lv.SRLevel(price=1.1100, kind="resistance", touches=3),
    ]
    # le rejet a eu lieu à la bougie 0 ; le prix est maintenant un peu plus haut
    tr = lv.Trigger(direction=lv.LONG, index=0, price=1.1000, close=1.1002, wick_ratio=0.6)
    plan = pl.build_plan(df, EURUSD, tr, levels, lv.LONG)
    assert plan.decision == pl.BUY
    assert plan.entry < float(df["Close"].iloc[-1])  # on n'entre pas au prix du moment
    assert plan.entry == pytest.approx(1.1000)      # on entre sur le niveau


def test_plan_refuse_si_le_price_a_trop_deja_parti():
    """Une limite qu'on ne peut plus poser n'est pas un plan.

    L'écart est mesuré en ATR : au-delà d'une bougie, l'entrée n'est plus
    honorable et le moteur propose d'attendre un nouveau rejet.
    """
    df = zigzag([1.1000, 1.1005, 1.1010, 1.1015, 1.1020, 1.1100])
    levels = [
        lv.SRLevel(price=1.1000, kind="support", touches=3),
        lv.SRLevel(price=1.1300, kind="resistance", touches=3),
    ]
    tr = lv.Trigger(direction=lv.LONG, index=0, price=1.1000, close=1.1005, wick_ratio=0.6)
    plan = pl.build_plan(df, EURUSD, tr, levels, lv.LONG)
    assert plan.decision == pl.WAIT
    assert any("nouveau rejet" in b for b in plan.blocks)
    assert plan.entry is None


def test_no_plan_explique():
    p = pl.no_plan("parce que")
    assert p.decision == pl.WAIT
    assert p.blocks == ["parce que"]


def test_ratio_est_recalcule_depuis_les_prix():
    df = zigzag(BOUNCE)
    levels = [
        lv.SRLevel(price=1.1000, kind="support", touches=3),
        lv.SRLevel(price=1.1150, kind="resistance", touches=3),
    ]
    tr = lv.Trigger(direction=lv.LONG, index=len(df) - 1, price=1.1000,
                    close=1.1020, wick_ratio=0.6)
    plan = pl.build_plan(df, EURUSD, tr, levels, lv.LONG)
    risk = abs(plan.entry - plan.stop)
    reward = abs(plan.target - plan.entry)
    assert plan.rr == pytest.approx(reward / risk)


def test_ratio_change_avec_le_minimum_demande():
    """Le seuil est un paramètre, pas une constante figée."""
    df = zigzag(BOUNCE)
    levels = [
        lv.SRLevel(price=1.1000, kind="support", touches=3),
        lv.SRLevel(price=1.1150, kind="resistance", touches=3),
    ]
    tr = lv.Trigger(direction=lv.LONG, index=len(df) - 1, price=1.1000,
                    close=1.1020, wick_ratio=0.6)
    assert pl.build_plan(df, EURUSD, tr, levels, lv.LONG, min_rr=0.5).actionable
    assert not pl.build_plan(df, EURUSD, tr, levels, lv.LONG, min_rr=99).actionable


# --------------------------------------------------------------------------- #
# Analyse complète
# --------------------------------------------------------------------------- #


def _synthetic_pair() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Un couple H1 / M15 cohérent : tendance haussière, rebond sur support.

    Le H1 donne une structure nette (vagues de 5 bougies, sommets et creux
    croissants). Le M15 replie le prix jusqu'au support du H1, puis rebondit —
    c'est exactement la configuration que le moteur doit reconnaître.
    """
    h1 = zigzag([
        1.0000, 1.0060, 1.0120, 1.0180, 1.0240,
        1.0150, 1.0100, 1.0160, 1.0220, 1.0280,
        1.0190, 1.0140, 1.0200, 1.0260, 1.0320,
        1.0230, 1.0180, 1.0240, 1.0300, 1.0360,
    ])
    m15 = zigzag([
        1.0360, 1.0330, 1.0300, 1.0260, 1.0220,
        1.0180, 1.0140, 1.0100, 1.0060, 1.0030,
        1.0050, 1.0090, 1.0130, 1.0180,
    ])
    return h1, m15


def test_analyse_complete_renvoie_un_rapport():
    h1, m15 = _synthetic_pair()
    report = an.analyse(EURUSD, h1, m15)
    assert report.ok
    assert report.structure.trend == stx.UP
    assert report.context_lines()
    assert report.verdict_lines()


def test_analyse_produit_une_scene_dessinable():
    h1, m15 = _synthetic_pair()
    scene = an.analyse(EURUSD, h1, m15).to_scene()
    assert scene.candles
    assert scene.steps
    assert scene.takeaway
    assert scene.digits == 5
    # la scène est cohérente comme celles des leçons
    from core.model import Level
    assert any(isinstance(a, Level) for a in scene.annotations)


def test_scene_donne_le_nombre_de_decimales_de_la_paire():
    h1, m15 = _synthetic_pair()
    assert an.analyse(USDJPY, h1, m15).to_scene().digits == 3


def test_scene_sur_echec_reste_dessinable():
    report = an.failed(EURUSD, "réseau coupé")
    scene = report.to_scene()
    assert scene.steps
    assert "réseau coupé" in scene.steps[0].text


def test_analyse_sans_structure_donne_attendre():
    h1 = zigzag([1.0, 1.0, 1.0, 1.0])
    m15 = zigzag([1.0, 1.0, 1.0, 1.0])
    report = an.analyse(EURUSD, h1, m15)
    assert report.waiting
    assert not report.plan.actionable


def test_echec_est_exploitable():
    report = an.failed(EURUSD, "pas de données")
    assert not report.ok
    assert report.error == "pas de données"
    assert report.context_lines() == []


def test_attendre_est_une_reponse_valide():
    """Le moteur doit pouvoir dire « rien à faire » sans que ce soit une panne."""
    h1, m15 = _synthetic_pair()
    report = an.analyse(EURUSD, h1, m15)
    assert report.decision in (an.BUY, an.SELL, an.WAIT)
    if report.waiting:
        assert report.plan.blocks
