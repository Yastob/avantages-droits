"""Schéma déclaratif du profil : un champ = (nom, type, choix, catégorie).

Types reconnus :
  "date", "float", "float_positif" (float >= 0), "bool", "enum" (une seule
  valeur parmi `choix`), "enum_multi" (plusieurs valeurs parmi `choix`),
  "text", "code_postal".
`choix` n'est utilisé que pour "enum"/"enum_multi". La catégorie sert
uniquement à regrouper l'affichage dans le formulaire/récap.
"""

CHAMPS_PERSONNE_A_CHARGE = [
    ("date_naissance", "date", None),
    ("lien", "enum", ["enfant", "autre"]),
    ("scolarise", "bool", None),
    ("situation_handicap", "bool", None),
    ("garde_alternee", "bool", None),
]

SCHEMA = [
    ("date_naissance", "date", None, "Identité"),
    ("situation_familiale", "enum",
     ["célibataire", "concubinage", "pacsé·e", "marié·e", "divorcé·e", "veuf·ve"], "Identité"),

    ("nombre_parts_fiscales", "float", None, "Foyer"),

    ("code_postal", "code_postal", None, "Logement"),
    ("commune", "text", None, "Logement"),
    ("statut_logement", "enum",
     ["locataire", "propriétaire", "hébergé·e à titre gratuit", "sans domicile stable"], "Logement"),
    ("residence", "enum", ["principale", "secondaire"], "Logement"),
    ("loyer_mensuel", "float", None, "Logement"),
    ("mensualite_pret_immobilier", "float", None, "Logement"),
    ("zone_faibles_emissions", "bool", None, "Logement"),

    ("revenu_net_mensuel_foyer", "float", None, "Ressources"),
    ("revenu_fiscal_reference", "float", None, "Ressources"),
    ("type_revenus", "enum_multi",
     ["salaire", "chômage", "retraite", "indépendant / auto-entrepreneur", "aucun revenu"], "Ressources"),
    ("epargne_liquide", "float_positif", None, "Ressources"),
    ("autre_bien_immobilier", "bool", None, "Ressources"),
    ("pension_alimentaire_recue", "float", None, "Ressources"),
    ("aides_deja_percues", "text", None, "Ressources"),

    ("frais_garde_enfants", "float", None, "Dépenses"),
    ("pension_alimentaire_versee", "float", None, "Dépenses"),

    ("statut_professionnel", "enum_multi", [
        "salarié·e", "indépendant·e-auto-entrepreneur·se", "demandeur·se d'emploi",
        "étudiant·e", "apprenti·e-alternant·e", "retraité·e", "sans activité",
    ], "Situation professionnelle"),
    ("anciennete_statut", "text", None, "Situation professionnelle"),
    ("inscrit_france_travail", "bool", None, "Situation professionnelle"),
    ("indemnise_chomage", "bool", None, "Situation professionnelle"),
    ("niveau_etudes", "enum", [
        "lycée", "BTS-DUT", "licence", "master", "doctorat", "formation sanitaire-sociale", "autre",
    ], "Situation professionnelle"),
    ("boursier", "bool", None, "Situation professionnelle"),
    ("echelon_bourse", "text", None, "Situation professionnelle"),
    ("entreprise_secteur", "enum", ["public", "privé"], "Situation professionnelle"),

    ("situation_handicap", "bool", None, "Situations particulières"),
    ("taux_incapacite", "float", None, "Situations particulières"),
    ("situation_perte_autonomie", "bool", None, "Situations particulières"),
    ("gir", "enum", ["GIR 1", "GIR 2", "GIR 3", "GIR 4", "GIR 5", "GIR 6"], "Situations particulières"),

    ("utilise_transports_commun", "bool", None, "Mobilité"),
    ("reseau_transport_principal", "enum_multi", [
        "SNCF (grandes lignes)",
        "Île-de-France Mobilités (RATP / Transilien / RER)",
        "réseau urbain hors IDF (métro/tram/bus de ma ville)",
        "réseau régional (TER, car interurbain)",
    ], "Mobilité"),
    ("carte_etudiante_scolaire", "bool", None, "Mobilité"),

    ("projet_vehicule_electrique", "bool", None, "Projets"),
    ("type_projet_vehicule", "enum_multi",
     ["achat neuf", "achat occasion", "location longue durée"], "Projets"),
    ("vehicule_actuel_a_mettre_a_la_casse", "bool", None, "Projets"),
    ("projet_velo", "bool", None, "Projets"),
    ("type_velo", "enum_multi", ["électrique", "cargo", "pliant", "adapté handicap"], "Projets"),
    ("etat_velo", "enum_multi", ["neuf", "occasion"], "Projets"),
    ("prix_velo", "float", None, "Projets"),
    ("projet_achat_logement", "bool", None, "Projets"),
    ("primo_accedant", "bool", None, "Projets"),
    ("projet_renovation_energetique", "bool", None, "Projets"),
    ("type_travaux_envisages", "enum_multi",
     ["isolation", "chauffage", "fenêtres"], "Projets"),

    ("pratique_sportive_reguliere", "bool", None, "Pratiques"),
    ("frequentation_culturelle", "bool", None, "Pratiques"),
]

