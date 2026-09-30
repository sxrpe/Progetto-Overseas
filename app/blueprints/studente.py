"""
DESCRIZIONE
    Area studente: pratiche, Learning Agreement, date, esami, rientro.
    Il filtro per studente_id sta sempre nella query, non nel template.

MAPPA
    GET  /studente/pratiche                              elenco_pratiche     le mie pratiche
    GET  /studente/pratiche/nuova                        nuova_pratica       form creazione
    POST /studente/pratiche/nuova                        nuova_pratica       salva pratica
    GET  /studente/pratiche/<id>/la                      nuovo_la            mappatura piano
    POST /studente/pratiche/<id>/la/scarta               scarta_bozza        elimina bozza
    POST /studente/pratiche/<id>/la/mapping              crea_map            aggiunge riga (JSON)
    POST /studente/la/mapping/<id>/modifica              modifica_map        modifica riga (JSON)
    POST /studente/la/mapping/<id>/elimina               elimina_map         elimina riga (JSON)
    GET  /studente/pratiche/<id>/la/documento.pdf        documento_pdf       anteprima/download PDF
    GET  /studente/pratiche/<id>/la/documento            documento_la        pagina firma
    POST /studente/pratiche/<id>/la/documento            documento_la        carica PDF firmato
    POST /studente/pratiche/<id>/inizio                  registra_inizio     data arrivo
    GET  /studente/pratiche/<id>/esami                   vedi_esami          inserimento voti
    POST /studente/pratiche/<id>/esami/<id>/salva        salva_esame         salva voto (JSON)
    POST /studente/pratiche/<id>/esami/<id>/elimina      elimina_esame       scarta voto (JSON)
    POST /studente/pratiche/<id>/rientro                 registra_rientro    rientro + Transcript
"""
import datetime as dt


import sqlalchemy as sa
from flask import (Blueprint, abort, flash, jsonify, redirect,
                   render_template, request, url_for, Response)
from flask_login import current_user, login_required
from sqlalchemy.orm import selectinload

from app.enums import Ruolo, Periodo, EsitoDocumento, EsitoRiconoscimento, StatoPratica
from app.extensions import db
from app.models import Pratica, Istituto, Utente, CorsoInterno,CorsoEsterno, LearningAgreement, Equivalenza, Transcript, Esame
from app.security import ruolo_richiesto, esigi_accesso, esigi_modifica
from app.documenti import (DocumentoNonValido, elimina_documento,
                           genera_pdf_la, salva_documento)
studente_bp = Blueprint("studente", __name__)

