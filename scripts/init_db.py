"""Creazione dello schema del database.

Esecuzione, dalla cartella radice del progetto:

    python -m scripts.init_db            # crea le tabelle mancanti
    python -m scripts.init_db --reset    # cancella tutto e ricrea da zero

Lo script fa tre cose, in quest'ordine:

  1. crea tabelle, chiavi, vincoli UNIQUE e CHECK a partire dai modelli ORM,
     che sono l'unica definizione dello schema;
  2. esegue schema_extra_postgres.sql, che aggiunge cio' che l'ORM non
     esprime: trigger, viste, viste materializzate, ruoli;
  3. non inserisce dati: quello e' compito di scripts/seed.py.

Il punto 2 viene saltato automaticamente su SQLite, che non supporta la
maggior parte di quelle istruzioni.
"""

import argparse
import sys
from pathlib import Path

# Permette di eseguire lo script anche con "python scripts/init_db.py".
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402

FILE_SQL_EXTRA = Path(__file__).resolve().parent / "schema_extra_postgres.sql"


def esegui_sql_extra() -> None:
    """Esegue il file SQL con trigger, viste e indici non esprimibili nell'ORM."""
    dialetto = db.engine.dialect.name
    if dialetto != "postgresql":
        print(f"  [salto] SQL aggiuntivo non eseguito: dialetto '{dialetto}'.")
        return
    if not FILE_SQL_EXTRA.exists():
        print("  [salto] File schema_extra_postgres.sql non trovato.")
        return

    testo = FILE_SQL_EXTRA.read_text(encoding="utf-8")
    # engine.begin() apre una transazione e fa commit da solo all'uscita:
    # o passa tutto il file, o non passa niente.
    #
    # Si usa exec_driver_sql e NON sa.text(): text() interpreterebbe i ":"
    # del PL/pgSQL come segnaposto di parametri, e il driver rifiuterebbe un
    # file con piu' istruzioni. exec_driver_sql passa la stringa al driver
    # cosi' com'e', che e' esattamente cio' che serve per uno script DDL.
    with db.engine.begin() as conn:
        conn.exec_driver_sql(testo)
    print("  [ok] Trigger, viste e indici aggiuntivi applicati.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Crea lo schema del database.")
    parser.add_argument(
        "--reset",
        action="store_true",
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
        print(f"  [ok] Tabelle create: {', '.join(sorted(db.metadata.tables))}")

        esegui_sql_extra()
        print("Schema pronto. Passo successivo:  python -m scripts.seed")


if __name__ == "__main__":
    main()