LIBELLES = {
    "date_naissance": "Date de naissance",
    "situation_familiale": "Situation familiale",
    "nombre_parts_fiscales": "Nombre de parts fiscales",
    "code_postal": "Code postal",
    "commune": "Commune",
    "statut_logement": "Statut du logement",
    "residence": "Résidence principale ou secondaire",
    "loyer_mensuel": "Loyer mensuel",
    "mensualite_pret_immobilier": "Mensualité de prêt immobilier",
    "zone_faibles_emissions": "En zone à faibles émissions (ZFE)",
    "revenu_net_mensuel_foyer": "Revenu net mensuel du foyer",
    "revenu_fiscal_reference": "Revenu fiscal de référence",
    "type_revenus": "Type(s) de revenus",
    "epargne_liquide": "Épargne (livrets, assurance-vie...)",
    "autre_bien_immobilier": "Autre bien immobilier (hors résidence principale)",
    "aides_deja_percues": "Aides déjà perçues",
    "frais_garde_enfants": "Frais de garde d'enfants",
    "pension_alimentaire_versee": "Pension alimentaire versée",
    "pension_alimentaire_recue": "Pension alimentaire reçue",
    "statut_professionnel": "Statut professionnel",
    "anciennete_statut": "Ancienneté dans ce statut",
    "inscrit_france_travail": "Inscrit·e à France Travail",
    "indemnise_chomage": "Indemnisé·e chômage",
    "niveau_etudes": "Niveau d'études",
    "boursier": "Boursier·ère",
    "echelon_bourse": "Échelon de bourse",
    "entreprise_secteur": "Secteur de l'entreprise (alternance)",
    "situation_handicap": "Situation de handicap",
    "taux_incapacite": "Taux d'incapacité",
    "situation_perte_autonomie": "Situation de perte d'autonomie",
    "utilise_transports_commun": "Utilise les transports en commun",
    "reseau_transport_principal": "Réseau(x) de transport utilisé(s)",
    "carte_etudiante_scolaire": "Carte étudiante/scolaire",
    "projet_vehicule_electrique": "Projet de véhicule électrique",
    "type_projet_vehicule": "Type de projet véhicule envisagé",
    "vehicule_actuel_a_mettre_a_la_casse": "Véhicule actuel à mettre à la casse",
    "projet_velo": "Projet vélo",
    "type_velo": "Type(s) de vélo envisagé(s)",
    "etat_velo": "Neuf et/ou d'occasion",
    "prix_velo": "Prix du vélo envisagé",
    "projet_achat_logement": "Projet d'achat de logement",
    "primo_accedant": "Primo-accédant·e",
    "projet_renovation_energetique": "Projet de rénovation énergétique",
    "type_travaux_envisages": "Type(s) de travaux envisagés",
    "pratique_sportive_reguliere": "Pratique sportive régulière",
    "frequentation_culturelle": "Fréquentation culturelle",
    "lien": "Lien",
    "scolarise": "Scolarisé·e",
    "garde_alternee": "Garde alternée",
    "gir": "GIR (degré de dépendance)",
}

