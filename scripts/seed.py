"""Popolamento del database con dati di prova.  ->  Da scrivere in FASE 4.

USO, dalla cartella radice:

    python -m scripts.seed

I TRE REQUISITI NON NEGOZIABILI

    1. DETERMINISTICO
       Lo stesso script produce sempre lo stesso database. Senza questo i
       test non sono ripetibili e il video della demo non e' preparabile.
       Quindi: niente dati casuali, niente date calcolate da "oggi".

    2. IDEMPOTENTE
       Rilanciarlo non deve duplicare i dati: ogni blocco controlla prima
       se i dati ci sono gia'.

    3. COMPLETO
       Deve esistere almeno una pratica PER OGNI STATO del ciclo di vita,
       piu' i casi non lineari:
         - un Learning Agreement rifiutato, con motivazione
         - una modifica approvata e una rifiutata
         - una pratica chiusa con un esame NON riconosciuto
         - uno studente con due pratiche
       Senza pratiche negli stati avanzati non puoi mostrare meta' delle
       funzionalita' nel video.

ORM O CORE?
    Tutti e due, e la divisione va motivata nella relazione.

    - CORE (sa.insert con una lista di dizionari) per gli inserimenti
      massivi di righe indipendenti, tipo l'elenco degli istituti: non
      servono oggetti, serve solo scrivere righe in fretta.

    - ORM per i dati collegati fra loro, tipo pratiche con i loro esami e
      documenti: qui serve il grafo di oggetti, e l'ORM lo costruisce da
      solo assegnando le chiavi esterne.

LA TRANSAZIONE
    Un solo commit alla fine, dentro un try/except con rollback: o entra
    tutto, o non entra niente. Un database popolato a meta' e' peggio di
    uno vuoto, perche' sembra a posto.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402

PASSWORD_DEMO = "Overseas2026!"


def main() -> None:
    app = create_app()
    with app.app_context():
        print(f"Database: {db.engine.url.render_as_string(hide_password=True)}")

        try:
            # ---------------------------------------------------------------
            # FASE 4 — inserimenti, in quest'ordine:
            #   1. istituti      (Core, inserimento massivo)
            #   2. utenti        (ORM, servono gli oggetti dopo)
            #   3. pratiche      (ORM, con esami e documenti collegati)
            #
            # Esempio di inserimento massivo con il Core:
            #
            # db.session.execute(
            #     sa.insert(Istituto.__table__),
            #     [
            #         {"nome": "Keio University", "paese": "Giappone",
            #          "citta": "Tokyo", "attivo": True},
            #         ...
            #     ],
            # )
            #
            # Esempio con l'ORM, per i dati collegati:
            #
            # p = Pratica(
            #     studente=marco, docente=raffaeta, istituto=keio,
            #     anno_accademico="2025/26", stato=StatoPratica.CREATA,
            #     esami=[EsameMappato(codice_estero="KEI-CS101", ...)],
            # )
            # db.session.add(p)
            # ---------------------------------------------------------------

            print("  [!]  Nessun dato inserito: lo script e' ancora da scrivere.")

            db.session.commit()   # <- UN SOLO commit, alla fine
        except Exception:
            db.session.rollback()
            print("  [errore] Popolamento annullato, nessun dato scritto.")
            raise


if __name__ == "__main__":
    main()
