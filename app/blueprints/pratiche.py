"""Dettaglio della pratica: la pagina condivisa dai tre ruoli.

PERCHE' UN BLUEPRINT SUO
    La pagina di dettaglio serve a tutti e tre i ruoli: cambiano solo i
    comandi disponibili, decisi dai controlli in security.py. Metterla sotto
    /studente/ costringerebbe un docente a navigare in un indirizzo che dice
    il contrario di quello che sta facendo.

    E' anche il centro dell'applicazione: da qui si raggiungono tutte le
    altre azioni, ed e' la schermata che si vede di piu' nel video.

ROTTE
    GET  /pratiche/<id>              il dettaglio
    GET  /pratiche/<id>/versioni     le versioni vecchie, come frammento HTML
    GET  /pratiche/la/<id>/documento download del Learning Agreement firmato

PERCHE' LE VERSIONI VECCHIE STANNO IN UNA ROTTA A PARTE
    Il dettaglio carica solo la versione che conta adesso, con i suoi corsi
    e le loro equivalenze. Le versioni precedenti sono storia: interessano
    di rado, e caricare tutti i loro corsi a ogni apertura della pagina
    significherebbe pagare sempre per un'informazione che quasi nessuno
    guarda. La rotta le restituisce come pezzo di HTML gia' disegnato, che
    lo script infila nella pagina al primo clic.
"""

import datetime as dt

import sqlalchemy as sa
from flask import Blueprint, abort, flash, redirect, render_template, send_file, url_for
from flask_login import current_user, login_required
from sqlalchemy.orm import selectinload

from app.documenti import percorso_documento
from app.enums import EsitoDocumento, Ruolo, StatoPratica
from app.extensions import db
from app.models import CorsoEsterno, Equivalenza, Esame, LearningAgreement, Pratica
from app.security import esigi_accesso , ruolo_richiesto

pratiche_bp = Blueprint("pratiche", __name__, url_prefix="/pratiche")


# ============================================================================
# UTILITY
# ============================================================================

def _carica_pratica(id_pratica: int) -> Pratica:
    """Le tre righe da ripetere ovunque: carica, gestisci il 404, verifica.

    esigi_accesso risponde 404 e non 403 anche quando la pratica esiste ma
    non e' tua: un 403 confermerebbe l'esistenza, e provando i numeri uno
    per uno si scoprirebbe quante pratiche ci sono nel sistema.
    """
    pratica = db.session.get(Pratica, id_pratica)
    if pratica is None:
        abort(404)
    esigi_accesso(pratica)
    return pratica


def _versione_in_attesa(pratica: Pratica):
    """La versione su cui il docente non ha ancora deciso, o None."""
    for versione in pratica.learning_agreements:
        if versione.esito == EsitoDocumento.IN_ATTESA:
            return versione
    return None


def _versione_approvata(pratica: Pratica):
    """La versione approvata con numero piu' alto: il piano che vale."""
    migliore = None
    for versione in pratica.learning_agreements:
        if versione.esito != EsitoDocumento.APPROVATO:
            continue
        if migliore is None or versione.numero_versione > migliore.numero_versione:
            migliore = versione
    return migliore


def _corsi_della_versione(versione):
    """I corsi della versione, con equivalenze e corsi interni gia' caricati.

    Due selectinload in catena perche' il template attraversa due relazioni:
    dal corso alle sue equivalenze, e da ogni equivalenza al corso interno.
    Senza, una query per ogni riga: e' il problema N+1.
    """
    if versione is None:
        return []
    return db.session.scalars(
        sa.select(CorsoEsterno)
        .where(CorsoEsterno.learning_agreement_id == versione.id)
        .options(selectinload(CorsoEsterno.equivalenze)
                 .selectinload(Equivalenza.corso_interno))
        .order_by(CorsoEsterno.codice)
    ).all()


def _esami_da_valutare(pratica: Pratica) -> int:
    """Voti già inseriti e ancora senza decisione del docente."""
    n = db.session.scalar(
        sa.select(sa.func.count(Esame.id))
        .join(CorsoEsterno)
        .join(LearningAgreement)
        .where(LearningAgreement.pratica_id == pratica.id)
        .where(LearningAgreement.esito == EsitoDocumento.APPROVATO)
        .where(Esame.esito_riconoscimento == "NON_VALUTATO")
    )
    return n or 0


def _restano_voti_da_inserire(pratica: Pratica) -> bool:
    """True se c'è un corso senza voto, o un voto ancora non deciso dal docente."""
    versione = _versione_approvata(pratica)
    if versione is None:
        return False
    n = db.session.scalar(
        sa.select(sa.func.count(CorsoEsterno.id))
        .outerjoin(Esame)
        .where(CorsoEsterno.learning_agreement_id == versione.id)
        .where(sa.or_(
            Esame.id.is_(None),
            Esame.esito_riconoscimento == "NON_VALUTATO",
        ))
    )
    return (n or 0) > 0


