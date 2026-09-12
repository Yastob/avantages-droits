"""Tests par sensibilité des 9 variables nationales : pour chaque dispositif,
on fait varier UNE variable (âge, revenu, enfants, handicap...) à la fois et
on vérifie que le résultat bascule au seuil attendu -- plutôt que de relire
le code source à la main, on utilise OpenFisca lui-même comme oracle.

Exécution rapide (pas de navigateur), sert à documenter noir sur blanc le
comportement réel attendu (cf. CLAUDE.md pour les seuils trouvés).
"""

import sys

sys.path.insert(0, ".")
from lire_profil import analyser_profil
from calculer_aides import calculer_aides


def montant(profil, nom_var):
    rapport = analyser_profil(profil)
    resultat = calculer_aides(rapport)
    trouve = [a for a in resultat["aides_nationales"] if a["nom"] == nom_var]
    return trouve[0]["montant"] if trouve else 0.0


def enfant(age_annees, scolarise=True):
    from datetime import date
    naissance = date.today().replace(year=date.today().year - age_annees)
    return {"date_naissance": naissance.isoformat(), "lien": "enfant", "scolarise": "oui" if scolarise else "non"}


CAS = []


def cas(nom, description, profil, nom_var):
    CAS.append((nom, description, profil, nom_var))


BASE = {"situation_familiale": "célibataire", "type_revenus": ["aucun revenu"], "revenu_net_mensuel_foyer": 0}

# ---- RSA : 25 ans+ OU enfant à charge, quel que soit l'âge ----
cas("rsa_moins_25_sans_enfant", "< 25 ans, sans enfant -> 0 attendu",
    {**BASE, "date_naissance": "2003-01-01"}, "rsa")
cas("rsa_25_sans_enfant", "25 ans, sans enfant -> > 0 attendu",
    {**BASE, "date_naissance": "2000-01-01"}, "rsa")
cas("rsa_moins_25_avec_enfant", "22 ans AVEC un enfant -> > 0 attendu (dérogation)",
    {**BASE, "date_naissance": "2004-01-01", "personnes_a_charge": [enfant(3)]}, "rsa")
cas("rsa_revenu_eleve", "25 ans, revenu élevé -> 0 attendu",
    {**BASE, "date_naissance": "2000-01-01", "type_revenus": ["salaire"], "revenu_net_mensuel_foyer": 3000}, "rsa")

# ---- PPA : pas de plancher d'âge à 25 ans (contrairement au RSA) ----
cas("ppa_jeune_actif_revenu_modeste", "22 ans, salaire modeste -> > 0 attendu",
    {**BASE, "date_naissance": "2004-01-01", "type_revenus": ["salaire"], "revenu_net_mensuel_foyer": 1000}, "ppa")
cas("ppa_sans_activite", "22 ans, aucun revenu d'activité -> 0 attendu (PPA suppose une activité)",
    {**BASE, "date_naissance": "2004-01-01"}, "ppa")

# ---- AF : nécessite au moins 2 enfants à charge ----
cas("af_un_enfant", "1 enfant -> 0 attendu (AF commence à 2 enfants)",
    {**BASE, "date_naissance": "1990-01-01", "personnes_a_charge": [enfant(8)]}, "af")
cas("af_deux_enfants", "2 enfants -> > 0 attendu",
    {**BASE, "date_naissance": "1990-01-01", "personnes_a_charge": [enfant(8), enfant(10)]}, "af")

# ---- Aide au logement : nécessite un loyer/statut logement renseigné ----
cas("aide_logement_sans_logement", "aucune info logement -> 0 attendu",
    {**BASE, "date_naissance": "1990-01-01"}, "aide_logement")
cas("aide_logement_locataire", "locataire, loyer 600€ -> > 0 attendu",
    {**BASE, "date_naissance": "1990-01-01", "statut_logement": "locataire", "loyer_mensuel": 600}, "aide_logement")

# ---- AAH : nécessite un taux d'incapacité (typiquement ≥ 80%, ou 50-79% + restriction) ----
cas("aah_sans_taux", "pas de taux d'incapacité renseigné -> 0 attendu",
    {**BASE, "date_naissance": "1990-01-01"}, "aah")
cas("aah_taux_80", "taux d'incapacité 80% -> > 0 attendu",
    {**BASE, "date_naissance": "1990-01-01", "situation_handicap": "oui", "taux_incapacite": 80}, "aah")

# ---- ASPA : âge minimum retraite (65 ans, ou âge légal selon génération) ----
cas("aspa_40_ans", "40 ans -> 0 attendu (trop jeune)",
    {**BASE, "date_naissance": "1986-01-01"}, "aspa")
cas("aspa_70_ans", "70 ans, aucun revenu -> > 0 attendu",
    {**BASE, "date_naissance": "1956-01-01"}, "aspa")

# ---- ARS : enfant(s) scolarisé(s) 6-18 ans ----
cas("ars_sans_enfant", "sans enfant -> 0 attendu",
    {**BASE, "date_naissance": "1990-01-01"}, "ars")
cas("ars_enfant_scolarise", "1 enfant scolarisé de 10 ans -> > 0 attendu",
    {**BASE, "date_naissance": "1990-01-01", "personnes_a_charge": [enfant(10)]}, "ars")

# ---- Chèque énergie : basé sur le revenu fiscal de référence par UC ----
cas("cheque_energie_revenu_eleve", "revenu élevé, locataire -> 0 attendu",
    {**BASE, "date_naissance": "1990-01-01", "type_revenus": ["salaire"], "revenu_net_mensuel_foyer": 4000,
     "revenu_fiscal_reference": 48000, "statut_logement": "locataire"}, "cheque_energie")
cas("cheque_energie_revenu_modeste", "revenu modeste, locataire -> > 0 attendu",
    {**BASE, "date_naissance": "1990-01-01", "type_revenus": ["salaire"], "revenu_net_mensuel_foyer": 900,
     "revenu_fiscal_reference": 10000, "statut_logement": "locataire"}, "cheque_energie")
cas("cheque_energie_sans_domicile", "revenu modeste, SDF -> 0 attendu (statut exclu par la loi)",
    {**BASE, "date_naissance": "1990-01-01", "type_revenus": ["salaire"], "revenu_net_mensuel_foyer": 900,
     "revenu_fiscal_reference": 10000, "statut_logement": "sans domicile stable"}, "cheque_energie")

# ---------------------------------------------------------------------------

resultats = []
for nom, description, profil, nom_var in CAS:
    try:
        m = montant(profil, nom_var)
    except Exception as e:
        m = f"ERREUR: {e}"
    resultats.append((nom, description, m))

print(f"{'cas':45} {'attendu':45} {'obtenu'}")
print("-" * 110)
for nom, description, m in resultats:
    print(f"{nom:45} {description:45} {m}")

import json
with open("tests/rapport_national.json", "w", encoding="utf-8") as f:
    json.dump([{"cas": n, "description": d, "montant": m} for n, d, m in resultats], f, ensure_ascii=False, indent=2)
