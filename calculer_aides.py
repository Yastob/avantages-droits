"""Calcule les aides réelles (national OpenFisca, local OpenFisca, vélo
Publicodes) à partir des valeurs normalisées d'un profil (sortie de
`analyser_profil`). Voir CLAUDE.md pour les approximations assumées.
"""

import json
import subprocess
import urllib.parse
import urllib.request
from datetime import date

from openfisca_core.simulation_builder import SimulationBuilder
from openfisca_france import FranceTaxBenefitSystem

_TBS = None
_NOMS_LOCAUX = None

# Variables intermédiaires (seuils, éligibilité, base de ressources...) à ne
# pas afficher comme si c'étaient des montants d'aide. Filtrage best-effort
# par mots-clés (pas de méthode fiable à 100% sans inspecter individuellement
# chacun des ~90 dispositifs locaux) — à affiner au fil des faux positifs
# constatés en usage réel.
_MOTS_INTERMEDIAIRES = (
    "eligibilite", "eligible", "plafond", "ressource", "condition", "seuil",
    "majoration", "reference", "indice", "forfait", "mois_demande", "taux",
    "smic", "parts", "revenus_nets_du_travail", "quotient_familial",
)

NATIONAL_VARIABLES = [
    ("rsa", "RSA", "month"),
    ("ppa", "Prime d'activité", "month"),
    ("af", "Allocations familiales", "month"),
    ("cf", "Complément familial", "month"),
    ("aide_logement", "Aide au logement (APL/AL)", "month"),
    ("aah", "Allocation adulte handicapé (AAH)", "month"),
    ("aspa", "Allocation de solidarité aux personnes âgées (ASPA)", "month"),
    ("ars", "Allocation de rentrée scolaire", "year"),
    ("cheque_energie", "Chèque énergie", "year"),
]

MOIS_FENETRE = 4  # RSA/PPA utilisent une moyenne glissante sur plusieurs mois :
# fournir un revenu sur un seul mois fausserait le calcul (voir CLAUDE.md).

# type_revenus est un champ à choix multiples (on peut cocher plusieurs
# sources) mais revenu_net_mensuel_foyer reste un montant total unique -> on
# ne peut pas répartir précisément entre plusieurs sources. On retient donc
# la source "principale" par ordre de priorité ci-dessous, et on avertit
# l'utilisateur si plusieurs cases sont cochées (voir calculer_aides.py::calculer_national_et_local).
PRIORITE_REVENU = [
    ("salaire", "salaire_net"),
    ("indépendant / auto-entrepreneur", "rpns_auto_entrepreneur_benefice"),
    ("chômage", "chomage_net"),
    ("retraite", "retraite_nette"),
]

MAPPING_STATUT_LOGEMENT = {
    "locataire": "locataire_vide",
    "propriétaire": "proprietaire",
    "hébergé·e à titre gratuit": "loge_gratuitement",
    "sans domicile stable": "sans_domicile",
}

MAPPING_TYPE_VELO = {
    "électrique": "électrique",
    "cargo": "cargo",
    "pliant": "pliant",
    "adapté handicap": "adapté",
}


def premiere_url(reference):
    """`variable.reference` d'OpenFisca est une liste qui mélange parfois un
    intitulé de texte de loi (pas une URL) et une vraie URL (ex: Cambrai ->
    ['Règlement relatif à...', 'https://...']) -- on ne garde que ce qui
    ressemble vraiment à un lien, jamais reference[0] à l'aveugle."""
    if not reference:
        return None
    return next((r for r in reference if r.startswith("http")), None)


def lien_source(libelle, reference):
    """Retourne (url, est_une_recherche). Utilise la vraie référence
    OpenFisca quand il y en a une ; sinon renvoie un lien de recherche vers
    service-public.fr plutôt que de fabriquer une URL qu'on ne peut pas
    vérifier (un mauvais lien est pire qu'un lien de recherche générique)."""
    url = premiere_url(reference)
    if url:
        return url, False
    requete = urllib.parse.quote(f"{libelle} site:service-public.fr")
    return f"https://www.google.com/search?q={requete}", True