# ============================================================================
# ELENCO PRATICHE
# GET  /studente/pratiche  ->  elenco_pratiche
# ============================================================================
@studente_bp.route("/pratiche", methods=["GET"])
@login_required
@ruolo_richiesto(Ruolo.STUDENTE)
def elenco_pratiche():
    """Le pratiche dello studente collegato, e solo le sue.

    selectinload precarica istituto e docente: senza, ogni riga nel template
    farebbe una query in più (N+1). scalars().all() restituisce una lista
    di oggetti Python. Ordinamento: anno desc, poi codice pratica.
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

# ============================================================================
# UTILITY CREAZIONE PRATICA
# ============================================================================
def _intero(nome_campo):
    """Legge un campo del form come intero; None se manca o non è un numero."""
    try:
        return int(request.form.get(nome_campo, ""))
    except ValueError:
        return None

def _dati_modulo():
    """Liste per i menu del form (atenei, docenti, anni).

    Da settembre l'anno accademico è quello nuovo. Ritorna un dizionario:
    con **_dati_modulo() le chiavi diventano argomenti del render_template.
    """
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

# ============================================================================
# NUOVA PRATICA
# GET/POST  /studente/pratiche/nuova  ->  nuova_pratica
# ============================================================================
@studente_bp.route("/pratiche/nuova", methods=["GET", "POST"])
@login_required
@ruolo_richiesto(Ruolo.STUDENTE)
def nuova_pratica():
    """Form di creazione (GET) e salvataggio della pratica (POST)."""

    if request.method == "GET":
        # ** spacchetta il dizionario: atenei/docenti/anni → argomenti del template
        return render_template("studente/nuova_pratica.html",**_dati_modulo(),
                               anno_selected=None, periodo_selected=None,istituto_selected=None, docente_selected=None,
                               note_selected=None)
    else:
        # Invio del form: leggiamo i campi e validiamo

        anno_selected = _intero("anno_accademico")

        if request.form.get("periodo", "") in Periodo.TUTTI:
            periodo_selected = request.form.get("periodo", "")
        else:
            periodo_selected = None

        istituto_selected = _intero("istituto_id")
        docente_selected = _intero("docente_id")
        note_selected = (request.form.get("note") or "").strip() or None

        # Campi incompleti → ripresentiamo il form con ciò che aveva già scritto
        if None in (anno_selected, periodo_selected,
                    istituto_selected, docente_selected):
            flash("Compila tutti i campi.", "danger")
            return render_template("studente/nuova_pratica.html",**_dati_modulo(),periodo_selected=periodo_selected, istituto_selected=istituto_selected, anno_selected=anno_selected, docente_selected=docente_selected, note_selected=note_selected)

        # Codice OVS-AAAA-NNN. sa.func.count() = count(*) SQL sull'anno scelto.
        quante = db.session.scalar(
            sa.select(sa.func.count())
            .select_from(Pratica)
            .where(Pratica.anno_accademico == anno_selected)
        )
        # :03d = tre cifre con zeri davanti = es. OVS-2025-001
        codice = f"OVS-{anno_selected}-{quante + 1:03d}"


        pratica = Pratica(
            codice_pratica=codice,
            anno_accademico=anno_selected,
            periodo=periodo_selected,
            istituto_id=istituto_selected,
            docente_id=docente_selected,
            studente_id=current_user.id,
            note=note_selected,
        )
        db.session.add(pratica)

        try:
            db.session.commit()
        except sa.exc.IntegrityError:
            db.session.rollback()
            flash("Non è stato possibile creare la pratica: dati non validi.", "danger")
            return render_template("studente/nuova_pratica.html", **_dati_modulo(),
                                   anno_selected=anno_selected,
                                   periodo_selected=periodo_selected,
                                   istituto_selected=istituto_selected,
                                   docente_selected=docente_selected,
                                   note_selected=note_selected)
        except sa.exc.DatabaseError as errore:
            db.session.rollback()
            flash(str(errore.orig).split("\n")[0], "danger")
            return render_template("studente/nuova_pratica.html", **_dati_modulo(),
                                   anno_selected=anno_selected,
                                   periodo_selected=periodo_selected,
                                   istituto_selected=istituto_selected,
                                   docente_selected=docente_selected,
                                   note_selected=note_selected)
        flash(f"Pratica {pratica.codice_pratica} creata.", "success")
        return redirect(url_for("pratiche.dettaglio", id_pratica=pratica.id))


# ============================================================================
# UTILITY MAPPING
# ============================================================================
def _bozza_aperta(pratica: Pratica):
    """La versione del piano ancora in attesa di decisione, o None.

    Ce n'è al massimo una per pratica: lo garantisce l'indice unico
    parziale uq_la_una_sola_in_attesa.
    """
    versione = db.session.scalar(
        sa.select(LearningAgreement)
        .where(LearningAgreement.pratica_id == pratica.id)
        .where(LearningAgreement.esito == EsitoDocumento.IN_ATTESA)
    )
    return versione
def _versione_approvata(pratica: Pratica):
    """L'ultima versione approvata, da cui copiare i corsi per una modifica."""
    migliore = None
    for v in pratica.learning_agreements:
        if v.esito == EsitoDocumento.APPROVATO:
            if migliore is None or v.numero_versione > migliore.numero_versione:
                migliore = v
    return migliore

