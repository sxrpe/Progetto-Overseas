# Piattaforma per la gestione delle mobilità Overseas

Progetto di Basi di Dati Mod. 2 — A.A. 2025/2026.
Web application in Flask + SQLAlchemy (ORM) su database relazionale.

---

## 1. Prerequisiti

- Python 3.11 o superiore
- PostgreSQL 14 o superiore (consigliato). In alternativa SQLite, già incluso in
  Python, sufficiente per provare l'applicazione ma privo di trigger, viste
  materializzate e ruoli.
- Git

Verifica rapida:

```bash
python --version
psql --version
git --version
```

---

## 2. Installazione

```bash
# 1. Clonare il repository
git clone <url-del-repository> overseas
cd overseas

# 2. Creare e attivare l'ambiente virtuale
python -m venv .venv
source .venv/bin/activate        # su Windows:  .venv\Scripts\activate

# 3. Installare le dipendenze
pip install -r requirements.txt

# 4. Preparare la configurazione
cp .env.example .env             # su Windows:  copy .env.example .env
```

Aprire `.env` e impostare almeno due valori:

- `SECRET_KEY` — generare con
  `python -c "import secrets; print(secrets.token_hex(32))"`
- `DATABASE_URL` — la stringa di connessione al proprio database

---

## 3. Creazione del database

Con PostgreSQL, creare prima database e utente:

```bash
createdb overseas
psql -d overseas -c "CREATE ROLE overseas_app LOGIN PASSWORD 'scegli-una-password';"
psql -d overseas -c "GRANT ALL ON SCHEMA public TO overseas_app;"
```

Poi, dalla cartella radice del progetto:

```bash
python -m scripts.init_db        # crea tabelle, vincoli, trigger e viste
python -m scripts.seed           # inserisce i dati di prova
```

Per ripartire da zero in qualsiasi momento:

```bash
python -m scripts.init_db --reset && python -m scripts.seed
```

---

## 4. Avvio

```bash
flask --app wsgi run --debug
```

L'applicazione risponde su <http://127.0.0.1:5000>.

---

## 5. Utenti di prova

Tutti gli account creati da `scripts/seed.py` condividono la password
`Overseas2026!`.

- Studenti — `marco.rossi@stud.unive.it`, `giulia.bianchi@stud.unive.it`,
  `luca.verdi@stud.unive.it`
- Docenti referenti — `a.raffaeta@unive.it`, `p.neri@unive.it`
- Ufficio Overseas — `overseas@unive.it`

I dati di prova comprendono una pratica per **ciascuno** stato del ciclo di
vita, un Learning Agreement rifiutato con motivazione e una pratica chiusa con
un esame non riconosciuto.

---

## 6. Struttura del progetto

- `wsgi.py` — punto di ingresso
- `config.py` — configurazione letta dalle variabili d'ambiente
- `app/extensions.py` — istanze di SQLAlchemy e Flask-Login
- `app/enums.py` — valori enumerati e transizioni di stato ammesse
- `app/models.py` — modelli ORM: unica definizione dello schema
- `app/security.py` — hashing password, controllo di ruolo e di appartenenza
- `app/queries.py` — interrogazioni analitiche, raccolte in un punto solo
- `app/blueprints/` — route suddivise per area funzionale
- `app/templates/` — template Jinja2
- `scripts/init_db.py` — creazione dello schema
- `scripts/schema_extra_postgres.sql` — trigger, viste, indici, ruoli
- `scripts/seed.py` — dati di prova
- `uploads/` — documenti caricati, esclusa dal versionamento

---

## 7. Suggerimenti per lo sviluppo

- Impostare `SQL_ECHO=1` nel file `.env` per vedere l'SQL generato: è lo
  strumento di debug più efficace e serve a individuare le query in eccesso.
- La cartella `uploads/` e il file `.env` non vanno mai committati: sono già
  esclusi dal `.gitignore`.
