import { AidesVeloEngine } from "aides-velo"

const engine = new AidesVeloEngine()

engine.setInputs({
  "localisation . code insee": "33119",
  "localisation . epci": "Bordeaux Métropole",
  "localisation . département": "33",
  "localisation . région": "75",
  "localisation . pays": "France",
  "vélo . type": "électrique",
  "vélo . état": "neuf",
  "vélo . prix": 1000,
  "revenu fiscal de référence par part . revenu de référence": 20000,
  "revenu fiscal de référence par part . nombre de parts": 2,
})

const aides = engine.computeAides()
console.log("Nombre d'aides éligibles trouvées :", aides.length)
aides.forEach(({ title, amount }) => console.log(`- ${title} : ${amount}€`))