def _cosa_fare(pratica: Pratica):
    """Chi deve muoversi adesso, e cosa deve fare.

    Restituisce (tocca_a_me, testo).

    STA QUI E NON NEL TEMPLATE
        Sono sei stati per tre ruoli: diciotto casi. Scritti come catena di
        {% if %} in Jinja diventano illeggibili, e la logica di processo non
        e' compito del template. Qui si legge, si corregge in un posto solo,
        e domani si puo' anche provare con un test.
    """
    ruolo = current_user.ruolo
    sono_lo_studente = pratica.studente_id == current_user.id
    sono_il_docente = pratica.docente_id == current_user.id
    stato = pratica.stato

    if stato == StatoPratica.APERTA:
        if sono_lo_studente:
            return True, ("Componi il Learning Agreement indicando gli esami "
                          "che seguirai all'estero e le loro equivalenze, poi "
                          "invialo al docente referente.")
        return False, (f"{pratica.studente.nome_completo} sta compilando il "
                       f"Learning Agreement.")

    if stato == StatoPratica.ATTESA_APPROVAZIONE_LA:
        if _versione_in_attesa(pratica) is not None:
            if sono_il_docente:
                return True, ("Lo studente ha inviato il piano firmato: "
                              "approvalo, oppure rifiutalo indicando il motivo.")
            if sono_lo_studente:
                return False, (f"Il piano è in valutazione presso "
                               f"{pratica.docente.nome_completo}.")
            return False, (f"In attesa della valutazione di "
                           f"{pratica.docente.nome_completo}.")
        # Nessuna versione in attesa ma lo stato non e' avanzato: il docente
        # ha approvato e la palla passa all'ufficio.
        if ruolo == Ruolo.UFFICIO:
            return True, ("Il docente ha approvato il piano: registra la "
                          "verifica pre-partenza per far partire lo studente.")
        return False, ("Piano approvato dal docente. L'ufficio Overseas deve "
                       "registrare la verifica pre-partenza.")

    if stato == StatoPratica.PRE_PARTENZA_COMPLETATA:
        if sono_lo_studente:
            return True, ("Documentazione verificata: puoi partire. Al tuo "
                          "arrivo registra la data di inizio della mobilità.")
        return False, (f"{pratica.studente.nome_completo} può partire e deve "
                       f"registrare la data di inizio.")

    if stato == StatoPratica.MOBILITA_IN_CORSO:
        # Una versione ancora in attesa congela il piano: il rientro
        # si registra solo quando non ne resta nessuna.
        in_attesa = _versione_in_attesa(pratica)
        if sono_lo_studente:
            if in_attesa is not None and in_attesa.file_path:
                return False, ("Una modifica del piano è in attesa del docente. "
                               "Il rientro si registra dopo la sua decisione.")
            if in_attesa is not None:
                return True, ("Hai una bozza del piano aperta: inviala o "
                              "scartala prima di registrare il rientro.")
            return True, ("Al rientro registra la data di fine e carica il "
                          "Transcript of Records rilasciato dall'ateneo "
                          "ospitante. Durante la mobilità puoi proporre una "
                          "modifica al piano.")
        if sono_il_docente and in_attesa is not None and in_attesa.file_path:
            return True, ("Lo studente ha proposto una modifica al piano: "
                          "approvala, oppure rifiutala indicando il motivo.")
        return False, "Mobilità in corso. Nessun intervento richiesto."

    if stato == StatoPratica.IN_RICONOSCIMENTO_ESAMI:
        if sono_lo_studente:
            if not pratica.transcript:
                return True, ("Rientro registrato. Carica il Transcript of Records per poter procedere con i voti.")
            if _restano_voti_da_inserire(pratica):
                return True, (
                    "Inserisci voto e data di superamento per ciascun esame sostenuto, poi il docente li valuterà.")
            return False, ("I voti inseriti sono stati valutati dal docente. Si attende la chiusura dell'ufficio.")
        if sono_il_docente:
            if not pratica.transcript:
                return False, ("In attesa che lo studente carichi il Transcript of Records.")
            if _esami_da_valutare(pratica) > 0:
                return True, ("Valuta gli esami sostenuti e il Transcript caricato.")
            return False, ("Hai valutato tutti i voti inseriti. La chiusura spetta all'ufficio.")
        return False, ("In attesa del riconoscimento degli esami.")

    if stato == StatoPratica.CHIUSA:
        return False, ("Pratica chiusa. Non è più modificabile da nessuno: "
                       "lo impedisce un vincolo del database.")

    return False, ""


# ============================================================================
# DETTAGLIO
# ============================================================================

