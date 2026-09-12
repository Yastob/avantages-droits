"""Pour chacun des 37 territoires, lance un calcul réel (national + local)
avec un profil plausible et vérifie qu'aucune exception n'est levée --
complète le test de filtrage géographique (pur texte) par une vraie
exécution OpenFisca de bout en bout.
"""

import json
import sys
from datetime import date

sys.path.insert(0, ".")
from lire_profil import analyser_profil
from calculer_aides import calculer_aides

with open("tests/localisations_territoires.json", encoding="utf-8") as f:
    localisations = json.load(f)

PROFIL_BASE = {
    "date_naissance": "1998-05-12",  # jeune adulte, plausible pour aide au permis / bourses / réductions jeunes
    "situation_familiale": "célibataire",
    "type_revenus": ["aucun revenu"],
    "revenu_net_mensuel_foyer": 0,
    "revenu_fiscal_reference": 6000,
    "nombre_parts_fiscales": 1,
    "statut_professionnel": ["demandeur·se d'emploi"],
    "statut_logement": "locataire",
    "loyer_mensuel": 400,
}

resultats = []
erreurs = []
for cle, loc in localisations.items():
    profil = {**PROFIL_BASE, "code_postal": None, "commune": loc["commune_nom"]}
    # on contourne resoudre_localisation (qui a besoin d'un vrai code postal)
    # en injectant directement le depcom déjà résolu -- calculer_aides()
    # rappelle resoudre_localisation en interne, donc on lui fournit un code
    # postal réel en cherchant celui du depcom choisi n'est pas nécessaire :
    # on teste ici directement via calculer_national_et_local pour cibler le
    # territoire exact déjà résolu, sans dépendre d'un aller-retour code postal.
    from calculer_aides import calculer_national_et_local

    rapport = analyser_profil(profil)
    avertissements = []
    try:
        nationales, locales, sans_montant = calculer_national_et_local(
            rapport["valeurs"], rapport["personnes_valeurs"], loc, avertissements
        )
        resultats.append({
            "territoire": cle, "commune_test": loc["commune_nom"],
            "nb_nationales": len(nationales), "nb_locales": len(locales),
            "locales": [a["nom"] for a in locales],
        })
    except Exception as e:
        erreurs.append({"territoire": cle, "commune_test": loc["commune_nom"], "erreur": str(e)})

print(f"{len(resultats)}/{len(localisations)} territoires calculés sans erreur.")
if erreurs:
    print(f"{len(erreurs)} ERREURS :")
    for e in erreurs:
        print(" -", e["territoire"], e["commune_test"], "->", e["erreur"])

total_locales_trouvees = sum(r["nb_locales"] for r in resultats)
print(f"{total_locales_trouvees} dispositifs locaux déclenchés au total sur les 37 territoires (profil : jeune, sans revenu, demandeur d'emploi, locataire).")
sans_aucune_locale = [r for r in resultats if r["nb_locales"] == 0]
print(f"{len(sans_aucune_locale)} territoires sans aucun dispositif local déclenché pour ce profil :")
for r in sans_aucune_locale:
    print("  -", r["territoire"], r["commune_test"])

with open("tests/rapport_calcul_reel.json", "w", encoding="utf-8") as f:
    json.dump({"resultats": resultats, "erreurs": erreurs}, f, ensure_ascii=False, indent=2)
