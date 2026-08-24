"""Valori enumerati del dominio: stati, ruoli, periodi, tipi di documento.

COSA VA QUI
    Ogni insieme chiuso di valori. Lo stato di una pratica puo' essere solo
    uno di sei valori: non e' testo libero, quindi si definisce qui una volta
    sola e non si scrive mai a mano da nessun'altra parte.

PERCHE' IMPORTA
    Una stringa scritta a mano nel codice ("chiusa" in un file, "Chiusa" in un
    altro) e' un bug che il computer non segnala. Un Enum invece si sbaglia
    subito, al primo avvio.

QUANDO LO RIEMPI
    Fase 1 (quando definisci il ciclo di vita) e Fase 4 (quando li mappi sul
    database).

COME SI MAPPANO SUL DATABASE
    Con sa.Enum(..., native_enum=False), che genera una colonna VARCHAR piu'
    un vincolo CHECK sui valori ammessi. Vantaggio doppio: il vincolo esiste
    davvero nel database ed e' ispezionabile, e lo stesso codice funziona sia
    su PostgreSQL sia su SQLite.
"""

import enum

# ---------------------------------------------------------------------------
# ESEMPIO da completare in Fase 1. Cancella o adatta.
# ---------------------------------------------------------------------------
#
# class Ruolo(enum.Enum):
#     STUDENTE = "studente"
#     DOCENTE = "docente"
#     UFFICIO = "ufficio"
#
#
# class StatoPratica(enum.Enum):
#     CREATA = "creata"
#     ATTESA_LA = "attesa_approvazione_la"
#     PRE_PARTENZA_OK = "pre_partenza_completata"
#     IN_CORSO = "mobilita_in_corso"
#     IN_RICONOSCIMENTO = "in_riconoscimento_esami"
#     CHIUSA = "chiusa"
#
#
# # Il ciclo di vita della pratica come grafo: quali passaggi sono ammessi.
# # E' l'UNICA definizione: la useranno i controlli applicativi, i test e il
# # trigger scritto in SQL, che deve dire esattamente la stessa cosa.
# TRANSIZIONI_AMMESSE: dict[StatoPratica, set[StatoPratica]] = {
#     StatoPratica.CREATA: {StatoPratica.ATTESA_LA},
#     ...
# }
