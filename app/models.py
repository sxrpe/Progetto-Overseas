"""Schema logico tradotto in modelli SQLAlchemy.

COME LEGGERE QUESTO FILE
    Ogni classe e' una tabella. Ogni Mapped[...] e' una colonna.
    Ogni relationship() NON e' una colonna: e' la scorciatoia Python che
    percorre una chiave esterna al posto tuo.

    In fondo a ogni classe c'e' __table_args__, che contiene i vincoli a
    livello di tabella: UNIQUE, CHECK, indici. Quelli sono la parte
    interessante per l'esame, non gli attributi.

CONVENZIONI ADOTTATE
    - chiave primaria surrogata "id" ovunque, anche nelle entita' deboli:
      la chiave concettuale composta diventa un vincolo UNIQUE. Scelta
      implementativa, dichiarata in relazione.
    - tutte le date sono Date e non DateTime. Confrontare un timestamp con
      una data in un CHECK ("verificata alle 14:00 <= partita il giorno
      stesso") darebbe falsi negativi. L'unica eccezione e' lo storico.
    - gli enum diventano VARCHAR + CHECK, non tipi nativi PostgreSQL.

QUELLO CHE QUI NON C'E'
    I trigger e le viste. Non sono esprimibili con l'ORM e stanno in
    scripts/schema_extra_postgres.sql, eseguito da init_db subito dopo
    create_all(). Ogni vincolo che vive li' e' segnalato nei commenti con
    la sigla [SQL].
"""

from __future__ import annotations

import datetime as dt

import sqlalchemy as sa
from flask_login import UserMixin
from sqlalchemy.orm import Mapped, mapped_column, relationship
from werkzeug.security import check_password_hash, generate_password_hash

from app.enums import (
    EsitoDocumento,
    EsitoRiconoscimento,
    Periodo,
    Ruolo,
    StatoPratica,
    STATI_DOPO_PARTENZA,
    STATI_DOPO_PRE_PARTENZA,
    STATI_DOPO_RIENTRO,
    valori,
)
from app.extensions import db


# ---------------------------------------------------------------------------
# Piccoli aiuti per scrivere i vincoli in modo leggibile
# ---------------------------------------------------------------------------

def _enum(enum_class, nome: str) -> sa.Enum:
    """VARCHAR + CHECK invece del tipo ENUM nativo. Vedi app/enums.py."""
    return sa.Enum(
        enum_class,
        name=nome,
        native_enum=False,
        values_callable=valori,
        validate_strings=True,
    )


def _elenco(stati) -> str:
    """Formatta una tupla di enum come lista SQL: 'A', 'B', 'C'."""
    return ", ".join(f"'{s.value}'" for s in stati)


def _ordine(prima: str, dopo: str) -> str:
    """Vincolo di ordinamento temporale tollerante ai NULL.

    Scritto ingenuamente come "prima <= dopo", il confronto sarebbe NULL
    (quindi non violato ma nemmeno utile) appena una delle due date manca.
    La forma esplicita rende chiaro nel DDL che i NULL sono ammessi.
    """
    return f"{prima} IS NULL OR {dopo} IS NULL OR {prima} <= {dopo}"


def _implica(condizione: str, conseguenza: str) -> str:
    """Implicazione logica: se vale la condizione, deve valere la conseguenza.

    In SQL non esiste l'operatore di implicazione: A -> B si scrive
    NOT A OR B.
    """
    return f"NOT ({condizione}) OR ({conseguenza})"


def _insieme_nullo(*colonne: str) -> str:
    """Le colonne sono tutte nulle oppure tutte valorizzate.

    Nasce dalla traduzione delle relazioni (0,1): una relazione o c'e' tutta
    o non c'e', quindi chiave esterna e attributo devono comparire insieme.
    Nel modello concettuale non serviva scriverlo.
    """
    prima, *resto = colonne
    pezzi = [f"({prima} IS NULL) = ({altra} IS NULL)" for altra in resto]
    return " AND ".join(pezzi)


# ---------------------------------------------------------------------------
# UTENTE
# ---------------------------------------------------------------------------

