"""
DESCRIZIONE
    Application factory: assembla configurazione, database, login,
    blueprint e pagine di errore in un'applicazione Flask pronta.
    Si chiama create_app così si possono avere ambienti diversi
    (dev, demo) senza oggetti globali sparsi.
"""

from flask import Flask, render_template

from config import CONFIGS, Config


def create_app(nome_config: str = "dev") -> Flask:
    """Monta e restituisce l'applicazione.

    L'ordine conta: prima la config, poi le estensioni,
    poi i modelli, poi login, template, blueprint e errori.
    """
    app = Flask(__name__)
    app.config.from_object(CONFIGS.get(nome_config, Config))

    # Import qui dentro, non in cima al file, per non riaprire
    # l'import circolare che extensions.py evita.
    from app.extensions import db, login_manager

    db.init_app(app)
    login_manager.init_app(app)

    # I modelli devono essere importati prima di create_all(), altrimenti
    # SQLAlchemy non conosce le tabelle e le crea in silenzio a zero.
    from app import models  # noqa: F401
    from app.models import Utente

    @login_manager.user_loader
    def carica_utente(id_utente: str):
        """Dal cookie firmato ricostruisce l'oggetto Utente a ogni richiesta."""
        return db.session.get(Utente, int(id_utente))

    # Enum disponibili in tutti i template, senza ripassarli a ogni render.
    from app.enums import (
        EsitoDocumento,
        EsitoRiconoscimento,
        Periodo,
        Ruolo,
        StatoPratica,
    )
    # Associazioni Enum = Oggetti jinja
    app.jinja_env.globals.update(
        Ruolo=Ruolo,
        Periodo=Periodo,
        StatoPratica=StatoPratica,
        EsitoDocumento=EsitoDocumento,
        EsitoRiconoscimento=EsitoRiconoscimento,
    )



    # Ogni blueprint porta le rotte di un'area del sito.
    from app.blueprints.auth import auth_bp
    from app.blueprints.docente import docente_bp
    from app.blueprints.pratiche import pratiche_bp
    from app.blueprints.istituti import istituti_bp
    from app.blueprints.pubblico import pubblico_bp
    from app.blueprints.studente import studente_bp
    from app.blueprints.ufficio import ufficio_bp

    # Il prefisso rende leggibile l'URL; i controlli di accesso stanno nelle rotte.
    app.register_blueprint(pubblico_bp)
    app.register_blueprint(pratiche_bp, url_prefix="/pratiche")
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(studente_bp, url_prefix="/studente")
    app.register_blueprint(docente_bp, url_prefix="/docente")
    app.register_blueprint(ufficio_bp, url_prefix="/ufficio")
    app.register_blueprint(istituti_bp, url_prefix="/ufficio")

    _registra_pagine_errore(app)

    # Senza questa cartella il primo upload di un documento andrebbe in errore.
    app.config["UPLOAD_FOLDER"].mkdir(parents=True, exist_ok=True)

    return app


def _registra_pagine_errore(app: Flask) -> None:
    """Collega le pagine di errore al posto della schermata grezza di Flask."""

    @app.errorhandler(401)
    def non_autenticato(_):
        # Nella pratica compare di rado, perché @login_required manda al login.
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

        # Se resta aperta una transazione fallita, le query successive
        # sulla stessa richiesta non funzionano più in modo affidabile.
        db.session.rollback()
        return render_template(
            "errore.html", codice=500,
            messaggio="Si e' verificato un errore interno."
        ), 500
