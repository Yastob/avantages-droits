"""Lit et valide data/profil.yml : classe chaque champ en capturé / non
renseigné / mal saisi, applique les règles de cohérence, écrit un rapport
JSON dans data/rapport_profil.json (consommé par l'Artifact de récap).

Usage : venv/Scripts/python.exe lire_profil.py [chemin_profil.yml]
"""

import json
import re
import sys
from datetime import date, datetime

import yaml

from schema_profil import CHAMPS_PERSONNE_A_CHARGE, SCHEMA

VIDE = (None, "", "n/a", "na")


def est_vide(valeur):
    if valeur is None:
        return True
    if isinstance(valeur, str) and valeur.strip().lower() in VIDE:
        return True
    return False


def parser_date(valeur):
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            d = datetime.strptime(str(valeur).strip(), fmt).date()
        except ValueError:
            continue
        if d > date.today():
            raise ValueError("date dans le futur")
        if d.year < 1900:
            raise ValueError("date antérieure à 1900")
        return d
    raise ValueError("format attendu JJ/MM/AAAA")


def parser_float(valeur):
    if isinstance(valeur, (int, float)):
        return float(valeur)
    nettoye = re.sub(r"[€\s]", "", str(valeur)).replace(",", ".")
    return float(nettoye)


def parser_bool(valeur):
    v = str(valeur).strip().lower()
    if v == "oui":
        return True
    if v == "non":
        return False
    raise ValueError("attendu 'oui' ou 'non'")


def parser_enum(valeur, choix):
    v = str(valeur).strip().lower()
    for c in choix:
        if c.lower() == v:
            return c
    raise ValueError(f"attendu l'une des valeurs : {', '.join(choix)}")


def parser_code_postal(valeur):
    v = str(valeur).strip()
    if not re.fullmatch(r"\d{5}", v):
        raise ValueError("attendu 5 chiffres")
    return v


PARSEURS = {
    "date": parser_date,
    "float": parser_float,
    "bool": parser_bool,
    "code_postal": parser_code_postal,
}


def valider_champ(nom, type_, choix, valeur):
    """Retourne (etat, valeur_normalisee, erreur) avec etat dans
    {"capture", "non_renseigne", "mal_saisi"}."""
    if est_vide(valeur):
        return "non_renseigne", None, None
    try:
        if type_ == "enum":
            normalisee = parser_enum(valeur, choix)
        elif type_ == "text":
            normalisee = str(valeur).strip()
        else:
            normalisee = PARSEURS[type_](valeur)
    except ValueError as e:
        return "mal_saisi", None, str(e)
    return "capture", normalisee, None


def analyser_profil(profil):
    resultats = []
    valeurs_normalisees = {}
    for nom, type_, choix, categorie in SCHEMA:
        etat, normalisee, erreur = valider_champ(nom, type_, choix, profil.get(nom))
        resultats.append({
            "nom": nom, "categorie": categorie, "etat": etat,
            "valeur_brute": profil.get(nom), "valeur": normalisee, "erreur": erreur,
        })
        valeurs_normalisees[nom] = normalisee

    personnes = profil.get("personnes_a_charge") or []
    personnes_resultats = []
    personnes_normalisees = []
    for i, personne in enumerate(personnes):
        personne = personne or {}
        # une entrée entièrement vide (le squelette du template non rempli) est ignorée
        if all(est_vide(personne.get(c[0])) for c in CHAMPS_PERSONNE_A_CHARGE):
            continue
        champs = []
        valeurs = {}
        for nom, type_, choix in CHAMPS_PERSONNE_A_CHARGE:
            etat, normalisee, erreur = valider_champ(nom, type_, choix, personne.get(nom))
            champs.append({
                "nom": nom, "etat": etat, "valeur_brute": personne.get(nom),
                "valeur": normalisee, "erreur": erreur,
            })
            valeurs[nom] = normalisee
        personnes_resultats.append({"index": i, "champs": champs})
        personnes_normalisees.append(valeurs)

    incoherences = appliquer_regles_coherence(valeurs_normalisees, personnes_normalisees)

    resume = {"capture": 0, "non_renseigne": 0, "mal_saisi": 0}
    for r in resultats:
        resume[r["etat"]] += 1
    for p in personnes_resultats:
        for c in p["champs"]:
            resume[c["etat"]] += 1
    resume["incoherences"] = len(incoherences)

    return {
        "champs": resultats,
        "personnes_a_charge": personnes_resultats,
        "incoherences": incoherences,
        "resume": resume,
    }


# ============================================================================
# Règles de cohérence — logique d'exécution. Le "quoi et pourquoi" est
# documenté dans data/regles_coherence.yml (à tenir synchronisé à la main
# si une règle change ici).
# ============================================================================

def age_a(naissance, reference=None):
    reference = reference or date.today()
    return reference.year - naissance.year - (
        (reference.month, reference.day) < (naissance.month, naissance.day)
    )


