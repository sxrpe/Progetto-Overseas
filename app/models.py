"""
    Lo schema logico tradotto in classi SQLAlchemy.
    Ogni classe è una tabella.

    Le stringhe dentro CheckConstraint sono SQL che SQLAlchemy le copia nel
    CREATE TABLE senza interpretarle.
"""

from __future__ import annotations

import datetime as dt

import sqlalchemy as sa
from flask_login import UserMixin
from sqlalchemy.orm import Mapped, mapped_column, relationship
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db


# ===========================================================================
#  UTENTE
# ===========================================================================

class Utente(UserMixin, db.Model):
    """
    TRADUZIONE SOTTOCLASSI:
        Nello schema concettuale c'era un padre Utente e tre figli.
        Qui la gerarchia è collassata in una tabella sola, con una
        colonna "ruolo" che distringue le sottoclassi e l'attributo "matricola" è
        nullabile perchè appartiene solo al sottotipo Studente.

    COSA SI PERDE DAL MODELLO CONCETTUALE:
        docente_id punta a Utente, non solo ai docenti: uno studente potrebbe
        risultare referente. Il ruolo lo controlla il trigger trg_ruoli_pratica.

    ARGOMENTI':
        Eredita la classe db.Model, che trasforma la classe Python in un modello ORM,
        che verrà poi interpretato da SQLAlchemy e trasformato in una tabella.
        Importa poi i metodi di Flask-Login is_authenticated, is_active, is_anonymous e get_id
        tramite la classe UserMixin
    """

    __tablename__ = "utente"

    id: Mapped[int] = mapped_column(primary_key=True)

    email: Mapped[str] = mapped_column(sa.String(120), nullable=False)
    password_hash: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    nome: Mapped[str] = mapped_column(sa.String(80), nullable=False)
    cognome: Mapped[str] = mapped_column(sa.String(80), nullable=False)
    ruolo: Mapped[str] = mapped_column(sa.String(20), nullable=False)

    matricola: Mapped[str | None] = mapped_column(sa.String(20))

    pratiche_come_studente: Mapped[list[Pratica]] = relationship(
        back_populates="studente",
        foreign_keys="Pratica.studente_id",
    )
    pratiche_come_referente: Mapped[list[Pratica]] = relationship(
        back_populates="docente",
        foreign_keys="Pratica.docente_id",
    )

    __table_args__ = (
        # Identificatore dell'entità nel modello concettuale, lo rendiamo UNIQUE
        sa.UniqueConstraint("email", name="uq_utente_email"),

        sa.UniqueConstraint("matricola", name="uq_utente_matricola"),

        sa.CheckConstraint(
            "ruolo IN ('STUDENTE', 'DOCENTE', 'UFFICIO')",
            name="ck_utente_ruolo",
        ),

        # La matricola c'è se e solo se l'utente è uno studente.
        sa.CheckConstraint(
            "(ruolo = 'STUDENTE') = (matricola IS NOT NULL)",
            name="ck_utente_matricola_solo_studenti",
        ),

        sa.CheckConstraint(
            "length(trim(email)) > 0",
            name="ck_utente_email_non_vuota",
        ),
    )

    # generate_password_hash applica una funzione di hash alla password e il sale
    def imposta_password(self, in_chiaro: str) -> None:
        self.password_hash = generate_password_hash(in_chiaro)

    def verifica_password(self, in_chiaro: str) -> bool:
        return check_password_hash(self.password_hash, in_chiaro)

    # @property fa si' che si usino senza parentesi: utente.e_studente.
    # Non esistono nel database, sono calcolate ogni volta. Servono a tenere i template leggibili.

    @property
    def e_studente(self) -> bool:
        return self.ruolo == "STUDENTE"

    @property
    def e_docente(self) -> bool:
        return self.ruolo == "DOCENTE"

    @property
    def e_ufficio(self) -> bool:
        return self.ruolo == "UFFICIO"

    @property
    def nome_completo(self) -> str:
        return f"{self.nome} {self.cognome}"

    def __repr__(self) -> str:
        # E' quello che il debugger mostra al posto di <Utente object at 0x7f..>
        return f"<Utente {self.email} ({self.ruolo})>"