class Utente(UserMixin, db.Model):
    """Collasso della generalizzazione Utente / Studente / Docente / Ufficio.

    TRADUZIONE
        Nel concettuale erano un padre e tre figli. Qui sono una sola tabella
        con un discriminatore "ruolo" e gli attributi specifici resi
        nullabili (solo "matricola", in questo caso).

    COSA SI PERDE
        Le relazioni del concettuale puntavano al sottotipo giusto: la
        referenza andava a Docente, non a Utente. Dopo il collasso tutte le
        chiavi esterne puntano a "utente" e nulla impedisce di mettere uno
        studente come docente referente.
        [SQL] Il trigger trg_ruoli_pratica ripristina quella garanzia.

    PERCHE' UserMixin
        Flask-Login pretende che l'oggetto utente sappia rispondere a
        is_authenticated, get_id() e poco altro. UserMixin fornisce
        implementazioni ragionevoli di tutto, gratis.
    """

    __tablename__ = "utente"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(sa.String(120), nullable=False)
    password_hash: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    nome: Mapped[str] = mapped_column(sa.String(80), nullable=False)
    cognome: Mapped[str] = mapped_column(sa.String(80), nullable=False)
    ruolo: Mapped[Ruolo] = mapped_column(_enum(Ruolo, "ruolo"), nullable=False)

    # Nullabile perche' appartiene al solo sottotipo Studente.
    matricola: Mapped[str | None] = mapped_column(sa.String(20))

    # --- relazioni (nessuna colonna: sono viste sulle chiavi esterne) ------
    # foreign_keys e' obbligatorio: pratica ha QUATTRO chiavi esterne verso
    # utente, e senza indicazione esplicita SQLAlchemy non sa quale usare.
    pratiche_come_studente: Mapped[list[Pratica]] = relationship(
        back_populates="studente",
        foreign_keys="Pratica.studente_id",
    )
    pratiche_come_referente: Mapped[list[Pratica]] = relationship(
        back_populates="docente",
        foreign_keys="Pratica.docente_id",
    )

    __table_args__ = (
        # U1 - identificatore dell'entita' nel modello concettuale.
        sa.UniqueConstraint("email", name="uq_utente_email"),
        # U2 - in PostgreSQL un UNIQUE ammette piu' NULL, quindi questo
        # vincolo non disturba docenti e personale d'ufficio.
        sa.UniqueConstraint("matricola", name="uq_utente_matricola"),
        # C19 - la matricola esiste se e solo se l'utente e' uno studente.
        # E' la traccia lasciata dal collasso della generalizzazione: nel
        # concettuale l'attributo stava sul solo sottotipo e non serviva
        # nessun vincolo.
        sa.CheckConstraint(
            f"(ruolo = '{Ruolo.STUDENTE.value}') = (matricola IS NOT NULL)",
            name="ck_utente_matricola_solo_studenti",
        ),
        sa.CheckConstraint("length(trim(email)) > 0", name="ck_utente_email_non_vuota"),
    )

    # --- password ---------------------------------------------------------
    # La password in chiaro non entra mai nel database. generate_password_hash
    # applica una funzione di hash lenta e con sale: due utenti con la stessa
    # password producono hash diversi, e provare tutte le password a forza
    # bruta costa tempo macchina.

    def imposta_password(self, in_chiaro: str) -> None:
        self.password_hash = generate_password_hash(in_chiaro)

    def verifica_password(self, in_chiaro: str) -> bool:
        return check_password_hash(self.password_hash, in_chiaro)

    # --- comodita' per i template ------------------------------------------
    @property
    def e_studente(self) -> bool:
        return self.ruolo == Ruolo.STUDENTE

    @property
    def e_docente(self) -> bool:
        return self.ruolo == Ruolo.DOCENTE

    @property
    def e_ufficio(self) -> bool:
        return self.ruolo == Ruolo.UFFICIO

    @property
    def nome_completo(self) -> str:
        return f"{self.nome} {self.cognome}"

    def __repr__(self) -> str:
        return f"<Utente {self.email} ({self.ruolo.value})>"


# ---------------------------------------------------------------------------
# ISTITUTO OSPITANTE
# ---------------------------------------------------------------------------

class Istituto(db.Model):
    """Catalogo degli atenei partner, gestito dall'ufficio Overseas.

    Entita' forte: lo studente sceglie da questa lista, non digita il nome.
    E' la traccia a richiederlo esplicitamente.
    """

    __tablename__ = "istituto"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(sa.String(160), nullable=False)
    paese: Mapped[str] = mapped_column(sa.String(80), nullable=False)
    citta: Mapped[str] = mapped_column(sa.String(80), nullable=False)

    pratiche: Mapped[list[Pratica]] = relationship(back_populates="istituto")

    __table_args__ = (
        # Il nome da solo non basta: atenei omonimi in paesi diversi esistono.
        sa.UniqueConstraint("nome", "citta", name="uq_istituto_nome_citta"),
    )

    def __repr__(self) -> str:
        return f"<Istituto {self.nome} ({self.citta})>"


# ---------------------------------------------------------------------------
# CORSO INTERNO
# ---------------------------------------------------------------------------

