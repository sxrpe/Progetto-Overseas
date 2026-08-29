"""Istanze delle estensioni Flask.

COSA FA QUESTO FILE
    Crea gli oggetti delle estensioni VUOTI, senza collegarli a nessuna
    applicazione. Il collegamento avviene dopo, dentro create_app().

PERCHE' SEPARATO
    Per evitare gli import circolari. I modelli hanno bisogno di "db", ma se
    lo importassero dall'applicazione si creerebbe un anello:
        app  ->  models  ->  app  ->  models  ->  ...
    Mettendo "db" in un file a parte l'anello si spezza:
        app  ->  models  ->  extensions
        app  ->  extensions

QUANDO LO TOCCHI
    Quasi mai. Solo se aggiungi una nuova estensione Flask.
"""

from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Classe base dichiarativa, stile SQLAlchemy 2.0.

    Tutti i modelli erediteranno da qui (tramite db.Model). Usare una Base
    esplicita, invece del vecchio db.Model automatico, abilita le annotazioni
    di tipo Mapped[...] che permettono a SQLAlchemy di dedurre da sole se una
    colonna e' NOT NULL.
    """


# L'oggetto attraverso cui si parla al database.
#   db.session  -> la sessione, legata alla singola richiesta HTTP
#   db.Model    -> la classe base dei modelli
#   db.select() -> costruisce le query
db = SQLAlchemy(model_class=Base)

# L'oggetto che gestisce chi e' collegato.
login_manager = LoginManager()

# Dove mandare chi tenta di aprire una pagina protetta senza essere entrato (Inizializzo l'oggetto Login_manager)
login_manager.login_view = "auth.login"   # uguale a url_for('auth.login'): nome del blueprint, punto, nome della funzione.
login_manager.login_message = "Devi accedere per visualizzare questa pagina."
login_manager.login_message_category = "warning"