def tax_benefit_system():
    global _TBS, _NOMS_LOCAUX
    if _TBS is None:
        national_seul = FranceTaxBenefitSystem()
        noms_nationaux = set(national_seul.variables.keys())
        _TBS = FranceTaxBenefitSystem()
        _TBS.load_extension("openfisca_france_local")
        _NOMS_LOCAUX = set(_TBS.variables.keys()) - noms_nationaux
    return _TBS, _NOMS_LOCAUX


def variable_revenu(types_revenus):
    types_revenus = types_revenus or []
    for valeur_enum, variable in PRIORITE_REVENU:
        if valeur_enum in types_revenus:
            return variable
    return "salaire_net"


# statut_professionnel (enum_multi, mêmes valeurs que le schéma) -> valeur
# OpenFisca "activite" (actif/chomeur/etudiant/retraite/inactif). Même
# logique de priorité que pour les revenus : si plusieurs statuts sont
# cochés, on retient celui qui a le plus d'impact sur l'éligibilité.
MAPPING_ACTIVITE = {
    "demandeur·se d'emploi": "chomeur",
    "étudiant·e": "etudiant",
    "retraité·e": "retraite",
    "salarié·e": "actif",
    "indépendant·e-auto-entrepreneur·se": "actif",
    "apprenti·e-alternant·e": "actif",
    "sans activité": "inactif",
}
PRIORITE_ACTIVITE = ["demandeur·se d'emploi", "étudiant·e", "retraité·e", "salarié·e",
                     "indépendant·e-auto-entrepreneur·se", "apprenti·e-alternant·e", "sans activité"]

MAPPING_STATUT_MARITAL = {
    "célibataire": "celibataire",
    "concubinage": "celibataire",  # le concubinage n'est pas un statut marital légal en France
    "pacsé·e": "pacse",
    "marié·e": "marie",
    "divorcé·e": "divorce",
    "veuf·ve": "veuf",
}


def variable_activite(statuts):
    for valeur_prioritaire in PRIORITE_ACTIVITE:
        if valeur_prioritaire in (statuts or []):
            return MAPPING_ACTIVITE[valeur_prioritaire]
    return None


def mois_glissants(mois_reference, n=MOIS_FENETRE):
    annee, mois = mois_reference.year, mois_reference.month
    resultat = []
    for _ in range(n):
        resultat.append(f"{annee:04d}-{mois:02d}")
        mois -= 1
        if mois == 0:
            mois, annee = 12, annee - 1
    return resultat


def communes_pour_code_postal(code_postal):
    """Appel brut geo.api.gouv.fr : liste des communes correspondant à un
    code postal (un code postal peut couvrir plusieurs communes, ou une
    commune plusieurs codes postaux). [] si injoignable/introuvable."""
    if not code_postal:
        return []
    try:
        url = ("https://geo.api.gouv.fr/communes?codePostal=" +
               urllib.parse.quote(code_postal) +
               "&fields=departement,region,codeEpci,nom&format=json")
        with urllib.request.urlopen(url, timeout=5) as reponse:
            return json.loads(reponse.read())
    except Exception:
        return []


def resoudre_localisation(code_postal, commune=None):
    """code postal (+ commune pour désambiguïser) -> code INSEE + EPCI +
    département + région. None si injoignable ou introuvable."""
    resultats = communes_pour_code_postal(code_postal)
    if not resultats:
        return None
    choix = resultats[0]
    if commune:
        for r in resultats:
            if r["nom"].lower() == commune.strip().lower():
                choix = r
                break
    epci_nom = None
    if choix.get("codeEpci"):
        try:
            url_epci = f"https://geo.api.gouv.fr/epcis/{choix['codeEpci']}?fields=nom&format=json"
            with urllib.request.urlopen(url_epci, timeout=5) as reponse:
                epci_nom = json.loads(reponse.read()).get("nom")
        except Exception:
            pass
    return {
        "depcom": choix["code"],
        "commune_nom": choix["nom"],
        "epci_nom": epci_nom,
        "departement_code": choix.get("departement", {}).get("code"),
        "departement_nom": choix.get("departement", {}).get("nom"),
        "region_code": choix.get("region", {}).get("code"),
        "region_nom": choix.get("region", {}).get("nom"),
    }