class CorsoInterno(db.Model):
    """Catalogo degli insegnamenti di Ca' Foscari.

    PERCHE' QUI IL CATALOGO C'E' E PER I CORSI ESTERI NO
        Il codice lo assegna l'ateneo, che e' la stessa organizzazione che
        ospita l'applicazione: e' stabile e univoco, quindi la dipendenza
        funzionale codice -> titolo, crediti vale davvero. Ripetere titolo e
        crediti su ogni riconoscimento sarebbe ridondanza, con il rischio che
        lo stesso insegnamento risulti riconosciuto con crediti diversi in
        pratiche diverse.
        Sui corsi esteri quella dipendenza non vale, e infatti la' non c'e'
        catalogo. La differenza di trattamento e' motivata dalla presenza o
        assenza della dipendenza funzionale, non dallo stile.
    """

    __tablename__ = "corso_interno"

    id: Mapped[int] = mapped_column(primary_key=True)
    codice: Mapped[str] = mapped_column(sa.String(20), nullable=False)
    titolo: Mapped[str] = mapped_column(sa.String(200), nullable=False)
    crediti: Mapped[int] = mapped_column(sa.Integer, nullable=False)

    equivalenze: Mapped[list[Equivalenza]] = relationship(
        back_populates="corso_interno",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        sa.UniqueConstraint("codice", name="uq_corso_interno_codice"),
        sa.CheckConstraint("crediti > 0", name="ck_corso_interno_crediti_positivi"),
        sa.CheckConstraint(
            "length(trim(titolo)) > 0", name="ck_corso_interno_titolo_non_vuoto"
        ),
    )

    def __repr__(self) -> str:
        return f"<CorsoInterno {self.codice}>"


# ---------------------------------------------------------------------------
# PRATICA
# ---------------------------------------------------------------------------

