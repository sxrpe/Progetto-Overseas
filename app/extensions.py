"""Istanze delle estensioni Flask.

Sono create qui, vuote e senza applicazione, e collegate all'app dentro la
factory create_app(). Questo evita gli import circolari: i modelli importano
"db" da questo modulo senza dover importare l'applicazione.
"""

from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Classe base dichiarativa in stile SQLAlchemy 2.0.

    Usarla al posto del vecchio db.Model automatico rende esplicito che i
    modelli sono normali classi mappate e abilita l'annotazione dei tipi.
    """


db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "Devi accedere per visualizzare questa pagina."
login_manager.login_message_category = "warning"