def _slugifier(texte):
    if not texte:
        return ""
    import unicodedata
    sans_accents = unicodedata.normalize("NFKD", texte).encode("ascii", "ignore").decode("ascii")
    sans_accents = sans_accents.replace("'", " ").replace("-", " ")
    return "_".join(sans_accents.lower().split())


def slugs_localisation(localisation):
    """Fragments de nom (commune, EPCI, département, région) utilisés pour
    ne garder que les dispositifs locaux dont le nom de variable correspond
    réellement à l'endroit où vit la personne — nécessaire car les formules
    openfisca-france-local ne filtrent pas toutes par territoire elles-mêmes
    (constaté en test : certaines renvoient un montant sans vérifier le
    depcom). Best-effort par correspondance de texte, pas garanti exhaustif."""
    if not localisation:
        return set()
    slugs = set()
    for cle in ("commune_nom", "epci_nom", "departement_nom", "region_nom"):
        slug = _slugifier(localisation.get(cle))
        if slug:
            slugs.add(slug)
    return slugs


def construire_situation(valeurs, personnes, depcom, mois_ref, avertissements=None):
    fenetre = mois_glissants(mois_ref)
    mois_courant = fenetre[0]

    types_revenus = valeurs.get("type_revenus") or []
    var_revenu = variable_revenu(types_revenus)
    revenu = valeurs.get("revenu_net_mensuel_foyer") or 0
    if avertissements is not None and len(types_revenus) > 1:
        source_retenue = next((v for v, _ in PRIORITE_REVENU if v in types_revenus), types_revenus[0])
        avertissements.append(
            f"Plusieurs types de revenus cochés ({', '.join(types_revenus)}) — le revenu total "
            f"déclaré est pris en compte au titre de « {source_retenue} » uniquement (priorité : "
            f"{' > '.join(p[0] for p in PRIORITE_REVENU)}), la répartition exacte entre plusieurs "
            f"sources n'est pas encore modélisée."
        )

    individus = {
        "declarant": {
            "date_naissance": {"ETERNITY": str(valeurs["date_naissance"])},
            var_revenu: {m: revenu for m in fenetre},
        }
    }
    if valeurs.get("situation_handicap"):
        individus["declarant"]["handicap"] = {mois_courant: True}
    if valeurs.get("taux_incapacite"):
        individus["declarant"]["taux_incapacite"] = {mois_courant: valeurs["taux_incapacite"]}
    if valeurs.get("pension_alimentaire_recue"):
        individus["declarant"]["pensions_alimentaires_percues"] = {
            m: valeurs["pension_alimentaire_recue"] for m in fenetre
        }
    if valeurs.get("pension_alimentaire_versee"):
        individus["declarant"]["pensions_alimentaires_versees_individu"] = {
            m: valeurs["pension_alimentaire_versee"] for m in fenetre
        }
    activite = variable_activite(valeurs.get("statut_professionnel"))
    if activite:
        individus["declarant"]["activite"] = {mois_courant: activite}
    statut_marital = MAPPING_STATUT_MARITAL.get(valeurs.get("situation_familiale"))
    if statut_marital:
        individus["declarant"]["statut_marital"] = {mois_courant: statut_marital}

    enfants = []
    for i, p in enumerate(personnes):
        naissance = p.get("date_naissance")
        if not naissance:
            continue
        nom = f"enfant_{i}"
        individus[nom] = {"date_naissance": {"ETERNITY": str(naissance)}}
        if p.get("situation_handicap"):
            individus[nom]["handicap"] = {mois_courant: True}
        enfants.append(nom)

    situation = {
        "individus": individus,
        "familles": {"famille": {"parents": ["declarant"], "enfants": enfants}},
        "foyers_fiscaux": {"foyer": {"declarants": ["declarant"], "personnes_a_charge": enfants}},
        "menages": {"menage": {"personne_de_reference": ["declarant"], "enfants": enfants}},
    }
    menage = situation["menages"]["menage"]
    if depcom:
        menage["depcom"] = {mois_courant: depcom}
    statut = MAPPING_STATUT_LOGEMENT.get(valeurs.get("statut_logement"))
    if statut:
        menage["statut_occupation_logement"] = {mois_courant: statut}
    if valeurs.get("loyer_mensuel"):
        menage["loyer"] = {mois_courant: valeurs["loyer_mensuel"]}
    return situation, mois_courant