class Pratica(db.Model):
    """L'entita' centrale: una mobilita' dalla creazione alla chiusura.

    LE QUATTRO CHIAVI ESTERNE VERSO UTENTE
        studente_id      relazione "apertura", con data_apertura come suo
                         attributo. E' anche la relazione di titolarita':
                         chi apre la pratica ne e' il proprietario, quindi
                         una relazione sola e non due.
        docente_id       relazione "referenza", senza attributi.
        verificata_da_id relazione "verifica pre-partenza", (0,1).
        chiusa_da_id     relazione "chiusura", (0,1).

        Le ultime due, avendo cardinalita' massima 1 dal lato pratica, non
        diventano tabelle: collassano in colonne. Da qui i vincoli di
        coerenza a coppie qui sotto, che nel concettuale non esistevano.

    LE DUE DATE CHE NON SONO ATTRIBUTI DI RELAZIONE
        data_inizio_effettivo e data_fine_effettiva sono fatti sulla
        mobilita' dichiarati dallo studente, non atti amministrativi
        compiuti da qualcuno. Per questo stanno sull'entita'.
    """

    __tablename__ = "pratica"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Identificatore del modello concettuale, qui affiancato al surrogato.
    codice_pratica: Mapped[str] = mapped_column(sa.String(20), nullable=False)

    anno_accademico: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    periodo: Mapped[Periodo] = mapped_column(_enum(Periodo, "periodo"), nullable=False)
    stato: Mapped[StatoPratica] = mapped_column(
        _enum(StatoPratica, "stato_pratica"),
        nullable=False,
        default=StatoPratica.APERTA,
    )

    # --- apertura (studente) ----------------------------------------------
    studente_id: Mapped[int] = mapped_column(
        sa.ForeignKey("utente.id", ondelete="RESTRICT"), nullable=False
    )
    data_apertura: Mapped[dt.date] = mapped_column(
        sa.Date, nullable=False, default=dt.date.today
    )

    # --- referenza (docente) ----------------------------------------------
    docente_id: Mapped[int] = mapped_column(
        sa.ForeignKey("utente.id", ondelete="RESTRICT"), nullable=False
    )

    # --- destinazione ------------------------------------------------------
    istituto_id: Mapped[int] = mapped_column(
        sa.ForeignKey("istituto.id", ondelete="RESTRICT"), nullable=False
    )

    # --- verifica pre-partenza (ufficio) ----------------------------------
    verificata_da_id: Mapped[int | None] = mapped_column(
        sa.ForeignKey("utente.id", ondelete="RESTRICT")
    )
    pre_partenza_verificata_il: Mapped[dt.date | None] = mapped_column(sa.Date)

    # --- fatti sulla mobilita' (studente) ---------------------------------
    data_inizio_effettivo: Mapped[dt.date | None] = mapped_column(sa.Date)
    data_fine_effettiva: Mapped[dt.date | None] = mapped_column(sa.Date)

    # --- chiusura (ufficio) ------------------------------------------------
    chiusa_da_id: Mapped[int | None] = mapped_column(
        sa.ForeignKey("utente.id", ondelete="RESTRICT")
    )
    chiusa_il: Mapped[dt.date | None] = mapped_column(sa.Date)

    # --- relazioni ---------------------------------------------------------
    studente: Mapped[Utente] = relationship(
        back_populates="pratiche_come_studente", foreign_keys=[studente_id]
    )
    docente: Mapped[Utente] = relationship(
        back_populates="pratiche_come_referente", foreign_keys=[docente_id]
    )
    verificata_da: Mapped[Utente | None] = relationship(foreign_keys=[verificata_da_id])
    chiusa_da: Mapped[Utente | None] = relationship(foreign_keys=[chiusa_da_id])
    istituto: Mapped[Istituto] = relationship(back_populates="pratiche")

    # cascade delete-orphan: cancellando la pratica spariscono le sue
    # versioni di Learning Agreement e il transcript. E' corretto proprio
    # perche' sono entita' deboli: fuori dalla pratica non significano nulla.
    learning_agreements: Mapped[list[LearningAgreement]] = relationship(
        back_populates="pratica",
        cascade="all, delete-orphan",
        order_by="LearningAgreement.numero_versione",
    )
    transcript: Mapped[Transcript | None] = relationship(
        back_populates="pratica", cascade="all, delete-orphan", uselist=False
    )
    storico: Mapped[list[StoricoStato]] = relationship(
        back_populates="pratica",
        cascade="all, delete-orphan",
        order_by="StoricoStato.quando",
    )

    __table_args__ = (
        # ------------------------------------------------------------------
        # UNICITA'
        # ------------------------------------------------------------------
        sa.UniqueConstraint("codice_pratica", name="uq_pratica_codice"),
        # Evita il doppione per errore. NON impedisce piu' pratiche allo
        # stesso studente: la traccia le ammette esplicitamente.
        sa.UniqueConstraint(
            "studente_id",
            "anno_accademico",
            "istituto_id",
            name="uq_pratica_studente_anno_istituto",
        ),

        # ------------------------------------------------------------------
        # DOMINIO
        # ------------------------------------------------------------------
        sa.CheckConstraint(
            "anno_accademico BETWEEN 2000 AND 2100",
            name="ck_pratica_anno_plausibile",
        ),

        # ------------------------------------------------------------------
        # COERENZA DELLE RELAZIONI (0,1) COLLASSATE IN COLONNE
        # Una relazione o c'e' tutta o non c'e'.
        # ------------------------------------------------------------------
        sa.CheckConstraint(
            _insieme_nullo("verificata_da_id", "pre_partenza_verificata_il"),
            name="ck_pratica_verifica_coerente",
        ),
        sa.CheckConstraint(
            _insieme_nullo("chiusa_da_id", "chiusa_il"),
            name="ck_pratica_chiusura_coerente",
        ),

        # ------------------------------------------------------------------
        # PREREQUISITI FRA FATTI
        # Ancorati ai fatti, MAI allo stato corrente. Un vincolo del tipo
        # "puoi valorizzare l'arrivo solo se lo stato e' PRE_PARTENZA"
        # verrebbe rivalutato a ogni UPDATE e si romperebbe da solo appena
        # la pratica avanza. Un CHECK vede la riga intera, non la colonna
        # che stai scrivendo.
        # ------------------------------------------------------------------
        sa.CheckConstraint(
            _implica(
                "data_inizio_effettivo IS NOT NULL",
                "pre_partenza_verificata_il IS NOT NULL",
            ),
            name="ck_pratica_inizio_dopo_verifica",
        ),
        sa.CheckConstraint(
            _implica(
                "data_fine_effettiva IS NOT NULL",
                "data_inizio_effettivo IS NOT NULL",
            ),
            name="ck_pratica_fine_dopo_inizio",
        ),
        sa.CheckConstraint(
            _implica("chiusa_il IS NOT NULL", "data_fine_effettiva IS NOT NULL"),
            name="ck_pratica_chiusura_dopo_fine",
        ),

        # ------------------------------------------------------------------
        # ORDINAMENTO TEMPORALE
        # ------------------------------------------------------------------
        sa.CheckConstraint(
            _ordine("data_apertura", "pre_partenza_verificata_il"),
            name="ck_pratica_ord_apertura_verifica",
        ),
        sa.CheckConstraint(
            _ordine("pre_partenza_verificata_il", "data_inizio_effettivo"),
            name="ck_pratica_ord_verifica_inizio",
        ),
        sa.CheckConstraint(
            _ordine("data_inizio_effettivo", "data_fine_effettiva"),
            name="ck_pratica_ord_inizio_fine",
        ),
        sa.CheckConstraint(
            _ordine("data_fine_effettiva", "chiusa_il"),
            name="ck_pratica_ord_fine_chiusura",
        ),

        # ------------------------------------------------------------------
        # DALLO STATO AI FATTI
        # Sempre in questa direzione. "Stato X implica che il fatto sia
        # avvenuto" resta vero anche negli stati successivi; l'implicazione
        # inversa si romperebbe al primo avanzamento.
        # ------------------------------------------------------------------
        sa.CheckConstraint(
            _implica(
                f"stato IN ({_elenco(STATI_DOPO_PRE_PARTENZA)})",
                "pre_partenza_verificata_il IS NOT NULL",
            ),
            name="ck_pratica_stato_implica_verifica",
        ),
        sa.CheckConstraint(
            _implica(
                f"stato IN ({_elenco(STATI_DOPO_PARTENZA)})",
                "data_inizio_effettivo IS NOT NULL",
            ),
            name="ck_pratica_stato_implica_inizio",
        ),
        sa.CheckConstraint(
            _implica(
                f"stato IN ({_elenco(STATI_DOPO_RIENTRO)})",
                "data_fine_effettiva IS NOT NULL",
            ),
            name="ck_pratica_stato_implica_fine",
        ),
        sa.CheckConstraint(
            _implica(
                f"stato = '{StatoPratica.CHIUSA.value}'",
                "chiusa_il IS NOT NULL",
            ),
            name="ck_pratica_chiusa_implica_data",
        ),

        # ------------------------------------------------------------------
        # INDICI PER LE INTERROGAZIONI FREQUENTI
        # ------------------------------------------------------------------
        # "tutte le pratiche di questo studente" e "tutte le pratiche di cui
        # sono referente" sono le due query eseguite a ogni accesso.
        sa.Index("ix_pratica_studente", "studente_id"),
        sa.Index("ix_pratica_docente", "docente_id"),
        # dashboard dell'ufficio: pratiche per stato, per anno.
        sa.Index("ix_pratica_stato", "stato"),
        sa.Index("ix_pratica_anno_stato", "anno_accademico", "stato"),
    )

    # ---------------------------------------------------------------------
    # [SQL] Vincoli su questa tabella che l'ORM non puo' esprimere:
    #   trg_ruoli_pratica       studente_id ha ruolo STUDENTE, docente_id
    #                           ruolo DOCENTE, verificata_da_id e
    #                           chiusa_da_id ruolo UFFICIO. Legge un'altra
    #                           tabella: fuori portata per un CHECK.
    #   trg_transizione_stato   la coppia (stato precedente, stato nuovo)
    #                           deve esistere in transizione_ammessa.
    #                           Serve il valore OLD della riga.
    #   trg_precondizioni_stato per PRE_PARTENZA_COMPLETATA serve un LA
    #                           approvato; per CHIUSA serve il transcript e
    #                           nessun esame NON_VALUTATO. Conta righe su
    #                           altre tabelle.
    #   trg_pratica_immutabile  una pratica CHIUSA non si modifica piu'.
    #   trg_storico_stato       registra ogni transizione.
    # ---------------------------------------------------------------------

    @property
    def learning_agreement_corrente(self) -> LearningAgreement | None:
        """La versione approvata con numero piu' alto.

        Attenzione: questa proprieta' lavora in memoria e va bene per la
        singola pratica gia' caricata. Per interrogare molte pratiche usare
        la vista learning_agreement_corrente, altrimenti si ricade nel
        problema N+1.
        """
        approvate = [
            la for la in self.learning_agreements
            if la.esito == EsitoDocumento.APPROVATO
        ]
        return max(approvate, key=lambda la: la.numero_versione, default=None)

    def __repr__(self) -> str:
        return f"<Pratica {self.codice_pratica} {self.stato.value}>"


