"""
DESCRIZIONE
    Area del docente referente: decidere sul Learning Agreement e sui voti.
    Vede solo le pratiche di cui è referente (filtro nella query, non nel template).

MAPPA
    GET  /docente/pratiche                               elenco_pratiche           elenco, diviso per lavoro
    GET  /docente/pratiche/<id>/la                       valuta_la                 piano proposto (lettura)
    POST /docente/pratiche/<id>/la/approva               approva_la                approva la versione
    POST /docente/pratiche/<id>/la/rifiuta               rifiuta_la                rifiuta con motivazione
    GET  /docente/pratiche/<id>/esami                    valuta_esami              pagina riconoscimento
    POST /docente/pratiche/<id>/esami/<id>/valuta        salva_valutazione_esame  esito voto (JSON)
"""

import datetime as dt

import sqlalchemy as sa
from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy.orm import selectinload

from app.enums import EsitoDocumento, Ruolo, StatoPratica
from app.extensions import db
from app.models import CorsoEsterno, Equivalenza, LearningAgreement, Pratica, Esame
from app.security import ruolo_richiesto

docente_bp = Blueprint("docente", __name__)


# ============================================================================
# UTILITY
# ============================================================================

def _pratica_del_docente(id_pratica: int) -> Pratica:
    """Carica la pratica solo se chi chiede ne è il referente.

    404 anche se esiste ma è di un altro docente: un 403 confermerebbe
    che la pratica c'è.
    """
    pratica = db.session.get(Pratica, id_pratica)
    if pratica is None:
        abort(404)
    if pratica.docente_id != current_user.id:
        abort(404)
    return pratica


def _versione_in_attesa(pratica: Pratica):
    """La versione su cui il docente deve decidere, o None.

    Al massimo una per pratica (indice parziale uq_la_una_sola_in_attesa).
    file_path obbligatorio: senza PDF è ancora una bozza dello studente.

    """
    return db.session.scalar(
        sa.select(LearningAgreement)
        .where(LearningAgreement.pratica_id == pratica.id)
        .where(LearningAgreement.esito == EsitoDocumento.IN_ATTESA)
        .where(LearningAgreement.file_path.is_not(None)) # senza file non si decide
    )

def _proposta_da_valutare(pratica):
    """Versione in attesa e già firmata (PDF caricato).

    IN_ATTESA senza file_path = bozza ancora in scrittura: non riguarda il docente.
    """
    for versione in pratica.learning_agreements:

        if versione.esito == EsitoDocumento.IN_ATTESA and versione.file_path:
            return versione
    return None

def _corsi_della_versione(versione):
    """Corsi esteri della versione, con equivalenze e corsi interni già caricati.

    Due selectinload in catena: il template legge corso → equivalenza → corso interno.
    """
    return db.session.scalars(
        sa.select(CorsoEsterno)
        .where(CorsoEsterno.learning_agreement_id == versione.id)
        .options(selectinload(CorsoEsterno.equivalenze)
                 .selectinload(Equivalenza.corso_interno))
        .order_by(CorsoEsterno.codice)
    ).all()


def _da_quando_aspetta(pratica: Pratica):
    """Giorni di attesa per il docente, o None se non sta aspettando niente.

    Conta da data_caricamento del LA (attesa piano) oppure da data_fine
    (riconoscimento esami dopo il rientro).
    """
    dal = None

    if pratica.stato == StatoPratica.ATTESA_APPROVAZIONE_LA:
        for versione in pratica.learning_agreements:
            if versione.esito == EsitoDocumento.IN_ATTESA:
                dal = versione.data_caricamento
                break
    elif pratica.stato == StatoPratica.IN_RICONOSCIMENTO_ESAMI:
        dal = pratica.data_fine_effettiva

    if dal is None:
        return None
    return (dt.date.today() - dal).days


def _ci_sono_esami_da_valutare(pratica):
    """True se ci sono voti caricati ancora NON_VALUTATO sul piano approvato."""
    if pratica.stato != StatoPratica.IN_RICONOSCIMENTO_ESAMI:
        return False

    # count(*) sugli esami del piano APPROVATO ancora senza decisione
    n = db.session.scalar(
        sa.select(sa.func.count(Esame.id))
        .join(CorsoEsterno)
        .join(LearningAgreement)
        .where(LearningAgreement.pratica_id == pratica.id)
        .where(LearningAgreement.esito == EsitoDocumento.APPROVATO)
        .where(Esame.esito_riconoscimento == 'NON_VALUTATO')
    )
    return (n or 0) > 0

