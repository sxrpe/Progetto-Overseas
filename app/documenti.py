"""
DESCRIZIONE
    Servizio file e PDF: non è un blueprint, nessuna route.
    (salvare/cancellare upload e generare il Learning Agreement).

REGOLE SUI FILE
    1. Il nome su disco lo genera l'app, mai l'utente.
       (Un nome tipo "../../config.py" potrebbe sovrascrivere codice.)
    2. Il nome originale resta in colonna (solo per mostrarlo), non nel path.
    3. Controllo Permessi: altrimenti Flask servirebbe i file a chiunque
       conosca l'URL. L'accesso passa da una route che controlla i permessi.
"""

from __future__ import annotations

import datetime as dt
import uuid
from pathlib import Path

from flask import current_app
from fpdf import FPDF
from fpdf.enums import XPos, YPos
from werkzeug.utils import secure_filename

# ============================================================================
# FILE CARICATI
# ============================================================================

ESTENSIONI_AMMESSE = {".pdf"}
DIMENSIONE_MASSIMA = 5 * 1024 * 1024      # 5 MB


class DocumentoNonValido(Exception):
    """File non accettabile. Il messaggio è pensato per il flash all'utente."""


def cartella_documenti() -> Path:
    """Cartella upload da config (UPLOAD_FOLDER)

    mkdir se non esiste ancora.
    """
    cartella = Path(current_app.config["UPLOAD_FOLDER"])
    cartella.mkdir(parents=True, exist_ok=True)
    return cartella


def salva_documento(file_caricato) -> tuple[str, str]:
    """Salva un upload e restituisce (nome_su_disco, nome_originale).

    file_caricato arriva da request.files[...].

    Il nome su disco è un UUID + estensione ammessa.
    """
    if file_caricato is None or not file_caricato.filename:
        raise DocumentoNonValido("Nessun file selezionato.")

    nome_originale = secure_filename(file_caricato.filename)
    estensione = Path(nome_originale).suffix.lower()

    if estensione not in ESTENSIONI_AMMESSE:
        ammesse = ", ".join(sorted(ESTENSIONI_AMMESSE))
        raise DocumentoNonValido(f"Formato non ammesso: sono accettati {ammesse}.")

    # Dimensione: seek a fine file, tell() legge i byte, poi rewind a 0
    file_caricato.seek(0, 2)
    dimensione = file_caricato.tell()
    file_caricato.seek(0)

    if dimensione == 0:
        raise DocumentoNonValido("Il file è vuoto.")
    if dimensione > DIMENSIONE_MASSIMA:
        massimo_mb = DIMENSIONE_MASSIMA // (1024 * 1024)
        raise DocumentoNonValido(f"Il file supera {massimo_mb} MB.")

    nome_su_disco = f"{uuid.uuid4().hex}{estensione}"
    file_caricato.save(cartella_documenti() / nome_su_disco)

    return nome_su_disco, nome_originale


def percorso_documento(nome_su_disco: str) -> Path:
    """Percorso completo di un file già salvato.

    Il nome viene dal DB (UUID di salva_documento).
    """
    if "/" in nome_su_disco or "\\" in nome_su_disco or ".." in nome_su_disco:
        raise DocumentoNonValido("Percorso del documento non valido.")
    return cartella_documenti() / nome_su_disco


def elimina_documento(nome_su_disco: str | None) -> None:
    """Cancella il file se c'è. Se manca già, non fa nulla."""
    if not nome_su_disco:
        return
    percorso = percorso_documento(nome_su_disco)
    if percorso.exists():
        percorso.unlink()


# ============================================================================
# GENERAZIONE PDF DEL LEARNING AGREEMENT
# ============================================================================

VERDE       = (15, 90, 82)
GRIGIO      = (110, 124, 120)
RIGA_CHIARA = (245, 247, 245)
NERO        = (22, 33, 31)

LARGHEZZE = [25, 60, 12, 71, 12]        # somma 180 = A4 meno margini da 15
INTESTAZIONI = ["Codice", "Insegnamento estero", "CFU",
                "Riconosciuto come", "CFU"]


def _l1(testo) -> str:
    """I font base di fpdf2 parlano solo latin-1.

    Un carattere fuori set farebbe crashare la generazione: qui diventa '?'.

    """
    return str(testo).encode("latin-1", "replace").decode("latin-1")


def _taglia(testo, massimo: int) -> str:
    """Accorcia il testo se non entra in cell().

    Senza, sborderebbe sulla colonna dopo.
    """
    testo = str(testo)
    return testo if len(testo) <= massimo else testo[: massimo - 1] + "..."


