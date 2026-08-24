"""Creazione dello schema del database.

USO, dalla cartella radice del progetto:

    python -m scripts.init_db            crea le tabelle mancanti
    python -m scripts.init_db --reset    cancella tutto e ricrea (DISTRUTTIVO)

COSA FA, IN ORDINE
    1. crea tabelle, chiavi, UNIQUE e CHECK a partire dai modelli ORM,
       che sono l'unica definizione dello schema;
    2. esegue schema_extra_postgres.sql, che aggiunge cio' che l'ORM non
       esprime: trigger, viste, viste materializzate, indici parziali, ruoli;
    3. NON inserisce dati: quello e' compito di scripts/seed.py.

    Il passo 2 viene saltato da solo se il database non e' PostgreSQL.

NOTA
    Finche' app/models.py e' vuoto, questo script funziona ma crea zero
    tabelle. E' normale: i modelli si scrivono in Fase 4.
"""

import argparse
import sys
from pathlib import Path

# Permette di lanciare lo script anche con "python scripts/init_db.py",
# aggiungendo la cartella radice ai percorsi in cui Python cerca i moduli.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402

FILE_SQL_EXTRA = Path(__file__).resolve().parent / "schema_extra_postgres.sql"


def esegui_sql_extra() -> None:
    """Applica trigger, viste e indici non esprimibili nell'ORM."""
    dialetto = db.engine.dialect.name
    if dialetto != "postgresql":
        print(f"  [salto] SQL aggiuntivo non eseguito: dialetto '{dialetto}'.")
        return
    if not FILE_SQL_EXTRA.exists():
        print("  [salto] File schema_extra_postgres.sql non trovato.")
        return

    testo = FILE_SQL_EXTRA.read_text(encoding="utf-8").strip()
    if not testo or all(r.lstrip().startswith("--") or not r.strip()
                        for r in testo.splitlines()):
        print("  [salto] File SQL aggiuntivo ancora vuoto.")
        return

    # engine.begin() apre una transazione e fa commit da solo all'uscita:
    # o passa tutto il file, o non passa niente.
    #
    # Si usa exec_driver_sql e NON sa.text(). Due motivi:
    #   - text() interpreterebbe i ":" dell'operatore := del PL/pgSQL come
    #     segnaposto di parametri, e fallirebbe;
    #   - il driver rifiuta un file con piu' istruzioni se ci sono parametri.
    # exec_driver_sql passa la stringa al driver cosi' com'e', che e'
    # esattamente cio' che serve per uno script DDL.
    with db.engine.begin() as conn:
        conn.exec_driver_sql(testo)
    print("  [ok] Trigger, viste e indici aggiuntivi applicati.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Crea lo schema del database.")
    parser.add_argument(
        "--reset", action="store_true",
        help="cancella tutte le tabelle prima di ricrearle (DISTRUTTIVO)",
    )
    argomenti = parser.parse_args()

    app = create_app()
    with app.app_context():
        print(f"Database: {db.engine.url.render_as_string(hide_password=True)}")

        if argomenti.reset:
            conferma = input("Cancello TUTTE le tabelle. Scrivi 'si' per procedere: ")
            if conferma.strip().lower() != "si":
                print("Annullato.")
                return
            db.drop_all()
            print("  [ok] Tabelle esistenti eliminate.")

        db.create_all()
        tabelle = sorted(db.metadata.tables)
        if tabelle:
            print(f"  [ok] Tabelle create: {', '.join(tabelle)}")
        else:
            print("  [!]  Nessuna tabella creata: app/models.py e' ancora vuoto.")
            print("       E' normale finche' non hai fatto la Fase 4.")

        esegui_sql_extra()
        print("Fatto. Passo successivo:  python -m scripts.seed")


if __name__ == "__main__":
    main()
