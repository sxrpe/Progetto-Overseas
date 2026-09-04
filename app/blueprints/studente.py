"""Area studente.  ->  Da scrivere in FASE 7 (punti 7.2, 7.3, 7.6, 7.8).

ROUTE PREVISTE
    GET  /studente/pratiche                     elenco delle PROPRIE pratiche
    GET  /studente/pratiche/nuova               form di creazione
    POST /studente/pratiche/nuova               creazione
    GET   /studente/pratiche/<id>/la                 mappatura del piano
    POST  /studente/pratiche/<id>/la/mapping         aggiunta riga      -> JSON
    POST  /studente/la/mapping/<id_map>/modifica     modifica riga      -> JSON
    POST  /studente/la/mapping/<id_map>/elimina      eliminazione riga  -> JSON
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




    200   ok                 il valore predefinito
    400   Bad Request        i dati che mi hai mandato non vanno bene
    403   Forbidden          non hai i permessi
    404   Not Found          non esiste
    500   Internal Error     ho sbagliato io
"""
import datetime as dt


import sqlalchemy as sa
from flask import (Blueprint, abort, flash, jsonify, redirect,
                   render_template, request, url_for, Response)
from flask_login import current_user, login_required
from sqlalchemy.orm import selectinload

from app.enums import Ruolo, Periodo, EsitoDocumento, StatoPratica
from app.extensions import db
from app.models import Pratica, Istituto, Utente, CorsoInterno,CorsoEsterno, LearningAgreement, Equivalenza
from app.security import ruolo_richiesto, esigi_accesso, esigi_modifica
from app.documenti import (DocumentoNonValido, elimina_documento,
                           genera_pdf_la, salva_documento)
studente_bp = Blueprint("studente", __name__)

# ============================================================================
# PAGINA DI BASE : ELENCO DELLE PRATICHE
# ============================================================================
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

# ============================================================================
# MODULO : CREAZIONE NUOVA PRATICA
# ============================================================================
def _intero(nome_campo):
    """Legge un campo del form come intero, None se manca o non è un numero."""
    try:
        return int(request.form.get(nome_campo, ""))
    except ValueError:
        return None

