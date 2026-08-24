"""Configurazione dell'applicazione.

COSA FA QUESTO FILE
    Legge le variabili dal file .env e le trasforma in una classe di
    configurazione che Flask sa usare. Nessuna password e nessuna chiave
    segreta e' scritta qui dentro: tutto arriva da .env, che non si versiona.

QUANDO LO TOCCHI
    Quando aggiungi una nuova impostazione (Fase 0 e poi raramente).

NON METTERE QUI
    Logica dell'applicazione. Questo file legge configurazione e basta.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Cartella radice del progetto, calcolata a partire da questo file.
# Serve per costruire percorsi assoluti: un percorso relativo cambia
# significato a seconda della cartella da cui lanci il programma.
BASE_DIR = Path(__file__).resolve().parent

# Carica le variabili dal file .env dentro os.environ.
load_dotenv(BASE_DIR / ".env")


class Config:
    """Impostazioni comuni a tutti gli ambienti."""

    # --- sicurezza ---------------------------------------------------------
    SECRET_KEY = os.environ.get("SECRET_KEY", "chiave-di-sviluppo-da-cambiare")

    # --- database ----------------------------------------------------------
    # Se DATABASE_URL non e' impostata si ripiega su SQLite, cosi' il progetto
    # parte comunque anche su una macchina senza PostgreSQL.
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{BASE_DIR / 'overseas.db'}"
    )

    # Deprecata e inutile: consuma memoria senza darci nulla.
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Stampa l'SQL generato quando nel .env c'e' SQL_ECHO=1.
    SQLALCHEMY_ECHO = os.environ.get("SQL_ECHO", "0") == "1"

    # pool_pre_ping verifica che la connessione sia ancora viva prima di
    # riusarla: evita l'errore che compare dopo un riavvio del database.
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    # --- upload dei documenti ----------------------------------------------
    UPLOAD_FOLDER = BASE_DIR / os.environ.get("UPLOAD_FOLDER", "uploads")
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_UPLOAD_MB", 10)) * 1024 * 1024
    ALLOWED_UPLOAD_EXTENSIONS = {".pdf"}


class DevConfig(Config):
    """Sviluppo: pagina di errore dettagliata e ricaricamento automatico."""

    DEBUG = True


class DemoConfig(Config):
    """Registrazione del video: niente pagine di debug nella demo."""

    DEBUG = False


CONFIGS = {"dev": DevConfig, "demo": DemoConfig}
