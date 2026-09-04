"""Area del docente referente.

ROTTE
    GET   /docente/pratiche                     elenco, diviso per lavoro
    GET   /docente/pratiche/<id>/la             il piano proposto, in lettura
    POST  /docente/pratiche/<id>/la/approva     approva la versione in attesa
    POST  /docente/pratiche/<id>/la/rifiuta     rifiuta, con motivazione

IL CRITERIO DELL'ELENCO
    Il docente ha un mestiere solo: decidere. Un elenco neutro delle sue
    pratiche non lo aiuta; un elenco che dice "queste aspettano te" si'.
    Da qui i due gruppi, e la colonna con i giorni di attesa.

LA REGOLA DA NON VIOLARE
    Il docente vede SOLO le pratiche di cui e' referente. Il filtro sta
    nella query:
        .where(Pratica.docente_id == current_user.id)
    e ogni rotta che riceve un <id> passa da _pratica_del_docente().

COSA SUCCEDE ALL'APPROVAZIONE
    Solo l'esito della versione diventa APPROVATO. Lo stato della pratica
    NON cambia: resta ATTESA_APPROVAZIONE_LA finche' l'ufficio non fa la
    verifica pre-partenza. Lo dice la tabella transizione_ammessa, che
    per il docente prevede una sola transizione:
        ATTESA_APPROVAZIONE_LA -> APERTA   (rifiuto)

COSA SUCCEDE AL RIFIUTO
    La pratica torna in APERTA e la versione resta li', RIFIUTATA, con la
    sua motivazione. Non si ripristina niente a mano: la versione
    precedentemente approvata non e' mai stata toccata, e resta quella
    valida. E' il requisito 7 della traccia, soddisfatto dal versionamento.
"""

import datetime as dt

import sqlalchemy as sa
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy.orm import selectinload

from app.enums import EsitoDocumento, Ruolo, StatoPratica
from app.extensions import db
from app.models import CorsoEsterno, Equivalenza, LearningAgreement, Pratica
from app.security import ruolo_richiesto

docente_bp = Blueprint("docente", __name__)




# ============================================================================
# UTILITY
# ============================================================================

def _pratica_del_docente(id_pratica: int) -> Pratica:
    """Carica la pratica verificando che chi chiede ne sia il referente.

    Risponde 404 e non 403 anche quando la pratica esiste ma e' di un altro
    docente: un 403 confermerebbe l'esistenza, e provando gli identificatori
    uno per uno si scoprirebbe quante pratiche ci sono nel sistema.
    """
    pratica = db.session.get(Pratica, id_pratica)
    if pratica is None:
        abort(404)
    if pratica.docente_id != current_user.id:
        abort(404)
    return pratica


def _versione_in_attesa(pratica: Pratica):
    """La versione del piano su cui il docente deve decidere, o None.

    Ce n'e' al massimo una per pratica: lo garantisce l'indice unico
    parziale uq_la_una_sola_in_attesa.

    NOTA: e' gemella di _bozza_aperta() in studente.py. Se ne serve una
    terza copia, e' il momento di spostarle in un modulo comune.
    """
    return db.session.scalar(
        sa.select(LearningAgreement)
        .where(LearningAgreement.pratica_id == pratica.id)
        .where(LearningAgreement.esito == EsitoDocumento.IN_ATTESA)
        .where(LearningAgreement.file_path.is_not(None)) # FIXME  per sistemare che il prof riesce a approvare un la senza doc
    )

def _proposta_da_valutare(pratica):
    """La versione che aspetta la TUA decisione: in attesa e gia' firmata.

    Una versione in attesa senza file_path e' una bozza che lo studente sta
    ancora scrivendo: non riguarda il docente.
    """
    for versione in pratica.learning_agreements:

        if versione.esito == EsitoDocumento.IN_ATTESA and versione.file_path:
            return versione
    return None

