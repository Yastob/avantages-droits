// Teste le moteur aides-velo sur TOUTES les communes d'Île-de-France en un
// seul processus Node (au lieu de 1266 lancements séparés -- plus rapide,
// et évite de spammer geo.api.gouv.fr commune par commune).
// Entrée : tests/idf_communes_completes.json (préparé en amont par
// tests/preparer_communes_idf.py). Sortie : tests/rapport_velo_idf.json
import { readFileSync, writeFileSync } from "fs"
import { AidesVeloEngine } from "aides-velo"

const communes = JSON.parse(readFileSync("../tests/idf_communes_completes.json", "utf-8"))

const resultats = []
let erreurs = 0
for (const c of communes) {
  try {
    const engine = new AidesVeloEngine()
    engine.setInputs({
      "localisation . code insee": c.code,
      "localisation . epci": c.epciNom || undefined,
      "localisation . département": c.codeDepartement,
      "localisation . région": "11",
      "localisation . pays": "France",
      "vélo . type": "électrique",
      "vélo . état": "neuf",
      "vélo . prix": 1200,
      "revenu fiscal de référence par part . revenu de référence": 15000,
      "revenu fiscal de référence par part . nombre de parts": 1,
    })
    const aides = engine.computeAides()
    resultats.push({
      commune: c.nom, code: c.code, epci: c.epciNom,
      nb_aides: aides.length,
      aides: aides.map((a) => ({ titre: a.title, montant: a.amount })),
    })
  } catch (e) {
    erreurs++
    resultats.push({ commune: c.nom, code: c.code, erreur: String(e && e.message || e) })
  }
}

writeFileSync("../tests/rapport_velo_idf.json", JSON.stringify(resultats))
console.log(`${communes.length} communes traitées, ${erreurs} erreurs.`)
const avecAides = resultats.filter((r) => r.nb_aides > 0).length
console.log(`${avecAides} communes avec au moins une aide vélo trouvée.`)
const sansIdfMobilites = resultats.filter((r) => !r.erreur && !r.aides.some((a) => a.titre.includes("Île-de-France") || a.titre.includes("Ile-de-France")))
console.log(`${sansIdfMobilites.length} communes SANS l'aide régionale Île-de-France Mobilités (attendu : 0, elle est censée s'appliquer à toute la région).`)
if (sansIdfMobilites.length) {
  console.log("Exemples :", sansIdfMobilites.slice(0, 5).map(r => r.commune))
}
