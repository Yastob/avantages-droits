"""API Flask — sert le moteur d'analyse de profil aux amis qui utilisent l'outil.

Sans état : chaque requête est traitée en mémoire et son contenu n'est jamais
journalisé ni persisté (voir CLAUDE.md, section "Vie privée / partage").

Lancement local : venv/Scripts/python.exe app.py
"""

import logging

import yaml
from flask import Flask, jsonify, request, send_from_directory

from lire_profil import analyser_profil
from schema_profil import CHAMPS_PERSONNE_A_CHARGE, LIBELLES, ORDRE_CATEGORIES, SCHEMA

app = Flask(__name__, static_folder="static", static_url_path="")

# Ne jamais journaliser le contenu des requêtes (données personnelles) —
# seul le werkzeug access log par défaut (méthode + route + code retour) est gardé.
logging.getLogger("werkzeug").setLevel(logging.WARNING)


@app.post("/api/analyser-profil")
def analyser_profil_endpoint():
    if request.is_json:
        profil = request.get_json(silent=True) or {}
    else:
        try:
            profil = yaml.safe_load(request.get_data(as_text=True)) or {}
        except yaml.YAMLError as e:
            return jsonify({"erreur": f"YAML invalide : {e}"}), 400

    if not isinstance(profil, dict):
        return jsonify({"erreur": "le profil doit être un mapping (objet YAML/JSON)"}), 400

    rapport = analyser_profil(profil)
    return jsonify(rapport)


@app.get("/api/sante")
def sante():
    return jsonify({"statut": "ok"})


@app.get("/api/schema")
def schema_endpoint():
    return jsonify({
        "champs": [
            {"nom": n, "type": t, "choix": c, "categorie": cat}
            for n, t, c, cat in SCHEMA
        ],
        "champs_personne_a_charge": [
            {"nom": n, "type": t, "choix": c} for n, t, c in CHAMPS_PERSONNE_A_CHARGE
        ],
        "libelles": LIBELLES,
        "ordre_categories": ORDRE_CATEGORIES,
    })


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


if __name__ == "__main__":
    app.run(debug=True, port=5000)
