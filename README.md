# DataViz — Vols et retards aériens aux États-Unis

**Projet Visualisation de données** — Sup de Vinci, Mastère Big Data & IA — M1  
Session 2026-2027 · Enseignant : M. L. NDAO

**Auteurs :** Sami & Rayane

---

## 1. Le jeu de données

**Source :** [Bureau of Transportation Statistics (BTS)](https://www.transtats.bts.gov/Tables.asp?QO_VQ=EFD), table *Reporting Carrier On-Time Performance (1987-present)*. Les fichiers mensuels viennent de `https://transtats.bts.gov/PREZIP/`, et le téléchargement est fait par `scripts/telecharger_donnees.sh`.

Chaque ligne est un vol intérieur programmé par une compagnie américaine, avec ses horaires prévus et réels, ses retards, son éventuelle annulation et la répartition de son retard par cause.

| Caractéristique | Détail |
|---|---|
| **Volume** | **7 079 061 vols**, l'année 2024 complète (le minimum demandé est de 2 M de lignes) |
| **Format** | 12 CSV, un par mois (environ 3 Go décompressés), 109 colonnes |
| **Dimension temporelle** | Date du vol, jour de la semaine, heures de départ et d'arrivée prévues et réelles |
| **Dimension géographique** | Aéroports d'origine et de destination (code IATA, ville, état). Les coordonnées viennent d'un second jeu, [OurAirports](https://ourairports.com/data/) (`airports.csv`), joint sur le code IATA |
| **Compagnies** | 15 compagnies (code BTS, par exemple `WN` Southwest, `DL` Delta) |
| **Licence** | Données publiques du gouvernement américain ; OurAirports est dans le domaine public |

### Colonnes principales (noms BTS)

| Colonne BTS | Nom en silver | Description |
|---|---|---|
| `FlightDate`, `DayOfWeek` | `date_vol`, `jour_semaine` | Date du vol, jour de la semaine (1 = lundi) |
| `Reporting_Airline`, `Flight_Number_Reporting_Airline` | `compagnie_code`, `numero_vol` | Compagnie qui opère le vol, numéro de vol |
| `Origin`, `Dest` | `origine`, `destination` | Codes IATA des aéroports |
| `CRSDepTime` | `heure_depart_prevue` | Heure de départ prévue (`HHMM`, heure locale) |
| `DepDelay`, `ArrDelay` | `retard_depart_min`, `retard_arrivee_min` | Retards au départ et à l'arrivée, en minutes (négatif = en avance) |
| `ArrDel15` | `retard_15` | 1 si le vol arrive avec 15 min de retard ou plus |
| `Cancelled`, `CancellationCode`, `Diverted` | `annule`, `code_annulation`, `detourne` | Annulation (A compagnie, B météo, C contrôle aérien, D sécurité), déroutement |
| `AirTime`, `Distance` | `temps_vol_min`, `distance_miles` | Temps de vol (min), distance (miles) |
| `CarrierDelay`, `LateAircraftDelay`, `WeatherDelay`, `NASDelay`, `SecurityDelay` | `retard_compagnie_min`, `retard_avion_min`, `retard_meteo_min`, `retard_nas_min`, `retard_securite_min` | Répartition du retard par cause (min), renseignée pour les vols arrivés avec 15 min de retard ou plus |

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
├── compose.yaml                  # Stack Docker : Jupyter/Spark, RustFS, PostgreSQL, Adminer, Streamlit, Fuseki
├── .env.example                  # Identifiants par défaut (à copier en .env)
├── scripts/
│   └── telecharger_donnees.sh    # Télécharge les 12 mois BTS 2024 et airports.csv dans data/raw/
├── commun/                       # Outils repris du dépôt du cours
│   ├── spark_utils.py            # creer_session(), LAKE, vers_postgres()
│   └── donnees.py                # lire() : tables PostgreSQL → pandas
├── notebooks/                    # À exécuter dans l'ordre
│   ├── 01_bronze.ipynb           # CSV → bronze (Delta, RustFS)
│   ├── 02_silver.ipynb           # Typage, 8 règles de nettoyage, référentiels
│   ├── 03_gold.ipynb             # Tables gold_* et sem_* → PostgreSQL
│   ├── 04_semantique.ipynb       # Graphe RDF (rdflib) → ontologie/graphe_vols.ttl → Fuseki
│   └── 05_exploration.ipynb      # Exploration des tables gold, avant / après
├── ontologie/
│   ├── vols.ttl                  # Ontologie OWL (classes, hiérarchies, propriétés)
│   ├── graphe_vols.ttl           # Graphe d'instances exporté par 04_semantique
│   └── requetes.sparql           # Requêtes SPARQL commentées
├── app/                          # Dashboard Streamlit (service « streamlit » du compose)
│   ├── app.py
│   ├── donnees_fictives.py       # Données de secours si PostgreSQL est vide
│   ├── Dockerfile
│   └── requirements.txt
└── data/                         # Non versionné : créé par le script de téléchargement
```

Le data lake (bronze, silver, gold) n'est pas un dossier du dépôt : il vit dans le volume Docker de RustFS (`s3a://datalake/…`, voir la section 6). Les tables gold sont copiées dans PostgreSQL (volume `pg-data`).

---

## 4. Lancement

**Prérequis**
- Docker Desktop avec **8 Go de mémoire** alloués (*Settings → Resources*).
- Environ **15 Go d'espace disque libre** : 3 Go de CSV, 1,8 Go de data lake, 7 Go pour l'image Jupyter/Spark et environ 2 Go pour les autres images.
- Le dépôt sur le **disque interne**. Sur un disque externe exFAT, Docker ne peut pas réécrire les fichiers, et JupyterLab ne sauvegarde plus les notebooks.

**1. Récupérer le projet et les données**
```bash
git clone <url-du-dépôt> projet-dataviz && cd projet-dataviz
cp .env.example .env
bash scripts/telecharger_donnees.sh      # 12 CSV BTS 2024 + airports.csv dans data/raw/ (~330 Mo à télécharger)
```
Le script saute les fichiers déjà présents : on peut le relancer s'il est interrompu.

**2. Démarrer la stack**
```bash
docker compose --profile semantique up -d --build
```
Le profil `semantique` ajoute Fuseki, utilisé par `04_semantique`. `--build` construit l'image du dashboard. Sans Fuseki, `docker compose up -d --build` suffit, et `04_semantique` passe alors par rdflib.

| Service | Adresse | Identifiants |
|---|---|---|
| JupyterLab | http://localhost:8888/lab?token=cours | jeton `cours` |
| Console RustFS (data lake) | http://localhost:9001 | `rustfsadmin` / `rustfsadmin` |
| Adminer (PostgreSQL) | http://localhost:8080 | système PostgreSQL, serveur `postgres`, `cours` / `cours`, base `vols` |
| Fuseki (SPARQL) | http://localhost:3030 | `admin` / `admin` |
| Dashboard | http://localhost:8501 | — |

**3. Exécuter les notebooks dans l'ordre**

Dans JupyterLab, ouvrir `work/notebooks/`, puis pour chaque notebook : *Run → Run All Cells*, et *File → Close and Shut Down Notebook* avant de passer au suivant.

| Notebook | Durée | Produit |
|---|---|---|
| `01_bronze` | ~3 min 30 | `bronze/vols`, `bronze/aeroports` |
| `02_silver` | ~1 min | `silver/vols`, `rejets`, `aeroports`, `compagnies` |
| `03_gold` | < 1 min | tables `gold_*` (dashboard) et `sem_*` (graphe) dans PostgreSQL |
| `04_semantique` | — | `ontologie/graphe_vols.ttl`, chargé dans Fuseki |
| `05_exploration` | — | graphiques et avant / après |

Le premier démarrage de Spark télécharge les jars Delta, S3 et JDBC (environ 1,5 Go), ce qui prend quelques minutes ; ils sont ensuite gardés dans un volume Docker. **Un seul notebook Spark ouvert à la fois** : à deux sessions, on dépasse 8 Go (voir la section 6.4).

**4. Ouvrir le dashboard** : http://localhost:8501. Il lit les tables `gold_*`. Tant qu'elles n'existent pas, il affiche des données fictives, avec un bandeau d'avertissement.

**Arrêter** : `docker compose --profile "*" down`. Les volumes, donc le data lake et la base, sont conservés. Pour tout effacer et repartir de zéro : `docker compose --profile "*" down -v`.

---

## 5. KPI du tableau de bord

Les quatre KPI du dashboard et leur fiche (définition, calcul, intérêt pour la directrice) sont en
**section 7.4**. Ils sont calculés sur les tables gold et suivent le contrat : « à l'heure » = arrivé avec moins
de 15 min de retard, annulés et détournés exclus du dénominateur.

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

Ces durées ont été mesurées sur un Mac avec 8 Go alloués à Docker. Le premier démarrage de Spark télécharge en plus les jars Delta, S3 et JDBC (environ 1,5 Go). Ils sont gardés dans le volume Docker `ivy-cache`, monté sur `~/.ivy2.5.2`, le dossier qu'utilise Spark 4 : les démarrages suivants prennent quelques secondes, même après recréation du conteneur.

- **Un seul notebook Spark ouvert à la fois.** Chaque noyau garde sa session Spark (2 à 5 Go) : à deux, on dépasse 8 Go et Linux arrête Spark (`Py4JNetworkError` / `Connection refused`). Pour fermer vraiment un notebook : *File → Close and Shut Down Notebook*, car fermer l'onglet ne suffit pas.
- **Pas de `spark.createDataFrame(liste)`** pour les petites tables de correspondance : il démarre un worker Python d'environ 360 Mo par cœur. On utilise `F.create_map(...)` à la place.
- **Pas de disque exFAT.** Sur un disque externe exFAT, Docker ne peut pas réécrire un fichier qu'il vient de créer : JupyterLab ne peut plus sauvegarder les notebooks. Il faut placer le dépôt sur le disque interne.

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
- Lancement : service `streamlit` du compose (`docker compose up -d --build` : `--build` reconstruit l'image
  quand `app/requirements.txt` change), ou en local :
  `cd app && pip install -r requirements.txt && streamlit run app.py` (variables `PG_HOST`, `PG_PORT`, `PG_DB`,
  `PG_USER`, `PG_PASSWORD`).
