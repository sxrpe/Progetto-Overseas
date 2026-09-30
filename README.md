# Piattaforma Overseas

Web application in Flask e SQLAlchemy su PostgreSQL, per le pratiche di mobilità Overseas di Ca' Foscari: Learning Agreement, verifica, rientro, riconoscimento degli esami e chiusura.

I comandi si lanciano dalla cartella del progetto, con l'ambiente virtuale attivo.

## Partire da zero

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
```

Nel `.env` imposta `SECRET_KEY` e `DATABASE_URL`.

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Esempio di `DATABASE_URL`:

```text
postgresql+psycopg://UTENTE@localhost:5432/overseas
```

Poi crea il database, le tabelle e i dati di prova:

```bash
createdb overseas
python -m scripts.init_db
python -m scripts.seed
flask --app wsgi run --debug
```

Apri http://127.0.0.1:5000

## Comandi utili

```bash
source .venv/bin/activate

flask --app wsgi run --debug          # avvia l'applicazione

python -m scripts.seed                 # cancella i dati e li reinserisce
python -m scripts.init_db             # crea le tabelle mancanti e i trigger
python -m scripts.init_db --reset     # cancella tutte le tabelle e le ricrea
```

`--reset` chiede di scrivere `si`. Dopo un reset serve di nuovo `python -m scripts.seed`.

`python -m scripts.seed` da solo basta per ripulire pratiche e account e ripartire con i dati di prova. Non cancella le tabelle.

## Account di prova

A scopo di testing. Password per tutti: `overseas`

| Nome | Ruolo | Email |
|---|---|---|
| Alessandra Verdi | docente | alessandra.verdi@unive.it |
| Marco Neri | docente | marco.neri@unive.it |
| Leonardo Rossi | studente | leonardo.rossi@stud.unive.it |
| Giulia Bianchi | studente | giulia.bianchi@stud.unive.it |
| Chiara Gallo | ufficio | chiara.gallo@unive.it |
