"""
Tables gold FICTIVES, au format exact du contrat (noms et types de colonnes, pourcentages de 0 à 100).

Elles servent au dashboard quand PostgreSQL n'a pas encore les tables gold_* (pipeline pas encore lancé),
et aux tests. Les ordres de grandeur imitent 2024 (≈ 7 M de vols, ≈ 79 % à l'heure, ≈ 75 % des minutes de
retard dues à des causes contrôlables), mais AUCUN chiffre n'est réel : ne rien en conclure.

    from donnees_fictives import tables_fictives
    tables = tables_fictives()          # {"gold_ponctualite_mensuelle": DataFrame, ...}
"""
import numpy as np
import pandas as pd

# code → (nom, vols par mois, ponctualité de base en %)
COMPAGNIES = {
    "WN": ("Southwest Airlines", 118_000, 79), "DL": ("Delta Air Lines", 84_000, 85),
    "AA": ("American Airlines", 82_000, 74), "UA": ("United Air Lines", 63_000, 77),
    "OO": ("SkyWest Airlines", 62_000, 81), "YX": ("Republic Airline", 25_000, 83),
    "MQ": ("Envoy Air", 23_000, 80), "NK": ("Spirit Airlines", 22_000, 75),
    "AS": ("Alaska Airlines", 20_000, 78), "B6": ("JetBlue Airways", 20_000, 69),
    "OH": ("PSA Airlines", 19_000, 77), "F9": ("Frontier Airlines", 17_000, 68),
    "9E": ("Endeavor Air", 16_500, 83), "G4": ("Allegiant Air", 9_800, 73),
    "HA": ("Hawaiian Airlines", 6_500, 82),
}

# Effet du mois sur la ponctualité (points) et sur les annulations (facteur) : hiver et été difficiles
EFFET_MOIS = [-4, -1, 1, 0, -1, -6, -8, -4, 4, 5, 4, -2]
ANNULATIONS_MOIS = [2.4, 1.2, 0.8, 1.1, 0.9, 1.3, 1.8, 1.4, 0.6, 0.5, 0.5, 0.9]

# Part des minutes de retard par cause (moyenne), contrôlable ou non
CAUSES = [("avion_retard", True, 40.5), ("compagnie", True, 34.3), ("nas", False, 19.0),
          ("meteo", False, 6.0), ("securite", False, 0.2)]