# Texte d'aide affiché sous certains champs, quand le libellé seul ne suffit
# pas à lever une ambiguïté (retours d'usage réel).
AIDE = {
    "revenu_net_mensuel_foyer": (
        "Net de cotisations sociales, avant impôt sur le revenu. Incluez les primes "
        "régulières (ex : 13e mois lissé sur l'année), pas les primes exceptionnelles ponctuelles."
    ),
    "epargne_liquide": (
        "Livrets, assurance-vie, comptes-titres... Ne comptez pas votre résidence "
        "principale ici (elle est déjà prise en compte via le logement ci-dessus)."
    ),
    "type_revenus": (
        "Si plusieurs cases sont cochées, le calcul retient le type principal "
        "(salaire > indépendant > chômage > retraite) — la répartition exacte entre "
        "plusieurs revenus n'est pas encore modélisée."
    ),
    "pension_alimentaire_recue": "Montant MENSUEL (pas annuel).",
    "pension_alimentaire_versee": "Montant MENSUEL (pas annuel).",
    "aides_deja_percues": (
        "Texte libre, ex : \"RSA, APL\". Informatif uniquement pour l'instant — "
        "ne modifie pas encore le calcul, sert juste de repère pour vous "
        "(et pour nous, si un jour on ajoute une vérification de cohérence dessus)."
    ),
    "gir": (
        "Groupe Iso-Ressources : classification officielle du degré de dépendance "
        "(1 = dépendance la plus forte, 6 = autonome), évaluée par une équipe "
        "médico-sociale (conseil départemental, médecin). Si vous ne le connaissez "
        "pas, un travailleur social ou votre conseil départemental peut vous orienter."
    ),
}

# Champs dont la pertinence dépend de la valeur d'un autre champ — grisés et
# non saisissables tant que la condition n'est pas remplie. Format :
# champ_dependant: (champ_dont_ça_dépend, [valeurs qui activent le champ]).
# Pour un champ parent "bool", la valeur activante est toujours "oui".
# Pour un parent "enum_multi", le champ s'active si au moins une des valeurs
# sélectionnées est dans la liste.
DEPENDANCES = {
    "loyer_mensuel": ("statut_logement", ["locataire"]),
    "mensualite_pret_immobilier": ("statut_logement", ["propriétaire"]),
    "inscrit_france_travail": ("statut_professionnel", ["demandeur·se d'emploi"]),
    "indemnise_chomage": ("statut_professionnel", ["demandeur·se d'emploi"]),
    "niveau_etudes": ("statut_professionnel", ["étudiant·e"]),
    "boursier": ("statut_professionnel", ["étudiant·e"]),
    "echelon_bourse": ("boursier", ["oui"]),
    "entreprise_secteur": ("statut_professionnel", ["apprenti·e-alternant·e"]),
    "taux_incapacite": ("situation_handicap", ["oui"]),
    "gir": ("situation_perte_autonomie", ["oui"]),
    "reseau_transport_principal": ("utilise_transports_commun", ["oui"]),
    "type_projet_vehicule": ("projet_vehicule_electrique", ["oui"]),
    "vehicule_actuel_a_mettre_a_la_casse": ("projet_vehicule_electrique", ["oui"]),
    "type_velo": ("projet_velo", ["oui"]),
    "etat_velo": ("projet_velo", ["oui"]),
    "prix_velo": ("projet_velo", ["oui"]),
    "primo_accedant": ("projet_achat_logement", ["oui"]),
    "type_travaux_envisages": ("projet_renovation_energetique", ["oui"]),
}

ORDRE_CATEGORIES = [
    "Identité", "Foyer", "Logement", "Ressources", "Dépenses",
    "Situation professionnelle", "Situations particulières", "Mobilité",
    "Projets", "Pratiques",
]
