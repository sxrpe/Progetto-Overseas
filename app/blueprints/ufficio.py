"""
DESCRIZIONE
    Area ufficio Overseas: verifica pre-partenza e chiusura pratica.
    Vede tutte le pratiche; non giudica il merito didattico (quello è del docente).

MAPPA
    GET  /ufficio/pratiche                     elenco_pratiche          tutte le pratiche
    GET  /ufficio/pratiche/<id>/la             vedi_la                  piano in sola lettura
    POST /ufficio/pratiche/<id>/verifica       verifica_pre_partenza    registra verifica
    POST /ufficio/pratiche/<id>/chiudi         chiudi_pratica           chiude la pratica
"""

import datetime as dt

import sqlalchemy as sa
from flask import Blueprint, abort, flash, redirect, render_template, url_for
from flask_login import current_user, login_required
from sqlalchemy.orm import selectinload

from app.enums import EsitoDocumento, Ruolo, StatoPratica
from app.extensions import db
from app.models import CorsoEsterno, Equivalenza, LearningAgreement, Pratica
from app.security import ruolo_richiesto

ufficio_bp = Blueprint("ufficio", __name__)


# ============================================================================
# UTILITY
# ============================================================================

def _pratica(id_pratica: int) -> Pratica:
    """Carica una pratica qualsiasi.

    L'ufficio le vede tutte: niente controllo, solo 404
    se l'id non esiste.
    """
    pratica = db.session.get(Pratica, id_pratica)
    if pratica is None:
        abort(404)
    return pratica


def _versione_approvata(pratica: Pratica):
    """Versione APPROVATO con numero più alto = piano valido."""
    migliore = None
    for versione in pratica.learning_agreements:
        if versione.esito != EsitoDocumento.APPROVATO:
            continue
        if migliore is None or versione.numero_versione > migliore.numero_versione:
            migliore = versione
    return migliore


def _versione_in_attesa(pratica: Pratica):
    """Versione IN_ATTESA con PDF già caricato (tocca al docente)."""
    for versione in pratica.learning_agreements:
        if versione.esito == EsitoDocumento.IN_ATTESA and versione.file_path is not None:
            return versione
    return None


def _corsi_della_versione(versione):
    """Corsi della versione, con equivalenze e corsi interni già in memoria."""
    return db.session.scalars(
        sa.select(CorsoEsterno)
        .where(CorsoEsterno.learning_agreement_id == versione.id)
        .options(selectinload(CorsoEsterno.equivalenze)
                 .selectinload(Equivalenza.corso_interno))
        .order_by(CorsoEsterno.codice)
    ).all()


def _id_pronte_per_chiusura() -> set[int]:
    """Id delle pratiche chiudibili secondo la vista v_pratiche_pronte_per_chiusura.

    La vista chiede: stato IN_RICONOSCIMENTO_ESAMI, Transcript presente,
    nessun esame ancora NON_VALUTATO (zero esami = ok, niente in sospeso).
    """
    righe = db.session.execute(
        sa.text("SELECT pratica_id FROM v_pratiche_pronte_per_chiusura")
    ).all()
    return {riga.pratica_id for riga in righe}


# ============================================================================
# ELENCO PRATICHE
# GET  /ufficio/pratiche  ->  elenco_pratiche
# ============================================================================
@ufficio_bp.route("/pratiche", methods=["GET"])
@login_required
@ruolo_richiesto(Ruolo.UFFICIO)
def elenco_pratiche():
    """Tutte le pratiche, divise per chi deve muoversi.

    Tre gruppi: da fare (ufficio), ferme dal docente (con giorni), le altre.
    Dentro ATTESA_APPROVAZIONE_LA distinguono l'esito della versione:
        IN_ATTESA = docente
        APPROVATO  =  tocca all'ufficio (verifica pre-partenza)
    """
    pratiche = db.session.scalars(
        sa.select(Pratica)
        .options(
            selectinload(Pratica.studente),
            selectinload(Pratica.docente),
            selectinload(Pratica.istituto),
            selectinload(Pratica.learning_agreements),
        )
        .order_by(Pratica.anno_accademico.desc(), Pratica.codice_pratica)
    ).all()

    pronte = _id_pronte_per_chiusura()

    da_fare = []        # tocca all'ufficio
    dal_docente = []    # ferme in attesa del docente
    le_altre = []

    for pratica in pratiche:
        in_attesa = _versione_in_attesa(pratica)

        # 1. tocca all'ufficio(piano approvato)
        if (pratica.stato == StatoPratica.ATTESA_APPROVAZIONE_LA
                and in_attesa is None
                and _versione_approvata(pratica) is not None):
            da_fare.append({"pratica": pratica, "azione": "verifica",
                            "giorni": None})
            continue

        if pratica.id in pronte:
            da_fare.append({"pratica": pratica, "azione": "chiudi",
                            "giorni": None})
            continue

        # 2. ferma dal docente
        if in_attesa is not None:
            giorni = (dt.date.today() - in_attesa.data_caricamento).days
            dal_docente.append({"pratica": pratica, "azione": None,
                                "giorni": giorni})
            continue

        # 3. tutto il resto
        le_altre.append({"pratica": pratica, "azione": None, "giorni": None})

    # Le più ferme in cima: sono quelle da sollecitare.
    dal_docente.sort(key=lambda r: r["giorni"] or 0, reverse=True)

    return render_template("ufficio/elenco.html",
                           da_fare=da_fare,
                           dal_docente=dal_docente,
                           le_altre=le_altre)


