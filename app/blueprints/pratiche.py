"""Vista di dettaglio della pratica, condivisa dai tre ruoli.

La pagina e' la stessa per studente, docente e ufficio: cambiano solo i
comandi disponibili, decisi dai controlli in app/security.py. Tenerla in un
blueprint proprio evita che un docente debba passare da un URL /studente/...
"""

from flask import Blueprint, abort, render_template
from flask_login import login_required

from app.enums import Esito, Ruolo, StatoPratica
from app.extensions import db
from app.models import Pratica
from app.security import esigi_accesso, puo_modificare_pratica
from flask_login import current_user

pratiche_bp = Blueprint("pratiche", __name__)


@pratiche_bp.route("/pratiche/<int:pratica_id>")
@login_required
def dettaglio(pratica_id: int):
    pratica = db.session.get(Pratica, pratica_id)
    if pratica is None:
        abort(404)
    # Controllo di APPARTENENZA: senza questo, cambiando l'id nell'URL si
    # leggerebbe la pratica di un altro utente.
    esigi_accesso(pratica)

    return render_template(
        "pratiche/dettaglio.html",
        pratica=pratica,
        modificabile=puo_modificare_pratica(pratica),
        # Il docente puo' decidere solo se il documento e' ancora in attesa.
        puo_decidere=(
            current_user.ruolo is Ruolo.DOCENTE
            and pratica.stato is not StatoPratica.CHIUSA
        ),
        Esito=Esito,
    )