# ============================================================================
# ELENCO PRATICHE
# GET  /docente/pratiche  ->  elenco_pratiche
# ============================================================================
@docente_bp.route("/pratiche", methods=["GET"])
@login_required
@ruolo_richiesto(Ruolo.DOCENTE)
def elenco_pratiche():
    """Le pratiche di cui è referente, divise in «da decidere» e «le altre».
    """
    pratiche = db.session.scalars(
        sa.select(Pratica)
        .where(Pratica.docente_id == current_user.id)
        .options(
            selectinload(Pratica.studente),
            selectinload(Pratica.istituto),
            selectinload(Pratica.learning_agreements),
        )
        .order_by(Pratica.anno_accademico.desc(), Pratica.codice_pratica)
    ).all()

    # Giorni di attesa calcolati qui
    da_decidere = []
    le_altre = []

    for pratica in pratiche:
        proposta = _proposta_da_valutare(pratica)
        tocca_a_me = (proposta is not None
                      or _ci_sono_esami_da_valutare(pratica))

        giorni = None
        if proposta is not None:
            giorni = (dt.date.today() - proposta.data_caricamento).days

        riga = {"pratica": pratica, "giorni": giorni}
        (da_decidere if tocca_a_me else le_altre).append(riga)

    # Le più ferme in cima: sono quelle che rischiano di essere dimenticate.
    da_decidere.sort(key=lambda r: r["giorni"] or 0, reverse=True)

    return render_template("docente/elenco.html",
                           da_decidere=da_decidere, le_altre=le_altre)


# ============================================================================
# VALUTAZIONE LEARNING AGREEMENT
# GET  /docente/pratiche/<id>/la  ->  valuta_la
# ============================================================================
@docente_bp.route("/pratiche/<int:id_pratica>/la", methods=["GET"])
@login_required
@ruolo_richiesto(Ruolo.DOCENTE)
def valuta_la(id_pratica: int):
    """Piano proposto in sola lettura, con i pulsanti di decisione.

    Stesso template dello studente: sola_lettura nasconde le modifiche,
    puo_decidere mostra documento firmato + approva/rifiuta.
    """
    pratica = _pratica_del_docente(id_pratica)
    versione = _versione_in_attesa(pratica)
    if versione is None:
        flash("Non c'è nessuna proposta in attesa su questa pratica.", "info")
        return redirect(url_for("pratiche.dettaglio", id_pratica=pratica.id))

    return render_template(
        "pratiche/mappatura.html",
        pratica=pratica,
        versione=versione,
        corsi=_corsi_della_versione(versione),
        corsi_interni=[],        # il docente non aggiunge righe
        sola_lettura=True,
        puo_decidere=True
    )


# ============================================================================
# APPROVA LA
# POST  /docente/pratiche/<id>/la/approva  ->  approva_la
# ============================================================================
@docente_bp.route("/pratiche/<int:id_pratica>/la/approva", methods=["POST"])
@login_required
@ruolo_richiesto(Ruolo.DOCENTE)
def approva_la(id_pratica: int):
    """Approva la versione in attesa.

    Cambia solo l'esito della versione (APPROVATO). Lo stato della pratica
    resta ATTESA_APPROVAZIONE_LA finché l'ufficio non fa la verifica
    pre-partenza → qui non scatta nessun trigger sulle transizioni.
    """
    pratica = _pratica_del_docente(id_pratica)
    versione = _versione_in_attesa(pratica)
    if versione is None:
        abort(404)

    versione.esito = EsitoDocumento.APPROVATO
    versione.data_decisione = dt.date.today()
    versione.motivazione = request.form.get("motivazione", "").strip() or None

    try:
        db.session.commit()
    except sa.exc.DatabaseError as errore:
        db.session.rollback()
        flash(str(errore.orig).split("\n")[0], "danger")
        return redirect(url_for("pratiche.dettaglio", id_pratica=pratica.id))

    flash(f"Learning Agreement versione {versione.numero_versione} approvato.",
          "success")
    return redirect(url_for("pratiche.dettaglio", id_pratica=pratica.id))


