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

| # | KPI | Définition | Calcul | Intérêt pour le persona |
|---|---|---|---|---|
| 1 | **Taux de ponctualité** | % de vols arrivés avec ≤15 min de retard | `COUNT(ARR_DELAY <= 15) / COUNT(*)` | Indicateur principal de performance opérationnelle |
| 2 | **Retard moyen à l'arrivée** | Moyenne du retard en minutes | `AVG(ARR_DELAY) WHERE ARR_DELAY > 0` | Mesure l'ampleur des retards quand ils surviennent |
| 3 | **Taux d'annulation** | % de vols annulés | `SUM(CANCELLED) / COUNT(*)` | Impact direct sur la satisfaction client et les coûts |
| 4 | **Top causes de retard** | Répartition des causes | Distribution de `CARRIER_DELAY`, `WEATHER_DELAY`, etc. | Identifie les leviers d'amélioration actionnables |
| 5 | **Score de fiabilité par route** | Ponctualité pondérée par volume | Composite ponctualité × volume | Priorise les routes à optimiser en premier |

---

## 6. Stockage : du data lake à PostgreSQL

Les données suivent une architecture **médaillon** (bronze → silver → gold) dans un data lake S3 local (**RustFS**), au format **Delta Lake**, traitée avec **Spark**. Seules les tables gold, petites, sont copiées dans **PostgreSQL**, que lit le dashboard.

```
data/raw/ (CSV)  ──01_bronze──►  bronze/  ──02_silver──►  silver/  ──03_gold──►  gold/  ──►  PostgreSQL (gold_*)  ──►  Streamlit
                                 brut, texte              typé, nettoyé           agrégé
```

| Couche | Emplacement | Tables | Rôle |
|---|---|---|---|
| Fichiers source | `data/raw/` (non versionné) | 12 CSV `bts_2024_MM.csv`, `airports.csv` | Téléchargés par `scripts/telecharger_donnees.sh` |
| Bronze | `s3a://datalake/bronze/` | `vols` (7 079 061 lignes), `aeroports` (86 387) | Copie brute, toutes colonnes en texte |
| Silver | `s3a://datalake/silver/` | `vols` (7 078 487), `rejets` (574), `aeroports` (348), `compagnies` (15) | Données typées, nettoyées, référentiels |
| Gold | `s3a://datalake/gold/` + PostgreSQL | 5 tables `gold_*` | Une question métier = une table |

Consoles : RustFS sur http://localhost:9001 (`rustfsadmin` / `rustfsadmin`), Adminer sur http://localhost:8080 (système PostgreSQL, serveur `postgres`, `cours` / `cours`, base `vols`).

### 6.1 Bronze — `notebooks/01_bronze.ipynb`