def _corso_esterno_dello_studente(id_map):
    """Carica il corso esterno, verificando che appartenga a chi lo chiede."""
    corso = db.session.get(CorsoEsterno, id_map)
    if corso is None:
        abort(404)
    pratica = corso.learning_agreement.pratica
    esigi_accesso(pratica)      # 404 se non è sua
    esigi_modifica(pratica)     # 403 se lo stato non lo permette
    return corso

def _pratica_dello_studente(id_pratica):
    """Carica la pratica: 404 se non esiste, poi controllo accesso e modifica."""
    pratica = db.session.get(Pratica, id_pratica)
    if pratica is None:
        abort(404)
    esigi_accesso(pratica)
    esigi_modifica(pratica)
    return pratica

# ============================================================================
# MAPPATURA LEARNING AGREEMENT
# GET  /studente/pratiche/<id>/la  ->  nuovo_la
# ============================================================================
@studente_bp.route("/pratiche/<int:id_pratica>/la", methods=["GET"])
@login_required
@ruolo_richiesto(Ruolo.STUDENTE)
def nuovo_la(id_pratica: int):
    """Pagina di mappatura: apre o riprende la bozza del piano."""

    pratica = _pratica_dello_studente(id_pratica)
    # Menu a tendina: corsi Unive con cui fare equivalenza
    corsi_interni = db.session.scalars(
        sa.select(CorsoInterno).order_by(CorsoInterno.codice)
    ).all()

    versione = _bozza_aperta(pratica)

    # Nessuna bozza aperta → ne apriamo una. Se esiste un piano approvato,
    # ne copiamo i corsi così la modifica parte da quello e non da zero.
    if versione is None:
        ultimo = db.session.scalar(
            sa.select(sa.func.max(LearningAgreement.numero_versione))
            .where(LearningAgreement.pratica_id == pratica.id)
        ) or 0

        versione = LearningAgreement(pratica_id=pratica.id, numero_versione=ultimo + 1)
        db.session.add(versione)

        vecchia_versione = _versione_approvata(pratica)
        if vecchia_versione:
            # flush: senza id della nuova versione non si possono attaccare i corsi
            db.session.flush()
            for c_vecchio in _corsi_della_versione(vecchia_versione):
                c_nuovo = CorsoEsterno(
                    codice=c_vecchio.codice, titolo=c_vecchio.titolo,
                    crediti=c_vecchio.crediti, learning_agreement_id=versione.id
                )
                for eq_vecchia in c_vecchio.equivalenze:
                    c_nuovo.equivalenze.append(Equivalenza(corso_interno_id=eq_vecchia.corso_interno_id))
                db.session.add(c_nuovo)

        db.session.commit()

        # Ricarichiamo i corsi appena salvati (non passiamo [])
        corsi_salvati = _corsi_della_versione(versione)

        return render_template('pratiche/mappatura.html', pratica=pratica, versione=versione,
                               corsi=corsi_salvati, corsi_interni=corsi_interni, sola_lettura=False, puo_decidere=False)
    else:
        corsi = db.session.scalars(
            sa.select(CorsoEsterno)
            .where(CorsoEsterno.learning_agreement_id == versione.id)
            .options(
                selectinload(CorsoEsterno.equivalenze)
                .selectinload(Equivalenza.corso_interno)
            )
            .order_by(CorsoEsterno.codice)
        ).all()
        # due selectinload annidati: nel template c.equivalenze[0].corso_interno.codice
        # senza N+1 (equivalenza + corso interno già in memoria)
        return render_template('pratiche/mappatura.html', pratica=pratica, versione=versione,
                               corsi=corsi,corsi_interni=corsi_interni, sola_lettura=False, puo_decidere=False)


