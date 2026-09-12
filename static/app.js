let SCHEMA = null;
let compteurPersonnes = 0;

async function chargerSchema() {
  const r = await fetch("/api/schema");
  SCHEMA = await r.json();
  construireFormulaire();
}

function construireChampSaisie(champ, idPrefix) {
  const wrap = document.createElement("div");
  wrap.className = "champ-saisie";
  wrap.dataset.champ = champ.nom;
  const id = idPrefix + champ.nom;
  const label = document.createElement("label");
  label.textContent = SCHEMA.libelles[champ.nom] || champ.nom;
  label.htmlFor = id;
  wrap.appendChild(label);

  if (champ.type === "enum_multi") {
    const groupe = document.createElement("div");
    groupe.className = "cases-a-cocher";
    groupe.id = id;
    champ.choix.forEach((c, i) => {
      const ligne = document.createElement("label");
      ligne.className = "case-a-cocher";
      const cb = document.createElement("input");
      cb.type = "checkbox";
      cb.value = c;
      cb.id = `${id}__${i}`;
      cb.dataset.type = "enum_multi";
      ligne.appendChild(cb);
      ligne.append(" " + c);
      groupe.appendChild(ligne);
    });
    wrap.appendChild(groupe);
  } else if (champ.nom === "commune") {
    // Cas spécial : plutôt que de laisser saisir un nom de commune à la
    // main (source d'erreurs, et double emploi avec le code postal), on
    // peuple ce menu dynamiquement depuis le code postal (voir
    // configurerCommuneDynamique). Un code postal peut correspondre à
    // plusieurs communes (ou l'inverse) -- d'où la désambiguïsation.
    const input = document.createElement("select");
    input.id = id;
    input.name = champ.nom;
    input.dataset.type = "enum";
    input.disabled = true;
    input.innerHTML = `<option value="">Renseignez d'abord le code postal</option>`;
    wrap.appendChild(input);
  } else {
    let input;
    if (champ.type === "bool") {
      input = document.createElement("select");
      input.innerHTML = `<option value="">Je ne sais pas</option><option value="oui">Oui</option><option value="non">Non</option>`;
    } else if (champ.type === "enum") {
      input = document.createElement("select");
      input.innerHTML = `<option value="">—</option>` + champ.choix.map((c) => `<option value="${c}">${c}</option>`).join("");
    } else if (champ.type === "date" || champ.type === "date_libre") {
      input = document.createElement("input");
      input.type = "date";
    } else if (champ.type === "float" || champ.type === "float_positif") {
      input = document.createElement("input");
      input.type = "number";
      input.step = "any";
      if (champ.type === "float_positif") input.min = "0";
    } else {
      input = document.createElement("input");
      input.type = "text";
      if (champ.type === "code_postal") { input.maxLength = 5; input.pattern = "\\d{5}"; }
    }
    input.id = id;
    input.name = champ.nom;
    input.dataset.type = champ.type;
    wrap.appendChild(input);
  }

  const aide = SCHEMA.aide && SCHEMA.aide[champ.nom];
  if (aide) {
    const p = document.createElement("p");
    p.className = "aide-champ";
    p.textContent = aide;
    wrap.appendChild(p);
  }
  return wrap;
}

function construireFormulaire() {
  const conteneur = document.getElementById("categories");
  for (const cat of SCHEMA.ordre_categories) {
    const champsCat = SCHEMA.champs.filter((c) => c.categorie === cat);
    if (!champsCat.length) continue;
    const section = document.createElement("div");
    section.className = "categorie";
    const h2 = document.createElement("h2");
    h2.textContent = cat;
    section.appendChild(h2);
    const grille = document.createElement("div");
    grille.className = "grille-champs";
    for (const champ of champsCat) grille.appendChild(construireChampSaisie(champ, "champ_"));
    section.appendChild(grille);
    conteneur.appendChild(section);
  }
  document.getElementById("ajouter-personne").addEventListener("click", () => ajouterPersonne());
  document.getElementById("telecharger-rempli").addEventListener("click", telechargerProfilRempli);
  configurerCommuneDynamique();

  const formulaire = document.getElementById("formulaire-profil");
  formulaire.addEventListener("input", surChangementFormulaire);
  formulaire.addEventListener("change", surChangementFormulaire);
  surChangementFormulaire();
}