# ===========================================================================
#  ISTITUTO OSPITANTE
# ===========================================================================

class Istituto(db.Model):
    """
    Catalogo degli atenei partner, gestito dall'ufficio Overseas.
    Lo studente sceglie da questa lista, non digita il nome.
    """

    __tablename__ = "istituto"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(sa.String(160), nullable=False)
    paese: Mapped[str] = mapped_column(sa.String(80), nullable=False)
    citta: Mapped[str] = mapped_column(sa.String(80), nullable=False)

    pratiche: Mapped[list[Pratica]] = relationship(back_populates="istituto")

    __table_args__ = (
        # Impedisce lo stesso nome nella stessa città.
        sa.UniqueConstraint("nome", "citta", name="uq_istituto_nome_citta"),
    )

    def __repr__(self) -> str:
        return f"<Istituto {self.nome} ({self.citta})>"


# ===========================================================================
#  CORSO INTERNO
# ===========================================================================

class CorsoInterno(db.Model):
    """Catalogo degli insegnamenti di Ca' Foscari.

    Viene gestita come catalogo, senza chiavi esterne che si collegano
    ad una determinata pratica o Learning Agreement perchè i corsi
    sono determinati solo dall'università Ca'Foscari in un catalogo preciso.
    Uno stesso corso non ha il problema di poter essere interpretato in modo
    diverso dalle varie università (come i corsi esteri)
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
        sa.CheckConstraint("crediti > 0", name="ck_corso_interno_crediti"),
        sa.CheckConstraint(
            "length(trim(titolo)) > 0",
            name="ck_corso_interno_titolo",
        ),
    )

    def __repr__(self) -> str:
        return f"<CorsoInterno {self.codice}>"


# ===========================================================================
#  PRATICA
# ===========================================================================

class Pratica(db.Model):
    """
    L'entità centrale: una mobilità dalla creazione alla chiusura.

    LE QUATTRO CHIAVI ESTERNE VERSO UTENTE
        - studente_id: relazione "apertura", con data_apertura come suo attributo.
            Stabilisce anche la titolarità della pratica di chi la apre.
        - docente_id: relazione "referenza" senza attributi.
        - verificata_da_id: relazione "verifica pre-partenza", cardinalita'
            (0,1) dal lato pratica.
        - chiusa_da_id: relazione "chiusura", con cardinalità (0,1).

        Le ultime due, avendo massimo 1 dal lato pratica, nel modello logico
        non diventano tabelle: collassano in colonne.
    """

    __tablename__ = "pratica"

    id: Mapped[int] = mapped_column(primary_key=True)

    codice_pratica: Mapped[str] = mapped_column(sa.String(20), nullable=False)

    anno_accademico: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    periodo: Mapped[str] = mapped_column(sa.String(30), nullable=False)
    stato: Mapped[str] = mapped_column(
        sa.String(30), nullable=False, default="APERTA"
    )
    note: Mapped[str | None] = mapped_column(sa.Text)

    # Relazione apertura con studente
    studente_id: Mapped[int] = mapped_column(
        sa.ForeignKey("utente.id", ondelete="RESTRICT"), nullable=False
    )

    data_apertura: Mapped[dt.date] = mapped_column(
        sa.Date, nullable=False, default=dt.date.today
    )

    # Relazione referenza con il docente
    docente_id: Mapped[int] = mapped_column(
        sa.ForeignKey("utente.id", ondelete="RESTRICT"), nullable=False
    )

    # Relazione destinazione con gli istituti
    istituto_id: Mapped[int] = mapped_column(
        sa.ForeignKey("istituto.id", ondelete="RESTRICT"), nullable=False
    )

    # Relazione verifica pre-partenza con l'ufficio
    verificata_da_id: Mapped[int | None] = mapped_column(
        sa.ForeignKey("utente.id", ondelete="RESTRICT")
    )
    pre_partenza_verificata_il: Mapped[dt.date | None] = mapped_column(sa.Date)

    data_inizio_effettivo: Mapped[dt.date | None] = mapped_column(sa.Date)
    data_fine_effettiva: Mapped[dt.date | None] = mapped_column(sa.Date)

    # Relazione chiusura con l'ufficio
    chiusa_da_id: Mapped[int | None] = mapped_column(
        sa.ForeignKey("utente.id", ondelete="RESTRICT")
    )
    chiusa_il: Mapped[dt.date | None] = mapped_column(sa.Date)

    # Scorciatoie dell'ORM per accedere direttamente ai dati
    # senza dover utilizzare query per eseguire JOIN tra tabelle
    studente: Mapped[Utente] = relationship(
        back_populates="pratiche_come_studente", foreign_keys=[studente_id]
    )
    docente: Mapped[Utente] = relationship(
        back_populates="pratiche_come_referente", foreign_keys=[docente_id]
    )
    verificata_da: Mapped[Utente | None] = relationship(
        foreign_keys=[verificata_da_id]
    )
    chiusa_da: Mapped[Utente | None] = relationship(foreign_keys=[chiusa_da_id])
    istituto: Mapped[Istituto] = relationship(back_populates="pratiche")

    # Cancellando la pratica spariscono le sue versioni di Learning Agreement
    # e il suo Transcript.
    # Denotano il ruolo debole di queste entità rispetto a Pratica.
    learning_agreements: Mapped[list[LearningAgreement]] = relationship(
        back_populates="pratica",
        cascade="all, delete-orphan",
        order_by="LearningAgreement.numero_versione",
    )
    transcript: Mapped[Transcript | None] = relationship(
        back_populates="pratica", cascade="all, delete-orphan", uselist=False
    )

    __table_args__ = (
        sa.UniqueConstraint("codice_pratica", name="uq_pratica_codice"),

        sa.UniqueConstraint(
            "studente_id", "anno_accademico", "istituto_id",
            name="uq_pratica_studente_anno_istituto",
        ),

        sa.CheckConstraint(
            "periodo IN ('PRIMO_SEMESTRE', 'SECONDO_SEMESTRE', 'INTERO_ANNO')",
            name="ck_pratica_periodo",
        ),
        sa.CheckConstraint(
            "stato IN ('APERTA', 'ATTESA_APPROVAZIONE_LA',"
            " 'PRE_PARTENZA_COMPLETATA', 'MOBILITA_IN_CORSO',"
            " 'IN_RICONOSCIMENTO_ESAMI', 'CHIUSA')",
            name="ck_pratica_stato",
        ),
        sa.CheckConstraint(
            "anno_accademico BETWEEN 2000 AND 2100",
            name="ck_pratica_anno_plausibile",
        ),

        # Controlla che se la pratica è verificata o chiusa,
        # ci sia qualcuno che se ne sia effettivamente occupato
        sa.CheckConstraint(
            "(verificata_da_id IS NULL) = (pre_partenza_verificata_il IS NULL)",
            name="ck_pratica_verifica_coerente",
        ),
        sa.CheckConstraint(
            "(chiusa_da_id IS NULL) = (chiusa_il IS NULL)",
            name="ck_pratica_chiusura_coerente",
        ),

        # Vincoli di implicazione:
        # Se la mobilità è iniziata, la verifica pre-partenza deve essere statwa effettuata
        sa.CheckConstraint(
            "NOT (data_inizio_effettivo IS NOT NULL)"
            " OR (pre_partenza_verificata_il IS NOT NULL)",
            name="ck_pratica_inizio_dopo_verifica",
        ),
        # Se la mobilità è finita, deve avere una data di inizio
        sa.CheckConstraint(
            "NOT (data_fine_effettiva IS NOT NULL)"
            " OR (data_inizio_effettivo IS NOT NULL)",
            name="ck_pratica_fine_dopo_inizio",
        ),
        # Se la pratica è chiusa, deve avere una data di fine mobilità
        sa.CheckConstraint(
            "NOT (chiusa_il IS NOT NULL)"
            " OR (data_fine_effettiva IS NOT NULL)",
            name="ck_pratica_chiusura_dopo_fine",
        ),

        # Controlla che le date siano ordinate temporalmente
        # in base all'ordine delle azioni
        sa.CheckConstraint(
            "data_apertura IS NULL OR pre_partenza_verificata_il IS NULL"
            " OR data_apertura <= pre_partenza_verificata_il",
            name="ck_pratica_ord_apertura_verifica",
        ),
        sa.CheckConstraint(
            "pre_partenza_verificata_il IS NULL OR data_inizio_effettivo IS NULL"
            " OR pre_partenza_verificata_il <= data_inizio_effettivo",
            name="ck_pratica_ord_verifica_inizio",
        ),
        sa.CheckConstraint(
            "data_inizio_effettivo IS NULL OR data_fine_effettiva IS NULL"
            " OR data_inizio_effettivo <= data_fine_effettiva",
            name="ck_pratica_ord_inizio_fine",
        ),

        # Altri vincoli di implicazione:
        # Dalla pre-partenza completata in poi serve la data di verifica.
        sa.CheckConstraint(
            "stato NOT IN ('PRE_PARTENZA_COMPLETATA', 'MOBILITA_IN_CORSO',"
            " 'IN_RICONOSCIMENTO_ESAMI', 'CHIUSA')"
            " OR pre_partenza_verificata_il IS NOT NULL",
            name="ck_pratica_stato_implica_verifica",
        ),
        # Se la pratica ha uno stato successivo alla pre-partenza, deve avere una data di inizio mobilità
        sa.CheckConstraint(
            "stato NOT IN ('MOBILITA_IN_CORSO', 'IN_RICONOSCIMENTO_ESAMI',"
            " 'CHIUSA')"
            " OR data_inizio_effettivo IS NOT NULL",
            name="ck_pratica_stato_implica_inizio",
        ),
        # Se la pratica ha uno stato successivo alla mobilità, deve avere una data di fine mobilità
        sa.CheckConstraint(
            "stato NOT IN ('IN_RICONOSCIMENTO_ESAMI', 'CHIUSA')"
            " OR data_fine_effettiva IS NOT NULL",
            name="ck_pratica_stato_implica_fine",
        ),
        # Se la pratica è in stato CHIUSA, deve avere una data di chiusura
        sa.CheckConstraint(
            "stato <> 'CHIUSA' OR chiusa_il IS NOT NULL",
            name="ck_pratica_chiusa_implica_data",
        ),

        # INDICI
        # Recuperano pratiche relative a determinati studenti o docenti
        sa.Index("ix_pratica_studente", "studente_id"),
        sa.Index("ix_pratica_docente", "docente_id"),
        # Recupera pratiche in base allo stato o all'anno accademico
        sa.Index("ix_pratica_stato", "stato"),
        sa.Index("ix_pratica_anno_stato", "anno_accademico", "stato"),
    )

    @property
    def learning_agreement_corrente(self) -> LearningAgreement | None:
        # Versione approvata con il numero più alto.
        migliore = None
        for la in self.learning_agreements:
            if la.esito != "APPROVATO":
                continue
            if migliore is None or la.numero_versione > migliore.numero_versione:
                migliore = la
        return migliore

    def __repr__(self) -> str:
        return f"<Pratica {self.codice_pratica} {self.stato}>"


# ===========================================================================
#  LEARNING AGREEMENT
# ===========================================================================

class LearningAgreement(db.Model):
    """
    Una versione del piano concordato.
    Entità debole rispetto a Pratica.

    PERCHE' UTILIZZIAMO DIVERSE VERSIONI
        Conserva le versioni precedenti in caso l'ultima versione venga rifiutata.
        In quel caso si recupera e si tiene valida la precedente.

    PERCHE' file_path E' NULLABILE
        La riga nasce come bozza quando lo studente comincia a compilare il
        piano. Il file diventa obbligatorio al momento dell'invio,
        e sarà il trigger sulla transizione a garantirlo.
    """

    __tablename__ = "learning_agreement"

    id: Mapped[int] = mapped_column(primary_key=True)
    pratica_id: Mapped[int] = mapped_column(
        sa.ForeignKey("pratica.id", ondelete="CASCADE"), nullable=False
    )
    numero_versione: Mapped[int] = mapped_column(sa.Integer, nullable=False)

    file_path: Mapped[str | None] = mapped_column(sa.String(255))
    nome_file_originale: Mapped[str | None] = mapped_column(sa.String(255))

    esito: Mapped[str] = mapped_column(
        sa.String(20), nullable=False, default="IN_ATTESA"
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
        # La chiave identificativa è la combinazione del numero di versione all'interno di una pratica
        sa.UniqueConstraint(
            "pratica_id", "numero_versione", name="uq_la_pratica_versione"
        ),
        sa.CheckConstraint("numero_versione >= 1", name="ck_la_versione_positiva"),

        sa.CheckConstraint(
            "esito IN ('IN_ATTESA', 'APPROVATO', 'RIFIUTATO')",
            name="ck_la_esito",
        ),

        # Se rifiutato, la motivazione è obbligatoria
        sa.CheckConstraint(
            "NOT (esito = 'RIFIUTATO')"
            " OR (motivazione IS NOT NULL AND length(trim(motivazione)) > 0)",
            name="ck_la_motivazione_se_rifiutato",
        ),

        # Ogni decisione presa ha una data corrispondente
        sa.CheckConstraint(
            "(esito = 'IN_ATTESA') = (data_decisione IS NULL)",
            name="ck_la_data_decisione_coerente",
        ),
        sa.CheckConstraint(
            "data_caricamento IS NULL OR data_decisione IS NULL"
            " OR data_caricamento <= data_decisione",
            name="ck_la_ord_caricamento_decisione",
        ),

        # Una sola proposta pendente alla volta per pratica
        sa.Index(
            "uq_la_una_sola_in_attesa",
            "pratica_id",
            unique=True,
            postgresql_where=sa.text("esito = 'IN_ATTESA'"),
        ),
        sa.Index("ix_la_pratica", "pratica_id"),
        sa.Index("ix_la_esito", "esito"),
    )

    def __repr__(self) -> str:
        return f"<LA v{self.numero_versione} pratica={self.pratica_id}>"


# ===========================================================================
#  TRANSCRIPT OF RECORDS
# ===========================================================================

class Transcript(db.Model):
    """
    Documento rilasciato dall'istituto ospitante.
    Entità debole.
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
        # Per realizzare la cardinalità (0,1), per cui un solo Transcript per pratica
        sa.UniqueConstraint("pratica_id", name="uq_transcript_pratica"),
    )

    def __repr__(self) -> str:
        return f"<Transcript pratica={self.pratica_id}>"


