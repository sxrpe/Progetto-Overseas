# Elenco di valori costanti ammessi per le colonne.


class Ruolo:
    # I tre tipi di utente

    STUDENTE = "STUDENTE"
    DOCENTE = "DOCENTE"
    UFFICIO = "UFFICIO"

    # Elenco completo dei ruoli per i cicli
    TUTTI = (STUDENTE, DOCENTE, UFFICIO)


class Periodo:
    # Periodi previsti per la mobilità

    PRIMO_SEMESTRE = "PRIMO_SEMESTRE"
    SECONDO_SEMESTRE = "SECONDO_SEMESTRE"
    INTERO_ANNO = "INTERO_ANNO"

    TUTTI = (PRIMO_SEMESTRE, SECONDO_SEMESTRE, INTERO_ANNO)

    # Come vengono visualizzati a video
    ETICHETTE = {
        PRIMO_SEMESTRE: "Primo semestre",
        SECONDO_SEMESTRE: "Secondo semestre",
        INTERO_ANNO: "Intero anno",
    }


class StatoPratica:
    # Gli stati del ciclo di vita della pratica.

    APERTA = "APERTA"
    ATTESA_APPROVAZIONE_LA = "ATTESA_APPROVAZIONE_LA"
    PRE_PARTENZA_COMPLETATA = "PRE_PARTENZA_COMPLETATA"
    MOBILITA_IN_CORSO = "MOBILITA_IN_CORSO"
    IN_RICONOSCIMENTO_ESAMI = "IN_RICONOSCIMENTO_ESAMI"
    CHIUSA = "CHIUSA"

    TUTTI = (
        APERTA,
        ATTESA_APPROVAZIONE_LA,
        PRE_PARTENZA_COMPLETATA,
        MOBILITA_IN_CORSO,
        IN_RICONOSCIMENTO_ESAMI,
        CHIUSA,
    )

    ETICHETTE = {
        APERTA: "Aperta",
        ATTESA_APPROVAZIONE_LA: "In attesa di approvazione del LA",
        PRE_PARTENZA_COMPLETATA: "Pre-partenza completata",
        MOBILITA_IN_CORSO: "Mobilita' in corso",
        IN_RICONOSCIMENTO_ESAMI: "In riconoscimento esami",
        CHIUSA: "Chiusa",
    }

    # Colori Bootstrap per le etichette colorate nell'interfaccia.
    COLORI = {
        APERTA: "secondary",
        ATTESA_APPROVAZIONE_LA: "warning",
        PRE_PARTENZA_COMPLETATA: "info",
        MOBILITA_IN_CORSO: "primary",
        IN_RICONOSCIMENTO_ESAMI: "warning",
        CHIUSA: "success",
    }


class EsitoDocumento:
    # Esito della valutazione del LA da parte del docente.

    IN_ATTESA = "IN_ATTESA"
    APPROVATO = "APPROVATO"
    RIFIUTATO = "RIFIUTATO"

    TUTTI = (IN_ATTESA, APPROVATO, RIFIUTATO)

    ETICHETTE = {
        IN_ATTESA: "In attesa",
        APPROVATO: "Approvato",
        RIFIUTATO: "Rifiutato",
    }

    COLORI = {
        IN_ATTESA: "warning",
        APPROVATO: "success",
        RIFIUTATO: "danger",
    }


class EsitoRiconoscimento:
    """
    Esito del riconoscimento di un singolo esame sostenuto all'estero.

    NON_VALUTATO è il valore iniziale, non l'assenza di valore.
    Per chiudere, nessun esame registrato deve restare NON_VALUTATO.
    """

    NON_VALUTATO = "NON_VALUTATO"
    ACCETTATO = "ACCETTATO"
    RIFIUTATO = "RIFIUTATO"

    TUTTI = (NON_VALUTATO, ACCETTATO, RIFIUTATO)

    ETICHETTE = {
        NON_VALUTATO: "Da valutare",
        ACCETTATO: "Riconosciuto",
        RIFIUTATO: "Non riconosciuto",
    }

    COLORI = {
        NON_VALUTATO: "secondary",
        ACCETTATO: "success",
        RIFIUTATO: "danger",
    }