AEROPORTS = [  # code, ville, état, lat, lon, départs annuels, écart de ponctualité à la moyenne (points)
    ("ATL", "Atlanta", "GA", 33.6367, -84.4281, 341896, 1), ("DFW", "Dallas/Fort Worth", "TX", 32.8968, -97.0380, 313574, -6),
    ("DEN", "Denver", "CO", 39.8600, -104.6738, 308639, -2), ("ORD", "Chicago", "IL", 41.9786, -87.9048, 280032, -3),
    ("CLT", "Charlotte", "NC", 35.2140, -80.9431, 217547, -6), ("LAX", "Los Angeles", "CA", 33.9425, -118.4081, 205000, -1),
    ("PHX", "Phoenix", "AZ", 33.4343, -112.0116, 175000, 3), ("LAS", "Las Vegas", "NV", 36.0840, -115.1537, 172000, -1),
    ("SEA", "Seattle", "WA", 47.4502, -122.3088, 160000, 2), ("LGA", "New York", "NY", 40.7769, -73.8740, 158000, 0),
    ("MCO", "Orlando", "FL", 28.4294, -81.3090, 150000, -5), ("BOS", "Boston", "MA", 42.3643, -71.0052, 132000, -1),
    ("DCA", "Washington", "VA", 38.8521, -77.0377, 131000, 1), ("SFO", "San Francisco", "CA", 37.6190, -122.3750, 130000, -5),
    ("DTW", "Detroit", "MI", 42.2124, -83.3534, 126000, 4), ("EWR", "Newark", "NJ", 40.6925, -74.1687, 121000, -7),
    ("MSP", "Minneapolis", "MN", 44.8820, -93.2218, 116000, 4), ("JFK", "New York", "NY", 40.6394, -73.7793, 111000, -3),
    ("IAH", "Houston", "TX", 29.9844, -95.3414, 109000, 0), ("SLC", "Salt Lake City", "UT", 40.7884, -111.9780, 104000, 5),
    ("MIA", "Miami", "FL", 25.7932, -80.2906, 92000, -6), ("PHL", "Philadelphia", "PA", 39.8719, -75.2411, 90000, -2),
    ("BNA", "Nashville", "TN", 36.1245, -86.6782, 89000, -3), ("BWI", "Baltimore", "MD", 39.1754, -76.6683, 86000, -1),
    ("SAN", "San Diego", "CA", 32.7336, -117.1897, 84000, -2), ("FLL", "Fort Lauderdale", "FL", 26.0726, -80.1527, 80000, -7),
    ("AUS", "Austin", "TX", 30.1945, -97.6699, 79000, -2), ("MDW", "Chicago", "IL", 41.7860, -87.7524, 75000, 1),
    ("TPA", "Tampa", "FL", 27.9755, -82.5332, 74000, -3), ("DAL", "Dallas", "TX", 32.8471, -96.8518, 72000, 0),
    ("PDX", "Portland", "OR", 45.5887, -122.5975, 62000, 3), ("HOU", "Houston", "TX", 29.6454, -95.2789, 56000, -1),
    ("STL", "St. Louis", "MO", 38.7487, -90.3700, 55000, 2), ("HNL", "Honolulu", "HI", 21.3187, -157.9226, 54000, 6),
    ("RDU", "Raleigh/Durham", "NC", 35.8776, -78.7875, 50000, 0), ("SMF", "Sacramento", "CA", 38.6954, -121.5908, 45000, 2),
    ("MSY", "New Orleans", "LA", 29.9934, -90.2580, 44000, -1), ("SJC", "San Jose", "CA", 37.3626, -121.9290, 40000, 1),
    ("SAT", "San Antonio", "TX", 29.5337, -98.4698, 40000, 0), ("MCI", "Kansas City", "MO", 39.2976, -94.7139, 39000, 2),
    ("SNA", "Santa Ana", "CA", 33.6757, -117.8682, 38000, 1), ("OAK", "Oakland", "CA", 37.7213, -122.2210, 35000, 0),
    ("IND", "Indianapolis", "IN", 39.7173, -86.2944, 34000, 2), ("CLE", "Cleveland", "OH", 41.4117, -81.8498, 30000, 1),
    ("PIT", "Pittsburgh", "PA", 40.4915, -80.2329, 30000, 2), ("PBI", "West Palm Beach/Palm Beach", "FL", 26.6832, -80.0956, 29476, -6),
    ("CVG", "Cincinnati", "KY", 39.0488, -84.6678, 29000, 2), ("RSW", "Fort Myers", "FL", 26.5362, -81.7552, 29000, -4),
    ("CMH", "Columbus", "OH", 39.9980, -82.8919, 28000, 1), ("ANC", "Anchorage", "AK", 61.1744, -149.9960, 25000, 3),
    ("JAX", "Jacksonville", "FL", 30.4941, -81.6879, 24000, -2), ("BUR", "Burbank", "CA", 34.2007, -118.3587, 23000, 2),
    ("OGG", "Kahului", "HI", 20.8986, -156.4305, 21000, 5), ("SJU", "San Juan", "PR", 18.4394, -66.0018, 20000, -5),
    ("ABQ", "Albuquerque", "NM", 35.0402, -106.6090, 19000, 1), ("ONT", "Ontario", "CA", 34.0560, -117.6012, 19000, 2),
    ("MKE", "Milwaukee", "WI", 42.9472, -87.8966, 18000, 2), ("BOI", "Boise", "ID", 43.5644, -116.2228, 17000, 3),
    ("CHS", "Charleston", "SC", 32.8986, -80.0405, 17000, -2), ("BDL", "Hartford", "CT", 41.9389, -72.6832, 16000, 0),
    ("OMA", "Omaha", "NE", 41.3032, -95.8941, 16000, 2), ("RNO", "Reno", "NV", 39.4991, -119.7681, 15000, 1),
    ("RIC", "Richmond", "VA", 37.5052, -77.3197, 14000, 0), ("TUS", "Tucson", "AZ", 32.1161, -110.9410, 13500, 3),
    ("ELP", "El Paso", "TX", 31.8072, -106.3776, 13000, 1), ("BUF", "Buffalo", "NY", 42.9405, -78.7322, 12500, 0),
    ("ASE", "Aspen", "CO", 39.2232, -106.8690, 8000, -9), ("GUM", "Guam", "TT", 13.4834, 144.7960, 1200, 4),
]


def _ponctualite_mensuelle(rng):
    lignes = []
    for m in range(12):
        for code, (nom, vols_mois, base) in COMPAGNIES.items():
            vols = int(vols_mois * rng.uniform(0.92, 1.08) * (1.06 if m in (5, 6, 7) else 1.0))
            pct = float(np.clip(base + EFFET_MOIS[m] + rng.normal(0, 1.5), 50, 95))
            annules = float(np.clip(1.3 * ANNULATIONS_MOIS[m] * rng.uniform(0.6, 1.5), 0.1, 15))
            lignes.append({
                "mois": pd.Timestamp(2024, m + 1, 1).date(), "compagnie_code": code, "compagnie_nom": nom,
                "vols": vols, "pct_a_l_heure": round(pct, 2), "pct_annules": round(annules, 2),
                "retard_moyen_min": round(max(-2.0, (84 - pct) * 1.05 + rng.normal(0, 1)), 1),
            })
    return pd.DataFrame(lignes)