# ---------------------------------------------------------------------------
# LEARNING AGREEMENT
# ---------------------------------------------------------------------------

class LearningAgreement(db.Model):
    """Una versione del piano concordato. Entita' debole rispetto a Pratica.

    PERCHE' VERSIONI E NON UN DOCUMENTO SOLO
        La traccia impone che, se una modifica proposta durante la mobilita'
        viene rifiutata, "deve essere ripristinata l'associazione degli esami
        precedentemente concordata". Con le versioni quel ripristino non e'
        un'operazione: la versione precedente non e' mai stata toccata e
        resta quella valida. Un progetto che modificasse le righe sul posto
        dovrebbe implementare un annullamento vero.

    IL FILE NON STA NEL DATABASE
        file_path e' il percorso su disco, dentro UPLOAD_FOLDER. Il nome con
        cui il file e' salvato lo genera l'applicazione (un UUID), mai
        l'utente: cosi' nessuno puo' caricare un file chiamato
        "../../config.py". Il nome originale si conserva a parte, solo per
        mostrarlo.
    """

    __tablename__ = "learning_agreement"

    id: Mapped[int] = mapped_column(primary_key=True)
    pratica_id: Mapped[int] = mapped_column(
        sa.ForeignKey("pratica.id", ondelete="CASCADE"), nullable=False
    )
    numero_versione: Mapped[int] = mapped_column(sa.Integer, nullable=False)

    file_path: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    nome_file_originale: Mapped[str] = mapped_column(sa.String(255), nullable=False)

    esito: Mapped[EsitoDocumento] = mapped_column(
        _enum(EsitoDocumento, "esito_documento"),
        nullable=False,
        default=EsitoDocumento.IN_ATTESA,
    )
    motivazione: Mapped[str | None] = mapped_column(sa.Text)
    data_caricamento: Mapped[dt.date] = mapped_column(
        sa.Date, nullable=False, default=dt.date.today
    )
    data_decisione: Mapped[dt.date | None] = mapped_column(sa.Date)

    pratica: Mapped[Pratica] = relationship(back_populates="learning_agreements")
    corsi_esterni: Mapped[list[CorsoEsterno]] = relationship(
        back_populates="learning_agreement",
        cascade="all, delete-orphan",
        order_by="CorsoEsterno.codice",
    )

    __table_args__ = (
        # La chiave concettuale: identificazione esterna, numero di versione
        # dentro la pratica. Qui e' un UNIQUE perche' la chiave primaria e'
        # il surrogato.
        sa.UniqueConstraint(
            "pratica_id", "numero_versione", name="uq_la_pratica_versione"
        ),
        sa.CheckConstraint("numero_versione >= 1", name="ck_la_versione_positiva"),

        # Se rifiutato, la motivazione e' obbligatoria: la traccia lo chiede
        # esplicitamente al punto 4 dei requisiti funzionali.
        sa.CheckConstraint(
            _implica(
                f"esito = '{EsitoDocumento.RIFIUTATO.value}'",
                "motivazione IS NOT NULL AND length(trim(motivazione)) > 0",
            ),
            name="ck_la_motivazione_se_rifiutato",
        ),
        # Una decisione presa ha sempre una data; una non ancora presa non
        # puo' averne una.
        sa.CheckConstraint(
            f"(esito = '{EsitoDocumento.IN_ATTESA.value}') "
            f"= (data_decisione IS NULL)",
            name="ck_la_data_decisione_coerente",
        ),
        sa.CheckConstraint(
            _ordine("data_caricamento", "data_decisione"),
            name="ck_la_ord_caricamento_decisione",
        ),
        # Una sola proposta pendente alla volta per pratica.
        # INDICE UNICO PARZIALE: non esprimibile con UniqueConstraint, che
        # non ammette una clausola WHERE. E' uno degli esempi di vincolo che
        # richiede SQL specifico del DBMS.
        sa.Index(
            "uq_la_una_sola_in_attesa",
            "pratica_id",
            unique=True,
            postgresql_where=sa.text(
                f"esito = '{EsitoDocumento.IN_ATTESA.value}'"
            ),
        ),
        sa.Index("ix_la_pratica", "pratica_id"),
        sa.Index("ix_la_esito", "esito"),
    )

    # ---------------------------------------------------------------------
    # [SQL] trg_la_stato_pratica: una nuova versione si puo' creare solo se
    #       la pratica e' in APERTA, ATTESA_APPROVAZIONE_LA o
    #       MOBILITA_IN_CORSO. Dopo il rientro il piano e' congelato, ed e'
    #       cio' che garantisce che i voti si registrino su una versione che
    #       non cambia piu'.
    # ---------------------------------------------------------------------

    def __repr__(self) -> str:
        return f"<LA v{self.numero_versione} pratica={self.pratica_id}>"


