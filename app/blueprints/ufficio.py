"""Area dell'ufficio Overseas.

ROTTE
    GET   /ufficio/pratiche                     elenco di TUTTE le pratiche
    GET   /ufficio/pratiche/<id>/la             il piano approvato, in lettura
    POST  /ufficio/pratiche/<id>/verifica       registra la verifica pre-partenza
    POST  /ufficio/pratiche/<id>/chiudi         chiude la pratica

COSA FA L'UFFICIO, E COSA NON FA
    Verifica che la pratica sia completa e la fa avanzare; chiude quando il
    percorso e' finito. NON entra nel merito didattico: se un esame estero
    valga davvero un esame di Ca' Foscari lo decide il docente referente.
    Per questo l'ufficio vede il piano ma non ha nessun pulsante per
    approvarlo.

I DUE STATI DENTRO ATTESA_APPROVAZIONE_LA
    La pratica resta in questo stato sia mentre il docente deve decidere,
    sia dopo che ha approvato. A distinguerli e' l'esito della versione:

        esiste una versione IN_ATTESA   -> tocca al docente
        esiste una versione APPROVATO   -> tocca all'ufficio

    L'elenco usa questa differenza per dividere le righe, ed e' il motivo
    per cui la colonna dei giorni di attesa ha senso anche qui: sono le
    pratiche che il docente sta trattenendo.

LE DUE TRANSIZIONI DELL'UFFICIO
    ATTESA_APPROVAZIONE_LA  -> PRE_PARTENZA_COMPLETATA
    IN_RICONOSCIMENTO_ESAMI -> CHIUSA
    Sono le uniche due righe di transizione_ammessa con ruolo UFFICIO.
    Le precondizioni le verifica il trigger, non questo file.
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

    L'ufficio le vede tutte, quindi non c'e' nessun controllo di
    appartenenza da fare: basta gestire l'id inventato. Il controllo di
    ruolo lo ha gia' fatto @ruolo_richiesto sulla rotta.
    """
    pratica = db.session.get(Pratica, id_pratica)
    if pratica is None:
        abort(404)
    return pratica


def _versione_approvata(pratica: Pratica):
    """La versione approvata con numero piu' alto, cioe' il piano valido."""
    migliore = None
    for versione in pratica.learning_agreements:
        if versione.esito != EsitoDocumento.APPROVATO:
            continue
        if migliore is None or versione.numero_versione > migliore.numero_versione:
            migliore = versione
    return migliore


def _versione_in_attesa(pratica: Pratica):
    """La versione su cui il docente non ha ancora deciso, o None."""
    for versione in pratica.learning_agreements:
        # AGGIUNTO IL CONTROLLO SUL FILE_PATH
        if versione.esito == EsitoDocumento.IN_ATTESA and versione.file_path is not None:
            return versione
    return None


def _corsi_della_versione(versione):
    """I corsi della versione, con equivalenze e corsi interni gia' caricati."""
    return db.session.scalars(
        sa.select(CorsoEsterno)
        .where(CorsoEsterno.learning_agreement_id == versione.id)
        .options(selectinload(CorsoEsterno.equivalenze)
                 .selectinload(Equivalenza.corso_interno))
        .order_by(CorsoEsterno.codice)
    ).all()


def _id_pronte_per_chiusura() -> set[int]:
    """Gli id delle pratiche che si possono chiudere.

    Arriva dalla vista SQL v_pratiche_pronte_per_chiusura, che incrocia tre
    condizioni: stato IN_RICONOSCIMENTO_ESAMI, nessun esame ancora da
    valutare, Transcript caricato. Rifarlo in Python significherebbe
    riscrivere qui una regola che nel database e' gia' espressa e verificata.
    """
    righe = db.session.execute(
        sa.text("SELECT pratica_id FROM v_pratiche_pronte_per_chiusura")
    ).all()
    return {riga.pratica_id for riga in righe}


# ============================================================================
# ELENCO
# ============================================================================

@ufficio_bp.route("/pratiche", methods=["GET"])
@login_required
@ruolo_richiesto(Ruolo.UFFICIO)
def elenco_pratiche():
    """Tutte le pratiche, divise per chi deve muoversi.

    Tre gruppi:
        1. richiedono un intervento dell'ufficio
        2. sono ferme dal docente  (con i giorni di attesa: e' il sollecito)
        3. tutte le altre
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
    dal_docente = []    # ferme in attesa di una decisione del docente
    le_altre = []

    for pratica in pratiche:
        in_attesa = _versione_in_attesa(pratica)

        # --- 1. tocca all'ufficio? ---
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

        # --- 2. ferma dal docente? ---
        if in_attesa is not None:
            giorni = (dt.date.today() - in_attesa.data_caricamento).days
            dal_docente.append({"pratica": pratica, "azione": None,
                                "giorni": giorni})
            continue

        # --- 3. tutto il resto ---
        le_altre.append({"pratica": pratica, "azione": None, "giorni": None})

    # Le piu' ferme in cima: sono quelle da sollecitare.
    dal_docente.sort(key=lambda r: r["giorni"] or 0, reverse=True)

    return render_template("ufficio/elenco.html",
                           da_fare=da_fare,
                           dal_docente=dal_docente,
                           le_altre=le_altre)


# ============================================================================
# VISUALIZZAZIONE DEL PIANO
# ============================================================================

@ufficio_bp.route("/pratiche/<int:id_pratica>/la", methods=["GET"])
@login_required
@ruolo_richiesto(Ruolo.UFFICIO)
def vedi_la(id_pratica: int):
    """Il piano approvato, in sola lettura e senza comandi.

    Riusa il template della mappatura con sola_lettura=True e
    puo_decidere=False: l'ufficio guarda per verificare la completezza,
    non per giudicare il merito.
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
# AZIONI
# ============================================================================

@ufficio_bp.route("/pratiche/<int:id_pratica>/verifica", methods=["POST"])
@login_required
@ruolo_richiesto(Ruolo.UFFICIO)
def verifica_pre_partenza(id_pratica: int):
    """Registra che la fase pre-partenza e' completa.

    Le tre colonne vanno riempite insieme: chi ha verificato, quando, e il
    nuovo stato. Il vincolo ck_pratica_verifica_coerente impone che
    verificata_da_id e pre_partenza_verificata_il siano entrambe piene o
    entrambe vuote, e il trigger sulla transizione controlla che ci siano
    davvero le condizioni per avanzare.
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


@ufficio_bp.route("/pratiche/<int:id_pratica>/chiudi", methods=["POST"])
@login_required
@ruolo_richiesto(Ruolo.UFFICIO)
def chiudi_pratica(id_pratica: int):
    """Chiude la pratica.

    NON E' ANCORA PROVABILE: serve una pratica in IN_RICONOSCIMENTO_ESAMI
    con il Transcript caricato e tutti gli esami valutati, cioe' le fasi
    che non sono ancora state scritte. La lascio qui perche' e' identica
    alla verifica e il trigger fa lo stesso lavoro.

    Dopo la chiusura trg_pratica_immutabile rende la riga di sola lettura
    per tutti, ed e' quello che rende la chiusura un atto definitivo.
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