"""Gestione dei file allegati e generazione del Learning Agreement in PDF.

QUESTO FILE NON E' UN BLUEPRINT
    Non contiene nessuna route. Sono funzioni di servizio che le route
    richiamano: la decisione di CHI puo' fare cosa resta nei blueprint,
    qui c'e' solo il COME.

LE QUATTRO REGOLE SUI FILE CARICATI
    1. Il nome del file lo genera l'applicazione, mai l'utente.
       Un file chiamato "../../config.py" sovrascriverebbe il codice.
       Qui si usa un UUID: nessun carattere del nome originale finisce
       nel percorso su disco.

    2. Il nome originale si conserva a parte, e serve SOLO per mostrarlo.
       Sta nella colonna nome_file_originale, mai nel percorso.

    3. La cartella degli upload sta FUORI da static/.
       Dentro static/ Flask servirebbe i file a chiunque conosca
       l'indirizzo, senza chiedere chi sei. L'unica via di accesso deve
       essere una route che prima verifica identita' e appartenenza.

    4. L'estensione dichiarata non e' una garanzia sul contenuto.
       Filtrarla evita gli errori onesti, non un attacco deliberato. Per
       questo progetto e' sufficiente, ed e' una riga fra le assunzioni.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import uuid
from pathlib import Path

from flask import current_app
from fpdf import FPDF
from fpdf.enums import XPos, YPos
from werkzeug.utils import secure_filename

# ===========================================================================
#  PARTE 1 — I FILE CARICATI
# ===========================================================================

ESTENSIONI_AMMESSE = {".pdf"}
DIMENSIONE_MASSIMA = 5 * 1024 * 1024      # 5 MB


class DocumentoNonValido(Exception):
    """Il file caricato non e' accettabile. Il messaggio e' per l'utente."""


def cartella_documenti() -> Path:
    """La cartella degli upload, creata se non esiste.

    Il percorso arriva da config.py (UPLOAD_FOLDER) e sta fuori da static/.
    """
    cartella = Path(current_app.config["UPLOAD_FOLDER"])
    cartella.mkdir(parents=True, exist_ok=True)
    return cartella


def salva_documento(file_caricato) -> tuple[str, str]:
    """Salva un file caricato e restituisce (nome_su_disco, nome_originale).

    file_caricato e' quello che arriva da request.files["..."].

    Solleva DocumentoNonValido con un messaggio pronto per il flash se il
    file manca, ha un'estensione non ammessa o supera la dimensione massima.

    IL NOME SU DISCO E' UN UUID
        Nessun carattere scritto dall'utente entra nel percorso. L'unica
        cosa che si conserva del nome originale e' l'estensione, e solo
        dopo averla confrontata con l'elenco ammesso.
    """
    if file_caricato is None or not file_caricato.filename:
        raise DocumentoNonValido("Nessun file selezionato.")

    nome_originale = secure_filename(file_caricato.filename)
    estensione = Path(nome_originale).suffix.lower()

    if estensione not in ESTENSIONI_AMMESSE:
        ammesse = ", ".join(sorted(ESTENSIONI_AMMESSE))
        raise DocumentoNonValido(f"Formato non ammesso: sono accettati {ammesse}.")

    # Dimensione: si va a fondo file, si legge la posizione, si torna all'inizio.
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
    """Il percorso completo di un file gia' salvato.

    Il nome arriva dal database, non dall'utente: e' un UUID generato da
    salva_documento(). Il controllo qui sotto e' una rete di sicurezza per
    il caso in cui un domani quel valore arrivasse da altrove.
    """
    if "/" in nome_su_disco or "\\" in nome_su_disco or ".." in nome_su_disco:
        raise DocumentoNonValido("Percorso del documento non valido.")
    return cartella_documenti() / nome_su_disco


def elimina_documento(nome_su_disco: str | None) -> None:
    """Cancella un file, se esiste. Non solleva niente se manca gia'."""
    if not nome_su_disco:
        return
    percorso = percorso_documento(nome_su_disco)
    if percorso.exists():
        percorso.unlink()


# ===========================================================================
#  PARTE 2 — L'IMPRONTA DEI DATI
# ===========================================================================

def impronta_piano(pratica, versione, corsi) -> str:
    """Impronta crittografica del contenuto del piano.

    Cambia se cambia un qualsiasi valore: codice, titolo, crediti o
    equivalenza. Stampata in fondo al PDF, permette di verificare che il
    documento firmato corrisponda ai dati ancora presenti nel database.

    L'ORDINAMENTO E' OBBLIGATORIO
        Gli stessi dati letti in ordine diverso devono produrre la stessa
        impronta, altrimenti non certifica niente.
    """
    pezzi = [f"{pratica.codice_pratica}|v{versione.numero_versione}"]

    for c in sorted(corsi, key=lambda x: x.codice):
        interni = ",".join(sorted(e.corso_interno.codice for e in c.equivalenze))
        pezzi.append(f"{c.codice}|{c.titolo}|{c.crediti}|{interni}")

    testo = "\n".join(pezzi)
    return hashlib.sha256(testo.encode("utf-8")).hexdigest()[:16].upper()


# ===========================================================================
#  PARTE 3 — IL PDF
# ===========================================================================

VERDE       = (15, 90, 82)
GRIGIO      = (110, 124, 120)
RIGA_CHIARA = (245, 247, 245)
NERO        = (22, 33, 31)

