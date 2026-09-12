"""Cahier de test complet -- lance toutes les suites et donne un bilan
consolidé. À relancer après toute modification de calculer_aides.py,
lire_profil.py ou schema_profil.py.

Usage : venv/Scripts/python.exe tests/executer_tous_les_tests.py
"""

import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")

ENV_UTF8 = {**os.environ, "PYTHONIOENCODING": "utf-8"}

ETAPES = [
    ("Filtrage géographique (exhaustif, 171 variables locales)", "tests/test_filtrage_geographique.py"),
    ("Sensibilité nationale (9 variables, 19 cas)", "tests/test_national.py"),
    ("Calcul réel par territoire (37 territoires, national+local)", "tests/test_calcul_reel_par_territoire.py"),
]

echecs = []
for titre, script in ETAPES:
    print(f"\n{'=' * 70}\n{titre}\n{'=' * 70}")
    r = subprocess.run([sys.executable, script], capture_output=True, text=True,
                        encoding="utf-8", env=ENV_UTF8)
    print(r.stdout)
    if r.returncode != 0:
        echecs.append(titre)
        print(r.stderr)

print(f"\n{'=' * 70}\nBILAN\n{'=' * 70}")
if echecs:
    print(f"{len(echecs)} suite(s) en échec : {echecs}")
else:
    print("Toutes les suites Python sont passées.")
print("\nVélo Île-de-France (1266 communes) : à lancer séparément depuis "
      "velo/ avec `node test_idf.mjs` (nécessite tests/idf_communes_completes.json, "
      "généré par tests/preparer_communes_idf.py).")

sys.exit(1 if echecs else 0)