- Spark lit les 12 CSV **sans typer** (`inferSchema=False`) : les 109 colonnes BTS restent en texte, sans filtre ni renommage. Une 110ᵉ colonne vide, `_c109`, vient de la virgule finale de chaque ligne : elle est gardée telle quelle.
- Deux colonnes techniques s'ajoutent : `_source_file` (fichier d'origine) et `_ingested_at` (heure d'ingestion).
- `bronze/vols` est partitionné par `Month` (un dossier par mois).
- **Ingestion idempotente** : seuls les fichiers absents de la table sont ajoutés, donc relancer le notebook ne crée pas de doublons.
- Démonstrations Delta : historique (`DESCRIBE HISTORY`), *time travel* (suppression de janvier, relecture de l'ancienne version, restauration) et refus d'une écriture au schéma incompatible.

### 6.2 Silver — `notebooks/02_silver.ipynb`

**Typage et sélection.** 30 colonnes sur 110 sont gardées et renommées en `snake_case` français : date, compagnie, origine, destination, heure de départ prévue, retards au départ et à l'arrivée, indicateur `retard_15`, annulation, déroutement, temps de vol, retard par cause. Les conversions utilisent `try_cast`, qui renvoie `NULL` au lieu de planter. `CRSDepTime = 2400` est accepté : c'est la notation BTS de minuit.

**Règles de nettoyage.** Chaque ligne reçoit la première règle qu'elle enfreint, ce qui garantit qu'une ligne n'est comptée qu'une fois. Les lignes retirées sont conservées dans `silver/rejets` avec leur motif, et le notebook vérifie que bronze = silver + rejets.

| Règle | Lignes retirées | Justification |
|---|---:|---|
| R1 — date, compagnie, origine ou destination manquante | 0 | Sans ces clés, le vol n'est rattachable à aucune analyse |
| R2 — doublon sur la clé du vol (date, compagnie, n° de vol, origine, heure prévue) | 0 | Un vol compté deux fois fausse tous les taux |
| R3 — heure de départ prévue invalide | 0 | Nécessaire à la heatmap jour × heure |
| R4 — vol opéré sans retard à l'arrivée connu | 0 | Ni « à l'heure » ni « en retard » : inclassable |
| R5 — retard à l'arrivée > 24 h | 567 | Valeurs extrêmes, jusqu'à 63 h, qui tirent les moyennes vers le haut |
| R6 — avance à l'arrivée > 90 min | 5 | Improbable sur un vol intérieur : erreur de saisie probable |
| R7 — `retard_15` incohérent avec le retard en minutes | 0 | La ponctualité repose sur cet indicateur |
| R8 — somme des 5 causes ≠ retard (vols ≥ 15 min de retard) | 2 | Sinon la part par cause du gold serait fausse |
| **Total** | **574 (0,008 %)** | |

Les données BTS sont très propres : une règle à 0 n'est pas inutile, elle prouve que le cas a été contrôlé.

**Vols annulés (96 315) et détournés (17 499) : conservés.** Ce ne sont pas des erreurs, et le gold en a besoin pour le taux d'annulation et pour les exclure du dénominateur de ponctualité. Les booléens `annule` et `detourne` permettent de les isoler.

**Référentiels.**
- `silver/aeroports` contient les 348 aéroports desservis. La ville et l'état viennent des vols BTS ; le nom, la latitude, la longitude et la page Wikipédia viennent d'OurAirports, par jointure sur le code IATA. Une correction est nécessaire : West Palm Beach (`PBI` dans les données 2024) est devenu `DJT` le 18/08/2026, et OurAirports ne connaît plus que ce nouveau code. Les coordonnées sont donc lues sous `DJT`, alors que les tables gardent `PBI`.
- `silver/compagnies` donne le nom des 15 compagnies présentes en 2024. Les vols ne contiennent que leur code : les noms ont été saisis à la main dans le notebook, et celui-ci vérifie qu'aucun code des vols n'est oublié.

### 6.3 Gold — `notebooks/03_gold.ipynb`

Chaque table est écrite en Delta dans `gold/<nom>` puis copiée dans PostgreSQL avec `vers_postgres()`.

| Table PostgreSQL | Une ligne = | Lignes | Colonnes | Répond à |
|---|---|---:|---|---|
| `gold_ponctualite_mensuelle` | mois × compagnie | 180 | `mois` (date), `compagnie_code`, `compagnie_nom`, `vols`, `pct_a_l_heure`, `pct_annules`, `retard_moyen_min` | Contexte : tendance et saisonnalité |
| `gold_causes_retard` | mois × compagnie × cause | 900 | `mois`, `compagnie_code`, `cause`, `controlable`, `minutes`, `part_pct` | Constat : quelles causes, contrôlables ou non |
| `gold_aeroports` | aéroport d'origine | 348 | `code_iata`, `ville`, `etat`, `lat`, `lon`, `departs`, `pct_a_l_heure`, `retard_moyen_min`, `pct_annules` | Constat : carte des points noirs |
| `gold_heure_jour` | jour de semaine × heure prévue | 168 | `jour_semaine` (1 = lundi), `heure` (0–23), `vols`, `pct_retard` | Constat : heatmap des créneaux à risque |
| `gold_routes` | origine × destination | 6 805 | `origine`, `destination`, `vols`, `pct_a_l_heure`, `retard_moyen_min`, `score_priorite` | Recommandation : routes à traiter en premier |

Toutes les tables sauf `gold_causes_retard` ont aussi trois colonnes de comptes : `vols_operes`, `vols_a_l_heure` et `vols_annules`.

**Définitions**

- `vols` : vols programmés, annulés et détournés compris. Un vol **opéré** n'est ni annulé ni détourné.
- **À l'heure** : vol opéré arrivé avec moins de 15 min de retard (`retard_15 = 0`). Le seuil de 15 min est celui du DOT.
- `pct_a_l_heure = 100 × vols_a_l_heure / vols_operes` ; `pct_annules = 100 × vols_annules / vols` ; `retard_moyen_min` est la moyenne du retard à l'arrivée des vols opérés, les avances comptant en négatif.
- `part_pct = 100 × minutes de la cause / minutes de toutes les causes`, par mois × compagnie. Les causes `compagnie` et `avion_retard` sont `controlable`.
- `score_priorite = vols × (1 − pct_a_l_heure / 100)`. Il approche le nombre de vols en retard, mais le dépasse un peu car `vols` inclut les annulés ; le nombre exact est `vols_operes − vols_a_l_heure`.

**Écart avec le chiffre officiel.** Le DOT garde les vols annulés et détournés au dénominateur et publie 78,10 % de vols à l'heure pour 2024 ([BTS](https://www.bts.gov/newsroom/air-travel-consumer-report-december-2024-full-year-2024-numbers)). Ce projet les exclut, pour mesurer la ponctualité des vols qui ont effectivement volé, les annulations ayant leur propre indicateur. On obtient **79,2 %**, et **77,9 %** avec la méthode du DOT.

**Ré-agréger correctement.** Dès qu'un filtre regroupe plusieurs lignes (plusieurs mois ou compagnies), on recalcule les taux à partir des comptes, jamais en faisant la moyenne des pourcentages :

```sql
SELECT 100.0 * SUM(vols_a_l_heure) / SUM(vols_operes) AS pct_a_l_heure,
       100.0 * SUM(vols_annules)   / SUM(vols)        AS pct_annules
FROM gold_ponctualite_mensuelle WHERE compagnie_code IN ('AA', 'DL');
-- causes : SUM(minutes) par cause, puis division par le total (jamais AVG(part_pct))
```

**Contrôles du notebook.** Chaque table gold totalise les 7 078 487 vols du silver. Les parts des causes font 100 % à 0,02 point près, à cause des arrondis. Aucune compagnie n'est sans nom, aucun aéroport sans coordonnées, aucune route sans score.

### 6.4 Exécution et mémoire

| Notebook | Durée | Produit |
|---|---|---|
| `01_bronze` | ~3 min 30 | `bronze/vols`, `bronze/aeroports` |
| `02_silver` | ~1 min | `silver/vols`, `rejets`, `aeroports`, `compagnies` |
| `03_gold` | ~35 s | 5 tables `gold_*` dans le data lake et PostgreSQL |

Ces durées ont été mesurées sur un Mac avec 8 Go alloués à Docker. Le premier démarrage de Spark télécharge en plus les jars Delta, S3 et JDBC, qui sont ensuite gardés en cache.

- **Un seul notebook Spark ouvert à la fois.** Chaque noyau garde sa session Spark (2 à 5 Go) : à deux, on dépasse 8 Go et Linux arrête Spark (`Py4JNetworkError` / `Connection refused`). Pour fermer vraiment un notebook : *File → Close and Shut Down Notebook*, car fermer l'onglet ne suffit pas.
- **Pas de `spark.createDataFrame(liste)`** pour les petites tables de correspondance : il démarre un worker Python d'environ 360 Mo par cœur. On utilise `F.create_map(...)` à la place.
- **Pas de disque exFAT.** Sur un disque externe exFAT, Docker ne peut pas réécrire un fichier qu'il vient de créer : JupyterLab ne peut plus sauvegarder les notebooks. Il faut placer le dépôt sur le disque interne.
