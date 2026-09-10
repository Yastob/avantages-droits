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
  des résultats). Vanilla JS, pas de framework.
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
- **`type_revenus` est un champ texte libre** (pas un enum) : mappé vers la
  bonne variable OpenFisca (`salaire_net`/`chomage_net`/`retraite_nette`/
  `rpns_auto_entrepreneur_benefice`) par recherche de mots-clés, repli sur
  `salaire_net` si rien ne correspond (proxy générique le plus large).
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
- **Libellé de périodicité approximatif** : une variable OpenFisca "month"
  n'est pas forcément une aide versée chaque mois (ex. aide au permis,
  modélisée en "month" mais versée une fois) — le front affiche donc les
  montants avec un avertissement général plutôt que de prétendre à une
  périodicité exacte par dispositif.

## Prochaines étapes

1. Construire le catalogue Publicodes maison pour les dispositifs hors
   OpenFisca/aides-velo — véhicule électrique (bonus écologique, prime à la
   conversion, leasing social) en premier, cf. priorités validées.
2. Affiner le filtrage des dispositifs locaux (faux positifs/négatifs -
   voir limites ci-dessus) au fil des retours d'usage réel.
3. Modéliser un deuxième adulte (couple) dans le profil, si les retours
   d'amis montrent que l'approximation actuelle pose problème.
