"""Valori enumerati del dominio.

Sono definiti come Enum di Python e mappati sul database con
sa.Enum(..., native_enum=False): SQLAlchemy genera una colonna VARCHAR con un
vincolo CHECK sui valori ammessi. Il vantaggio e' doppio:

  - il vincolo esiste davvero nel database, non solo nel codice Python;
  - resta portabile fra PostgreSQL e SQLite, senza tipi ENUM nativi.
"""

import enum


class Ruolo(enum.Enum):
    STUDENTE = "studente"
    DOCENTE = "docente"
    UFFICIO = "ufficio"


class Periodo(enum.Enum):
    PRIMO_SEMESTRE = "primo_semestre"
    SECONDO_SEMESTRE = "secondo_semestre"
    INTERO_ANNO = "intero_anno"


class StatoPratica(enum.Enum):
    CREATA = "creata"
    ATTESA_LA = "attesa_approvazione_la"
    PRE_PARTENZA_OK = "pre_partenza_completata"
    IN_CORSO = "mobilita_in_corso"
    IN_RICONOSCIMENTO = "in_riconoscimento_esami"
    CHIUSA = "chiusa"


class TipoDocumento(enum.Enum):
    LEARNING_AGREEMENT = "learning_agreement"
    TRANSCRIPT_OF_RECORDS = "transcript_of_records"


class Esito(enum.Enum):
    """Esito di una decisione presa dal docente referente."""

    IN_ATTESA = "in_attesa"
    APPROVATO = "approvato"
    RIFIUTATO = "rifiutato"


# Transizioni di stato ammesse: chiave = stato attuale, valore = stati raggiungibili.
# E' l'unica definizione del ciclo di vita della pratica: la usano sia il
# controllo applicativo sia i test.
TRANSIZIONI_AMMESSE: dict[StatoPratica, set[StatoPratica]] = {
    StatoPratica.CREATA: {StatoPratica.ATTESA_LA},
    StatoPratica.ATTESA_LA: {StatoPratica.CREATA, StatoPratica.PRE_PARTENZA_OK},
    StatoPratica.PRE_PARTENZA_OK: {StatoPratica.IN_CORSO},
    StatoPratica.IN_CORSO: {StatoPratica.IN_RICONOSCIMENTO},
    StatoPratica.IN_RICONOSCIMENTO: {StatoPratica.CHIUSA},
    StatoPratica.CHIUSA: set(),
}