# ---------------------------------------------------------------------------
# TRANSCRIPT OF RECORDS
# ---------------------------------------------------------------------------

class Transcript(db.Model):
    """Il documento rilasciato dall'istituto ospitante. Entita' debole.

    NON HA UN ESITO, ED E' VOLUTO
        Il punto 10 della traccia richiede, per la chiusura, che il
        Transcript sia "stato caricato" - non approvato. La valutazione
        avviene sui singoli esami, non sul documento.

    NON E' COLLEGATO AGLI ESAMI, ED E' VOLUTO
        E' la prova documentale, non il contenitore dei dati. Collegarlo ai
        corsi creerebbe un ciclo nello schema: dal voto si arriverebbe alla
        pratica per due strade diverse, senza nulla che garantisca che
        convergano.
    """

    __tablename__ = "transcript"

    id: Mapped[int] = mapped_column(primary_key=True)
    pratica_id: Mapped[int] = mapped_column(
        sa.ForeignKey("pratica.id", ondelete="CASCADE"), nullable=False
    )
    file_path: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    nome_file_originale: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    data_caricamento: Mapped[dt.date] = mapped_column(
        sa.Date, nullable=False, default=dt.date.today
    )

    pratica: Mapped[Pratica] = relationship(back_populates="transcript")

    __table_args__ = (
        # E' questo vincolo a realizzare la cardinalita' (0,1) del
        # concettuale: al massimo un transcript per pratica.
        sa.UniqueConstraint("pratica_id", name="uq_transcript_pratica"),
    )

    def __repr__(self) -> str:
        return f"<Transcript pratica={self.pratica_id}>"


# ---------------------------------------------------------------------------
# CORSO ESTERNO
# ---------------------------------------------------------------------------

