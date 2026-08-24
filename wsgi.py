"""Punto di ingresso dell'applicazione.

Avvio in sviluppo:
    flask --app wsgi run --debug
oppure:
    python wsgi.py
"""

from app import create_app

app = create_app("dev")

if __name__ == "__main__":
    app.run(debug=True)