@pratiche_bp.route("/<int:id_pratica>")
@login_required
def dettaglio(id_pratica: int):
    """Mostra una pratica, a chi ha diritto di vederla.

    QUALE VERSIONE DEL PIANO SI MOSTRA
        mostriamo sempre l'ultima in modifica se esiste, e quella approvata se esista, dobbiamo recuperare entrambe
    """
    pratica = _carica_pratica(id_pratica)

    in_attesa = _versione_in_attesa(pratica)
    approvata = _versione_approvata(pratica)
    # versione = in_attesa or approvata

    tocca_a_me, avviso = _cosa_fare(pratica)

    # Calcoliamo quante versioni vanno nello storico (tutte tranne quelle mostrate sopra)
    mostrate = 0
    if in_attesa: mostrate += 1
    if approvata: mostrate += 1
    altre = len(pratica.learning_agreements) - mostrate

    return render_template(
        "pratiche/dettaglio.html",
        pratica=pratica,
        approvata=approvata,  # <-- PASSIAMO IL PIANO OPERATIVO
        corsi_approvata=_corsi_della_versione(approvata),
        in_attesa=in_attesa,  # <-- PASSIAMO LA BOZZA/PROPOSTA
        corsi_in_attesa=_corsi_della_versione(in_attesa),
        altre_versioni=altre,
        tocca_a_me=tocca_a_me,
        avviso=avviso,
        oggi=dt.date.today(),
    )


@pratiche_bp.route("/<int:id_pratica>/esami")
@login_required
def consulta_esami(id_pratica: int):
    """Gli esami del piano, in sola lettura, per studente, docente e ufficio.

    E' la stessa pagina usata per inserire i voti e per valutarli.
    sola_lettura dice alla macro di non disegnare i comandi: qui nessuno
    scrive, si guarda solo l'esito.
    """
    pratica = _carica_pratica(id_pratica)
    if pratica.stato not in (
        StatoPratica.IN_RICONOSCIMENTO_ESAMI,
        StatoPratica.CHIUSA,
    ):
        flash("Gli esami non sono ancora disponibili.", "info")
        return redirect(url_for("pratiche.dettaglio", id_pratica=pratica.id))

    approvata = _versione_approvata(pratica)
    corsi = _corsi_della_versione(approvata) if approvata else []
    esami = {c.id: c.esame for c in corsi if c.esame}

    return render_template(
        "pratiche/esami.html",
        pratica=pratica,
        corsi=corsi,
        esami=esami,
        valuta=False,
        sola_lettura=True,
    )


@pratiche_bp.route("/<int:id_pratica>/versioni")
@login_required
def versioni_vecchie(id_pratica: int):
    """Le versioni precedenti, come frammento di HTML gia' disegnato.

    Non restituisce JSON: restituisce il pezzo di pagina. Cosi' la logica di
    presentazione resta in un template invece di essere riscritta in
    JavaScript, e lo script deve solo infilare il testo nel contenitore.
    """
    pratica = _carica_pratica(id_pratica)
    in_attesa = _versione_in_attesa(pratica)
    approvata = _versione_approvata(pratica)

    # ID delle versioni già disegnate in alto (da NON rimettere nello storico)
    id_esclusi = [v.id for v in (in_attesa, approvata) if v is not None]

    versioni = db.session.scalars(
        sa.select(LearningAgreement)
        .where(LearningAgreement.pratica_id == pratica.id)
        .options(selectinload(LearningAgreement.corsi_esterni)
                 .selectinload(CorsoEsterno.equivalenze)
                 .selectinload(Equivalenza.corso_interno))
        .order_by(LearningAgreement.numero_versione.desc())
    ).all()

    return render_template(
        "pratiche/_versioni_vecchie.html",
        pratica=pratica,
        versioni=[v for v in versioni if v.id not in id_esclusi],
    )


# ============================================================================
# DOWNLOAD LEARNING AGREEMENT
# ============================================================================

@pratiche_bp.route("/la/<int:id_versione>/documento")
@login_required
def scarica_la(id_versione: int):
    """Scarica il Learning Agreement firmato, a chi ha diritto di vederlo.

    E' QUESTA ROTTA A GIUSTIFICARE uploads/ FUORI DA static/
        Dentro static/ Flask servirebbe il file a chiunque ne conosca
        l'indirizzo, senza chiedere chi sia. Cosi' invece si passa di qui,
        e qui esigi_accesso verifica identita' e appartenenza prima di
        consegnare qualsiasi cosa.

    Il nome con cui il file viene scaricato lo genera l'applicazione: quello
    scelto dall'utente resta nel database solo per essere mostrato.
    """
    versione = db.session.get(LearningAgreement, id_versione)
    if versione is None or not versione.file_path:
        abort(404)

    esigi_accesso(versione.pratica)

    nome = (f"LA-{versione.pratica.codice_pratica}"
            f"-v{versione.numero_versione}.pdf")

    return send_file(percorso_documento(versione.file_path),
                     mimetype="application/pdf",
                     as_attachment=True,
                     download_name=nome)




# ============================================================================
# DOWNLOAD TRANSCRIPT
# ============================================================================
@pratiche_bp.route("/transcript/<int:id_pratica>/documento")
@login_required
def scarica_transcript(id_pratica: int):
    pratica = _carica_pratica(id_pratica)
    if not pratica.transcript or not pratica.transcript.file_path:
        abort(404)

    nome = f"Transcript-{pratica.codice_pratica}.pdf"
    return send_file(
        percorso_documento(pratica.transcript.file_path),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=nome,
    )