# ============================================================================
# SCARTA BOZZA
# POST  /studente/pratiche/<id>/la/scarta  ->  scarta_bozza
# ============================================================================
@studente_bp.route("/pratiche/<int:id_pratica>/la/scarta", methods=["POST"])
@login_required
@ruolo_richiesto(Ruolo.STUDENTE)
def scarta_bozza(id_pratica: int):
    """Elimina una bozza in lavorazione (ancora senza file caricato)."""
    pratica = _pratica_dello_studente(id_pratica)
    versione = _bozza_aperta(pratica)

    # Si scarta solo se è ancora bozza IN_ATTESA e il PDF non è stato caricato.
    # Dopo l'invio del documento non si torna indietro da qui.
    if versione is not None and versione.file_path is None:
        db.session.delete(versione)
        db.session.commit()
        flash("La bozza del Learning Agreement è stata annullata ed eliminata.", "success")
    else:
        flash("Impossibile scartare questo documento.", "danger")

    return redirect(url_for("pratiche.dettaglio", id_pratica=pratica.id))

# ============================================================================
# CREA RIGA MAPPING
# POST  /studente/pratiche/<id>/la/mapping  ->  crea_map
# ============================================================================
@studente_bp.route("/pratiche/<int:id_pratica>/la/mapping", methods=["POST"])
@login_required
@ruolo_richiesto(Ruolo.STUDENTE)
def crea_map(id_pratica: int):
    """Aggiunge una riga di mapping. Risposta JSON: la pagina non si ricarica,
    è lo script JS che aggiorna la tabella."""
    pratica = _pratica_dello_studente(id_pratica)

    codice = request.form.get("codice", "").strip().upper()
    titolo = request.form.get("titolo", "").strip()
    crediti = _intero("crediti")
    corso_interno_id = _intero("corso_interno_id")
    # jsonify perché la chiamata è AJAX: niente redirect, solo ok/errore
    if not codice or not titolo or crediti is None or corso_interno_id is None:
        return jsonify(ok=False, errore="Compila tutti i campi."), 400

    if crediti < 1 or crediti > 60:
        return jsonify(ok=False, errore="I CFU devono essere fra 1 e 60."), 400


    versione = _bozza_aperta(pratica)
    if versione is None:
        return jsonify(ok=False, errore="Nessuna bozza aperta per questa pratica."), 400

    corso_esterno = CorsoEsterno(
        codice=codice,
        titolo=titolo,
        crediti=crediti,
        learning_agreement_id=versione.id,
    )
    # L'id del corso esterno nasce al commit: append sull'oggetto ORM basta,
    # SQLAlchemy salva l'equivalenza insieme quando fa il flush.
    corso_esterno.equivalenze.append(
        Equivalenza(corso_interno_id=corso_interno_id)
    )
    db.session.add(corso_esterno)

    try:
        db.session.commit()
        return jsonify(ok=True)
    except sa.exc.IntegrityError:
        db.session.rollback()
        return jsonify(ok=False, errore="Codice già presente in questo piano."), 400
    except sa.exc.DatabaseError as errore:
        db.session.rollback()
        return jsonify(ok=False, errore=str(errore.orig).split("\n")[0]), 400


# ============================================================================
# MODIFICA RIGA MAPPING
# POST  /studente/la/mapping/<id>/modifica  ->  modifica_map
# ============================================================================
@studente_bp.route("/la/mapping/<int:id_map>/modifica", methods=["POST"])
@login_required
@ruolo_richiesto(Ruolo.STUDENTE)
def modifica_map(id_map: int):
    """Modifica una riga esistente. Anche qui risposta JSON (AJAX)."""
    corso_esterno =  _corso_esterno_dello_studente(id_map)

    codice = request.form.get("codice", "").strip().upper()
    titolo = request.form.get("titolo", "").strip()
    crediti = _intero("crediti")
    corso_interno_id = _intero("corso_interno_id")
    if not codice or not titolo or crediti is None or corso_interno_id is None:
        return jsonify(ok=False, errore="Compila tutti i campi."), 400

    if crediti < 1 or crediti > 60:
        return jsonify(ok=False, errore="I CFU devono essere fra 1 e 60."), 400

    corso_esterno.titolo = titolo
    corso_esterno.crediti = crediti
    corso_esterno.codice = codice

    # Sostituisce l'equivalenza: clear() cancella la riga vecchia
    # (cascade delete-orphan), append ne mette una nuova.
    corso_esterno.equivalenze.clear()
    corso_esterno.equivalenze.append(Equivalenza(corso_interno_id=corso_interno_id))

    # Niente session.add: l'oggetto è già in sessione, basta il commit.
    try:

        interno = db.session.get(CorsoInterno, corso_interno_id)
        db.session.commit()

        return jsonify(ok=True, corso={
            "codice": corso_esterno.codice,
            "titolo": corso_esterno.titolo,
            "crediti": corso_esterno.crediti,
            "equivalenza": f"→ {interno.codice}",
        })
    except sa.exc.IntegrityError:
        db.session.rollback()
        return jsonify(ok=False, errore="Codice già presente in questo piano."), 400
    except sa.exc.DatabaseError as errore:
        db.session.rollback()
        return jsonify(ok=False, errore=str(errore.orig).split("\n")[0]), 400

