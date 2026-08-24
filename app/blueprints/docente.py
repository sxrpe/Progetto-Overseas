"""Area docente referente: valutazione dei documenti e riconoscimento esami."""

from datetime import datetime

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy.orm import selectinload

from app.enums import Esito, Ruolo, StatoPratica
from app.extensions import db
from app.models import Documento, Pratica
from app.security import esigi_accesso, ruolo_richiesto

docente_bp = Blueprint("docente", __name__)


@docente_bp.route("/pratiche")
@login_required
@ruolo_richiesto(Ruolo.DOCENTE)
def elenco_pratiche():
    pratiche = db.session.scalars(
        db.select(Pratica)
        .where(Pratica.docente_id == current_user.id)
        .options(selectinload(Pratica.studente), selectinload(Pratica.istituto))
        .order_by(Pratica.stato, Pratica.id)
    ).all()
    return render_template("docente/elenco.html", pratiche=pratiche)


@docente_bp.route("/documenti/<int:documento_id>/decidi", methods=["POST"])
@login_required
@ruolo_richiesto(Ruolo.DOCENTE)
def decidi_documento(documento_id: int):
    """Approva o rifiuta un documento e aggiorna lo stato della pratica.

    Le due scritture stanno in UNA sola transazione: non deve poter esistere
    un documento approvato su una pratica rimasta nello stato precedente.
    """
    documento = db.session.get(Documento, documento_id)
    if documento is None:
        abort(404)
    esigi_accesso(documento.pratica)

    approvato = request.form.get("azione") == "approva"
    motivazione = request.form.get("motivazione", "").strip() or None

    if not approvato and not motivazione:
        flash("Il rifiuto richiede una motivazione.", "error")
        return redirect(url_for("pratiche.dettaglio", pratica_id=documento.pratica_id))

    try:
        documento.esito = Esito.APPROVATO if approvato else Esito.RIFIUTATO
        documento.motivazione = motivazione
        documento.deciso_il = datetime.now()
        documento.deciso_da_id = current_user.id
        # Nessuna UPDATE scritta a mano: la Session se ne accorge da sola.
        if not approvato:
            documento.pratica.stato = StatoPratica.CREATA
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    flash("Decisione registrata.", "success")
    return redirect(url_for("pratiche.dettaglio", pratica_id=documento.pratica_id))
