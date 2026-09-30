"""
DESCRIZIONE
    Definisce gli oggetti delle estensioni Flask ancora scollegati dall'app.
    Il collegamento avviene in create_app() con init_app().
    Stanno in un file a parte per evitare import circolari tra applicazione,
    modelli ed estensioni.
"""

from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base dichiarativa di SQLAlchemy 2.0, usata da tutti i modelli."""


# Punto di accesso al database: sessione, modelli e costruzione delle query.
db = SQLAlchemy(model_class=Base)

# Gestisce l'utente collegato nella sessione corrente.
login_manager = LoginManager()

# Pagina di destinazione se si apre una rotta protetta senza essere entrati.
login_manager.login_view = "auth.login"
login_manager.login_message = "Devi accedere per visualizzare questa pagina."
login_manager.login_message_category = "warning"