# ============================================================================
# ELIMINA RIGA MAPPING
# POST  /studente/la/mapping/<id>/elimina  ->  elimina_map
# ============================================================================
@studente_bp.route("/la/mapping/<int:id_map>/elimina", methods=["POST"])
@login_required
@ruolo_richiesto(Ruolo.STUDENTE)
def elimina_map(id_map: int):
    """Elimina una riga di mapping. Risposta JSON per AJAX."""
    corso = _corso_esterno_dello_studente(id_map)
    db.session.delete(corso)
    # Solo DatabaseError: un trigger sul DB può bloccare; IntegrityError no.
    try:
        db.session.commit()
        return jsonify(ok=True)
    except sa.exc.DatabaseError as errore:
        db.session.rollback()
        return jsonify(ok=False, errore=str(errore.orig).split("\n")[0]), 400



# ============================================================================
# UTILITY DOCUMENTO
# ============================================================================

def _corsi_della_versione(versione):
    """Corsi esterni della versione, con equivalenze e corsi interni già caricati.

    Così nel template (o in un for) si può leggere eq.corso_interno.titolo
    senza altre query: i dati sono già in memoria.
    """
    return db.session.scalars(
        sa.select(CorsoEsterno)
        .where(CorsoEsterno.learning_agreement_id == versione.id)
        .options(selectinload(CorsoEsterno.equivalenze)
                 .selectinload(Equivalenza.corso_interno))
        .order_by(CorsoEsterno.codice)
    ).all()

# ============================================================================
# DOCUMENTO PDF
# GET  /studente/pratiche/<id>/la/documento.pdf  ->  documento_pdf
# ============================================================================
@studente_bp.route("/pratiche/<int:id_pratica>/la/documento.pdf")
@login_required
@ruolo_richiesto(Ruolo.STUDENTE)
def documento_pdf(id_pratica: int):
    """Anteprima o download del PDF generato dalla bozza."""
    pratica = _pratica_dello_studente(id_pratica)
    versione = _bozza_aperta(pratica)
    if versione is None:
        abort(404)

    pdf = genera_pdf_la(pratica, versione, _corsi_della_versione(versione))

    # ?scarica=1 → download; altrimenti anteprima nel browser (inline)
    modo = "attachment" if request.args.get("scarica") else "inline"
    nome = f"LA-{pratica.codice_pratica}-v{versione.numero_versione}.pdf"

    return Response(pdf, mimetype="application/pdf", headers={
        "Content-Disposition": f'{modo}; filename="{nome}"',
    })

