# Plan de développement — Atelier Price Action

> Suivi de l'état du projet. Une case cochée = vérifié par un test ou par un
> contrôle exécutable, pas « ça a l'air de marcher ».

---

## Fondations

- [x] **Modèle de scène** (`src/core/model.py`) — bougies, annotations
      typées, étapes. Testé par `tests/test_model.py`.
- [x] **Canevas de rendu** (`src/core/canvas.py`) — conversion (index, prix) →
      pixels, révélation progressive, étiquettes ramenées dans le cadre.
      Testé par `tests/test_canvas.py`.
- [x] **Thème** (`src/core/theme.py`) — palette, association `kind` → couleur.
- [x] **Catalogue auto-découvert** (`src/lessons/__init__.py`) — ajouter un
      fichier suffit à ajouter une leçon, sans toucher à une liste centrale.
- [x] **Interface** (`src/ui/`) — liste des leçons, panneau d'étapes,
      raccourcis clavier ← → ↑ ↓.

## Contenu pédagogique

- [x] Structure de marché — HH+HL, LH+LL, range, cassure (4 leçons)
- [x] Support / résistance — zone, flip, force (3 leçons)
- [x] Liquidité — sommets égaux, sweep, piège du sweep (3 leçons)
- [x] Order blocks — haussier, baissier (2 leçons)
- [x] FVG — haussier, baissier (2 leçons)
- [x] Figures de bougies — pin bar, engulfing, inside bar (3 leçons)
- [x] Cassure / retest — retest, faux breakout (2 leçons)
- [x] Risque — anatomie, R:R, taille de position (3 leçons)

**22 leçons**, chacune en 3 étapes, chacune avec principe, explication et
« à retenir ».

## Qualité

- [x] **Tests** — 327 tests (`python -m pytest tests -q`), sans fenêtre
      ouverte (Qt en mode `offscreen`).
- [x] **Audit de mise en page** (`src/tools/audit.py`) — détecte ce qu'un œil
      ne voit pas sur un PNG : étiquettes hors cadre, étiquettes superposées,
      bougies incohérentes, contenu incomplet. Testé à 3 tailles de fenêtre.
- [x] **Rendu PNG** (`src/tools/render.py`) — export de toutes les leçons et de
      toutes leurs étapes, pour relecture hors ligne.
- [x] **Contrôle de la doc** (`tests/test_docs.py`) — références à des fichiers
      inexistants, caractères parasites.
- [x] **Lint** — `ruff` propre sur `src/core`, `src/lessons`, `src/ui`,
      `src/tools`, `tests`.

## Prochaine étape possible

- [ ] **Leçons manquantes** — ordre de structure interne (breakout of structure),
      order block mitigé, imbalance multi-bougies, gestion d'un trade gagnant
      (déplacer le stop), biais de séance.
- [ ] **Mode « quiz »** — masquer l'étape 3 et demander à l'utilisateur de
      trouver le biais, puis révéler.
- [ ] **Export PDF** — `render.py` produit déjà les PNG ; il ne reste qu'à les
      assembler en document.
- [ ] **Leçons sur données réelles** — trouver des occurrences réelles de chaque
      notion dans un historique et les annoter. À évaluer : l'intérêt pédagogique
      est réel, mais le bruit gêne.

## Héritage — ancien moteur de trading

`src/app.py`, `src/chart_widget.py`, `src/lib/` : l'ancienne application
d'analyse multi-timeframe avec IA locale. Elle n'est plus lancée, plus
documentée, plus testée.

Bugs connus relevés lors de l'audit, non corrigés (le code n'est plus
maintenu) :

| Fichier | Problème |
|---|---|
| `lib/price_action.py` | le paramètre `compute_signal` masque la fonction du même nom → `analyze_pair('EURUSD', compute_signal=True)` lève `TypeError` |
| `chart_widget.py` | les niveaux, le prix et Entrée/SL/TP sont tracés depuis l'index 0 au lieu de la fenêtre visible → invisibles par défaut |
| `lib/price_action.py` | `confidence` vaut structurellement ≥ 86 % (aucun facteur n'est neutre) ; HOLD est donc rare |
| `lib/ai.py` | inatteint |
| `lib/analysis.py` | `detect_candlestick_patterns` et `build_price_action_signal` morts ; ce dernier a `'pair': 'EUR/USD'` codé en dur |

Suppression ou conservation : à trancher. Voir la question ouverte.
