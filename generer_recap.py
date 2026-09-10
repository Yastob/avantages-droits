"""Construit artifact/recap_profil.html à partir de data/rapport_profil.json
(généré par lire_profil.py) en injectant les données dans le gabarit HTML.

Usage : venv/Scripts/python.exe generer_recap.py
"""

import json
import sys

from schema_profil import LIBELLES, ORDRE_CATEGORIES

with open("data/rapport_profil.json", encoding="utf-8") as f:
    rapport = json.load(f)

payload = {
    "rapport": rapport,
    "libelles": LIBELLES,
    "ordre_categories": ORDRE_CATEGORIES,
}

with open("artifact/recap_profil_gabarit.html", encoding="utf-8") as f:
    gabarit = f.read()

sortie = gabarit.replace(
    "/*__DONNEES_JSON__*/",
    json.dumps(payload, ensure_ascii=False),
)

with open("artifact/recap_profil.html", "w", encoding="utf-8") as f:
    f.write(sortie)

print("Écrit dans artifact/recap_profil.html")
