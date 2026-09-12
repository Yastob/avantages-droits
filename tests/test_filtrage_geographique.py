"""Test EXHAUSTIF du filtrage géographique des ~171 variables locales.

Ce qu'on teste réellement ici : pas "OpenFisca calcule-t-il le bon montant"
(on fait confiance à OpenFisca pour ça), mais "notre filtre géographique
maison (slugs_localisation + le any(slug in nom_var...) dans
calculer_aides.py) garde-t-il chaque variable pour SON territoire, et la
rejette-t-il pour les autres ?". C'est notre code à nous, pas OpenFisca,
donc c'est là qu'est le risque de bug (cf. le faux positif "antony" trouvé
pour un profil à Bordeaux avant qu'on ajoute ce filtre).

Pur test de correspondance de texte, aucun appel OpenFisca -> exécution en
quelques secondes pour les 171 x 37 combinaisons.
"""

import json
import sys

sys.path.insert(0, ".")
from calculer_aides import _MOTS_INTERMEDIAIRES, variable_correspond_localisation, slugs_localisation, tax_benefit_system

with open("tests/territoires_locaux.json", encoding="utf-8") as f:
    territoires_var = json.load(f)
with open("tests/localisations_territoires.json", encoding="utf-8") as f:
    localisations = json.load(f)

tbs, noms_locaux = tax_benefit_system()

# Variables numériques uniquement (les autres -- eligibilite, base_ressources...
# -- sont exclues du résultat final par _MOTS_INTERMEDIAIRES, donc hors périmètre
# de ce test qui porte sur ce qui est réellement affiché à l'utilisateur).
EXCLUS = {"test_dispositif"}


def est_candidate_affichage(nom_var):
    if nom_var in EXCLUS:
        return False
    if any(mot in nom_var for mot in _MOTS_INTERMEDIAIRES):
        return False
    variable = tbs.variables.get(nom_var)
    return variable is not None and variable.value_type in (float, int)


candidates = [n for n in sorted(noms_locaux) if est_candidate_affichage(n)]
print(f"{len(candidates)} variables locales candidates à l'affichage (sur {len(noms_locaux)} au total).")

# ---- Test 1 : inclusion -- la variable doit être gardée sur SON territoire ----
echecs_inclusion = []
for nom_var in candidates:
    info = territoires_var.get(nom_var)
    if not info:
        continue  # pas de territoire identifié (mécanisme générique), hors périmètre
    cle = f"{info['type']}:{info['slug']}"
    loc = localisations.get(cle)
    if not loc:
        echecs_inclusion.append((nom_var, "territoire non résolu : " + cle))
        continue
    slugs = slugs_localisation(loc)
    if not variable_correspond_localisation(nom_var, slugs):
        echecs_inclusion.append((nom_var, f"pas retenue pour {loc['commune_nom']} ({cle}), slugs={sorted(slugs)}"))

# ---- Test 2 : exclusion -- la variable ne doit PAS apparaître pour un
# territoire différent et non hiérarchiquement lié (pas la même région/dept/EPCI) ----
echecs_exclusion = []
for nom_var in candidates:
    info = territoires_var.get(nom_var)
    if not info:
        continue
    cle_propre = f"{info['type']}:{info['slug']}"
    for cle_autre, loc_autre in localisations.items():
        if cle_autre == cle_propre:
            continue
        # Si le territoire "autre" partage la même région/département/EPCI que le
        # territoire propre, un chevauchement légitime est possible -> on ne le
        # compte pas comme un faux positif (hiérarchie commune ⊂ département ⊂ région).
        loc_propre = localisations[cle_propre]
        chevauchement = (
            loc_autre.get("region_nom") == loc_propre.get("region_nom")
            or loc_autre.get("departement_nom") == loc_propre.get("departement_nom")
            or loc_autre.get("epci_nom") == loc_propre.get("epci_nom")
        )
        if chevauchement:
            continue
        slugs_autre = slugs_localisation(loc_autre)
        if variable_correspond_localisation(nom_var, slugs_autre):
            echecs_exclusion.append(
                (nom_var, f"apparaît à tort pour {loc_autre['commune_nom']} ({cle_autre})")
            )

print(f"\n=== Inclusion (doit être retenue sur son propre territoire) ===")
print(f"{len(candidates) - len(echecs_inclusion)}/{len(candidates)} OK")
for nom, raison in echecs_inclusion:
    print(f"  ÉCHEC : {nom} -> {raison}")

print(f"\n=== Exclusion (ne doit pas apparaître ailleurs) ===")
print(f"{len(echecs_exclusion)} faux positifs détectés")
for nom, raison in echecs_exclusion:
    print(f"  ÉCHEC : {nom} -> {raison}")

with open("tests/rapport_filtrage_geographique.json", "w", encoding="utf-8") as f:
    json.dump({
        "candidates_testees": len(candidates),
        "echecs_inclusion": echecs_inclusion,
        "echecs_exclusion": echecs_exclusion,
    }, f, ensure_ascii=False, indent=2)

sys.exit(1 if (echecs_inclusion or echecs_exclusion) else 0)
