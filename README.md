# Piattaforma per la gestione delle mobilità Overseas

Progetto di **Basi di Dati Mod. 2** — A.A. 2025/2026 — Università Ca' Foscari Venezia.
Web application in **Flask + SQLAlchemy (ORM)** su database **PostgreSQL**.

> **Questo è uno scheletro, non il progetto.**
> Ci sono le cartelle, la configurazione e il collegamento al database. Non c'è
> nessuna funzionalità: quelle si scrivono seguendo le fasi del piano di lavoro.
> Ogni file contiene un commento che spiega cosa va scritto dentro e in quale fase.

### I tre documenti, e cosa contiene ciascuno

- **`PIANO_DI_LAVORO.md`** — **cosa** fare e **perché**. Le sedici fasi, il
  percorso a tappe, il calendario, le appendici. È il documento da leggere per
  capire dove state andando.
- **`GUIDA.md`** — **quale file aprire, in che ordine, come verificare.**
  È il ponte fra il piano e la tastiera: apritelo ogni volta che iniziate una
  fase.
- **`README.md`** (questo) — **com'è fatto** il progetto e come si muovono i
  dati. Leggetelo una volta all'inizio, poi tornateci per consultazione.

Nella cartella `docs/` ci sono invece i documenti da **riempire** man mano:
lo scheletro della relazione, il diario delle decisioni, la checklist di
collaudo e la raccolta delle query.

---

## Indice

