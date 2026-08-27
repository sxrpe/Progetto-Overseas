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
"""I valori ammessi per le colonne "a scelta fissa".

COS'E' QUESTO FILE
    Un elenco di costanti. Niente di piu'.

    Il ruolo di un utente puo' essere solo STUDENTE, DOCENTE o UFFICIO.
    Invece di scrivere la stringa "STUDENTE" a mano in venti punti del
    programma, la scriviamo una volta qui e poi usiamo Ruolo.STUDENTE.

PERCHE' NON BASTA SCRIVERE LA STRINGA OGNI VOLTA
    Perche' un refuso in una stringa non da' errore. Se scrivi

        if utente.ruolo == "STUEDNTE":

    Python non protesta: confronta due stringhe diverse e risponde False.
    Il programma non si rompe, semplicemente non funziona, e tu passi un'ora
    a cercare il perche'.

    Con la costante:

        if utente.ruolo == Ruolo.STUEDNTE:

    Python dice subito "AttributeError: STUEDNTE", e in PyCharm il nome e'
    gia' sottolineato in rosso mentre lo scrivi.

COME FINISCONO NEL DATABASE
    Come normalissime colonne di testo (VARCHAR), accompagnate da un vincolo
    CHECK che elenca i valori ammessi. In models.py il CHECK e' scritto per
    esteso, cosi':

        sa.CheckConstraint(
            "ruolo IN ('STUDENTE', 'DOCENTE', 'UFFICIO')",
            name="ck_utente_ruolo",
        )

    Il risultato nel CREATE TABLE e' esattamente quello che leggi, e lo puoi
    mostrare in sede d'esame senza dover spiegare cosa ha generato cosa.

    L'alternativa sarebbe il tipo ENUM nativo di PostgreSQL
    (CREATE TYPE ruolo AS ENUM (...)). Scartata perche' e' specifico di
    PostgreSQL, e perche' aggiungere un valore richiede una migrazione del
    tipo invece che una modifica del vincolo.

PERCHE' UNA CLASSE E NON DELLE VARIABILI SCIOLTE
    Solo per raggruppare. Queste classi non vengono mai istanziate: nessuno
    scrive Ruolo(). Servono come contenitore di nomi, in modo da poter
    scrivere Ruolo.STUDENTE e StatoPratica.APERTA senza confusione.
"""


class Ruolo:
    """I tre tipi di utente."""

    STUDENTE = "STUDENTE"
    DOCENTE = "DOCENTE"
    UFFICIO = "UFFICIO"

    # L'elenco completo, comodo quando serve ciclare su tutti i ruoli
    # (per esempio nel seed, o in un menu a tendina).
    TUTTI = (STUDENTE, DOCENTE, UFFICIO)


class Periodo:
    """Periodo previsto della mobilita'."""

    PRIMO_SEMESTRE = "PRIMO_SEMESTRE"
    SECONDO_SEMESTRE = "SECONDO_SEMESTRE"
    INTERO_ANNO = "INTERO_ANNO"

    TUTTI = (PRIMO_SEMESTRE, SECONDO_SEMESTRE, INTERO_ANNO)

    # Come si scrivono a video. La chiave e' il valore salvato nel database,
    # il testo e' quello che legge l'utente. Nei template:
    #     {{ Periodo.ETICHETTE[pratica.periodo] }}
    ETICHETTE = {
        PRIMO_SEMESTRE: "Primo semestre",
        SECONDO_SEMESTRE: "Secondo semestre",
        INTERO_ANNO: "Intero anno",
    }


class StatoPratica:
    """Gli stati del ciclo di vita della pratica.

    L'ordine in cui sono scritti qui e' quello in cui la pratica li
    attraversa, ma e' solo una comodita' di lettura: le transizioni
    effettivamente ammesse stanno nella tabella transizione_ammessa e le
    controlla un trigger.
    """

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
    """Esito della valutazione di un Learning Agreement da parte del docente."""

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
    """Esito del riconoscimento di un singolo esame sostenuto all'estero.

    NON_VALUTATO e' il valore iniziale, non l'assenza di valore: la colonna
    e' NOT NULL e parte da qui. La differenza conta, perche' la condizione di
    chiusura della pratica e' "nessun esame e' rimasto a NON_VALUTATO", e un
    confronto fra stringhe e' molto piu' semplice da scrivere e da
    indicizzare di un confronto con NULL.
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