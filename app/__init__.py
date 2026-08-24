"""Application factory.

Creare l'applicazione dentro una funzione invece che come variabile globale
permette di istanziarla piu' volte con configurazioni diverse (sviluppo,
demo, test) e rende espliciti gli import: e' lo schema raccomandato da Flask.
"""

from flask import Flask, render_template

from config import CONFIGS, Config


def create_app(nome_config: str = "dev") -> Flask:
    app = Flask(__name__)
    app.config.from_object(CONFIGS.get(nome_config, Config))

    # Le estensioni sono importate qui dentro per evitare import circolari.
    from app.extensions import db, login_manager

    db.init_app(app)
    login_manager.init_app(app)

    # I modelli vanno importati prima di create_all(), altrimenti i metadati
    # sono vuoti e non viene creata nessuna tabella.
    from app import models  # noqa: F401
    from app.models import Utente

    @login_manager.user_loader
    def carica_utente(id_utente: str) -> Utente | None:
        """Trasforma l'identita' salvata in sessione in un oggetto Utente."""
        return db.session.get(Utente, int(id_utente))

    # Registrazione dei blueprint: un'area dell'applicazione per ogni ruolo.
    from app.blueprints.auth import auth_bp
    from app.blueprints.docente import docente_bp
    from app.blueprints.pratiche import pratiche_bp
    from app.blueprints.pubblico import pubblico_bp
    from app.blueprints.studente import studente_bp
    from app.blueprints.ufficio import ufficio_bp

    app.register_blueprint(pubblico_bp)
    app.register_blueprint(pratiche_bp)  # dettaglio condiviso dai tre ruoli
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(studente_bp, url_prefix="/studente")
    app.register_blueprint(docente_bp, url_prefix="/docente")
    app.register_blueprint(ufficio_bp, url_prefix="/ufficio")

    _registra_pagine_errore(app)

    # La cartella degli upload deve esistere, altrimenti il primo caricamento
    # fallisce con un errore poco chiaro.
    app.config["UPLOAD_FOLDER"].mkdir(parents=True, exist_ok=True)

    return app


def _registra_pagine_errore(app: Flask) -> None:
    @app.errorhandler(403)
    def accesso_negato(_):
        return render_template("errore.html", codice=403,
                               messaggio="Non hai i permessi per questa pagina."), 403

    @app.errorhandler(404)
    def non_trovato(_):
        return render_template("errore.html", codice=404,
                               messaggio="Pagina o risorsa inesistente."), 404

    @app.errorhandler(500)
    def errore_interno(_):
        from app.extensions import db

        # Una transazione lasciata a meta' va sempre annullata.
        db.session.rollback()
        return render_template("errore.html", codice=500,
                               messaggio="Si e' verificato un errore interno."), 500
