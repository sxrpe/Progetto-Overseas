"""
DESCRIZIONE
    Legge il file .env e lo traduce in classi di configurazione per Flask.
    Non contiene logica applicativa, solo impostazioni.
    Chiavi e password restano nel .env, fuori dal repository.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Cartella radice del progetto, usata per costruire percorsi assoluti.
BASE_DIR = Path(__file__).resolve().parent

# Carica le variabili del .env in os.environ.
load_dotenv(BASE_DIR / ".env")


class Config:
    """Impostazioni comuni a tutti gli ambienti."""

    # Firma i cookie di sessione, così il login resta certificato.
    SECRET_KEY = os.environ.get("SECRET_KEY", "chiave-di-sviluppo-da-cambiare")

    # Indirizzo del database. Se manca DATABASE_URL si usa un SQLite locale.
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{BASE_DIR / 'overseas.db'}"
    )

    # Opzione deprecata di SQLAlchemy, lasciata disattivata.
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Con SQL_ECHO=1 l'applicazione stampa l'SQL generato in console.
    SQLALCHEMY_ECHO = os.environ.get("SQL_ECHO", "0") == "1"

    # Prima di riusare una connessione controlla che sia ancora disponibile.
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    # Cartella, dimensione massima ed estensioni ammesse per i documenti.
    UPLOAD_FOLDER = BASE_DIR / os.environ.get("UPLOAD_FOLDER", "uploads")
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_UPLOAD_MB", 10)) * 1024 * 1024
    ALLOWED_UPLOAD_EXTENSIONS = {".pdf"}



# CLASSI DI DEBUG
class DevConfig(Config):
    """Ambiente di sviluppo, con messaggi di errore dettagliati."""
    DEBUG = True


class DemoConfig(Config):
    """Ambiente per la presentazione.

    In sviluppo DEBUG mostra a schermo lo stack trace completo quando qualcosa
    va storto.
    Si attiva mettendo create_app("demo") al posto di create_app("dev") in
    wsgi.py. Database, upload e secret key restano quelli di Config: cambia
    solo questo comportamento a schermo.
    """
    DEBUG = False


# create_app("dev") usa DevConfig, create_app("demo") usa DemoConfig.
CONFIGS = {"dev": DevConfig, "demo": DemoConfig}
