"""Popolamento del database con dati di prova deterministici.

Esecuzione, dalla cartella radice del progetto:

    python -m scripts.seed

Lo script e' IDEMPOTENTE: se i dati esistono gia' non li duplica, cosi' lo
si puo' rilanciare senza paura. Per ripartire davvero da zero:

    python -m scripts.init_db --reset && python -m scripts.seed

I dati coprono TUTTI gli stati della pratica: senza pratiche negli stati
avanzati non e' possibile mostrare le funzionalita' finali nel video demo.

Nota tecnica: gli inserimenti massivi usano il Core (sa.insert) invece
dell'ORM, perche' qui non servono oggetti ne' logica di dominio: serve
velocita' e controllo sull'SQL prodotto.
"""

import sys
from datetime import date, datetime
from pathlib import Path

import sqlalchemy as sa

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app  # noqa: E402
from app.enums import Esito, Periodo, Ruolo, StatoPratica, TipoDocumento  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models import Documento, EsameMappato, Istituto, Pratica, Utente  # noqa: E402
from app.security import hash_password  # noqa: E402

PASSWORD_DEMO = "Overseas2026!"


# ---------------------------------------------------------------------------
def crea_istituti() -> None:
    """Inserimento massivo con il Core: nessun oggetto, solo righe."""
    if db.session.scalar(sa.select(sa.func.count(Istituto.id))):
        print("  [salto] Istituti gia' presenti.")
        return

    db.session.execute(
        sa.insert(Istituto.__table__),
        [
            {"nome": "University of Melbourne", "paese": "Australia", "citta": "Melbourne", "attivo": True},
            {"nome": "Keio University", "paese": "Giappone", "citta": "Tokyo", "attivo": True},
            {"nome": "University of Toronto", "paese": "Canada", "citta": "Toronto", "attivo": True},
            {"nome": "Universidad de Buenos Aires", "paese": "Argentina", "citta": "Buenos Aires", "attivo": True},
            {"nome": "Fudan University", "paese": "Cina", "citta": "Shanghai", "attivo": True},
            {"nome": "University of Cape Town", "paese": "Sudafrica", "citta": "Citta' del Capo", "attivo": True},
            {"nome": "Boston University", "paese": "Stati Uniti", "citta": "Boston", "attivo": True},
            {"nome": "Seoul National University", "paese": "Corea del Sud", "citta": "Seoul", "attivo": False},
        ],
    )
    print("  [ok] 8 istituti inseriti.")


def crea_utenti() -> dict[str, Utente]:
    """Qui invece usiamo l'ORM: ci servono gli oggetti subito dopo."""
    if db.session.scalar(sa.select(sa.func.count(Utente.id))):
        print("  [salto] Utenti gia' presenti.")
        return {
            u.email: u for u in db.session.scalars(sa.select(Utente)).all()
        }

    hash_comune = hash_password(PASSWORD_DEMO)
    utenti = [
        Utente(email="marco.rossi@stud.unive.it", nome="Marco", cognome="Rossi",
               ruolo=Ruolo.STUDENTE, matricola="890123", password_hash=hash_comune),
        Utente(email="giulia.bianchi@stud.unive.it", nome="Giulia", cognome="Bianchi",
               ruolo=Ruolo.STUDENTE, matricola="890124", password_hash=hash_comune),
        Utente(email="luca.verdi@stud.unive.it", nome="Luca", cognome="Verdi",
               ruolo=Ruolo.STUDENTE, matricola="890125", password_hash=hash_comune),
        Utente(email="a.raffaeta@unive.it", nome="Alessandra", cognome="Raffaeta",
               ruolo=Ruolo.DOCENTE, password_hash=hash_comune),
        Utente(email="p.neri@unive.it", nome="Paolo", cognome="Neri",
               ruolo=Ruolo.DOCENTE, password_hash=hash_comune),
        Utente(email="overseas@unive.it", nome="Ufficio", cognome="Overseas",
               ruolo=Ruolo.UFFICIO, password_hash=hash_comune),
    ]
    db.session.add_all(utenti)
    db.session.flush()  # assegna gli id senza chiudere la transazione
    print(f"  [ok] {len(utenti)} utenti inseriti (password comune: {PASSWORD_DEMO}).")
    return {u.email: u for u in utenti}


