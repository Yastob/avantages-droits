// Calcule les aides vélo pour une situation donnée.
// Entrée : JSON sur stdin -- { codeInsee, epci, departement, region, veloType, veloEtat, veloPrix, revenuReference, nombreParts }
// Sortie : JSON sur stdout -- [{ title, amount }]
import { AidesVeloEngine } from "aides-velo"

let entree = ""
for await (const chunk of process.stdin) entree += chunk
const donnees = JSON.parse(entree)

const engine = new AidesVeloEngine()
engine.setInputs({
  "localisation . code insee": donnees.codeInsee,
  "localisation . epci": donnees.epci,
  "localisation . département": donnees.departement,
  "localisation . région": donnees.region,
  "localisation . pays": "France",
  "vélo . type": donnees.veloType,
  "vélo . état": donnees.veloEtat,
  "vélo . prix": donnees.veloPrix,
  "revenu fiscal de référence par part . revenu de référence": donnees.revenuReference,
  "revenu fiscal de référence par part . nombre de parts": donnees.nombreParts,
})

const aides = engine.computeAides().map(({ title, amount }) => ({ title, amount }))
process.stdout.write(JSON.stringify(aides))