def _causes_retard(rng, ponctualite):
    lignes = []
    for p in ponctualite.itertuples(index=False):
        vols_en_retard = p.vols * (1 - p.pct_annules / 100) * (1 - p.pct_a_l_heure / 100)
        total = vols_en_retard * rng.uniform(62, 72)                     # ≈ 65 min de retard par vol en retard
        hiver_ou_ete = p.mois.month in (1, 6, 7, 12)
        poids = np.array([c[2] for c in CAUSES]) * rng.uniform(0.85, 1.15, len(CAUSES))
        poids[3] *= 1.8 if hiver_ou_ete else 1.0                          # plus de météo l'hiver et l'été
        parts = poids / poids.sum()
        for (cause, controlable, _), part in zip(CAUSES, parts):
            lignes.append({"mois": p.mois, "compagnie_code": p.compagnie_code, "cause": cause,
                           "controlable": controlable, "minutes": float(round(total * part)),
                           "part_pct": round(100 * part, 2)})
    return pd.DataFrame(lignes)


def _aeroports(rng):
    lignes = []
    for code, ville, etat, lat, lon, departs, ecart in AEROPORTS:
        pct = float(np.clip(79 + ecart + rng.normal(0, 0.8), 55, 92))
        lignes.append({"code_iata": code, "ville": ville, "etat": etat, "lat": lat, "lon": lon,
                       "departs": departs, "pct_a_l_heure": round(pct, 2),
                       "retard_moyen_min": round((84 - pct) * 1.05 + rng.normal(0, 0.8), 1),
                       "pct_annules": round(float(np.clip(rng.normal(1.4, 0.4), 0.3, 4)), 2)})
    return pd.DataFrame(lignes)


def _heure_jour(rng):
    total = 7_078_487
    profil_vols = np.array([2, 1, 0.5, 0.3, 0.5, 4, 7, 7.5, 7, 6.5, 6.5, 6.3, 6.2, 6.2, 6.1, 6.0, 6.2,
                            6.3, 6.0, 5.5, 4.5, 3.5, 2.5, 1.5])
    effet_jour = {1: 0.5, 2: -2.5, 3: -2.0, 4: 1.5, 5: 2.5, 6: -3.0, 7: 2.0}   # 1 = lundi
    lignes = []
    for jour in range(1, 8):
        for heure in range(24):
            vols = int(total / 7 * profil_vols[heure] / profil_vols.sum() * rng.uniform(0.95, 1.05)
                       * (0.85 if jour == 6 else 1.0))
            base = 9 + 24 / (1 + np.exp(-(heure - 14) / 2.6))                 # monte de 9 % à 33 % dans la journée
            if heure < 5:
                base = 16 + rng.normal(0, 3)                                   # vols de nuit, peu nombreux
            lignes.append({"jour_semaine": jour, "heure": heure, "vols": vols,
                           "pct_retard": round(float(np.clip(base + effet_jour[jour] + rng.normal(0, 0.8), 3, 60)), 2)})
    return pd.DataFrame(lignes)


def _routes(rng, aeroports):
    codes = aeroports["code_iata"].tolist()
    departs = dict(zip(codes, aeroports["departs"]))
    ecart = {c: e for c, *_, e in AEROPORTS}
    lignes = []
    for i, o in enumerate(codes[:40]):
        for d in codes[:40]:
            if o == d or rng.random() > 0.35:
                continue
            vols = int(departs[o] * departs[d] / 2.2e7 * rng.uniform(0.5, 1.6))
            if vols < 300:
                continue
            pct = float(np.clip(79 + (ecart[o] + ecart[d]) / 2 + rng.normal(0, 4), 45, 95))
            lignes.append({"origine": o, "destination": d, "vols": vols, "pct_a_l_heure": round(pct, 2),
                           "retard_moyen_min": round((84 - pct) * 1.05 + rng.normal(0, 1.5), 1)})
    routes = pd.DataFrame(lignes)
    routes["score_priorite"] = (routes["vols"] * (1 - routes["pct_a_l_heure"] / 100)).round().astype(int)
    return routes.sort_values("score_priorite", ascending=False).reset_index(drop=True)


def tables_fictives(graine=2024):
    """Les cinq tables du contrat gold, fictives mais au bon format. Même graine → mêmes tables."""
    rng = np.random.default_rng(graine)
    ponctualite = _ponctualite_mensuelle(rng)
    aeroports = _aeroports(rng)
    return {
        "gold_ponctualite_mensuelle": ponctualite,
        "gold_causes_retard": _causes_retard(rng, ponctualite),
        "gold_aeroports": aeroports,
        "gold_heure_jour": _heure_jour(rng),
        "gold_routes": _routes(rng, aeroports),
    }
