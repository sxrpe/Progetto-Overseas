"""Interrogazioni analitiche, raccolte in un unico modulo.

Tenerle qui invece che sparse nelle route ha due vantaggi:
  - le route restano leggibili e si occupano solo di HTTP;
  - quando si scrive la relazione, le "query principali" sono gia' tutte
    in un file solo, commentate e pronte da citare.

Sono espresse con select(), cioe' Expression Language: restano indipendenti
dal dialetto SQL, come richiesto dalla traccia. L'SQL effettivamente inviato
al database si legge attivando SQL_ECHO=1 nel file .env.
"""

import sqlalchemy as sa

from app.enums import Esito, StatoPratica, TipoDocumento
from app.extensions import db
from app.models import Documento, Istituto, Pratica


def pratiche_per_paese(anno_accademico: str | None = None) -> list[sa.Row]:
    """Quante mobilita' per ciascun paese, facoltativamente in un dato anno.

    SQL equivalente:
        SELECT i.paese, COUNT(*) AS totale
        FROM pratica p JOIN istituto i ON p.istituto_id = i.id
        [WHERE p.anno_accademico = :anno]
        GROUP BY i.paese
        ORDER BY totale DESC, i.paese;
    """
    query = (
        sa.select(Istituto.paese, sa.func.count(Pratica.id).label("totale"))
        .join(Pratica, Pratica.istituto_id == Istituto.id)
        .group_by(Istituto.paese)
        .order_by(sa.desc("totale"), Istituto.paese)
    )
    if anno_accademico:
        query = query.where(Pratica.anno_accademico == anno_accademico)
    return db.session.execute(query).all()


def conteggio_per_stato() -> dict[StatoPratica, int]:
    """Distribuzione delle pratiche per stato, per il cruscotto dell'ufficio."""
    righe = db.session.execute(
        sa.select(Pratica.stato, sa.func.count(Pratica.id)).group_by(Pratica.stato)
    ).all()
    return {stato: totale for stato, totale in righe}


def documenti_in_attesa() -> list[Documento]:
    """Documenti caricati e non ancora valutati, i piu' vecchi per primi."""
    return list(
        db.session.scalars(
            sa.select(Documento)
            .where(Documento.esito == Esito.IN_ATTESA, Documento.corrente.is_(True))
            .order_by(Documento.caricato_il)
        )
    )


def pratiche_incomplete() -> list[Pratica]:
    """Pratiche avviate ma prive del Learning Agreement approvato.

    Usa NOT EXISTS: e' il modo piu' efficiente di esprimere "non esiste alcun
    documento approvato di questo tipo per questa pratica".
    """
    documento_approvato = (
        sa.select(Documento.id)
        .where(
            Documento.pratica_id == Pratica.id,
            Documento.tipo == TipoDocumento.LEARNING_AGREEMENT,
            Documento.esito == Esito.APPROVATO,
        )
        .exists()
    )
    return list(
        db.session.scalars(
            sa.select(Pratica)
            .where(Pratica.stato != StatoPratica.CHIUSA, ~documento_approvato)
            .order_by(Pratica.data_creazione)
        )
    )