// ============================================================================
// Commune déduite du code postal plutôt que saisie librement : un code
// postal recouvre parfois plusieurs communes (et une commune peut avoir
// plusieurs codes postaux), d'où le menu déroulant peuplé dynamiquement
// plutôt qu'un texte libre source d'erreurs de frappe/orthographe.
// ============================================================================

let minuteurCommune = null;

function configurerCommuneDynamique() {
  const champCodePostal = document.getElementById("champ_code_postal");
  const champCommune = document.getElementById("champ_commune");
  if (!champCodePostal || !champCommune) return;

  champCodePostal.addEventListener("input", () => {
    clearTimeout(minuteurCommune);
    const code = champCodePostal.value.trim();
    if (!/^\d{5}$/.test(code)) {
      champCommune.disabled = true;
      champCommune.innerHTML = `<option value="">Renseignez d'abord le code postal</option>`;
      return;
    }
    champCommune.disabled = true;
    champCommune.innerHTML = `<option value="">Recherche…</option>`;
    minuteurCommune = setTimeout(() => chargerCommunes(code, champCommune), 400);
  });
}

async function chargerCommunes(codePostal, champCommune) {
  try {
    const r = await fetch(`/api/communes?code_postal=${codePostal}`);
    const donnees = await r.json();
    const communes = donnees.communes || [];
    if (!communes.length) {
      champCommune.innerHTML = `<option value="">Code postal non reconnu</option>`;
      champCommune.disabled = true;
      return;
    }
    champCommune.innerHTML = communes.map((c) => `<option value="${c.nom}">${c.nom}</option>`).join("");
    champCommune.disabled = false;
    mettreAJourProgression();
  } catch (e) {
    champCommune.innerHTML = `<option value="">Recherche indisponible, réessayez</option>`;
  }
}

function surChangementFormulaire() {
  appliquerDependances();
  mettreAJourProgression();
}

// ============================================================================
// Lecture générique de la valeur d'un champ, quel que soit son type de saisie
// (select, input, ou groupe de cases à cocher) — utilisée par la progression
// et par le grisage conditionnel.
// ============================================================================

function valeurBruteChamp(nom, idPrefix) {
  const groupe = document.getElementById(idPrefix + nom);
  if (groupe && groupe.classList.contains("cases-a-cocher")) {
    return Array.from(groupe.querySelectorAll("input:checked")).map((c) => c.value);
  }
  const input = document.getElementById(idPrefix + nom);
  return input ? input.value.trim() : "";
}

function champEstRempli(nom, idPrefix) {
  const v = valeurBruteChamp(nom, idPrefix);
  return Array.isArray(v) ? v.length > 0 : v !== "";
}

function mettreAJourProgression() {
  let remplis = 0;
  let total = 0;
  for (const champ of SCHEMA.champs) {
    total++;
    if (champEstRempli(champ.nom, "champ_")) remplis++;
  }
  const pourcentage = total ? Math.round((remplis / total) * 100) : 0;
  document.getElementById("progression-remplie").style.width = pourcentage + "%";
  document.getElementById("progression-texte").textContent = `${remplis} / ${total} champs`;
}

// ============================================================================
// Grisage conditionnel : un champ n'a de sens que si un autre champ a une
// certaine valeur (cf. schema_profil.DEPENDANCES). On désactive et grise
// visuellement ces champs tant que la condition n'est pas remplie, pour ne
// pas laisser saisir une info qui ne sera pas utilisée sans que ce soit clair.
// ============================================================================

function conditionRemplie(parent, valeursActivantes, idPrefix) {
  const v = valeurBruteChamp(parent, idPrefix);
  if (Array.isArray(v)) return v.some((x) => valeursActivantes.includes(x));
  return valeursActivantes.includes(v);
}

