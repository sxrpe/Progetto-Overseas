"""
DESCRIZIONE
    Inserisce i dati di prova: utenti, istituti e corsi interni.
    Senza questo il database è vuoto e non si può fare login.
    Si può rilanciare: prima svuota ciò che aveva inserito, poi ricrea tutto.

USO
    python -m scripts.seed

    Password di tutti gli account di prova: overseas
"""

import sqlalchemy as sa

from app import create_app
from app.enums import Ruolo
from app.extensions import db
from app.models import CorsoInterno, Istituto, Pratica, Utente

PASSWORD_DI_PROVA = "overseas"


def svuota() -> None:
    """Cancella i dati di prova, dalle tabelle figlie verso i padri.

    L'ordine conta perché le chiavi esterne verso utente e istituto
    sono RESTRICT: non si può togliere un utente che ha ancora pratiche.
    Learning Agreement e Transcript seguono la pratica in CASCADE.
    """
    db.session.execute(sa.delete(Pratica))
    db.session.execute(sa.delete(CorsoInterno))
    db.session.execute(sa.delete(Istituto))
    db.session.execute(sa.delete(Utente))
    db.session.commit()


def crea_utenti() -> dict[str, Utente]:
    """Un account per ruolo, più un secondo studente e un secondo docente.

    Il secondo studente serve a verificare che nessuno apra le pratiche altrui.
    """
    utenti = {
        "studente": Utente(
            email="leonardo.rossi@stud.unive.it",
            nome="Leonardo", cognome="Rossi",
            ruolo=Ruolo.STUDENTE, matricola="891234",
        ),
        "studente2": Utente(
            email="giulia.bianchi@stud.unive.it",
            nome="Giulia", cognome="Bianchi",
            ruolo=Ruolo.STUDENTE, matricola="891235",
        ),
        "docente": Utente(
            email="alessandra.verdi@unive.it",
            nome="Alessandra", cognome="Verdi",
            ruolo=Ruolo.DOCENTE,
        ),
        "docente2": Utente(
            email="marco.neri@unive.it",
            nome="Marco", cognome="Neri",
            ruolo=Ruolo.DOCENTE,
        ),
        "ufficio": Utente(
            email="chiara.gallo@unive.it",
            nome="Chiara", cognome="Gallo",
            ruolo=Ruolo.UFFICIO,
        ),
    }

    for utente in utenti.values():
        # Anche nei dati di prova la password in chiaro non entra nel database.
        utente.imposta_password(PASSWORD_DI_PROVA)
        db.session.add(utente)

    db.session.commit()
    return utenti


def crea_istituti() -> list[Istituto]:
    """Catalogo iniziale degli atenei partner."""
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
    """Catalogo iniziale degli insegnamenti di Ca' Foscari."""
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


def main() -> None:
    """Svuota, ripopola e stampa le credenziali di prova."""
    app = create_app()

    # Fuori da una richiesta HTTP serve il contesto applicazione, altrimenti
    # db non sa a quale app è collegato.
    with app.app_context():
        print("Svuoto le tabelle...")
        svuota()

        print("Creo gli utenti...")
        crea_utenti()

        print("Creo gli istituti partner...")
        crea_istituti()

        print("Creo il catalogo dei corsi interni...")
        crea_corsi_interni()

        print()
        print("Fatto. Credenziali di prova (password: %s)" % PASSWORD_DI_PROVA)
        for utente in db.session.scalars(sa.select(Utente).order_by(Utente.ruolo)):
            print(f"   {utente.ruolo:<10} {utente.email}")


if __name__ == "__main__":
    main()