1. [Avvio rapido](#1-avvio-rapido)
2. [Com'è fatto il progetto](#2-comè-fatto-il-progetto)
3. [Come si muovono i dati](#3-come-si-muovono-i-dati)
4. [A cosa serve ogni file](#4-a-cosa-serve-ogni-file)
5. [Come si parla al database](#5-come-si-parla-al-database)
6. [Dove vive ogni regola](#6-dove-vive-ogni-regola)
7. [Convenzioni del progetto](#7-convenzioni-del-progetto)
8. [Comandi utili](#8-comandi-utili)
9. [Problemi comuni](#9-problemi-comuni)

---

## 1. Avvio rapido

### Prerequisiti

- Python 3.11 o superiore
- PostgreSQL 14 o superiore *(oppure SQLite, per partire senza installare nulla)*
- Git

Verifica:

```bash
python --version
psql --version
git --version
```

### Installazione

```bash
git clone <url-del-repository> overseas
cd overseas

python -m venv .venv
source .venv/bin/activate          # Windows:  .venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env               # Windows:  copy .env.example .env
```

Apri `.env` e imposta due valori:

- `SECRET_KEY` — generala con
  `python -c "import secrets; print(secrets.token_hex(32))"`
- `DATABASE_URL` — la connessione al tuo database

### Database

Con PostgreSQL:

```bash
createdb overseas
psql -d overseas -c "CREATE ROLE overseas_app LOGIN PASSWORD 'scegli-una-password';"
psql -d overseas -c "GRANT ALL ON SCHEMA public TO overseas_app;"
```

Poi, dalla cartella radice:

```bash
python -m scripts.init_db
```

Per partire subito senza installare PostgreSQL, metti invece questa riga
nel `.env` e salta i comandi qui sopra:

```
DATABASE_URL=sqlite:///overseas.db
```

### Avvio

```bash
flask --app wsgi run --debug
```

Apri <http://127.0.0.1:5000>. Se vedi la pagina di verifica con il riquadro
**Database** in verde, l'ambiente funziona e puoi cominciare.

---

## 2. Com'è fatto il progetto

```
overseas/
│
├── wsgi.py                  L'interruttore: accende l'applicazione
├── config.py                Legge le impostazioni dal file .env
├── requirements.txt         Elenco delle librerie da installare
├── .env                     Le TUE impostazioni (non su GitHub)
├── .env.example             Modello delle impostazioni (sì su GitHub)
├── .gitignore               Cosa Git deve ignorare
│
├── app/                     ← L'APPLICAZIONE
│   ├── __init__.py          Monta i pezzi insieme: create_app()
│   ├── extensions.py        Gli oggetti db e login_manager
│   ├── enums.py             Valori fissi: stati, ruoli, periodi
│   ├── models.py            Le tabelle del database, come classi Python
│   ├── security.py          Chi può fare cosa + hashing password
│   ├── queries.py           Le interrogazioni complicate, tutte insieme
│   ├── documenti.py         Caricamento e archiviazione dei file
│   │
│   ├── blueprints/          ← LE PAGINE, divise per area
│   │   ├── pubblico.py        /              senza login
│   │   ├── auth.py            /auth/...      accesso e uscita
│   │   ├── pratiche.py        /pratiche/...  dettaglio, per tutti i ruoli
│   │   ├── studente.py        /studente/...  area studente
│   │   ├── docente.py         /docente/...   area docente
│   │   └── ufficio.py         /ufficio/...   area ufficio
│   │
│   ├── templates/           ← L'HTML
│   │   ├── base.html          struttura comune, estesa da tutti
│   │   ├── _frammenti.html    macro riutilizzabili (etichette di stato…)
│   │   ├── home.html          pagina di verifica, da cancellare in Fase 7
│   │   ├── errore.html        403, 404, 500
│   │   ├── auth/login.html
│   │   ├── pratiche/dettaglio.html
│   │   ├── studente/          elenco, nuova, esami, documenti
│   │   ├── docente/           elenco, valutazioni, riconoscimento
│   │   └── ufficio/           elenco, istituti, cruscotto
│   │
│   └── static/              ← CSS, immagini, eventuale JavaScript
│       └── css/style.css
│
├── scripts/                 ← PROGRAMMI DA LANCIARE A MANO
│   ├── init_db.py             crea le tabelle
│   ├── seed.py                inserisce i dati di prova
│   └── schema_extra_postgres.sql   trigger, viste, indici, ruoli
│
├── docs/                    ← DOCUMENTI DA RIEMPIRE
│   ├── RELAZIONE.md           scheletro della relazione, 7 sezioni
│   ├── decisioni.md           diario delle scelte + contributi
│   ├── collaudo.md            checklist di test (Fase 13)
│   ├── query_principali.sql   raccolta query per la relazione
│   └── schema_er/             diagrammi ER e schema logico
│
└── uploads/                 I documenti caricati (non su GitHub)
```

Tre criteri spiegano questa disposizione, e vanno riportati nella relazione.

**Un blueprint per area funzionale.** L'URL dice già chi può accedere: tutto
ciò che sta sotto `/docente/` è per i docenti. Rende i permessi verificabili a
colpo d'occhio, sia per te sia per chi corregge.

**Il dettaglio della pratica ha un blueprint suo**, perché è l'unica pagina che
serve a tutti e tre i ruoli. Metterla sotto `/studente/` costringerebbe un
docente a navigare in un URL che dice il contrario di quello che sta facendo.

**La logica sta fuori dalle route.** Le interrogazioni non banali in
`queries.py`, i controlli di autorizzazione in `security.py`. Le route si
occupano solo di HTTP: leggono la richiesta, chiamano, restituiscono una
risposta.

---

## 3. Come si muovono i dati

Questa è la parte da capire davvero. Tutto il progetto è **una sola sequenza**,
ripetuta per ogni pagina.

### La sequenza, in sei passi

```
   ①                ②              ③               ④
BROWSER  ──────>  FLASK  ──────>  ROUTE  ──────>  MODELLI  ──────>  DATABASE
chiede           trova la        controlla       traducono          PostgreSQL
un URL           funzione        i permessi      in SQL
                 giusta          e chiede
                                 i dati
                                     │                                  │
                                     │         oggetti Python           │
                                     │  <───────────────────────────────┘
                                     ▼
                                  ⑤ TEMPLATE  ──────>  ⑥ HTML  ──────>  BROWSER
                                    riempie                              mostra
                                    la pagina                            la pagina
```

### Lo stesso percorso, sui file veri

Immagina che uno studente clicchi su **"Le mie pratiche"**.

**① Il browser chiede `/studente/pratiche`**

**② Flask cerca chi risponde a quell'indirizzo.** In `app/__init__.py` è
scritto che tutto ciò che comincia per `/studente/` è gestito dal blueprint in
`app/blueprints/studente.py`. Lì dentro trova la funzione con sopra scritto
`@studente_bp.route("/pratiche")`.

**③ La funzione fa due cose prima di tutto: controlla chi sei.**
`@login_required` verifica che tu sia entrato, `@ruolo_richiesto(Ruolo.STUDENTE)`
che tu sia uno studente. I due decoratori vengono da `app/security.py`.

**④ La funzione chiede i dati.** Scrive una query con l'ORM:

```python
pratiche = db.session.scalars(
    db.select(Pratica).where(Pratica.studente_id == current_user.id)
).all()
```

SQLAlchemy legge la classe `Pratica` in `app/models.py`, capisce che
corrisponde alla tabella `pratica`, traduce in SQL vero
(`SELECT ... FROM pratica WHERE studente_id = 12`), lo manda a PostgreSQL, e
riceve indietro delle righe. Poi le **trasforma in oggetti Python**: non ricevi
tuple, ricevi una lista di `Pratica` su cui puoi scrivere `p.anno_accademico`.

**⑤ La funzione passa gli oggetti a un template.**

```python
return render_template("studente/elenco.html", pratiche=pratiche)
```

**⑥ Il template scrive l'HTML.** In `app/templates/studente/elenco.html` c'è un
ciclo che, per ogni pratica, produce un pezzo di pagina. Il risultato torna al
browser.

**Fine.** Tutte le altre pagine sono questa stessa sequenza con nomi diversi.

### E quando l'utente invia un form?

Cambiano solo i passi ④ e ⑤:

```
BROWSER  ──> ROUTE ──> valida i dati ──> modifica gli oggetti ──> db.session.commit()
(POST)                      │                                            │
                            │ se i dati sono sbagliati                   │ SQLAlchemy
                            ▼                                            ▼ genera le
                     rimostra il form                              INSERT / UPDATE
                     con gli errori
                                                                         │
                                                                         ▼
                                                          redirect a una pagina GET
```

Il punto sorprendente per chi viene da SQL: **non scrivi mai una `UPDATE`.**

```python
pratica = db.session.get(Pratica, 12)
pratica.stato = StatoPratica.IN_CORSO     # cambi l'oggetto
db.session.commit()                        # la UPDATE la genera SQLAlchemy
```

Questo meccanismo si chiama *unit of work*: la sessione tiene traccia di cosa
hai toccato e, al `commit`, scrive solo quello che serve.

### Chi apre e chiude la sessione?

Nessuno: lo fa Flask-SQLAlchemy. `db.session` **non è globale**, è legata alla
singola richiesta HTTP. Nasce quando arriva la richiesta, viene chiusa alla
fine, sempre, anche se la richiesta muore con un errore. È il lavoro che con
SQLAlchemy "nudo" dovresti scrivere tu, ed è la fonte più comune di bug
difficili da diagnosticare.

---

## 4. A cosa serve ogni file

| Devi... | Apri questo file |
|---|---|
| cambiare un'impostazione | `config.py` e `.env` |
| aggiungere una tabella | `app/models.py` |
| aggiungere uno stato o un ruolo | `app/enums.py` |
| aggiungere una pagina | il blueprint dell'area + un template |
| cambiare chi può fare cosa | `app/security.py` |
| scrivere una query complicata | `app/queries.py` |
| aggiungere un trigger o una vista | `scripts/schema_extra_postgres.sql` |
| cambiare i dati di prova | `scripts/seed.py` |
| cambiare il menu o l'aspetto comune | `app/templates/base.html` |

Descrizione estesa:

- **`wsgi.py`** — l'interruttore. Lo apri una volta e non lo tocchi più.
- **`config.py`** — trasforma le variabili del `.env` in impostazioni per
  Flask. Nessuna password è scritta qui dentro.
- **`app/__init__.py`** — la funzione `create_app()` monta tutto: configurazione,
  database, login, blueprint, pagine di errore. Lo tocchi quando aggiungi un
  blueprint.
- **`app/extensions.py`** — crea `db` e `login_manager` vuoti. Esiste per
  spezzare l'import circolare: i modelli importano `db` da qui invece che
  dall'applicazione.
- **`app/enums.py`** — gli insiemi chiusi di valori. Una stringa scritta a mano
  ("chiusa" in un file, "Chiusa" in un altro) è un bug che il computer non
  segnala; un Enum invece si sbaglia subito.
- **`app/models.py`** — l'unica definizione dello schema. Da qui
  `db.create_all()` genera le tabelle vere.
- **`app/security.py`** — hashing delle password e i due controlli di
  autorizzazione. Vedi il capitolo 6.
- **`app/queries.py`** — le interrogazioni analitiche. Raccoglierle qui serve
  soprattutto per la relazione: la sezione "Query principali" è già pronta.
- **`app/blueprints/*.py`** — le route, cioè le funzioni collegate agli URL.
- **`app/templates/*.html`** — l'HTML. Tutti estendono `base.html`.
- **`scripts/init_db.py`** — crea le tabelle dai modelli, poi applica il file
  SQL con trigger e viste.
- **`scripts/seed.py`** — inserisce i dati di prova.
- **`scripts/schema_extra_postgres.sql`** — tutto ciò che l'ORM non esprime.

---

## 5. Come si parla al database

Il progetto usa **l'ORM per quasi tutto** e **l'Expression Language per le
query complesse**. Non sono due strumenti alternativi: l'ORM è costruito
*sopra* il Core, e `select()` è la stessa identica funzione nei due casi.

### ORM — per il 95% del codice

Tutto ciò che riguarda una singola entità o poche entità collegate.

```python
# leggere per id
pratica = db.session.get(Pratica, 12)

# leggere con un filtro
pratiche = db.session.scalars(
    db.select(Pratica).where(Pratica.stato == StatoPratica.CREATA)
).all()

# navigare una relazione: la join la fa l'ORM
nome_istituto = pratica.istituto.nome

# creare
db.session.add(Pratica(studente_id=1, anno_accademico="2025/26"))
db.session.commit()

# modificare: nessuna UPDATE scritta a mano
pratica.stato = StatoPratica.IN_CORSO
db.session.commit()
```

### Expression Language — per le query analitiche

Conteggi, raggruppamenti, statistiche. Vanno in `app/queries.py`.

```python
stmt = (
    sa.select(Istituto.paese, sa.func.count(Pratica.id).label("totale"))
    .join(Pratica, Pratica.istituto_id == Istituto.id)
    .where(Pratica.anno_accademico == anno)
    .group_by(Istituto.paese)
    .order_by(sa.desc("totale"))
)
righe = db.session.execute(stmt).all()
```

Questo copre il punto 4 degli aspetti raccomandati dalla traccia
(*astrazione dal DBMS sottostante*): il codice non contiene SQL specifico di
PostgreSQL e continuerebbe a funzionare cambiando database.

### SQL testuale — solo dove serve davvero

Espressioni di finestra, CTE ricorsive, funzioni specifiche di PostgreSQL.
Sempre con **parametri nominati**, mai concatenando stringhe.

```python
righe = db.session.execute(
    sa.text("SELECT ... WHERE anno = :anno"), {"anno": "2025/26"}
).all()
```

Ogni uso di `text()` va motivato nella relazione, perché rinuncia
all'indipendenza dal dialetto.

### Il trabocchetto: le query a cascata

Se una pagina carica 50 pratiche e il template legge `pratica.istituto.nome`,
l'ORM esegue **51 query** invece di 1: una per l'elenco e una per ogni riga.

```python
# sbagliato: 51 query
pratiche = db.session.scalars(db.select(Pratica)).all()

# giusto: 2 query
from sqlalchemy.orm import selectinload
pratiche = db.session.scalars(
    db.select(Pratica).options(selectinload(Pratica.istituto))
).all()
```

Per accorgertene: metti `SQL_ECHO=1` nel `.env` e conta le righe che scorrono
nel terminale quando carichi una pagina. Il confronto prima/dopo è ottimo
materiale per la sezione sulle performance della relazione.

---

## 6. Dove vive ogni regola

Ogni regola del dominio va garantita in **un posto preciso**, scelto e
motivato. Questo è il criterio del progetto:

- **`CHECK` nei modelli** — controlli su una singola riga.
  *Il voto è fra 18 e 31. I crediti sono positivi. La partenza non precede
  l'arrivo.*
- **`UNIQUE` e chiavi** — identità e unicità.
  *Non due istituti con lo stesso nome nella stessa città.*
- **Chiavi esterne** — integrità dei collegamenti.
  *`RESTRICT` verso utenti e istituti: una pratica chiusa non sparisce perché
  è stato cancellato un utente.*
- **Trigger** (nel file SQL) — regole che coinvolgono più tabelle.
  *La pre-partenza si registra solo se il Learning Agreement è approvato.*
  Un `CHECK` non può esprimerle: vede solo la riga che sta controllando.
- **Transazioni** (nelle route) — atomicità delle operazioni composte.
  *Approvare un documento cambia il documento E lo stato della pratica: o
  entrambe, o nessuna.*
- **Codice applicativo** — solo ciò che il database non può esprimere, e i
  messaggi comprensibili all'utente.

**Il principio, da scrivere anche nella relazione:** le regole che riguardano
la *correttezza dei dati* stanno nel database; quelle che riguardano
l'*esperienza d'uso* stanno nell'applicazione.

**Corollario:** un controllo presente solo nel form HTML non è un controllo.
Ogni validazione lato browser deve avere la sua controparte lato server.

### I due controlli di autorizzazione

Vanno tenuti distinti, e servono **entrambi**.

**Controllo di ruolo** — *questo tipo di utente può usare questa funzione?*

```python
@login_required
@ruolo_richiesto(Ruolo.UFFICIO)
def chiudi_pratica(pratica_id): ...
```

**Controllo di appartenenza** — *questo utente può toccare questo oggetto?*

```python
pratica = db.session.get(Pratica, pratica_id)
esigi_accesso(pratica)      # <- senza questo, basta cambiare l'id nell'URL
```

Il secondo è quello che si dimentica più spesso ed è il più grave. Va applicato
su **ogni** route che riceve un identificatore.

E vale anche per gli elenchi: il filtro sta **nella query**, non nel template.
Caricare tutto e poi nascondere le righe altrui in Jinja non è un filtro, è una
falla.

---

## 7. Convenzioni del progetto

Decise una volta, valide per tutti e tre.

- **Una lingua sola: italiano.** Nomi di tabelle, colonne, variabili, funzioni,
  commenti. Mescolare italiano e inglese è l'errore più visibile in fase di
  correzione.
- **Tabelle al singolare**: `pratica`, non `pratiche`.
- **Chiave primaria** surrogata intera, sempre di nome `id`.
- **Chiavi esterne**: `<tabella>_id`, per esempio `studente_id`.
- **Valori enumerati** in minuscolo con underscore, definiti solo in
  `enums.py`.
- **Riga massima 100 caratteri.**
- **I commenti spiegano il perché, non il cosa.**
  `# incrementa il contatore` è rumore.
  `# 404 e non 403: un 403 confermerebbe che la pratica esiste` è informazione.

### Git, lavorando in tre

- Nessuno lavora direttamente su `main`.
- Un branch per attività: `feature/mapping-esami`.
- `git pull` **prima** di iniziare, sempre.
- Merge su `main` tramite pull request, con un altro che dà un'occhiata.
- Dividetevi **per file**, non per riga: se due persone devono toccare
  `models.py` insieme, meglio che una aspetti dieci minuti.

---

## 8. Comandi utili

```bash
# ambiente
source .venv/bin/activate               # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# database
python -m scripts.init_db               # crea le tabelle mancanti
python -m scripts.init_db --reset       # ricostruisce tutto da zero
python -m scripts.seed                  # inserisce i dati di prova

# avvio
flask --app wsgi run --debug

# generare una chiave segreta
python -c "import secrets; print(secrets.token_hex(32))"
```

Gli script si lanciano **dalla cartella radice** e **con `-m`**. Entrare in
`scripts/` e lanciare `python init_db.py` non funziona.

---

## 9. Problemi comuni

Elencati per messaggio d'errore, perché è così che li incontrerai.

**`ModuleNotFoundError: No module named 'app'`**
Hai lanciato lo script dalla cartella sbagliata. Vai nella radice e usa
`python -m scripts.init_db`.

**`RuntimeError: Working outside of application context`**
Stai usando `db.session` fuori da una richiesta HTTP. Negli script serve
`with app.app_context():`.

**Le tabelle non vengono create, e nessun errore**
I modelli non sono stati importati prima di `create_all()`. Controlla che in
`app/__init__.py` ci sia `from app import models`. Se `models.py` è ancora
vuoto, invece, è tutto normale.

**`sqlalchemy.exc.IntegrityError`**
Un vincolo del database ha respinto la scrittura. Il messaggio contiene il nome
del vincolo: da lì risali alla regola violata. Non è un bug, è il database che
fa il suo lavoro.

**`AttributeError: 'AnonymousUserMixin' object has no attribute 'ruolo'`**
Manca `@login_required` su una route che usa `current_user`.

**Il login riesce ma `current_user` resta anonimo**
Manca la callback `user_loader` in `app/__init__.py`, oppure non restituisce
l'oggetto utente.

**`psycopg.errors.InsufficientPrivilege`**
All'utente dell'applicazione manca un privilegio. È corretto: significa che i
`GRANT` funzionano. Concedi il privilegio mancante, non usare l'utente
amministratore.

**La pagina è lenta e nel terminale scorrono decine di query**
È il problema delle query a cascata. Aggiungi `selectinload` sulle relazioni
che il template legge.

**`jinja2.exceptions.UndefinedError`**
Il template usa una variabile che la route non gli ha passato. Il messaggio
dice quale.

**Ho committato `.env` su GitHub**
Aggiungerlo al `.gitignore` non basta: il file è già nella cronologia. Rimuovilo
con `git rm --cached .env` e soprattutto **cambia tutte le credenziali che
conteneva**.

---

## Utenti di prova

*(Da compilare dopo la Fase 4, quando `scripts/seed.py` sarà scritto.)*

Password comune: `Overseas2026!`

- Studenti — …
- Docenti referenti — …
- Ufficio Overseas — …
