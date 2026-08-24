"""Modelli ORM: unica definizione dello schema relazionale.

Convenzioni adottate in tutto il file:

  - chiavi primarie surrogate intere, per semplificare le join e l'uso nell'ORM;
  - le chiavi naturali restano dichiarate come vincoli UNIQUE;
  - ogni colonna obbligatoria e' NOT NULL (Mapped[T] senza Optional);
  - i vincoli CHECK stanno in __table_args__, accanto alla tabella che vincolano;
  - nessuna cancellazione a cascata verso i dati amministrativi storici.

Trigger, viste e indici particolari NON stanno qui: sono in
scripts/schema_extra_postgres.sql, perche' l'ORM non li esprime.
"""

from __future__ import annotations

from datetime import date, datetime

import sqlalchemy as sa
from flask_login import UserMixin
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.enums import Esito, Periodo, Ruolo, StatoPratica, TipoDocumento
from app.extensions import db


def _enum(tipo, nome_vincolo: str) -> sa.Enum:
    """Enum portabile: VARCHAR + CHECK, invece di un tipo ENUM nativo."""
    return sa.Enum(
        tipo,
        native_enum=False,
        validate_strings=True,
        values_callable=lambda e: [membro.value for membro in e],
        name=nome_vincolo,
    )


# ---------------------------------------------------------------------------
# Utenti
# ---------------------------------------------------------------------------
class Utente(UserMixin, db.Model):
    __tablename__ = "utente"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(sa.String(120), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(sa.String(255))
    nome: Mapped[str] = mapped_column(sa.String(60))
    cognome: Mapped[str] = mapped_column(sa.String(60))
    ruolo: Mapped[Ruolo] = mapped_column(_enum(Ruolo, "ck_utente_ruolo"), index=True)
    matricola: Mapped[str | None] = mapped_column(sa.String(10), unique=True)
    attivo: Mapped[bool] = mapped_column(default=True)

    pratiche_da_studente: Mapped[list[Pratica]] = relationship(
        back_populates="studente", foreign_keys="Pratica.studente_id"
    )
    pratiche_da_referente: Mapped[list[Pratica]] = relationship(
        back_populates="docente", foreign_keys="Pratica.docente_id"
    )

    __table_args__ = (
        # La matricola esiste se e solo se l'utente e' uno studente.
        sa.CheckConstraint(
            "(ruolo = 'studente' AND matricola IS NOT NULL)"
            " OR (ruolo <> 'studente' AND matricola IS NULL)",
            name="ck_utente_matricola_solo_studenti",
        ),
    )

    @property
    def nominativo(self) -> str:
        return f"{self.cognome} {self.nome}"

    def ha_ruolo(self, *ruoli: Ruolo) -> bool:
        return self.ruolo in ruoli

    def __repr__(self) -> str:
        return f"<Utente {self.email} ({self.ruolo.value})>"


# ---------------------------------------------------------------------------
# Istituti partner
# ---------------------------------------------------------------------------
class Istituto(db.Model):
    __tablename__ = "istituto"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(sa.String(150))
    paese: Mapped[str] = mapped_column(sa.String(80), index=True)
    citta: Mapped[str] = mapped_column(sa.String(80))
    attivo: Mapped[bool] = mapped_column(default=True)

    pratiche: Mapped[list[Pratica]] = relationship(back_populates="istituto")

    __table_args__ = (
        sa.UniqueConstraint("nome", "citta", name="uq_istituto_nome_citta"),
    )

    def __repr__(self) -> str:
        return f"<Istituto {self.nome} ({self.paese})>"


# ---------------------------------------------------------------------------
# Pratica di mobilita'
# ---------------------------------------------------------------------------
class Pratica(db.Model):
    __tablename__ = "pratica"

    id: Mapped[int] = mapped_column(primary_key=True)
    studente_id: Mapped[int] = mapped_column(
        sa.ForeignKey("utente.id", ondelete="RESTRICT"), index=True
    )
    docente_id: Mapped[int] = mapped_column(
        sa.ForeignKey("utente.id", ondelete="RESTRICT"), index=True
    )
    istituto_id: Mapped[int] = mapped_column(
        sa.ForeignKey("istituto.id", ondelete="RESTRICT"), index=True
    )

    anno_accademico: Mapped[str] = mapped_column(sa.String(9), index=True)
    periodo: Mapped[Periodo] = mapped_column(_enum(Periodo, "ck_pratica_periodo"))
    stato: Mapped[StatoPratica] = mapped_column(
        _enum(StatoPratica, "ck_pratica_stato"),
        default=StatoPratica.CREATA,
        index=True,
    )
    note: Mapped[str | None] = mapped_column(sa.Text)

    data_creazione: Mapped[datetime] = mapped_column(server_default=sa.func.now())
    arrivo_effettivo: Mapped[date | None]
    partenza_effettiva: Mapped[date | None]
    pre_partenza_verificata_il: Mapped[datetime | None]
    chiusa_il: Mapped[datetime | None]

    studente: Mapped[Utente] = relationship(
        back_populates="pratiche_da_studente", foreign_keys=[studente_id]
    )
    docente: Mapped[Utente] = relationship(
        back_populates="pratiche_da_referente", foreign_keys=[docente_id]
    )
    istituto: Mapped[Istituto] = relationship(back_populates="pratiche")
    esami: Mapped[list[EsameMappato]] = relationship(
        back_populates="pratica",
        cascade="all, delete-orphan",
        order_by="EsameMappato.codice_estero",
    )
    documenti: Mapped[list[Documento]] = relationship(
        back_populates="pratica",
        cascade="all, delete-orphan",
        order_by="Documento.caricato_il.desc()",
    )
    modifiche: Mapped[list[ModificaLA]] = relationship(
        back_populates="pratica", cascade="all, delete-orphan"
    )

    __table_args__ = (
        sa.CheckConstraint(
            "studente_id <> docente_id", name="ck_pratica_studente_diverso_docente"
        ),
        sa.CheckConstraint(
            "partenza_effettiva IS NULL OR arrivo_effettivo IS NULL"
            " OR partenza_effettiva >= arrivo_effettivo",
            name="ck_pratica_date_coerenti",
        ),
        sa.CheckConstraint(
            "anno_accademico LIKE '____/__'", name="ck_pratica_formato_anno"
        ),
        # Uno studente non puo' avere due pratiche per lo stesso anno e istituto.
        sa.UniqueConstraint(
            "studente_id",
            "anno_accademico",
            "istituto_id",
            name="uq_pratica_studente_anno_istituto",
        ),
        # Indice composto per la query piu' frequente dell'ufficio.
        sa.Index("ix_pratica_stato_anno", "stato", "anno_accademico"),
    )

    # --- proprieta' derivate, comode nei template -------------------------
    @property
    def cfu_esteri(self) -> int:
        return sum(e.cfu_estero for e in self.esami)

    @property
    def cfu_interni(self) -> int:
        return sum(e.cfu_interno for e in self.esami)

    @property
    def learning_agreement(self) -> Documento | None:
        """Ultima versione corrente del Learning Agreement."""
        return next(
            (
                d
                for d in self.documenti
                if d.tipo is TipoDocumento.LEARNING_AGREEMENT and d.corrente
            ),
            None,
        )

    @property
    def transcript(self) -> Documento | None:
        return next(
            (
                d
                for d in self.documenti
                if d.tipo is TipoDocumento.TRANSCRIPT_OF_RECORDS and d.corrente
            ),
            None,
        )

    def __repr__(self) -> str:
        return f"<Pratica {self.id} {self.anno_accademico} {self.stato.value}>"


# ---------------------------------------------------------------------------
# Mapping esame estero <-> esame di Ca' Foscari
# ---------------------------------------------------------------------------
class EsameMappato(db.Model):
    __tablename__ = "esame_mappato"

    id: Mapped[int] = mapped_column(primary_key=True)
    pratica_id: Mapped[int] = mapped_column(
        sa.ForeignKey("pratica.id", ondelete="CASCADE"), index=True
    )

    codice_estero: Mapped[str] = mapped_column(sa.String(30))
    titolo_estero: Mapped[str] = mapped_column(sa.String(200))
    cfu_estero: Mapped[int]

    codice_interno: Mapped[str] = mapped_column(sa.String(30))
    titolo_interno: Mapped[str] = mapped_column(sa.String(200))
    cfu_interno: Mapped[int]

    # Compilati dallo studente dopo il caricamento del Transcript of Records.
    voto: Mapped[int | None]
    data_superamento: Mapped[date | None]

    # Compilati dal docente in fase di riconoscimento.
    esito: Mapped[Esito] = mapped_column(
        _enum(Esito, "ck_esame_esito"), default=Esito.IN_ATTESA
    )
    motivazione: Mapped[str | None] = mapped_column(sa.Text)
    deciso_il: Mapped[datetime | None]

    pratica: Mapped[Pratica] = relationship(back_populates="esami")

    __table_args__ = (
        sa.UniqueConstraint(
            "pratica_id", "codice_estero", name="uq_esame_pratica_codice"
        ),
        sa.CheckConstraint("cfu_estero > 0 AND cfu_estero <= 30", name="ck_esame_cfu_estero"),
        sa.CheckConstraint("cfu_interno > 0 AND cfu_interno <= 30", name="ck_esame_cfu_interno"),
        sa.CheckConstraint(
            "voto IS NULL OR (voto >= 18 AND voto <= 31)", name="ck_esame_voto"
        ),
        # Un rifiuto deve essere motivato.
        sa.CheckConstraint(
            "esito <> 'rifiutato' OR motivazione IS NOT NULL",
            name="ck_esame_rifiuto_motivato",
        ),
        # Non si puo' decidere su un esame privo di voto.
        sa.CheckConstraint(
            "esito = 'in_attesa' OR voto IS NOT NULL", name="ck_esame_decisione_dopo_voto"
        ),
    )

    @property
    def voto_registrato(self) -> bool:
        return self.voto is not None

    def __repr__(self) -> str:
        return f"<EsameMappato {self.codice_estero} -> {self.codice_interno}>"


# ---------------------------------------------------------------------------
# Documenti allegati
# ---------------------------------------------------------------------------
class Documento(db.Model):
    __tablename__ = "documento"

    id: Mapped[int] = mapped_column(primary_key=True)
    pratica_id: Mapped[int] = mapped_column(
        sa.ForeignKey("pratica.id", ondelete="CASCADE"), index=True
    )
    caricato_da_id: Mapped[int] = mapped_column(
        sa.ForeignKey("utente.id", ondelete="RESTRICT")
    )

    tipo: Mapped[TipoDocumento] = mapped_column(_enum(TipoDocumento, "ck_documento_tipo"))
    nome_originale: Mapped[str] = mapped_column(sa.String(255))
    nome_archivio: Mapped[str] = mapped_column(sa.String(255), unique=True)
    dimensione_byte: Mapped[int]
    versione: Mapped[int] = mapped_column(default=1)
    corrente: Mapped[bool] = mapped_column(default=True)
    caricato_il: Mapped[datetime] = mapped_column(server_default=sa.func.now())

    # Valutazione del docente referente.
    esito: Mapped[Esito] = mapped_column(
        _enum(Esito, "ck_documento_esito"), default=Esito.IN_ATTESA
    )
    motivazione: Mapped[str | None] = mapped_column(sa.Text)
    deciso_il: Mapped[datetime | None]
    deciso_da_id: Mapped[int | None] = mapped_column(
        sa.ForeignKey("utente.id", ondelete="RESTRICT")
    )

    pratica: Mapped[Pratica] = relationship(back_populates="documenti")

    __table_args__ = (
        sa.UniqueConstraint(
            "pratica_id", "tipo", "versione", name="uq_documento_versione"
        ),
        sa.CheckConstraint("dimensione_byte > 0", name="ck_documento_dimensione"),
        sa.CheckConstraint("versione >= 1", name="ck_documento_versione"),
        sa.CheckConstraint(
            "esito <> 'rifiutato' OR motivazione IS NOT NULL",
            name="ck_documento_rifiuto_motivato",
        ),
        sa.Index("ix_documento_in_attesa", "esito", "tipo"),
    )

    def __repr__(self) -> str:
        return f"<Documento {self.tipo.value} v{self.versione} pratica={self.pratica_id}>"


# ---------------------------------------------------------------------------
# Modifiche al Learning Agreement
# ---------------------------------------------------------------------------
class ModificaLA(db.Model):
    """Proposta di modifica del piano durante la mobilita'.

    Il campo snapshot_precedente conserva in JSON il mapping approvato prima
    della proposta: in caso di rifiuto il ripristino avviene da qui, come
    richiesto dalla traccia.
    """

    __tablename__ = "modifica_la"

    id: Mapped[int] = mapped_column(primary_key=True)
    pratica_id: Mapped[int] = mapped_column(
        sa.ForeignKey("pratica.id", ondelete="CASCADE"), index=True
    )
    documento_id: Mapped[int | None] = mapped_column(
        sa.ForeignKey("documento.id", ondelete="SET NULL")
    )

    numero: Mapped[int]
    esito: Mapped[Esito] = mapped_column(
        _enum(Esito, "ck_modifica_esito"), default=Esito.IN_ATTESA
    )
    motivazione: Mapped[str | None] = mapped_column(sa.Text)
    snapshot_precedente: Mapped[str] = mapped_column(sa.Text)
    proposta_il: Mapped[datetime] = mapped_column(server_default=sa.func.now())
    decisa_il: Mapped[datetime | None]

    pratica: Mapped[Pratica] = relationship(back_populates="modifiche")

    __table_args__ = (
        sa.UniqueConstraint("pratica_id", "numero", name="uq_modifica_numero"),
        sa.CheckConstraint("numero >= 1", name="ck_modifica_numero"),
        sa.CheckConstraint(
            "esito <> 'rifiutato' OR motivazione IS NOT NULL",
            name="ck_modifica_rifiuto_motivato",
        ),
    )

    def __repr__(self) -> str:
        return f"<ModificaLA {self.numero} pratica={self.pratica_id} {self.esito.value}>"