def calculer_national_et_local(valeurs, personnes, localisation, avertissements):
    if not valeurs.get("date_naissance"):
        avertissements.append(
            "Date de naissance manquante : impossible de calculer les aides sociales/fiscales."
        )
        return [], []

    depcom = localisation["depcom"] if localisation else None
    tbs, noms_locaux = tax_benefit_system()
    mois_ref = date.today()
    situation, mois_courant = construire_situation(valeurs, personnes, depcom, mois_ref, avertissements)
    annee_courante = str(mois_ref.year)

    try:
        simulation = SimulationBuilder().build_from_entities(tbs, situation)
    except Exception as e:
        avertissements.append(f"Impossible de construire la simulation OpenFisca : {e}")
        return [], []

    nationales = []
    for nom_var, libelle, type_periode in NATIONAL_VARIABLES:
        periode = mois_courant if type_periode == "month" else annee_courante
        try:
            valeur = float(simulation.calculate(nom_var, periode)[0])
        except Exception:
            continue
        if valeur > 0:
            variable = tbs.variables.get(nom_var)
            reference = getattr(variable, "reference", None) if variable else None
            url, recherche = lien_source(libelle, reference)
            nationales.append({
                "nom": nom_var, "libelle": libelle, "montant": round(valeur, 2), "periode": periode,
                "unite": "€",
                "institution": "Prestation nationale (calculée avec OpenFisca-France, le même moteur "
                                "que mes-aides.1jeune1solution.beta.gouv.fr)",
                "url": url, "url_est_recherche": recherche,
            })

    locales = []
    if not depcom:
        # Sans commune résolue, les formules locales ne filtrent pas
        # correctement par territoire -> les calculer produirait des faux
        # positifs (aides d'autres communes). On les saute entièrement.
        return nationales, locales

    slugs = slugs_localisation(localisation)
    for nom_var in sorted(noms_locaux):
        if any(mot in nom_var for mot in _MOTS_INTERMEDIAIRES):
            continue
        # Beaucoup de formules openfisca-france-local ne vérifient pas
        # elles-mêmes le territoire (constaté en test) -> on ne garde que les
        # variables dont le nom correspond à la commune/EPCI/département/
        # région de la personne, sinon ça ressort les aides de communes au
        # hasard partout en France.
        if not any(slug in nom_var for slug in slugs):
            continue
        variable = tbs.variables.get(nom_var)
        if variable is None or variable.value_type not in (float, int):
            continue
        periode = mois_courant if variable.definition_period.value == "month" else annee_courante
        try:
            valeur = float(simulation.calculate(nom_var, periode)[0])
        except Exception:
            continue
        if valeur > 0:
            if variable.label:
                libelle = variable.label.replace("\\%", "%")
            else:
                libelle = nom_var.replace("_", " ")
                libelle = libelle[0].upper() + libelle[1:]
            # Pas de métadonnée fiable pour distinguer un montant en € d'un
            # pourcentage/taux côté OpenFisca -> détection best-effort sur le
            # libellé (ex: "Réduction obtenue en %") pour éviter d'afficher
            # "80,00 €" quand c'est en fait "80 %".
            unite = "%" if ("%" in libelle or "pourcentage" in libelle.lower()) else "€"
            reference = getattr(variable, "reference", None)
            url, recherche = lien_source(libelle, reference)
            locales.append({
                "nom": nom_var, "libelle": libelle, "montant": round(valeur, 2), "periode": periode,
                "unite": unite,
                "institution": institution_locale(nom_var, localisation)
                or "Collectivité locale (calculé avec openfisca-france-local)",
                "url": url, "url_est_recherche": recherche,
            })

    return nationales, locales


