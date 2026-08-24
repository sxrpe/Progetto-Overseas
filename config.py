"""Configurazione dell'applicazione, letta dalle variabili d'ambiente.

Nessun valore sensibile e' scritto qui dentro: tutto arriva dal file .env,
che non viene versionato. In questo modo lo stesso codice gira in sviluppo,
in test e in dimostrazione cambiando solo la configurazione.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


class Config:
    """Configurazione di base, condivisa da tutti gli ambienti."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "chiave-di-sviluppo-da-cambiare")

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{BASE_DIR / 'overseas.db'}"
    )
    # Disattivato: e' deprecato e consuma memoria senza darci nulla.
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Stampa l'SQL generato quando SQL_ECHO=1.
    SQLALCHEMY_ECHO = os.environ.get("SQL_ECHO", "0") == "1"
    # Verifica che la connessione sia viva prima di riusarla dal pool.
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    UPLOAD_FOLDER = BASE_DIR / os.environ.get("UPLOAD_FOLDER", "uploads")
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_UPLOAD_MB", 10)) * 1024 * 1024
    ALLOWED_UPLOAD_EXTENSIONS = {".pdf"}


class DevConfig(Config):
    DEBUG = True


class DemoConfig(Config):
    """Usata per la registrazione del video: niente debug in video."""

    DEBUG = False


CONFIGS = {"dev": DevConfig, "demo": DemoConfig}
