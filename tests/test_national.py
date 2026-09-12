"""Tests par sensibilité des 9 variables nationales : pour chaque dispositif,
on fait varier UNE variable (âge, revenu, enfants, handicap...) à la fois et
on vérifie que le résultat bascule au seuil attendu -- plutôt que de relire
le code source à la main, on utilise OpenFisca lui-même comme oracle.

Exécution rapide (pas de navigateur), sert à documenter noir sur blanc le
comportement réel attendu (cf. CLAUDE.md pour les seuils trouvés).
"""

import sys
from datetime import date, timedelta

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

# ---- AEEH : enfant à charge en situation de handicap ----
cas("aeeh_enfant_handicape", "enfant handicapé à charge -> > 0 attendu",
    {**BASE, "date_naissance": "1990-01-01",
     "personnes_a_charge": [{"date_naissance": "2015-01-01", "lien": "enfant", "situation_handicap": "oui"}]},
    "aeeh")
cas("aeeh_enfant_non_handicape", "enfant à charge sans handicap -> 0 attendu",
    {**BASE, "date_naissance": "1990-01-01",
     "personnes_a_charge": [{"date_naissance": "2015-01-01", "lien": "enfant", "situation_handicap": "non"}]},
    "aeeh")

# ---- AEFA (prime de Noël) : suit l'éligibilité RSA/ASS ----
cas("aefa_rsa", "au RSA -> prime de Noël attendue",
    {**BASE, "date_naissance": "1990-01-01"}, "aefa")

# ---- Mobili-Jeune : alternant, locataire ----
cas("mobili_jeune_eligible", "alternant, locataire, revenu modeste -> > 0 attendu",
    {**BASE, "date_naissance": "2001-01-01", "statut_professionnel": ["apprenti·e-alternant·e"],
     "type_revenus": ["salaire"], "revenu_net_mensuel_foyer": 900, "statut_logement": "locataire",
     "loyer_mensuel": 400}, "mobili_jeune")
cas("mobili_jeune_pas_alternant", "salarié classique (pas alternant) -> 0 attendu",
    {**BASE, "date_naissance": "2001-01-01", "statut_professionnel": ["salarié·e"],
     "type_revenus": ["salaire"], "revenu_net_mensuel_foyer": 900, "statut_logement": "locataire",
     "loyer_mensuel": 400}, "mobili_jeune")

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


# ---- Droits sans montant calculable (APA, CPF) : présence/absence dans
# droits_sans_montant plutôt qu'un montant dans aides_nationales ----
def a_le_droit(profil, libelle_partiel):
    rapport = analyser_profil(profil)
    resultat = calculer_aides(rapport)
    return any(libelle_partiel in d["libelle"] for d in resultat["droits_sans_montant"])


print(f"\n{'cas':45} {'attendu':45} {'obtenu'}")
print("-" * 110)
CAS_SANS_MONTANT = [
    ("apa_eligible", "76 ans, GIR 2 -> APA listée",
     {**BASE, "date_naissance": "1950-01-01", "situation_perte_autonomie": "oui", "gir": "GIR 2"}, "APA", True),
    ("apa_gir_autonome", "76 ans, GIR 6 (autonome) -> APA non listée",
     {**BASE, "date_naissance": "1950-01-01", "situation_perte_autonomie": "oui", "gir": "GIR 6"}, "APA", False),
    ("apa_trop_jeune", "40 ans, GIR 2 -> APA non listée (âge)",
     {**BASE, "date_naissance": "1986-01-01", "situation_perte_autonomie": "oui", "gir": "GIR 2"}, "APA", False),
    ("cpf_toujours_present", "N'importe quel profil -> CPF toujours listé",
     {**BASE, "date_naissance": "1990-01-01"}, "CPF", True),
    ("visale_emmenagement_futur", "locataire, emménagement dans 30 jours -> Visale listée",
     {**BASE, "date_naissance": "2001-01-01", "statut_logement": "locataire", "loyer_mensuel": 300,
      "date_emmenagement": (date.today() + timedelta(days=30)).isoformat()}, "Visale", True),
    ("visale_deja_installe", "locataire depuis 2 ans -> Visale non listée (bail déjà signé)",
     {**BASE, "date_naissance": "2001-01-01", "statut_logement": "locataire", "loyer_mensuel": 400,
      "date_emmenagement": "2024-01-01"}, "Visale", False),
    ("locapass_emmenagement_recent", "salarié, locataire, emménagement il y a 20 jours -> LOCA-PASS listée",
     {**BASE, "date_naissance": "2001-01-01", "statut_professionnel": ["salarié·e"],
      "statut_logement": "locataire", "loyer_mensuel": 300,
      "date_emmenagement": (date.today() - timedelta(days=20)).isoformat()}, "LOCA-PASS", True),
    ("pass_culture_16ans", "16 ans -> Pass Culture listé",
     {**BASE, "date_naissance": "2010-01-01"}, "Pass Culture", True),
    ("pass_culture_25ans", "25 ans -> Pass Culture non listé",
     {**BASE, "date_naissance": "2001-01-01"}, "Pass Culture", False),
    ("sncf_jeune_20ans", "20 ans -> Carte SNCF Jeune listée",
     {**BASE, "date_naissance": "2006-01-01"}, "SNCF Jeune", True),
    ("sncf_senior_65ans", "65 ans -> Carte SNCF Senior listée",
     {**BASE, "date_naissance": "1960-01-01"}, "SNCF Senior", True),
    ("famille_nombreuse_3enfants", "3 enfants -> Carte Familles nombreuses listée",
     {**BASE, "date_naissance": "1985-01-01", "personnes_a_charge": [
         {"date_naissance": "2010-01-01", "lien": "enfant"},
         {"date_naissance": "2012-01-01", "lien": "enfant"},
         {"date_naissance": "2015-01-01", "lien": "enfant"}]}, "Familles nombreuses", True),
    ("famille_nombreuse_2enfants", "2 enfants -> Carte Familles nombreuses non listée",
     {**BASE, "date_naissance": "1985-01-01", "personnes_a_charge": [
         {"date_naissance": "2010-01-01", "lien": "enfant"},
         {"date_naissance": "2012-01-01", "lien": "enfant"}]}, "Familles nombreuses", False),
    ("bonus_ecologique_avec_projet", "projet véhicule électrique -> bonus écologique listé",
     {**BASE, "date_naissance": "1990-01-01", "projet_vehicule_electrique": "oui"}, "conversion", True),
    ("bonus_ecologique_sans_projet", "pas de projet véhicule -> bonus écologique non listé",
     {**BASE, "date_naissance": "1990-01-01", "projet_vehicule_electrique": "non"}, "conversion", False),
    ("aide_juridictionnelle_toujours", "N'importe quel profil -> aide juridictionnelle toujours listée",
     {**BASE, "date_naissance": "1990-01-01"}, "juridictionnelle", True),
]
for nom, description, profil, libelle, attendu in CAS_SANS_MONTANT:
    obtenu = a_le_droit(profil, libelle)
    print(f"{nom:45} {description:45} {obtenu} {'OK' if obtenu == attendu else 'ÉCHEC'}")
