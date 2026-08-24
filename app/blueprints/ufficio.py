"""Area ufficio Overseas.  ->  Da scrivere in FASE 7 (punti 7.1, 7.5, 7.10).

ROUTE PREVISTE
    GET  /ufficio/pratiche                      TUTTE le pratiche, con filtri
    GET  /ufficio/istituti                      gestione degli istituti partner
    POST /ufficio/istituti                      inserimento o modifica
    POST /ufficio/pratiche/<id>/pre-partenza    registra la fase pre-partenza
    POST /ufficio/pratiche/<id>/chiudi          chiude la pratica
    GET  /ufficio/cruscotto                     statistiche (Fase 12)

I DUE CONTROLLI OBBLIGATORI DELLA TRACCIA
    - la fase pre-partenza si registra SOLO SE i dati essenziali ci sono
      e il Learning Agreement e' stato approvato dal docente
    - la pratica si chiude SOLO SE il Transcript of Records e' caricato
      e il riconoscimento degli esami e' completato

    Vanno verificati LATO SERVER, non solo nascondendo il pulsante nel
    template. Nascondere un comando non e' una misura di sicurezza: chiunque
    puo' inviare la richiesta a mano.

    Questi due controlli esistono anche come trigger nel database
    (schema_extra_postgres.sql). La duplicazione e' voluta: il controllo
    applicativo serve a dare un messaggio comprensibile, il trigger serve a
    garantire che la regola valga comunque, anche per chi scrive in SQL.
    Va dichiarata e motivata nella relazione.

NOTA SUL RUOLO
    L'ufficio verifica la completezza amministrativa. Non entra nel merito
    delle approvazioni didattiche, che restano al docente.
"""

from flask import Blueprint

ufficio_bp = Blueprint("ufficio", __name__)
