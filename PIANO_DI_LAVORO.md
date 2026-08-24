# Progetto Basi di Dati Mod. 2 — A.A. 2025/2026
## Piattaforma per la gestione delle mobilità Overseas
### Piano operativo completo: struttura del progetto e passaggi da svolgere

---

## Come usare questo documento

Questo documento non è la relazione finale: è il **piano di lavoro**. Serve a sapere in ogni momento cosa è stato fatto, cosa manca e in che ordine procedere.

- Ogni fase è indipendente ma ordinata: le fasi successive danno per scontato che le precedenti siano chiuse.
- Ogni punto è formulato come **azione concreta**, non come argomento di studio.
- I punti contrassegnati come *Consigliato* non sono obbligatori per la sufficienza, ma incidono sulla valutazione.
- I punti contrassegnati come *Facoltativo* sono estensioni: da affrontare solo se il nucleo obbligatorio è già solido.
- Alla fine di ogni fase c'è un **criterio di chiusura**: finché non è soddisfatto, la fase non è finita.

**Nota sul codice.** Le Fasi 0, 4 e 5 contengono estratti di codice reale, non pseudo-codice: sono presi dallo scheletro di progetto allegato a questo piano, dove ogni file è completo, commentato e già verificato. Il codice mostrato qui serve a capire *perché* una cosa si fa in un certo modo; il file completo serve a partire.

Regola generale del corso, da tenere presente per tutta la durata del lavoro: *è meglio approfondire bene pochi aspetti che coprirli tutti in modo insoddisfacente*. Un progetto artificiosamente complicato viene penalizzato.

---

## Indice delle fasi

1. Fase 0 — Impostazione del lavoro e dell'ambiente
2. Fase 1 — Analisi della traccia e raccolta dei requisiti
3. Fase 2 — Progettazione concettuale
4. Fase 3 — Progettazione logica e normalizzazione
5. Fase 4 — Implementazione fisica della base di dati
6. Fase 5 — Impostazione dell'applicazione Flask
7. Fase 6 — Autenticazione e autorizzazione
8. Fase 7 — Implementazione delle funzionalità (flusso della pratica)
9. Fase 8 — Gestione dei documenti allegati
10. Fase 9 — Integrità, transazioni e consistenza
11. Fase 10 — Performance
12. Fase 11 — Front-end
13. Fase 12 — Estensioni facoltative
14. Fase 13 — Testing e collaudo
15. Fase 14 — Stesura della relazione
16. Fase 15 — Video dimostrativo
17. Fase 16 — Pacchetto di consegna
18. Appendice A — Autovalutazione sui quattro criteri
19. Appendice B — Errori comuni da evitare
20. Appendice C — Ordine di lavoro consigliato
21. Appendice D — Comandi di riferimento
22. Appendice E — Diagnosi dei problemi più comuni

---

# FASE 0 — Impostazione del lavoro e dell'ambiente

Obiettivo: partire tutti dalla stessa base. Ogni ora spesa qui ne fa risparmiare cinque più avanti, perché evita il caso peggiore di un progetto di gruppo: tre macchine configurate in tre modi diversi e un repository che nessuno riesce ad avviare.

## 0.1 Decisioni tecnologiche — già prese

Queste scelte sono decise, non aperte. Cambiarle a metà progetto costa più che accettarle ora.

- **DBMS: PostgreSQL.** È quello consigliato dalla docente ed è l'unico che permette di mostrare trigger, viste materializzate, indici parziali e ruoli. SQLite resta utilizzabile come ripiego per far girare l'applicazione su una macchina non configurata, ma rinuncia a metà degli aspetti raccomandati dalla traccia.
- **Accesso ai dati: Flask-SQLAlchemy con l'ORM.** La traccia dice *"uso di Expression Language **o** ORM"*: sono alternative, non un elenco di cose da fare entrambe. L'ORM soddisfa il requisito per intero.
- **Interrogazioni analitiche: `select()` in Expression Language**, raccolte in un unico modulo. Restano indipendenti dal dialetto SQL e sono già pronte per la sezione "Query principali" della relazione. L'SQL testuale con `text()` si usa solo dove la versione astratta diventerebbe illeggibile, e la scelta va motivata.
- **Front-end: W3.CSS.** Framework leggero, senza dipendenze, sufficiente per un front-end minimale. Niente JavaScript: la traccia dice esplicitamente che non è richiesto e non incide sulla valutazione.
- **Autenticazione: Flask-Login.** È quella vista a lezione. L'autorizzazione va invece scritta a mano, perché Flask-Login non la fornisce.
- **Hashing delle password: Passlib con pbkdf2_sha256.** È puro Python e non richiede compilatori installati, quindi si installa senza problemi su tutte e tre le macchine.

Una nota da riportare in relazione: **l'ORM non sostituisce il Core, ci sta sopra.** La mappatura dichiarativa genera oggetti `Table` del Core, la `Session` incapsula una `Connection`, e `select()` è la stessa identica funzione nei due modi. Scegliere l'ORM non significa rinunciare al Core: significa non scriverlo a mano.

## 0.2 Installazione degli strumenti

Da fare su tutte e tre le macchine, prima di scrivere qualsiasi cosa.

- **Python 3.11 o superiore.** Su Windows, durante l'installazione, spuntare "Add Python to PATH": è la causa numero uno dei problemi successivi.
- **PostgreSQL 14 o superiore.** Durante l'installazione viene chiesta la password dell'utente `postgres`: annotarla, serve subito dopo. Su Windows viene installato anche pgAdmin, comodo per ispezionare il database a colpo d'occhio.
- **Git.** Su Windows conviene Git for Windows, che porta con sé Git Bash.
- **PyCharm.** La versione Community è gratuita e sufficiente. La Professional è gratuita per gli studenti con l'account universitario e aggiunge il pannello Database integrato, che è molto comodo ma non indispensabile.

Verifica finale, da terminale:

```
python --version
psql --version
git --version
```

Se uno dei tre comandi non viene riconosciuto, il problema è nella variabile PATH e va risolto adesso, non dopo.

## 0.3 Creazione del repository su GitHub

Un solo membro del gruppo crea il repository; gli altri due lo clonano.

- Su GitHub: **New repository**, nome del progetto, visibilità **privata**.
- **Non** spuntare "Add a README", "Add .gitignore" e "Choose a license": il repository deve nascere vuoto, altrimenti il primo push da PyCharm richiede una fusione inutile.
- In **Settings → Collaborators**, aggiungere gli altri due componenti del gruppo.
- Sempre in **Settings → Branches**, valutare una regola di protezione su `main` che richieda una pull request: costringe a non spingere direttamente sul branch principale, che è la principale causa di conflitti in un gruppo da tre.

Sull'autenticazione, una precisazione che fa perdere tempo a molti: **GitHub non accetta più la password dell'account** per le operazioni Git. Le due strade sono:

- **Token personale**, da **Settings → Developer settings → Personal access tokens → Tokens (classic)**, con il permesso `repo`. Il token si usa al posto della password quando Git la chiede. Va copiato subito, perché non viene più mostrato.
- **Chiave SSH**, più comoda a lungo termine: si genera con `ssh-keygen -t ed25519 -C "tua@email"` e si incolla il contenuto del file `.pub` in **Settings → SSH and GPG keys**.

## 0.4 Configurazione di PyCharm

**Collegare l'account GitHub.** In **Settings → Version Control → GitHub**, aggiungere l'account con "Log in via GitHub" oppure con il token. Fatto una volta, PyCharm gestisce da solo le credenziali di tutte le operazioni Git.

**Clonare il progetto.** Dalla schermata iniziale, **Get from VCS**, incollare l'URL del repository e scegliere la cartella locale. Gli altri due componenti partono da qui.

**Creare l'ambiente virtuale.** In **Settings → Project → Python Interpreter → Add Interpreter → Add Local Interpreter → Virtualenv Environment → New**, con posizione `.venv` dentro la cartella del progetto e l'interprete di sistema come base. PyCharm attiverà l'ambiente in automatico in ogni terminale che apre.

**Installare le dipendenze.** Aprire il terminale integrato (Alt+F12) e lanciare `pip install -r requirements.txt`. Quando PyCharm riconosce il file `requirements.txt` mostra anche un banner con un pulsante per installarle.

**Configurare l'avvio.** In alto a destra, **Edit Configurations → + → Flask server**:

- *Target type*: Script path — puntare a `wsgi.py`
- *FLASK_DEBUG*: spuntato
- *Working directory*: la cartella radice del progetto

Da quel momento l'applicazione parte con il pulsante di esecuzione e si possono usare i punti di interruzione del debugger, che valgono dieci volte le stampe a video.

**Impostazioni che conviene attivare subito:**

- **Settings → Editor → General → On Save**: attivare "Reformat code" e "Remove trailing blank lines". Il codice resta uniforme fra tre persone senza discussioni.
- **Settings → Editor → Code Style → Python**: lasciare il limite di riga a 88 o 100 caratteri e rispettarlo.
- **Settings → Tools → Actions on Save**: attivare "Optimize imports", così spariscono gli import inutilizzati.
- Se avete PyCharm Professional, nel pannello **Database** aggiungete la connessione a PostgreSQL: potete ispezionare tabelle e lanciare query senza uscire dall'editor.

## 0.5 Struttura delle cartelle

Questa è la struttura definitiva. Va creata adesso, vuota, e non riorganizzata più.

```
overseas/
├── .env                     ← configurazione locale, MAI su GitHub
├── .env.example             ← modello con valori fittizi, questo sì versionato
├── .gitignore
├── README.md                ← istruzioni di installazione e avvio
├── requirements.txt         ← elenco delle dipendenze
├── config.py                ← lettura della configurazione
├── wsgi.py                  ← punto di ingresso dell'applicazione
│
├── app/
│   ├── __init__.py          ← application factory: create_app()
│   ├── extensions.py        ← istanze di SQLAlchemy e Flask-Login
│   ├── enums.py             ← valori enumerati e transizioni di stato
│   ├── models.py            ← modelli ORM: UNICA definizione dello schema
│   ├── security.py          ← password, controllo di ruolo e di appartenenza
│   ├── queries.py           ← interrogazioni analitiche, tutte insieme
│   │
│   ├── blueprints/
│   │   ├── pubblico.py      ← home e smistamento per ruolo
│   │   ├── auth.py          ← accesso e uscita
│   │   ├── pratiche.py      ← dettaglio pratica, condiviso dai tre ruoli
│   │   ├── studente.py      ← area studente
│   │   ├── docente.py       ← area docente referente
│   │   └── ufficio.py       ← area ufficio Overseas
│   │
│   ├── templates/
│   │   ├── base.html        ← struttura comune, estesa da tutti
│   │   ├── home.html
│   │   ├── errore.html
│   │   ├── auth/login.html
│   │   ├── pratiche/dettaglio.html
│   │   ├── studente/…
│   │   ├── docente/…
│   │   └── ufficio/…
│   │
│   └── static/css/style.css
│
├── scripts/
│   ├── init_db.py                    ← crea lo schema
│   ├── schema_extra_postgres.sql     ← trigger, viste, indici, ruoli
│   └── seed.py                       ← dati di prova
│
└── uploads/                 ← documenti caricati, esclusa dal versionamento
```

Tre criteri spiegano questa disposizione, e vanno riportati nella relazione:

- **Un blueprint per area funzionale.** L'URL dice già chi può accedere: tutto ciò che sta sotto `/docente/` è per i docenti. Rende i permessi verificabili a colpo d'occhio.
- **Il dettaglio della pratica ha un blueprint proprio**, perché è l'unica pagina che serve a tutti e tre i ruoli. Metterla sotto `/studente/` avrebbe costretto un docente a navigare in un URL che dice il contrario di quello che sta facendo.
- **La logica di accesso ai dati sta fuori dalle route.** Le interrogazioni non banali stanno in `queries.py`, i controlli di autorizzazione in `security.py`. Le route si occupano solo di HTTP: leggono la richiesta, chiamano, restituiscono una risposta.