# ===========================================================================
#  CORSO ESTERNO
# ===========================================================================

class CorsoEsterno(db.Model):
    """
    Insegnamento pianificato all'estero, dentro una versione del piano.

    ENTITA' DEBOLE RISPETTO AL LEARNING AGREEMENT
        Il codice non identifica un insegnamento in assoluto: non sappiamo le
        codifiche estere per cui lo stesso codice potrebbe indicare corsi
        diversi in atenei diversi e cambiare titolo o crediti da un anno
        all'altro. Identifica un corso com'era in quel momento e in quel
        piano, quindi per identificarlo serve anche la versione del Learning
        Agreement a cui appartiene.
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
        # Chiave identificativa data dal codice del corso in quella versione del LA
        sa.UniqueConstraint(
            "learning_agreement_id", "codice", name="uq_corso_esterno_la_codice"
        ),
        sa.CheckConstraint("crediti > 0", name="ck_corso_esterno_crediti"),
        sa.CheckConstraint(
            "length(trim(titolo)) > 0", name="ck_corso_esterno_titolo"
        ),
        sa.Index("ix_corso_esterno_la", "learning_agreement_id"),
    )

    def __repr__(self) -> str:
        return f"<CorsoEsterno {self.codice} la={self.learning_agreement_id}>"


# ===========================================================================
#  EQUIVALENZA
# ===========================================================================

class Equivalenza(db.Model):
    """
    Mapping fra un insegnamento estero e uno di Ca'Foscari.

    Relazione N:M dello schema, che diventa tabella nella traduzione.
    La chiave primaria è la coppia delle due chiavi esterne.
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
        # Quali esami sono stati riconosciuti come un corso interno
        sa.Index("ix_equivalenza_interno", "corso_interno_id"),
    )

    def __repr__(self) -> str:
        return f"<Equivalenza {self.corso_esterno_id}->{self.corso_interno_id}>"


