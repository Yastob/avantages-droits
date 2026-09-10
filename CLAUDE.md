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

- `app.py` — API Flask, endpoint `POST /api/analyser-profil` (accepte YAML
  ou JSON), réutilise `analyser_profil()` de `lire_profil.py`. **Sans état** :
  chaque requête est traitée en mémoire, rien n'est journalisé ni persisté
  côté serveur — décision volontaire pour limiter la responsabilité sur des
  données sensibles d'un tiers (voir "Vie privée" ci-dessous). Testé en
  local via `app.test_client()`, pas encore déployé.
- `Procfile` — `gunicorn app:app`, prêt pour un déploiement Render (choisi
  comme hébergeur — palier gratuit, déploiement direct depuis GitHub, mais
  le service gratuit se met en veille après inactivité).
- Front-end web (formulaire de profil, affichage des résultats) : **pas
  encore construit**. Le flux "template YAML téléchargé / édité en
  local / uploadé" pensé pour l'usage perso solo reste à réévaluer pour des
  amis moins techniques — probablement un vrai formulaire web à un moment,
  pas encore tranché.

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

## Prochaines étapes (non commencées)

1. Front-end web pour remplir un profil (probablement un vrai formulaire,
   à trancher) + afficher le récap (reprendre le design de
   `artifact/recap_profil_gabarit.html`, adapté pour consommer l'API au
   lieu de données injectées).
2. Moteur de matching : orchestrer les runtimes (appel subprocess vers
   `velo/` depuis `app.py`) + le futur catalogue Publicodes, à partir d'un
   profil reçu par l'API.
3. Construire le catalogue Publicodes maison (véhicule électrique en
   premier, cf. priorités validées).
4. Créer le dépôt GitHub public (nom à définir, cf. convention CLAUDE.md
   global : le nom du dépôt n'a pas besoin de correspondre au dossier
   local), pousser le code, déployer sur Render.
