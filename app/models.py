"""Modelli ORM: l'UNICA definizione dello schema del database.

COSA VA QUI
    Una classe per tabella. Ogni classe descrive colonne, tipi, chiavi
    primarie, chiavi esterne, vincoli UNIQUE e vincoli CHECK.
    Da queste classi il comando db.create_all() genera le tabelle vere.

COSA NON VA QUI
    Trigger, viste, viste materializzate, indici parziali, ruoli e privilegi.
    L'ORM non li esprime: stanno in scripts/schema_extra_postgres.sql.

QUANDO LO RIEMPI
    Fase 4, e SOLO DOPO aver chiuso la progettazione logica della Fase 3.
    Scrivere i modelli prima di aver normalizzato lo schema significa
    riscriverli.

CONVENZIONI DEL PROGETTO
    - chiave primaria surrogata intera, sempre di nome "id"
    - chiave esterna di nome "<tabella>_id"
    - Mapped[str]        -> colonna NOT NULL
    - Mapped[str | None] -> colonna che ammette il valore nullo
    - i vincoli CHECK stanno in __table_args__, accanto alla loro tabella
    - verso utenti e istituti si usa ondelete="RESTRICT": una pratica chiusa
      non deve sparire perche' e' stato cancellato un utente
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship  # noqa: F401

from app.extensions import db


def enum_portabile(tipo, nome_vincolo: str) -> sa.Enum:
    """Mappa un Enum di Python su VARCHAR + CHECK invece che su un ENUM nativo.

    Un tipo ENUM nativo di PostgreSQL e' scomodissimo da modificare dopo la
    creazione. Un VARCHAR con CHECK si modifica con un ALTER, e' ispezionabile
    e funziona identico anche su SQLite.
    """
    return sa.Enum(
        tipo,
        native_enum=False,
        validate_strings=True,
        values_callable=lambda e: [membro.value for membro in e],
        name=nome_vincolo,
    )


# ---------------------------------------------------------------------------
# ESEMPIO della forma che avranno i modelli. Cancellalo e scrivi i tuoi
# in Fase 4, partendo dallo schema logico della Fase 3.
# ---------------------------------------------------------------------------
#
# class Istituto(db.Model):
#     __tablename__ = "istituto"
#
#     id:    Mapped[int]  = mapped_column(primary_key=True)
#     nome:  Mapped[str]  = mapped_column(sa.String(150))
#     paese: Mapped[str]  = mapped_column(sa.String(80), index=True)
#     citta: Mapped[str]  = mapped_column(sa.String(80))
#     attivo: Mapped[bool] = mapped_column(default=True)
#
#     pratiche: Mapped[list[Pratica]] = relationship(back_populates="istituto")
#
#     __table_args__ = (
#         sa.UniqueConstraint("nome", "citta", name="uq_istituto_nome_citta"),
#     )
#
#     def __repr__(self) -> str:
#         return f"<Istituto {self.nome} ({self.paese})>"
