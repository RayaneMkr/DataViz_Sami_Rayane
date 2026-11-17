"""
Téléchargement des données BTS On-Time Performance.
Source : Bureau of Transportation Statistics (transtats.bts.gov)

Usage :
    python scripts/download_data.py
"""

import os
import zipfile
import requests
from tqdm import tqdm
from pathlib import Path

BASE_URL = (
    "https://transtats.bts.gov/PREZIP/"
    "On_Time_Reporting_Carrier_On_Time_Performance_1987_present_{year}_{month}.zip"
)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
YEARS = [2023, 2024]
MONTHS = range(1, 13)


def download_file(url: str, dest: Path) -> bool:
    resp = requests.get(url, stream=True, timeout=60)
    if resp.status_code != 200:
        print(f"  ⚠ Fichier non disponible : {url} (HTTP {resp.status_code})")
        return False
    total = int(resp.headers.get("content-length", 0))
    with open(dest, "wb") as f:
        with tqdm(total=total, unit="B", unit_scale=True, desc=dest.name) as bar:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
                bar.update(len(chunk))
    return True


def extract_zip(zip_path: Path, dest_dir: Path):
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(dest_dir)
    zip_path.unlink()


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    for year in YEARS:
        for month in MONTHS:
            url = BASE_URL.format(year=year, month=month)
            zip_name = f"flights_{year}_{month:02d}.zip"
            zip_path = DATA_DIR / zip_name

            print(f"\n📥 Téléchargement {year}-{month:02d}...")
            if download_file(url, zip_path):
                print(f"  📦 Extraction...")
                extract_zip(zip_path, DATA_DIR)
                print(f"  ✅ {year}-{month:02d} OK")

    csv_files = list(DATA_DIR.glob("*.csv"))
    print(f"\n🎉 Terminé ! {len(csv_files)} fichiers CSV dans {DATA_DIR}")


if __name__ == "__main__":
    main()
