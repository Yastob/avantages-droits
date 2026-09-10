"""Vérifie que l'environnement OpenFisca (national + local, venv/, Python 3.11) est fonctionnel.

Python 3.11 (pas la version système 3.14) car openfisca-france-local épingle
pandas<2.0, sans wheel pour 3.14. Nécessite aussi numpy<2 dans ce venv (sinon
conflit d'ABI binaire avec ce pandas ancien).
"""

from openfisca_france import FranceTaxBenefitSystem

tbs = FranceTaxBenefitSystem()
tbs.load_extension("openfisca_france_local")
print("OK — variables disponibles (national + local) :", len(tbs.variables))
for v in ("rsa", "aide_logement_montant", "ppa", "seine_saint_denis_cheque_reussite"):
    print(f"  - {v} : {'présent' if v in tbs.variables else 'ABSENT'}")
