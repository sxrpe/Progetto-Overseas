"""Area docente referente.  ->  Da scrivere in FASE 7 (punti 7.4, 7.7, 7.9).

ROUTE PREVISTE
    GET  /docente/pratiche                      pratiche di cui e' referente
    GET  /docente/valutazioni                   coda dei documenti in attesa
    POST /docente/documenti/<id>/decidi         approva o rifiuta un documento
    POST /docente/modifiche/<id>/decidi         approva o rifiuta una modifica
    POST /docente/esami/<id>/riconosci          riconosce un singolo esame

REGOLE DEL DOMINIO DA RISPETTARE
    - il docente vede SOLO le pratiche di cui e' referente
    - non puo' modificare i dati inseriti dallo studente, solo decidere
    - ogni rifiuto richiede una motivazione e registra la data
    - il riconoscimento e' PER SINGOLO ESAME, non per l'intera pratica:
      deve funzionare il caso misto, alcuni approvati e altri no

LA TRANSAZIONE
    Approvare un documento tocca due tabelle: il documento (esito, data,
    autore della decisione) e la pratica (nuovo stato). Le due scritture
    devono stare in UNA sola transazione, con un solo commit alla fine:

        try:
            documento.esito = ...
            documento.pratica.stato = ...
            db.session.commit()      # <- un solo commit
        except Exception:
            db.session.rollback()
            raise

    Non deve poter esistere un documento approvato su una pratica rimasta
    nello stato precedente.
"""

from flask import Blueprint

docente_bp = Blueprint("docente", __name__)
