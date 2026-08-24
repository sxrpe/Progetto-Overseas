"""Area studente.  ->  Da scrivere in FASE 7 (punti 7.2, 7.3, 7.6, 7.8).

ROUTE PREVISTE
    GET  /studente/pratiche                     elenco delle PROPRIE pratiche
    GET  /studente/pratiche/nuova               form di creazione
    POST /studente/pratiche/nuova               creazione
    POST /studente/pratiche/<id>/esami          aggiunta riga di mapping
    POST /studente/pratiche/<id>/date           date effettive di arrivo/partenza
    POST /studente/pratiche/<id>/documenti      caricamento di un documento

LE DUE REGOLE DA NON VIOLARE MAI IN QUESTO FILE

    1. Il filtro sta NELLA QUERY, non nel template.
       Giusto:     .where(Pratica.studente_id == current_user.id)
       Sbagliato:  caricare tutto e poi nascondere le righe altrui in Jinja.
       La seconda non e' un filtro: e' una falla.

    2. Ogni route che riceve un <id> deve chiamare esigi_accesso().
       Senza, basta cambiare il numero nell'URL per leggere la pratica di un
       altro studente.

ATTENZIONE ALLE QUERY A CASCATA
    Se l'elenco carica 50 pratiche e il template legge pratica.istituto.nome,
    l'ORM esegue 51 query invece di 1. Si risolve chiedendo il caricamento
    anticipato:
        .options(selectinload(Pratica.istituto), selectinload(Pratica.docente))
    Per accorgertene: metti SQL_ECHO=1 nel .env e conta le righe che scorrono.
"""

from flask import Blueprint

studente_bp = Blueprint("studente", __name__)


# @studente_bp.route("/pratiche")
# @login_required
# @ruolo_richiesto(Ruolo.STUDENTE)
# def elenco_pratiche():
#     ...
