"""Area studente: creazione e gestione delle proprie pratiche."""

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.enums import Periodo, Ruolo, StatoPratica
from app.extensions import db
from app.models import Istituto, Pratica, Utente
from app.security import ruolo_richiesto

studente_bp = Blueprint("studente", __name__)


@studente_bp.route("/pratiche")
@login_required
@ruolo_richiesto(Ruolo.STUDENTE)
def elenco_pratiche():
    """Solo le proprie pratiche: il filtro e' NELLA QUERY, non nel template."""
    pratiche = db.session.scalars(
        db.select(Pratica)
        .where(Pratica.studente_id == current_user.id)
        # selectinload evita il problema delle query a cascata: senza di esso
        # il template eseguirebbe una query per ogni riga dell'elenco.
        .options(selectinload(Pratica.istituto), selectinload(Pratica.docente))
        .order_by(Pratica.anno_accademico.desc(), Pratica.id.desc())
    ).all()
    return render_template("studente/elenco.html", pratiche=pratiche)


@studente_bp.route("/pratiche/nuova", methods=["GET", "POST"])
@login_required
@ruolo_richiesto(Ruolo.STUDENTE)
def nuova_pratica():
    istituti = db.session.scalars(
        db.select(Istituto).where(Istituto.attivo.is_(True)).order_by(Istituto.nome)
    ).all()
    docenti = db.session.scalars(
        db.select(Utente)
        .where(Utente.ruolo == Ruolo.DOCENTE, Utente.attivo.is_(True))
        .order_by(Utente.cognome)
    ).all()

    if request.method == "POST":
        errori = []
        anno = request.form.get("anno_accademico", "").strip()
        if len(anno) != 7 or anno[4] != "/":
            errori.append("L'anno accademico deve avere il formato 2025/26.")

        try:
            periodo = Periodo(request.form.get("periodo", ""))
        except ValueError:
            periodo = None
            errori.append("Periodo non valido.")

        istituto_id = request.form.get("istituto_id", type=int)
        docente_id = request.form.get("docente_id", type=int)
        if istituto_id not in {i.id for i in istituti}:
            errori.append("Istituto non valido.")
        if docente_id not in {d.id for d in docenti}:
            errori.append("Docente referente non valido.")

        if errori:
            for messaggio in errori:
                flash(messaggio, "error")
            return render_template(
                "studente/nuova.html",
                istituti=istituti,
                docenti=docenti,
                dati=request.form,
            ), 400

        pratica = Pratica(
            studente_id=current_user.id,
            docente_id=docente_id,
            istituto_id=istituto_id,
            anno_accademico=anno,
            periodo=periodo,
            note=request.form.get("note", "").strip() or None,
            stato=StatoPratica.CREATA,
        )
        db.session.add(pratica)
        try:
            # Un solo commit: se qualcosa viola un vincolo non resta nulla a meta'.
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("Esiste gia' una tua pratica per questo anno e questo istituto.", "error")
            return render_template(
                "studente/nuova.html", istituti=istituti, docenti=docenti, dati=request.form
            ), 409

        flash("Pratica creata.", "success")
        return redirect(url_for("pratiche.dettaglio", pratica_id=pratica.id))

    return render_template(
        "studente/nuova.html", istituti=istituti, docenti=docenti, dati={}
    )