def regle_parts_fiscales(v, personnes):
    declare = v.get("nombre_parts_fiscales")
    situation = v.get("situation_familiale")
    if declare is None or situation is None:
        return None

    parts = 2.0 if situation in ("marié·e", "pacsé·e", "concubinage") else 1.0
    enfants_a_charge = [p for p in personnes if p.get("lien") in ("enfant", "autre")]
    for i, enfant in enumerate(enfants_a_charge):
        increment = 0.25 if enfant.get("garde_alternee") else 0.5
        if i >= 2:
            increment = (0.5 if enfant.get("garde_alternee") else 1.0)
        parts += increment
    parent_isole = situation in ("célibataire", "divorcé·e", "veuf·ve") and enfants_a_charge
    if parent_isole:
        parts += 0.5

    if abs(declare - parts) > 0.01:
        return (
            f"Nombre de parts renseigné ({declare}) différent du nombre attendu "
            f"({parts}) d'après votre situation familiale. Vérifiez votre saisie, "
            f"ou confirmez si un cas particulier s'applique (invalidité, ancien "
            f"combattant, veuvage récent...)."
        )
    return None


def regle_logement_loyer_vs_statut(v, personnes):
    statut = v.get("statut_logement")
    if statut is None:
        return None
    if statut == "propriétaire" and v.get("loyer_mensuel"):
        return "Un loyer mensuel est renseigné alors que votre statut de logement est \"propriétaire\" — vérifiez que c'est bien intentionnel."
    if statut == "locataire" and v.get("mensualite_pret_immobilier"):
        return "Une mensualité de prêt immobilier est renseignée alors que votre statut de logement est \"locataire\" — vérifiez que c'est bien intentionnel."
    return None


def regle_personne_a_charge_age_limite(v, personnes):
    messages = []
    for p in personnes:
        naissance = p.get("date_naissance")
        if naissance is None:
            continue
        age = age_a(naissance)
        limite = 25 if p.get("scolarise") else 21
        if age > limite and not p.get("situation_handicap"):
            messages.append(
                f"La personne à charge née le {naissance:%d/%m/%Y} a {age} ans — "
                f"au-delà de 21 ans (25 si scolarisée), elle n'est en général plus "
                f"fiscalement à charge. Vérifiez cette entrée."
            )
    return messages or None


def regle_revenus_ordre_grandeur(v, personnes):
    mensuel = v.get("revenu_net_mensuel_foyer")
    annuel = v.get("revenu_fiscal_reference")
    if not mensuel or not annuel:
        return None
    annualise = mensuel * 12
    ratio = annuel / annualise if annualise else None
    if ratio is not None and (ratio > 2 or ratio < 0.5):
        return (
            f"Le revenu fiscal de référence déclaré ({annuel:.0f} €/an) et le revenu "
            f"net mensuel du foyer ({mensuel:.0f} €/mois × 12 = {annualise:.0f} €) "
            f"semblent incohérents entre eux. Vérifiez ces deux valeurs."
        )
    return None


def regle_boursier_sans_echelon(v, personnes):
    if v.get("boursier") is True and not v.get("echelon_bourse"):
        return "Vous êtes déclaré·e boursier·ère mais l'échelon n'est pas renseigné — complétez-le pour affiner le calcul des bourses (sinon une hypothèse basse sera utilisée)."
    return None


def regle_etudiant_sans_niveau(v, personnes):
    if v.get("statut_professionnel") == "étudiant·e" and not v.get("niveau_etudes"):
        return "Statut \"étudiant·e\" déclaré sans niveau d'études renseigné — plusieurs dispositifs (bourses, réductions) en dépendent."
    return None


def regle_conversion_sans_projet_vehicule(v, personnes):
    if v.get("vehicule_actuel_a_mettre_a_la_casse") is True and v.get("projet_vehicule_electrique") is False:
        return "Vous indiquez un véhicule à mettre à la casse sans projet de véhicule électrique — la prime à la conversion suppose un achat en remplacement."
    return None


REGLES = [
    ("parts_fiscales_incoherentes", regle_parts_fiscales),
    ("logement_loyer_vs_statut", regle_logement_loyer_vs_statut),
    ("personne_a_charge_age_limite", regle_personne_a_charge_age_limite),
    ("revenus_ordre_grandeur", regle_revenus_ordre_grandeur),
    ("boursier_sans_echelon", regle_boursier_sans_echelon),
    ("etudiant_sans_niveau", regle_etudiant_sans_niveau),
    ("conversion_sans_projet_vehicule", regle_conversion_sans_projet_vehicule),
]


def appliquer_regles_coherence(valeurs, personnes):
    incoherences = []
    for id_, regle in REGLES:
        resultat = regle(valeurs, personnes)
        if resultat is None:
            continue
        messages = resultat if isinstance(resultat, list) else [resultat]
        for message in messages:
            incoherences.append({"id": id_, "message": message})
    return incoherences


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    chemin = sys.argv[1] if len(sys.argv) > 1 else "data/profil.yml"
    with open(chemin, encoding="utf-8") as f:
        profil = yaml.safe_load(f) or {}

    rapport = analyser_profil(profil)

    with open("data/rapport_profil.json", "w", encoding="utf-8") as f:
        json.dump(rapport, f, ensure_ascii=False, indent=2, default=str)

    r = rapport["resume"]
    print(f"✅ capturés : {r['capture']}  ⚠️ non renseignés : {r['non_renseigne']}  "
          f"❌ mal saisis : {r['mal_saisi']}  🔶 incohérences : {r['incoherences']}")
    print("Rapport écrit dans data/rapport_profil.json")
