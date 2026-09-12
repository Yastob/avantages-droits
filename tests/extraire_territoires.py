"""Cartographie chaque variable locale (openfisca-france-local) vers son
territoire cible (commune/département/région/métropole), en lisant
directement le chemin du fichier source via introspection_data -- pas de
devinette sur le nom de variable, c'est la source de vérité du paquet.

Écrit tests/territoires_locaux.json : { nom_variable: {type, slug, fichier} }
"""

import json
import re
import sys

sys.path.insert(0, ".")
from calculer_aides import tax_benefit_system

tbs, noms_locaux = tax_benefit_system()

TERRITOIRE_RE = re.compile(r"openfisca_france_local[\\/](communes|departements|regions|metropoles)[\\/]([^\\/]+)[\\/]")

resultat = {}
sans_territoire = []

for nom in sorted(noms_locaux):
    variable = tbs.variables[nom]
    intro = getattr(variable, "introspection_data", None)
    fichier = intro[0] if intro else None
    m = TERRITOIRE_RE.search(fichier) if fichier else None
    if m:
        type_territoire = {"communes": "commune", "departements": "departement",
                            "regions": "region", "metropoles": "metropole"}[m.group(1)]
        resultat[nom] = {"type": type_territoire, "slug": m.group(2), "fichier": fichier}
    else:
        sans_territoire.append((nom, fichier))

with open("tests/territoires_locaux.json", "w", encoding="utf-8") as f:
    json.dump(resultat, f, ensure_ascii=False, indent=2)

print(f"{len(resultat)}/{len(noms_locaux)} variables locales rattachées à un territoire.")
print(f"{len(sans_territoire)} sans territoire identifié (mécanismes génériques, pas des dispositifs eux-mêmes) :")
for nom, fichier in sans_territoire:
    print(f"  - {nom} -> {fichier}")

from collections import Counter
compte_par_type = Counter(v["type"] for v in resultat.values())
print("Répartition :", dict(compte_par_type))
compte_par_slug = Counter(v["slug"] for v in resultat.values())
print(f"{len(compte_par_slug)} territoires distincts couverts.")
