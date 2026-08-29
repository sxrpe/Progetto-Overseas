"""Area studente.  ->  Da scrivere in FASE 7 (punti 7.2, 7.3, 7.6, 7.8).

ROUTE PREVISTE
    GET  /studente/pratiche                     elenco delle PROPRIE pratiche
    GET  /studente/pratiche/nuova               form di creazione
    POST /studente/pratiche/nuova               creazione
    POST /studente/pratiche/<id>/esami          aggiunta riga di mapping
    POST /studente/pratiche/<id>/date           date effettive di arrivo/partenza
    POST /studente/pratiche/<id>/documenti      caricamento di un documento

LE DUE REGOLE DA NON VIOLARE MAI IN QUESTO FILE

    1. Il filtro sta NELLA QUERY, non nel template.
       Giusto:     .where(Pratica.studente_id == current_user.id)
       Sbagliato:  caricare tutto e poi nascondere le righe altrui in Jinja.
       La seconda non e' un filtro: e' una falla.

    2. Ogni route che riceve un <id> deve chiamare esigi_accesso().
       Senza, basta cambiare il numero nell'URL per leggere la pratica di un
       altro studente.

ATTENZIONE ALLE QUERY A CASCATA
    Se l'elenco carica 50 pratiche e il template legge pratica.istituto.nome,
    l'ORM esegue 51 query invece di 1. Si risolve chiedendo il caricamento
    anticipato:
        .options(selectinload(Pratica.istituto), selectinload(Pratica.docente))
    Per accorgertene: metti SQL_ECHO=1 nel .env e conta le righe che scorrono.
"""
import datetime as dt
import sqlalchemy as sa
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy.orm import selectinload

from app.enums import Ruolo, Periodo
from app.extensions import db
from app.models import Pratica, Istituto, Utente
from app.security import ruolo_richiesto

studente_bp = Blueprint("studente", __name__)


@studente_bp.route("/pratiche", methods=["GET"])
@login_required
@ruolo_richiesto(Ruolo.STUDENTE)
def elenco_pratiche():
    """Le pratiche dello studente collegato, e solo le sue.
        option pre carica nell'oggetto le informazioni, di base si crea un'oggetto, e poi quando richiedi una info legata
        ad una chiave estera, sotto viene fatta una query, precaricarlo cosi semplifica di molto le richieste al db
        Ordinamento : ordiniamo per anno accademico e sucessivamente per il codice pratica
        scalard e all ci permettono di creare una lista di oggetti python
    """
    pratiche = db.session.scalars(
        sa.select(Pratica)
        .where(Pratica.studente_id == current_user.id)
        .options(
            selectinload(Pratica.istituto),
            selectinload(Pratica.docente),
        )
        .order_by(Pratica.anno_accademico.desc(), Pratica.codice_pratica)
    ).all()

    return render_template("studente/elenco.html", pratiche=pratiche)

def _intero(nome_campo):
    #"""Legge un campo del form come intero, None se manca o non è un numero."""
    try:
        return int(request.form.get(nome_campo, ""))
    except ValueError:
        return None

def _dati_modulo():
    #"""Le liste che servono a riempire i menu del modulo,da settembre in poi l'anno accademico è quello nuovo """
    oggi = dt.date.today()
    anno_corrente = oggi.year if oggi.month >= 9 else oggi.year - 1
    return {
        "atenei": db.session.scalars(
            sa.select(Istituto).order_by(Istituto.nome)
        ).all(),
        "docenti": db.session.scalars(
            sa.select(Utente)
            .where(Utente.ruolo == Ruolo.DOCENTE)
            .order_by(Utente.cognome, Utente.nome)
        ).all(),
        "anni": [anno_corrente, anno_corrente + 1],
    }

@studente_bp.route("/pratiche/nuova", methods=["GET", "POST"])
@login_required
@ruolo_richiesto(Ruolo.STUDENTE)
def nuova_pratica():

    if request.method == "GET":
       # "**_dati_modulo() esegue e spacchetta il dizionario "
        return render_template("studente/nuova.html",**_dati_modulo(),
                               anno_selected=None, periodo_selected=None,istituto_selected=None, docente_selected=None)
    else:
        #"Gestiamo l'invio del FORM"

        anno_selected = _intero("anno_accademico")

        if request.form.get("periodo", "") in Periodo.TUTTI:
            periodo_selected = request.form.get("periodo", "")
        else:
            periodo_selected = None

        istituto_selected = _intero("istituto_id")
        docente_selected = _intero("docente_id")

        #"Gestione campi non completati correttamente"
        if None in (anno_selected, periodo_selected,
                    istituto_selected, docente_selected):
            flash("Compila tutti i campi.", "danger")
            return render_template("studente/nuova.html",**_dati_modulo(),periodo_selected=periodo_selected, istituto_selected=istituto_selected, anno_selected=anno_selected, docente_selected=docente_selected)

        #"Formattazione del nome della Pratica : sa.func.count() = count(*)"
        quante = db.session.scalar(
            sa.select(sa.func.count())
            .select_from(Pratica)
            .where(Pratica.anno_accademico == anno_selected)
        )
        codice = f"OVS-{anno_selected}-{quante + 1:03d}"
        #"OVS-2025-001   :03d formatta l'intero su tre cifre riempendo le cifre con gli zeri"

       # "NOTA IMPORTANTE : Due studenti che premono nello stesso millisecondo potrebbero generare lo stesso codice. Il UNIQUE lo blocca e finisci nell'except del punto 7. Su questo progetto va bene così — è una riga fra le assunzioni della relazione."
        pratica = Pratica(
            codice_pratica=codice,
            anno_accademico=anno_selected,
            periodo=periodo_selected,
            istituto_id=istituto_selected,
            docente_id=docente_selected,
            studente_id=current_user.id,
        )
        db.session.add(pratica)

        try:
            db.session.commit()
        except sa.exc.IntegrityError:
            db.session.rollback()
            flash("Non è stato possibile creare la pratica: dati non validi.", "danger")
            return render_template("studente/nuova.html", **_dati_modulo(),
                                   anno_selected=anno_selected,
                                   periodo_selected=periodo_selected,
                                   istituto_selected=istituto_selected,
                                   docente_selected=docente_selected)
        except sa.exc.DatabaseError as errore:
            db.session.rollback()
            flash(str(errore.orig).split("\n")[0], "danger")
            return render_template("studente/nuova.html", **_dati_modulo(),
                                   anno_selected=anno_selected,
                                   periodo_selected=periodo_selected,
                                   istituto_selected=istituto_selected,
                                   docente_selected=docente_selected)
        flash(f"Pratica {pratica.codice_pratica} creata.", "success")
        return redirect(url_for("pratiche.dettaglio", id_pratica=pratica.id))