## 0.6 Il file delle dipendenze

Il file si chiama `requirements.txt`, sta nella cartella radice e **si installa**, non si legge:

```
pip install -r requirements.txt
```

Non è uno script eseguibile: è un elenco che `pip` interpreta. È il modo standard, ed è quello che la docente si aspetta di trovare nel pacchetto di consegna, perché le permette di ricostruire l'ambiente con un comando solo.

```
# ---------------------------------------------------------------------------
# Dipendenze del progetto Overseas
#
# Installazione (dopo aver attivato l'ambiente virtuale):
#     pip install -r requirements.txt
#
# Le versioni sono vincolate al minor release: si accettano gli aggiornamenti
# correttivi ma non i cambi di major version, che potrebbero rompere il codice.
# ---------------------------------------------------------------------------

Flask~=3.1.0                # framework web
Flask-SQLAlchemy~=3.1.1     # integrazione SQLAlchemy <-> Flask
Flask-Login~=0.6.3          # autenticazione basata su sessione
SQLAlchemy~=2.0.36          # ORM e Core
passlib~=1.7.4              # hashing delle password (pbkdf2_sha256)
python-dotenv~=1.0.1        # lettura della configurazione dal file .env

# Driver del DBMS: lasciare attiva SOLO la riga del database realmente usato.
psycopg[binary]~=3.2.3      # PostgreSQL
# SQLite non richiede driver: e' incluso in Python.
```

Due precisazioni sull'uso:

- **L'operatore `~=` blocca il cambio di versione maggiore.** `Flask~=3.1.0` accetta la 3.1.4 ma non la 3.2. Serve a evitare che fra due settimane un aggiornamento cambi il comportamento di una libreria durante la registrazione del video.
- **Aggiungere una dipendenza è un'operazione in due passi**: la si installa e la si scrive nel file. Se si dimentica il secondo passo, il progetto funziona sulla propria macchina e non su quella degli altri. È il classico "da me funziona".

Se volete l'automatismo completo, esiste `pip freeze > requirements.txt`, che scrive l'elenco esatto di tutto ciò che è installato. Sconsigliato in questo caso: produce quaranta righe fra cui le dipendenze delle dipendenze, illeggibile per chi corregge. Meglio un file scritto a mano e commentato.

## 0.7 I file di configurazione

**`.gitignore`** — decide cosa Git deve ignorare. Va creato **prima** del primo commit: un file già finito nella cronologia non sparisce aggiungendolo dopo.

```
# Ambiente virtuale
.venv/
venv/

# Configurazione con credenziali reali: NON deve mai finire su GitHub
.env

# Documenti caricati dagli utenti
uploads/*
!uploads/.gitkeep

# Database locale SQLite di sviluppo
*.db
*.sqlite3

# Cache Python
__pycache__/
*.py[cod]

# PyCharm
.idea/

# Sistema operativo
.DS_Store
Thumbs.db
```

**`.env`** — contiene i valori veri e non si versiona. **`.env.example`** — contiene gli stessi nomi con valori fittizi e si versiona, così chi clona il repository sa cosa deve impostare.

```
# Chiave usata per firmare il cookie di sessione.
# Generarne una nuova con:
#     python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY=sostituire-con-una-stringa-casuale-lunga

# Stringa di connessione al database.
DATABASE_URL=postgresql+psycopg://overseas_app:password@localhost:5432/overseas
# In alternativa, per partire subito senza PostgreSQL:
# DATABASE_URL=sqlite:///overseas.db

UPLOAD_FOLDER=uploads
MAX_UPLOAD_MB=10

# Stampa sul terminale l'SQL generato: utilissimo in sviluppo.
SQL_ECHO=0
```

La riga `SQL_ECHO` merita attenzione: attivarla mostra ogni istruzione che SQLAlchemy manda al database. È lo strumento con cui si scoprono le query in eccesso, e serve anche per la relazione, perché permette di riportare l'SQL realmente generato accanto alla query scritta in Python.

## 0.8 Convenzioni da fissare per iscritto

- **Una lingua sola.** Italiano oppure inglese per nomi di tabelle, colonne, variabili, funzioni e commenti. Mescolarli è l'errore più visibile in fase di correzione. In questo progetto: italiano ovunque.
- **Tabelle al singolare** (`pratica`, non `pratiche`), colonne in minuscolo con underscore.
- **Chiavi primarie surrogate** intere di nome `id`; chiavi esterne di nome `<tabella>_id`.
- **Stati e valori enumerati** in minuscolo con underscore, definiti una volta sola in `enums.py` e mai scritti a mano altrove.
- **Riga massima 100 caratteri.**
- **Commenti che spiegano il perché**, non il cosa. `# incrementa il contatore` è rumore; `# 404 e non 403: un 403 confermerebbe che la pratica esiste` è informazione.

## 0.9 Flusso di lavoro Git nel gruppo

Con tre persone sullo stesso repository serve una regola sola, ma rispettata.

- **Nessuno lavora direttamente su `main`.** Ogni attività ha il suo branch: `feature/mapping-esami`, `feature/upload-documenti`.
- In PyCharm: **Git → Branches → New Branch** in basso a destra.
- **Commit piccoli e frequenti**, con un messaggio che dica cosa cambia e perché. `fix` non è un messaggio.
- **Prima di iniziare a lavorare, sempre `pull`.** Prima di aprire una pull request, `pull` di nuovo. La maggior parte dei conflitti nasce dal saltare questo passaggio.
- **Merge su `main` tramite pull request**, con almeno un altro componente che dà un'occhiata. Serve anche a far sapere agli altri cosa sta succedendo nel progetto.
- **Dividersi per file, non per riga.** Se due persone devono toccare `models.py` nello stesso momento, meglio che una aspetti dieci minuti: risolvere un conflitto su un file di modelli costa molto più tempo.

## 0.10 Tracciamento del lavoro

- Aprire un elenco condiviso di attività con stato. Va bene anche la scheda Projects di GitHub.
- Tenere un **diario delle decisioni progettuali**: per ogni scelta non banale, cosa si è deciso e perché. È la materia prima della sezione "Principali scelte progettuali" della relazione, e ricostruirlo a memoria alla fine costa molto di più che scriverlo strada facendo.
- Tenere l'elenco di **chi ha fatto cosa**: l'appendice sui contributi è richiesta esplicitamente.

**Criterio di chiusura della Fase 0:** tutti e tre clonano il repository, creano l'ambiente virtuale, installano le dipendenze e avviano l'applicazione vuota da PyCharm senza intoppi. Le convenzioni sono scritte in un file dentro il repository.

---

# FASE 1 — Analisi della traccia e raccolta dei requisiti

Obiettivo: trasformare la traccia discorsiva in un elenco di requisiti verificabili. Nessuna riga di codice prima di aver chiuso questa fase.

## 1.1 Rilettura ragionata della traccia

- Rileggere il documento della traccia sottolineando ogni frase che contiene un obbligo ("deve poter", "solo se", "almeno").
- Costruire l'elenco delle **entità nominate esplicitamente**: studente, docente referente, personale dell'ufficio Overseas, istituto ospitante, pratica di mobilità, insegnamento estero, insegnamento del piano di studi, Learning Agreement, modifica al Learning Agreement, Transcript of Records, esame sostenuto.
- Segnare i punti ambigui, cioè quelli che la traccia lascia volutamente aperti.
  - Un utente può avere più ruoli contemporaneamente?
  - Uno studente può avere più pratiche attive nello stesso anno accademico?
  - Un insegnamento estero può essere mappato su più insegnamenti di Ca' Foscari e viceversa?
  - Le modifiche al Learning Agreement sono più di una? La traccia dice di sì.
  - Cosa si conserva della versione precedente quando una modifica viene rifiutata?
- Portare i dubbi rilevanti alla docente **prima** di iniziare lo sviluppo, come la traccia stessa suggerisce.

## 1.2 Definizione degli attori e dei loro permessi

- **Studente**
  - Crea, visualizza e modifica solo le proprie pratiche.
  - Carica documenti relativi alle proprie pratiche.
  - Non vede pratiche altrui in nessuna schermata, in nessuna lista, in nessun risultato di ricerca.
- **Docente referente**
  - Visualizza solo le pratiche per cui è indicato come referente.
  - Approva o rifiuta il Learning Agreement, le modifiche e il riconoscimento degli esami.
  - Non può modificare i dati inseriti dallo studente.
- **Ufficio Overseas**
  - Visualizza tutte le pratiche.
  - Gestisce l'elenco degli istituti partner.
  - Registra il completamento della fase pre-partenza e chiude le pratiche.
  - Non entra nel merito delle approvazioni didattiche, che restano al docente.

## 1.3 Casi d'uso, raggruppati per fase della mobilità

- **Prima della partenza**
  - Creazione della pratica con anno accademico, istituto ospitante, periodo previsto, docente referente ed eventuali note.
  - Inserimento del mapping fra esami esteri ed esami del piano di studio, con codice, titolo e crediti per entrambi i lati.
  - Caricamento del Learning Agreement firmato.
  - Visualizzazione e valutazione del documento da parte del docente, con motivazione obbligatoria in caso di rifiuto.
  - Verifica di completezza e registrazione della fase pre-partenza da parte dell'ufficio.
- **Durante la mobilità**
  - Inserimento delle date effettive di arrivo e partenza.
  - Proposta di modifica del piano: nuova lista di esami, nuovo mapping, nuovo documento allegato.
  - Approvazione o rifiuto della modifica da parte del docente.
  - Ripristino del mapping precedente in caso di rifiuto.
- **Dopo il rientro**
  - Caricamento del Transcript of Records.
  - Inserimento di voto e data di superamento per ciascun esame.
  - Approvazione o rifiuto di ciascun esame e del relativo voto da parte del docente.
  - Verifica finale e chiusura della pratica da parte dell'ufficio.

## 1.4 Regole di business da rendere esplicite

Queste sono le regole che poi andranno garantite con vincoli, trigger o transazioni. Vanno scritte ora, in italiano, prima di decidere come implementarle.

- Una pratica fa riferimento a **un solo** istituto ospitante e a **un solo** docente referente.
- L'istituto ospitante deve essere scelto da una lista predefinita, non inserito a mano dallo studente.
- La fase pre-partenza può essere registrata come completa **solo se** i dati essenziali sono presenti **e** il Learning Agreement è stato approvato dal docente.
- Una pratica può essere chiusa **solo se** il Transcript of Records è stato caricato **e** il riconoscimento degli esami è stato completato.
- Un rifiuto, di qualsiasi tipo, richiede una motivazione e registra la data della decisione.
- Il rifiuto di una modifica al Learning Agreement deve riportare il mapping degli esami allo stato precedentemente concordato.
- Voto e data di superamento hanno senso solo dopo il caricamento del Transcript of Records.
- Lo stato della pratica non può saltare fasi né tornare indietro arbitrariamente.

## 1.5 Definizione del ciclo di vita della pratica

- Elencare gli stati previsti: creata; in attesa di approvazione del Learning Agreement; pre-partenza completata; mobilità in corso; in riconoscimento esami; chiusa.
- Per ogni stato, definire:
  - quali azioni sono permesse in quello stato e a chi;
  - quali stati successivi sono raggiungibili;
  - quale evento provoca il passaggio;
  - quali condizioni devono essere vere perché il passaggio avvenga.
- Disegnare il **diagramma degli stati** come grafo. Questo disegno andrà nella relazione: è uno dei modi più efficaci per mostrare che la logica applicativa è stata pensata e non improvvisata.
- Decidere se lo stato è un attributo memorizzato oppure derivato dai dati.
  - Memorizzato: più semplice da interrogare e indicizzare, ma richiede disciplina per non entrare in contraddizione con i dati.
  - Derivato: sempre coerente, ma costoso e scomodo.
  - Scelta consigliata: memorizzato, con vincoli e trigger che ne impediscono i valori incoerenti. La motivazione va nella relazione.

