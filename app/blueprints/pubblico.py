"""Pagine accessibili senza autenticazione.

In questo scheletro contiene l'unica route funzionante: una pagina di
verifica che dice se l'applicazione e' montata bene e se il database
risponde. Serve a chiudere la Tappa 1 con una prova visibile.

Quando il progetto crescera', qui resteranno solo la home pubblica e lo
smistamento verso l'area del ruolo dell'utente.
"""

import sqlalchemy as sa
from flask import Blueprint, current_app, render_template

from app.extensions import db

pubblico_bp = Blueprint("pubblico", __name__)


@pubblico_bp.route("/")
def home():
    """Pagina di verifica dell'installazione.

    Prova a eseguire la query piu' banale possibile (SELECT 1) per capire se
    la connessione al database funziona davvero, invece di limitarsi a
    mostrare la stringa di configurazione.
    """
    try:
        db.session.execute(sa.text("SELECT 1"))
        db_ok, db_errore = True, None
    except Exception as e:                      # noqa: BLE001
        db_ok, db_errore = False, str(e)

    url = db.engine.url
    return render_template(
        "home.html",
        db_ok=db_ok,
        db_errore=db_errore,
        db_dialetto=url.get_backend_name(),
        db_descrizione=url.render_as_string(hide_password=True),
        tabelle=sorted(db.metadata.tables),
        debug=current_app.debug,
    )


# ---------------------------------------------------------------------------
# FASE 6 — da aggiungere quando esistono gli utenti e i ruoli.
#
# @pubblico_bp.route("/cruscotto")
# @login_required
# def cruscotto():
#     """Manda ogni utente nell'area del proprio ruolo."""
#     destinazioni = {
#         Ruolo.STUDENTE: "studente.elenco_pratiche",
#         Ruolo.DOCENTE:  "docente.elenco_pratiche",
#         Ruolo.UFFICIO:  "ufficio.elenco_pratiche",
#     }
#     return redirect(url_for(destinazioni[current_user.ruolo]))