LARGHEZZE = [25, 60, 12, 71, 12]        # somma 180 = A4 meno margini da 15
INTESTAZIONI = ["Codice", "Insegnamento estero", "CFU",
                "Riconosciuto come", "CFU"]


def _l1(testo) -> str:
    """I font di base di fpdf2 gestiscono solo latin-1.

    Un carattere fuori da quell'insieme farebbe fallire la generazione:
    qui viene sostituito con un punto interrogativo. Per alfabeti diversi
    servirebbe un font TTF aggiunto con pdf.add_font().
    """
    return str(testo).encode("latin-1", "replace").decode("latin-1")


def _taglia(testo, massimo: int) -> str:
    """Accorcia un testo troppo lungo per la sua colonna.

    Con cell() un testo che non ci sta sborda sulla colonna successiva:
    tagliare e' brutale ma prevedibile.
    """
    testo = str(testo)
    return testo if len(testo) <= massimo else testo[: massimo - 1] + "..."


def genera_pdf_la(pratica, versione, corsi) -> bytes:
    """Il Learning Agreement come PDF, costruito dai dati del piano.

    Restituisce i byte del file: sta alla route decidere se mostrarli nel
    browser (Content-Disposition: inline) o farli scaricare (attachment).
    """
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=22)
    pdf.add_page()

    # ---------- fascia di intestazione ----------
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

    # ---------- dati della pratica ----------
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

    # ---------- titolo della sezione ----------
    pdf.set_x(15)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*VERDE)
    pdf.cell(0, 7, _l1("Insegnamenti concordati"),
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_text_color(*NERO)
    pdf.ln(1)

    # ---------- intestazione della tabella ----------
    pdf.set_x(15)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_fill_color(*VERDE)
    pdf.set_text_color(255, 255, 255)
    for larghezza, testo in zip(LARGHEZZE, INTESTAZIONI):
        pdf.cell(larghezza, 8, _l1(testo), fill=True)
    pdf.ln()

    # ---------- righe ----------
    pdf.set_text_color(*NERO)
    pdf.set_font("Helvetica", "", 8)

    numero_riga = 0
    totale_estero = 0
    totale_interno = 0

    for c in corsi:

        # --- 1. gli insegnamenti di Ca' Foscari collegati a questo corso ---
        # c.equivalenze e' la lista dei collegamenti; ogni collegamento ha
        # dentro l'oggetto del corso interno vero (e.corso_interno).
        descrizioni = []  # ["CT0371 Algoritmi", "CT0429 Data mining"]
        cfu_interni = 0  # la somma dei loro crediti

        for e in c.equivalenze:
            interno = e.corso_interno
            descrizioni.append(f"{interno.codice} {interno.titolo}")
            cfu_interni += interno.crediti

        # --- 2. il testo della colonna "Riconosciuto come" ---
        # join incolla gli elementi mettendo ", " fra uno e l'altro.
        if descrizioni:
            testo_interni = ", ".join(descrizioni)
            testo_cfu_interni = str(cfu_interni)
        else:
            testo_interni = "-"
            testo_cfu_interni = "-"

        # --- 3. i totali in fondo alla tabella ---
        totale_estero += c.crediti
        totale_interno += cfu_interni

        # --- 4. una riga su due con lo sfondo grigio chiaro ---
        # % e' il resto della divisione: vale 1 sulle righe dispari.
        if numero_riga % 2 == 1:
            colora = True
            pdf.set_fill_color(*RIGA_CHIARA)
        else:
            colora = False

        # --- 5. le cinque celle della riga ---
        # set_x(15) riporta il cursore al margine sinistro; ogni cell()
        # avanza da sola, e ln() va a capo alla fine.
        pdf.set_x(15)
        pdf.cell(LARGHEZZE[0], 7, _l1(c.codice), fill=colora)
        pdf.cell(LARGHEZZE[1], 7, _l1(_taglia(c.titolo, 45)), fill=colora)
        pdf.cell(LARGHEZZE[2], 7, str(c.crediti), align="C", fill=colora)
        pdf.cell(LARGHEZZE[3], 7, _l1(_taglia(testo_interni, 52)), fill=colora)
        pdf.cell(LARGHEZZE[4], 7, testo_cfu_interni, align="C", fill=colora)
        pdf.ln()

        numero_riga += 1
    # ---------- totali ----------
    pdf.set_x(15)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(LARGHEZZE[0] + LARGHEZZE[1], 8, _l1("Totale"))
    pdf.cell(LARGHEZZE[2], 8, str(totale_estero), align="C")
    pdf.cell(LARGHEZZE[3], 8, "")
    pdf.cell(LARGHEZZE[4], 8, str(totale_interno), align="C")
    pdf.ln(18)

    # ---------- firme ----------
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

    # ---------- pie' di pagina con l'impronta ----------
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

    pdf.set_x(15)
    pdf.set_font("Helvetica", "B", 7)
    pdf.cell(0, 4, _l1(f"Impronta dei dati: "
                       f"{impronta_piano(pratica, versione, corsi)}"),
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_x(15)
    pdf.set_font("Helvetica", "", 7)
    pdf.cell(0, 4, _l1("L'impronta cambia se i dati del piano vengono "
                       "modificati: permette di verificare che il documento "
                       "firmato corrisponda ai dati registrati."))

    return bytes(pdf.output())