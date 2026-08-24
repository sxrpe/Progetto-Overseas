"""Dettaglio della pratica: la pagina condivisa dai tre ruoli.

PERCHE' UN BLUEPRINT SUO
    La pagina di dettaglio serve a tutti e tre i ruoli: cambiano solo i
    comandi disponibili, decisi dai controlli in security.py. Metterla sotto
    /studente/ costringerebbe un docente a navigare in un URL che dice il
    contrario di quello che sta facendo.

    E' anche il punto centrale dell'applicazione: da qui si raggiungono tutte
    le altre azioni, ed e' la schermata che si vede di piu' nel video demo.

COSA DEVE MOSTRARE, IN ALTO E BEN VISIBILE
    Tre informazioni, sempre nella stessa posizione:
        - in che STATO e' la pratica
        - cosa MANCA per andare avanti
        - CHI deve agire adesso
    E' il modo piu' semplice per rendere comprensibile l'applicazione a chi
    la guarda per la prima volta.

ROUTE PREVISTA
    GET /pratiche/<id>      -> Fase 7
"""

from flask import Blueprint

pratiche_bp = Blueprint("pratiche", __name__)


# @pratiche_bp.route("/pratiche/<int:pratica_id>")
# @login_required
# def dettaglio(pratica_id: int):
#     pratica = db.session.get(Pratica, pratica_id)
#     if pratica is None:
#         abort(404)
#     esigi_accesso(pratica)      # <- controllo di APPARTENENZA, obbligatorio
#     return render_template("pratiche/dettaglio.html", pratica=pratica)
