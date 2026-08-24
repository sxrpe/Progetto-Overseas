# Guida all'implementazione

**Come usare questa guida.** Ci sono tre documenti e non si sovrappongono:

- **`PIANO_DI_LAVORO.md`** dice **cosa** fare e **perché**. È il documento
  lungo, con le sedici fasi.
- **`README.md`** dice **com'è fatto** il progetto e come si muovono i dati.
- **Questa guida** dice **quale file apro, in che ordine, e come verifico che
  funzioni.** È il ponte fra il piano e la tastiera.

Ogni sezione qui sotto ha la stessa forma: obiettivo, file da toccare, ordine
delle operazioni, e una **prova di fine fase**. Se la prova non passa, la fase
non è chiusa: non andate avanti.

---

## Mappa rapida: fase → file

- **Fase 0** — `.env`, `requirements.txt`, PyCharm, GitHub
- **Fasi 1–3** — `docs/schema_er/`, `docs/RELAZIONE.md` §3. *Nessun codice.*
- **Fase 4** — `app/enums.py`, `app/models.py`, `scripts/schema_extra_postgres.sql`, `scripts/seed.py`
- **Fase 5** — `app/__init__.py`, `config.py` *(già quasi pronti)*
- **Fase 6** — `app/security.py`, `app/blueprints/auth.py`, `app/templates/auth/login.html`, la `user_loader` in `app/__init__.py`
- **Fase 7** — i blueprint di area + i template corrispondenti
- **Fase 8** — `app/documenti.py`
- **Fase 9** — trigger nel file SQL, transazioni dentro le route
- **Fase 10** — indici nei modelli, viste nel file SQL, `app/queries.py`
- **Fase 11** — `app/templates/`, `app/templates/_frammenti.html`, `style.css`
- **Fase 13** — `docs/collaudo.md`
- **Fase 14** — `docs/RELAZIONE.md`, `docs/decisioni.md`, `docs/query_principali.sql`

---

## Fase 0 — Far partire l'ambiente

**Obiettivo:** tutti e tre vedete la pagina di verifica con il riquadro verde.

**Ordine:**

1. Installate Python, PostgreSQL, Git e PyCharm. Verificate con `python --version`, `psql --version`, `git --version`.
2. Uno crea il repository su GitHub (privato, vuoto, senza README) e aggiunge gli altri due come collaboratori.
3. Ognuno clona da PyCharm: *Get from VCS*.
4. Ognuno crea l'ambiente virtuale: *Settings → Project → Python Interpreter → Add → Virtualenv*, cartella `.venv`.
5. `pip install -r requirements.txt`
6. `cp .env.example .env`, poi generate la chiave con `python -c "import secrets; print(secrets.token_hex(32))"` e incollatela in `SECRET_KEY`.
7. Per ora mettete `DATABASE_URL=sqlite:///overseas.db`. PostgreSQL si installa in Fase 4, quando serve davvero.
8. Configurate l'avvio: *Edit Configurations → + → Flask server*, target `wsgi.py`, FLASK_DEBUG spuntato.

**Prova di fine fase:** `flask --app wsgi run --debug`, aprite
<http://127.0.0.1:5000>, e il riquadro **Database** è verde. Su tutte e tre le
macchine.

---

## Fasi 1–3 — Progettare (nessun codice)

**Obiettivo:** schema logico congelato e normalizzazione dimostrata.

Questa è la parte che si è più tentati di saltare ed è quella su cui si
guadagna di più. **Non aprite nessun file `.py`.**

**Ordine:**

1. Rileggete la traccia sottolineando ogni obbligo ("deve poter", "solo se").
2. Elencate attori, casi d'uso e regole di business.
3. Disegnate il diagramma degli stati della pratica.
4. Disegnate l'ER **nella notazione del Modulo 1**, salvate in `docs/schema_er/`.
5. Ristrutturate: generalizzazioni, relazioni molti a molti, attributi multivalore.
6. Traducete in schema logico: chiavi primarie, chiavi esterne, politiche.
7. Dipendenze funzionali, copertura canonica, verifica di 1NF → BCNF.
8. **Scrivete subito la sezione 3 di `docs/RELAZIONE.md`**, finché è fresca.

**Timebox:** se alla fine del terzo giorno lo schema non è chiuso, si chiude
com'è. Arrivare al giorno sei con un ER perfetto e zero codice è il modo più
comune di non consegnare.

**Prova di fine fase:** prendete i dieci requisiti minimi della traccia e
verificate, uno per uno, che lo schema contenga i dati per soddisfarli.

