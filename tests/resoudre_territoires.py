"""Pour chacun des territoires distincts extraits (commune/département/
région/métropole), trouve une commune représentative réelle (via
geo.api.gouv.fr) pour pouvoir construire un profil de test qui y est
localisé. Écrit tests/localisations_territoires.json.
"""

import json
import time
import urllib.parse
import urllib.request

with open("tests/territoires_locaux.json", encoding="utf-8") as f:
    territoires = json.load(f)

distincts = {}
for nom_var, info in territoires.items():
    distincts.setdefault((info["type"], info["slug"]), []).append(nom_var)

# Corrections des cas où le slug ne matche pas directement le nom officiel.
CORRECTIONS_NOM = {
    "eure_et_loir": "Eure-et-Loir",
    "cotes_d_armor": "Côtes-d'Armor",
    "haute_saone": "Haute-Saône",
    "haute_vienne": "Haute-Vienne",
    "loire_atlantique": "Loire-Atlantique",
    "meurthe_et_moselle": "Meurthe-et-Moselle",
    "seine_saint_denis": "Seine-Saint-Denis",
    "nouvelle-aquitaine": "Nouvelle-Aquitaine",
    "ile_de_france": "Île-de-France",
    "auvergne_rhone_alpes": "Auvergne-Rhône-Alpes",
    "grand_est": "Grand Est",
    "hauts_de_france": "Hauts-de-France",
    "pays_de_la_loire": "Pays de la Loire",
    "illkirch_graffenstaden": "Illkirch-Graffenstaden",
    "les_rues_des_vignes": "Les Rues-des-Vignes",
    "le_cateau": "Le Cateau-Cambrésis",
    "saint_louis": "Saint-Louis",
}


def get(url):
    with urllib.request.urlopen(url, timeout=10) as r:
        return json.loads(r.read())


def nom_a_chercher(slug):
    return CORRECTIONS_NOM.get(slug, slug.replace("_", " ").replace("-", " ").title())


resultats = {}
echecs = []

for (type_territoire, slug), variables in distincts.items():
    nom = nom_a_chercher(slug)
    try:
        if type_territoire == "commune":
            r = get(f"https://geo.api.gouv.fr/communes?nom={urllib.parse.quote(nom)}&fields=nom,code,codeEpci,departement,region&boost=population")
            if not r:
                echecs.append((type_territoire, slug, nom))
                continue
            c = r[0]
        elif type_territoire == "metropole":
            r = get(f"https://geo.api.gouv.fr/communes?nom={urllib.parse.quote(nom)}&fields=nom,code,codeEpci,departement,region&boost=population")
            if not r:
                echecs.append((type_territoire, slug, nom))
                continue
            c = r[0]
        elif type_territoire == "departement":
            dep = get(f"https://geo.api.gouv.fr/departements?nom={urllib.parse.quote(nom)}&fields=nom,code")
            if not dep:
                echecs.append((type_territoire, slug, nom))
                continue
            code_dep = dep[0]["code"]
            r = get(f"https://geo.api.gouv.fr/communes?codeDepartement={code_dep}&fields=nom,code,codeEpci,departement,region&boost=population")
            c = r[0]
        elif type_territoire == "region":
            reg = get(f"https://geo.api.gouv.fr/regions?nom={urllib.parse.quote(nom)}&fields=nom,code")
            if not reg:
                echecs.append((type_territoire, slug, nom))
                continue
            code_reg = reg[0]["code"]
            r = get(f"https://geo.api.gouv.fr/communes?codeRegion={code_reg}&fields=nom,code,codeEpci,departement,region&boost=population")
            c = r[0]
        epci_nom = None
        if c.get("codeEpci"):
            try:
                epci = get(f"https://geo.api.gouv.fr/epcis/{c['codeEpci']}?fields=nom")
                epci_nom = epci.get("nom")
            except Exception:
                pass
        resultats[f"{type_territoire}:{slug}"] = {
            "type": type_territoire, "slug": slug, "variables": variables,
            "depcom": c["code"], "commune_nom": c["nom"], "epci_nom": epci_nom,
            "departement_code": c.get("departement", {}).get("code"),
            "departement_nom": c.get("departement", {}).get("nom"),
            "region_code": c.get("region", {}).get("code"),
            "region_nom": c.get("region", {}).get("nom"),
        }
    except Exception as e:
        echecs.append((type_territoire, slug, f"{nom} -> ERREUR {e}"))
    time.sleep(0.05)

with open("tests/localisations_territoires.json", "w", encoding="utf-8") as f:
    json.dump(resultats, f, ensure_ascii=False, indent=2)

print(f"{len(resultats)}/{len(distincts)} territoires résolus.")
if echecs:
    print("Échecs :")
    for e in echecs:
        print(" -", e)