# ===========================================================================
#  ESAME
# ===========================================================================

class Esame(db.Model):
    """
    Risultato conseguito su un insegnamento estero pianificato.

    PERCHE' UN'ENTITA' SEPARATA E NON DELLE COLONNE NULLABILI SU CorsoEsterno
        Voto e data sono attributi che sono tutti nulli insieme o tutti
        valorizzati insieme.
    """

    __tablename__ = "esame"

    id: Mapped[int] = mapped_column(primary_key=True)
    corso_esterno_id: Mapped[int] = mapped_column(
        sa.ForeignKey("corso_esterno.id", ondelete="CASCADE"), nullable=False
    )

    voto: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    data_esame: Mapped[dt.date] = mapped_column(sa.Date, nullable=False)

    esito_riconoscimento: Mapped[str] = mapped_column(
        sa.String(20), nullable=False, default="NON_VALUTATO"
    )
    data_riconoscimento: Mapped[dt.date | None] = mapped_column(sa.Date)

    corso_esterno: Mapped[CorsoEsterno] = relationship(back_populates="esame")

    __table_args__ = (
        # Realizza la cardinalità (0,1): al massimo un esito per corso.
        sa.UniqueConstraint("corso_esterno_id", name="uq_esame_corso"),

        sa.CheckConstraint("voto BETWEEN 18 AND 31", name="ck_esame_voto"),

        sa.CheckConstraint(
            "esito_riconoscimento IN ('NON_VALUTATO', 'ACCETTATO', 'RIFIUTATO')",
            name="ck_esame_esito",
        ),
        sa.CheckConstraint(
            "(esito_riconoscimento = 'NON_VALUTATO')"
            " = (data_riconoscimento IS NULL)",
            name="ck_esame_data_riconoscimento_coerente",
        ),
        sa.CheckConstraint(
            "data_esame IS NULL OR data_riconoscimento IS NULL"
            " OR data_esame <= data_riconoscimento",
            name="ck_esame_ord_esame_riconoscimento",
        ),

        # Visualizza gli esami per esito
        sa.Index("ix_esame_esito", "esito_riconoscimento"),
    )

    def __repr__(self) -> str:
        return f"<Esame corso={self.corso_esterno_id} voto={self.voto}>"

