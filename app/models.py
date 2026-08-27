"""Lo schema logico tradotto in classi SQLAlchemy.

COME SI LEGGE QUESTO FILE
    Ogni classe e' una tabella. Dentro ogni classe trovi solo quattro tipi
    di riga, ripetuti:

      1) una colonna
             nome: Mapped[str] = mapped_column(sa.String(80), nullable=False)

      2) una colonna che punta a un'altra tabella (chiave esterna)
             studente_id: Mapped[int] = mapped_column(
                 sa.ForeignKey("utente.id"))

      3) la scorciatoia per arrivare all'oggetto puntato
         (NON e' una colonna: la colonna e' quella del punto 2)
             studente: Mapped[Utente] = relationship(...)

      4) un vincolo, dentro __table_args__ in fondo alla classe
             sa.CheckConstraint("crediti > 0", name="ck_crediti_positivi")

    Se riconosci queste quattro forme, il file lo leggi tutto.

COME SI SCRIVONO I VINCOLI
    Le stringhe dentro CheckConstraint sono SQL puro: SQLAlchemy le copia nel
    CREATE TABLE senza interpretarle. Sono scritte per esteso, cosi' quello
    che leggi qui e' esattamente quello che finisce nel database.

    Due forme ricorrono spesso e conviene riconoscerle a colpo d'occhio:

      "se A allora B"     ->   NOT (A) OR (B)
                               In SQL non esiste l'implicazione. Si scrive
                               cosi', ed e' logicamente equivalente.

      "o entrambi o nessuno dei due"
                          ->   (A IS NULL) = (B IS NULL)
                               Vero quando sono tutti e due nulli o tutti e
                               due valorizzati.

    Sui confronti fra date, la forma e' sempre
        X IS NULL OR Y IS NULL OR X <= Y
    perche' senza i due controlli sui NULL il confronto darebbe NULL appena
    una delle due date manca, e il vincolo smetterebbe di dire qualcosa.

QUELLO CHE QUI NON C'E'
    I trigger e le viste, che l'ORM non sa esprimere. Stanno in
    scripts/schema_extra_postgres.sql, eseguito da init_db subito dopo la
    creazione delle tabelle. Dove un vincolo vive li', il commento della
    classe lo dice.
"""