**Criterio di chiusura della Fase 1:** esiste un documento con attori, casi d'uso, regole di business e diagramma degli stati, e i dubbi sono stati chiariti con la docente.

---

# FASE 2 — Progettazione concettuale

Obiettivo: produrre lo schema Entità-Relazione, usando **la notazione grafica del Modulo 1 del corso**. Questo è un requisito esplicito: usare una notazione diversa è un errore che si paga in sede di valutazione.

## 2.1 Individuazione delle entità

- Partire dall'elenco dei sostantivi ricavato in Fase 1 e distinguere:
  - cosa è un'**entità** (ha esistenza propria e identità);
  - cosa è un **attributo** (descrive qualcosa d'altro e non ha vita autonoma);
  - cosa è una **relazione** (lega due o più entità).
- Entità candidate da valutare:
  - Utente, con le sue specializzazioni Studente, Docente, Personale d'ufficio.
  - Istituto ospitante.
  - Pratica di mobilità.
  - Associazione fra esame estero ed esame interno (il mapping).
  - Documento allegato.
  - Decisione o valutazione (approvazione/rifiuto).
  - Insegnamento di Ca' Foscari, se si sceglie di gestirne un catalogo.
- Per ciascuna entità elencare gli attributi con il relativo dominio e specificare quali sono obbligatori e quali opzionali.

## 2.2 Gestione dei ruoli utente

Va presa una decisione esplicita e motivata fra tre alternative:

- **Generalizzazione** dell'entità Utente in Studente, Docente e Personale.
  - Coerente con la teoria del Modulo 1, elegante da rappresentare.
  - Va dichiarato se la generalizzazione è totale o parziale, esclusiva o sovrapposta.
- **Entità unica Utente con attributo ruolo.**
  - Più semplice, più diretta da tradurre, sufficiente se le tre categorie hanno pochi attributi propri.
- **Entità unica Utente con relazione verso un'entità Ruolo.**
  - Necessaria solo se un utente può avere più ruoli contemporaneamente.

Qualunque sia la scelta, va giustificata nella relazione con un argomento tecnico, non con "era più comodo".

## 2.3 Individuazione delle relazioni e delle cardinalità

- Per ogni coppia di entità collegate, definire:
  - il nome della relazione, espresso come verbo;
  - la cardinalità minima e massima da entrambi i lati;
  - la partecipazione obbligatoria o facoltativa;
  - gli eventuali attributi propri della relazione.
- Relazioni principali da modellare:
  - Studente – Pratica: uno a molti, uno studente può avere più pratiche.
  - Pratica – Istituto ospitante: molti a uno, una pratica ha un solo istituto.
  - Pratica – Docente referente: molti a uno, una pratica ha un solo referente.
  - Pratica – Associazione esami: uno a molti.
  - Pratica – Documento: uno a molti, se si vuole lo storico delle versioni.
  - Pratica – Modifica al Learning Agreement: uno a molti.
- Prestare particolare attenzione al **mapping degli esami**: è il punto concettualmente più delicato del progetto.
  - Se un esame estero può corrispondere a più esami interni, o viceversa, la corrispondenza è una relazione molti a molti e va reificata in un'entità propria.
  - Se il legame è sempre uno a uno, si può semplificare, ma la semplificazione va dichiarata.

## 2.4 Vincoli non esprimibili graficamente

- Elencare in una **tabella dei vincoli non esprimibili nello schema ER** — da presentare come elenco puntato, non come tabella grafica — tutte le regole della sezione 1.4 che il diagramma non riesce a rappresentare.
- Per ciascun vincolo indicare:
  - la formulazione in linguaggio naturale, precisa e non ambigua;
  - il livello a cui verrà garantito: `CHECK`, chiave, trigger, transazione applicativa, o controllo nel back-end;
  - il motivo della scelta di quel livello.
- Questo elenco è uno dei punti che distinguono un progetto discreto da uno buono: mostra consapevolezza del limite del modello concettuale.

## 2.5 Ristrutturazione dello schema

- Eliminare o rendere esplicite le generalizzazioni, secondo il criterio scelto.
- Reificare le relazioni molti a molti con attributi propri.
- Eliminare gli attributi multivalore.
- Scomporre o accorpare le entità dove serve, motivando ogni intervento.
- Individuare per ogni entità un **identificatore**, distinguendo fra identificatori naturali e surrogati.

## 2.6 Redazione del dizionario dei dati

- Per ogni entità: nome, descrizione in una frase, elenco degli attributi.
- Per ogni attributo: nome, tipo, dominio ammesso, obbligatorietà, valore di default se previsto.
- Per ogni relazione: nome, entità coinvolte, cardinalità, descrizione.
- Presentare tutto come elenco strutturato con sotto-punti.

**Criterio di chiusura della Fase 2:** esiste uno schema ER disegnato nella notazione del corso, con dizionario dei dati e elenco dei vincoli non esprimibili, e tutte le regole della Fase 1 trovano posto in almeno un elemento dello schema.

---

# FASE 3 — Progettazione logica e normalizzazione

Obiettivo: tradurre lo schema concettuale in uno schema relazionale corretto e normalizzato, documentando ogni passaggio.

## 3.1 Traduzione dallo schema ER allo schema relazionale

- Tradurre ogni entità in una relazione, riportando gli attributi.
- Tradurre le relazioni secondo le cardinalità:
  - relazioni uno a molti: chiave esterna sul lato "molti";
  - relazioni molti a molti: nuova relazione con chiave composta dalle due chiavi esterne;
  - relazioni uno a uno: chiave esterna sul lato con partecipazione obbligatoria, con vincolo di unicità.
- Tradurre la generalizzazione con il criterio scelto: accorpamento nel padre, accorpamento nei figli, o sostituzione con relazioni. Motivare.
- Scrivere lo schema logico risultante in forma testuale, elencando per ogni relazione: nome, attributi, chiave primaria sottolineata concettualmente, chiavi esterne con la relazione di destinazione.

## 3.2 Chiavi

- Per ogni relazione individuare **tutte** le chiavi candidate, non solo quella scelta.
- Scegliere la chiave primaria motivando la scelta: stabilità, semplicità, dimensione, uso nelle join.
- Dichiarare esplicitamente le chiavi alternative, che diventeranno vincoli `UNIQUE`.
- Decidere caso per caso fra chiavi naturali e chiavi surrogate.
  - Le chiavi surrogate semplificano l'ORM e le join, ma non esimono dal dichiarare l'unicità della chiave naturale sottostante.
- Definire per ogni chiave esterna la politica di integrità referenziale: comportamento su cancellazione e su aggiornamento, con motivazione.
  - Per i dati amministrativi la cancellazione a cascata è quasi sempre sbagliata: una pratica chiusa non deve sparire perché è stato cancellato un utente.
  - Valutare la cancellazione logica al posto di quella fisica per gli utenti e per gli istituti non più attivi.

## 3.3 Dipendenze funzionali e normalizzazione

Questa sezione è quella in cui si dimostra di padroneggiare la teoria del Modulo 1, quindi va svolta per esteso e non liquidata con una frase.

- Elencare per ogni relazione le **dipendenze funzionali** che valgono sui suoi attributi.
- Calcolare la **chiusura** degli attributi dove serve per verificare le chiavi.
- Calcolare la **copertura canonica** dell'insieme delle dipendenze funzionali, mostrando i passaggi:
  - riduzione dei membri destri a un singolo attributo;
  - eliminazione degli attributi estranei nei membri sinistri;
  - eliminazione delle dipendenze ridondanti.
- Verificare le forme normali, una relazione alla volta:
  - **1NF**: atomicità dei valori, nessun attributo multivalore o composto residuo.
  - **2NF**: nessuna dipendenza parziale da una chiave composta.
  - **3NF**: nessuna dipendenza transitiva da attributi non primi.
  - **BCNF**: ogni determinante è una superchiave.
- Dove una relazione non è normalizzata, mostrare la **decomposizione** e verificarne le proprietà:
  - decomposizione senza perdita (join lossless);
  - conservazione delle dipendenze funzionali.
- Se si decide di **non** normalizzare fino a BCNF, dirlo apertamente e motivarlo con un argomento di performance o di conservazione delle dipendenze. Una denormalizzazione consapevole e motivata vale più di una normalizzazione subita.

## 3.4 Verifica di copertura dei requisiti

- Riprendere l'elenco dei dieci requisiti funzionali della traccia e verificare, uno per uno, che lo schema logico contenga tutti i dati necessari a soddisfarli.
- Riprendere l'elenco delle regole di business e verificare che ciascuna sia esprimibile sullo schema.
- Simulare a mente le query più frequenti e verificare che non richiedano acrobazie: se una query naturale risulta contorta, probabilmente lo schema va rivisto adesso, non dopo aver scritto il codice.

**Criterio di chiusura della Fase 3:** lo schema logico è scritto per esteso, ogni relazione ha chiave primaria e chiavi esterne dichiarate, la normalizzazione è documentata con i passaggi, e ogni requisito della traccia è soddisfacibile sullo schema.

---

# FASE 4 — Implementazione fisica della base di dati

Obiettivo: avere un database funzionante e popolato, ricostruibile da zero con due comandi.

## 4.1 Il principio: dove vive ogni pezzo dello schema

Questa è la decisione strutturale della fase, e va dichiarata nella relazione.

- **I modelli ORM sono l'unica definizione di tabelle, colonne, chiavi primarie ed esterne, vincoli `UNIQUE` e vincoli `CHECK`.** Ogni colonna è scritta una volta sola.
- **Un file SQL separato aggiunge ciò che l'ORM non esprime**: trigger, viste, viste materializzate, indici parziali, ruoli e privilegi.
- **Uno script unico esegue i due passi in fila.**

L'alternativa — DDL scritto a mano come fonte di verità e modelli che lo rispecchiano — è più ortodossa, ma costringe a scrivere ogni colonna due volte. Con sei tabelle sono oltre cento righe duplicate e un errore di battitura che si manifesta come errore incomprensibile a runtime. Con due settimane a disposizione il rischio non vale l'ortodossia. Nella relazione questa scelta si motiva così: *la definizione unica elimina il disallineamento fra schema logico e schema fisico; gli oggetti non esprimibili nell'ORM sono raccolti in un file SQL dedicato e versionato.*

Attenzione al punto delicato: i `CHECK` scritti nei modelli **sono comunque stringhe SQL** e finiscono davvero nel `CREATE TABLE`. Non si sta rinunciando a nulla, si sta solo scrivendo il vincolo accanto alla colonna che vincola.

## 4.2 Definizione dei modelli

- Un file `app/models.py`, una classe per tabella, nell'ordine delle dipendenze.
- Per ogni colonna usare il **tipo più stretto possibile**: le date sono date, i crediti sono interi con un intervallo, i codici hanno una lunghezza massima.
- L'obbligatorietà si esprime con l'annotazione: `Mapped[str]` genera `NOT NULL`, `Mapped[str | None]` ammette il nullo. Il nullo va concesso solo dove significa davvero "non ancora noto".
- Dichiarare le chiavi esterne con la politica esplicita, senza lasciare il default implicito. Per i dati amministrativi la cancellazione a cascata verso gli utenti è quasi sempre sbagliata: una pratica chiusa non deve sparire perché è stato cancellato un utente. Si usa `RESTRICT` verso utenti e istituti, e `CASCADE` solo verso ciò che appartiene davvero alla pratica.
- Per gli utenti e gli istituti non più attivi, preferire la **cancellazione logica** con un campo `attivo`.

Estratto rappresentativo, con i vincoli in evidenza:

```python
class Pratica(db.Model):
    __tablename__ = "pratica"

    id: Mapped[int] = mapped_column(primary_key=True)
    studente_id: Mapped[int] = mapped_column(
        sa.ForeignKey("utente.id", ondelete="RESTRICT"), index=True
    )
    docente_id: Mapped[int] = mapped_column(
        sa.ForeignKey("utente.id", ondelete="RESTRICT"), index=True
    )
    istituto_id: Mapped[int] = mapped_column(
        sa.ForeignKey("istituto.id", ondelete="RESTRICT"), index=True
    )

    anno_accademico: Mapped[str] = mapped_column(sa.String(9), index=True)
    periodo: Mapped[Periodo] = mapped_column(_enum(Periodo, "ck_pratica_periodo"))
    stato: Mapped[StatoPratica] = mapped_column(
        _enum(StatoPratica, "ck_pratica_stato"),
        default=StatoPratica.CREATA, index=True,
    )
    note: Mapped[str | None] = mapped_column(sa.Text)

    data_creazione: Mapped[datetime] = mapped_column(server_default=sa.func.now())
    arrivo_effettivo: Mapped[date | None]
    partenza_effettiva: Mapped[date | None]

    studente: Mapped[Utente] = relationship(
        back_populates="pratiche_da_studente", foreign_keys=[studente_id]
    )
    esami: Mapped[list[EsameMappato]] = relationship(
        back_populates="pratica", cascade="all, delete-orphan",
        order_by="EsameMappato.codice_estero",
    )

    __table_args__ = (
        sa.CheckConstraint(
            "studente_id <> docente_id", name="ck_pratica_studente_diverso_docente"
        ),
        sa.CheckConstraint(
            "partenza_effettiva IS NULL OR arrivo_effettivo IS NULL"
            " OR partenza_effettiva >= arrivo_effettivo",
            name="ck_pratica_date_coerenti",
        ),
        sa.CheckConstraint(
            "anno_accademico LIKE '____/__'", name="ck_pratica_formato_anno"
        ),
        sa.UniqueConstraint(
            "studente_id", "anno_accademico", "istituto_id",
            name="uq_pratica_studente_anno_istituto",
        ),
        sa.Index("ix_pratica_stato_anno", "stato", "anno_accademico"),
    )
```

## 4.3 Valori enumerati

Stati, periodi, ruoli e tipi di documento non devono essere testo libero. Vanno definiti una volta sola in `app/enums.py` come `Enum` di Python e mappati con una funzione di comodo:

```python
def _enum(tipo, nome_vincolo: str) -> sa.Enum:
    """Enum portabile: VARCHAR + CHECK, invece di un tipo ENUM nativo."""
    return sa.Enum(
        tipo, native_enum=False, validate_strings=True,
        values_callable=lambda e: [membro.value for membro in e],
        name=nome_vincolo,
    )
```

Il parametro `native_enum=False` è la scelta chiave: invece di un tipo `ENUM` nativo di PostgreSQL, SQLAlchemy genera una colonna `VARCHAR` con un vincolo `CHECK` sui valori ammessi. I vantaggi sono due, entrambi da citare nella relazione: il vincolo resta visibile e ispezionabile nello schema, e lo stesso codice funziona anche su SQLite. Il tipo `ENUM` nativo, per contro, è scomodissimo da modificare dopo la creazione.

Nello stesso file va definito il **grafo delle transizioni di stato ammesse**, come dizionario. Essendo l'unica definizione del ciclo di vita, la usano sia i controlli applicativi sia i test, e corrisponde uno a uno al trigger scritto in SQL.

## 4.4 Il file SQL aggiuntivo

In `scripts/schema_extra_postgres.sql` vanno gli oggetti che l'ORM non esprime. Ogni istruzione deve essere **idempotente**, cioè rieseguibile senza errori: `CREATE OR REPLACE`, `DROP ... IF EXISTS`, `CREATE INDEX IF NOT EXISTS`.

Contenuto previsto:

- **Trigger sulle transizioni di stato**, che impedisce salti di fase e ritorni indietro non previsti.
- **Trigger sulla verifica pre-partenza**, che rifiuta il passaggio se il Learning Agreement non risulta approvato o se non c'è alcun esame mappato. È una regola su tre tabelle: non esprimibile con un `CHECK`.
- **Trigger sulla chiusura**, che rifiuta la chiusura se manca il Transcript of Records o se restano esami non riconosciuti.
- **Trigger sulla data di decisione**, che la imposta automaticamente quando l'esito cambia.
- **Indice unico parziale** per garantire una sola versione corrente per tipo di documento: un `UNIQUE` normale non basta, perché il vincolo deve valere solo sulle righe correnti.
- **Vista** delle pratiche incomplete, che incapsula una delle query più frequenti citate dalla traccia.
- **Vista materializzata** per le statistiche del cruscotto, con la politica di aggiornamento documentata.
- **Ruoli e privilegi**, con il principio del privilegio minimo.

Esempio di trigger, quello sulle transizioni:

```sql
CREATE OR REPLACE FUNCTION verifica_transizione_stato()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.stato = OLD.stato THEN
        RETURN NEW;
    END IF;

    IF NOT (
        (OLD.stato = 'creata'                  AND NEW.stato = 'attesa_approvazione_la')
     OR (OLD.stato = 'attesa_approvazione_la'  AND NEW.stato IN ('creata', 'pre_partenza_completata'))
     OR (OLD.stato = 'pre_partenza_completata' AND NEW.stato = 'mobilita_in_corso')
     OR (OLD.stato = 'mobilita_in_corso'       AND NEW.stato = 'in_riconoscimento_esami')
     OR (OLD.stato = 'in_riconoscimento_esami' AND NEW.stato = 'chiusa')
    ) THEN
        RAISE EXCEPTION 'Transizione di stato non ammessa: % -> %', OLD.stato, NEW.stato;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_transizione_stato ON pratica;
CREATE TRIGGER trg_transizione_stato
    BEFORE UPDATE OF stato ON pratica
    FOR EACH ROW EXECUTE FUNCTION verifica_transizione_stato();
```

E l'indice unico parziale, che è un buon esempio da citare in relazione perché mostra un vincolo che l'ORM non sa esprimere:

```sql
CREATE UNIQUE INDEX IF NOT EXISTS uq_documento_corrente
    ON documento (pratica_id, tipo)
    WHERE corrente;
```

## 4.5 Lo script di creazione dello schema

`scripts/init_db.py` fa tre cose in fila e nient'altro:

1. crea tabelle, chiavi e vincoli dai modelli;
2. esegue il file SQL aggiuntivo, saltandolo automaticamente se il DBMS non è PostgreSQL;
3. non inserisce dati, che sono compito di un altro script.

```python
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app
from app.extensions import db

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
    parser.add_argument("--reset", action="store_true",
                        help="cancella tutte le tabelle prima di ricrearle (DISTRUTTIVO)")
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
```

Il commento su `exec_driver_sql` non è pedanteria: usare `sa.text()` su un file PL/pgSQL è un errore che si manifesta con un messaggio incomprensibile, perché i due punti dell'operatore di assegnamento `:=` verrebbero interpretati come segnaposto di parametri e il driver rifiuterebbe comunque un file con più istruzioni.

## 4.6 Popolamento con dati di prova

`scripts/seed.py`, con tre requisiti non negoziabili:

- **Deterministico.** Lo stesso script produce sempre lo stesso database, così i test sono ripetibili e il video della demo è preparabile.
- **Idempotente.** Rilanciarlo non duplica i dati: ogni blocco controlla prima se i dati esistono già.
- **Completo.** Deve esistere almeno una pratica **per ogni stato** del ciclo di vita, più un Learning Agreement rifiutato con motivazione, una modifica approvata, una rifiutata, e una pratica chiusa con un esame non riconosciuto. Senza pratiche negli stati avanzati non è possibile mostrare le funzionalità finali nel video.

Qui c'è la seconda scelta tecnica da motivare in relazione: **gli inserimenti massivi usano il Core, non l'ORM.**

```python
db.session.execute(
    sa.insert(Istituto.__table__),
    [
        {"nome": "University of Melbourne", "paese": "Australia", "citta": "Melbourne", "attivo": True},
        {"nome": "Keio University", "paese": "Giappone", "citta": "Tokyo", "attivo": True},
        # ...
    ],
)
```

Il motivo è che qui non servono né oggetti né logica di dominio: serve velocità e controllo sull'SQL prodotto. È esattamente il caso d'uso per cui il Core esiste. Dove invece servono gli oggetti subito dopo — per collegare pratiche, esami e documenti fra loro — si usa l'ORM. La divisione è deliberata e nella relazione si racconta così: *ORM dove serve il grafo di oggetti, Core dove serve solo scrivere righe.*

Un solo `commit`, alla fine, dentro un `try` con `rollback`: o entra tutto, o non entra niente.

## 4.7 Verifica della fase

- Eseguire `python -m scripts.init_db --reset` e poi `python -m scripts.seed`: si deve ottenere uno schema completo e popolato.
- Ispezionare il database con pgAdmin o `psql` e verificare che ci siano davvero le tabelle, i vincoli, i trigger e le viste attesi.
- Tentare **a mano**, direttamente in SQL, un'operazione vietata, e verificare che il database la rifiuti. Per esempio:

```sql
UPDATE pratica SET stato = 'chiusa' WHERE id = 1;
-- deve fallire: transizione non ammessa da 'creata'
```

Questa prova va conservata: è ottimo materiale per la sezione della relazione sull'integrità, perché dimostra che il vincolo esiste davvero e non solo nel codice Python.

**Criterio di chiusura della Fase 4:** due comandi ricostruiscono il database da zero, e i tentativi di violazione vengono respinti dal DBMS, non dall'applicazione.

---

# FASE 5 — Impostazione dell'applicazione Flask

Obiettivo: avere lo scheletro dell'applicazione collegato al database, prima di implementare qualunque funzionalità.

## 5.1 Le estensioni, create vuote

In `app/extensions.py` si creano le istanze delle estensioni **senza applicazione**, e le si collega dentro la factory. È il modo per evitare gli import circolari: i modelli importano `db` da qui senza dover importare l'applicazione.

```python
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Classe base dichiarativa in stile SQLAlchemy 2.0."""


db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "Devi accedere per visualizzare questa pagina."
login_manager.login_message_category = "warning"
```

L'uso di una `DeclarativeBase` esplicita al posto del vecchio `db.Model` automatico rende chiaro che i modelli sono normali classi mappate e abilita l'annotazione dei tipi con `Mapped[...]`, che è ciò che permette a SQLAlchemy di dedurre `NOT NULL` dalla presenza o assenza di `| None`.

## 5.2 L'application factory

Creare l'applicazione dentro una funzione invece che come variabile globale permette di istanziarla più volte con configurazioni diverse — sviluppo, dimostrazione, test — e rende espliciti gli import. È lo schema raccomandato da Flask.

```python
def create_app(nome_config: str = "dev") -> Flask:
    app = Flask(__name__)
    app.config.from_object(CONFIGS.get(nome_config, Config))

    from app.extensions import db, login_manager
    db.init_app(app)
    login_manager.init_app(app)

    # I modelli vanno importati PRIMA di create_all(), altrimenti i metadati
    # sono vuoti e non viene creata nessuna tabella.
    from app import models
    from app.models import Utente

    @login_manager.user_loader
    def carica_utente(id_utente: str) -> Utente | None:
        """Trasforma l'identita' salvata in sessione in un oggetto Utente."""
        return db.session.get(Utente, int(id_utente))

    from app.blueprints.auth import auth_bp
    from app.blueprints.docente import docente_bp
    from app.blueprints.pratiche import pratiche_bp
    from app.blueprints.pubblico import pubblico_bp
    from app.blueprints.studente import studente_bp
    from app.blueprints.ufficio import ufficio_bp

    app.register_blueprint(pubblico_bp)
    app.register_blueprint(pratiche_bp)          # dettaglio condiviso dai tre ruoli
    app.register_blueprint(auth_bp,     url_prefix="/auth")
    app.register_blueprint(studente_bp, url_prefix="/studente")
    app.register_blueprint(docente_bp,  url_prefix="/docente")
    app.register_blueprint(ufficio_bp,  url_prefix="/ufficio")

    _registra_pagine_errore(app)
    app.config["UPLOAD_FOLDER"].mkdir(parents=True, exist_ok=True)
    return app
```

Tre dettagli che risolvono altrettanti bug tipici:

- **I modelli si importano dentro la factory**, non in cima al file: importarli fuori riporta l'import circolare che si era evitato con `extensions.py`.
- **La `user_loader` è obbligatoria.** È il punto 4 dei cinque ingredienti di Flask-Login visti a lezione, ed è l'unico insieme alla classe utente che deve scrivere il programmatore. Senza, l'utente risulta autenticato ma `current_user` resta anonimo.
- **La cartella degli upload va creata all'avvio.** Altrimenti il primo caricamento fallisce con un errore di sistema poco comprensibile.

## 5.3 Configurazione

Nessun valore sensibile nel codice: tutto arriva dal file `.env` tramite `config.py`. Le opzioni che contano:

- `SQLALCHEMY_TRACK_MODIFICATIONS = False` — è deprecata e consuma memoria senza dare nulla.
- `SQLALCHEMY_ECHO` pilotata dalla variabile `SQL_ECHO` — si accende quando serve, senza toccare il codice.
- `SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}` — verifica che la connessione sia viva prima di riusarla dal pool, evitando l'errore che compare dopo che il database è stato riavviato.
- `MAX_CONTENT_LENGTH` — dimensione massima dei file caricati, calcolata dalla variabile `MAX_UPLOAD_MB`.

## 5.4 La sessione e le transazioni

Questo è il punto in cui Flask-SQLAlchemy fa il lavoro che altrimenti andrebbe scritto a mano, ed è utile capirlo perché va spiegato nella relazione.

- `db.session` **non è una sessione globale**: è legata alla singola richiesta HTTP. Nasce quando arriva la richiesta e viene chiusa alla fine, sempre, anche se la richiesta termina con un errore.
- Dentro una route, quindi, si lavora su oggetti e si chiude con un solo `db.session.commit()`. Non si scrivono `UPDATE`: la `Session` si accorge da sola degli oggetti modificati e genera le istruzioni necessarie. È l'unit of work.
- Ogni operazione che tocca più righe o più tabelle va racchiusa in un `try` con `rollback` esplicito, così non resta mai nulla a metà.

```python
try:
    documento.esito = Esito.APPROVATO if approvato else Esito.RIFIUTATO
    documento.motivazione = motivazione
    documento.deciso_il = datetime.now()
    if not approvato:
        documento.pratica.stato = StatoPratica.CREATA
    # Un solo commit: le due scritture sono atomiche.
    db.session.commit()
except Exception:
    db.session.rollback()
    raise
```

Va gestita anche `IntegrityError`, che è l'eccezione sollevata quando il database rifiuta una scrittura per violazione di un vincolo. Intercettarla e tradurla in un messaggio comprensibile è ciò che distingue un'applicazione curata da una che mostra all'utente il messaggio grezzo di PostgreSQL.

## 5.5 Le query e il problema delle query a cascata

È il difetto di performance più comune con un ORM, e il più facile da evitare se lo si conosce.

Se una route carica cento pratiche e il template, per ognuna, legge `pratica.istituto.nome`, l'ORM esegue **centouno query** invece di una: una per l'elenco e una per ogni riga. La soluzione è chiedere il caricamento anticipato della relazione:

```python
pratiche = db.session.scalars(
    db.select(Pratica)
    .where(Pratica.studente_id == current_user.id)
    # selectinload evita il problema delle query a cascata: senza di esso
    # il template eseguirebbe una query per ogni riga dell'elenco.
    .options(selectinload(Pratica.istituto), selectinload(Pratica.docente))
    .order_by(Pratica.anno_accademico.desc())
).all()
```

Il modo per accorgersene è attivare `SQL_ECHO=1` e contare le righe che scorrono nel terminale al caricamento di una pagina. Vale la pena farlo su ogni pagina di elenco: il confronto prima e dopo è ottimo materiale per la sezione sulle performance della relazione.

Due regole che tengono pulito il codice:

- **Il filtro di appartenenza sta nella query**, non nel template. Un elenco che carica tutto e poi nasconde le righe altrui nel template non è filtrato: è una falla.
- **Le interrogazioni non banali stanno in `app/queries.py`**, una funzione per query, ciascuna con il commento che spiega a cosa serve e l'SQL equivalente. Quando si arriva a scrivere la sezione "Query principali" della relazione, il materiale è già tutto lì.

## 5.6 Pagine di errore e messaggi

- Definire subito le pagine per 403, 404 e 500, con un template unico parametrizzato.
- Nel gestore del 500, chiamare `db.session.rollback()`: una transazione lasciata a metà va sempre annullata.
- Usare i messaggi flash con tre categorie — `success`, `warning`, `error` — rese nel template base con tre stili diversi.
- All'utente non deve mai arrivare il messaggio tecnico grezzo del database: quello va nel log.

**Criterio di chiusura della Fase 5:** l'applicazione si avvia da PyCharm, si collega al database, mostra una pagina che legge dati reali, il login funziona e la struttura delle cartelle è quella definitiva.

---

# FASE 6 — Autenticazione e autorizzazione

Obiettivo: nessuno vede o modifica ciò che non gli compete. È il primo dei dieci requisiti funzionali ed è anche uno degli aspetti su cui la traccia chiede attenzione particolare.

## 6.1 Autenticazione

- Implementare la classe utente richiesta da Flask-Login, con un identificatore univoco in forma di stringa.
- Implementare la callback che, a partire dall'identità salvata in sessione, ricostruisce l'istanza dell'utente.
- Implementare le route di accesso e di uscita, con i relativi template.
- Proteggere con il decoratore apposito tutte le route che richiedono un utente autenticato. Verificare che **nessuna** route sensibile sia rimasta scoperta.
- Gestire il redirect: chi tenta di accedere a una pagina protetta viene portato al login e, dopo l'accesso, alla pagina che voleva.

## 6.2 Gestione delle password

- Non memorizzare mai le password in chiaro, nemmeno nei dati di prova.
- Usare una libreria di hashing con algoritmo adeguato e sale automatico.
- Memorizzare solo l'hash, in una colonna di lunghezza sufficiente.
- Definire dei requisiti minimi sulle password in fase di registrazione e validarli lato server, non solo lato browser.
- Prevedere il messaggio di errore generico in caso di credenziali errate, senza rivelare se l'errore riguarda l'utente o la password.

## 6.3 Autorizzazione

Flask-Login gestisce l'autenticazione ma **non** l'autorizzazione: quella va implementata.

- Implementare un meccanismo riutilizzabile per il controllo del ruolo, per esempio un decoratore che accetta i ruoli ammessi.
- Distinguere due livelli di controllo, entrambi necessari:
  - **controllo di ruolo**: questo tipo di utente può accedere a questa funzione?
  - **controllo di appartenenza**: questo specifico utente può accedere a questo specifico oggetto?
- Il secondo è quello che viene dimenticato più spesso ed è il più grave. Va applicato su ogni route che riceve un identificatore di pratica, di documento o di esame.
  - Uno studente che modifica l'identificatore nell'URL non deve poter vedere la pratica di un altro.
  - Un docente non deve poter approvare una pratica di cui non è referente.
- Applicare il filtro anche alle **query di lista**, non solo alle pagine di dettaglio: le liste devono essere filtrate alla fonte, nella query, non nascondendo elementi nel template.
- Nascondere nell'interfaccia i comandi non permessi, ma non considerare questo un controllo di sicurezza: il controllo vero sta sempre lato server.

## 6.4 Protezione dei dati personali

- Limitare i dati personali esposti nelle pagine a quelli effettivamente necessari alla funzione.
- Non esporre in URL o in pagine pubbliche identificatori che permettano di enumerare gli utenti.
- Proteggere i documenti caricati: sono dati personali, e la traccia lo sottolinea espressamente.
- Registrare in un log le operazioni sensibili: approvazioni, rifiuti, chiusure, accessi ai documenti. *Consigliato*

**Criterio di chiusura della Fase 6:** provando ad accedere a risorse altrui manipolando gli URL, l'applicazione risponde sempre con un rifiuto, per tutti e tre i ruoli.

---

# FASE 7 — Implementazione delle funzionalità

Obiettivo: coprire i dieci requisiti funzionali minimi. L'ordine suggerito segue il flusso reale di una pratica, così che in ogni momento si possa provare l'applicazione dall'inizio.

## 7.1 Gestione degli istituti ospitanti

- Elenco degli istituti partner, visibile a tutti gli utenti autenticati.
- Inserimento, modifica e disattivazione degli istituti, riservati all'ufficio Overseas.
- Attributi minimi richiesti dalla traccia: nome, paese, città. Se ne possono aggiungere altri, purché motivati.
- Filtri e ordinamento per paese e per nome.
- Gestire la disattivazione di un istituto senza cancellarlo: le pratiche storiche devono continuare a riferirsi a esso.

## 7.2 Creazione della pratica di mobilità

- Form di creazione con: anno accademico, istituto ospitante scelto dalla lista, periodo previsto, docente referente ed eventuali note.
- Validazione lato server di ogni campo, con messaggi di errore chiari e riproposizione dei dati già inseriti.
- Impostazione automatica dello stato iniziale e della data di creazione.
- Elenco delle proprie pratiche per lo studente, con stato ben visibile.
- Pagina di dettaglio della pratica, che è il punto centrale dell'applicazione e da cui si raggiungono tutte le altre azioni.
  - Il dettaglio deve mostrare chiaramente **in che stato è la pratica e qual è il prossimo passo atteso, e da parte di chi**.

## 7.3 Inserimento del mapping degli esami

- Aggiunta, modifica ed eliminazione delle righe di corrispondenza fra esame estero ed esame interno.
- Per ogni riga sono richiesti: codice, titolo e crediti dell'insegnamento estero; codice, titolo e crediti dell'insegnamento di Ca' Foscari.
- Validazioni da prevedere:
  - nessun codice estero ripetuto nella stessa pratica;
  - crediti positivi ed entro un intervallo plausibile;
  - campi obbligatori non vuoti.
- Mostrare il totale dei crediti esteri e il totale dei crediti interni, così che lo squilibrio sia evidente a colpo d'occhio.
- Bloccare la modifica del mapping quando lo stato della pratica non lo consente.

## 7.4 Caricamento e valutazione del Learning Agreement

- Caricamento del file da parte dello studente, con i controlli descritti nella Fase 8.
- Passaggio della pratica allo stato di attesa di approvazione.
- Pagina del docente con l'elenco dei documenti in attesa di valutazione, ordinati per data.
- Visualizzazione o scaricamento del documento da parte del docente.
- Azione di approvazione e azione di rifiuto.
  - Registrazione della data della decisione.
  - Motivazione **obbligatoria** in caso di rifiuto, facoltativa in caso di approvazione.
  - Aggiornamento dello stato della pratica.
- Notifica dell'esito allo studente, almeno come messaggio visibile nel dettaglio della pratica.
- Gestione del caso di rifiuto: lo studente deve poter correggere e ricaricare.

## 7.5 Verifica pre-partenza

- Vista dell'ufficio con le pratiche pronte per la verifica.
- Controllo automatico delle condizioni prima di permettere l'azione: dati essenziali presenti e Learning Agreement approvato.
- Se le condizioni non sono soddisfatte, il pulsante non deve essere disponibile e il tentativo via URL deve essere respinto.
- Registrazione della fase pre-partenza completata, con data e utente che ha effettuato la verifica.
- Passaggio di stato conseguente.

## 7.6 Gestione della mobilità in corso

- Inserimento e modifica delle date effettive di arrivo e di partenza da parte dello studente.
- Validazioni: la partenza non precede l'arrivo; le date sono compatibili con l'anno accademico e con il periodo previsto.
- Passaggio allo stato di mobilità in corso.
- Segnalazione visibile quando le date effettive divergono significativamente dal periodo previsto. *Facoltativo*

## 7.7 Modifiche al Learning Agreement

Questa è la funzionalità più complessa del progetto e va progettata con cura prima di scriverla.

- Avvio di una proposta di modifica da parte dello studente.
- Modifica della lista degli esami e del relativo mapping all'interno della proposta.
- Caricamento del Learning Agreement aggiornato insieme alla proposta.
- Valutazione da parte del docente, con approvazione o rifiuto, data e motivazione.
- **Comportamento in caso di rifiuto: ripristino del mapping precedentemente concordato.** Va deciso e documentato come si realizza:
  - conservando una copia dello stato approvato e ripristinandola;
  - oppure applicando le modifiche solo dopo l'approvazione, tenendole in un'area separata fino a quel momento;
  - oppure con versionamento completo del mapping, in cui ogni versione ha uno stato.
  - La terza opzione è la più solida e la più interessante da raccontare in relazione, ma anche la più costosa: sceglierla solo se c'è tempo.
- Sono ammesse più modifiche successive: la struttura deve reggere la seconda e la terza proposta, non solo la prima.
- Storico delle modifiche visibile nel dettaglio della pratica, con esito e data di ciascuna.

## 7.8 Caricamento del Transcript of Records

- Caricamento del documento da parte dello studente dopo il rientro.
- Sblocco dell'inserimento di voto e data di superamento per ciascun esame solo dopo il caricamento.
- Inserimento dei risultati per ciascuna riga del mapping approvato.
- Validazioni: voto nell'intervallo ammesso, data di superamento coerente con il periodo di mobilità, gestione degli esami non sostenuti.
- Passaggio allo stato di riconoscimento esami una volta completato l'inserimento.

## 7.9 Riconoscimento degli esami

- Vista del docente con gli esami da riconoscere, raggruppati per pratica.
- Approvazione o rifiuto **per singolo esame**, non solo per l'intera pratica.
- Registrazione per ciascuna decisione di data, esito ed eventuale motivazione.
- Gestione del caso misto, in cui alcuni esami sono riconosciuti e altri no.
- Indicatore di avanzamento del riconoscimento sulla pratica.

## 7.10 Chiusura della pratica

- Vista dell'ufficio con le pratiche pronte per la chiusura.
- Verifica automatica delle condizioni: Transcript of Records caricato e riconoscimento completato.
- Registrazione della chiusura con data e utente.
- Passaggio allo stato finale.
- Dopo la chiusura la pratica diventa di sola lettura per tutti i ruoli. Questa regola va imposta lato server, non solo nascondendo i pulsanti.
- Riepilogo finale della pratica: crediti riconosciuti, esami approvati, esami non approvati.

**Criterio di chiusura della Fase 7:** è possibile percorrere l'intero ciclo di vita di una pratica, dalla creazione alla chiusura, usando tre account di ruolo diverso, senza mai intervenire manualmente sul database.

---

# FASE 8 — Gestione dei documenti allegati

Obiettivo: gestire in modo sicuro i file caricati dagli utenti. La traccia chiarisce che non serve modellare il contenuto dei documenti, ma la loro gestione va fatta bene.

## 8.1 Caricamento

- Definire i formati ammessi e rifiutare tutto il resto.
- Definire una dimensione massima e gestire con un messaggio chiaro il superamento, non con un errore del server.
- Non fidarsi mai del nome del file fornito dal browser: va normalizzato prima dell'uso.
- Non fidarsi dell'estensione dichiarata come garanzia del contenuto.
- Generare un nome di archiviazione indipendente dal nome originale, conservando quest'ultimo solo come dato da mostrare all'utente.

## 8.2 Archiviazione

- Decidere dove risiedono i file e motivare la scelta:
  - **su filesystem, con riferimento nel database**: leggero, semplice, ma richiede attenzione alla coerenza fra file e righe;
  - **dentro il database come dato binario**: coerenza transazionale garantita, backup unico, ma database più pesante.
  - Per un progetto di questo tipo la prima opzione è generalmente preferibile, purché la coerenza sia gestita.
- Se si sceglie il filesystem, la cartella dei documenti deve essere **fuori dalla cartella dei file statici**: nessun file deve essere raggiungibile con un indirizzo diretto.
- Organizzare i file in sottocartelle per pratica, per non ritrovarsi con una cartella unica ingestibile.

## 8.3 Metadati da memorizzare

- Riferimento alla pratica e al tipo di documento.
- Nome originale del file e nome di archiviazione.
- Data e ora di caricamento.
- Utente che ha effettuato il caricamento.
- Dimensione e tipo del file.
- Numero di versione, se si gestisce lo storico.
- Eventuale stato di validazione.

## 8.4 Accesso ai file

- Ogni scaricamento passa da una route dedicata che, prima di restituire il file, verifica i permessi dell'utente sulla pratica.
- Impostare correttamente le intestazioni di risposta, così che il browser gestisca il file nel modo previsto.
- Non esporre mai il percorso reale del file sul disco.

## 8.5 Storico delle versioni — *Consigliato*

La traccia lo indica esplicitamente fra gli spunti di arricchimento.

- Conservare tutte le versioni caricate anziché sovrascriverle.
- Registrare per ciascuna versione la data di caricamento.
- Indicare quale versione è quella corrente.
- Mostrare la cronologia nel dettaglio della pratica, con possibilità di consultare le versioni precedenti.
- Impedire la cancellazione di versioni già valutate dal docente.

**Criterio di chiusura della Fase 8:** un file caricato da uno studente non è raggiungibile da un altro studente in nessun modo, nemmeno conoscendone il nome.

---

# FASE 9 — Integrità, transazioni e consistenza

Obiettivo: garantire che il database non finisca mai in uno stato incoerente, nemmeno in caso di errore a metà di un'operazione o di accessi concorrenti. È il primo degli aspetti raccomandati dalla traccia.

## 9.1 Individuazione delle operazioni transazionali

Un'operazione va racchiusa in una transazione quando tocca più righe o più tabelle e ha senso solo se riesce per intero.

- Creazione della pratica con l'inserimento contestuale del mapping degli esami.
- Approvazione del Learning Agreement con contestuale cambio di stato della pratica e registrazione della decisione.
- Approvazione di una modifica con sostituzione del mapping precedente.
- Rifiuto di una modifica con ripristino del mapping precedentemente concordato.
- Caricamento del Transcript of Records con creazione delle righe dei risultati.
- Chiusura della pratica con verifica delle condizioni e registrazione finale.

## 9.2 Implementazione delle transazioni

- Definire con precisione dove inizia e dove finisce ogni transazione. Deve essere leggibile dal codice, non dedotto.
- Nessuna operazione parziale deve poter essere confermata: in caso di eccezione la transazione va annullata per intero.
- Gestire esplicitamente le eccezioni del database, distinguendo violazione di vincolo, violazione di unicità e altri errori, e traducendole in messaggi comprensibili.
- Attenzione al caso misto file più database: se il salvataggio del file riesce ma la scrittura sul database fallisce, il file orfano va rimosso. Definire l'ordine delle operazioni per rendere questo caso gestibile.

## 9.3 Livelli di isolamento

- Ricordare che PostgreSQL considera ogni istruzione una transazione implicita e usa `READ COMMITTED` come livello predefinito.
- Individuare le operazioni per cui il livello predefinito non basta, cioè quelle che leggono un valore e poi decidono in base a esso.
  - La verifica pre-partenza legge lo stato del Learning Agreement e poi scrive.
  - La chiusura della pratica legge lo stato del riconoscimento e poi scrive.
  - L'approvazione concorrente della stessa pratica da parte di due sessioni.
- Per queste operazioni valutare un livello di isolamento più stretto oppure un blocco esplicito in lettura, e **motivare la scelta** nella relazione facendo riferimento alle anomalie evitate: letture sporche, letture non ripetibili, aggiornamenti persi, righe fantasma.
- Non alzare il livello di isolamento ovunque per prudenza: va alzato dove serve e spiegato perché.

## 9.4 Dove vive ciascun controllo

- Compilare l'elenco definitivo delle regole di business della Fase 1 indicando per ciascuna dove è garantita:
  - vincolo di dominio o `CHECK`, per i controlli sulla singola riga;
  - chiave o vincolo di unicità, per l'identità;
  - integrità referenziale, per i collegamenti;
  - trigger, per le regole che coinvolgono più tabelle;
  - transazione, per l'atomicità delle operazioni composte;
  - codice applicativo, solo per ciò che non è esprimibile a livello di database.
- Il principio da seguire e da dichiarare: **le regole che riguardano la correttezza dei dati stanno nel database**, quelle che riguardano l'esperienza d'uso stanno nell'applicazione.
- Un controllo presente solo nel front-end non è un controllo. Ogni validazione lato browser deve avere la sua controparte lato server.

**Criterio di chiusura della Fase 9:** interrompendo artificialmente un'operazione composta a metà, il database resta coerente e nessun dato parziale sopravvive.

---

# FASE 10 — Performance

Obiettivo: mostrare consapevolezza del costo delle query. È il terzo aspetto raccomandato dalla traccia.

## 10.1 Individuazione delle query frequenti

- Elencare le interrogazioni che l'applicazione esegue più spesso o su più dati:
  - elenco delle pratiche di uno studente;
  - elenco delle pratiche di cui un docente è referente;
  - elenco dei documenti in attesa di valutazione;
  - ricerca delle pratiche incomplete;
  - pratiche per anno accademico;
  - pratiche per stato, per paese o per istituto ospitante;
  - riepilogo dei crediti riconosciuti per pratica.
- Per ciascuna annotare: con quale frequenza viene eseguita, quali colonne compaiono nelle condizioni di filtro, quali negli ordinamenti, quali nelle join.

## 10.2 Definizione degli indici

- Verificare quali indici esistono già implicitamente: le chiavi primarie e i vincoli di unicità sono già indicizzati, non vanno duplicati.
- Aggiungere indici sulle chiavi esterne usate nelle join più frequenti.
- Aggiungere indici sulle colonne usate nei filtri più frequenti, in particolare stato, anno accademico e riferimento allo studente.
- Valutare indici composti dove il filtro combina più colonne, rispettando l'ordine delle colonne nell'indice.
- Ricordare il costo degli indici: rallentano gli inserimenti e le modifiche e occupano spazio. Non indicizzare tutto.
- Documentare **ogni indice creato con la query che lo giustifica**. Un indice senza motivazione vale zero in sede di valutazione.

## 10.3 Viste e viste materializzate — *Consigliato*

- Usare **viste** per incapsulare le query ricorrenti e complesse, migliorando anche la leggibilità del codice applicativo.
- Valutare **viste materializzate** per i riepiloghi aggregati che non devono essere in tempo reale, per esempio le statistiche della dashboard d'ufficio.
- Definire e documentare la politica di aggiornamento della vista materializzata: quando e come viene ricalcolata.
- Discutere il compromesso fra freschezza del dato e costo del ricalcolo.

## 10.4 Verifica sperimentale

- Usare lo strumento di analisi del piano di esecuzione del DBMS per confrontare la stessa query con e senza indice.
- Conservare gli esiti del confronto: sono materiale eccellente per la relazione, perché mostrano una scelta misurata e non dichiarata.
- Attivare la stampa dell'SQL generato dall'ORM e verificare che non ci siano **query ripetute in ciclo**: è il problema di performance più comune con un ORM, e si risolve con la strategia di caricamento appropriata sulle relazioni.

**Criterio di chiusura della Fase 10:** esiste un elenco motivato degli indici e delle viste, e almeno un confronto misurato prima/dopo da citare nella relazione.

---

# FASE 11 — Front-end

Obiettivo: un'interfaccia minimale ma coerente e usabile. La traccia è esplicita: il front-end deve essere minimale, JavaScript non è richiesto e non influisce sulla valutazione. Non è qui che si guadagnano punti, ma è qui che si possono perdere se l'applicazione risulta incomprensibile nella demo.

## 11.1 Impostazione dei template

- Creare un **template base** con la struttura comune: intestazione, menu di navigazione, area dei messaggi, contenuto, piè di pagina.
- Tutti gli altri template estendono il base. Nessuna pagina deve ripetere la struttura.
- Creare frammenti riutilizzabili per gli elementi ricorrenti: riga di una pratica, scheda di un documento, indicatore di stato, blocco di un form.
- Il menu di navigazione deve cambiare in base al ruolo dell'utente autenticato.

## 11.2 Pagine da realizzare

- Pagina pubblica di benvenuto e pagina di accesso.
- **Area studente**: elenco delle proprie pratiche; creazione di una pratica; dettaglio della pratica; gestione del mapping degli esami; caricamento dei documenti; proposta di modifica; inserimento dei risultati.
- **Area docente**: elenco delle pratiche di cui è referente; coda delle valutazioni in attesa; dettaglio della pratica in sola lettura con i comandi di decisione; schermata di riconoscimento degli esami.
- **Area ufficio**: elenco completo delle pratiche con filtri; gestione degli istituti partner; verifica pre-partenza; chiusura delle pratiche; eventuale dashboard.
- Pagine di errore per risorsa non trovata, accesso negato ed errore interno.

## 11.3 Presentazione delle informazioni senza tabelle pesanti

- Rappresentare gli elenchi come schede o righe con etichette esplicite, evitando griglie fitte difficili da leggere.
- Rendere lo **stato della pratica immediatamente riconoscibile**, per esempio con un'etichetta colorata sempre nella stessa posizione.
- Mostrare in ogni pagina di dettaglio, in alto, la risposta a tre domande: in che stato siamo, cosa manca, chi deve agire.
- Ordinare gli elenchi con un criterio sensato e dichiararlo.
- Prevedere il caso di elenco vuoto con un messaggio che spieghi cosa fare, non con una pagina bianca.

## 11.4 Form e validazione

- Ogni campo ha un'etichetta esplicita e, dove serve, un testo di aiuto.
- Gli errori di validazione compaiono accanto al campo interessato, non solo in cima alla pagina.
- I dati già inseriti vengono ripresentati dopo un errore: non far riscrivere tutto all'utente.
- I campi obbligatori sono segnalati in modo uniforme.
- I menu a tendina sono popolati dal database, mai scritti a mano nel template: vale in particolare per istituti, docenti e valori di stato.
- Le azioni distruttive o irreversibili chiedono conferma su una pagina dedicata.

## 11.5 Coerenza e cura finale

- Un unico framework CSS, un'unica tavolozza di colori, un unico stile per i pulsanti.
- Terminologia coerente fra interfaccia, database e relazione: se nel database si chiama "pratica", non chiamarla "domanda" nell'interfaccia.
- Formato uniforme delle date in tutta l'applicazione.
- Verificare la leggibilità su una finestra stretta: durante il video la finestra potrebbe non essere a schermo intero.

**Criterio di chiusura della Fase 11:** una persona che non ha sviluppato il progetto riesce a completare un intero ciclo di pratica senza chiedere spiegazioni.

---

# FASE 12 — Estensioni facoltative

Da affrontare **solo** dopo che tutto il nucleo obbligatorio funziona. La traccia avverte che complicare il progetto senza motivo è penalizzante: meglio due estensioni fatte bene che cinque abbozzate.

## 12.1 Dashboard per l'ufficio Overseas

- Conteggio delle pratiche per stato.
- Distribuzione delle mobilità per paese e per istituto ospitante.
- Confronto per anno accademico.
- Elenco delle pratiche ferme da più tempo in uno stato intermedio.
- Realizzabile con viste o viste materializzate, ricollegandosi alla Fase 10.

## 12.2 Notifiche per pratiche incomplete

- Individuazione delle pratiche ferme oltre una soglia di tempo.
- Segnalazione visibile nell'area dell'utente che deve agire.
- Eventuale riepilogo periodico per l'ufficio.
- Definire dove risiede la logica: query su richiesta oppure tabella di notifiche popolata da trigger.

## 12.3 Gestione della firma dei documenti

- Definizione dei firmatari previsti per ciascun tipo di documento.
- Definizione dell'ordine in cui devono firmare.
- Stato di avanzamento della raccolta firme.
- Ciclo di scaricamento e nuovo caricamento del documento firmato.
- È l'estensione più impegnativa fra quelle suggerite: valutarla solo con tempo abbondante.

## 12.4 Altre estensioni sensate

- Catalogo degli insegnamenti di Ca' Foscari, per evitare che lo studente digiti codice e titolo a mano.
- Esportazione del riepilogo della pratica in formato stampabile.
- Ricerca testuale sulle pratiche per l'ufficio.
- Storico completo delle transizioni di stato, con data e utente per ciascun passaggio.

---

# FASE 13 — Testing e collaudo

Obiettivo: trovare i problemi prima che li trovi la docente.

## 13.1 Collaudo funzionale

- Percorrere l'intero ciclo di vita di una pratica con i tre ruoli, dall'inizio alla chiusura, verificando ogni passaggio di stato.
- Ripetere il percorso nei casi non lineari:
  - Learning Agreement rifiutato e poi ricaricato e approvato;
  - modifica proposta e approvata;
  - modifica proposta e rifiutata, verificando il ripristino del mapping precedente;
  - due modifiche successive sulla stessa pratica;
  - esami parzialmente riconosciuti;
  - studente con due pratiche in anni accademici diversi.
- Verificare che ogni requisito dei dieci minimi sia dimostrabile con una sequenza concreta di clic. Se non è dimostrabile, non è implementato.

## 13.2 Collaudo dei permessi

- Per ogni ruolo, tentare deliberatamente di accedere alle risorse degli altri ruoli.
- Manipolare gli identificatori negli URL e verificare che si venga sempre respinti.
- Verificare l'accesso alle route protette senza autenticazione.
- Verificare che i documenti non siano scaricabili da chi non ha diritto.

## 13.3 Collaudo dei vincoli e dell'integrità

- Tentare a mano, direttamente sul database, le operazioni che devono essere vietate, e verificare che il DBMS le rifiuti.
- Verificare che ogni trigger scatti nelle condizioni previste e che non scatti in quelle non previste.
- Verificare le transizioni di stato illegali.
- Simulare un errore a metà di un'operazione composta e verificare l'annullamento completo.

## 13.4 Casi limite e robustezza

- Campi vuoti, campi con soli spazi, testi molto lunghi.
- Caratteri accentati e caratteri speciali nei nomi e nei titoli.
- Date implausibili: nel futuro remoto, nel passato remoto, invertite.
- Voti fuori intervallo e crediti negativi o nulli.
- File di formato non ammesso, file troppo grandi, file vuoti, file senza estensione.
- Doppio invio dello stesso form.
- Uso dei pulsanti avanti e indietro del browser dopo un'azione.
- Sessione scaduta durante la compilazione di un form.

## 13.5 Revisione del codice

- Rileggere il codice cercando funzioni troppo lunghe, logica duplicata, nomi poco chiari.
- Eliminare codice morto, stampe di debug e commenti obsoleti.
- Verificare che i commenti spieghino le scelte e non ripetano ciò che il codice già dice.
- Verificare che nessuna credenziale sia rimasta scritta nel codice.
- Verificare che la struttura in cartelle e blueprint sia ancora coerente con quanto dichiarato.
- Verificare che l'applicazione parta da zero su una macchina pulita seguendo solo le proprie istruzioni.

**Criterio di chiusura della Fase 13:** l'intero elenco è stato percorso e ogni problema trovato è stato corretto o annotato consapevolmente.

---

# FASE 14 — Stesura della relazione

Obiettivo: un unico file PDF strutturato secondo l'indice raccomandato dalla docente. La documentazione è **il primo dei quattro parametri di valutazione**: vale quanto il codice, e va trattata come tale.

## 14.1 Struttura richiesta

L'ordine è quello indicato dalla traccia e va rispettato.

- **1. Introduzione**
  - Descrizione ad alto livello dell'applicazione.
  - Contesto del programma Overseas e problema affrontato.
  - Struttura del documento.
- **2. Funzionalità principali**
  - Descrizione delle funzionalità offerte, organizzata per ruolo o per fase della mobilità.
  - Spiegazione di come è stato interpretato lo spunto della traccia e di cosa è stato aggiunto.
  - Eventuali schermate dell'applicazione a supporto.
- **3. Progettazione concettuale e logica**
  - Schema Entità-Relazione **nella notazione grafica del Modulo 1**.
  - Spiegazione delle entità, delle relazioni e delle cardinalità.
  - Elenco dei vincoli non esprimibili graficamente.
  - Ristrutturazione dello schema, con le scelte motivate.
  - Schema logico risultante, con chiavi primarie ed esterne.
  - Analisi delle dipendenze funzionali, copertura canonica e verifica delle forme normali.
  - Eventuali denormalizzazioni consapevoli, con motivazione.
- **4. Query principali**
  - Selezione delle interrogazioni più interessanti, in sintassi SQL leggibile.
  - Per ciascuna: cosa serve a fare, perché è interessante, come è stata resa efficiente.
  - Evitare l'elenco di dieci `SELECT` banali: meglio quattro o cinque query che mostrano join, aggregazioni, sottointerrogazioni e viste.
- **5. Principali scelte progettuali**
  - Politiche di integrità e livello a cui sono garantite.
  - Ruoli e politiche di autorizzazione.
  - Uso di indici e viste, con le motivazioni.
  - Gestione degli allegati.
  - Gestione degli stati della pratica, con il diagramma degli stati.
  - Uso delle transazioni e scelta dei livelli di isolamento.
  - **Ogni scelta va motivata**: è la parola che ricorre più spesso nella traccia.
- **6. Ulteriori informazioni**
  - DBMS scelto e perché.
  - Librerie utilizzate e loro ruolo.
  - Struttura del codice e organizzazione in moduli.
  - Istruzioni per l'installazione e l'avvio.
  - Limiti noti e possibili sviluppi futuri.
- **7. Appendice: contributo al progetto**
  - Spiegazione di come i diversi membri hanno contribuito al design e allo sviluppo.
  - È richiesta esplicitamente: non ometterla e non liquidarla con una riga.

## 14.2 Criteri di qualità della relazione

- Scrivere in modo scorrevole, in italiano corretto, evitando l'elenco puntato per ogni cosa: la relazione è un testo, non una scaletta.
- Le figure vanno numerate, referenziate nel testo e leggibili una volta stampate.
- Il codice riportato va limitato ai frammenti significativi: non incollare interi file.
- Uniformare la terminologia con quella dell'applicazione e del database.
- Rileggere per intero almeno una volta a distanza di un giorno dalla stesura.
- Far rileggere il testo a qualcuno che non lo ha scritto.

## 14.3 Errori da evitare nella relazione

- Descrivere solo cosa si è fatto senza mai dire perché.
- Usare una notazione ER diversa da quella del corso.
- Presentare uno schema logico che non corrisponde al database realmente implementato.
- Dichiarare vincoli e trigger che nel codice non esistono.
- Saltare la normalizzazione o liquidarla con "lo schema è in terza forma normale" senza dimostrarlo.
- Consegnare la relazione in un formato diverso dal PDF o divisa in più file.

**Criterio di chiusura della Fase 14:** la relazione è un unico PDF, segue i sette punti richiesti, e ogni affermazione che contiene corrisponde a qualcosa che esiste davvero nel codice o nel database.

---

# FASE 15 — Video dimostrativo

Obiettivo: un video di **massimo 10 minuti**, con cattura dello schermo e commento a voce fuori campo, che mostri l'applicazione funzionante.

## 15.1 Preparazione

- Ripristinare il database con lo script di popolamento, così da partire da uno stato noto e pulito.
- Preparare in anticipo gli account dei tre ruoli e tenerli pronti per l'accesso.
- Preparare i file da caricare durante la demo, con nomi sensati.
- Chiudere notifiche, schede del browser non pertinenti e tutto ciò che potrebbe comparire nella registrazione.
- Aumentare la dimensione dei caratteri del browser se necessario: il video deve essere leggibile.
- Fare almeno una prova completa a vuoto, cronometrando.

## 15.2 Scaletta consigliata

- Apertura molto breve: cosa fa l'applicazione, in due frasi.
- Accesso come studente: creazione della pratica, inserimento del mapping degli esami, caricamento del Learning Agreement.
- Accesso come docente: visualizzazione del documento, rifiuto con motivazione, poi approvazione dopo la correzione.
- Accesso come ufficio: verifica pre-partenza.
- Ritorno allo studente: date effettive, proposta di modifica.
- Docente: valutazione della modifica, mostrando il ripristino in caso di rifiuto.
- Studente: caricamento del Transcript of Records e inserimento dei voti.
- Docente: riconoscimento degli esami.
- Ufficio: chiusura della pratica ed eventuale dashboard.
- Chiusura: accenno agli aspetti non visibili nell'interfaccia, come vincoli, trigger e indici.

## 15.3 Consigli sulla registrazione

- Parlare con calma e spiegare **cosa si sta mostrando e perché**, non descrivere i movimenti del mouse.
- Non leggere un testo scritto in modo meccanico, ma non improvvisare del tutto: tenere una traccia a punti.
- Non mostrare il codice, se non per pochi secondi e solo se serve a spiegare qualcosa che l'interfaccia non mostra.
- Non superare il limite dei 10 minuti: è un vincolo, non un'indicazione.
- Verificare prima di consegnare che l'audio si senta e che lo schermo sia leggibile.

---

# FASE 16 — Pacchetto di consegna

Obiettivo: un unico file ZIP caricato su Moodle nella finestra dedicata, con dentro esattamente ciò che è richiesto.

## 16.1 Contenuto del pacchetto

- **Codice sorgente completo**, con tutte le risorse: immagini, fogli di stile, template.
- **Script** di creazione dello schema e di popolamento del database.
- **File delle dipendenze**, per permettere la ricostruzione dell'ambiente.
- **Istruzioni di avvio** in un file leggibile alla radice del pacchetto: prerequisiti, installazione, configurazione, creazione del database, avvio, credenziali degli utenti di prova.
- **Relazione in un unico file PDF**.
- **Video** della demo, entro i 10 minuti.
- Non è richiesto il dump del database usato in sviluppo.

## 16.2 Controlli finali prima dell'invio

- Nessuna credenziale reale, nessuna chiave segreta vera, nessun dato personale reale nel pacchetto.
- Nessun ambiente virtuale, nessuna cartella di cache, nessun file temporaneo.
- Nessun file caricato dagli utenti durante i test dentro la cartella degli upload.
- Il codice nel pacchetto è la versione finale, non una intermedia.
- La relazione è aggiornata rispetto al codice consegnato.
- Il pacchetto è stato estratto in una cartella pulita e l'applicazione è stata avviata **da lì**, seguendo solo le istruzioni scritte, senza usare nulla che sia rimasto sulla macchina di sviluppo.
- Il nome del file ZIP identifica chiaramente il gruppo.
- Il caricamento su Moodle è stato completato ed è stata verificata la ricevuta.

---

# APPENDICE A — Autovalutazione sui quattro criteri

Il progetto viene valutato su quattro parametri. Prima di consegnare, rispondere onestamente a ciascuna domanda.

## A.1 Documentazione

- La relazione segue i sette punti richiesti?
- Lo schema ER usa la notazione del Modulo 1?
- Ogni scelta progettuale è motivata e non solo descritta?
- La normalizzazione è dimostrata con i passaggi?
- L'appendice sui contributi è presente?

## A.2 Database

- Lo schema è normalizzato, o le eccezioni sono motivate?
- I vincoli di integrità sono dichiarati nel database e non solo nel codice?
- Ci sono trigger, e risolvono problemi reali?
- Le transazioni sono usate dove servono, con il livello di isolamento giusto?
- Gli indici esistono e sono giustificati da query concrete?
- I ruoli e le autorizzazioni sono definiti?

## A.3 Funzionalità

- Tutti e dieci i requisiti minimi sono implementati e dimostrabili?
- Il flusso completo della pratica funziona senza interventi manuali?
- I casi non lineari, in particolare il rifiuto di una modifica, sono gestiti correttamente?
- Le estensioni aggiunte sono utili e motivate, e non complicazioni fini a sé stesse?

## A.4 Codice

- La struttura in moduli e blueprint è chiara?
- La logica di accesso ai dati è separata dalle route?
- Non ci sono duplicazioni evidenti?
- I nomi sono coerenti e in una sola lingua?
- I commenti spiegano le scelte non ovvie?
- L'applicazione parte da zero su una macchina pulita?

---

# APPENDICE B — Errori comuni da evitare

- Iniziare a scrivere codice prima di aver chiuso la progettazione concettuale e logica.
- Progettare lo schema partendo dalle schermate invece che dai dati.
- Mettere tutti i controlli nel codice applicativo e nessuno nel database, e poi scrivere nella relazione che l'integrità è garantita.
- Dichiarare nella relazione vincoli e trigger che non esistono nel codice.
- Mescolare italiano e inglese nei nomi di tabelle, colonne e variabili.
- Dimenticare il controllo di appartenenza e proteggere solo con il controllo di ruolo.
- Filtrare le liste nel template invece che nella query.
- Gestire il mapping degli esami senza pensare in anticipo al caso del rifiuto di una modifica.
- Salvare i documenti dentro la cartella dei file statici.
- Popolare il database con dati insufficienti, che non permettono di mostrare gli stati avanzati durante la demo.
- Rimandare la relazione alla fine e doverla ricostruire a memoria.
- Aggiungere funzionalità complesse ma non motivate, che la traccia avverte esplicitamente essere penalizzanti.
- Superare i 10 minuti di video.
- Consegnare un pacchetto che non parte su una macchina pulita.

---

# APPENDICE C — Ordine di lavoro consigliato

I blocchi sono elencati nell'ordine in cui conviene affrontarli. I blocchi sulla stessa riga logica possono procedere in parallelo una volta che le fasi precedenti sono chiuse.

- **Blocco iniziale, sequenziale e indispensabile:** Fase 0, Fase 1, Fase 2, Fase 3. Nulla di ciò che viene dopo ha senso se questo blocco non è chiuso, e rifarlo dopo costa moltissimo.
- **Blocco di avvio dello sviluppo:** Fase 4 e Fase 5 possono procedere in parallelo, purché lo schema logico sia già congelato.
- **Blocco fondante dell'applicazione:** Fase 6. Va fatta prima delle funzionalità, perché ogni funzionalità dovrà appoggiarsi ai controlli di accesso.
- **Blocco centrale:** Fase 7 e Fase 8 procedono insieme, seguendo l'ordine del flusso della pratica. La Fase 11 può avanzare in parallelo, pagina per pagina, man mano che le funzionalità si completano.
- **Blocco di consolidamento:** Fase 9 e Fase 10, da affrontare quando le funzionalità sono complete, perché prima non si sa ancora quali siano le query e le operazioni critiche reali.
- **Blocco facoltativo:** Fase 12, solo con tempo residuo e solo su ciò che si riesce a fare bene.
- **Blocco di chiusura:** Fase 13, poi Fase 14, poi Fase 15, poi Fase 16, in quest'ordine. Il video si registra su un'applicazione già collaudata, e il pacchetto si prepara su una relazione già finita.

**Nota sulla parallelizzazione:** le fasi di progettazione vanno affrontate insieme e discusse da tutti, perché le decisioni prese lì condizionano tutto il resto. Le fasi di implementazione si dividono bene per area funzionale o per blueprint, purché ci si accordi in anticipo sulle interfacce fra le parti e si eviti che due persone tocchino gli stessi file.

# APPENDICE D — Comandi di riferimento

Da tenere a portata di mano: sono i comandi che servono ogni giorno.

## D.1 Primo avvio su una macchina nuova

```
git clone <url-del-repository> overseas
cd overseas
python -m venv .venv
source .venv/bin/activate          # su Windows:  .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # su Windows:  copy .env.example .env
```

Poi aprire `.env` e impostare `SECRET_KEY` e `DATABASE_URL`.

## D.2 Creazione del database PostgreSQL

```
createdb overseas
psql -d overseas -c "CREATE ROLE overseas_app LOGIN PASSWORD 'scegli-una-password';"
psql -d overseas -c "GRANT ALL ON SCHEMA public TO overseas_app;"
```

## D.3 Ciclo quotidiano

```
python -m scripts.init_db              # crea le tabelle mancanti
python -m scripts.init_db --reset      # ricostruisce tutto da zero
python -m scripts.seed                 # inserisce i dati di prova
flask --app wsgi run --debug           # avvia l'applicazione
```

Generazione di una chiave segreta:

```
python -c "import secrets; print(secrets.token_hex(32))"
```

## D.4 Git nel lavoro di gruppo

```
git pull                                  # sempre, prima di iniziare
git switch -c feature/nome-attivita       # nuovo branch per ogni attività
git add -A && git commit -m "messaggio"
git push -u origin feature/nome-attivita
```

Poi si apre la pull request su GitHub. Dopo il merge:

```
git switch main && git pull
git branch -d feature/nome-attivita
```

## D.5 Verifiche prima di consegnare

- Estrarre il pacchetto in una cartella pulita e seguire **solo** le istruzioni del README, senza usare nulla che sia rimasto sulla macchina di sviluppo.
- Controllare che `.env` e la cartella `uploads/` non siano nel pacchetto.
- Controllare che `requirements.txt` contenga davvero tutto: se l'installazione in un ambiente virtuale nuovo va a buon fine e l'applicazione parte, il file è completo.

---

# APPENDICE E — Diagnosi dei problemi più comuni

Elencati per messaggio d'errore, perché è così che li incontrerete.

- **`ModuleNotFoundError: No module named 'app'`** — lo script è stato lanciato dalla cartella sbagliata. Gli script si eseguono dalla radice del progetto con `python -m scripts.init_db`, non entrando in `scripts/`.
- **`RuntimeError: Working outside of application context`** — si sta usando `db.session` fuori da una richiesta HTTP. Negli script serve il blocco `with app.app_context():`.
- **Le tabelle non vengono create, senza errori** — i modelli non sono stati importati prima di `create_all()`, quindi i metadati erano vuoti.
- **`sqlalchemy.exc.IntegrityError`** — un vincolo del database ha respinto la scrittura. Il messaggio contiene il nome del vincolo: da lì si risale alla regola violata. Non è un bug, è il database che fa il suo lavoro.
- **`AttributeError: 'AnonymousUserMixin' object has no attribute 'ruolo'`** — manca `@login_required` su una route che usa `current_user`.
- **Il login riesce ma `current_user` resta anonimo** — manca la callback `user_loader`, oppure non restituisce l'oggetto utente.
- **`psycopg.errors.InsufficientPrivilege`** — l'utente dell'applicazione non ha i privilegi sulla tabella. Corretto: significa che i `GRANT` stanno funzionando. Vanno concessi i privilegi mancanti, non usato l'utente amministratore.
- **La pagina si carica lentamente e nel terminale scorrono decine di query** — è il problema delle query a cascata. Va aggiunto `selectinload` sulle relazioni lette nel template.
- **`jinja2.exceptions.UndefinedError`** — il template usa una variabile che la route non ha passato. Il messaggio dice quale.
- **Il file caricato non si trova più** — il percorso di archiviazione è relativo e cambia con la cartella di lavoro. Va usato un percorso assoluto costruito dalla configurazione.
- **`.env` finito su GitHub** — aggiungerlo al `.gitignore` non basta, perché il file è già nella cronologia. Va rimosso dall'indice con `git rm --cached .env`, e soprattutto **vanno cambiate tutte le credenziali che conteneva**.

---

