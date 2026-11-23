#!/usr/bin/env bash
# Télécharge les données du projet dans data/raw :
#   - BTS On-Time Performance : les 12 mois de 2024 (un CSV par mois, ~600 000 vols chacun)
#   - le référentiel des aéroports d'OurAirports (code IATA, coordonnées)
#
# Usage :  bash scripts/telecharger_donnees.sh          (année par défaut : 2024)
#          bash scripts/telecharger_donnees.sh 2024 6   (seulement les 6 premiers mois)
# Un mois déjà présent n'est pas retéléchargé : on peut relancer le script s'il a été coupé.
# Sources : https://www.transtats.bts.gov/  (Reporting Carrier On-Time Performance, 1987-present)
#           https://ourairports.com/data/
set -euo pipefail

cd "$(dirname "$0")/.."
ANNEE="${1:-2024}"
NB_MOIS="${2:-12}"
BTS="https://transtats.bts.gov/PREZIP"
RAW="data/raw"
mkdir -p "$RAW"

for MOIS in $(seq 1 "$NB_MOIS"); do
  CIBLE="$RAW/bts_${ANNEE}_$(printf '%02d' "$MOIS").csv"
  if [ -s "$CIBLE" ]; then
    echo "✓ $CIBLE déjà présent"
    continue
  fi
  echo "→ Vols BTS ${ANNEE}-$(printf '%02d' "$MOIS")"
  ZIP="$RAW/bts_tmp.zip"
  curl -fL --retry 3 -o "$ZIP" \
    "${BTS}/On_Time_Reporting_Carrier_On_Time_Performance_1987_present_${ANNEE}_${MOIS}.zip"
  # Le zip contient un CSV (+ un readme.html) : on extrait le CSV sous un nom court.
  CSV_DANS_ZIP=$(unzip -Z1 "$ZIP" | grep -i '\.csv$' | head -1)
  unzip -p "$ZIP" "$CSV_DANS_ZIP" > "$CIBLE"
  rm -f "$ZIP"
done

echo "→ Référentiel des aéroports (OurAirports)"
curl -fL --retry 3 -o "$RAW/airports.csv" \
  "https://davidmegginson.github.io/ourairports-data/airports.csv"

echo
echo "Terminé :"
ls -lh "$RAW"
