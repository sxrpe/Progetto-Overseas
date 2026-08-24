"""Punto di ingresso dell'applicazione: l'interruttore che la accende.

AVVIO
    flask --app wsgi run --debug
oppure, da PyCharm, con la configurazione "Flask server" che punta a questo file.

Questo file e' volutamente minuscolo: tutto il montaggio dell'applicazione
avviene dentro create_app(), in app/__init__.py. Lo apri una volta e non lo
tocchi piu'.
"""

from app import create_app

app = create_app("dev")

if __name__ == "__main__":
    app.run(debug=True)
