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