# ============================================================================
# VISUALIZZAZIONE PIANO
# GET  /ufficio/pratiche/<id>/la  ->  vedi_la
# ============================================================================
@ufficio_bp.route("/pratiche/<int:id_pratica>/la", methods=["GET"])
@login_required
@ruolo_richiesto(Ruolo.UFFICIO)
def vedi_la(id_pratica: int):
    """Piano in sola lettura, senza pulsanti di decisione.

    Stesso template mappatura: sola_lettura=True, puo_decidere=False.
    """
    pratica = _pratica(id_pratica)

    versione = _versione_approvata(pratica) or _versione_in_attesa(pratica)
    if versione is None:
        flash("Questa pratica non ha ancora nessun piano.", "info")
        return redirect(url_for("pratiche.dettaglio", id_pratica=pratica.id))

    return render_template(
        "pratiche/mappatura.html",
        pratica=pratica,
        versione=versione,
        corsi=_corsi_della_versione(versione),
        corsi_interni=[],
        sola_lettura=True,
        puo_decidere=False,
    )


# ============================================================================
# VERIFICA PRE-PARTENZA
# POST  /ufficio/pratiche/<id>/verifica  ->  verifica_pre_partenza
# ============================================================================
@ufficio_bp.route("/pratiche/<int:id_pratica>/verifica", methods=["POST"])
@login_required
@ruolo_richiesto(Ruolo.UFFICIO)
def verifica_pre_partenza(id_pratica: int):
    """Registra la verifica pre-partenza e passa a PRE_PARTENZA_COMPLETATA.

    Tre campi insieme: chi ha verificato, quando, nuovo stato.
    """
    pratica = _pratica(id_pratica)

    pratica.verificata_da_id = current_user.id
    pratica.pre_partenza_verificata_il = dt.date.today()
    pratica.stato = StatoPratica.PRE_PARTENZA_COMPLETATA

    try:
        db.session.commit()
    except sa.exc.IntegrityError:
        db.session.rollback()
        flash("Dati non coerenti: verifica non registrata.", "danger")
        return redirect(url_for("pratiche.dettaglio", id_pratica=pratica.id))
    except sa.exc.DatabaseError as errore:
        db.session.rollback()
        flash(str(errore.orig).split("\n")[0], "danger")
        return redirect(url_for("pratiche.dettaglio", id_pratica=pratica.id))

    flash(f"Verifica pre-partenza registrata per {pratica.codice_pratica}. "
          f"Lo studente può partire.", "success")
    return redirect(url_for("pratiche.dettaglio", id_pratica=pratica.id))


# ============================================================================
# CHIUSURA PRATICA
# POST  /ufficio/pratiche/<id>/chiudi  ->  chiudi_pratica
# ============================================================================
@ufficio_bp.route("/pratiche/<int:id_pratica>/chiudi", methods=["POST"])
@login_required
@ruolo_richiesto(Ruolo.UFFICIO)
def chiudi_pratica(id_pratica: int):
    """Chiude la pratica (CHIUSA).

    Il pulsante compare se la vista dice che si può: Transcript ok e nessun
    esame ancora da valutare (anche con zero esami).
    """
    pratica = _pratica(id_pratica)

    pratica.chiusa_da_id = current_user.id
    pratica.chiusa_il = dt.date.today()
    pratica.stato = StatoPratica.CHIUSA

    try:
        db.session.commit()
    except sa.exc.IntegrityError:
        db.session.rollback()
        flash("Dati non coerenti: chiusura non registrata.", "danger")
        return redirect(url_for("pratiche.dettaglio", id_pratica=pratica.id))
    except sa.exc.DatabaseError as errore:
        db.session.rollback()
        flash(str(errore.orig).split("\n")[0], "danger")
        return redirect(url_for("pratiche.dettaglio", id_pratica=pratica.id))

    flash(f"Pratica {pratica.codice_pratica} chiusa.", "success")
    return redirect(url_for("pratiche.dettaglio", id_pratica=pratica.id))