from __future__ import annotations
# ^ Questa riga serve solo a permettere di nominare una classe prima che sia
#   stata definita: Pratica parla di LearningAgreement, che sta duecento
#   righe piu' sotto. E' il sostituto della forward declaration del C++.
#   Vale solo per le annotazioni (quello che sta fra ":" e "="); dentro gli
#   argomenti di una funzione i nomi vanno comunque fra virgolette.

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
    """Studenti, docenti referenti e personale d'ufficio, in un'unica tabella.

    TRADUZIONE DAL MODELLO CONCETTUALE
        Nel concettuale c'era una generalizzazione: un padre Utente e tre
        figli. Qui la gerarchia e' collassata in una tabella sola, con una
        colonna "ruolo" che fa da discriminatore e "matricola" resa nullabile
        perche' appartiene al solo sottotipo Studente.

    COSA SI PERDE COL COLLASSO
        Nel concettuale la relazione "referenza" collegava la Pratica al
        sottotipo Docente: il vincolo era espresso dal disegno. Ora tutte le
        chiavi esterne puntano a "utente" e nulla impedisce di mettere uno
        studente come referente.
        [SQL] Il trigger trg_ruoli_pratica ripristina quella garanzia. E' un
        vincolo che non nasce dal dominio ma dalla traduzione, ed e' la
        giustificazione piu' pulita che abbiamo per l'uso di un trigger.

    PERCHE' EREDITA DA DUE CLASSI
        db.Model  -> la rende una tabella
        UserMixin -> le aggiunge i quattro metodi che Flask-Login pretende
                     (is_authenticated, is_active, is_anonymous, get_id).
        Sono due librerie che non si conoscono fra loro e i cui pezzi si
        combinano senza attriti perche' toccano metodi diversi.
    """

    __tablename__ = "utente"

    id: Mapped[int] = mapped_column(primary_key=True)

    email: Mapped[str] = mapped_column(sa.String(120), nullable=False)
    password_hash: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    nome: Mapped[str] = mapped_column(sa.String(80), nullable=False)
    cognome: Mapped[str] = mapped_column(sa.String(80), nullable=False)
    ruolo: Mapped[str] = mapped_column(sa.String(20), nullable=False)

    # Nullabile: nel concettuale apparteneva al solo sottotipo Studente.
    matricola: Mapped[str | None] = mapped_column(sa.String(20))

    # --- scorciatoie verso le pratiche -----------------------------------
    # foreign_keys serve perche' la tabella pratica ha QUATTRO chiavi esterne
    # verso utente: senza indicazione esplicita SQLAlchemy non sa quale
    # seguire e si ferma con un errore all'avvio.
    pratiche_come_studente: Mapped[list[Pratica]] = relationship(
        back_populates="studente",
        foreign_keys="Pratica.studente_id",
    )
    pratiche_come_referente: Mapped[list[Pratica]] = relationship(
        back_populates="docente",
        foreign_keys="Pratica.docente_id",
    )

    __table_args__ = (
        # E' una tupla: la virgola dopo l'ultimo elemento serve davvero.

        # L'identificatore dell'entita' nel modello concettuale.
        sa.UniqueConstraint("email", name="uq_utente_email"),

        # In PostgreSQL un UNIQUE ammette piu' righe con NULL, quindi questo
        # vincolo non disturba docenti e personale d'ufficio.
        sa.UniqueConstraint("matricola", name="uq_utente_matricola"),

        sa.CheckConstraint(
            "ruolo IN ('STUDENTE', 'DOCENTE', 'UFFICIO')",
            name="ck_utente_ruolo",
        ),

        # La matricola c'e' se e solo se l'utente e' uno studente.
        # E' la traccia lasciata dal collasso della generalizzazione: nel
        # concettuale l'attributo stava sul solo sottotipo e non serviva
        # nessun vincolo.
        sa.CheckConstraint(
            "(ruolo = 'STUDENTE') = (matricola IS NOT NULL)",
            name="ck_utente_matricola_solo_studenti",
        ),

        sa.CheckConstraint(
            "length(trim(email)) > 0",
            name="ck_utente_email_non_vuota",
        ),
    )

    # --- password ---------------------------------------------------------
    # La password in chiaro non entra mai nel database. generate_password_hash
    # le applica una funzione di hash lenta e con sale: due utenti con la
    # stessa password ottengono hash diversi, e provarle tutte a forza bruta
    # costa tempo macchina.

    def imposta_password(self, in_chiaro: str) -> None:
        self.password_hash = generate_password_hash(in_chiaro)

    def verifica_password(self, in_chiaro: str) -> bool:
        return check_password_hash(self.password_hash, in_chiaro)

    # --- comodita' per i template -----------------------------------------
    # @property fa si' che si usino senza parentesi: utente.e_studente.
    # Non esistono nel database, sono calcolate ogni volta. Servono a tenere
    # i template leggibili.

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
    """Catalogo degli atenei partner, gestito dall'ufficio Overseas.

    Lo studente sceglie da questa lista, non digita il nome: lo richiede
    esplicitamente il punto 2 dei requisiti funzionali.
    """

    __tablename__ = "istituto"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(sa.String(160), nullable=False)
    paese: Mapped[str] = mapped_column(sa.String(80), nullable=False)
    citta: Mapped[str] = mapped_column(sa.String(80), nullable=False)

    pratiche: Mapped[list[Pratica]] = relationship(back_populates="istituto")

    __table_args__ = (
        # Il nome da solo non basta come identificatore: atenei omonimi in
        # citta' diverse esistono.
        sa.UniqueConstraint("nome", "citta", name="uq_istituto_nome_citta"),
    )

    def __repr__(self) -> str:
        return f"<Istituto {self.nome} ({self.citta})>"