---

## Fase 4 — Dare corpo al database

**Obiettivo:** due comandi ricostruiscono il database da zero.

**Ordine:**

1. **`app/enums.py`** — ruoli, stati, periodi, tipi di documento, esiti, e il dizionario `TRANSIZIONI_AMMESSE`.
2. **`app/models.py`** — una classe per relazione dello schema logico, nell'ordine delle dipendenze: prima le tabelle senza chiavi esterne. Colonne, tipi, `NOT NULL`, `UNIQUE`, `CHECK`, chiavi esterne con `ondelete`.
3. Installate PostgreSQL e cambiate `DATABASE_URL` nel `.env`.
4. `python -m scripts.init_db` — devono comparire le tabelle.
5. **`scripts/schema_extra_postgres.sql`** — trigger, indice unico parziale, viste, ruoli.
6. `python -m scripts.init_db --reset` — riapplica tutto.
7. **`scripts/seed.py`** — dati di prova: Core per gli inserimenti massivi, ORM per i dati collegati. Una pratica **per ogni stato**.

**Errore da evitare:** scrivere i modelli prima di aver chiuso la Fase 3.
Significa riscriverli.

**Prova di fine fase:** aprite `psql` e tentate a mano un'operazione vietata:

```sql
UPDATE pratica SET stato = 'chiusa' WHERE id = 1;
```

Deve fallire con il messaggio del trigger. Conservate l'esito: serve per la
relazione.

---

## Fase 5 — L'applicazione

**Obiettivo:** l'app legge dati veri dal database.

Quasi tutto è già pronto nello scaffold. Vi resta:

1. In **`app/__init__.py`**, controllare che `from app import models` ci sia.
2. Ricaricare la pagina di verifica: le tabelle devono comparire nell'elenco.

**Prova di fine fase:** la pagina mostra i nomi delle vostre tabelle.

---

## Fase 6 — Login e permessi

**Obiettivo:** nessuno vede ciò che non gli compete.

**Ordine:**

1. **`app/models.py`** — la classe `Utente` deve ereditare da `UserMixin` oltre che da `db.Model`.
2. **`app/__init__.py`** — scommentate e completate la `user_loader`.
3. **`app/blueprints/auth.py`** — le route `login` e `logout`.
4. **`app/templates/auth/login.html`** — scommentate il form.
5. **`app/templates/base.html`** — scommentate il link "Esci" e le voci di menu per ruolo.
6. **`app/security.py`** — `puo_vedere_pratica()` e `esigi_accesso()`.

**Errore da evitare:** proteggere solo con il ruolo e dimenticare
l'appartenenza. Ogni route che riceve un `<id>` deve chiamare
`esigi_accesso()`.

**Prova di fine fase:** entrate come studente A, aprite una sua pratica,
cambiate il numero nell'URL con l'id di una pratica di studente B. Deve
uscire 404. Ripetete per tutti e tre i ruoli.

---

## Fase 7 — Le funzionalità

**Obiettivo:** il ciclo di vita completo, senza toccare il database a mano.

**Ognuno dei dieci punti è una micro-tappa:** si scrive, si prova nel browser,
e solo dopo si passa al successivo. L'ordine segue il flusso reale di una
pratica, così potete sempre provare dall'inizio.

**Ordine, e chi tocca cosa:**

1. **7.1 Istituti** → `ufficio.py` + `ufficio/istituti.html`. *Fatela per prima: è la più semplice e serve a prendere confidenza col ciclo form → route → database → pagina.*
2. **7.2 Creazione pratica** → `studente.py` + `studente/nuova.html`, `studente/elenco.html`
3. **7.2b Dettaglio** → `pratiche.py` + `pratiche/dettaglio.html`
4. **7.3 Mapping esami** → `studente.py` + `studente/esami.html`
5. **7.4 Learning Agreement** → `studente/documenti.html`, `docente.py`, `docente/valutazioni.html` *(serve la Fase 8)*
6. **7.5 Verifica pre-partenza** → `ufficio.py` + `ufficio/elenco.html`
7. **7.6 Date effettive** → `studente.py`
8. **7.7 Modifiche al LA** → `studente.py`, `docente.py`. *La più complessa: sceglietene la versione più semplice.*
9. **7.8 Transcript of Records** → `studente/documenti.html`
10. **7.9 Riconoscimento** → `docente.py` + `docente/riconoscimento.html`
11. **7.10 Chiusura** → `ufficio.py`

