"""Application factory: il montaggio dell'applicazione.

COSA FA QUESTO FILE
    La funzione create_app() prende i pezzi sparsi (configurazione, database,
    login, blueprint, pagine di errore) e li assembla in un'applicazione
    Flask funzionante.

PERCHE' UNA FUNZIONE E NON UNA VARIABILE GLOBALE
    Perche' cosi' puoi crearne piu' di una, con configurazioni diverse: una
    per lo sviluppo, una per la demo, una per i test automatici. E' lo schema
    raccomandato dalla documentazione di Flask.

L'ORDINE DELLE OPERAZIONI CONTA
    1. crea l'app e carica la configurazione
    2. collega le estensioni (db, login)
    3. IMPORTA i modelli  <- se salti questo, db.create_all() non crea niente
    4. definisce la user_loader di Flask-Login
    5. registra i blueprint
    6. registra le pagine di errore

QUANDO LO TOCCHI
    Fase 5 per scriverlo, poi ogni volta che aggiungi un blueprint.
"""

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
    # importate: se questa riga manca, i metadati restano vuoti e
    # "python -m scripts.init_db" crea zero tabelle senza dare errore.
    # ------------------------------------------------------------------
    from app import models  # noqa: F401

    # ------------------------------------------------------------------
    # FASE 6 — Flask-Login: da scommentare quando esiste il modello Utente.
    #
    # E' la callback che, partendo dall'identita' salvata nel cookie di
    # sessione, ricostruisce l'oggetto utente. Senza di questa, il login
    # "riesce" ma current_user resta anonimo.
    # ------------------------------------------------------------------
    #
    # from app.models import Utente
    #
    # @login_manager.user_loader
    # def carica_utente(id_utente: str) -> "Utente | None":
    #     return db.session.get(Utente, int(id_utente))

    # ------------------------------------------------------------------
    # Blueprint: un'area del sito per ogni gruppo di funzionalita'.
    # L'URL dice gia' chi puo' accedere: tutto cio' che sta sotto
    # /docente/ e' per i docenti.
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
        # altrimenti la sessione resta in uno stato inutilizzabile.
        db.session.rollback()
        return render_template(
            "errore.html", codice=500,
            messaggio="Si e' verificato un errore interno."
        ), 500