# ===========================================================================
#  CORSO INTERNO
# ===========================================================================

class CorsoInterno(db.Model):
    """Catalogo degli insegnamenti di Ca' Foscari.

    PERCHE' QUI IL CATALOGO C'E' E PER I CORSI ESTERI NO
        Il codice lo assegna Ca' Foscari, che e' la stessa organizzazione che
        ospita l'applicazione: e' stabile e univoco per costruzione, quindi
        la dipendenza funzionale "codice determina titolo e crediti" vale
        davvero. Ripetere titolo e crediti su ogni riconoscimento sarebbe
        ridondanza, con il rischio concreto che lo stesso insegnamento
        risulti riconosciuto con crediti diversi in pratiche diverse.

        Sui corsi esteri quella dipendenza non vale, e infatti la' il
        catalogo non c'e'. La differenza di trattamento e' motivata dalla
        presenza o assenza della dipendenza funzionale, non dallo stile.
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
    """L'entita' centrale: una mobilita' dalla creazione alla chiusura.

    LE QUATTRO CHIAVI ESTERNE VERSO UTENTE, E COSA SIGNIFICANO
        studente_id       relazione "apertura", con data_apertura come suo
                          attributo. E' anche la relazione di titolarita':
                          chi apre la pratica ne e' il proprietario, quindi
                          una relazione sola e non due.
        docente_id        relazione "referenza", senza attributi.
        verificata_da_id  relazione "verifica pre-partenza", cardinalita'
                          (0,1) dal lato pratica.
        chiusa_da_id      relazione "chiusura", (0,1).

        Le ultime due, avendo massimo 1 dal lato pratica, nel modello logico
        non diventano tabelle: collassano in colonne. Da qui nascono i due
        vincoli "o entrambi o nessuno" piu' sotto, che nel concettuale non
        servivano perche' una relazione o c'e' tutta o non c'e'.

    LE DUE DATE CHE INVECE NON SONO ATTRIBUTI DI RELAZIONE
        data_inizio_effettivo e data_fine_effettiva sono fatti sulla
        mobilita' dichiarati dallo studente, non atti amministrativi compiuti
        da qualcuno. Per questo stanno sull'entita'.

    [SQL] Vincoli su questa tabella che l'ORM non puo' esprimere:
        trg_ruoli_pratica       i quattro utenti devono avere il ruolo giusto
                                (legge un'altra tabella)
        trg_transizione_stato   la coppia (stato vecchio, stato nuovo) deve
                                essere ammessa, e le precondizioni sui dati
                                soddisfatte (serve OLD, e conta righe altrove)
        trg_pratica_immutabile  una pratica chiusa non si modifica piu'
    """

    __tablename__ = "pratica"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Identificatore del modello concettuale, affiancato alla chiave
    # surrogata "id" per comodita' dell'ORM.
    codice_pratica: Mapped[str] = mapped_column(sa.String(20), nullable=False)

    anno_accademico: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    periodo: Mapped[str] = mapped_column(sa.String(30), nullable=False)
    stato: Mapped[str] = mapped_column(
        sa.String(30), nullable=False, default="APERTA"
    )
    note: Mapped[str | None] = mapped_column(sa.Text)

    # --- apertura: relazione con lo studente, con la sua data -------------
    studente_id: Mapped[int] = mapped_column(
        sa.ForeignKey("utente.id", ondelete="RESTRICT"), nullable=False
    )
    # ATTENZIONE: default=dt.date.today SENZA parentesi.
    # Con le parentesi si passerebbe il risultato calcolato una volta sola
    # all'avvio del server, e tutte le pratiche avrebbero la stessa data.
    # Senza parentesi si passa la funzione, che viene chiamata a ogni
    # inserimento.
    data_apertura: Mapped[dt.date] = mapped_column(
        sa.Date, nullable=False, default=dt.date.today
    )

    # --- referenza: relazione col docente, senza attributi ----------------
    docente_id: Mapped[int] = mapped_column(
        sa.ForeignKey("utente.id", ondelete="RESTRICT"), nullable=False
    )

    # --- destinazione ------------------------------------------------------
    istituto_id: Mapped[int] = mapped_column(
        sa.ForeignKey("istituto.id", ondelete="RESTRICT"), nullable=False
    )

    # --- verifica pre-partenza: relazione (0,1) con l'ufficio -------------
    verificata_da_id: Mapped[int | None] = mapped_column(
        sa.ForeignKey("utente.id", ondelete="RESTRICT")
    )
    pre_partenza_verificata_il: Mapped[dt.date | None] = mapped_column(sa.Date)

    # --- fatti sulla mobilita', dichiarati dallo studente -----------------
    data_inizio_effettivo: Mapped[dt.date | None] = mapped_column(sa.Date)
    data_fine_effettiva: Mapped[dt.date | None] = mapped_column(sa.Date)

    # --- chiusura: relazione (0,1) con l'ufficio --------------------------
    chiusa_da_id: Mapped[int | None] = mapped_column(
        sa.ForeignKey("utente.id", ondelete="RESTRICT")
    )
    chiusa_il: Mapped[dt.date | None] = mapped_column(sa.Date)

    # --- scorciatoie -------------------------------------------------------
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

    # cascade="all, delete-orphan": cancellando la pratica spariscono le sue
    # versioni di Learning Agreement e il suo Transcript. E' corretto proprio
    # perche' sono entita' deboli: fuori dalla pratica non significano nulla.
    learning_agreements: Mapped[list[LearningAgreement]] = relationship(
        back_populates="pratica",
        cascade="all, delete-orphan",
        order_by="LearningAgreement.numero_versione",
    )
    transcript: Mapped[Transcript | None] = relationship(
        back_populates="pratica", cascade="all, delete-orphan", uselist=False
    )

    __table_args__ = (
        # ------------------------------------------------------------------
        # UNICITA'
        # ------------------------------------------------------------------
        sa.UniqueConstraint("codice_pratica", name="uq_pratica_codice"),

        # Evita il doppione per errore. NON impedisce a uno studente di avere
        # piu' pratiche: la traccia lo consente esplicitamente.
        sa.UniqueConstraint(
            "studente_id", "anno_accademico", "istituto_id",
            name="uq_pratica_studente_anno_istituto",
        ),

        # ------------------------------------------------------------------
        # DOMINIO
        # ------------------------------------------------------------------
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

        # ------------------------------------------------------------------
        # O ENTRAMBI O NESSUNO DEI DUE
        # Nascono dal collasso delle relazioni (0,1) in colonne: una
        # relazione o c'e' tutta o non c'e'.
        # ------------------------------------------------------------------
        sa.CheckConstraint(
            "(verificata_da_id IS NULL) = (pre_partenza_verificata_il IS NULL)",
            name="ck_pratica_verifica_coerente",
        ),
        sa.CheckConstraint(
            "(chiusa_da_id IS NULL) = (chiusa_il IS NULL)",
            name="ck_pratica_chiusura_coerente",
        ),

        # ------------------------------------------------------------------
        # PREREQUISITI FRA FATTI      "se A allora B"  ->  NOT (A) OR (B)
        #
        # Sono ancorati ai fatti, MAI allo stato corrente. Un vincolo del
        # tipo "puoi valorizzare l'inizio solo se lo stato e' PRE_PARTENZA"
        # si romperebbe da solo appena la pratica avanza: un CHECK viene
        # rivalutato a ogni modifica della riga, non solo quando scrivi
        # quella colonna.
        # ------------------------------------------------------------------
        sa.CheckConstraint(
            "NOT (data_inizio_effettivo IS NOT NULL)"
            " OR (pre_partenza_verificata_il IS NOT NULL)",
            name="ck_pratica_inizio_dopo_verifica",
        ),
        sa.CheckConstraint(
            "NOT (data_fine_effettiva IS NOT NULL)"
            " OR (data_inizio_effettivo IS NOT NULL)",
            name="ck_pratica_fine_dopo_inizio",
        ),
        sa.CheckConstraint(
            "NOT (chiusa_il IS NOT NULL)"
            " OR (data_fine_effettiva IS NOT NULL)",
            name="ck_pratica_chiusura_dopo_fine",
        ),

        # ------------------------------------------------------------------
        # ORDINAMENTO TEMPORALE
        # I due controlli sui NULL servono: senza, il confronto darebbe NULL
        # appena una delle due date manca.
        # ------------------------------------------------------------------
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
        sa.CheckConstraint(
            "data_fine_effettiva IS NULL OR chiusa_il IS NULL"
            " OR data_fine_effettiva <= chiusa_il",
            name="ck_pratica_ord_fine_chiusura",
        ),

        # ------------------------------------------------------------------
        # DALLO STATO AI FATTI
        # Sempre in questa direzione, mai il contrario. "Lo stato X implica
        # che il fatto sia gia' avvenuto" resta vero anche negli stati
        # successivi; l'implicazione inversa si romperebbe al primo
        # avanzamento della pratica.
        # ------------------------------------------------------------------
        sa.CheckConstraint(
            "stato NOT IN ('PRE_PARTENZA_COMPLETATA', 'MOBILITA_IN_CORSO',"
            " 'IN_RICONOSCIMENTO_ESAMI', 'CHIUSA')"
            " OR pre_partenza_verificata_il IS NOT NULL",
            name="ck_pratica_stato_implica_verifica",
        ),
        sa.CheckConstraint(
            "stato NOT IN ('MOBILITA_IN_CORSO', 'IN_RICONOSCIMENTO_ESAMI',"
            " 'CHIUSA')"
            " OR data_inizio_effettivo IS NOT NULL",
            name="ck_pratica_stato_implica_inizio",
        ),
        sa.CheckConstraint(
            "stato NOT IN ('IN_RICONOSCIMENTO_ESAMI', 'CHIUSA')"
            " OR data_fine_effettiva IS NOT NULL",
            name="ck_pratica_stato_implica_fine",
        ),
        sa.CheckConstraint(
            "stato <> 'CHIUSA' OR chiusa_il IS NOT NULL",
            name="ck_pratica_chiusa_implica_data",
        ),

        # ------------------------------------------------------------------
        # INDICI PER LE INTERROGAZIONI PIU' FREQUENTI
        # ------------------------------------------------------------------
        # "le mie pratiche" e "le pratiche di cui sono referente" girano a
        # ogni accesso allo spazio personale.
        sa.Index("ix_pratica_studente", "studente_id"),
        sa.Index("ix_pratica_docente", "docente_id"),
        # dashboard dell'ufficio: pratiche per stato e per anno accademico.
        sa.Index("ix_pratica_stato", "stato"),
        sa.Index("ix_pratica_anno_stato", "anno_accademico", "stato"),
    )

    @property
    def learning_agreement_corrente(self) -> LearningAgreement | None:
        """La versione approvata con numero piu' alto, cioe' il piano valido.

        Lavora sugli oggetti gia' caricati in memoria: va bene sulla pagina di
        dettaglio di una pratica. Per un elenco di molte pratiche usare la
        vista v_learning_agreement_corrente, altrimenti si fa una query per
        ogni riga dell'elenco (il problema N+1).
        """
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
    """Una versione del piano concordato. Entita' debole rispetto a Pratica.

    PERCHE' VERSIONI E NON UN DOCUMENTO SOLO
        La traccia impone che, se una modifica proposta durante la mobilita'
        viene rifiutata, "deve essere ripristinata l'associazione degli esami
        precedentemente concordata". Con le versioni quel ripristino non e'
        un'operazione: la versione precedente non e' mai stata toccata e
        resta quella valida. Un progetto che modificasse le righe sul posto
        dovrebbe implementare un annullamento vero, con tutto quello che
        comporta.

    IL FILE NON STA NEL DATABASE
        file_path e' il percorso su disco, dentro la cartella degli upload.
        Il nome con cui il file viene salvato lo genera l'applicazione (un
        UUID), mai l'utente: cosi' nessuno puo' caricare un file chiamato
        "../../config.py". Il nome originale si conserva a parte, e serve
        solo per mostrarlo a video.

    PERCHE' file_path E' NULLABILE
        La riga nasce come bozza quando lo studente comincia a compilare il
        piano; il PDF arriva dopo. Il file diventa obbligatorio al momento
        dell'invio, ed e' il trigger sulla transizione a garantirlo.

    [SQL] trg_la_creabile: una nuova versione si puo' creare solo con la
          pratica in APERTA, ATTESA_APPROVAZIONE_LA o MOBILITA_IN_CORSO.
          Dopo il rientro il piano e' congelato, ed e' questo che garantisce
          che i voti si registrino su una versione che non cambia piu'.
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
        # La chiave del modello concettuale: identificazione esterna, cioe'
        # numero di versione DENTRO la pratica. Qui e' un UNIQUE perche' la
        # chiave primaria e' la surrogata "id".
        sa.UniqueConstraint(
            "pratica_id", "numero_versione", name="uq_la_pratica_versione"
        ),
        sa.CheckConstraint("numero_versione >= 1", name="ck_la_versione_positiva"),

        sa.CheckConstraint(
            "esito IN ('IN_ATTESA', 'APPROVATO', 'RIFIUTATO')",
            name="ck_la_esito",
        ),

        # Se rifiutato, la motivazione e' obbligatoria: lo chiede
        # esplicitamente il punto 4 dei requisiti funzionali.
        sa.CheckConstraint(
            "NOT (esito = 'RIFIUTATO')"
            " OR (motivazione IS NOT NULL AND length(trim(motivazione)) > 0)",
            name="ck_la_motivazione_se_rifiutato",
        ),

        # Una decisione presa ha sempre una data; una non ancora presa non
        # puo' averne una.
        sa.CheckConstraint(
            "(esito = 'IN_ATTESA') = (data_decisione IS NULL)",
            name="ck_la_data_decisione_coerente",
        ),
        sa.CheckConstraint(
            "data_caricamento IS NULL OR data_decisione IS NULL"
            " OR data_caricamento <= data_decisione",
            name="ck_la_ord_caricamento_decisione",
        ),

        # Una sola proposta pendente alla volta per pratica.
        # E' un INDICE UNICO PARZIALE: la clausola WHERE lo limita alle sole
        # righe in attesa. UniqueConstraint non ammette un WHERE, quindi
        # questo vincolo si puo' esprimere solo cosi', ed e' uno degli
        # esempi di vincolo che richiede sintassi specifica del DBMS.
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
    """Il documento rilasciato dall'istituto ospitante. Entita' debole.

    NON HA UN ESITO, ED E' VOLUTO
        Il punto 10 della traccia richiede, per la chiusura, che il Transcript
        sia "stato caricato" - non approvato. La valutazione avviene sui
        singoli esami, non sul documento.

    NON E' COLLEGATO AGLI ESAMI, ED E' VOLUTO
        E' la prova documentale, non il contenitore dei dati. Collegarlo ai
        corsi creerebbe un ciclo nello schema: dal voto si arriverebbe alla
        pratica per due strade diverse, senza nulla che garantisca che
        convergano sulla stessa.
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
        # E' questo UNIQUE a realizzare la cardinalita' (0,1) del
        # concettuale: al massimo un Transcript per pratica.
        sa.UniqueConstraint("pratica_id", name="uq_transcript_pratica"),
    )

    def __repr__(self) -> str:
        return f"<Transcript pratica={self.pratica_id}>"


# ===========================================================================
#  CORSO ESTERNO
# ===========================================================================

class CorsoEsterno(db.Model):
    """Un insegnamento pianificato all'estero, dentro una versione del piano.

    ENTITA' DEBOLE RISPETTO AL LEARNING AGREEMENT
        Il codice non identifica un insegnamento in assoluto: sulle codifiche
        estere non abbiamo autorita', lo stesso codice puo' indicare corsi
        diversi in atenei diversi e cambiare titolo o crediti da un anno
        all'altro. Identifica un corso com'era in quel momento e in quel
        piano, quindi per identificarlo serve anche la versione del Learning
        Agreement a cui appartiene.

    PERCHE' NON UN CATALOGO
        La dipendenza funzionale "codice determina titolo e crediti" non vale
        nel dominio. Non essendoci dipendenza non c'e' ridondanza da
        eliminare, e un catalogo imporrebbe ai dati un vincolo che la realta'
        non rispetta: il primo studente con un codice riusato non riuscirebbe
        a inserire i suoi dati veri.
        La verifica di veridicita' e' affidata al controllo dell'ufficio in
        fase pre-partenza: e' un vincolo di processo, non di schema, e come
        tale e' dichiarato fra le assunzioni.

    [SQL] trg_corso_esterno_modificabile: il contenuto si puo' toccare solo
          finche' la versione a cui appartiene e' IN_ATTESA. E' cio' che
          rende vero l'assunto su cui poggia tutto il versionamento.
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
        # La chiave del concettuale: il codice DENTRO quella versione.
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
    """Il mapping fra un insegnamento estero e uno di Ca' Foscari.

    E' l'unica relazione N:M dello schema, e per questo l'unica che nella
    traduzione logica diventa una tabella. La chiave primaria e' la coppia
    delle due chiavi esterne: la stessa equivalenza non ha senso due volte.

    LE DUE CARDINALITA' N SERVONO ENTRAMBE
        piu' esami esteri riconosciuti su un unico insegnamento interno, e un
        esame estero scomposto su piu' insegnamenti interni. Entrambi i casi
        si ottengono senza modellare nulla in piu'.
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
        # La chiave primaria indicizza gia' il primo campo. Questo indice
        # serve alla direzione opposta: "quali esami esteri sono stati
        # riconosciuti come Basi di Dati".
        sa.Index("ix_equivalenza_interno", "corso_interno_id"),
    )

    def __repr__(self) -> str:
        return f"<Equivalenza {self.corso_esterno_id}->{self.corso_interno_id}>"


# ===========================================================================
#  ESAME
# ===========================================================================

class Esame(db.Model):
    """Il risultato conseguito su un insegnamento estero pianificato.

    PERCHE' UN'ENTITA' SEPARATA E NON DELLE COLONNE NULLABILI SU CorsoEsterno
        Voto e data sono attributi che sono tutti nulli insieme o tutti
        valorizzati insieme: e' la firma di un'entita' nascosta. Con le
        colonne sul corso, il valore NULL significherebbe due cose diverse e
        indistinguibili: "esame non ancora registrato" e "esame che lo
        studente non ha sostenuto". Con l'entita' separata, l'assenza della
        riga e' la seconda, senza bisogno di convenzioni.

    PERCHE' NON UNA GENERALIZZAZIONE
        Un esame non e' un tipo particolare di corso: e' un fatto distinto
        che riguarda un corso. Una gerarchia con un solo sottotipo e nessun
        attributo proprio nel supertipo, nella traduzione logica, avrebbe
        dato comunque questa stessa tabella.

    [SQL] trg_esame_registrabile: si registra solo con la pratica in
          IN_RICONOSCIMENTO_ESAMI, e solo su un corso che appartiene alla
          versione operativa del piano.
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
        # Realizza la cardinalita' (0,1): al massimo un esito per corso.
        sa.UniqueConstraint("corso_esterno_id", name="uq_esame_corso"),

        # Voto in trentesimi. 31 rappresenta la lode; se preferite una
        # colonna booleana separata, si cambia qui e basta.
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

        # "restano esami da valutare in questa pratica?" gira a ogni
        # visualizzazione della pagina dell'ufficio.
        sa.Index("ix_esame_esito", "esito_riconoscimento"),
    )

    def __repr__(self) -> str:
        return f"<Esame corso={self.corso_esterno_id} voto={self.voto}>"


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