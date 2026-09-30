"""
DESCRIZIONE
    Punto di ingresso dell'applicazione.
    Accende Flask e lascia a create_app() tutto il montaggio.

AVVIO
    flask --app wsgi run --debug
    oppure la configurazione Flask di PyCharm puntata a questo file.
"""

from app import create_app

# "dev" in lavorazione, "demo" in presentazione (vedi config.py).
app = create_app("dev")

if __name__ == "__main__":
    app.run(debug=True)
