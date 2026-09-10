let SCHEMA = null;
let compteurPersonnes = 0;

async function chargerSchema() {
  const r = await fetch("/api/schema");
  SCHEMA = await r.json();
  construireFormulaire();
}

function construireChampSaisie(champ) {
  const wrap = document.createElement("div");
  wrap.className = "champ-saisie";
  const label = document.createElement("label");
  label.textContent = SCHEMA.libelles[champ.nom] || champ.nom;
  label.htmlFor = "champ_" + champ.nom;
  wrap.appendChild(label);

  let input;
  if (champ.type === "bool") {
    input = document.createElement("select");
    input.innerHTML = `<option value="">—</option><option value="oui">Oui</option><option value="non">Non</option>`;
  } else if (champ.type === "enum") {
    input = document.createElement("select");
    input.innerHTML = `<option value="">—</option>` + champ.choix.map((c) => `<option value="${c}">${c}</option>`).join("");
  } else if (champ.type === "date") {
    input = document.createElement("input");
    input.type = "date";
  } else if (champ.type === "float") {
    input = document.createElement("input");
    input.type = "number";
    input.step = "any";
  } else {
    input = document.createElement("input");
    input.type = "text";
    if (champ.type === "code_postal") { input.maxLength = 5; input.pattern = "\\d{5}"; }
  }
  input.id = "champ_" + champ.nom;
  input.name = champ.nom;
  input.dataset.type = champ.type;
  wrap.appendChild(input);
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
    for (const champ of champsCat) grille.appendChild(construireChampSaisie(champ));
    section.appendChild(grille);
    conteneur.appendChild(section);
  }
  document.getElementById("ajouter-personne").addEventListener("click", () => ajouterPersonne());
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
  retirer.addEventListener("click", () => carte.remove());
  entete.appendChild(retirer);
  carte.appendChild(entete);

  const grille = document.createElement("div");
  grille.className = "grille-champs";
  for (const champ of SCHEMA.champs_personne_a_charge) {
    const c = construireChampSaisie(champ);
    c.querySelector("input, select").id = `personne_${index}_${champ.nom}`;
    c.querySelector("input, select").dataset.personneIndex = index;
    grille.appendChild(c);
  }
  carte.appendChild(grille);
  document.getElementById("personnes").appendChild(carte);
}

function valeurChamp(input) {
  const v = input.value.trim();
  if (v === "") return null;
  if (input.dataset.type === "float") return parseFloat(v);
  return v;
}

function collecterProfil() {
  const profil = {};
  for (const champ of SCHEMA.champs) {
    const input = document.getElementById("champ_" + champ.nom);
    profil[champ.nom] = valeurChamp(input);
  }
  const personnes = [];
  document.querySelectorAll(".personne-carte").forEach((carte) => {
    const index = carte.dataset.index;
    const personne = {};
    for (const champ of SCHEMA.champs_personne_a_charge) {
      const input = document.getElementById(`personne_${index}_${champ.nom}`);
      personne[champ.nom] = valeurChamp(input);
    }
    personnes.push(personne);
  });
  profil.personnes_a_charge = personnes;
  return profil;
}

function formatValeur(champ) {
  if (champ.etat === "non_renseigne") return "—";
  if (champ.etat === "mal_saisi") return champ.erreur || "format invalide";
  const v = champ.valeur;
  if (v === true) return "oui";
  if (v === false) return "non";
  if (v === null || v === undefined) return "—";
  return String(v);
}

function afficherResultats(rapport) {
  const r = rapport.resume;
  document.getElementById("resultats").hidden = false;

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