function appliquerDependancesSur(idPrefix) {
  if (!SCHEMA.dependances) return;
  for (const [champ, [parent, valeursActivantes]] of Object.entries(SCHEMA.dependances)) {
    const actif = conditionRemplie(parent, valeursActivantes, idPrefix);
    const wrap = document.querySelector(`[data-champ="${champ}"]`);
    // Pour les personnes à charge, wrap ci-dessus ne cible que le formulaire
    // principal ; les cartes de personnes gèrent leurs propres dépendances
    // (aucune pour l'instant côté personne_a_charge, donc rien à faire ici).
    if (!wrap) continue;
    wrap.classList.toggle("champ-grise", !actif);
    const elements = wrap.querySelectorAll("input, select");
    elements.forEach((el) => {
      el.disabled = !actif;
      if (!actif) {
        if (el.type === "checkbox") el.checked = false;
        else el.value = "";
      }
    });
  }
}

function appliquerDependances() {
  appliquerDependancesSur("champ_");
}

function ajouterPersonne() {
  const index = compteurPersonnes++;
  const carte = document.createElement("div");
  carte.className = "personne-carte";
  carte.dataset.index = index;
  const entete = document.createElement("div");
  entete.className = "personne-entete";
  entete.innerHTML = `<span>Personne à charge</span>`;
  const retirer = document.createElement("button");
  retirer.type = "button";
  retirer.className = "bouton-lien";
  retirer.textContent = "Retirer";
  retirer.addEventListener("click", () => { carte.remove(); mettreAJourProgression(); });
  entete.appendChild(retirer);
  carte.appendChild(entete);

  const grille = document.createElement("div");
  grille.className = "grille-champs";
  for (const champ of SCHEMA.champs_personne_a_charge) {
    grille.appendChild(construireChampSaisie(champ, `personne_${index}_`));
  }
  carte.appendChild(grille);
  document.getElementById("personnes").appendChild(carte);
}

function valeurChamp(nom, idPrefix) {
  const v = valeurBruteChamp(nom, idPrefix);
  if (Array.isArray(v)) return v;
  if (v === "") return null;
  const champDef = SCHEMA.champs.concat(SCHEMA.champs_personne_a_charge).find((c) => c.nom === nom);
  if (champDef && (champDef.type === "float" || champDef.type === "float_positif")) return parseFloat(v);
  return v;
}

function collecterProfil() {
  const profil = {};
  for (const champ of SCHEMA.champs) {
    profil[champ.nom] = valeurChamp(champ.nom, "champ_");
  }
  const personnes = [];
  document.querySelectorAll(".personne-carte").forEach((carte) => {
    const index = carte.dataset.index;
    const personne = {};
    for (const champ of SCHEMA.champs_personne_a_charge) {
      personne[champ.nom] = valeurChamp(champ.nom, `personne_${index}_`);
    }
    personnes.push(personne);
  });
  profil.personnes_a_charge = personnes;
  return profil;
}

