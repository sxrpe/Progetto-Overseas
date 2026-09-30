"""
DESCRIZIONE
    Crea le tabelle del database a partire dai modelli ORM.
    Poi, su PostgreSQL, applica anche schema_extra_postgres.sql
    (trigger, viste, indici che l'ORM non esprime).
    Non inserisce dati: quello lo fa scripts/seed.py.

USO
    python -m scripts.init_db
    python -m scripts.init_db --reset
"""

import argparse
import sys
from pathlib import Path

# Consente di lanciare anche con python scripts/init_db.py.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402

FILE_SQL_EXTRA = Path(__file__).resolve().parent / "schema_extra_postgres.sql"


def esegui_sql_extra() -> None:
    """Applica il file SQL aggiuntivo, se il database è PostgreSQL."""
    dialetto = db.engine.dialect.name
    if dialetto != "postgresql":
        print(f"  [salto] SQL aggiuntivo non eseguito: dialetto '{dialetto}'.")
        return
    if not FILE_SQL_EXTRA.exists():
        print("  [salto] File schema_extra_postgres.sql non trovato.")
        return

    testo = FILE_SQL_EXTRA.read_text(encoding="utf-8").strip()
    if not testo or all(
        r.lstrip().startswith("--") or not r.strip()
        for r in testo.splitlines()
    ):
        print("  [salto] File SQL aggiuntivo ancora vuoto.")
        return

    # Si usa il cursore grezzo del driver, non conn.execute().
    # Nel PL/pgSQL il simbolo % appare nei messaggi di errore, e psycopg
    # lo interpreta come segnaposto dei parametri. Passando solo il testo,
    # senza lista di parametri, la stringa arriva a PostgreSQL così com'è.
    # Anche i ":" di := darebbero problemi con sa.text(), per lo stesso motivo.
    with db.engine.begin() as conn:
        cursore = conn.connection.cursor()
        try:
            cursore.execute(testo)
        finally:
            cursore.close()

    print("  [ok] Trigger, viste e indici aggiuntivi applicati.")


def main() -> None:
    """Crea lo schema, con reset opzionale delle tabelle esistenti."""
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

        esegui_sql_extra()
        print("Fatto. Passo successivo:  python -m scripts.seed")


if __name__ == "__main__":
    main()