# ============================================================================
# RIFIUTA LA
# POST  /docente/pratiche/<id>/la/rifiuta  ->  rifiuta_la
# ============================================================================
@docente_bp.route("/pratiche/<int:id_pratica>/la/rifiuta", methods=["POST"])
@login_required
@ruolo_richiesto(Ruolo.DOCENTE)
def rifiuta_la(id_pratica: int):
    """Rifiuta la versione e riporta la pratica in APERTA (se era in attesa).

    Non si ripristina nulla a mano: la versione approvata prima
    non è mai stata toccata, learning_agreement_corrente la restituisce ancora.

    Ordine: prima si scrive la versione (flush), poi lo stato della pratica.
    """
    pratica = _pratica_del_docente(id_pratica)
    versione = _versione_in_attesa(pratica)
    if versione is None:
        abort(404)

    motivazione = request.form.get("motivazione", "").strip()
    if not motivazione:
        flash("Per rifiutare serve una motivazione.", "danger")
        return redirect(url_for("docente.valuta_la", id_pratica=pratica.id))

    versione.esito = EsitoDocumento.RIFIUTATO
    versione.motivazione = motivazione
    versione.data_decisione = dt.date.today()
    db.session.flush()

    # Solo se eravamo in attesa del primo piano: in mobilità lo stato non torna APERTA
    if pratica.stato == StatoPratica.ATTESA_APPROVAZIONE_LA:
        pratica.stato = StatoPratica.APERTA

    try:
        db.session.commit()
    except sa.exc.IntegrityError:
        db.session.rollback()
        flash("Non è stato possibile registrare il rifiuto.", "danger")
        return redirect(url_for("docente.valuta_la", id_pratica=pratica.id))
    except sa.exc.DatabaseError as errore:
        db.session.rollback()
        flash(str(errore.orig).split("\n")[0], "danger")
        return redirect(url_for("docente.valuta_la", id_pratica=pratica.id))

    flash("Learning Agreement rifiutato. Lo studente potrà proporne "
          "una nuova versione.", "warning")
    return redirect(url_for("pratiche.dettaglio", id_pratica=pratica.id))


# ============================================================================
# UTILITY ESAMI
# ============================================================================
def _versione_approvata(pratica: Pratica):
    """L'ultima versione APPROVATO (numero più alto) = piano valido."""
    migliore = None
    for versione in pratica.learning_agreements:
        if versione.esito == EsitoDocumento.APPROVATO:
            if migliore is None or versione.numero_versione > migliore.numero_versione:
                migliore = versione
    return migliore

# ============================================================================
# VALUTAZIONE ESAMI
# GET  /docente/pratiche/<id>/esami  ->  valuta_esami
# ============================================================================
@docente_bp.route("/pratiche/<int:id_pratica>/esami", methods=["GET"])
@login_required
@ruolo_richiesto(Ruolo.DOCENTE)
def valuta_esami(id_pratica: int):
    """Pagina di riconoscimento voti (stesso dello studente, valuta=True)."""
    pratica = _pratica_del_docente(id_pratica)

    if pratica.stato != StatoPratica.IN_RICONOSCIMENTO_ESAMI:
        flash("La pratica non è nella fase di riconoscimento esami.", "warning")
        return redirect(url_for("pratiche.dettaglio", id_pratica=pratica.id))

    approvata = _versione_approvata(pratica)
    corsi = _corsi_della_versione(approvata) if approvata else []

    # id_corso → esame: nel template si vede subito se c'è un voto da giudicare
    esami = {c.id: c.esame for c in corsi if c.esame}

    return render_template("pratiche/esami.html", pratica=pratica, corsi=corsi, esami=esami, valuta=True)

# ============================================================================
# SALVA VALUTAZIONE ESAME
# POST  /docente/pratiche/<id>/esami/<id>/valuta  ->  salva_valutazione_esame
# ============================================================================
@docente_bp.route("/pratiche/<int:id_pratica>/esami/<int:id_corso>/valuta", methods=["POST"])
@login_required
@ruolo_richiesto(Ruolo.DOCENTE)
def salva_valutazione_esame(id_pratica: int, id_corso: int):
    """Registra ACCETTATO/RIFIUTATO su un esame. Risposta JSON (AJAX)."""
    pratica = _pratica_del_docente(id_pratica)

    if pratica.stato != StatoPratica.IN_RICONOSCIMENTO_ESAMI:
        return jsonify(ok=False, errore="La pratica non è in fase di riconoscimento."), 403

    corso = db.session.get(CorsoEsterno, id_corso)
    if not corso or corso.learning_agreement.pratica_id != pratica.id or not corso.esame:
        return jsonify(ok=False, errore="Esame da valutare non trovato."), 404

    esito = request.form.get("esito")
    if esito not in ['ACCETTATO', 'RIFIUTATO']:
        return jsonify(ok=False, errore="Esito non valido."), 400

    corso.esame.esito_riconoscimento = esito
    corso.esame.data_riconoscimento = dt.date.today()

    try:
        db.session.commit()
        return jsonify(ok=True)
    except sa.exc.DatabaseError:
        db.session.rollback()
        return jsonify(ok=False, errore="Errore nel salvataggio della valutazione."), 400