def _dati_modulo():
    """Le liste che servono a riempire i menu del modulo,da settembre in poi l'anno accademico è quello nuovo """
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
        return render_template("studente/nuova_pratica.html",**_dati_modulo(),
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
            return render_template("studente/nuova_pratica.html",**_dati_modulo(),periodo_selected=periodo_selected, istituto_selected=istituto_selected, anno_selected=anno_selected, docente_selected=docente_selected)

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
            return render_template("studente/nuova_pratica.html", **_dati_modulo(),
                                   anno_selected=anno_selected,
                                   periodo_selected=periodo_selected,
                                   istituto_selected=istituto_selected,
                                   docente_selected=docente_selected)
        except sa.exc.DatabaseError as errore:
            db.session.rollback()
            flash(str(errore.orig).split("\n")[0], "danger")
            return render_template("studente/nuova_pratica.html", **_dati_modulo(),
                                   anno_selected=anno_selected,
                                   periodo_selected=periodo_selected,
                                   istituto_selected=istituto_selected,
                                   docente_selected=docente_selected)
        flash(f"Pratica {pratica.codice_pratica} creata.", "success")
        return redirect(url_for("pratiche.dettaglio", id_pratica=pratica.id))


# ============================================================================
# MAPPING : UTILITY
# ============================================================================
def _bozza_aperta(pratica: Pratica):
    """La versione del piano ancora in attesa di decisione, o None.

       Ce n'e' al massimo una per pratica: lo garantisce l'indice unico
       parziale uq_la_una_sola_in_attesa.
       """
    versione = db.session.scalar(
        sa.select(LearningAgreement)
        .where(LearningAgreement.pratica_id == pratica.id)
        .where(LearningAgreement.esito == EsitoDocumento.IN_ATTESA)
    )
    return versione
def _corso_esterno_dello_studente(id_map):
    """Carica il corso esterno, verificando che appartenga a chi lo chiede."""
    corso = db.session.get(CorsoEsterno, id_map)
    if corso is None:
        abort(404)
    pratica = corso.learning_agreement.pratica
    esigi_accesso(pratica)      # 404 se non e' sua
    esigi_modifica(pratica)     # 403 se lo stato non lo permette
    return corso

def _pratica_dello_studente(id_pratica):
    pratica = db.session.get(Pratica, id_pratica)
    if pratica is None:
        abort(404)
    esigi_accesso(pratica)
    esigi_modifica(pratica)
    return pratica
# ============================================================================
# PAGINA DI BASE : MAPPING LEARNIN E AGREEMENTS
# ============================================================================

# La pagina della mappatura.
@studente_bp.route("/pratiche/<int:id_pratica>/la", methods=["GET"])
@login_required
@ruolo_richiesto(Ruolo.STUDENTE)
def nuovo_la(id_pratica: int):

    pratica = _pratica_dello_studente(id_pratica)
    #Carichiamo la lista dei Corsi Interni
    corsi_interni = db.session.scalars(
        sa.select(CorsoInterno).order_by(CorsoInterno.codice)
    ).all()

    versione = _bozza_aperta(pratica)

    # Gestione nessuna bozza: crearne una nuova
    if versione is None:
        # Prende il numero dell'ultima versione il or 0 consente se la risposta é NULL = None
        # in python None or 0 scrive 0
        ultimo = db.session.scalar(
            sa.select(sa.func.max(LearningAgreement.numero_versione))
            .where(LearningAgreement.pratica_id == pratica.id)
        ) or 0

        # Creiamo un'ogetto della Bozza
        versione = LearningAgreement(
            pratica_id=pratica.id,
            numero_versione=ultimo + 1,
        )
        db.session.add(versione)
        db.session.commit()
        return render_template('pratiche/mappatura.html', pratica=pratica, versione=versione,
                               corsi=[], corsi_interni=corsi_interni, sola_lettura=False, puo_decidere=False)
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
        # {{ c.equivalenze[0].corso_interno.codice }} sono due selection load annidati
        return render_template('pratiche/mappatura.html', pratica=pratica, versione=versione,
                               corsi=corsi,corsi_interni=corsi_interni, sola_lettura=False, puo_decidere=False)


# ============================================================================
# GESTIONE MAPPING : CREAZIONE
# ============================================================================


# Aggiunge una riga di mapping. Risponde JSON.
@studente_bp.route("/pratiche/<int:id_pratica>/la/mapping", methods=["POST"])
@login_required
@ruolo_richiesto(Ruolo.STUDENTE)
def crea_map(id_pratica: int):
    pratica = _pratica_dello_studente(id_pratica)

    codice = request.form.get("codice", "").strip().upper()
    titolo = request.form.get("titolo", "").strip()
    crediti = _intero("crediti")
    corso_interno_id = _intero("corso_interno_id")
    # ritorniamo un json perche la richiesta non ricarica la pagina, é lo script di javascript che attende una risposta alla richiesta senza ricaricare la paginas
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
    # Appendiamo l'aggiunta dell'equivalenza, perche l'id del corso esterno non esiste ancora, esiste quando facciamo il commit,
    # cosi stiamo appendendo l'aggiunta al database
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
# GESTIONE MAPPING : MODIFICA
# ============================================================================


# Modifica una riga esistente. Risponde JSON.
@studente_bp.route("/la/mapping/<int:id_map>/modifica", methods=["POST"])
@login_required
@ruolo_richiesto(Ruolo.STUDENTE)
def modifica_map(id_map: int):
    corso_esterno =  _corso_esterno_dello_studente(id_map)

    codice = request.form.get("codice", "").strip().upper()
    titolo = request.form.get("titolo", "").strip()
    crediti = _intero("crediti")
    corso_interno_id = _intero("corso_interno_id")
    # ritorniamo un json perche la richiesta non ricarica la pagina, é lo script di javascript che attende una risposta alla richiesta senza ricaricare la paginas
    if not codice or not titolo or crediti is None or corso_interno_id is None:
        return jsonify(ok=False, errore="Compila tutti i campi."), 400

    if crediti < 1 or crediti > 60:
        return jsonify(ok=False, errore="I CFU devono essere fra 1 e 60."), 400

    corso_esterno.titolo = titolo
    corso_esterno.crediti = crediti
    corso_esterno.codice = codice

    # Sostituisce l'equivalenza: clear() cancella la riga vecchia grazie al
    # cascade delete-orphan, append aggiunge quella nuova.
    corso_esterno.equivalenze.clear()
    corso_esterno.equivalenze.append(Equivalenza(corso_interno_id=corso_interno_id))

   # nessun sesison.ad, abbiamo gia gli oggetti nel database dobbiamo solo modificarli col commit

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
# GESTIONE MAPPING : ELIMINAZIONE
# ============================================================================

# Elimina una riga. Risponde JSON.
@studente_bp.route("/la/mapping/<int:id_map>/elimina", methods=["POST"])
@login_required
@ruolo_richiesto(Ruolo.STUDENTE)
def elimina_map(id_map: int):
    corso = _corso_esterno_dello_studente(id_map)
    db.session.delete(corso)
    #Facciamo solo il controllo per l'errore del possibile trigger, nessun integrity error
    try:
        db.session.commit()
        return jsonify(ok=True)
    except sa.exc.DatabaseError as errore:
        db.session.rollback()
        return jsonify(ok=False, errore=str(errore.orig).split("\n")[0]), 400



# ============================================================================
# GESTIONE DOCUMENTO : CREAZIONE
# ============================================================================

def _corsi_della_versione(versione):
    """Ritorna una lista di corsi esterni della versione, con interpolati i corsi interni

     Se faccio corsi = _corsi_della_versione(versione),
     for corso_est in corsi:
        print(f"Corso all'estero: {corso_est.titolo}")
        for eq in corso_est.equivalenze:
            # Questo non lancia query aggiuntive, i dati sono già in memoria!
            print(f"  Riconosciuto a Ca' Foscari come: {eq.corso_interno.titolo}")
     """
    return db.session.scalars(
        sa.select(CorsoEsterno)
        .where(CorsoEsterno.learning_agreement_id == versione.id)
        .options(selectinload(CorsoEsterno.equivalenze)
                 .selectinload(Equivalenza.corso_interno))
        .order_by(CorsoEsterno.codice)
    ).all()

# ============================================================================
# GESTIONE DOCUMENTO : CREAZIONE
# ============================================================================
@studente_bp.route("/pratiche/<int:id_pratica>/la/documento.pdf")
@login_required
@ruolo_richiesto(Ruolo.STUDENTE)
def documento_pdf(id_pratica: int):
    pratica = _pratica_dello_studente(id_pratica)
    versione = _bozza_aperta(pratica)
    if versione is None:
        abort(404)

    pdf = genera_pdf_la(pratica, versione, _corsi_della_versione(versione))

    modo = "attachment" if request.args.get("scarica") else "inline"
    nome = f"LA-{pratica.codice_pratica}-v{versione.numero_versione}.pdf"

    return Response(pdf, mimetype="application/pdf", headers={
        "Content-Disposition": f'{modo}; filename="{nome}"',
    })

# Con GET ritorniamo la pagina di visualizzazione  del documento, con POST gestiamo la richiesta di creazione del documento
@studente_bp.route("/pratiche/<int:id_pratica>/la/documento", methods=["GET", "POST"])
@login_required
@ruolo_richiesto(Ruolo.STUDENTE)
def documento_la(id_pratica: int):
    pratica = _pratica_dello_studente(id_pratica)
    versione = _bozza_aperta(pratica)
    if versione is None:
        abort(404)
    # FIXME finire il post che non funziona il caricamento
    if request.method == "POST":
        try:
            nome_disco, nome_originale = salva_documento(request.files.get("documento"))

        except DocumentoNonValido as errore:
            flash(str(errore), "danger")
            return redirect(url_for("studente.documento_la", id_pratica=pratica.id))

        versione.file_path = nome_disco
        versione.nome_file_originale = nome_originale
        db.session.flush()
        # Da APERTA la pratica entra in valutazione. Durante la mobilita' invece
        # resta MOBILITA_IN_CORSO: e' la versione in attesa a dire che c'e' una
        # proposta pendente, non lo stato della pratica.
        if pratica.stato == StatoPratica.APERTA:
            pratica.stato = StatoPratica.ATTESA_APPROVAZIONE_LA


        try:
            db.session.commit()
        except sa.exc.DatabaseError as errore:
            db.session.rollback()
            elimina_documento(nome_disco)      # il file era gia' su disco
            flash(str(errore.orig).split("\n")[0], "danger")
            return redirect(url_for("studente.documento_la", id_pratica=pratica.id))

        flash("Learning Agreement inviato al docente referente.", "success")
        return redirect(url_for("pratiche.dettaglio", id_pratica=pratica.id))

    return render_template("pratiche/documento.html",
                           pratica=pratica, versione=versione,
                           corsi=_corsi_della_versione(versione))


# ============================================================================
# DATE DELLA MOBILITA'
# ============================================================================

@studente_bp.route("/pratiche/<int:id_pratica>/inizio", methods=["POST"])
@login_required
@ruolo_richiesto(Ruolo.STUDENTE)
def registra_inizio(id_pratica: int):
    """Registra l'arrivo presso l'ateneo ospitante.

    Data e stato stanno sulla stessa riga, quindi partono in un solo UPDATE:
    qui non serve nessun flush. Il CHECK ck_pratica_stato_implica_inizio
    verifica proprio che i due valori arrivino insieme.
    """
    pratica = _pratica_dello_studente(id_pratica)

    try:
        giorno = dt.date.fromisoformat(request.form.get("data_inizio_effettivo", ""))
    except ValueError:
        flash("Data di arrivo non valida.", "danger")
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


@studente_bp.route("/pratiche/<int:id_pratica>/rientro", methods=["POST"])
@login_required
@ruolo_richiesto(Ruolo.STUDENTE)
def registra_rientro(id_pratica: int):
    """Registra il rientro e carica il Transcript of Records.

    L'ORDINE DELLE SCRITTURE
        Il trigger sulla transizione verso IN_RICONOSCIMENTO_ESAMI conta le
        righe in transcript per quella pratica. Se l'UPDATE su pratica
        partisse per primo, il transcript non ci sarebbe ancora e il
        controllo fallirebbe. Da qui il flush() prima di toccare lo stato.

    IL FILE SU DISCO NON SEGUE IL ROLLBACK
        salva_documento() ha gia' scritto sul disco quando arriva il commit.
        Se il commit fallisce, il rollback annulla il database ma non il
        file: va cancellato a mano, altrimenti si accumulano orfani.
    """
    pratica = _pratica_dello_studente(id_pratica)

    try:
        giorno = dt.date.fromisoformat(request.form.get("data_fine_effettiva", ""))
    except ValueError:
        flash("Data di rientro non valida.", "danger")
        return redirect(url_for("pratiche.dettaglio", id_pratica=pratica.id))

    try:
        nome_disco, nome_originale = salva_documento(request.files.get("documento"))
    except DocumentoNonValido as errore:
        flash(str(errore), "danger")
        return redirect(url_for("pratiche.dettaglio", id_pratica=pratica.id))

    db.session.add(Transcript(
        pratica_id=pratica.id,
        file_path=nome_disco,
        nome_file_originale=nome_originale,
    ))
    db.session.flush()          # il trigger deve vederlo

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

    flash("Rientro registrato e Transcript caricato. "
          "Ora puoi inserire i voti degli esami sostenuti.", "success")
    return redirect(url_for("pratiche.dettaglio", id_pratica=pratica.id))