# ============================================================================
# DOCUMENTO LA (FIRMA)
# GET/POST  /studente/pratiche/<id>/la/documento  ->  documento_la
# ============================================================================
@studente_bp.route("/pratiche/<int:id_pratica>/la/documento", methods=["GET", "POST"])
@login_required
@ruolo_richiesto(Ruolo.STUDENTE)
def documento_la(id_pratica: int):
    """GET: pagina di firma. POST: carica il PDF firmato e lo manda al docente."""
    pratica = _pratica_dello_studente(id_pratica)
    versione = _bozza_aperta(pratica)
    if versione is None:
        abort(404)
    if request.method == "POST":
        try:
            nome_disco, nome_originale = salva_documento(request.files.get("documento"))

        except DocumentoNonValido as errore:
            flash(str(errore), "danger")
            return redirect(url_for("studente.documento_la", id_pratica=pratica.id))

        versione.file_path = nome_disco
        versione.nome_file_originale = nome_originale
        db.session.flush()
        # Da APERTA entra in valutazione. In mobilità resta MOBILITA_IN_CORSO:
        # è la versione IN_ATTESA a dire che c'è una proposta pendente,
        # non lo stato della pratica.
        if pratica.stato == StatoPratica.APERTA:
            pratica.stato = StatoPratica.ATTESA_APPROVAZIONE_LA


        try:
            db.session.commit()
        except sa.exc.DatabaseError as errore:
            db.session.rollback()
            elimina_documento(nome_disco)      # il file era già su disco: va tolto
            flash(str(errore.orig).split("\n")[0], "danger")
            return redirect(url_for("studente.documento_la", id_pratica=pratica.id))

        flash("Learning Agreement inviato al docente referente.", "success")
        return redirect(url_for("pratiche.dettaglio", id_pratica=pratica.id))

    return render_template("pratiche/documento.html",
                           pratica=pratica, versione=versione,
                           corsi=_corsi_della_versione(versione))


# ============================================================================
# REGISTRA INIZIO
# POST  /studente/pratiche/<id>/inizio  ->  registra_inizio
# ============================================================================
@studente_bp.route("/pratiche/<int:id_pratica>/inizio", methods=["POST"])
@login_required
@ruolo_richiesto(Ruolo.STUDENTE)
def registra_inizio(id_pratica: int):
    """Registra l'arrivo presso l'ateneo ospitante.

    Data e stato stanno sulla stessa riga → un solo UPDATE, niente flush.
    Il CHECK ck_pratica_stato_implica_inizio vuole proprio che arrivino insieme.
    """
    pratica = _pratica_dello_studente(id_pratica)

    try:
        giorno = dt.date.fromisoformat(request.form.get("data_inizio_effettivo", ""))
    except ValueError:
        flash("Data di arrivo non valida.", "danger")
        return redirect(url_for("pratiche.dettaglio", id_pratica=pratica.id))

    # L'arrivo è un fatto già accaduto: al massimo oggi (come il rientro).
    if giorno > dt.date.today():
        flash("La data di arrivo non può essere successiva a oggi.", "danger")
        return redirect(url_for("pratiche.dettaglio", id_pratica=pratica.id))

    pratica.data_inizio_effettivo = giorno
    pratica.stato = StatoPratica.MOBILITA_IN_CORSO

    try:
        db.session.commit()
    except sa.exc.IntegrityError:
        db.session.rollback()
        flash("La data non è coerente con le altre date della pratica.", "danger")
        return redirect(url_for("pratiche.dettaglio", id_pratica=pratica.id))
    except sa.exc.DatabaseError as errore:
        db.session.rollback()
        flash(str(errore.orig).split("\n")[0], "danger")
        return redirect(url_for("pratiche.dettaglio", id_pratica=pratica.id))

    flash("Inizio della mobilità registrato. Buon soggiorno.", "success")
    return redirect(url_for("pratiche.dettaglio", id_pratica=pratica.id))



