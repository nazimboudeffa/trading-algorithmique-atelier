# Atelier Price Action — support pédagogique visuel

Un logiciel de bureau qui **explique les principes du Price Action par l'image**.

Chaque notion est illustrée par un schéma construit à la main : on ne voit pas
du bruit de marché réel, mais le cas idéal, puis l'erreur classique, puis la
règle. L'affichage est progressif — le schéma se révèle étape par étape, ce qui
apprend bien plus qu'une figure déjà annotée.

## Démarrage

```bash
setup.bat        # création du venv + installation (1ʳᵉ fois)
run.bat          # lancement de l'atelier
```

L'atelier est autonome : aucune donnée de marché, aucun réseau, aucun modèle IA.

## Utilisation

- **Colonne de gauche** : les 22 leçons, groupées par thème.
- **← / →** : avancer/reculer d'une étape dans la leçon courante.
- **↑ / ↓** : passer à la leçon précédente/suivante.
- **Tout voir** : affiche le schéma complet d'un coup.

Chaque leçon suit la même structure : un **principe** en haut, le **schéma**
au centre, l'**explication de l'étape** courante en dessous, et l'**à retenir**
en bas.

## Programme

| Thème | Leçons |
|---|---|
| Structure | HH+HL (tendance), LH+LL (tendance), range, la cassure de structure |
| Support/résistance | un niveau est une zone, le flip (support → résistance), ce qui rend un niveau solide |
| Liquidité | sommets égaux, le sweep, le piège du sweep |
| Order blocks | haussier, baissier |
| FVG | haussier, baissier |
| Bougies | pin bar, engulfing, inside bar |
| Cassure/retest | entrer sur le retest, le faux breakout |
| Risque | anatomie d'un trade, R:R et règle des 2:1, taille de position |

## Structure du projet

```
src/
  core/          modèle de scène + canevas de rendu (indépendant des leçons)
    model.py     Candle, Level, Zone, Marker, Arrow, Path, Scene, Step
    canvas.py    ChartCanvas : conversion (index, prix) -> pixels, révélation
    theme.py     palette
  lessons/       une notion = un module exposant SCENES()
  ui/            LessonPanel (leçon + pas-à-pas), MainWindow
  tools/         audit.py (mise en page), render.py (PNG)
  main.py        point d'entrée
tests/           317 tests (modèle, canevas, catalogue de leçons)
```

Le registre des leçons se construit tout seul : déposer un fichier dans
`src/lessons/` exposant `SCENES()` suffit pour l'ajouter au programme.

## Ajouter une leçon

```python
from core.model import Level, Marker, Scene, build

def ma_lecon() -> Scene:
    scene = Scene(
        id="xx-mon-theme",
        title="Titre affiché",
        principle="La phrase qui résume la notion.",
        candles=build(1.0850, [1.0852, 1.0861, 1.0860, 1.0840]),
        takeaway="Ce qu'il faut retenir une fois la leçon finie.",
    )
    scene.add(
        Level(price=1.0850, label="Support", kind="support", step=1),
        Marker(index=3, price=1.0840, text="rejet", kind="good", step=2),
    )
    scene.at(
        ("1. Première étape", "Explication de l'étape 1."),
        ("2. Deuxième étape", "Explication de l'étape 2."),
        ("3. Conclusion", "Explication de l'étape 3."),
    )
    return scene

def SCENES() -> list[Scene]:
    return [ma_lecon()]
```

L'étape est portée par le champ `step` des annotations et des bougies : un
élément marqué `step=2` n'apparaît qu'à partir de la deuxième étape.

## Développement

```bash
python -m pytest tests -q        # 317 tests
python src/tools/audit.py        # mise en page, géométrie, contenu des leçons
python src/tools/render.py       # export PNG de toutes les leçons
python -m ruff check src tests
```

`audit.py` contrôle ce qu'un œil ne voit pas sur un PNG : étiquettes hors
cadre, étiquettes superposées, bougies incohérentes, contenu pédagogique
incomplet, texte tronqué.

## Ancien moteur de trading

`src/app.py`, `src/chart_widget.py` et `src/lib/` sont l'ancienne application
d'analyse multi-timeframe. Elle n'est plus utilisée ni documentée ici, et n'est
plus couverte par les tests. Voir la section « Héritage » du guide si besoin.

## AVERTISSEMENT

> [!WARNING]
> **PROJET STRICTEMENT ÉDUCATIF**
>
> Cet atelier est un support d'apprentissage. Il ne constitue **en aucun cas**
> un conseil en investissement, une recommandation financière, une incitation à
> acheter ou vendre un actif, ni une promesse de performance.
>
> Les notions présentées décrivent des schémas observés sur des prix, pas des
> règles gagnantes. Les marchés sont volatils et imprévisibles ; une méthode
> qui semble cohérente sur un schéma peut se révéler fausse en conditions
> réelles.
>
> **Si vous tradez, vous pouvez perdre une part importante de votre capital,
> voire la totalité de ce qui est engagé.** N'utilisez jamais ce type d'outil
> avec de l'argent que vous ne pouvez pas perdre. Vous le faites à vos seuls
> risques et sous votre entière responsabilité.
