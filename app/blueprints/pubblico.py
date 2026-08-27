"""Pagine accessibili senza autenticazione.

Per ora contiene solo la home, che fa tre cose:
    - verifica che il database risponda davvero (non che sia configurato:
      che risponda)
    - saluta chi e' entrato
    - indirizza ciascun ruolo alla propria area

Quando ci saranno le rotte delle tre aree, i collegamenti si accendono
togliendo i commenti nel template.
"""

import sqlalchemy as sa
from flask import Blueprint, render_template

from app.extensions import db

pubblico_bp = Blueprint("pubblico", __name__)


@pubblico_bp.route("/")
def home():
    """Home pubblica, con diagnosi della connessione al database.

    PERCHE' UNA QUERY VERA E NON UN CONTROLLO DELLA CONFIGURAZIONE
        Leggere SQLALCHEMY_DATABASE_URI dice solo che c'e' scritto qualcosa
        nel file di configurazione. "SELECT 1" e' la query piu' banale che
        esista e prova che la connessione si apre davvero: se PostgreSQL e'
        spento, o la password e' sbagliata, o il database non esiste, qui
        salta fuori subito invece che alla prima pagina vera.

    PERCHE' try/except
        Se il database non risponde vogliamo mostrare una pagina che lo dice,
        non una schermata di errore. Un'eccezione non gestita qui renderebbe
        l'applicazione muta proprio nel momento in cui serve capire cosa non
        va.
    """
    try:
        db.session.execute(sa.text("SELECT 1"))
        db_ok = True
        db_messaggio = "Connessione al database attiva."
    except Exception as errore:
        db_ok = False
        db_messaggio = f"Database non raggiungibile: {errore.__class__.__name__}"

    return render_template("home.html", db_ok=db_ok, db_messaggio=db_messaggio)