def _corsi_della_versione(versione):
    """I corsi esteri della versione, con le equivalenze gia' caricate.

    Due selectinload in catena perche' il template attraversa due
    relazioni: dal corso alle sue equivalenze, e da ogni equivalenza al
    corso interno.
    """
    return db.session.scalars(
        sa.select(CorsoEsterno)
        .where(CorsoEsterno.learning_agreement_id == versione.id)
        .options(selectinload(CorsoEsterno.equivalenze)
                 .selectinload(Equivalenza.corso_interno))
        .order_by(CorsoEsterno.codice)
    ).all()


def _da_quando_aspetta(pratica: Pratica):
    """Da quanti giorni la pratica e' ferma in attesa del docente.

    None se non sta aspettando niente. La data di partenza dipende da cosa
    si sta aspettando: la proposta del piano, oppure il rientro dello
    studente.
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


# ============================================================================
# ELENCO
# ============================================================================

@docente_bp.route("/pratiche", methods=["GET"])
@login_required
@ruolo_richiesto(Ruolo.DOCENTE)
def elenco_pratiche():
    """Le pratiche di cui il docente e' referente, divise per lavoro.

    Una query sola: la divisione in due gruppi si fa in Python, perche'
    andare due volte al database per la stessa tabella non serve a niente.
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

    # Ogni riga porta con se' i giorni di attesa, calcolati qui e non nel
    # template: Jinja disegna, la rotta decide.
    da_decidere = []
    le_altre = []

    for pratica in pratiche:
        proposta = _proposta_da_valutare(pratica)
        tocca_a_me = (proposta is not None
                      or pratica.stato == StatoPratica.IN_RICONOSCIMENTO_ESAMI)

        giorni = None
        if proposta is not None:
            giorni = (dt.date.today() - proposta.data_caricamento).days

        riga = {"pratica": pratica, "giorni": giorni}
        (da_decidere if tocca_a_me else le_altre).append(riga)

    # Le piu' ferme in cima: sono quelle che rischiano di essere dimenticate.
    da_decidere.sort(key=lambda r: r["giorni"] or 0, reverse=True)

    return render_template("docente/elenco.html",
                           da_decidere=da_decidere, le_altre=le_altre)


# ============================================================================
# VALUTAZIONE DEL LEARNING AGREEMENT
# ============================================================================

@docente_bp.route("/pratiche/<int:id_pratica>/la", methods=["GET"])
@login_required
@ruolo_richiesto(Ruolo.DOCENTE)
def valuta_la(id_pratica: int):
    """Il piano proposto, con i comandi di approvazione.

    Riusa lo stesso template dello studente: cambia solo il flag
    sola_lettura, che nasconde i comandi di modifica e mostra al loro
    posto il documento firmato e i due pulsanti della decisione.
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


@docente_bp.route("/pratiche/<int:id_pratica>/la/approva", methods=["POST"])
@login_required
@ruolo_richiesto(Ruolo.DOCENTE)
def approva_la(id_pratica: int):
    """Approva la versione in attesa.

    Lo stato della pratica NON cambia: resta ATTESA_APPROVAZIONE_LA finche'
    l'ufficio non registra la verifica pre-partenza. Quindi qui non scatta
    nessun trigger sulle transizioni.
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


@docente_bp.route("/pratiche/<int:id_pratica>/la/rifiuta", methods=["POST"])
@login_required
@ruolo_richiesto(Ruolo.DOCENTE)
def rifiuta_la(id_pratica: int):
    """Rifiuta la versione in attesa e riporta la pratica in APERTA.

    IL RIPRISTINO NON ESISTE, ED E' IL PUNTO
        Il requisito 7 chiede che al rifiuto "sia ripristinata
        l'associazione degli esami precedentemente concordata". Qui non si
        ripristina niente: la versione precedente non e' mai stata toccata,
        e learning_agreement_corrente continua a restituirla.
        Lo studente che riapre la mappatura non trova nessuna bozza aperta,
        quindi ne crea una nuova con il numero successivo.

    L'ORDINE DELLE SCRITTURE
        Il trigger sulla transizione controlla i dati della versione,
        quindi la versione va scritta PRIMA che l'UPDATE su pratica faccia
        scattare il controllo. Da qui il flush().
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