def genera_pdf_la(pratica, versione, corsi) -> bytes:
    """Costruisce il PDF del piano dai dati. Restituisce i byte grezzi.

    La route decide se inline (anteprima) o attachment (download).
    """
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=22)
    pdf.add_page()

    # --- fascia di intestazione ---
    pdf.set_fill_color(*VERDE)
    pdf.rect(0, 0, 210, 28, style="F")

    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(15, 8)
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 7, _l1("Learning Agreement"),
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_x(15)
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 5, _l1("Universita Ca' Foscari Venezia  -  Mobilita Overseas"),
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_text_color(*NERO)
    pdf.set_y(40)

    # --- dati della pratica ---
    dati = [
        ("Pratica",           pratica.codice_pratica),
        ("Studente",          f"{pratica.studente.nome_completo}  "
                              f"(matricola {pratica.studente.matricola})"),
        ("Ateneo ospitante",  f"{pratica.istituto.nome} - "
                              f"{pratica.istituto.citta}, {pratica.istituto.paese}"),
        ("Anno accademico",   f"{pratica.anno_accademico}/"
                              f"{pratica.anno_accademico + 1}"),
        ("Docente referente", pratica.docente.nome_completo),
        ("Versione del piano", str(versione.numero_versione)),
    ]

    for etichetta, valore in dati:
        pdf.set_x(15)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*GRIGIO)
        pdf.cell(42, 6, _l1(etichetta))
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(*NERO)
        pdf.cell(0, 6, _l1(valore), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.ln(6)

    # --- titolo sezione insegnamenti ---
    pdf.set_x(15)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*VERDE)
    pdf.cell(0, 7, _l1("Insegnamenti concordati"),
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_text_color(*NERO)
    pdf.ln(1)

    # --- intestazione tabella ---
    pdf.set_x(15)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_fill_color(*VERDE)
    pdf.set_text_color(255, 255, 255)
    for larghezza, testo in zip(LARGHEZZE, INTESTAZIONI):
        pdf.cell(larghezza, 8, _l1(testo), fill=True)
    pdf.ln()

    # --- righe corsi ---
    pdf.set_text_color(*NERO)
    pdf.set_font("Helvetica", "", 8)

    numero_riga = 0
    totale_estero = 0
    totale_interno = 0

    for c in corsi:

        # equivalenze → testi "CT0371 Algoritmi" e somma CFU Unive
        descrizioni = []
        cfu_interni = 0

        for e in c.equivalenze:
            interno = e.corso_interno
            descrizioni.append(f"{interno.codice} {interno.titolo}")
            cfu_interni += interno.crediti

        # join mette ", " fra gli insegnamenti riconosciuti
        if descrizioni:
            testo_interni = ", ".join(descrizioni)
            testo_cfu_interni = str(cfu_interni)
        else:
            testo_interni = "-"
            testo_cfu_interni = "-"

        totale_estero += c.crediti
        totale_interno += cfu_interni

        # zebra: % 2 == 1 sulle righe dispari → sfondo chiaro
        if numero_riga % 2 == 1:
            colora = True
            pdf.set_fill_color(*RIGA_CHIARA)
        else:
            colora = False

        # set_x(15) al margine; ogni cell avanza; ln() a capo
        pdf.set_x(15)
        pdf.cell(LARGHEZZE[0], 7, _l1(c.codice), fill=colora)
        pdf.cell(LARGHEZZE[1], 7, _l1(_taglia(c.titolo, 45)), fill=colora)
        pdf.cell(LARGHEZZE[2], 7, str(c.crediti), align="C", fill=colora)
        pdf.cell(LARGHEZZE[3], 7, _l1(_taglia(testo_interni, 52)), fill=colora)
        pdf.cell(LARGHEZZE[4], 7, testo_cfu_interni, align="C", fill=colora)
        pdf.ln()

        numero_riga += 1

    # --- totali CFU ---
    pdf.set_x(15)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(LARGHEZZE[0] + LARGHEZZE[1], 8, _l1("Totale"))
    pdf.cell(LARGHEZZE[2], 8, str(totale_estero), align="C")
    pdf.cell(LARGHEZZE[3], 8, "")
    pdf.cell(LARGHEZZE[4], 8, str(totale_interno), align="C")
    pdf.ln(18)

    # --- righe per firme a mano (sul PDF stampato/scaricato) ---
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*GRIGIO)
    pdf.set_x(15)
    pdf.cell(85, 6, _l1("Firma dello studente"))
    pdf.cell(10, 6, "")
    pdf.cell(85, 6, _l1("Firma del docente referente"),
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_text_color(*NERO)
    pdf.set_x(15)
    pdf.cell(85, 14, "", border="B")
    pdf.cell(10, 14, "")
    pdf.cell(85, 14, "", border="B", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # --- pie' di pagina ---
    pdf.set_y(-30)
    pdf.set_draw_color(*GRIGIO)
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(2)

    ora = dt.datetime.now().strftime("%d/%m/%Y alle %H:%M")

    pdf.set_x(15)
    pdf.set_font("Helvetica", "", 7)
    pdf.set_text_color(*GRIGIO)
    pdf.cell(0, 4, _l1(f"Documento generato automaticamente il {ora} "
                       f"dal sistema Overseas."),
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    return bytes(pdf.output())