**Divisione fra tre persone:** per fetta verticale, non per strato. Uno l'area
studente, uno l'area docente, uno l'area ufficio più i documenti. Ognuno tocca
i propri file, i conflitti quasi spariscono. Una persona è responsabile
dell'integrazione: ogni sera fa il merge e verifica che `main` parta.

**Prova di fine fase:** percorrete l'intero ciclo con tre account diversi,
dalla creazione alla chiusura, senza mai aprire `psql`.

---

## Fase 8 — I documenti

**Obiettivo:** un file caricato da uno studente non è raggiungibile da un altro.

**File:** `app/documenti.py`, più una route di scaricamento che verifica i
permessi prima di restituire il file.

**Le tre cose che si sbagliano:** il form senza
`enctype="multipart/form-data"`, la cartella dentro `static/`, e il nome del
file preso dall'utente invece che generato.

**Prova di fine fase:** entrate come studente B e provate a scaricare il
documento di studente A conoscendone l'indirizzo. Deve fallire.

---

## Fase 9 — Integrità e transazioni

**Obiettivo:** nessuno stato incoerente, nemmeno interrompendo a metà.

Non è codice nuovo: è **rivedere** quello che avete scritto in Fase 7 e
sistemare i punti dove due scritture devono essere atomiche. Cercate nelle
route ogni posto con due `commit`, o con un `commit` a metà di
un'operazione: vanno accorpati in uno solo, dentro `try` / `except` con
`rollback`.

Poi individuate le operazioni che leggono un valore e poi decidono in base a
esso — verifica pre-partenza, chiusura — e valutate un livello di isolamento
più stretto, motivandolo.

**Prova di fine fase:** provocate un errore artificiale a metà di
un'operazione composta (per esempio un `raise` temporaneo dopo la prima
scrittura) e verificate che non resti nulla.

---

## Fase 10 — Performance

**Obiettivo:** un elenco motivato di indici, e una misura.

1. Mettete `SQL_ECHO=1` nel `.env` e caricate ogni pagina di elenco. Se per una pagina scorrono decine di query, aggiungete `selectinload` sulle relazioni lette dal template.
2. Elencate le query più frequenti e aggiungete gli indici che le sostengono, nei modelli.
3. Fate un `EXPLAIN ANALYZE` prima e dopo su almeno una query e annotate i due tempi in `docs/query_principali.sql`.

**Prova di fine fase:** nessuna pagina di elenco genera più di due o tre query.

---

## Fase 11 — Front-end

Procede **in parallelo** alla Fase 7, pagina per pagina. Alla fine passate una
volta sola su tutto per uniformare: stessi colori, stesse etichette di stato,
stesso formato delle date, terminologia coerente con il database.

Spostate in `_frammenti.html` ogni pezzo di HTML che vi accorgete di aver
copiato due volte.

**Prova di fine fase:** una persona che non ha sviluppato il progetto
completa un ciclo intero senza chiedere spiegazioni.

---

## Fase 13 — Collaudo

Aprite `docs/collaudo.md` e percorretelo tutto. **Incrociato:** ognuno prova
l'area scritta da un altro.

---

## Fase 14 — Relazione

Se avete scritto le sezioni man mano, qui state solo cucendo. Attingete a
`docs/decisioni.md` per la sezione 5 e a `docs/query_principali.sql` per la 4.

**Il controllo finale che conta:** ogni affermazione della relazione deve
corrispondere a qualcosa che esiste davvero nel codice o nel database.
Dichiarare un trigger che non c'è è l'errore più grave e il più facile da
scoprire.

---

## Fasi 15–16 — Video e consegna

Video: massimo 10 minuti, database ripristinato con `seed.py`, prova a vuoto
cronometrata prima di registrare.

Pacchetto: estraetelo in una cartella pulita e avviatelo **da lì**, seguendo
solo il README, senza usare niente che sia rimasto sulla vostra macchina.
Verificate che `.env` e `uploads/` non ci siano dentro.

---

## Se siete in ritardo

Decidete adesso cosa sacrificare, non alle tre di notte del penultimo giorno.
In quest'ordine:

1. Tutte le estensioni facoltative, tranne al massimo il cruscotto.
2. Lo storico delle versioni dei documenti: tenete solo l'ultima.
3. Le modifiche al Learning Agreement: la versione più semplice che soddisfi
   "in caso di rifiuto ripristina il mapping precedente", cioè salvare una
   copia prima e rimetterla.

**Non si tagliano mai:** i dieci requisiti minimi e la relazione. Un progetto
con nove requisiti su dieci e una relazione ottima vale più di uno completo
con una relazione raffazzonata.