def crea_pratiche(utenti: dict[str, Utente]) -> None:
    if db.session.scalar(sa.select(sa.func.count(Pratica.id))):
        print("  [salto] Pratiche gia' presenti.")
        return

    istituti = {
        i.nome: i for i in db.session.scalars(sa.select(Istituto)).all()
    }
    marco = utenti["marco.rossi@stud.unive.it"]
    giulia = utenti["giulia.bianchi@stud.unive.it"]
    luca = utenti["luca.verdi@stud.unive.it"]
    raffaeta = utenti["a.raffaeta@unive.it"]
    neri = utenti["p.neri@unive.it"]

    # --- 1. pratica appena creata, senza documenti ------------------------
    p1 = Pratica(
        studente=marco, docente=raffaeta, istituto=istituti["Keio University"],
        anno_accademico="2025/26", periodo=Periodo.PRIMO_SEMESTRE,
        stato=StatoPratica.CREATA,
        note="Interessato ai corsi di data science.",
        esami=[
            EsameMappato(codice_estero="KEI-CS101", titolo_estero="Database Systems",
                         cfu_estero=6, codice_interno="CT0371",
                         titolo_interno="Basi di Dati", cfu_interno=6),
        ],
    )

    # --- 2. Learning Agreement rifiutato, con motivazione -----------------
    p2 = Pratica(
        studente=marco, docente=raffaeta, istituto=istituti["Fudan University"],
        anno_accademico="2025/26", periodo=Periodo.SECONDO_SEMESTRE,
        stato=StatoPratica.CREATA,
        esami=[
            EsameMappato(codice_estero="FDU-AI200", titolo_estero="Machine Learning",
                         cfu_estero=9, codice_interno="CT0429",
                         titolo_interno="Intelligenza Artificiale", cfu_interno=6),
        ],
        documenti=[
            Documento(tipo=TipoDocumento.LEARNING_AGREEMENT, nome_originale="LA_rossi_v1.pdf",
                      nome_archivio="p2_la_v1.pdf", dimensione_byte=185_000, versione=1,
                      corrente=True, caricato_da_id=marco.id, esito=Esito.RIFIUTATO,
                      motivazione="Squilibrio di crediti fra esame estero e interno.",
                      deciso_il=datetime(2026, 3, 2, 10, 30), deciso_da_id=raffaeta.id),
        ],
    )

    # --- 3. in attesa di approvazione -------------------------------------
    p3 = Pratica(
        studente=giulia, docente=neri, istituto=istituti["University of Toronto"],
        anno_accademico="2025/26", periodo=Periodo.INTERO_ANNO,
        stato=StatoPratica.ATTESA_LA,
        esami=[
            EsameMappato(codice_estero="UT-ECO210", titolo_estero="Microeconomics",
                         cfu_estero=6, codice_interno="ET0055",
                         titolo_interno="Microeconomia", cfu_interno=6),
            EsameMappato(codice_estero="UT-STA220", titolo_estero="Statistics",
                         cfu_estero=6, codice_interno="ET0061",
                         titolo_interno="Statistica", cfu_interno=6),
        ],
        documenti=[
            Documento(tipo=TipoDocumento.LEARNING_AGREEMENT, nome_originale="LA_bianchi.pdf",
                      nome_archivio="p3_la_v1.pdf", dimensione_byte=201_400, versione=1,
                      corrente=True, caricato_da_id=giulia.id, esito=Esito.IN_ATTESA),
        ],
    )

    # --- 4. mobilita' in corso --------------------------------------------
    p4 = Pratica(
        studente=giulia, docente=neri, istituto=istituti["Boston University"],
        anno_accademico="2024/25", periodo=Periodo.PRIMO_SEMESTRE,
        stato=StatoPratica.IN_CORSO,
        arrivo_effettivo=date(2025, 9, 1), partenza_effettiva=date(2026, 1, 20),
        pre_partenza_verificata_il=datetime(2025, 7, 15, 9, 0),
        esami=[
            EsameMappato(codice_estero="BU-CS330", titolo_estero="Algorithms",
                         cfu_estero=8, codice_interno="CT0361",
                         titolo_interno="Algoritmi", cfu_interno=6),
        ],
        documenti=[
            Documento(tipo=TipoDocumento.LEARNING_AGREEMENT, nome_originale="LA_bianchi_bu.pdf",
                      nome_archivio="p4_la_v1.pdf", dimensione_byte=178_900, versione=1,
                      corrente=True, caricato_da_id=giulia.id, esito=Esito.APPROVATO,
                      deciso_il=datetime(2025, 7, 1, 14, 0), deciso_da_id=neri.id),
        ],
    )

    # --- 5. in riconoscimento esami ---------------------------------------
    p5 = Pratica(
        studente=luca, docente=raffaeta, istituto=istituti["University of Melbourne"],
        anno_accademico="2024/25", periodo=Periodo.SECONDO_SEMESTRE,
        stato=StatoPratica.IN_RICONOSCIMENTO,
        arrivo_effettivo=date(2025, 2, 10), partenza_effettiva=date(2025, 6, 30),
        pre_partenza_verificata_il=datetime(2024, 12, 10, 11, 0),
        esami=[
            EsameMappato(codice_estero="UM-INF250", titolo_estero="Web Technologies",
                         cfu_estero=6, codice_interno="CT0372",
                         titolo_interno="Tecnologie Web", cfu_interno=6,
                         voto=28, data_superamento=date(2025, 6, 12)),
            EsameMappato(codice_estero="UM-INF260", titolo_estero="Operating Systems",
                         cfu_estero=6, codice_interno="CT0365",
                         titolo_interno="Sistemi Operativi", cfu_interno=6,
                         voto=24, data_superamento=date(2025, 6, 20)),
        ],
        documenti=[
            Documento(tipo=TipoDocumento.LEARNING_AGREEMENT, nome_originale="LA_verdi.pdf",
                      nome_archivio="p5_la_v1.pdf", dimensione_byte=190_200, versione=1,
                      corrente=True, caricato_da_id=luca.id, esito=Esito.APPROVATO,
                      deciso_il=datetime(2024, 12, 1, 15, 30), deciso_da_id=raffaeta.id),
            Documento(tipo=TipoDocumento.TRANSCRIPT_OF_RECORDS, nome_originale="ToR_verdi.pdf",
                      nome_archivio="p5_tor_v1.pdf", dimensione_byte=140_500, versione=1,
                      corrente=True, caricato_da_id=luca.id, esito=Esito.IN_ATTESA),
        ],
    )

    # --- 6. pratica chiusa, con un esame non riconosciuto -----------------
    p6 = Pratica(
        studente=luca, docente=raffaeta, istituto=istituti["Universidad de Buenos Aires"],
        anno_accademico="2023/24", periodo=Periodo.PRIMO_SEMESTRE,
        stato=StatoPratica.CHIUSA,
        arrivo_effettivo=date(2023, 8, 15), partenza_effettiva=date(2023, 12, 20),
        pre_partenza_verificata_il=datetime(2023, 6, 5, 10, 0),
        chiusa_il=datetime(2024, 3, 1, 16, 45),
        esami=[
            EsameMappato(codice_estero="UBA-DER100", titolo_estero="Derecho Internacional",
                         cfu_estero=6, codice_interno="ET0045",
                         titolo_interno="Diritto Internazionale", cfu_interno=6,
                         voto=27, data_superamento=date(2023, 12, 1),
                         esito=Esito.APPROVATO, deciso_il=datetime(2024, 2, 10, 9, 0)),
            EsameMappato(codice_estero="UBA-ESP110", titolo_estero="Espanol Avanzado",
                         cfu_estero=3, codice_interno="LT0100",
                         titolo_interno="Lingua Spagnola", cfu_interno=6,
                         voto=22, data_superamento=date(2023, 12, 5),
                         esito=Esito.RIFIUTATO,
                         motivazione="Crediti insufficienti rispetto all'esame di destinazione.",
                         deciso_il=datetime(2024, 2, 10, 9, 5)),
        ],
        documenti=[
            Documento(tipo=TipoDocumento.LEARNING_AGREEMENT, nome_originale="LA_verdi_uba.pdf",
                      nome_archivio="p6_la_v1.pdf", dimensione_byte=166_300, versione=1,
                      corrente=True, caricato_da_id=luca.id, esito=Esito.APPROVATO,
                      deciso_il=datetime(2023, 5, 20, 12, 0), deciso_da_id=raffaeta.id),
            Documento(tipo=TipoDocumento.TRANSCRIPT_OF_RECORDS, nome_originale="ToR_verdi_uba.pdf",
                      nome_archivio="p6_tor_v1.pdf", dimensione_byte=133_700, versione=1,
                      corrente=True, caricato_da_id=luca.id, esito=Esito.APPROVATO,
                      deciso_il=datetime(2024, 2, 9, 11, 0), deciso_da_id=raffaeta.id),
        ],
    )

    db.session.add_all([p1, p2, p3, p4, p5, p6])
    print("  [ok] 6 pratiche inserite, una per ogni stato del ciclo di vita.")


# ---------------------------------------------------------------------------
def main() -> None:
    app = create_app()
    with app.app_context():
        print(f"Database: {db.engine.url.render_as_string(hide_password=True)}")
        try:
            crea_istituti()
            utenti = crea_utenti()
            crea_pratiche(utenti)
            # UN SOLO commit alla fine: o entra tutto, o non entra niente.
            db.session.commit()
        except Exception:
            db.session.rollback()
            print("  [errore] Popolamento annullato, nessun dato scritto.")
            raise

        print("\nUtenti di prova (password unica: " + PASSWORD_DEMO + ")")
        for utente in db.session.scalars(sa.select(Utente).order_by(Utente.ruolo)):
            print(f"  {utente.ruolo.value:9s}  {utente.email}")


if __name__ == "__main__":
    main()