# FIXME

# ===========================================================================
#  STRUTTURA DI SUPPORTO
#  Non appartiene al dominio applicativo: e' al servizio del trigger che
#  valida i cambi di stato. Nel diagramma concettuale non compare.
# ===========================================================================


class TransizioneAmmessa(db.Model):
    """La macchina a stati come dato, invece che scritta dentro il trigger.

    Tre vantaggi:
      - il corpo del trigger diventa dieci righe che non cambiano mai: per
        modificare il processo si aggiunge o si toglie una riga qui;
      - la tabella si stampa nella relazione ed e' gia' la documentazione
        della macchina a stati;
      - l'interfaccia interroga la stessa tabella per decidere quali pulsanti
        mostrare, quindi le regole stanno in un posto solo invece che
        duplicate fra trigger e template.

    Il ruolo fa parte della chiave primaria: una transizione consentita a
    piu' ruoli si esprime con piu' righe, senza toccare il codice.

    Le sei righe vengono inserite da scripts/schema_extra_postgres.sql.
    """

    __tablename__ = "transizione_ammessa"

    stato_da: Mapped[str] = mapped_column(sa.String(30), primary_key=True)
    stato_a: Mapped[str] = mapped_column(sa.String(30), primary_key=True)
    ruolo: Mapped[str] = mapped_column(sa.String(20), primary_key=True)

    descrizione: Mapped[str] = mapped_column(sa.String(200), nullable=False)

    __table_args__ = (
        sa.CheckConstraint("stato_da <> stato_a", name="ck_transizione_non_banale"),
    )

    def __repr__(self) -> str:
        return f"<Transizione {self.stato_da}->{self.stato_a}>"
