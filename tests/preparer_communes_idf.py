"""Prépare la liste des ~1266 communes d'Île-de-France avec leurs noms
d'EPCI (nécessaires au moteur aides-velo) -- une seule requête pour les
communes, une par EPCI distinct (52), pas 1266 requêtes individuelles.
Écrit tests/idf_communes_completes.json.
"""

import json
import urllib.request

with open("tests/idf_communes.json", encoding="utf-8") as f:
    communes = json.load(f)

epci_codes = sorted({c["codeEpci"] for c in communes if c.get("codeEpci")})
noms_epci = {}
for code in epci_codes:
    try:
        with urllib.request.urlopen(f"https://geo.api.gouv.fr/epcis/{code}?fields=nom", timeout=10) as r:
            noms_epci[code] = json.loads(r.read())["nom"]
    except Exception as e:
        noms_epci[code] = None
        print("échec EPCI", code, e)

for c in communes:
    c["epciNom"] = noms_epci.get(c.get("codeEpci"))

with open("tests/idf_communes_completes.json", "w", encoding="utf-8") as f:
    json.dump(communes, f, ensure_ascii=False, indent=2)

print(f"{len(communes)} communes, {len(epci_codes)} EPCI résolus.")
