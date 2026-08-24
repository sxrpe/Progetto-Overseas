"""Area ufficio Overseas: vista su tutte le pratiche, verifica e chiusura."""

from datetime import datetime

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import login_required
from sqlalchemy.orm import selectinload

from app.enums import Esito, Ruolo, StatoPratica, TipoDocumento
from app.extensions import db
from app.models import Pratica
from app.queries import pratiche_per_paese
from app.security import ruolo_richiesto

ufficio_bp = Blueprint("ufficio", __name__)


@ufficio_bp.route("/pratiche")
@login_required
@ruolo_richiesto(Ruolo.UFFICIO)
def elenco_pratiche():
    """L'ufficio vede tutto, con filtro facoltativo per stato."""
    query = (
        db.select(Pratica)
        .options(selectinload(Pratica.studente), selectinload(Pratica.istituto))
        .order_by(Pratica.id.desc())
    )
    stato_richiesto = request.args.get("stato")
    if stato_richiesto:
        try:
            query = query.where(Pratica.stato == StatoPratica(stato_richiesto))
        except ValueError:
            abort(400)

    return render_template(
        "ufficio/elenco.html",
        pratiche=db.session.scalars(query).all(),
        stati=list(StatoPratica),
        stato_attivo=stato_richiesto,
    )


@ufficio_bp.route("/cruscotto")
@login_required
@ruolo_richiesto(Ruolo.UFFICIO)
def cruscotto():
    return render_template("ufficio/cruscotto.html", per_paese=pratiche_per_paese())


@ufficio_bp.route("/pratiche/<int:pratica_id>/pre-partenza", methods=["POST"])
@login_required
@ruolo_richiesto(Ruolo.UFFICIO)
def verifica_pre_partenza(pratica_id: int):
    """Registra la fase pre-partenza SOLO se le condizioni sono soddisfatte.

    Il controllo e' ripetuto lato server anche se il pulsante viene nascosto
    nel template: nascondere un comando non e' una misura di sicurezza.
    """
    pratica = db.session.get(Pratica, pratica_id)
    if pratica is None:
        abort(404)

    la = pratica.learning_agreement
    condizioni_ok = (
        pratica.stato is StatoPratica.ATTESA_LA
        and la is not None
        and la.tipo is TipoDocumento.LEARNING_AGREEMENT
        and la.esito is Esito.APPROVATO
        and len(pratica.esami) > 0
    )
    if not condizioni_ok:
        flash("Condizioni non soddisfatte: la fase pre-partenza non puo' essere chiusa.", "error")
        return redirect(url_for("ufficio.elenco_pratiche"))

    try:
        pratica.stato = StatoPratica.PRE_PARTENZA_OK
        pratica.pre_partenza_verificata_il = datetime.now()
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    flash("Fase pre-partenza registrata.", "success")
    return redirect(url_for("ufficio.elenco_pratiche"))
