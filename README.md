# DataViz — Vols et retards aériens aux États-Unis

**Projet Visualisation de données** — Sup de Vinci, Mastère Big Data & IA — M1  
Session 2026-2027 · Enseignant : M. L. NDAO

**Auteurs :** Sami & Rayane

---

## 1. Le jeu de données

**Source :** [Bureau of Transportation Statistics (BTS)](https://www.transtats.bts.gov/Tables.asp?QO_VQ=EFD) — *Reporting Carrier On-Time Performance*

Le dataset contient l'intégralité des vols commerciaux intérieurs aux États-Unis, publiés mensuellement par le Département des Transports américain (DOT).

| Caractéristique | Détail |
|---|---|
| **Volume** | ~6 millions de lignes par an (nous utilisons 2023 + 2024, soit ~12M lignes) |
| **Dimension temporelle** | Date du vol (`FL_DATE`), heure de départ/arrivée prévue et réelle |
| **Dimension géographique** | Aéroport d'origine et de destination (code IATA, ville, état, coordonnées) |
| **Format** | CSV zippés, un fichier par mois |
| **Licence** | Données publiques du gouvernement américain (domaine public) |

### Colonnes principales

| Colonne | Description |
|---|---|
| `FL_DATE` | Date du vol |
| `OP_UNIQUE_CARRIER` | Code de la compagnie aérienne |
| `ORIGIN` / `DEST` | Codes IATA des aéroports d'origine et de destination |
| `DEP_DELAY` | Retard au départ (en minutes, négatif = en avance) |
| `ARR_DELAY` | Retard à l'arrivée (en minutes) |
| `CANCELLED` | Vol annulé (1) ou non (0) |
| `CANCELLATION_CODE` | Cause d'annulation (A=compagnie, B=météo, C=NAS, D=sécurité) |
| `AIR_TIME` | Temps de vol effectif (minutes) |
| `DISTANCE` | Distance du trajet (miles) |
| `CARRIER_DELAY`, `WEATHER_DELAY`, `NAS_DELAY`, `SECURITY_DELAY`, `LATE_AIRCRAFT_DELAY` | Décomposition du retard par cause |

---

## 2. Le persona

### Sarah Chen — Directrice des Opérations, compagnie aérienne régionale

| | |
|---|---|
| **Qui** | Directrice des opérations d'une compagnie aérienne régionale opérant sur le marché domestique US |
| **Ce qu'elle décide** | Allocation des ressources, ajustements de planning, choix des routes à renforcer ou abandonner |
| **Fréquence** | Revue hebdomadaire des performances, planification trimestrielle des routes |
| **Question principale** | *« Quels sont les aéroports, les routes et les périodes qui génèrent le plus de retards, et quelles en sont les causes principales, pour optimiser notre ponctualité ? »* |

### Sous-questions du persona

1. Quels aéroports concentrent les retards les plus fréquents et les plus longs ?
2. Les retards sont-ils saisonniers ? Quels mois/jours sont les plus critiques ?
3. Quelle est la part de chaque cause de retard (météo, compagnie, contrôle aérien) ?
4. Quelles routes présentent le pire ratio ponctualité/volume ?
5. Comment notre performance se compare-t-elle aux autres compagnies sur les mêmes routes ?

---

## 3. Architecture du projet

```
├── README.md
├── docker-compose.yml
├── scripts/
│   └── download_data.py        # Téléchargement des données BTS
├── notebooks/
│   ├── 01_bronze.ipynb         # Ingestion brute → Delta (MinIO/S3)
│   ├── 02_silver.ipynb         # Nettoyage, typage, validation
│   ├── 03_gold.ipynb           # Agrégats → PostgreSQL
│   └── 04_exploration.ipynb    # Exploration & visualisations (avant/après)
├── ontology/
│   ├── flights.ttl             # Ontologie OWL/RDF du domaine
│   └── queries.sparql          # Requêtes SPARQL
├── streamlit/
│   ├── app.py                  # Dashboard Streamlit
│   └── requirements.txt
├── docker/
│   └── Dockerfile.streamlit
└── data/                       # (non versionné) données téléchargées
```

---

## 4. Lancement

```bash
# 1. Télécharger les données
pip install -r scripts/requirements.txt
python scripts/download_data.py

# 2. Lancer l'infrastructure
docker compose up -d

# 3. Exécuter les notebooks dans l'ordre
#    01_bronze → 02_silver → 03_gold → 04_exploration

# 4. Le dashboard Streamlit est accessible sur http://localhost:8501
```

---

## 5. KPI du tableau de bord

Les quatre KPI du dashboard et leur fiche (définition, calcul, intérêt pour la directrice) sont en
**section 7.4**. Ils sont calculés sur les tables gold et suivent le contrat : « à l'heure » = arrivé avec moins
de 15 min de retard, annulés et détournés exclus du dénominateur.

---

## 7. Sémantique et visualisation

Cette partie couvre la couche sémantique (S03) et la restitution (S04–S06) :

```
ontologie/vols.ttl ──┐
sem_* (03_gold) ─────┴─► 04_semantique (rdflib) ─► ontologie/graphe_vols.ttl ─► Fuseki :3030 ─► requetes.sparql
gold_* (PostgreSQL) ───► 05_exploration (pandas, matplotlib) : choix des graphiques, avant / après
gold_* (PostgreSQL) ───► app/app.py (Streamlit, plotly) :8501 : Contexte → Constat → Recommandation
```

### 7.1 Ontologie — `ontologie/vols.ttl`

Le fichier ne contient que le schéma (T-Box) ; les instances sont générées par `04_semantique`. Vocabulaire
dans l'espace `vols:` (`http://example.org/vols/ontologie#`), un espace par type d'instance (`aer:ATL`, `cie:DL`,
`route:LAX-SFO`, `vol:…`, `etat:CA`, `imp:…`).

| Classe | Rôle |
|---|---|
| `Vol` | un vol programmé (peut être annulé ou détourné) |
| `Aeroport` ⊃ **`Hub`** | un hub assure au moins 1 % des départs nationaux (seuil *large hub* de la FAA) |
| `Compagnie`, `Route`, `Etat` | qui opère, quelle liaison orientée, quel État |
| `CauseRetard` ⊃ **`CauseControlable`** / **`CauseNonControlable`** | les 5 causes BTS, rangées selon que la compagnie peut agir dessus |
| `ImputationRetard` | « tel vol a N minutes de retard dues à telle cause » (relation n-aire, motif du W3C) |

```
CauseRetard                                   Aeroport
├── CauseControlable     compagnie,           └── Hub      (≥ 1 % des départs)
│                        avion_retard
└── CauseNonControlable  meteo, nas, securite
```

- **10 propriétés objet** (`operePar`, `aeroportDepart`, `aeroportArrivee`, `surRoute`, `aImputation`, `cause`,
  `causeAnnulation`, `origine`, `destination`, `situeDans`) et **26 propriétés de données** (types XSD, unités en
  commentaire), toutes avec domaine et portée.
- Les deux sous-classes de causes sont **disjointes et couvrent** `CauseRetard` ; les classes principales sont
  déclarées disjointes (`owl:AllDisjointClasses`).
- `Hub` a une **définition formelle OWL 2** : `Hub ≡ Aeroport ⊓ ∃ partDepartsPct . [≥ 1.0]`.
- Les annulations réutilisent les mêmes causes (`causeAnnulation`, codes A–D) : elles se rangent dans la même
  hiérarchie.

### 7.2 Graphe d'instances — `notebooks/04_semantique.ipynb`

Le notebook lit les tables `sem_*` préparées par `03_gold` (sans Spark), construit le graphe avec **rdflib** et
l'exporte dans `ontologie/graphe_vols.ttl` (schéma + instances : le fichier se charge seul dans Fuseki ou Protégé).

| Contenu | Nombre |
|---|---|
| Aéroports (tous), typés `Hub` ou `Aeroport`, avec coordonnées, départs et État | 348, dont 30 hubs |
| Compagnies | 15 |
| Routes au plus fort `score_priorite` (avec rang et indicateurs gold) | 50 |
| Vols échantillonnés sur ces routes, avec leurs imputations de retard par cause | 500 |
| Liens `owl:sameAs` des hubs vers **Wikidata** | 30 |

- Un hub n'est **pas** typé `Aeroport` explicitement : les requêtes le retrouvent par `a/rdfs:subClassOf*`.
- Les identifiants Wikidata ont été obtenus par une requête sur `query.wikidata.org` (code IATA `P238`, pays
  `P17` = États-Unis), documentée dans le notebook ; deux homonymes (AUS, EWR) ont été départagés à la main.
- **Contrôles** avant export : la hiérarchie retrouve les 348 aéroports, la somme des imputations d'un vol en
  retard égale son retard à l'arrivée, chaque vol part de l'origine de sa route.
- **Fuseki** (`docker compose --profile semantique up -d`, http://localhost:3030) : le notebook crée le dataset
  `vols` (TDB2) s'il manque, puis remplace son graphe (`PUT`, *Graph Store Protocol*) ; relancer ne duplique rien.
  **Repli** : si Fuseki n'est pas lancé, les mêmes requêtes passent par rdflib.

### 7.3 Requêtes SPARQL — `ontologie/requetes.sparql`

Quatre requêtes commentées, exécutées dans la section 7 de `04_semantique` (lues dans le fichier) et
copiables dans l'interface de Fuseki.

| Requête | Question du persona | Ce qu'elle exploite |
|---|---|---|
| **Q1** | Au départ de quels hubs les retards sont-ils surtout contrôlables ? | les **deux hiérarchies** : `a/rdfs:subClassOf* vols:Hub` et `?cause a/rdfs:subClassOf* vols:CauseControlable` |
| Q2 | Quelles routes traiter en premier, entre quelles villes ? | le parcours route → aéroports → États (hub à hub, intra-État) |
| Q3 | Comment se comparent les compagnies sur ces routes ? | `estEnRetard` n'existe que pour les vols opérés : le dénominateur du contrat sans filtre |
| Q4 | Où se concentrent les hubs ? | les liens `owl:sameAs` ; variante **fédérée** qui va chercher la date d'ouverture des hubs dans Wikidata |

**Pourquoi Q1 serait plus lourde en SQL** (la requête SQL complète est en commentaire dans le fichier) :
- SQL n'a pas de sous-classes : il faut une table de hiérarchie et un `WITH RECURSIVE` là où SPARQL écrit
  `rdfs:subClassOf*` ;
- les cinq causes sont cinq colonnes : il faut cinq `SELECT … UNION ALL` pour les dépivoter, et ajouter une cause
  change le schéma **et** chaque requête ; dans le graphe, c'est un individu de plus et la requête ne change pas ;
- « hub » et « contrôlable » deviennent des colonnes recopiées (`est_hub`, `controlable` sur chaque ligne de
  `gold_causes_retard`) : reclasser une cause oblige à recalculer la table, alors que dans l'ontologie c'est un
  triplet.

### 7.4 KPI du tableau de bord

Quatre KPI, en tête du dashboard. Chacun a sa fiche dans un `st.expander` sous sa valeur. Ils sont **ré-agrégés à
partir des comptes** (`vols_operes`, `vols_a_l_heure`, `vols_annules`, `minutes`), jamais par moyenne de
pourcentages : un mois de 120 000 vols pèse plus qu'un mois de 6 000. Quand une compagnie est choisie, chaque KPI
affiche son écart à l'ensemble des compagnies sur la même période.

| KPI | Définition | Calcul (tables gold) | Intérêt pour la directrice |
|---|---|---|---|
| **Ponctualité à l'arrivée** | part des vols opérés arrivés avec moins de 15 min de retard (définition du DOT) | `100 × Σ vols_a_l_heure / Σ vols_operes` — `gold_ponctualite_mensuelle` | l'indicateur de référence, publié par le DOT ; c'est lui que les actions doivent faire monter |
| **Retard moyen à l'arrivée** | retard moyen des vols opérés, avances comptées en négatif (min) | `Σ (retard_moyen_min × vols_operes) / Σ vols_operes` | la ponctualité dit combien de vols sont en retard, pas de combien : l'ampleur fait les correspondances manquées et les coûts |
| **Taux d'annulation** | part des vols programmés annulés | `100 × Σ vols_annules / Σ vols` | les annulés sont exclus de la ponctualité : sans ce KPI, annuler un vol fragile « améliorerait » la ponctualité |
| **Part des retards contrôlables** | part des minutes de retard dues à la compagnie ou à un avion en retard de son vol précédent | `Σ minutes (controlable) / Σ minutes` — `gold_causes_retard` | dit quelle part du problème la compagnie peut réduire elle-même : l'ambition réaliste d'un plan d'action |

### 7.5 Exploration et choix des graphiques — `notebooks/05_exploration.ipynb`

Le notebook explore les tables gold (pandas, matplotlib) et fixe la forme de chaque graphique repris dans le
dashboard. Règles appliquées partout (S04) : **titre = la conclusion** (calculé sur les données, donc toujours
vrai), sous-titre = la mesure, unités sur les axes, **barres depuis 0**, pas de camembert ni d'arc-en-ciel,
**une seule couleur d'accent** (bleu = « là où agir », le reste en gris), **étiquettes directes** plutôt que légende.

| Question du persona | Graphique | Pourquoi cette forme |
|---|---|---|
| Les retards sont-ils saisonniers ? | courbe mensuelle de ponctualité, moyenne annuelle en repère | une évolution dans le temps se lit sur une ligne ; une ligne code par la position, son axe n'a pas à partir de 0 (plage de 30 points pour ne pas grossir les écarts) |
| Comment se placent les compagnies ? | barres horizontales triées, bleu = sous la moyenne | la longueur se compare mieux que tout autre codage ; le tri donne le rang ; les noms se lisent sans pivoter |
| Où sont les points noirs ? | 20 plus gros aéroports en barres ; **carte** dans le dashboard (taille = départs) | le volume compte autant que le taux : un grand hub en retard désorganise tout le réseau |
| Quels créneaux sont à risque ? | **heatmap** jour × heure | deux dimensions ordonnées et une grandeur : une seule teinte du clair au foncé, échelle depuis 0 |
| Quelles routes traiter en premier ? | barres du `score_priorite` (≈ vols en retard sur l'année) | une seule série, donc une seule couleur ; score et ponctualité écrits au bout de chaque barre |
| Quelles causes, et sur lesquelles agir ? | **avant / après** ci-dessous | — |

**Avant / après.** Le camembert des causes (cinq couleurs par défaut, codes techniques, titre « Causes de
retard ») est refait en **barres horizontales triées** depuis 0 : les causes contrôlables en bleu, les autres en
gris, la valeur au bout de chaque barre et une accolade qui nomme chaque groupe et son total. Le titre devient la
conclusion (« X % des minutes de retard ont une cause que la compagnie contrôle »). Chaque correction est justifiée
dans le notebook : **Cleveland & McGill** (une longueur se juge mieux qu'un angle ou une aire), **couleur = sens**
(la seule distinction utile, contrôlable ou non), **ratio données / encre** (Tufte), **étiquettes directes**.

La palette (accent `#257de0`, gris `#b4b4b4`, rampe bleue pour la heatmap) a été vérifiée au validateur de
palettes : l'accent et le gris restent distincts pour les trois formes de daltonisme.

### 7.6 Dashboard — `app/app.py` (http://localhost:8501)

Le dashboard suit le récit **Contexte → Constat → Recommandation** :

| Temps | Contenu |
|---|---|
| **1 · Contexte** | les 4 KPI et leurs fiches ; courbe mensuelle de ponctualité (sélection en bleu, marché en gris) |
| **2 · Constat** | causes en barres (version « après ») ; carte des aéroports ; heatmap jour × heure |
| **3 · Recommandation** | 10 routes au plus fort `score_priorite` ; une **phrase d'action** calculée (routes à traiter, part contrôlable, part « avion en retard », heure la plus exposée) ; tableau des routes |

- **Filtres** sur une ligne, au-dessus de tout ce qu'ils filtrent : **compagnie(s)**, **période** (mois), **aéroport**.
  Les tables gold n'ont pas toutes les mêmes dimensions : une ligne sous chaque graphique dit quels filtres s'y
  appliquent (par exemple, la carte et la heatmap couvrent toujours l'année entière, toutes compagnies).
- **Données fictives** : si PostgreSQL ou les tables `gold_*` sont absents, le dashboard affiche
  `app/donnees_fictives.py` (les cinq tables du contrat, au format exact, chiffres inventés) avec un bandeau
  d'avertissement. `DONNEES_FICTIVES=1` force ce mode.
- Lancement : service `streamlit` du compose (`docker compose up -d`), ou en local :
  `cd app && pip install -r requirements.txt && streamlit run app.py` (variables `PG_HOST`, `PG_PORT`, `PG_DB`,
  `PG_USER`, `PG_PASSWORD`).
