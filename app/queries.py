"""Interrogazioni analitiche, tutte raccolte in un file solo.

COSA VA QUI
    Le query che non sono un banale "prendimi questo oggetto per id":
    conteggi, raggruppamenti, ricerche con condizioni complesse, statistiche.

COSA NON VA QUI
    Le letture semplici dentro una route (db.session.get, un select con un
    where su una colonna). Quelle restano dove servono.

PERCHE' RACCOGLIERLE
    Due motivi, e il secondo vale piu' del primo.
    1. Le route restano leggibili: si occupano solo di HTTP.
    2. Quando arriverai a scrivere la sezione "Query principali" della
       relazione, il materiale sara' gia' tutto qui, commentato.

COME SI SCRIVONO: ORM + EXPRESSION LANGUAGE
    Le query si costruiscono con select(), che e' la stessa identica funzione
    sia nell'ORM sia nel Core. Il codice resta indipendente dal dialetto SQL,
    che e' esattamente cio' che la traccia chiede al punto 4 degli aspetti
    raccomandati.

    Si ricorre a sa.text() con SQL scritto a mano SOLO dove la versione
    astratta diventerebbe illeggibile (espressioni di finestra, CTE
    ricorsive, funzioni specifiche di PostgreSQL). In quel caso: sempre
    parametri nominati, mai concatenazione di stringhe.

QUANDO LO RIEMPI
    Man mano, dalla Fase 7 in avanti. Ogni volta che in una route ti accorgi
    di star scrivendo una query di piu' di tre righe, spostala qui.

FORMA DI OGNI FUNZIONE
    - nome che dice cosa restituisce
    - docstring con l'SQL equivalente, per la relazione
    - una cosa sola per funzione
"""

import sqlalchemy as sa  # noqa: F401

from app.extensions import db  # noqa: F401

# ---------------------------------------------------------------------------
# ESEMPIO della forma. Cancellalo e scrivi le tue in Fase 7 e Fase 10.
# ---------------------------------------------------------------------------
#
# def pratiche_per_paese(anno_accademico: str | None = None):
#     """Quante mobilita' per ciascun paese.
#
#     SQL equivalente:
#         SELECT i.paese, COUNT(*) AS totale
#         FROM pratica p JOIN istituto i ON p.istituto_id = i.id
#         [WHERE p.anno_accademico = :anno]
#         GROUP BY i.paese
#         ORDER BY totale DESC, i.paese;
#     """
#     query = (
#         sa.select(Istituto.paese, sa.func.count(Pratica.id).label("totale"))
#         .join(Pratica, Pratica.istituto_id == Istituto.id)
#         .group_by(Istituto.paese)
#         .order_by(sa.desc("totale"), Istituto.paese)
#     )
#     if anno_accademico:
#         query = query.where(Pratica.anno_accademico == anno_accademico)
#     return db.session.execute(query).all()