class CorsoEsterno(db.Model):
    """Un insegnamento pianificato all'estero, dentro una versione del piano.

    ENTITA' DEBOLE RISPETTO AL LEARNING AGREEMENT
        Il codice non identifica un insegnamento in assoluto: sulle codifiche
        estere non abbiamo autorita', lo stesso codice puo' indicare corsi
        diversi in atenei diversi e cambiare titolo o crediti da un anno
        all'altro. Identifica un corso com'era in quel momento e in quel
        piano.

    PERCHE' NON UN CATALOGO
        La dipendenza funzionale codice -> titolo, crediti non vale nel
        dominio. Non essendoci dipendenza non c'e' ridondanza da eliminare,
        e un catalogo imporrebbe ai dati un vincolo che la realta' non
        rispetta. La verifica di veridicita' e' affidata al controllo
        dell'ufficio in fase pre-partenza: vincolo di processo, non di
        schema.
    """

    __tablename__ = "corso_esterno"

    id: Mapped[int] = mapped_column(primary_key=True)
    learning_agreement_id: Mapped[int] = mapped_column(
        sa.ForeignKey("learning_agreement.id", ondelete="CASCADE"), nullable=False
    )
    codice: Mapped[str] = mapped_column(sa.String(40), nullable=False)
    titolo: Mapped[str] = mapped_column(sa.String(200), nullable=False)
    crediti: Mapped[int] = mapped_column(sa.Integer, nullable=False)

    learning_agreement: Mapped[LearningAgreement] = relationship(
        back_populates="corsi_esterni"
    )
    equivalenze: Mapped[list[Equivalenza]] = relationship(
        back_populates="corso_esterno", cascade="all, delete-orphan"
    )
    esame: Mapped[Esame | None] = relationship(
        back_populates="corso_esterno", cascade="all, delete-orphan", uselist=False
    )

    __table_args__ = (
        # La chiave concettuale: codice dentro la versione del piano.
        sa.UniqueConstraint(
            "learning_agreement_id", "codice", name="uq_corso_esterno_la_codice"
        ),
        sa.CheckConstraint("crediti > 0", name="ck_corso_esterno_crediti_positivi"),
        sa.CheckConstraint(
            "length(trim(titolo)) > 0", name="ck_corso_esterno_titolo_non_vuoto"
        ),
        sa.Index("ix_corso_esterno_la", "learning_agreement_id"),
    )

    def __repr__(self) -> str:
        return f"<CorsoEsterno {self.codice} la={self.learning_agreement_id}>"


# ---------------------------------------------------------------------------
# EQUIVALENZA  (l'unica tabella nata da una relazione)
# ---------------------------------------------------------------------------

class Equivalenza(db.Model):
    """Il mapping fra un insegnamento estero e uno di Ca' Foscari.

    E' l'unica relazione N:M dello schema, e per questo l'unica che diventa
    una tabella. La chiave primaria e' la coppia delle due chiavi esterne:
    la stessa equivalenza non ha senso due volte.

    LE DUE CARDINALITA' N SERVONO ENTRAMBE
        piu' esami esteri riconosciuti su un unico insegnamento interno, e
        un esame estero scomposto su piu' insegnamenti interni. Entrambi i
        casi si ottengono senza modellare nulla in piu'.
    """

    __tablename__ = "equivalenza"

    corso_esterno_id: Mapped[int] = mapped_column(
        sa.ForeignKey("corso_esterno.id", ondelete="CASCADE"), primary_key=True
    )
    corso_interno_id: Mapped[int] = mapped_column(
        sa.ForeignKey("corso_interno.id", ondelete="RESTRICT"), primary_key=True
    )

    corso_esterno: Mapped[CorsoEsterno] = relationship(back_populates="equivalenze")
    corso_interno: Mapped[CorsoInterno] = relationship(back_populates="equivalenze")

    __table_args__ = (
        # La chiave primaria indicizza gia' il primo campo; questo indice
        # serve alla direzione opposta ("quali esami esteri sono stati
        # riconosciuti come Basi di Dati").
        sa.Index("ix_equivalenza_interno", "corso_interno_id"),
    )

    def __repr__(self) -> str:
        return f"<Equivalenza {self.corso_esterno_id}->{self.corso_interno_id}>"


# ---------------------------------------------------------------------------
# ESAME
# ---------------------------------------------------------------------------

