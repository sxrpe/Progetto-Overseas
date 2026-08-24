"""Autorizzazione: controllo di ruolo e controllo di appartenenza.

Flask-Login gestisce l'AUTENTICAZIONE (chi sei). L'AUTORIZZAZIONE (cosa puoi
fare) va scritta a mano, ed e' interamente qui dentro cosi' da avere un solo
posto da controllare e da citare nella relazione.
"""

from functools import wraps

from flask import abort
from flask_login import current_user
from passlib.hash import pbkdf2_sha256

from app.enums import Ruolo, StatoPratica


# --- password --------------------------------------------------------------
def hash_password(password: str) -> str:
    return pbkdf2_sha256.hash(password)


def verifica_password(password: str, hash_memorizzato: str) -> bool:
    return pbkdf2_sha256.verify(password, hash_memorizzato)


# --- controllo di ruolo ----------------------------------------------------
def ruolo_richiesto(*ruoli: Ruolo):
    """Consente l'accesso alla route solo agli utenti con uno di questi ruoli.

    Va sempre applicato SOTTO @login_required, cosi' l'utente anonimo viene
    prima mandato al login e non riceve un 403 poco comprensibile.
    """

    def decoratore(vista):
        @wraps(vista)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated or not current_user.ha_ruolo(*ruoli):
                abort(403)
            return vista(*args, **kwargs)

        return wrapper

    return decoratore


# --- controllo di appartenenza --------------------------------------------
def puo_vedere_pratica(pratica) -> bool:
    """Lo studente vede le proprie, il docente quelle di cui e' referente,
    l'ufficio tutte."""
    if current_user.ruolo is Ruolo.UFFICIO:
        return True
    if current_user.ruolo is Ruolo.STUDENTE:
        return pratica.studente_id == current_user.id
    if current_user.ruolo is Ruolo.DOCENTE:
        return pratica.docente_id == current_user.id
    return False


def puo_modificare_pratica(pratica) -> bool:
    """Solo lo studente proprietario, e solo finche' la pratica non e' chiusa."""
    return (
        current_user.ruolo is Ruolo.STUDENTE
        and pratica.studente_id == current_user.id
        and pratica.stato is not StatoPratica.CHIUSA
    )


def esigi_accesso(pratica) -> None:
    """Interrompe la richiesta con 404 se l'utente non ha diritto di vedere.

    Si usa 404 e non 403 di proposito: un 403 confermerebbe che la pratica
    esiste, permettendo di enumerare gli identificatori altrui.
    """
    if not puo_vedere_pratica(pratica):
        abort(404)
