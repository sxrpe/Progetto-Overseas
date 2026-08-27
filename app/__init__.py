"""Application factory: il montaggio dell'applicazione.

COSA FA QUESTO FILE
    La funzione create_app() prende i pezzi sparsi (configurazione, database,
    login, blueprint, pagine di errore) e li assembla in un'applicazione
    Flask funzionante.

PERCHE' UNA FUNZIONE E NON UNA VARIABILE GLOBALE
    Perche' cosi' puoi crearne piu' di una, con configurazioni diverse: una
    per lo sviluppo, una per la demo, una per i test. E' lo schema
    raccomandato dalla documentazione di Flask.

L'ORDINE DELLE OPERAZIONI NON E' NEGOZIABILE
    1. crea l'app e carica la configurazione
       (init_app legge da qui l'indirizzo del database)
    2. collega le estensioni (db, login)
    3. IMPORTA i modelli
       (se salti questo, db.create_all() crea zero tabelle SENZA dare errore)
    4. definisce la user_loader di Flask-Login
    5. mette a disposizione dei template le costanti degli enum
    6. registra i blueprint
    7. registra le pagine di errore

QUANDO LO TOCCHI
    Praticamente mai, dopo oggi. Solo se aggiungi un blueprint nuovo.
"""

import sqlalchemy as sa
from flask import Flask, render_template

from config import CONFIGS, Config


