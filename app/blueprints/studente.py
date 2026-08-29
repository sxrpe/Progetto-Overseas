"""Area studente.  ->  Da scrivere in FASE 7 (punti 7.2, 7.3, 7.6, 7.8).

ROUTE PREVISTE
    GET  /studente/pratiche                     elenco delle PROPRIE pratiche
    GET  /studente/pratiche/nuova               form di creazione
    POST /studente/pratiche/nuova               creazione
    POST /studente/pratiche/<id>/esami          aggiunta riga di mapping
    POST /studente/pratiche/<id>/date           date effettive di arrivo/partenza
    POST /studente/pratiche/<id>/documenti      caricamento di un documento

LE DUE REGOLE DA NON VIOLARE MAI IN QUESTO FILE

    1. Il filtro sta NELLA QUERY, non nel template.
       Giusto:     .where(Pratica.studente_id == current_user.id)
       Sbagliato:  caricare tutto e poi nascondere le righe altrui in Jinja.
       La seconda non e' un filtro: e' una falla.

    2. Ogni route che riceve un <id> deve chiamare esigi_accesso().
       Senza, basta cambiare il numero nell'URL per leggere la pratica di un
       altro studente.

ATTENZIONE ALLE QUERY A CASCATA
    Se l'elenco carica 50 pratiche e il template legge pratica.istituto.nome,
    l'ORM esegue 51 query invece di 1. Si risolve chiedendo il caricamento
    anticipato:
        .options(selectinload(Pratica.istituto), selectinload(Pratica.docente))
    Per accorgertene: metti SQL_ECHO=1 nel .env e conta le righe che scorrono.
"""

import sqlalchemy as sa
from flask import Blueprint, render_template
from flask_login import current_user, login_required
from sqlalchemy.orm import selectinload

from app.enums import Ruolo
from app.extensions import db
from app.models import Pratica
from app.security import ruolo_richiesto

studente_bp = Blueprint("studente", __name__)


@studente_bp.route("/pratiche", methods=["GET"])
@login_required
@ruolo_richiesto(Ruolo.STUDENTE)
def elenco_pratiche():
    """Le pratiche dello studente collegato, e solo le sue.
        option pre carica nell'oggetto le informazioni, di base si crea un'oggetto, e poi quando richiedi una info legata
        ad una chiave estera, sotto viene fatta una query, precaricarlo cosi semplifica di molto le richieste al db
        Ordinamento : ordiniamo per anno accademico e sucessivamente per il codice pratica
        scalard e all ci permettono di creare una lista di oggetti python
    """
    pratiche = db.session.scalars(
        sa.select(Pratica)
        .where(Pratica.studente_id == current_user.id)
        .options(
            selectinload(Pratica.istituto),
            selectinload(Pratica.docente),
        )
        .order_by(Pratica.anno_accademico.desc(), Pratica.codice_pratica)
    ).all()

    return render_template("studente/elenco.html", pratiche=pratiche)