def institution_locale(nom_var, localisation):
    """Devine à quelle collectivité un dispositif local appartient, en
    recoupant le nom de la variable avec le nom de la commune/EPCI/
    département/région de la personne (même logique que slugs_localisation)."""
    if not localisation:
        return None
    for cle, etiquette in (
        ("commune_nom", "Commune"), ("epci_nom", "Intercommunalité"),
        ("departement_nom", "Département"), ("region_nom", "Région"),
    ):
        valeur = localisation.get(cle)
        if valeur and _slugifier(valeur) in nom_var:
            return f"{etiquette} : {valeur}"
    return None


def calculer_velo(valeurs, localisation, avertissements):
    if not valeurs.get("projet_velo"):
        return []
    if not localisation:
        avertissements.append("Localisation introuvable : impossible de calculer les aides vélo.")
        return []
    types_choisis = valeurs.get("type_velo") or ["électrique"]
    velo_types = [MAPPING_TYPE_VELO.get(t, t) for t in types_choisis]
    velo_etats = valeurs.get("etat_velo") or ["neuf"]
    prix = valeurs.get("prix_velo")
    if not prix:
        avertissements.append(
            "Prix du vélo non renseigné : estimation faite sur la base d'un prix par défaut (1200 €), "
            "renseignez-le pour un montant exact."
        )
        prix = 1200

    entree = json.dumps({
        "codeInsee": localisation["depcom"],
        "epci": localisation.get("epci_nom"),
        "departement": localisation.get("departement_code"),
        "region": localisation.get("region_code"),
        "veloTypes": velo_types,
        "veloEtats": velo_etats,
        "veloPrix": prix,
        "revenuReference": valeurs.get("revenu_fiscal_reference") or 0,
        "nombreParts": valeurs.get("nombre_parts_fiscales") or 1,
    })
    try:
        resultat = subprocess.run(
            ["node", "velo/calculer.mjs"], input=entree, capture_output=True,
            text=True, timeout=20, encoding="utf-8",
        )
        if resultat.returncode != 0:
            avertissements.append(f"Erreur dans le calcul des aides vélo : {resultat.stderr[:300]}")
            return []
        scenarios = json.loads(resultat.stdout)
    except Exception as e:
        avertissements.append(f"Impossible de calculer les aides vélo : {e}")
        return []

    resultats = []
    for scenario in scenarios:
        aides = []
        for a in scenario["aides"]:
            url, recherche = (a["url"], False) if a.get("url") else lien_source(a["title"], None)
            aides.append({
                "libelle": a["title"], "montant": round(a["amount"], 2), "unite": "€",
                "description": a.get("description"), "url": url, "url_est_recherche": recherche,
                "institution": a.get("institution"),
            })
        resultats.append({"scenario": scenario["scenario"], "aides": aides})
    return resultats


def calculer_aides(rapport):
    """rapport = sortie de analyser_profil(profil) (contient valeurs/personnes_valeurs)."""
    valeurs = rapport["valeurs"]
    personnes = rapport["personnes_valeurs"]
    avertissements = []

    localisation = resoudre_localisation(valeurs.get("code_postal"), valeurs.get("commune"))
    if valeurs.get("code_postal") and not localisation:
        avertissements.append("Code postal non reconnu : les aides locales et vélo n'ont pas pu être calculées.")

    nationales, locales = calculer_national_et_local(valeurs, personnes, localisation, avertissements)
    velo = calculer_velo(valeurs, localisation, avertissements)

    return {
        "aides_nationales": nationales,
        "aides_locales": locales,
        "aides_velo": velo,
        "avertissements": avertissements,
    }
