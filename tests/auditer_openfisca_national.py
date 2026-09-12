"""Audit exhaustif des variables NATIONALES d'openfisca-france (hors
openfisca-france-local, déjà traité) pour repérer les dispositifs jamais
câblés dans NATIONAL_VARIABLES -- même logique que l'audit des variables
locales, mais côté national. Filtre par mots-clés dans le LABEL (plus fiable
qu'un filtre sur le nom technique de la variable) plutôt qu'une liste
noire de mots à exclure, pour ne pas risquer de cacher un vrai dispositif.
"""

import sys

sys.path.insert(0, ".")
from openfisca_france import FranceTaxBenefitSystem
from calculer_aides import NATIONAL_VARIABLES

tbs = FranceTaxBenefitSystem()
deja_cables = {n for n, _, _ in NATIONAL_VARIABLES}

MOTS_POSITIFS = [
    "allocation", "aide ", "aide au", "aide à", "aide aux", "prime ", "indemnite",
    "indemnité", "prestation", "chèque", "cheque", "bourse", "complément", "complement",
    "supplément", "supplement", "pension", "dotation", "secours", "subvention",
    "garantie", "réduction", "reduction", "crédit d'impôt", "credit d'impot",
]
MOTS_NEGATIFS_LABEL = [
    "plafond", "seuil", "abattement", "coefficient", "barème", "bareme",
    "base ressources", "assiette", "cotisation", "charges patronales", "csg",
    "crds", "prélèvement", "prelevement", "taux de", "montant forfaitaire de base",
    "revalorisation", "éligibilité", "eligibilite", "décote", "decote",
]

candidats = []
for nom, variable in tbs.variables.items():
    if nom in deja_cables:
        continue
    if variable.entity.key not in ("individu", "famille", "foyer_fiscal", "menage"):
        continue
    if variable.value_type not in (float, int):
        continue
    if str(variable.definition_period) not in ("month", "year", "DateUnit.MONTH", "DateUnit.YEAR"):
        continue
    label = (variable.label or "").lower()
    if not any(mot in label for mot in MOTS_POSITIFS):
        continue
    if any(mot in label for mot in MOTS_NEGATIFS_LABEL):
        continue
    candidats.append((nom, variable.label, variable.entity.key, str(variable.definition_period)))

print(f"{len(candidats)} candidats trouvés (sur {len(tbs.variables)} variables nationales au total).")
for nom, label, entity, periode in sorted(candidats):
    print(f"{nom:55} | {entity:12} | {periode:20} | {label}")

import json
with open("tests/candidats_openfisca_national.json", "w", encoding="utf-8") as f:
    json.dump([{"nom": n, "label": l, "entity": e, "periode": p} for n, l, e, p in candidats],
              f, ensure_ascii=False, indent=2)