# ============================================================================
# INSERIMENTO ESAMI
# GET  /studente/pratiche/<id>/esami  ->  vedi_esami
# ============================================================================
@studente_bp.route("/pratiche/<int:id_pratica>/esami", methods=["GET"])
@login_required
@ruolo_richiesto(Ruolo.STUDENTE)
def vedi_esami(id_pratica: int):
    """Pagina di inserimento voti allo studente."""
    # get + esigi_accesso, non _pratica_dello_studente: esigi_modifica
    # bloccherebbe perché lo stato non è più APERTA.
    pratica = db.session.get(Pratica, id_pratica)
    if pratica is None:
        abort(404)
    esigi_accesso(pratica)

    if pratica.stato != StatoPratica.IN_RICONOSCIMENTO_ESAMI:
        flash("La pratica non è nella fase di riconoscimento esami.", "warning")
        return redirect(url_for("pratiche.dettaglio", id_pratica=pratica.id))

    approvata = _versione_approvata(pratica)
    corsi = _corsi_della_versione(approvata) if approvata else []

    # Dizionario id_corso → esame: nel template si trova subito se c'è già un voto
    esami = {c.id: c.esame for c in corsi if c.esame}

    if corsi and all(
        c.esame is not None
        and c.esame.esito_riconoscimento != EsitoRiconoscimento.NON_VALUTATO
        for c in corsi
    ):
        flash("I voti sono già stati valutati. Si attende la chiusura dell'ufficio.", "info")
        return redirect(url_for("pratiche.dettaglio", id_pratica=pratica.id))

    return render_template("pratiche/esami.html", pratica=pratica, corsi=corsi, esami=esami, valuta=False)

# ============================================================================
# SALVA ESAME
# POST  /studente/pratiche/<id>/esami/<id>/salva  ->  salva_esame
# ============================================================================
@studente_bp.route("/pratiche/<int:id_pratica>/esami/<int:id_corso>/salva", methods=["POST"])
@login_required
@ruolo_richiesto(Ruolo.STUDENTE)
def salva_esame(id_pratica: int, id_corso: int):
    """Salva o aggiorna il voto di un esame. Risposta JSON per AJAX."""
    pratica = db.session.get(Pratica, id_pratica)
    esigi_accesso(pratica)

    if pratica.stato != StatoPratica.IN_RICONOSCIMENTO_ESAMI:
        return jsonify(ok=False, errore="La pratica non è in fase di riconoscimento."), 403

    corso = db.session.get(CorsoEsterno, id_corso)
    if not corso or corso.learning_agreement.pratica_id != pratica.id:
        return jsonify(ok=False, errore="Insegnamento non trovato."), 404

    voto = _intero("voto")
    try:
        data_esame = dt.date.fromisoformat(request.form.get("data_esame", ""))
    except ValueError:
        return jsonify(ok=False, errore="Data non valida."), 400

    # Il riconoscimento confronta con la data in cui decide il docente:
    # una data futura non potrebbe mai essere <= a quella.
    if data_esame > dt.date.today():
        return jsonify(
            ok=False,
            errore="La data dell'esame non può essere successiva a oggi.",
        ), 400

    if not voto or voto < 18 or voto > 31:
        return jsonify(ok=False, errore="Il voto deve essere compreso tra 18 e 31."), 400

    if (corso.esame and corso.esame.esito_riconoscimento
            in (EsitoRiconoscimento.ACCETTATO, EsitoRiconoscimento.RIFIUTATO)):
        return jsonify(
            ok=False,
            errore="Il docente ha già deciso su questo voto e non si può più modificare.",
        ), 403

    # Se c'era già un voto lo aggiorno, altrimenti lo creo
    if corso.esame:
        corso.esame.voto = voto
        corso.esame.data_esame = data_esame
    else:
        db.session.add(Esame(corso_esterno_id=corso.id, voto=voto, data_esame=data_esame))

    try:
        db.session.commit()
        return jsonify(ok=True)
    except sa.exc.DatabaseError:
        db.session.rollback()
        return jsonify(ok=False, errore="Errore di salvataggio nel database."), 400


