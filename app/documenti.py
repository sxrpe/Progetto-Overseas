"""Gestione dei file caricati: validazione, archiviazione, lettura.

PERCHE' UN MODULO A PARTE
    La gestione dei file non e' logica HTTP e non e' logica di dominio: e'
    infrastruttura. Se la scrivi dentro le route la ritrovi duplicata in tre
    posti (Learning Agreement, Transcript, modifiche) e la sbagli in due.

QUANDO LO RIEMPI
    Fase 8, subito prima o subito dopo la 7.4.

LE CINQUE REGOLE, in ordine di gravita' se le violi

    1. La cartella degli upload sta FUORI da app/static/.
       Tutto cio' che sta in static/ e' servito direttamente dal server a
       chiunque conosca l'indirizzo. I documenti degli studenti sono dati
       personali: devono passare da una route che verifica i permessi.

    2. Il nome del file scelto dall'utente non si usa mai come nome di
       archiviazione. Puo' contenere percorsi ("../../qualcosa"), caratteri
       che rompono il filesystem, o collidere con un file esistente.
       Si genera un nome nuovo e si conserva l'originale solo come dato da
       mostrare.

    3. L'estensione dichiarata non garantisce il contenuto. Il controllo
       sull'estensione serve a filtrare gli errori onesti, non gli attacchi.

    4. La dimensione massima si imposta in configurazione
       (MAX_CONTENT_LENGTH) e va gestita con un messaggio comprensibile,
       non con un errore 413 grezzo.

    5. File e database devono restare coerenti. Se salvi il file e poi la
       scrittura sul database fallisce, resta un file orfano. Ordine
       consigliato: prima la riga nel database, poi il file; se il salvataggio
       del file fallisce, annulla la transazione.
"""

import uuid
from pathlib import Path

from flask import current_app

# ---------------------------------------------------------------------------
# FASE 8 — da scrivere.
# ---------------------------------------------------------------------------
#
# def estensione_ammessa(nome_file: str) -> bool:
#     """Controlla l'estensione contro l'elenco in configurazione."""
#     return Path(nome_file).suffix.lower() in current_app.config["ALLOWED_UPLOAD_EXTENSIONS"]
#
#
# def nome_archivio(pratica_id: int, nome_originale: str) -> str:
#     """Genera un nome di archiviazione univoco e innocuo.
#
#     uuid4 garantisce che due studenti che caricano "LA.pdf" non si
#     sovrascrivano a vicenda.
#     """
#     estensione = Path(nome_originale).suffix.lower()
#     return f"p{pratica_id}_{uuid.uuid4().hex}{estensione}"
#
#
# def percorso_documento(nome_archivio: str) -> Path:
#     """Percorso assoluto sul disco. Assoluto e non relativo: un percorso
#     relativo cambia significato a seconda della cartella di lavoro."""
#     return current_app.config["UPLOAD_FOLDER"] / nome_archivio
#
#
# def salva(file_ricevuto, pratica_id: int) -> tuple[str, int]:
#     """Salva il file e restituisce (nome_archivio, dimensione_in_byte)."""
#     ...
#
#
# def elimina(nome_archivio: str) -> None:
#     """Rimuove un file dal disco. Serve per ripulire dopo un rollback."""
#     ...
