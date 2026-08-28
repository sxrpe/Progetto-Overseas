"""Dettaglio della pratica: la pagina condivisa dai tre ruoli.

PERCHE' UN BLUEPRINT SUO
    La pagina di dettaglio serve a tutti e tre i ruoli: cambiano solo i
    comandi disponibili, decisi dai controlli in security.py. Metterla sotto
    /studente/ costringerebbe un docente a navigare in un indirizzo che dice
    il contrario di quello che sta facendo.

    E' anche il centro dell'applicazione: da qui si raggiungono tutte le
    altre azioni, ed e' la schermata che si vede di piu' nel video.

UNA PAGINA PER CONCETTO, NON UNA PER RUOLO
    Tre pagine quasi identiche significherebbero correggere ogni cosa tre
    volte, e due volte su tre dimenticarsene.
"""

import sqlalchemy as sa
from flask import Blueprint, abort, render_template
from sqlalchemy.orm import selectinload
from flask_login import login_required



from app.extensions import db
from app.models import CorsoEsterno, LearningAgreement, Pratica
from app.security import esigi_accesso

pratiche_bp = Blueprint("pratiche", __name__, url_prefix="/pratiche")

"Stiamo dando alla tabella delle rotte che si crea flask che accetta solo interi se non ce intero rifiuta la rotta, il comando Blueprint() serve appunto perche crea questa tabella"
@pratiche_bp.route("/<int:id_pratica>")
@login_required
def dettaglio(id_pratica: int):
    """Mostra una pratica, a chi ha diritto di vederla.

    LE PRIME TRE RIGHE SONO LO SCHEMA DA RIPETERE OVUNQUE

        pratica = db.session.get(Pratica, id_pratica)
        if pratica is None:
            abort(404)
        esigi_accesso(pratica)

    La prima carica. La seconda gestisce l'id inventato. La terza verifica
    che chi chiede abbia diritto: studente solo le proprie, docente solo
    quelle di cui e' referente, ufficio tutte.

    PERCHE' NON C'E' @ruolo_richiesto QUI
        Perche' tutti e tre i ruoli possono vedere questa pagina. Il
        controllo non e' sul TIPO di utente ma sul LEGAME fra quell'utente e
        quella pratica, ed e' esattamente cio' che fa esigi_accesso.

        Non serve nemmeno @login_required: esigi_accesso, su un utente
        anonimo, risponde comunque 404.

    PERCHE' esigi_accesso RISPONDE 404 E NON 403
        Un 403 direbbe "questa pratica esiste ma non e' tua". Provando gli
        identificatori uno per uno si scoprirebbe quante pratiche ci sono e
        quali numeri sono in uso. Il 404 non distingue fra "non esiste" e
        "non e' tua", e non lascia trapelare niente.

    IL CARICAMENTO ANTICIPATO
        La pagina mostra istituto, docente, tutte le versioni del piano con
        dentro i corsi, le loro equivalenze e i voti. Senza selectinload
        sarebbero decine di query separate: e' il problema N+1.

        selectinload(A).selectinload(B) segue la catena di un livello in
        piu': "caricami i corsi di ogni versione, e per ogni corso anche le
        sue equivalenze".
    """
    pratica = db.session.get(Pratica, id_pratica)
    if pratica is None:
        abort(404)
    esigi_accesso(pratica)

    # Tutte le versioni del piano, con il loro contenuto, in poche query.
    versioni = db.session.scalars(
        sa.select(LearningAgreement)
        .where(LearningAgreement.pratica_id == pratica.id)
        .options(
            selectinload(LearningAgreement.corsi_esterni).selectinload(
                CorsoEsterno.esame
            ),
            selectinload(LearningAgreement.corsi_esterni)
            .selectinload(CorsoEsterno.equivalenze),
        )
        .order_by(LearningAgreement.numero_versione.desc())
    ).all()

    return render_template(
        "pratiche/dettaglio.html",
        pratica=pratica,
        versioni=versioni,
        corrente=pratica.learning_agreement_corrente,
    )