# ============================================================================
# ELIMINA ESAME
# POST  /studente/pratiche/<id>/esami/<id>/elimina  ->  elimina_esame
# ============================================================================
@studente_bp.route("/pratiche/<int:id_pratica>/esami/<int:id_corso>/elimina", methods=["POST"])
@login_required
@ruolo_richiesto(Ruolo.STUDENTE)
def elimina_esame(id_pratica: int, id_corso: int):
    """Scarta un voto inserito. Risposta JSON per AJAX."""
    pratica = db.session.get(Pratica, id_pratica)
    esigi_accesso(pratica)

    if pratica.stato != StatoPratica.IN_RICONOSCIMENTO_ESAMI:
        return jsonify(ok=False, errore="La pratica non è in fase di riconoscimento."), 403

    corso = db.session.get(CorsoEsterno, id_corso)
    if not corso or corso.learning_agreement.pratica_id != pratica.id:
        return jsonify(ok=False, errore="Insegnamento non trovato."), 404

    if (corso.esame and corso.esame.esito_riconoscimento
            in (EsitoRiconoscimento.ACCETTATO, EsitoRiconoscimento.RIFIUTATO)):
        return jsonify(
            ok=False,
            errore="Il docente ha già deciso su questo voto e non si può più scartare.",
        ), 403

    if corso.esame:
        db.session.delete(corso.esame)
        try:
            db.session.commit()
        except sa.exc.DatabaseError:
            db.session.rollback()
            return jsonify(ok=False, errore="Errore di rete, riprova."), 400

    return jsonify(ok=True)


# ============================================================================
# REGISTRA RIENTRO
# POST  /studente/pratiche/<id>/rientro  ->  registra_rientro
# ============================================================================
@studente_bp.route("/pratiche/<int:id_pratica>/rientro", methods=["POST"])
@login_required
@ruolo_richiesto(Ruolo.STUDENTE)
def registra_rientro(id_pratica: int):
    """Registra il rientro e carica il Transcript of Records insieme."""
    pratica = _pratica_dello_studente(id_pratica)

    # Il piano deve essere fermo: una bozza in attesa non può convivere col Transcript.
    if _bozza_aperta(pratica) is not None:
        flash("Non puoi registrare il rientro: c'è ancora un piano in attesa.", "danger")
        return redirect(url_for("pratiche.dettaglio", id_pratica=pratica.id))

    try:
        giorno = dt.date.fromisoformat(request.form.get("data_fine_effettiva", ""))
    except ValueError:
        flash("Data di rientro non valida.", "danger")
        return redirect(url_for("pratiche.dettaglio", id_pratica=pratica.id))

    # Il rientro è già avvenuto: al massimo oggi. Altrimenti la chiusura
    # ufficio (sempre oggi) resterebbe prima del rientro.
    if giorno > dt.date.today():
        flash("La data di rientro non può essere successiva a oggi.", "danger")
        return redirect(url_for("pratiche.dettaglio", id_pratica=pratica.id))

    try:
        nome_disco, nome_originale = salva_documento(request.files.get("documento"))
    except DocumentoNonValido as errore:
        flash(str(errore), "danger")
        return redirect(url_for("pratiche.dettaglio", id_pratica=pratica.id))

    # 1. Transcript in sessione (file già su disco)
    db.session.add(Transcript(
        pratica_id=pratica.id,
        file_path=nome_disco,
        nome_file_originale=nome_originale,
    ))

    # 2. Flush: scrive il record così il trigger "vede" già il Transcript
    db.session.flush()

    # 3. Poi cambio stato: il trigger scatta e trova il documento
    pratica.data_fine_effettiva = giorno
    pratica.stato = StatoPratica.IN_RICONOSCIMENTO_ESAMI

    try:
        db.session.commit()
    except sa.exc.IntegrityError:
        db.session.rollback()
        elimina_documento(nome_disco)
        flash("Transcript già presente, oppure date non coerenti.", "danger")
        return redirect(url_for("pratiche.dettaglio", id_pratica=pratica.id))
    except sa.exc.DatabaseError as errore:
        db.session.rollback()
        elimina_documento(nome_disco)
        flash(str(errore.orig).split("\n")[0], "danger")
        return redirect(url_for("pratiche.dettaglio", id_pratica=pratica.id))

    flash("Rientro registrato e Transcript caricato. Ora puoi inserire i voti degli esami sostenuti.", "success")
    return redirect(url_for("pratiche.dettaglio", id_pratica=pratica.id))
