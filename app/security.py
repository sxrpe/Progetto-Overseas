"""Autorizzazione: chi puo' fare cosa.

LA DISTINZIONE DA AVERE CHIARA
    AUTENTICAZIONE = chi sei.        La gestisce Flask-Login.
    AUTORIZZAZIONE = cosa puoi fare. Non la gestisce nessuno: sta qui.

I DUE CONTROLLI, ENTRAMBI NECESSARI
    1. controllo di RUOLO
       "Questo tipo di utente puo' usare questa funzione?"
       Esempio: solo l'ufficio puo' chiudere una pratica.

    2. controllo di APPARTENENZA
       "Questo utente puo' toccare QUESTO oggetto?"
       Esempio: lo studente 12 puo' vedere la pratica 5 solo se e' sua.

    Il secondo e' quello che si dimentica piu' spesso ed e' il piu' grave:
    senza, basta cambiare il numero nell'URL per leggere i dati di un altro.
    Il primo da solo non protegge niente, perche' tutti gli studenti hanno
    lo stesso ruolo.

DOVE STANNO LE PASSWORD
    Non qui. I metodi imposta_password() e verifica_password() sono sulla
    classe Utente in models.py, perche' riguardano l'utente e non
    l'autorizzazione. Un posto solo per ogni cosa.

PERCHE' UN FILE A PARTE
    Quando scriverete la sezione della relazione sulle politiche di
    autorizzazione, il materiale e' gia' tutto raccolto qui.
"""

from functools import wraps

from flask import abort
from flask_login import current_user

from app.enums import Ruolo


# ===========================================================================
#  CONTROLLO DI RUOLO
# ===========================================================================

def ruolo_richiesto(*ruoli_ammessi: str):
    """Decoratore: consente la rotta solo agli utenti con uno di questi ruoli.

    Uso:

        @studente_bp.route("/pratiche")
        @login_required
        @ruolo_richiesto(Ruolo.STUDENTE)
        def elenco():
            ...

    L'ORDINE DEI DECORATORI CONTA. @login_required va SOPRA: cosi' chi non e'
    autenticato viene mandato alla pagina di login, invece di ricevere un 403
    che non gli dice cosa fare.

    COME FUNZIONA, VISTO CHE I DECORATORI CONFONDONO
        ruolo_richiesto(Ruolo.STUDENTE) non e' il decoratore: e' una funzione
        che RESTITUISCE il decoratore. Serve un livello in piu' perche' il
        decoratore deve ricordarsi quali ruoli accettare.

        Tre livelli, dall'esterno verso l'interno:
            ruolo_richiesto(...)  riceve i ruoli, restituisce decoratore
            decoratore(vista)     riceve la tua funzione, restituisce wrapper
            wrapper(...)          e' quello che Flask chiamera' davvero:
                                  controlla, e solo se passa chiama la tua

    @wraps(vista) copia nome e documentazione dalla funzione originale al
    wrapper. Senza, tutte le rotte si chiamerebbero "wrapper" e Flask andrebbe
    in confusione: url_for() usa proprio quel nome per costruire gli URL.
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


# ===========================================================================
#  CONTROLLO DI APPARTENENZA
# ===========================================================================

def puo_vedere_pratica(pratica) -> bool:
    """Chi ha diritto di LEGGERE questa pratica.

    Sono le tre regole del punto 1 dei requisiti funzionali:
        studente -> solo le proprie
        docente  -> solo quelle di cui e' referente
        ufficio  -> tutte

    Nessuna query: studente_id e docente_id sono colonne, sono gia' in
    memoria insieme alla pratica.
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
    """Interrompe la richiesta se l'utente non ha diritto di vedere.

    PERCHE' 404 E NON 403
        Un 403 direbbe "questa pratica esiste ma non e' tua". Provando gli
        identificatori uno per uno si scoprirebbe quante pratiche ci sono e
        quali numeri sono in uso. Il 404 non distingue fra "non esiste" e
        "non e' tua", e non lascia trapelare niente.

    Si usa cosi', come prima riga dopo aver caricato la pratica:

        pratica = db.session.get(Pratica, id) or abort(404)
        esigi_accesso(pratica)
    """
    if not puo_vedere_pratica(pratica):
        abort(404)


def puo_modificare_pratica(pratica) -> bool:
    """Chi ha diritto di MODIFICARE il contenuto di questa pratica.

    Piu' stretto della lettura: e' solo lo studente titolare, e solo finche'
    la pratica non e' chiusa. Il docente e l'ufficio leggono e prendono
    decisioni, ma non compilano il piano al posto dello studente.

    ATTENZIONE: questo e' il livello applicativo, non l'ultima parola. Le
    condizioni sostanziali (in quale stato si puo' fare cosa) le riverifica
    il database con i trigger, e valgono anche per chi scrive senza passare
    di qui.
    """
    if not current_user.is_authenticated:
        return False
    if current_user.ruolo != Ruolo.STUDENTE:
        return False
    if pratica.studente_id != current_user.id:
        return False
    return pratica.stato != "CHIUSA"


def esigi_modifica(pratica) -> None:
    """Come esigi_accesso, ma per le operazioni di scrittura.

    Qui il 403 e' corretto: l'utente sta gia' guardando la pratica, quindi
    sa che esiste. Non c'e' niente da nascondere, e un messaggio chiaro gli
    dice perche' non puo' procedere.
    """
    if not puo_modificare_pratica(pratica):
        abort(403)