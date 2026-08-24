"""Autorizzazione: chi puo' fare cosa. E hashing delle password.

LA DISTINZIONE CHE DEVI AVERE CHIARA
    AUTENTICAZIONE = chi sei.        La gestisce Flask-Login.
    AUTORIZZAZIONE = cosa puoi fare. NON la gestisce nessuno: la scrivi qui.

I DUE CONTROLLI, ENTRAMBI NECESSARI
    1. controllo di RUOLO
       "Questo tipo di utente puo' usare questa funzione?"
       Esempio: solo l'ufficio puo' chiudere una pratica.

    2. controllo di APPARTENENZA
       "Questo specifico utente puo' toccare questo specifico oggetto?"
       Esempio: lo studente 12 puo' vedere la pratica 5 solo se e' sua.

    Il secondo e' quello che si dimentica piu' spesso ed e' il piu' grave:
    senza, basta cambiare il numero nell'URL per leggere i dati di un altro.

QUANDO LO RIEMPI
    Fase 6, prima di scrivere qualunque funzionalita'.

TENERE TUTTO IN QUESTO FILE ha un vantaggio pratico: quando scriverai la
sezione della relazione sulle politiche di autorizzazione, il materiale e'
gia' tutto in un posto solo.
"""

from functools import wraps

from flask import abort
from flask_login import current_user
from passlib.hash import pbkdf2_sha256


# ---------------------------------------------------------------------------
# PASSWORD
# Le password non si memorizzano mai in chiaro, nemmeno nei dati di prova.
# ---------------------------------------------------------------------------
def hash_password(password: str) -> str:
    """Trasforma una password in un hash da salvare nel database."""
    return pbkdf2_sha256.hash(password)


def verifica_password(password: str, hash_memorizzato: str) -> bool:
    """Controlla se una password corrisponde all'hash salvato."""
    return pbkdf2_sha256.verify(password, hash_memorizzato)


# ---------------------------------------------------------------------------
# CONTROLLO DI RUOLO
# ---------------------------------------------------------------------------
def ruolo_richiesto(*ruoli):
    """Decoratore: consente la route solo agli utenti con uno di questi ruoli.

    Va messo SEMPRE SOTTO @login_required, cosi' l'utente non autenticato
    viene prima mandato al login invece di ricevere un 403 incomprensibile:

        @studente_bp.route("/pratiche")
        @login_required
        @ruolo_richiesto(Ruolo.STUDENTE)
        def elenco_pratiche():
            ...
    """

    def decoratore(vista):
        @wraps(vista)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated or current_user.ruolo not in ruoli:
                abort(403)
            return vista(*args, **kwargs)

        return wrapper

    return decoratore


# ---------------------------------------------------------------------------
# CONTROLLO DI APPARTENENZA
# Da completare in Fase 6, quando esistono i modelli.
# ---------------------------------------------------------------------------
#
# def puo_vedere_pratica(pratica) -> bool:
#     """Studente: solo le sue. Docente: quelle di cui e' referente.
#     Ufficio: tutte."""
#     ...
#
#
# def esigi_accesso(pratica) -> None:
#     """Interrompe la richiesta se l'utente non ha diritto di vedere.
#
#     Si usa 404 e non 403 di proposito: un 403 confermerebbe che la pratica
#     esiste, permettendo di scoprire gli identificatori altrui provandoli
#     uno per uno.
#     """
#     if not puo_vedere_pratica(pratica):
#         abort(404)
