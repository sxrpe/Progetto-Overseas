"""
DESCRIZIONE
    Regole di autorizzazione: chi può fare cosa su una pratica.
    L'autenticazione (chi sei) la gestisce Flask-Login; qui resta
    solo il permesso di accesso e di modifica.
"""

from functools import wraps

from flask import abort
from flask_login import current_user

from app.enums import Ruolo


def ruolo_richiesto(*ruoli_ammessi: str):
    """Consente la rotta solo agli utenti con uno dei ruoli indicati.

    Si usa così, con @login_required sopra, così chi non è entrato
    viene mandato al login invece di ricevere un 403:

        @login_required
        @ruolo_richiesto(Ruolo.STUDENTE)
        def elenco():


    ruolo_richiesto() restituisce il decoratore.
    """

    def decoratore(vista):
        @wraps(vista)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            if current_user.ruolo not in ruoli_ammessi:
                abort(403)
            return vista(*args, **kwargs)

        return wrapper

    return decoratore


def puo_vedere_pratica(pratica) -> bool:
    """True se l'utente corrente può leggere questa pratica.

    Studente solo le proprie, docente solo quelle di cui è referente,
    ufficio tutte. Non serve una query in più: gli id sono già sulla pratica.
    """
    if not current_user.is_authenticated:
        return False
    if current_user.ruolo == Ruolo.UFFICIO:
        return True
    if current_user.ruolo == Ruolo.STUDENTE:
        return pratica.studente_id == current_user.id
    if current_user.ruolo == Ruolo.DOCENTE:
        return pratica.docente_id == current_user.id
    return False


def esigi_accesso(pratica) -> None:
    """Interrompe la richiesta se l'utente non può vedere la pratica.

    Si risponde 404 e non 403 cosi non si distingue se non ce una risorsa, oppure se non é di tua competenza

        pratica = db.session.get(Pratica, id) or abort(404)
        esigi_accesso(pratica)
    """
    if not puo_vedere_pratica(pratica):
        abort(404)


def puo_modificare_pratica(pratica) -> bool:
    """True se lo studente titolare può ancora scrivere sulla pratica.

    Docente e ufficio leggono e decidono, ma non compilano il piano al
    posto suo. Una pratica chiusa non è più modificabile da qui.

    """
    if not current_user.is_authenticated:
        return False
    if current_user.ruolo != Ruolo.STUDENTE:
        return False
    if pratica.studente_id != current_user.id:
        return False
    return pratica.stato != "CHIUSA"
    # dopo aver controllato che sei lo studente titolare, la modifica è ammessa solo se la pratica non è chiusa.


def esigi_modifica(pratica) -> None:
    """Come esigi_accesso, ma per le scritture.

    Qui il 403 va bene l'utente sta già guardando la pratica e sa che esiste.
    """
    if not puo_modificare_pratica(pratica):
        abort(403)
