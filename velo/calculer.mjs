// Calcule les aides vélo pour une situation donnée, pour chaque combinaison
// type x état sélectionnée (une personne peut hésiter entre plusieurs).
// Entrée JSON sur stdin : { codeInsee, epci, departement, region,
//   veloTypes: [...], veloEtats: [...], veloPrix, revenuReference, nombreParts }
// Sortie JSON sur stdout : [{ scenario: "type / état", aides: [{ title, amount,
//   description, url, institution }] }]
import { AidesVeloEngine } from "aides-velo"

let entree = ""
for await (const chunk of process.stdin) entree += chunk
const donnees = JSON.parse(entree)

const types = donnees.veloTypes && donnees.veloTypes.length ? donnees.veloTypes : ["électrique"]
const etats = donnees.veloEtats && donnees.veloEtats.length ? donnees.veloEtats : ["neuf"]

const resultats = []
for (const type of types) {
  for (const etat of etats) {
    const engine = new AidesVeloEngine()
    engine.setInputs({
      "localisation . code insee": donnees.codeInsee,
      "localisation . epci": donnees.epci,
      "localisation . département": donnees.departement,
      "localisation . région": donnees.region,
      "localisation . pays": "France",
      "vélo . type": type,
      "vélo . état": etat,
      "vélo . prix": donnees.veloPrix,
      "revenu fiscal de référence par part . revenu de référence": donnees.revenuReference,
      "revenu fiscal de référence par part . nombre de parts": donnees.nombreParts,
    })
    const aides = engine.computeAides().map((a) => ({
      title: a.title,
      amount: a.amount,
      description: a.description || null,
      url: a.url || null,
      institution: a.collectivity ? `${a.collectivity.kind} ${a.collectivity.value}` : null,
    }))
    resultats.push({ scenario: `${type} / ${etat}`, aides })
  }
}
process.stdout.write(JSON.stringify(resultats))
