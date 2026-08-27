"""Popolamento del database con dati di prova.

    python -m scripts.seed

COSA FA
    Crea gli utenti, gli istituti partner e il catalogo dei corsi interni, piu'
    una pratica di esempio. Senza questo non potete nemmeno fare login: il
    database e' vuoto.

E' RIESEGUIBILE
    Prima di inserire, cancella tutto quello che aveva inserito prima. Cosi'
    lo potete rilanciare quante volte volete senza accumulare doppioni ne'
    violare i vincoli di unicita'.

PERCHE' NON INSERISCE PRATICHE IN STATI AVANZATI
    Perche' i trigger, giustamente, non lo permettono: una pratica non puo'
    nascere gia' in MOBILITA_IN_CORSO, deve attraversare le transizioni. Per
    la demo si parte da qui e si fa avanzare la pratica dall'interfaccia, che
    e' anche il modo migliore di mostrare che i controlli funzionano.
"""

import datetime as dt

import sqlalchemy as sa

from app import create_app
from app.enums import Periodo, Ruolo, StatoPratica
from app.extensions import db
from app.models import CorsoInterno, Istituto, Pratica, Utente

PASSWORD_DI_PROVA = "overseas"


def svuota() -> None:
    """Cancella i dati esistenti, dal figlio verso il padre.

    L'ordine conta: cancellare prima un utente che ha pratiche verrebbe
    rifiutato dalla chiave esterna (ondelete="RESTRICT"). Si parte quindi
    dalle tabelle che nessuno punta.

    Le tabelle figlie di pratica (learning_agreement, transcript, storico)
    non compaiono: hanno ondelete="CASCADE" e spariscono da sole.
    """
    db.session.execute(sa.delete(Pratica))
    db.session.execute(sa.delete(CorsoInterno))
    db.session.execute(sa.delete(Istituto))
    db.session.execute(sa.delete(Utente))
    db.session.commit()


def crea_utenti() -> dict[str, Utente]:
    """Un utente per ruolo, piu' un secondo studente e un secondo docente.

    Il secondo studente serve a dimostrare il controllo di appartenenza: si
    entra come studente 2 e si prova ad aprire la pratica dello studente 1.
    """
    utenti = {
        "studente": Utente(
            email="studente@stud.unive.it",
            nome="Leonardo", cognome="Rossi",
            ruolo=Ruolo.STUDENTE, matricola="891234",
        ),
        "studente2": Utente(
            email="studente2@stud.unive.it",
            nome="Giulia", cognome="Bianchi",
            ruolo=Ruolo.STUDENTE, matricola="891235",
        ),
        "docente": Utente(
            email="docente@unive.it",
            nome="Alessandra", cognome="Verdi",
            ruolo=Ruolo.DOCENTE,
        ),
        "docente2": Utente(
            email="docente2@unive.it",
            nome="Marco", cognome="Neri",
            ruolo=Ruolo.DOCENTE,
        ),
        "ufficio": Utente(
            email="ufficio@unive.it",
            nome="Chiara", cognome="Gallo",
            ruolo=Ruolo.UFFICIO,
        ),
    }

    for utente in utenti.values():
        # Mai la password in chiaro nel database, nemmeno nei dati di prova.
        utente.imposta_password(PASSWORD_DI_PROVA)
        db.session.add(utente)

    db.session.commit()
    return utenti


def crea_istituti() -> list[Istituto]:
    """Il catalogo degli atenei partner, gestito dall'ufficio."""
    istituti = [
        Istituto(nome="University of California, Berkeley",
                 paese="Stati Uniti", citta="Berkeley"),
        Istituto(nome="University of Tokyo", paese="Giappone", citta="Tokyo"),
        Istituto(nome="University of Melbourne",
                 paese="Australia", citta="Melbourne"),
        Istituto(nome="Universidade de Sao Paulo",
                 paese="Brasile", citta="San Paolo"),
        Istituto(nome="McGill University", paese="Canada", citta="Montreal"),
    ]
    db.session.add_all(istituti)
    db.session.commit()
    return istituti


def crea_corsi_interni() -> list[CorsoInterno]:
    """Il catalogo degli insegnamenti di Ca' Foscari."""
    corsi = [
        CorsoInterno(codice="CT0004", titolo="Basi di dati", crediti=12),
        CorsoInterno(codice="CT0111", titolo="Algoritmi e strutture dati", crediti=12),
        CorsoInterno(codice="CT0371", titolo="Ingegneria del software", crediti=6),
        CorsoInterno(codice="CT0619", titolo="Intelligenza artificiale", crediti=6),
        CorsoInterno(codice="CT0442", titolo="Reti di calcolatori", crediti=6),
        CorsoInterno(codice="CT0126", titolo="Sistemi operativi", crediti=12),
        CorsoInterno(codice="CT0555", titolo="Interazione uomo-macchina", crediti=6),
    ]
    db.session.add_all(corsi)
    db.session.commit()
    return corsi


def crea_pratiche(utenti: dict[str, Utente], istituti: list[Istituto]) -> None:
    """Due pratiche appena aperte, da far avanzare dall'interfaccia."""
    pratiche = [
        Pratica(
            codice_pratica="OVS-2025-001",
            anno_accademico=2025,
            periodo=Periodo.PRIMO_SEMESTRE,
            stato=StatoPratica.APERTA,
            studente_id=utenti["studente"].id,
            docente_id=utenti["docente"].id,
            istituto_id=istituti[0].id,
            data_apertura=dt.date.today(),
            note="Interessata ai corsi di area database.",
        ),
        Pratica(
            codice_pratica="OVS-2025-002",
            anno_accademico=2025,
            periodo=Periodo.INTERO_ANNO,
            stato=StatoPratica.APERTA,
            studente_id=utenti["studente2"].id,
            docente_id=utenti["docente2"].id,
            istituto_id=istituti[1].id,
            data_apertura=dt.date.today(),
        ),
    ]
    db.session.add_all(pratiche)
    db.session.commit()


def main() -> None:
    app = create_app()

    # app_context serve perche' db deve sapere a quale applicazione parla, e
    # fuori da una richiesta HTTP nessuno glielo dice.
    with app.app_context():
        print("Svuoto le tabelle...")
        svuota()

        print("Creo gli utenti...")
        utenti = crea_utenti()

        print("Creo gli istituti partner...")
        istituti = crea_istituti()

        print("Creo il catalogo dei corsi interni...")
        crea_corsi_interni()

        print("Creo le pratiche di esempio...")
        crea_pratiche(utenti, istituti)

        print()
        print("Fatto. Credenziali di prova (password: %s)" % PASSWORD_DI_PROVA)
        for utente in db.session.scalars(sa.select(Utente).order_by(Utente.ruolo)):
            print(f"   {utente.ruolo:<10} {utente.email}")


if __name__ == "__main__":
    main()