function telechargerProfilRempli() {
  const profil = collecterProfil();
  const texte = jsyaml.dump(profil, { skipInvalid: true });
  const blob = new Blob([texte], { type: "text/yaml" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "mon_profil.yml";
  a.click();
  URL.revokeObjectURL(url);
}

function formatMontant(montant) {
  return montant.toLocaleString("fr-FR", { maximumFractionDigits: 2 });
}

function rendreAideCarte(aide, periode) {
  const carte = document.createElement("div");
  carte.className = "aide-carte";
  const unite = aide.unite || "€";
  const suffixe = unite === "%" || periode === undefined || periode === "ponctuel" ? ""
    : periode.length === 4 ? " / an" : " / mois";
  const valeurAffichee = unite === "%" ? `${formatMontant(aide.montant)} %` : `${formatMontant(aide.montant)} €${suffixe}`;
  let details = "";
  if (aide.institution) details += `<div class="aide-institution">${aide.institution}</div>`;
  if (aide.description) details += `<div class="aide-description">${aide.description}</div>`;
  if (aide.url) {
    const texteLien = aide.url_est_recherche ? "Rechercher cette aide ↗" : "Voir la source ↗";
    const classe = aide.url_est_recherche ? "aide-lien aide-lien-recherche" : "aide-lien";
    details += `<a class="${classe}" href="${aide.url}" target="_blank" rel="noopener">${texteLien}</a>`;
  }
  carte.innerHTML = `
    <div class="aide-carte-entete">
      <span class="aide-nom">${aide.libelle}</span>
      <span class="aide-montant">${valeurAffichee}</span>
    </div>
    <div class="aide-details">${details}</div>
  `;
  return carte;
}

function rendreDroitSansMontantCarte(droit) {
  const carte = document.createElement("div");
  carte.className = "aide-carte aide-carte-sans-montant";
  carte.innerHTML = `
    <div class="aide-carte-entete">
      <span class="aide-nom">${droit.libelle}</span>
    </div>
    <div class="aide-details">
      <div class="aide-description">${droit.description}</div>
      <a class="aide-lien" href="${droit.url}" target="_blank" rel="noopener">Vérifier ma situation réelle ↗</a>
    </div>
  `;
  return carte;
}

function afficherAides(aides) {
  const bloc = document.getElementById("bloc-aides");
  bloc.innerHTML = "";
  let total = 0;
  let nombre = 0;

  for (const [cle, titre] of [["aides_nationales", "Aides nationales"], ["aides_locales", "Aides locales"]]) {
    const liste = aides[cle] || [];
    if (!liste.length) continue;
    nombre += liste.length;
    const groupe = document.createElement("div");
    groupe.className = "groupe-aides";
    groupe.innerHTML = `<h3>${titre}</h3>`;
    const conteneurListe = document.createElement("div");
    conteneurListe.className = "liste-aides";
    for (const aide of liste) {
      total += aide.montant;
      conteneurListe.appendChild(rendreAideCarte(aide, aide.periode));
    }
    groupe.appendChild(conteneurListe);
    bloc.appendChild(groupe);
  }

  const scenarios = aides.aides_velo || [];
  if (scenarios.length) {
    const groupe = document.createElement("div");
    groupe.className = "groupe-aides";
    const multiScenarios = scenarios.length > 1;
    groupe.innerHTML = `<h3>Aides vélo</h3>`;
    for (const scenario of scenarios) {
      if (!scenario.aides.length) continue;
      if (multiScenarios) {
        const sousTitre = document.createElement("div");
        sousTitre.className = "sous-titre-scenario";
        sousTitre.textContent = scenario.scenario;
        groupe.appendChild(sousTitre);
      }
      const conteneurListe = document.createElement("div");
      conteneurListe.className = "liste-aides";
      for (const aide of scenario.aides) {
        total += aide.montant;
        nombre++;
        conteneurListe.appendChild(rendreAideCarte(aide, "ponctuel"));
      }
      groupe.appendChild(conteneurListe);
    }
    bloc.appendChild(groupe);
  }

  const droitsSansMontant = aides.droits_sans_montant || [];
  if (droitsSansMontant.length) {
    const groupe = document.createElement("div");
    groupe.className = "groupe-aides";
    groupe.innerHTML = `<h3>Droits à vérifier (montant non calculable)</h3>`;
    const conteneurListe = document.createElement("div");
    conteneurListe.className = "liste-aides";
    for (const droit of droitsSansMontant) conteneurListe.appendChild(rendreDroitSansMontantCarte(droit));
    groupe.appendChild(conteneurListe);
    bloc.appendChild(groupe);
  }

  const suffixeDroits = droitsSansMontant.length
    ? ` + ${droitsSansMontant.length} droit${droitsSansMontant.length > 1 ? "s" : ""} à vérifier séparément (montant non calculable).`
    : "";
  document.getElementById("sous-titre-aides").textContent = nombre
    ? `${nombre} aide${nombre > 1 ? "s" : ""} potentielle${nombre > 1 ? "s" : ""} trouvée${nombre > 1 ? "s" : ""} — estimation totale ${formatMontant(total)} €.${suffixeDroits}`
    : (droitsSansMontant.length
      ? `Aucun montant calculé, mais ${droitsSansMontant.length} droit${droitsSansMontant.length > 1 ? "s" : ""} à vérifier ci-dessous.`
      : "Aucune aide trouvée avec les informations saisies — complétez le formulaire pour affiner la recherche.");

  if (!nombre && !droitsSansMontant.length) {
    bloc.innerHTML = `<p class="aucune-aide">Aucun résultat pour l'instant. Plus vous renseignez de champs, plus la recherche est précise.</p>`;
  }

  const blocAvert = document.getElementById("bloc-avertissements");
  blocAvert.innerHTML = "";
  if (aides.avertissements && aides.avertissements.length) {
    blocAvert.hidden = false;
    for (const a of aides.avertissements) {
      const d = document.createElement("div");
      d.className = "avertissement";
      d.innerHTML = `<span>ℹ️</span><span>${a}</span>`;
      blocAvert.appendChild(d);
    }
  } else {
    blocAvert.hidden = true;
  }
}

function formatValeurRecap(champ) {
  if (champ.etat === "non_renseigne") return "—";
  if (champ.etat === "mal_saisi") return champ.erreur || "format invalide";
  const v = champ.valeur;
  if (v === true) return "oui";
  if (v === false) return "non";
  if (Array.isArray(v)) return v.length ? v.join(", ") : "—";
  if (v === null || v === undefined) return "—";
  return String(v);
}

function afficherResultats(rapport) {
  const r = rapport.resume;
  document.getElementById("resultats").hidden = false;

  afficherAides(rapport.aides || { aides_nationales: [], aides_locales: [], aides_velo: [], droits_sans_montant: [], avertissements: [] });

  const tuiles = document.getElementById("tuiles");
  tuiles.innerHTML = "";
  const specTuiles = [
    ["capture", "✅ capturés", r.capture],
    ["non_renseigne", "⚠ non renseignés", r.non_renseigne],
    ["mal_saisi", "❌ mal saisis", r.mal_saisi],
    ["incoherences", "🔶 incohérences", r.incoherences],
  ];
  for (const [cle, etiquette, valeur] of specTuiles) {
    const t = document.createElement("div");
    t.className = "tuile " + cle;
    t.innerHTML = `<div class="valeur">${valeur}</div><div class="etiquette">${etiquette}</div>`;
    tuiles.appendChild(t);
  }

  const blocInc = document.getElementById("bloc-incoherences");
  const liste = document.getElementById("liste-incoherences");
  liste.innerHTML = "";
  if (rapport.incoherences.length) {
    blocInc.hidden = false;
    document.getElementById("compte-incoherences").textContent = `(${rapport.incoherences.length})`;
    for (const inc of rapport.incoherences) {
      const d = document.createElement("div");
      d.className = "incoherence";
      d.innerHTML = `<span>🔶</span><span>${inc.message}</span>`;
      liste.appendChild(d);
    }
  } else {
    blocInc.hidden = true;
  }

  document.getElementById("resultats").scrollIntoView({ behavior: "smooth", block: "start" });
}

async function soumettreFormulaire(evenement) {
  evenement.preventDefault();
  const bouton = document.getElementById("bouton-analyser");
  const statut = document.getElementById("statut-envoi");
  bouton.disabled = true;
  statut.textContent = "Analyse en cours…";

  try {
    const reponse = await fetch("/api/analyser-profil", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(collecterProfil()),
    });
    const donnees = await reponse.json();
    if (!reponse.ok) {
      statut.textContent = "";
      statut.innerHTML = `<div class="bandeau-erreur">${donnees.erreur || "Erreur inattendue."}</div>`;
      return;
    }
    statut.textContent = "";
    afficherResultats(donnees);
  } catch (e) {
    statut.innerHTML = `<div class="bandeau-erreur">Impossible de contacter le serveur. Réessayez dans un instant.</div>`;
  } finally {
    bouton.disabled = false;
  }
}

document.getElementById("formulaire-profil").addEventListener("submit", soumettreFormulaire);
chargerSchema();
