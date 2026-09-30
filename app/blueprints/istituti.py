"""
DESCRIZIONE
    Catalogo degli istituti partner, riservato all'ufficio Overseas.
    Lo studente non passa di qui: quando crea una pratica legge già
    tutte le righe di istituto e ne sceglie una.

MAPPA
    GET   /ufficio/istituti    elenco    catalogo e modulo di inserimento
    POST  /ufficio/istituti    elenco    aggiunge nome, paese e città
"""

import sqlalchemy as sa
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required

from app.enums import Ruolo
from app.extensions import db
from app.models import Istituto
from app.security import ruolo_richiesto

istituti_bp = Blueprint("istituti", __name__)


# ============================================================================
# ELENCO E INSERIMENTO
# GET/POST  /ufficio/istituti  ->  elenco
# ============================================================================
@istituti_bp.route("/istituti", methods=["GET", "POST"])
@login_required
@ruolo_richiesto(Ruolo.UFFICIO)
def elenco():
    """Elenco del catalogo e inserimento di un istituto (nome, paese, città)."""
    if request.method == "POST":
        nome = (request.form.get("nome") or "").strip()
        paese = (request.form.get("paese") or "").strip()
        citta = (request.form.get("citta") or "").strip()

        if not nome or not paese or not citta:
            flash("Compila nome, paese e città.", "danger")
        elif len(nome) > 160 or len(paese) > 80 or len(citta) > 80:
            flash("Nome, paese o città troppo lunghi.", "danger")
        else:
            db.session.add(Istituto(nome=nome, paese=paese, citta=citta))
            try:
                db.session.commit()
            except sa.exc.IntegrityError:
                db.session.rollback()
                flash(
                    "Esiste già un istituto con questo nome in questa città.",
                    "danger",
                )
            else:
                flash("Istituto aggiunto.", "success")
        return redirect(url_for("istituti.elenco"))

    istituti = db.session.scalars(
        sa.select(Istituto).order_by(Istituto.nome, Istituto.citta)
    ).all()
    return render_template("ufficio/istituti.html", istituti=istituti)
