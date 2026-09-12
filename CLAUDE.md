# avantages_droits

Outil pour identifier les aides sociales, avantages fiscaux, aides à l'achat
et réductions auxquels on peut prétendre, à partir d'un profil personnel
(âge, foyer, logement, ressources, statut pro, projets en cours...).

**Changement de cap (conservé pour comprendre les choix ci-dessous)** :
conçu au départ comme un outil perso 100% local (un seul profil, jamais de
réseau). Devenu un projet à **partager avec des amis** : chacun doit pouvoir
utiliser l'outil avec son propre profil, sans repasser par moi. Ça a changé
plusieurs décisions structurantes (licence, stockage, hébergement) — voir
les sections concernées plus bas.

## Portée

Périmètre visé, sans se limiter à : aides sociales, aides fiscales, aides à
l'achat (véhicule électrique, vélo, logement), réductions (transport,
culture, sport). Discussion complète de cadrage (catégories envisagées,
sources évaluées, arbitrages) dans l'historique de conversation — non
dupliquée ici.

## Architecture — moteurs de calcul (hybride, 2 runtimes)

Le calcul d'éligibilité ne passe **pas** par un seul moteur : chaque famille
de dispositifs utilise la source la plus fiable disponible, plutôt que de
tout recoder à la main.

| Dossier | Rôle | Runtime | Pourquoi |
|---|---|---|---|
| `venv/` | `openfisca-france` + extension `openfisca-france-local` chargée dessus — prestations sociales/fiscalité nationales **et** ~90 dispositifs locaux (communes, départements, métropoles, régions) en un seul `TaxBenefitSystem` | **Python 3.11 dédié** (pas le 3.14 système) | `openfisca-france-local` épingle `pandas<2.0`, sans wheel pour Python 3.14 → Python 3.11 installé spécifiquement pour ce venv (voir note plus bas). Nécessite aussi `numpy<2` dans ce venv (sinon conflit d'ABI binaire avec ce pandas ancien). Comme l'extension inclut déjà tout `openfisca-france`, un seul environnement Python suffit pour tout le périmètre OpenFisca — pas besoin d'un venv 3.14 séparé pour le national seul. |
| `velo/` | `aides-velo` (ex `@betagouv/aides-velo`, package renommé) — moteur Publicodes pour les aides vélo nationales et locales | Node.js | Le seul module vélo public réutilisable est en JS/Publicodes, pas de portage Python |

Chaque dossier a son propre `valider_installation.{py,mjs}` — à relancer
après toute mise à jour de dépendances pour vérifier que l'environnement
charge correctement.

**Catalogue Publicodes maison** (à construire, pas encore commencé) : réservé
aux dispositifs non couverts par les trois moteurs ci-dessus — véhicule
électrique (bonus écologique, prime à la conversion, leasing social),
réductions nationales hors CAF (pass Culture, cartes SNCF grand public,
pass Sport), emploi (ACRE...), aide juridictionnelle. Le format de
métadonnées observé chez `aides-jeunes` (label / institution / description /
conditions / link / teleservice) sert de gabarit.

## Profil utilisateur

- `data/profil_template.yml` — modèle commenté, téléchargeable, à remplir
  hors ligne (édition locale, aucune donnée transmise tant que le fichier
  n'est pas relu).
- `data/profil.yml` — le profil réel, **jamais commité** (voir
  `.gitignore`), donné en local ou collé dans le chat pour traitement.
- `data/regles_coherence.yml` — règles de cohérence non bloquantes,
  vérifiées à la relecture du profil (ex : nombre de parts fiscales déclaré
  vs calculé à partir de la situation familiale). Liste vivante : proposer
  une nouvelle règle dès qu'une incohérence plausible est identifiée en
  construisant le catalogue.

Le récap de relecture du profil affiche 4 états par champ : ✅ capturé,
⚠️ non renseigné, ❌ mal saisi (format), 🔶 incohérence détectée
(cross-champ, non bloquant).

**Schéma (`schema_profil.py`)** — source de vérité unique, consommée à la
fois par le back-end (validation) et le front-end (formulaire, via
`/api/schema`) :
- Types : `date`, `float`, `float_positif` (rejette les négatifs — ex.
  épargne), `bool`, `enum` (un seul choix), `enum_multi` (plusieurs choix,
  rendu en cases à cocher côté front, stocké en liste YAML/JSON côté
  données), `text`, `code_postal`.
- `AIDE` : texte d'aide affiché sous certains champs quand le libellé seul
  prête à confusion (ex. préciser "net avant impôt, primes régulières
  incluses" pour le revenu).
- `DEPENDANCES` : quels champs ne sont pertinents que si un autre champ a
  une certaine valeur (ex. `echelon_bourse` seulement si `boursier=oui`).
  Utilisé à deux endroits : le front grise/désactive ces champs en direct
  (`appliquerDependances` dans `app.js`), et `lire_profil.py` a une règle de
  cohérence générique (`regle_champs_dependants`) qui rattrape le cas où le
  YAML est édité à la main en contournant le formulaire.

Note historique : `type_revenus` a été texte libre au tout début (le
matching par mots-clés n'était pas fiable), puis converti en `enum_multi`
— beaucoup plus robuste, mais introduit son propre compromis (voir
`calculer_aides.py` ci-dessous : un seul revenu total, pas de ventilation
par source).

## Partage avec des amis — architecture web

**Contrainte qui a tranché le design** : un Artifact Claude ne peut pas
appeler un serveur perso (CSP bloque tout `fetch` hors CDN autorisés). Le
calcul OpenFisca (Python) ne peut donc pas tourner dans un Artifact partagé
— il faut une vraie appli web autonome, hébergée en dehors de l'écosystème
Artifact.

**État : en ligne.** Dépôt public [github.com/Yastob/avantages-droits](https://github.com/Yastob/avantages-droits),
déployé sur Render (Blueprint via `render.yaml`) à
`https://avantages-droits.onrender.com`. Palier gratuit : le service se met
en veille après inactivité, 30-50s de redémarrage au premier accès.

- `app.py` — API Flask. `POST /api/analyser-profil` (YAML ou JSON) exécute
  `analyser_profil()` (validation/cohérence) **puis** `calculer_aides()`
  (éligibilité réelle), retourne les deux dans une seule réponse. `GET
  /api/schema` expose le schéma pour que le front construise le formulaire
  dynamiquement (une seule source de vérité : `schema_profil.py`). **Sans
  état** : rien n'est journalisé ni persisté côté serveur.
- `static/` — front-end (formulaire généré depuis `/api/schema`, affichage
  des résultats). Vanilla JS, pas de framework. `js-yaml` (CDN cdnjs) pour
  le bouton "Télécharger mon profil (YAML)" — sérialise `collecterProfil()`
  côté client, aucun aller-retour serveur. Le modèle vierge est servi tel
  quel par `GET /modele-profil.yml` (fichier `data/profil_template.yml`).
- `calculer_aides.py` — le moteur d'éligibilité, voir section dédiée
  ci-dessous.

## Licence des dépendances — obligation AGPL active

`openfisca-france` et `openfisca-france-local` sont sous AGPL-3.0 ;
`aides-velo` sous Apache-2.0. Tant que le service tourne en réseau et est
utilisé par d'autres (le cas dès que des amis l'utilisent), l'AGPL impose de
rendre le code source de l'appli accessible publiquement — **dépôt GitHub
public requis**, pas encore fait à ce stade.

Important : rendre le *code* public ne publie pas de *données*. Aucune
donnée personnelle ne doit jamais entrer dans le dépôt :
- `data/profil.yml`, `data/rapport_profil.json`, `artifact/recap_profil.html`
  restent git-ignorés (contiennent potentiellement de vraies données).
- Le choix "sans état" côté serveur (ci-dessus) évite qu'une base de
  données de profils d'amis existe quelque part à faire fuiter.
- Vérifier avant tout push que les logs serveur ne journalisent jamais le
  corps des requêtes (seulement méthode/route/code retour).

## Moteur d'éligibilité (`calculer_aides.py`)

Construit une simulation OpenFisca (national + local) à partir du profil,
plus un appel au module vélo Node en subprocess. Points de conception non
évidents, à ne pas re-découvrir à chaque session :

- **Revenus étalés sur 4 mois glissants**, pas juste le mois courant. RSA/PPA
  se basent sur une moyenne glissante ; fournir un revenu sur un seul mois
  fausse gravement le résultat (testé : un salaire de 1800€ déclaré sur un
  seul mois donnait un RSA de 569€, alors qu'il tombe à 0€ correctement une
  fois le même revenu étalé sur 4 mois — l'algorithme "regarde en arrière"
  sur des mois non renseignés, donc vides, donc sous-évalués).
- **`type_revenus` (enum_multi) → une seule variable OpenFisca retenue**
  (`PRIORITE_REVENU` : salaire > indépendant > chômage > retraite). Le
  profil ne capture qu'un montant total (`revenu_net_mensuel_foyer`), pas de
  ventilation par source — si plusieurs cases sont cochées, impossible de
  savoir combien vient de chaque source, donc tout est attribué à la
  source prioritaire et un avertissement explicite est ajouté au résultat.
  `pension_alimentaire_recue` est ajoutée séparément (`pensions_alimentaires_percues`).
- **Couples non modélisés individuellement** : le profil ne capture qu'une
  personne + ses personnes à charge, pas de deuxième adulte. Pour un couple,
  tout le revenu du foyer est attribué au déclarant — correct pour les
  prestations dont le calcul agrège les ressources de la famille (RSA, PPA,
  APL...), mais faussé pour les variables individuelles (AAH...). Limite
  connue, non résolue.
- **`code_postal` ≠ code INSEE (`depcom`)** : résolu via l'API publique
  `geo.api.gouv.fr` (`resoudre_localisation`), qui donne aussi EPCI/
  département/région — nécessaire à la fois pour les variables locales et
  pour le module vélo.
- **Les formules `openfisca-france-local` ne filtrent pas toutes par
  territoire elles-mêmes** (constaté en test : `antony_aide_depart_...`
  renvoyait un montant pour un profil à Bordeaux). Sans un filtrage
  supplémentaire, on ressort des aides de communes au hasard partout en
  France. Palliatif actuel : ne garder une variable locale que si son nom
  contient un des "slugs" de la commune/EPCI/département/région de la
  personne (`slugs_localisation`) — heuristique texte, pas une vraie
  vérification géographique, donc imparfaite dans les deux sens (faux
  négatifs si le nom de variable ne correspond pas au slug ; faux positifs
  résiduels possibles).
- **Distinguer un montant d'aide d'une variable intermédiaire** (plafond,
  base de ressources, taux, éligibilité booléenne...) parmi les ~90
  variables locales n'a pas de méthode fiable sans inspecter chaque
  dispositif individuellement. Filtrage par mots-clés dans le nom
  (`_MOTS_INTERMEDIAIRES`) — best-effort, à enrichir à chaque faux positif
  repéré en usage réel.
- **Vélo sans prix connu** : le profil ne demande pas systématiquement le
  prix du vélo envisagé (`prix_velo`, optionnel) ; à défaut, un prix par
  défaut (1200€) est utilisé pour l'estimation, avec avertissement explicite
  à l'utilisateur.
- **Vélo : `type_velo`/`etat_velo` en `enum_multi`** (on peut hésiter entre
  plusieurs types/états) → `calculer_velo` calcule le **produit cartésien**
  des combinaisons choisies (électrique+cargo × neuf+occasion = 4 scénarios)
  en un seul appel au sous-processus Node (`velo/calculer.mjs` accepte des
  listes `veloTypes`/`veloEtats`), pour éviter de relancer Node plusieurs
  fois. Chaque scénario est présenté séparément côté front.
- **Source et méthode de calcul affichées pour chaque aide** (national,
  local, vélo) — pas seulement le montant :
  - National/local : `variable.reference` d'OpenFisca (URL légale si
    disponible) + un texte d'institution générique ("Prestation nationale,
    calculée avec OpenFisca-France" / la collectivité identifiée via
    `institution_locale`, qui recoupe le nom de variable avec le nom de
    commune/EPCI/département/région de la personne).
  - Local : `variable.label` (texte officiel du dispositif, bien plus lisible
    que le nom de variable) utilisé comme libellé plutôt que le nom dérivé.
  - Vélo : `description`/`url`/`collectivity` renvoyés directement par
    `aides-velo` (`computeAides()` renvoie bien plus que `title`/`amount` —
    à vérifier avant de jeter des champs qu'on ne pense pas utiliser).
- **Unité € vs % pour les variables locales** : certaines variables
  openfisca-france-local ne sont pas un montant en euros mais un pourcentage
  (ex. `nouvelle_aquitaine_carte_solidaire` = "réduction obtenue en %").
  Aucune métadonnée fiable (`variable.unit` est `None` partout, y compris
  pour de vrais montants) → détection best-effort sur la présence de "%"
  dans `variable.label`. Sans ce garde-fou, on afficherait "80,00 €" pour ce
  qui est en fait "80 %".
- **Libellé de périodicité approximatif** : une variable OpenFisca "month"
  n'est pas forcément une aide versée chaque mois (ex. aide au permis,
  modélisée en "month" mais versée une fois) — le front affiche donc les
  montants avec un avertissement général plutôt que de prétendre à une
  périodicité exacte par dispositif.
- **Source citée systématiquement** (`lien_source`) : URL OpenFisca
  (`variable.reference`) quand elle existe — attention, cette liste mélange
  parfois un intitulé de texte de loi et une vraie URL (ex. Cambrai), donc
  on filtre sur ce qui commence par "http" (`premiere_url`), jamais
  `reference[0]` à l'aveugle. Sinon, lien de recherche service-public.fr
  généré à la volée (`url_est_recherche: true`) — jamais d'URL fabriquée à
  la main pour un dispositif précis, un lien inventé/faux serait pire que
  pas de lien.
- **Commune déduite du code postal, pas saisie libre** (`/api/communes`,
  `configurerCommuneDynamique` dans `app.js`) : un texte libre pour la
  commune était source d'erreurs et faisait doublon avec le code postal.
  Le champ est maintenant un menu déroulant peuplé dynamiquement (gère le
  cas où un code postal recouvre plusieurs communes, ex. `07100` →
  Annonay/Boulieu-lès-Annonay/Roiffieux/Saint-Marcel-lès-Annonay).

### Audit des champs du profil réellement utilisés dans le calcul

Retour d'usage : beaucoup de champs du formulaire n'étaient pas exploités
par `calculer_aides.py`, malgré une correspondance OpenFisca disponible.
Vérifié avec `grep -oE 'valeurs\.get\("[a-z_]+"\)' calculer_aides.py` (à
relancer après tout ajout de champ pour vérifier qu'il est bien câblé, ou
consciemment laissé de côté).

**Câblés au calcul** (via OpenFisca sauf mention contraire) : `date_naissance`,
`situation_familiale` (→ `statut_marital`), `code_postal`/`commune` (→
localisation), `statut_logement`, `loyer_mensuel`, `revenu_net_mensuel_foyer`,
`revenu_fiscal_reference` (vélo uniquement), `type_revenus`, `situation_handicap`,
`taux_incapacite`, `pension_alimentaire_recue`, `pension_alimentaire_versee`,
`statut_professionnel` (→ `activite`), `nombre_parts_fiscales` (cohérence +
vélo, pas injecté dans OpenFisca qui le recalcule lui-même — normal),
`projet_velo`/`type_velo`/`etat_velo`/`prix_velo`.

**Pas encore câblés** — délibérément, réservés au futur catalogue
Publicodes (véhicule électrique, logement, réductions, emploi...) déjà
identifié comme non commencé : `residence`, `mensualite_pret_immobilier`,
`zone_faibles_emissions`, `epargne_liquide`, `autre_bien_immobilier`,
`aides_deja_percues`, `frais_garde_enfants`, `anciennete_statut`,
`inscrit_france_travail`, `indemnise_chomage`, `niveau_etudes`, `boursier`,
`echelon_bourse`, `entreprise_secteur`, `situation_perte_autonomie`,
`utilise_transports_commun`, `reseau_transport_principal`,
`carte_etudiante_scolaire`, `projet_vehicule_electrique`,
`type_projet_vehicule`, `vehicule_actuel_a_mettre_a_la_casse`,
`projet_achat_logement`, `primo_accedant`, `projet_renovation_energetique`,
`type_travaux_envisages`, `pratique_sportive_reguliere`,
`frequentation_culturelle`.

Note pour `epargne_liquide`/`autre_bien_immobilier` spécifiquement : pas de
variable OpenFisca "patrimoine total" en entrée directe trouvée (seulement
des variables très spécifiques comme `livret_a`, ou des variables déjà
calculées comme `rsa_base_ressources_patrimoine_individu`) — contrairement
aux autres champs de cette liste, ce n'est pas juste "pas encore fait", il
faudrait d'abord clarifier comment OpenFisca attend cette donnée avant de
pouvoir la câbler correctement.

## Droits sans montant calculable (`droits_sans_montant`, APA/CPF)

Certains droits ont une **éligibilité** calculable mais un **montant** qui
ne l'est pas à partir d'un simple profil déclaratif :
- **APA** (`gir` + `situation_perte_autonomie` dans le profil) : l'âge et le
  GIR (Groupe Iso-Ressources, 1-6, classification officielle du degré de
  dépendance) suffisent à calculer `apa_eligibilite`, mais le montant réel
  dépend d'un "plan d'aide" évalué au cas par cas par le conseil
  départemental (`dependance_plan_aide_domicile_accepte`, une donnée qu'on
  n'a pas et ne peut pas demander). Afficher un montant ici serait trompeur.
- **CPF** : aucune variable dans OpenFisca — le CPF est un vrai compte
  individuel alimenté par l'historique d'emploi réel, pas une règle
  calculable. Toujours affiché (`DROITS_TOUJOURS_AFFICHES`), avec un lien
  vers moncompteformation.gouv.fr plutôt qu'une estimation (choix
  utilisateur : lien seul, pas d'estimation du taux d'acquisition annuel).
- **PCH** : variable présente dans OpenFisca mais son propre commentaire
  dit littéralement `# inutilisée pour l'instant` — formule non
  implémentée côté OpenFisca lui-même. Pas exploitable, à traiter un jour
  via un lien externe si besoin (comme le CPF), pas via OpenFisca.

Mécanisme (`calculer_aides.py`) : `DROITS_SANS_MONTANT` (variable
d'éligibilité + libellé + description + lien, vérifiée par simulation) et
`DROITS_TOUJOURS_AFFICHES` (toujours inclus, sans condition). Résultat
exposé dans une 4e clé `droits_sans_montant` (à côté de
`aides_nationales`/`aides_locales`/`aides_velo`), rendu par le front dans
une section visuellement distincte ("Droits à vérifier (montant non
calculable)", bordure de couleur différente) — jamais mélangé au total en
€ des aides chiffrées.

**Formations gratuites** (France Travail, régions, VAE, Transitions Pro...)
— pas encore traité : trop hétérogène pour un calcul d'éligibilité unique,
plutôt candidat à des fiches-annuaire (même format que
`DROITS_TOUJOURS_AFFICHES`) orientant selon le statut de la personne. Pas
commencé.

## Ambiguïtés de format/périodicité clarifiées dans l'aide contextuelle

Retour d'usage : plusieurs champs ne précisaient pas leur unité, source de
confusion. Clarifié via `AIDE` (`schema_profil.py`) plutôt que renommer les
champs :
- `pension_alimentaire_recue`/`pension_alimentaire_versee` : montant
  **mensuel**, pas annuel (aucune indication avant).
- `aides_deja_percues` : texte libre (ex. "RSA, APL"), purement informatif
  pour l'instant — ne modifie pas le calcul (aucune règle de cohérence ne
  le lit encore).
- Confirmé à l'utilisateur : les APL/ALF/ALS sont bien couvertes, via la
  variable OpenFisca unique `aide_logement` qui choisit automatiquement la
  bonne prestation selon la situation (déjà dans `NATIONAL_VARIABLES`
  depuis le début, mais pas explicitement documenté comme réponse à "est-ce
  que les APL sont gérées ?").

## Cahier de test (`tests/`)

Suite à un signalement ("le RSA n'est pas trouvé pour un profil sans
enfant" — en fait le comportement correct : RSA réservé aux 25 ans+ sauf
enfant à charge, cf. discussion), une vraie campagne de test a été montée.
Méthode : **utiliser OpenFisca lui-même comme oracle** (analyse de
sensibilité — faire varier une variable à la fois et observer le seuil de
bascule) plutôt que de relire le code source à la main pour deviner les
conditions d'éligibilité.

Composition :
- `tests/extraire_territoires.py` — cartographie chacune des ~171 variables
  locales vers son territoire cible (commune/département/région/métropole),
  lu directement depuis `variable.introspection_data[0]` (le chemin du
  fichier source dans le paquet installé) — pas une déduction depuis le nom
  de variable, une vraie source de vérité.
- `tests/resoudre_territoires.py` — trouve une commune réelle représentative
  de chacun des territoires distincts (via geo.api.gouv.fr).
- `tests/test_filtrage_geographique.py` — **exhaustif** sur les 171
  variables locales (51 candidates réellement affichables une fois les
  variables intermédiaires exclues) : teste que le filtrage géographique
  maison (`variable_correspond_localisation`) inclut chaque variable sur
  son propre territoire et l'exclut de tous les autres. Pur test de texte,
  aucun appel OpenFisca, quelques secondes d'exécution.
- `tests/test_national.py` — 19 cas de sensibilité sur les 9 variables
  nationales (âge, revenu, enfants, handicap, logement...).
- `tests/test_calcul_reel_par_territoire.py` — un calcul réel (pas juste du
  filtrage texte) par territoire, pour vérifier qu'aucune exception n'est
  levée sur l'ensemble des 37 territoires réels.
- `tests/executer_tous_les_tests.py` — lance tout, bilan consolidé.
- `velo/test_idf.mjs` — **exhaustif** sur les 1266 communes d'Île-de-France
  (un seul processus Node, pas 1266 lancements séparés) : vérifie l'absence
  d'erreur et que l'aide régionale IDF Mobilités ressort partout.

**Résultat au moment de la rédaction** : filtrage géographique 48/51 (3
variables MSA volontairement non couvertes, cf. ci-dessous) ; national
19/19 ; calcul réel 37/37 sans erreur ; vélo IDF 1266/1266 sans erreur.

### Bugs réels trouvés et corrigés grâce à ce cahier de test

1. **Faux positifs par sous-chaîne courte** : le département "Ain" (slug
   `ain`) matchait à tort n'importe quelle variable contenant "s**ain**t"
   ou "aquit**ain**e" — `nouvelle_aquitaine_aide_permis` ressortait pour un
   profil dans l'Ain. Corrigé : `slug_correspond` compare des **mots
   entiers** (séquence de tokens snake_case), plus jamais une sous-chaîne
   brute.
2. **RFR (revenu fiscal de référence) jamais transmis à OpenFisca** :
   `revenu_fiscal_reference` n'était utilisé que par le module vélo ;
   `cheque_energie` (et d'autres dispositifs basés sur le RFR) restaient à
   0 car OpenFisca le recalculait lui-même à partir d'un revenu mensuel
   incomplet (fenêtre glissante, pas l'année entière). Corrigé : le RFR
   déclaré écrase directement `foyers_fiscaux.foyer.rfr`.
3. **`cheque_energie_montant` lit le RFR de l'année N-2** (`rfr(period.n_2)`),
   pas l'année en cours — découvert en lisant le code source de la formule
   via `variable.introspection_data[1]` (OpenFisca expose le code source
   complet, pas juste les métadonnées). Corrigé : le RFR déclaré est
   renseigné à la fois pour l'année en cours et l'année N-2.
4. **Désalignement de période** : `statut_occupation_logement`/`depcom`/
   `loyer` n'étaient renseignés que pour le mois courant, mais certaines
   formules annuelles (ex. `cheque_energie_eligibilite_logement`) lisent
   spécifiquement `period.first_month` (= janvier) — invisible si le mois
   courant est différent de janvier. Corrigé : `MOIS_FENETRE` passé de 4 à
   13 mois, et tous les champs mensuels (revenus, logement, activité,
   statut marital, handicap...) suivent désormais cette même fenêtre
   étendue plutôt que le seul mois courant.

### Limites connues restant après ce cahier de test

- **3 aides au permis MSA** (Armorique / Midi-Pyrénées Sud / Nord-Pas-de-
  Calais) non détectées : les caisses MSA ont leurs propres découpages
  territoriaux, différents des départements/régions INSEE — deviner leur
  périmètre exact risquerait d'afficher l'aide aux mauvaises personnes,
  jugé pire que ne pas la détecter du tout.
- Le calcul réel par territoire vérifie l'absence de crash, pas que
  chaque dispositif se déclenche pour un profil donné (une valeur à 0 peut
  être une vraie inéligibilité du profil de test, pas un bug) — c'est le
  test de filtrage géographique qui garantit l'exhaustivité proprement dite.
- "RSA jeune actif" (dérogation d'âge par activité professionnelle passée,
  pas seulement par enfant à charge) non modélisé — nécessiterait de
  collecter un historique d'emploi qu'on ne demande pas actuellement.

## Prochaines étapes

1. Construire le catalogue Publicodes maison pour les dispositifs hors
   OpenFisca/aides-velo — véhicule électrique (bonus écologique, prime à la
   conversion, leasing social) en premier, cf. priorités validées.
2. Affiner le filtrage des dispositifs locaux (faux positifs/négatifs -
   voir limites ci-dessus) au fil des retours d'usage réel.
3. Modéliser un deuxième adulte (couple) dans le profil, si les retours
   d'amis montrent que l'approximation actuelle pose problème.