class Esame(db.Model):
    """Il risultato conseguito su un insegnamento estero pianificato.

    PERCHE' ENTITA' SEPARATA E NON ATTRIBUTI NULLABILI SU CorsoEsterno
        Voto e data sono attributi che sono tutti nulli insieme o tutti
        valorizzati insieme: e' la firma di un'entita' nascosta. Con gli
        attributi sul corso, il NULL significherebbe due cose diverse e
        indistinguibili: "esame non ancora registrato" e "esame che lo
        studente non ha sostenuto". Con l'entita' separata, l'assenza della
        riga e' la seconda, senza bisogno di convenzioni.

    PERCHE' NON UNA GENERALIZZAZIONE
        Un esame non e' un tipo particolare di corso: e' un fatto distinto
        che riguarda un corso. La gerarchia avrebbe avuto un solo sottotipo
        e nessun attributo proprio nel supertipo, e nella traduzione logica
        avrebbe dato comunque questa stessa tabella.
    """

    __tablename__ = "esame"

    id: Mapped[int] = mapped_column(primary_key=True)
    corso_esterno_id: Mapped[int] = mapped_column(
        sa.ForeignKey("corso_esterno.id", ondelete="CASCADE"), nullable=False
    )

    voto: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    data_esame: Mapped[dt.date] = mapped_column(sa.Date, nullable=False)

    esito_riconoscimento: Mapped[EsitoRiconoscimento] = mapped_column(
        _enum(EsitoRiconoscimento, "esito_riconoscimento"),
        nullable=False,
        default=EsitoRiconoscimento.NON_VALUTATO,
    )
    data_riconoscimento: Mapped[dt.date | None] = mapped_column(sa.Date)

    corso_esterno: Mapped[CorsoEsterno] = relationship(back_populates="esame")

    __table_args__ = (
        # Realizza la cardinalita' (0,1): al massimo un esito per corso.
        sa.UniqueConstraint("corso_esterno_id", name="uq_esame_corso"),
        # Voto in trentesimi. 31 rappresenta la lode; se preferite tenerla
        # come colonna booleana separata, cambiate qui.
        sa.CheckConstraint("voto BETWEEN 18 AND 31", name="ck_esame_voto_valido"),
        sa.CheckConstraint(
            f"(esito_riconoscimento = '{EsitoRiconoscimento.NON_VALUTATO.value}') "
            f"= (data_riconoscimento IS NULL)",
            name="ck_esame_data_riconoscimento_coerente",
        ),
        sa.CheckConstraint(
            _ordine("data_esame", "data_riconoscimento"),
            name="ck_esame_ord_esame_riconoscimento",
        ),
        # La query "restano esami da valutare in questa pratica?" gira a ogni
        # visualizzazione della pagina dell'ufficio.
        sa.Index("ix_esame_esito", "esito_riconoscimento"),
    )

    # ---------------------------------------------------------------------
    # [SQL] trg_esame_stato_pratica: un esame si registra solo quando la
    #       pratica e' in IN_RICONOSCIMENTO_ESAMI, e solo su un corso che
    #       appartiene alla versione operativa del piano. Attraversa tre
    #       tabelle: fuori portata per un CHECK.
    # ---------------------------------------------------------------------

    def __repr__(self) -> str:
        return f"<Esame corso={self.corso_esterno_id} voto={self.voto}>"


# ---------------------------------------------------------------------------
# STRUTTURE DI SUPPORTO
# Non appartengono al dominio applicativo: sono al servizio dei vincoli e
# della tracciabilita'. Nel diagramma concettuale non compaiono.
# ---------------------------------------------------------------------------

class TransizioneAmmessa(db.Model):
    """La macchina a stati come DATO, non come codice.

    Tre vantaggi rispetto a un CASE scritto dentro il trigger:
      - il trigger diventa dieci righe che non cambiano mai;
      - la tabella si stampa nella relazione ed e' la documentazione;
      - l'interfaccia interroga la stessa tabella per decidere quali pulsanti
        mostrare, quindi le regole non sono scritte in due posti diversi.
    """

    __tablename__ = "transizione_ammessa"

    stato_da: Mapped[StatoPratica] = mapped_column(
        _enum(StatoPratica, "stato_pratica"), primary_key=True
    )
    stato_a: Mapped[StatoPratica] = mapped_column(
        _enum(StatoPratica, "stato_pratica"), primary_key=True
    )
    ruolo: Mapped[Ruolo] = mapped_column(_enum(Ruolo, "ruolo"), primary_key=True)

    descrizione: Mapped[str] = mapped_column(sa.String(200), nullable=False)

    __table_args__ = (
        sa.CheckConstraint("stato_da <> stato_a", name="ck_transizione_non_banale"),
    )

    def __repr__(self) -> str:
        return f"<Transizione {self.stato_da.value}->{self.stato_a.value}>"


class StoricoStato(db.Model):
    """Registro di ogni cambiamento di stato: chi, cosa, quando.

    Scritto dal trigger, mai dall'applicazione: cosi' la traccia esiste anche
    per le modifiche fatte da uno script o a mano sul DBMS.

    Qui il timestamp e' un DateTime e non un Date, perche' due transizioni
    nello stesso giorno devono restare ordinabili.
    """

    __tablename__ = "storico_stato"

    id: Mapped[int] = mapped_column(primary_key=True)
    pratica_id: Mapped[int] = mapped_column(
        sa.ForeignKey("pratica.id", ondelete="CASCADE"), nullable=False
    )
    stato_da: Mapped[StatoPratica | None] = mapped_column(
        _enum(StatoPratica, "stato_pratica")
    )
    stato_a: Mapped[StatoPratica] = mapped_column(
        _enum(StatoPratica, "stato_pratica"), nullable=False
    )
    quando: Mapped[dt.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )
    utente_id: Mapped[int | None] = mapped_column(
        sa.ForeignKey("utente.id", ondelete="SET NULL")
    )

    pratica: Mapped[Pratica] = relationship(back_populates="storico")
    utente: Mapped[Utente | None] = relationship()

    __table_args__ = (
        sa.Index("ix_storico_pratica", "pratica_id"),
        # "da quanto tempo questa pratica e' ferma": ordina per data
        # decrescente dentro la pratica.
        sa.Index("ix_storico_pratica_quando", "pratica_id", "quando"),
    )

    def __repr__(self) -> str:
        return f"<Storico pratica={self.pratica_id} -> {self.stato_a.value}>"