def create_app(nome_config: str = "dev") -> Flask:
    app = Flask(__name__)
    app.config.from_object(CONFIGS.get(nome_config, Config))

    # Le estensioni si importano QUI DENTRO, non in cima al file:
    # importarle fuori ricrea l'import circolare che extensions.py evita.
    from app.extensions import db, login_manager

    db.init_app(app)
    login_manager.init_app(app)

    # ------------------------------------------------------------------
    # I MODELLI VANNO IMPORTATI PRIMA DI create_all().
    # SQLAlchemy conosce solo le classi che sono state effettivamente
    # eseguite: se questa riga manca, i metadati restano vuoti e
    # "python -m scripts.init_db" crea zero tabelle senza dare errore.
    #
    # "noqa: F401" dice agli strumenti di controllo del codice: lo so che
    # sembra un import inutilizzato, e' voluto.
    # ------------------------------------------------------------------
    from app import models  # noqa: F401
    from app.models import Utente

    # ------------------------------------------------------------------
    # FLASK-LOGIN: dall'identita' salvata nel cookie all'oggetto Utente.
    #
    # Viene chiamata a OGNI richiesta in cui serve current_user. L'id
    # arriva come stringa perche' i cookie contengono solo testo, da qui
    # la conversione con int().
    #
    # Nel cookie c'e' solo l'id, firmato con la SECRET_KEY. Non la
    # password, non il ruolo: cosi' se un utente viene disabilitato o
    # cambia ruolo, la modifica ha effetto alla richiesta successiva e non
    # alla scadenza del cookie.
    #
    # Deve esistere fin da subito: appena un template nomina current_user,
    # Flask-Login la cerca, e senza di essa solleva un'eccezione.
    # ------------------------------------------------------------------
    @login_manager.user_loader
    def carica_utente(id_utente: str):
        return db.session.get(Utente, int(id_utente))

    # ------------------------------------------------------------------
    # COMUNICARE AL DATABASE CHI STA AGENDO.
    #
    # PostgreSQL non sa chi e' l'utente applicativo: la connessione e'
    # sempre la stessa. Questa riga glielo dice all'inizio di ogni
    # richiesta, e i trigger la rileggono con current_setting() per
    # verificare il ruolo di chi cambia stato e per riempire lo storico.
    #
    # SET LOCAL significa "solo per questa transazione": non sporca le
    # richieste degli altri utenti.
    # ------------------------------------------------------------------
    @app.before_request
    def dichiara_utente_al_database():
        from flask_login import current_user

        if current_user.is_authenticated:
            # NON si puo' scrivere "SET LOCAL app.utente_id = :id".
            # SET LOCAL e' un comando di configurazione, non una query, e
            # PostgreSQL non accetta parametri al suo interno: il driver
            # sostituirebbe :id con un segnaposto $1 e il parser lo rifiuta.
            #
            # set_config() fa la stessa identica cosa ma e' una FUNZIONE,
            # quindi i parametri li accetta. Il terzo argomento, true,
            # significa "solo per questa transazione": e' l'equivalente
            # esatto della parola LOCAL.
            #
            # Concatenare l'id nella stringa funzionerebbe, ma sarebbe una
            # SQL injection in attesa di succedere. Il parametro no.
            db.session.execute(
                sa.text("SELECT set_config('app.utente_id', :id, true)"),
                {"id": str(current_user.id)},
            )

    # ------------------------------------------------------------------
    # COSTANTI DISPONIBILI NEI TEMPLATE.
    #
    # Senza questo, in un template non potresti scrivere
    #     {{ StatoPratica.ETICHETTE[pratica.stato] }}
    # perche' Jinja vede solo le variabili passate a render_template().
    # Registrandole come "globali" diventano visibili in tutte le pagine,
    # e non devi ripassarle a ogni chiamata.
    # ------------------------------------------------------------------
    from app.enums import (
        EsitoDocumento,
        EsitoRiconoscimento,
        Periodo,
        Ruolo,
        StatoPratica,
    )

    app.jinja_env.globals.update(
        Ruolo=Ruolo,
        Periodo=Periodo,
        StatoPratica=StatoPratica,
        EsitoDocumento=EsitoDocumento,
        EsitoRiconoscimento=EsitoRiconoscimento,
    )

    # ------------------------------------------------------------------
    # BLUEPRINT: un'area del sito per ogni gruppo di funzionalita'.
    # L'URL dice gia' chi dovrebbe poterci accedere: tutto cio' che sta
    # sotto /docente/ e' per i docenti. Non e' un controllo di sicurezza
    # (quello sta nelle rotte), ma rende i permessi verificabili a colpo
    # d'occhio guardando la mappa degli URL.
    # ------------------------------------------------------------------
    from app.blueprints.auth import auth_bp
    from app.blueprints.docente import docente_bp
    from app.blueprints.pratiche import pratiche_bp
    from app.blueprints.pubblico import pubblico_bp
    from app.blueprints.studente import studente_bp
    from app.blueprints.ufficio import ufficio_bp

    app.register_blueprint(pubblico_bp)                      # /
    app.register_blueprint(pratiche_bp)                      # /pratiche/...
    app.register_blueprint(auth_bp, url_prefix="/auth")      # /auth/...
    app.register_blueprint(studente_bp, url_prefix="/studente")
    app.register_blueprint(docente_bp, url_prefix="/docente")
    app.register_blueprint(ufficio_bp, url_prefix="/ufficio")

    _registra_pagine_errore(app)

    # La cartella degli upload deve esistere, altrimenti il primo
    # caricamento fallisce con un errore di sistema poco comprensibile.
    app.config["UPLOAD_FOLDER"].mkdir(parents=True, exist_ok=True)

    return app


def _registra_pagine_errore(app: Flask) -> None:
    """Pagine di errore uniformi, invece della schermata grezza di Flask."""

    @app.errorhandler(401)
    def non_autenticato(_):
        # Non dovrebbe quasi mai comparire: @login_required intercetta prima
        # e manda alla pagina di accesso. Resta come rete di sicurezza per le
        # rotte protette solo da @ruolo_richiesto.
        return render_template(
            "errore.html", codice=401,
            messaggio="Devi accedere per usare questa funzione."
        ), 401

    @app.errorhandler(403)
    def accesso_negato(_):
        return render_template(
            "errore.html", codice=403,
            messaggio="Non hai i permessi per accedere a questa pagina."
        ), 403

    @app.errorhandler(404)
    def non_trovato(_):
        return render_template(
            "errore.html", codice=404,
            messaggio="La pagina o la risorsa che cerchi non esiste."
        ), 404

    @app.errorhandler(500)
    def errore_interno(_):
        from app.extensions import db

        # Fondamentale: una transazione lasciata a meta' va sempre annullata,
        # altrimenti la sessione resta inutilizzabile per tutta la richiesta e
        # ogni query successiva fallisce con un errore che non c'entra niente.
        db.session.rollback()
        return render_template(
            "errore.html", codice=500,
            messaggio="Si e' verificato un errore interno."
        ), 500