# Guida operativa al progetto Overseas

Il codice, file per file, nell'ordine in cui viene eseguito.

---

## Come usare questa guida

Non è un manuale da leggere in fila: è una visita guidata al codice che hai
già davanti. Tieni aperti due schermi, o il portatile e il progetto in
PyCharm. Per ogni file trovi:

- **Cosa fa** — una riga
- **Il codice che conta** — l'estratto vero dal tuo file
- **Cosa devi capire** — la sola cosa che conta davvero
- **Esperimento** — rompilo di proposito, guarda cosa succede, rimettilo

Gli esperimenti sono la parte che fa la differenza. Leggere che
`selectinload` evita il problema N+1 non lascia traccia; vedere trenta
`SELECT` identiche scorrere nel terminale, sì.

**L'ordine dei file segue l'esecuzione, non la cartella.** È l'unico ordine in
cui le cose si spiegano da sole, perché ogni file usa solo quelli venuti
prima.

Le altre due guide restano utili per cose diverse:

- `Guida_Models_Da_Zero.md` — la **sintassi** Python e SQLAlchemy, se una riga
  non ti torna
- `Mappa_Del_Progetto.md` — la **visione dall'alto**, i diagrammi di flusso e
  la ricetta per aggiungere una funzionalità

Questa qui sta in mezzo: è il codice vero, spiegato.

---

## Indice

- [Parte 0 — I venti file in una pagina](#parte-0--i-venti-file-in-una-pagina)
- [Parte 1 — Come nasce l'applicazione](#parte-1--come-nasce-lapplicazione)
- [Parte 2 — Come si descrivono i dati](#parte-2--come-si-descrivono-i-dati)
- [Parte 3 — Come si serve una pagina](#parte-3--come-si-serve-una-pagina)
- [Parte 4 — Chi sei e cosa puoi fare](#parte-4--chi-sei-e-cosa-puoi-fare)
- [Parte 5 — La prima funzionalità vera](#parte-5--la-prima-funzionalità-vera)
- [Parte 6 — Il database](#parte-6--il-database)
- [Parte 7 — Il percorso completo](#parte-7--il-percorso-completo)
- [Appendice A — Gli esperimenti in fila](#appendice-a--gli-esperimenti-in-fila)
- [Appendice B — Glossario](#appendice-b--glossario)
- [Appendice C — I comandi](#appendice-c--i-comandi)

---

# Parte 0 — I venti file in una pagina

```
wsgi.py                    accende l'applicazione. 3 righe.
config.py                  indirizzo del database, chiave segreta, upload
.env                       i valori veri (NON va su GitHub)
requirements.txt           l'elenco delle librerie

app/extensions.py          crea db e login_manager VUOTI. 4 righe.
app/__init__.py            create_app(): monta tutto. IL FILE CHIAVE.

app/enums.py               le costanti: STUDENTE, APERTA, ...
app/models.py              le 11 tabelle, i 33 CHECK, gli indici

app/security.py            chi può fare cosa
app/blueprints/pubblico.py /                  la home
app/blueprints/auth.py     /auth/...          login, logout
app/blueprints/studente.py /studente/...      elenco pratiche
app/blueprints/pratiche.py /pratiche/<id>     dettaglio
app/blueprints/docente.py  /docente/...       ancora vuoto
app/blueprints/ufficio.py  /ufficio/...       ancora vuoto

app/templates/base.html            l'intelaiatura di ogni pagina
app/templates/_frammenti.html      le macro riutilizzabili
app/templates/home.html            la home
app/templates/auth/login.html      il form di accesso
app/templates/studente/elenco.html l'elenco
app/templates/pratiche/dettaglio.html  il dettaglio

scripts/init_db.py                 crea le tabelle ed esegue il file SQL
scripts/seed.py                    riempie di dati finti
scripts/schema_extra_postgres.sql  gli 8 trigger e le 4 viste
scripts/collaudo.sql               32 prove sull'integrità
```

**I tre che non riaprirai mai più:** `config.py`, `extensions.py`,
`__init__.py`. La loro complessità la paghi una volta.

**I due che aprirai ogni giorno:** i blueprint e i template.

---

# Parte 1 — Come nasce l'applicazione

Tempo: 30 minuti. È il blocco più astratto e il più importante.

## 1.1 `wsgi.py`

**Cosa fa:** accende l'applicazione.

```python
from app import create_app

app = create_app("dev")

if __name__ == "__main__":
    app.run(debug=True)
```

**Cosa devi capire:** `from app import create_app` esegue `app/__init__.py`
e ne prende la funzione. `create_app("dev")` la chiama e restituisce
l'oggetto applicazione. Tutto qui.

`if __name__ == "__main__":` significa "solo se questo file è stato lanciato
direttamente, non se è stato importato". Quando avvii con
`flask --app wsgi run`, Flask *importa* il file e chiama lui `app.run()`, per
cui quel blocco non serve — ma se un giorno fai `python wsgi.py`, funziona
lo stesso.

## 1.2 `config.py`

**Cosa fa:** raccoglie tutte le impostazioni in un posto solo.

```python
class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "chiave-di-sviluppo-da-cambiare")

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{BASE_DIR / 'overseas.db'}"
    )
    SQLALCHEMY_ECHO = os.environ.get("SQL_ECHO", "0") == "1"

    UPLOAD_FOLDER = BASE_DIR / os.environ.get("UPLOAD_FOLDER", "uploads")
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_UPLOAD_MB", 10)) * 1024 * 1024
    ALLOWED_UPLOAD_EXTENSIONS = {".pdf"}


CONFIGS = {"dev": DevConfig, "demo": DemoConfig}
```

**Cosa devi capire — tre cose.**

`os.environ.get("X", "valore di riserva")` legge una variabile d'ambiente e,
se non c'è, usa il secondo argomento. Le variabili vengono dal file `.env`,
caricato in cima con `load_dotenv`. **Il `.env` non va su GitHub**: contiene la
password del database. `.env.example` sì, perché ha i nomi senza i valori.

`SECRET_KEY` è la chiave con cui Flask **firma i cookie**. Non li cifra: li
firma, così se un utente ne modifica il contenuto la firma non torna e il
cookie viene buttato. È il motivo per cui nessuno può scrivere `id=1` nel
proprio cookie e diventare un altro utente.

`CONFIGS` è un dizionario di classi. `create_app("dev")` prende `DevConfig`,
`create_app("demo")` prende `DemoConfig`. Serve per avere impostazioni diverse
senza toccare il codice: nella demo `DEBUG = False`, così non compare la
pagina gialla di errore durante la registrazione del video.

> **Esperimento.** Nel `.env` metti `SQL_ECHO=1` e riavvia. Ora ogni query
> generata compare nel terminale. È lo strumento più utile che hai per capire
> cosa fa davvero l'ORM. Poi rimettilo a 0, perché è rumorosissimo.

## 1.3 `app/extensions.py`

**Cosa fa:** crea gli oggetti delle estensioni **vuoti**.

```python
class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "Devi accedere per visualizzare questa pagina."
```

**Cosa devi capire.** `SQLAlchemy()` viene creato **senza applicazione**: non
sa ancora a quale database parlare. Il collegamento avviene dopo, dentro
`create_app`, con `db.init_app(app)`.

Perché questa complicazione? Per rompere un anello. Il modo ingenuo sarebbe:

```python
# app/__init__.py                    # app/models.py
app = Flask(__name__)                from app import db
db = SQLAlchemy(app)
from app import models
```

`__init__.py` importa `models`, che importa `__init__.py`, che non ha ancora
finito di essere eseguito. Python si ferma con un `ImportError` poco chiaro.

Mettendo `db` in un terzo file **che non importa niente del progetto**, la
dipendenza diventa un albero:

```
        extensions.py
        ^          ^
        |          |
    models.py   __init__.py
        ^          |
        +----------+
```

`login_view = "auth.login"` è il nome della rotta a cui Flask-Login manda chi
tenta di aprire una pagina protetta senza essere entrato.

## 1.4 `app/__init__.py` — il file chiave

**Cosa fa:** assembla l'applicazione. Sette passi, in un ordine obbligato.

```python
def create_app(nome_config: str = "dev") -> Flask:
    app = Flask(__name__)
    app.config.from_object(CONFIGS.get(nome_config, Config))     # 1

    from app.extensions import db, login_manager
    db.init_app(app)                                             # 2
    login_manager.init_app(app)

    from app import models                                       # 3
    from app.models import Utente

    @login_manager.user_loader                                   # 4
    def carica_utente(id_utente: str):
        return db.session.get(Utente, int(id_utente))

    @app.before_request                                          # 5
    def dichiara_utente_al_database():
        from flask_login import current_user
        if current_user.is_authenticated:
            db.session.execute(
                sa.text("SELECT set_config('app.utente_id', :id, true)"),
                {"id": str(current_user.id)},
            )

    app.jinja_env.globals.update(StatoPratica=StatoPratica, ...)  # 6

    app.register_blueprint(pubblico_bp)                          # 7
    app.register_blueprint(auth_bp, url_prefix="/auth")
    ...

    _registra_pagine_errore(app)
    app.config["UPLOAD_FOLDER"].mkdir(parents=True, exist_ok=True)
    return app
```

**Cosa devi capire, passo per passo.**

**Passo 1 — la configurazione per prima.** `init_app` legge l'indirizzo del
database da `app.config`. Se la configurazione non è ancora caricata, non lo
trova.

**Passo 2 — `init_app` collega l'oggetto vuoto a questa applicazione.** Da qui
in poi `db.session` funziona.

**Passo 3 — l'import che sembra inutile e non lo è.**

```python
from app import models  # noqa: F401
```

Nessuno usa `models` in questo file. Serve a **eseguirlo**. Quando Python
esegue `class Utente(db.Model):`, un meccanismo dentro `db.Model` registra la
tabella in un elenco globale. `db.create_all()` legge quell'elenco.

Se questa riga manca, l'elenco resta vuoto, `init_db` crea **zero tabelle** e
non dà nessun errore. È il guasto più silenzioso di tutto il progetto.

`# noqa: F401` dice agli strumenti di controllo del codice: lo so che sembra
un import inutilizzato, lasciami stare.

**Passo 4 — la `user_loader`.** Flask-Login salva nel cookie **solo l'id**
dell'utente, firmato. A ogni richiesta legge quell'id e chiama questa funzione
per ricostruire l'oggetto dal database.

`int(id_utente)` perché l'id arriva come **stringa**: i cookie contengono solo
testo.

Ricaricare l'utente a ogni richiesta invece che tenerlo nel cookie ha un
motivo: se un utente viene disabilitato o cambia ruolo, la modifica ha effetto
subito e non alla scadenza del cookie.

**Passo 5 — dire al database chi sta agendo.** PostgreSQL non sa chi è
l'utente applicativo: la connessione è sempre la stessa. Questa riga glielo
comunica all'inizio di ogni richiesta, e i **trigger** la rileggono con
`current_setting('app.utente_id', true)` per verificare il ruolo di chi cambia
stato e per riempire lo storico.

Il terzo argomento `true` di `set_config` significa "solo per questa
transazione": non si mescola con le richieste degli altri utenti.

> **Attenzione, errore già incontrato.** Non si può scrivere
> `SET LOCAL app.utente_id = :id`. `SET LOCAL` è un comando di
> configurazione, non una query, e PostgreSQL **non accetta parametri** al suo
> interno: il driver sostituisce `:id` con un segnaposto `$1` e il parser lo
> rifiuta. `set_config()` fa la stessa cosa ma è una **funzione**, quindi i
> parametri li accetta.

**Passo 6 — le costanti nei template.** Senza questa riga, in un template non
potresti scrivere `{{ StatoPratica.ETICHETTE[pratica.stato] }}`, perché Jinja
vede solo le variabili passate a `render_template`. Registrandole come globali
diventano visibili ovunque.

**Passo 7 — i blueprint.** Ogni area del sito ha il suo prefisso. L'URL dice
già chi dovrebbe poterci accedere: tutto ciò che sta sotto `/docente/` è per i
docenti. Non è un controllo di sicurezza — quello sta nelle rotte — ma rende
la mappa dei permessi leggibile a colpo d'occhio.

**In fondo, le pagine di errore.** `_registra_pagine_errore` associa 401, 403,
404 e 500 a `errore.html`. Nota il 500:

```python
@app.errorhandler(500)
def errore_interno(_):
    db.session.rollback()
    return render_template("errore.html", codice=500, ...), 500
```

Il `rollback` è essenziale: una transazione lasciata a metà rende la sessione
inutilizzabile, e ogni query successiva fallirebbe con un errore che non
c'entra niente con la causa vera.

> **Esperimento 1.** Commenta `from app import models`, poi:
> `dropdb overseas && createdb overseas && python -m scripts.init_db`.
> Guarda quante tabelle crea. Rimettila.
>
> **Esperimento 2.** Commenta il blocco `@login_manager.user_loader` e apri
> una pagina qualsiasi. L'errore è
> `Missing user_loader or request_loader`, e compare perché `base.html` nomina
> `current_user`.

**Domanda di controllo:** perché `db` viene creato in `extensions.py` invece
che dentro `create_app`?

---

# Parte 2 — Come si descrivono i dati

Tempo: 45 minuti.

## 2.1 `app/enums.py`

**Cosa fa:** raccoglie i valori ammessi per le colonne "a scelta fissa".

```python
class Ruolo:
    STUDENTE = "STUDENTE"
    DOCENTE = "DOCENTE"
    UFFICIO = "UFFICIO"
    TUTTI = (STUDENTE, DOCENTE, UFFICIO)


class StatoPratica:
    APERTA = "APERTA"
    ...
    ETICHETTE = {APERTA: "Aperta", ...}
    COLORI = {APERTA: "secondary", ...}
```

**Cosa devi capire.** Sono classi usate come **contenitore di nomi**: nessuno
scrive mai `Ruolo()`. `utente.ruolo` è una stringa normalissima, e il
confronto è un confronto fra stringhe.

Perché non scrivere la stringa a mano ogni volta? Perché un refuso in una
stringa **non dà errore**:

```python
if utente.ruolo == "STUEDNTE":     # Python non protesta. Risponde False.
if utente.ruolo == Ruolo.STUEDNTE: # AttributeError, e PyCharm lo segna rosso
```

**L'unica disciplina che ti serve** in tutto il progetto: mai scrivere quelle
stringhe a mano. Sempre `StatoPratica.CHIUSA`, mai `"CHIUSA"`.

`ETICHETTE` e `COLORI` servono nei template: stampano `Mobilità in corso`
invece di `MOBILITA_IN_CORSO`, e danno il colore Bootstrap all'etichetta.

## 2.2 `app/models.py`

**Cosa fa:** descrive le 11 tabelle, i vincoli e gli indici.

**Non leggerlo tutto.** Leggi due classi: `Utente` e `Pratica`. Le altre nove
sono le stesse forme con nomi diversi.

### Le quattro forme di riga

Tutto il file è fatto di queste quattro, ripetute:

```python
# 1. una colonna
nome: Mapped[str] = mapped_column(sa.String(80), nullable=False)

# 2. una colonna che punta a un'altra tabella
studente_id: Mapped[int] = mapped_column(sa.ForeignKey("utente.id"))

# 3. la scorciatoia per arrivare all'oggetto puntato
studente: Mapped[Utente] = relationship(foreign_keys=[studente_id])

# 4. un vincolo, dentro __table_args__
sa.CheckConstraint("crediti > 0", name="ck_corso_interno_crediti")
```

### `Utente`: l'ereditarietà multipla

```python
class Utente(UserMixin, db.Model):
    __tablename__ = "utente"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(sa.String(120), nullable=False)
    ruolo: Mapped[str] = mapped_column(sa.String(20), nullable=False)
    matricola: Mapped[str | None] = mapped_column(sa.String(20))
```

`db.Model` la rende una tabella. `UserMixin` le aggiunge i quattro metodi che
Flask-Login pretende (`is_authenticated`, `is_active`, `is_anonymous`,
`get_id`). Due librerie che non si conoscono, i cui pezzi si incastrano perché
toccano metodi diversi.

`Mapped[str]` senza `| None` significa `NOT NULL`. `Mapped[str | None]`
ammette i NULL. È l'unica informazione che passa **solo** dall'annotazione.

**La traduzione dal concettuale, e cosa si perde.** Nel modello concettuale
c'era una generalizzazione: un padre `Utente` e tre figli. Qui è collassata in
una tabella sola, con `ruolo` come discriminatore.

Il prezzo: nel concettuale la relazione *referenza* puntava al sottotipo
`Docente`, e il vincolo era espresso dal disegno. Ora tutte le chiavi esterne
puntano a `utente` e nulla impedisce di mettere uno studente come referente.
**Da qui nasce il trigger sui ruoli** — un vincolo che non viene dal dominio
ma dalla traduzione. È la giustificazione più pulita che hai per l'uso di un
trigger, e va detta così all'orale.

**Le password:**

```python
def imposta_password(self, in_chiaro: str) -> None:
    self.password_hash = generate_password_hash(in_chiaro)

def verifica_password(self, in_chiaro: str) -> bool:
    return check_password_hash(self.password_hash, in_chiaro)
```

Nel database c'è **solo l'hash**. Non esiste modo di rileggere la password
vera, nemmeno per noi. `generate_password_hash` applica una funzione lenta e
con sale: due utenti con la stessa password ottengono hash diversi, e provarle
tutte a forza bruta costa tempo macchina.

**I `@property`:**

```python
@property
def e_studente(self) -> bool:
    return self.ruolo == "STUDENTE"
```

Si usano **senza parentesi**: `current_user.e_studente`. Non esistono nel
database, sono calcolati ogni volta. Servono a tenere i template leggibili.

### `Pratica`: quattro chiavi esterne verso la stessa tabella

```python
studente_id:      Mapped[int]        = mapped_column(sa.ForeignKey("utente.id"))
docente_id:       Mapped[int]        = mapped_column(sa.ForeignKey("utente.id"))
verificata_da_id: Mapped[int | None] = mapped_column(sa.ForeignKey("utente.id"))
chiusa_da_id:     Mapped[int | None] = mapped_column(sa.ForeignKey("utente.id"))
```

Sono le quattro relazioni del modello concettuale:

- `studente_id` → **apertura**, con `data_apertura` come suo attributo. È
  anche la titolarità: chi apre la pratica ne è il proprietario, quindi una
  relazione sola e non due.
- `docente_id` → **referenza**, senza attributi.
- `verificata_da_id` → **verifica pre-partenza**, cardinalità (0,1).
- `chiusa_da_id` → **chiusura**, (0,1).

Le ultime due, avendo massimo 1 dal lato pratica, nel modello logico **non
diventano tabelle**: collassano in colonne. Da qui nascono i vincoli "o
entrambi o nessuno", che nel concettuale non servivano:

```python
sa.CheckConstraint(
    "(verificata_da_id IS NULL) = (pre_partenza_verificata_il IS NULL)",
    name="ck_pratica_verifica_coerente",
),
```

Con quattro chiavi esterne verso `utente`, ogni `relationship` deve dire
**quale seguire**:

```python
studente: Mapped[Utente] = relationship(
    back_populates="pratiche_come_studente", foreign_keys=[studente_id]
)
```

Senza `foreign_keys`, SQLAlchemy si ferma all'avvio con
`Could not determine join condition`.

### I CHECK: tre famiglie, e la regola d'oro

**Coerenza delle relazioni collassate** — o entrambi o nessuno, già visto
sopra.

**Prerequisiti fra fatti:**

```python
sa.CheckConstraint(
    "NOT (data_inizio_effettivo IS NOT NULL)"
    " OR (pre_partenza_verificata_il IS NOT NULL)",
    name="ck_pratica_inizio_dopo_verifica",
),
```

`"se A allora B"` in SQL non esiste: si scrive `NOT A OR B`.

(Due stringhe una sotto l'altra senza virgola in mezzo si concatenano da sole:
è una comodità di Python per spezzare le righe lunghe.)

**Dallo stato ai fatti — e qui sta la regola d'oro:**

```python
sa.CheckConstraint(
    "stato NOT IN ('MOBILITA_IN_CORSO', 'IN_RICONOSCIMENTO_ESAMI', 'CHIUSA')"
    " OR data_inizio_effettivo IS NOT NULL",
    name="ck_pratica_stato_implica_inizio",
),
```

Sempre **dallo stato al fatto**, mai il contrario.

Il motivo: un CHECK viene rivalutato **a ogni modifica della riga**, non solo
quando scrivi quella colonna. Un vincolo del tipo "puoi valorizzare l'inizio
solo se lo stato è PRE_PARTENZA_COMPLETATA" si romperebbe da solo appena la
pratica passa a MOBILITA_IN_CORSO: la data sarebbe ancora lì, lo stato no, e
l'UPDATE verrebbe rifiutato.

**La regola:** un CHECK che nomina lo stato è valido solo se la condizione
resta vera anche in tutti gli stati successivi.

### Le entità deboli

`LearningAgreement`, `CorsoEsterno`, `Esame`, `Transcript` sono entità deboli:
non hanno un identificatore proprio, lo prendono dal padre.

```python
sa.UniqueConstraint("pratica_id", "numero_versione", name="uq_la_pratica_versione"),
```

Questa è la **chiave concettuale**: numero di versione *dentro* la pratica. La
chiave primaria è un `id` surrogato, scelta implementativa dettata dall'ORM —
chiavi composte propagate su tre livelli renderebbero illeggibili le
relazioni. Va dichiarato in relazione.

### L'indice unico parziale

```python
sa.Index(
    "uq_la_una_sola_in_attesa",
    "pratica_id",
    unique=True,
    postgresql_where=sa.text("esito = 'IN_ATTESA'"),
),
```

Una sola proposta pendente per pratica. `UniqueConstraint` **non ammette una
clausola WHERE**, quindi questo vincolo si può esprimere solo come indice, ed
è uno degli esempi di vincolo che richiede sintassi specifica del DBMS. Ottimo
materiale per la relazione.

### `[SQL]`

Nei commenti delle classi troverai la sigla `[SQL]` seguita dal nome di un
trigger. Significa: questo vincolo esiste, ma non qui — vive in
`scripts/schema_extra_postgres.sql`, perché l'ORM non sa esprimerlo.

> **Esperimento.** In `psql`:
> ```sql
> INSERT INTO utente (email, password_hash, nome, cognome, ruolo, matricola)
> VALUES ('x@y.it','x','A','B','DOCENTE','123');
> ```
> Leggi il nome del vincolo che ti blocca e ritrovalo in `models.py`. Questo
> è il legame fra il codice Python e il messaggio d'errore di PostgreSQL.

**Domanda di controllo:** qual è la differenza fra `pratica.studente_id` e
`pratica.studente`?

---

# Parte 3 — Come si serve una pagina

Tempo: 30 minuti.

## 3.1 `app/blueprints/pubblico.py`

**Cosa fa:** la home. È la rotta più semplice che esista.

```python
pubblico_bp = Blueprint("pubblico", __name__)


@pubblico_bp.route("/")
def home():
    try:
        db.session.execute(sa.text("SELECT 1"))
        db_ok = True
        db_messaggio = "Connessione al database attiva."
    except Exception as errore:
        db_ok = False
        db_messaggio = f"Database non raggiungibile: {errore.__class__.__name__}"

    return render_template("home.html", db_ok=db_ok, db_messaggio=db_messaggio)
```

**Cosa devi capire.**

`Blueprint("pubblico", __name__)` crea un gruppo di rotte. Il primo argomento
è il **nome**, e serve a `url_for`: `url_for('pubblico.home')` significa "la
rotta `home` del blueprint `pubblico`".

`@pubblico_bp.route("/")` registra la funzione. Il decoratore consegna la tua
funzione a Flask, che la chiamerà quando arriva una richiesta per `/`.

`render_template("home.html", db_ok=..., db_messaggio=...)` costruisce l'HTML.
Gli argomenti con nome diventano **variabili dentro il template**. Il template
vede solo queste: non ha accesso alle altre variabili della funzione.

`SELECT 1` è la query più banale che esista, e prova che la connessione si
apre davvero. Leggere la configurazione direbbe solo che c'è scritto qualcosa
nel file.

## 3.2 `app/templates/base.html`

**Cosa fa:** l'intelaiatura comune a tutte le pagine.

```jinja
<nav class="navbar ...">
  ...
  {% if current_user.is_authenticated %}
    {% if current_user.e_studente %}
      <a class="nav-link" href="{{ url_for('studente.elenco') }}">Le mie pratiche</a>
    {% endif %}
  {% endif %}
  ...
</nav>

<main>
  {% with messaggi = get_flashed_messages(with_categories=true) %}
    {% for categoria, testo in messaggi %}
      <div class="alert alert-{{ categoria }}">{{ testo }}</div>
    {% endfor %}
  {% endwith %}

  {% block contenuto %}{% endblock %}
</main>
```

**Cosa devi capire.**

`{% block contenuto %}{% endblock %}` è **il buco**. Ogni altra pagina scrive
`{% extends "base.html" %}` e riempie solo quel buco. Cambi il menu qui, e
cambia in venti pagine.

`current_user` non lo passa nessuno: lo rende disponibile Flask-Login in tutti
i template. Se non c'è nessuno collegato è un oggetto anonimo, per cui
`is_authenticated` vale `False`.

**Nascondere una voce di menu NON è un controllo di sicurezza.** Chiunque può
digitare l'URL a mano. Il controllo vero sta nella rotta, lato server. Qui si
evita solo di mostrare comandi che non riguardano l'utente.

I **messaggi flash** sono il canale unico per parlare all'utente. Nel codice:
`flash("Pratica creata.", "success")`. Le categorie usate sono quattro e
corrispondono ai nomi Bootstrap: `success`, `danger`, `warning`, `info`.

Un flash **sopravvive a un redirect** perché viene messo nella sessione, cioè
nel cookie, che viaggia con la richiesta successiva.

> **Attenzione, errore già incontrato.** I commenti Jinja `{# ... #}` **non si
> annidano**. Il primo `#}` che l'interprete incontra chiude il commento,
> anche se era dentro una frase. Da lì in poi il testo viene letto come
> codice, e l'errore che ne esce non assomiglia per niente alla causa.

## 3.3 `app/templates/home.html`

```jinja
{% extends "base.html" %}

{% block titolo %}Home{% endblock %}

{% block contenuto %}
  {% if current_user.is_authenticated %}
    <h2>Ciao {{ current_user.nome }}</h2>
    {% if current_user.e_studente %}
      <p>Da qui potrai creare le tue pratiche...</p>
    {% elif current_user.e_docente %}
      ...
    {% endif %}
  {% else %}
    <a class="btn btn-primary" href="{{ url_for('auth.login') }}">Accedi</a>
  {% endif %}
{% endblock %}
```

**Cosa devi capire.** Tre tipi di parentesi:

- `{{ ... }}` stampa un valore
- `{% ... %}` esegue un'istruzione
- `{# ... #}` è un commento

Il template **non esegue Python**: può solo leggere le variabili che la rotta
gli ha passato. È voluto, e serve a tenere la logica nelle rotte invece che
sparsa nelle pagine.

**Una pagina per concetto, non una per ruolo.** La home è una sola, con dei
`{% if %}` dentro. Fare tre pagine quasi identiche significherebbe correggere
ogni cosa tre volte, e due volte su tre dimenticarsene.

> **Esperimento.** In `base.html` cambia `Overseas` nella barra in `CIAO` e
> ricarica una pagina qualsiasi. Un file toccato, tutte le pagine cambiate: è
> il senso di `extends`.

**Domanda di controllo:** dove finisce l'HTML di `home.html` dentro
`base.html`?

---

# Parte 4 — Chi sei e cosa puoi fare

Tempo: 45 minuti. È il blocco concettualmente più denso.

## 4.1 `app/blueprints/auth.py`

**Cosa fa:** login e logout.

```python
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("pubblico.home"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        utente = db.session.scalar(
            sa.select(Utente).where(Utente.email == email)
        )

        if utente is None or not utente.verifica_password(password):
            flash("Credenziali non valide.", "danger")
            return render_template("auth/login.html", email=email)

        login_user(utente, remember=False)

        destinazione = request.args.get("next", "")
        if not destinazione or urlsplit(destinazione).netloc != "":
            destinazione = url_for("pubblico.home")

        flash(f"Bentornato, {utente.nome}.", "success")
        return redirect(destinazione)

    return render_template("auth/login.html", email="")
```

**Cosa devi capire — cinque cose.**

**Una funzione, due metodi HTTP.** `methods=["GET", "POST"]` e poi
`if request.method == "POST"`. È la convenzione di Flask e tiene vicine due
cose che parlano dello stesso form.

**`request.form.get("email", "")` invece di `request.form["email"]`.** Il
secondo esplode se il campo manca. Non ci si fida mai della forma dei dati che
arrivano dal browser.

**Un solo messaggio per due casi.** `utente is None or not
utente.verifica_password(...)` produce lo stesso `"Credenziali non valide"`.
Dire "email inesistente" permetterebbe di scoprire quali indirizzi sono
registrati provandoli uno per uno.

**`login_user(utente)`** scrive l'id nel cookie firmato. Da qui in poi
`current_user` esiste in tutta l'applicazione.

**Il controllo su `next`.** Quando `@login_required` respinge qualcuno, mette
la pagina di partenza in `?next=...`. Va usata, ma **non ci si può fidare**:
è un parametro nell'URL, quindi lo scrive chi vuole.

`urlsplit(destinazione).netloc` è il nome del sito. Se è vuoto, l'indirizzo è
interno (`/studente/pratiche`). Se è pieno, punta fuori
(`https://sito-finto.it/login`) e va scartato: altrimenti si crea un **open
redirect**, cioè un link del vostro dominio che porta a una pagina di accesso
contraffatta.

**E il `redirect` finale, che è la cosa più importante del file.**

Se rispondessi con `render_template`, l'indirizzo nel browser resterebbe
`POST /auth/login`. L'utente preme F5, il browser chiede "vuoi rimandare i
dati?", e il form viene inviato due volte. Con il redirect, l'indirizzo finale
è una GET normale e F5 non fa danni.

Si chiama **POST-redirect-GET**, ed è la regola per **ogni** form del progetto.

## 4.2 `app/templates/auth/login.html`

```jinja
<form method="post" novalidate>
  <input type="email" name="email" value="{{ email }}" required>
  <input type="password" name="password" required>
  <button type="submit">Accedi</button>
</form>
```

**Cosa devi capire.**

`method="post"` fa viaggiare i dati **nel corpo** della richiesta e non
nell'URL. Fondamentale per una password: gli URL finiscono nella cronologia
del browser e nei log del server.

Non c'è `action`: il form si invia alla stessa pagina, cioè alla stessa
funzione, che sa già distinguere GET da POST.

**`name="email"` è l'unico legame fra i due file.** È la chiave con cui la
rotta legge il valore, con `request.form.get("email")`. Se cambi il `name`,
devi cambiare anche la rotta.

`value="{{ email }}"` ripropone quello che l'utente aveva scritto dopo un
tentativo fallito. La password no: si riscrive sempre.

## 4.3 `app/security.py`

**Cosa fa:** decide chi può fare cosa. È il file più concettuale del progetto.

### La distinzione da avere chiara

**Autenticazione** = chi sei. La gestisce Flask-Login.
**Autorizzazione** = cosa puoi fare. Non la gestisce nessuno: sta qui.

### Il controllo di ruolo

```python
def ruolo_richiesto(*ruoli_ammessi: str):
    def decoratore(vista):
        @wraps(vista)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            if current_user.ruolo not in ruoli_ammessi:
                abort(403)
            return vista(*args, **kwargs)
        return wrapper
    return decoratore
```

**Tre funzioni annidate. È la cosa che confonde tutti, ed è più semplice di
come sembra.**

Ricorda cosa fa un decoratore. Questo:

```python
@login_required
def elenco(): ...
```

equivale a `elenco = login_required(elenco)`. Il decoratore è una funzione che
prende una funzione e ne restituisce un'altra.

Ma noi vogliamo scrivere `@ruolo_richiesto(Ruolo.STUDENTE)`, cioè un
decoratore **con un argomento**. E allora serve un livello in più:

```
ruolo_richiesto(Ruolo.STUDENTE)   riceve i ruoli, restituisce il decoratore
     decoratore(vista)            riceve la tua funzione, restituisce wrapper
          wrapper(...)            e' quello che Flask chiamera' davvero
```

`wrapper` controlla, e **solo se il controllo passa** chiama la tua funzione.
Se non passa, `abort(403)` interrompe tutto.

**`@wraps(vista)`** copia nome e documentazione dalla funzione originale al
wrapper. Senza, tutte le rotte si chiamerebbero `wrapper` e Flask andrebbe in
confusione: `url_for()` usa proprio quel nome per costruire gli URL.

**L'ordine dei decoratori conta:**

```python
@studente_bp.route("/pratiche")
@login_required
@ruolo_richiesto(Ruolo.STUDENTE)
def elenco(): ...
```

`login_required` va **sopra**: chi non è autenticato deve essere mandato alla
pagina di accesso, non ricevere un 403 che non gli dice cosa fare.

### Il controllo di appartenenza

```python
def puo_vedere_pratica(pratica) -> bool:
    if not current_user.is_authenticated:
        return False
    if current_user.ruolo == Ruolo.UFFICIO:
        return True
    if current_user.ruolo == Ruolo.STUDENTE:
        return pratica.studente_id == current_user.id
    if current_user.ruolo == Ruolo.DOCENTE:
        return pratica.docente_id == current_user.id
    return False


def esigi_accesso(pratica) -> None:
    if not puo_vedere_pratica(pratica):
        abort(404)
```

**Sei righe che sono l'intera politica di autorizzazione sui dati.** Sono le
tre regole del punto 1 dei requisiti funzionali: studente solo le proprie,
docente solo quelle di cui è referente, ufficio tutte.

Nessuna query: `studente_id` e `docente_id` sono colonne, sono già in memoria
insieme alla pratica.

**Perché 404 e non 403.** Un 403 direbbe "questa pratica esiste ma non è tua".
Provando gli identificatori uno per uno si scoprirebbe quante pratiche ci sono
e quali numeri sono in uso. Il 404 non distingue fra "non esiste" e "non è
tua".

Il controllo di ruolo da solo **non protegge niente**, perché tutti gli
studenti hanno lo stesso ruolo. È il controllo di appartenenza quello che
impedisce a uno studente di leggere la pratica di un altro, ed è quello che si
dimentica più spesso.

> **Esperimento 1.** In `auth.py` sostituisci il `redirect` finale con
> `render_template("home.html", db_ok=True, db_messaggio="")`. Fai login, poi
> premi F5 e guarda cosa ti chiede il browser. Poi rimetti a posto.
>
> **Esperimento 2.** Entra come studente e apri `/pratiche/2`: ricevi 404. Ora
> commenta `esigi_accesso(pratica)` in `pratiche.py` e riprova: vedi i dati di
> Giulia. **Questo è il buco che quella riga chiude.** Rimettila.

**Domanda di controllo:** perché dopo il login si fa `redirect` e non
`render_template`?

---

# Parte 5 — La prima funzionalità vera

Tempo: 40 minuti. Da qui in poi tutto il progetto è ripetizione.

## 5.1 `app/blueprints/studente.py`

```python
@studente_bp.route("/pratiche")
@login_required
@ruolo_richiesto(Ruolo.STUDENTE)
def elenco():
    pratiche = db.session.scalars(
        sa.select(Pratica)
        .where(Pratica.studente_id == current_user.id)
        .options(selectinload(Pratica.istituto), selectinload(Pratica.docente))
        .order_by(Pratica.anno_accademico.desc(), Pratica.codice_pratica)
    ).all()

    return render_template("studente/elenco.html", pratiche=pratiche)
```

**Cosa devi capire — la query pezzo per pezzo.**

`sa.select(Pratica)` costruisce una SELECT. **Non la esegue**: è solo la
descrizione.

`.where(Pratica.studente_id == current_user.id)` è il filtro di sicurezza.
Nota che confronta con `current_user`, non con un parametro dell'URL: non c'è
modo per l'utente di influenzarlo.

`db.session.scalars(...).all()` — **adesso** parte l'SQL.

**`scalar` o `scalars`:**

```
scalar()    un oggetto solo, oppure None
scalars()   molti, da consumare con .all() o con un ciclo
execute()   righe complete, quando selezioni piu' cose insieme
```

### La regola numero uno

**Il filtro sta NELLA QUERY, non nel template.**

```python
giusto:     .where(Pratica.studente_id == current_user.id)
sbagliato:  caricare tutto e nascondere le righe altrui in Jinja
```

La seconda non è un filtro: è una **falla**. I dati sono già arrivati nel
browser, basta guardare il sorgente della pagina.

### Il problema N+1

Il template scrive `pratica.istituto.nome`. Senza `selectinload`, SQLAlchemy
caricherebbe l'istituto solo in quel momento, **una volta per riga**: con 50
pratiche sarebbero 51 query invece di 2.

`selectinload` dice "già che ci sei, portami anche gli istituti": fa una
seconda query sola che li prende tutti insieme.

È l'ottimizzazione più importante del progetto e la più facile da dimenticare.

> **Esperimento.** Metti `SQL_ECHO=1` nel `.env`, togli la riga `.options(...)`
> e ricarica l'elenco. Nel terminale scorrono le SELECT ripetute. Rimettila e
> guarda la differenza. Questo è materiale per la sezione "performance" della
> relazione.

## 5.2 `app/templates/studente/elenco.html`

```jinja
{% extends "base.html" %}
{% from "_frammenti.html" import stato_pratica, periodo, data %}

{% block contenuto %}
  {% if not pratiche %}
    <p>Non hai ancora nessuna pratica di mobilità.</p>
  {% else %}
    {% for p in pratiche %}
      <a href="{{ url_for('pratiche.dettaglio', id_pratica=p.id) }}">
        {{ p.codice_pratica }}
      </a>
      {{ stato_pratica(p.stato) }}
      {{ p.istituto.nome }}
      {{ data(p.data_apertura) }}
    {% endfor %}
  {% endif %}
{% endblock %}
```

**Cosa devi capire.**

L'import delle macro va in cima, subito dopo `extends`.

Il **caso vuoto va sempre gestito**, ed è la prima cosa che vede un utente
nuovo. Una pagina bianca sembra un errore.

`url_for('pratiche.dettaglio', id_pratica=p.id)` costruisce l'indirizzo a
partire dal **nome della rotta**, non scrivendolo a mano: se domani cambi il
percorso, i link si aggiornano da soli. I parametri della rotta si passano
come argomenti con nome.

`{% for %} ... {% endfor %}`: ogni blocco aperto va chiuso esplicitamente,
perché l'indentazione nell'HTML non conta niente.

## 5.3 `app/templates/_frammenti.html`

```jinja
{% macro stato_pratica(stato) %}
  <span class="badge text-bg-{{ StatoPratica.COLORI.get(stato, 'secondary') }}">
    {{ StatoPratica.ETICHETTE.get(stato, stato) }}
  </span>
{% endmacro %}
```

**Cosa devi capire.** Una macro è una **funzione che produce HTML**. Serve per
gli elementi che compaiono in più pagine: se l'etichetta di stato appare in
cinque template e la scrivi cinque volte, cambiarla significa cambiarla cinque
volte, e dimenticarne una.

`StatoPratica` è visibile qui dentro perché è registrata in
`app.jinja_env.globals` — passo 6 di `create_app`.

`.get(stato, 'secondary')` restituisce il valore di riserva se la chiave non
c'è, invece di esplodere.

C'è anche una macro `data()` che stampa un trattino quando la data è nulla.
Serve più spesso di quanto sembri: metà delle date dello schema sono
nullabili, e senza quel controllo il template stamperebbe `None`.

## 5.4 `app/blueprints/pratiche.py`

```python
@pratiche_bp.route("/<int:id_pratica>")
def dettaglio(id_pratica: int):
    pratica = db.session.get(Pratica, id_pratica)
    if pratica is None:
        abort(404)
    esigi_accesso(pratica)
    ...
```

**Cosa devi capire — queste tre righe sono lo schema da ripetere ovunque.**

La prima carica. La seconda gestisce l'id inventato. La terza verifica che chi
chiede abbia diritto.

`<int:id_pratica>` nella rotta: la parte variabile dell'URL. `int:` fa due
cose — converte in numero e **rifiuta** ciò che numero non è. `/pratiche/ciao`
dà 404 senza nemmeno arrivare alla tua funzione.

**Perché qui non c'è `@ruolo_richiesto`.** Perché tutti e tre i ruoli possono
vedere questa pagina. Il controllo non è sul **tipo** di utente ma sul
**legame** fra quell'utente e quella pratica, ed è esattamente ciò che fa
`esigi_accesso`.

Non serve nemmeno `@login_required`: `esigi_accesso`, su un utente anonimo,
risponde comunque 404.

**Perché un blueprint suo.** La pagina serve a tutti e tre i ruoli: cambiano
solo i comandi disponibili. Metterla sotto `/studente/` costringerebbe un
docente a navigare in un indirizzo che dice il contrario di quello che sta
facendo.

## 5.5 `app/templates/pratiche/dettaglio.html`

È la pagina più lunga, ma non c'è niente di nuovo: `extends`, macro, `{% if %}`
e `{% for %}`. Tre cose da notare.

**Le tre informazioni sempre in alto:** in che stato è la pratica, chi deve
agire adesso, cosa manca per andare avanti. È il modo più semplice per rendere
l'applicazione comprensibile a chi la guarda per la prima volta, e conta molto
nel video.

**Le versioni del Learning Agreement, con quella operativa evidenziata.** È il
versionamento che diventa visibile, e la risposta alla domanda "perché avete
fatto le versioni".

**Lo storico in fondo**, scritto dal trigger e non dall'applicazione. Le righe
con utente vuoto vengono dal seed, che non dichiara nessuna identità al
database.

**Domanda di controllo:** perché in `pratiche.py` non c'è `@ruolo_richiesto`?

---

# Parte 6 — Il database

Questo blocco è delegabile a un compagno.

## 6.1 `scripts/init_db.py`

```python
def esegui_sql_extra() -> None:
    testo = FILE_SQL_EXTRA.read_text(encoding="utf-8").strip()
    with db.engine.begin() as conn:
        conn.exec_driver_sql(testo)


def main() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        esegui_sql_extra()
```

**Cosa devi capire — e questa è la cosa più importante di tutto il blocco.**

**Lo schema nasce da DUE sorgenti.** `create_all()` legge il registro dei
modelli e genera i `CREATE TABLE` con i CHECK e gli indici. Poi
`esegui_sql_extra()` applica i trigger e le viste. **La creazione del database
è completa solo quando sono state applicate entrambe.**

È il motivo per cui puoi ritrovarti con un database che sembra funzionare —
l'app parte, il login va, il seed inserisce — e non ha **nessun** trigger
installato. Nessuna schermata te lo dice.

Regola operativa: dopo ogni `dropdb`/`createdb`, **`init_db` va lanciato
sempre**, perché è lui che esegue tutti e due i pezzi.

`with app.app_context():` serve perché `db` deve sapere a quale applicazione
sta parlando, e fuori da una richiesta HTTP non c'è nessuno a dirglielo. Il
`with` è la struttura Python equivalente al RAII: apre un contesto all'inizio
del blocco e lo chiude all'uscita, anche se salta un'eccezione.

**`exec_driver_sql` e non `sa.text()`**, per due motivi scritti nel file:
`text()` interpreterebbe i `:` dell'operatore `:=` del PL/pgSQL come segnaposto
di parametri, e il driver rifiuta un file con più istruzioni se ci sono
parametri.

> **Attenzione.** `create_all()` **non modifica le tabelle esistenti**. Se
> aggiungi una colonna a un modello, non te la aggiunge e non ti avvisa.
> Durante lo sviluppo si ricrea il database.

## 6.2 `scripts/seed.py`

Si legge da solo. Una cosa da notare:

```python
def svuota() -> None:
    db.session.execute(sa.delete(Pratica))
    db.session.execute(sa.delete(CorsoInterno))
    db.session.execute(sa.delete(Istituto))
    db.session.execute(sa.delete(Utente))
```

**L'ordine conta:** dal figlio verso il padre. Cancellare prima un utente che
ha pratiche verrebbe rifiutato dalla chiave esterna (`ondelete="RESTRICT"`).

Le tabelle figlie di `pratica` non compaiono: hanno `ondelete="CASCADE"` e
spariscono da sole.

E le password, anche nei dati finti, passano da `imposta_password`: in chiaro
non entrano mai nel database.

## 6.3 `scripts/schema_extra_postgres.sql`

Otto trigger e quattro viste. Leggine due.

**`fn_verifica_ruoli_pratica`** — il più semplice:

```sql
SELECT ruolo INTO r FROM utente WHERE id = NEW.docente_id;
IF r <> 'DOCENTE' THEN
    RAISE EXCEPTION 'Il referente deve avere ruolo DOCENTE (trovato: %)', r;
END IF;
```

`NEW` è la riga che si sta inserendo o modificando. Perché non un CHECK: deve
**leggere un'altra tabella**, e un CHECK vede solo la riga corrente.

**`fn_transizione_stato`** — il più importante:

```sql
IF NEW.stato = OLD.stato THEN RETURN NEW; END IF;

SELECT count(*) INTO n FROM transizione_ammessa
 WHERE stato_da = OLD.stato AND stato_a = NEW.stato;
IF n = 0 THEN
    RAISE EXCEPTION 'Transizione non ammessa: da % a %', OLD.stato, NEW.stato;
END IF;
```

`OLD` è la riga **prima** della modifica. Perché non un CHECK: un CHECK vede
solo la versione nuova, e non saprebbe distinguere "questa riga era già
chiusa" da "questa riga sta venendo chiusa adesso".

**La macchina a stati è un DATO**, non codice: sta nella tabella
`transizione_ammessa`. Il corpo del trigger non cambia mai — per modificare il
processo si aggiunge una riga alla tabella. E la stessa tabella la può
interrogare l'interfaccia per decidere quali pulsanti mostrare, così le regole
stanno in un posto solo.

**Le viste** sono query salvate con un nome. Non contengono dati: ogni lettura
riesegue la query sottostante. Esistono perché la stessa domanda ricorre in
molti punti — per esempio `v_learning_agreement_corrente`, che dice qual è il
piano valido, e che altrimenti andrebbe riscritta in cinque rotte diverse.

## 6.4 `scripts/collaudo.sql`

Non studiarlo, **lancialo**:

```
psql overseas -f scripts/collaudo.sql
```

32 prove. Ogni riga `[ok]` è un vincolo che ha fatto il suo lavoro. Comincia
con un controllo preliminare: se i trigger non ci sono, si ferma e te lo dice,
invece di produrre trenta righe di errori a cascata.

L'esito di questo script è il contenuto della sezione "collaudo" della
relazione, e nel video sono venti secondi in cui si vede il database rifiutare
trentadue operazioni sbagliate.

---

# Parte 7 — Il percorso completo

Questa è la domanda a cui devi saper rispondere quando hai finito, ed è anche
la risposta migliore che puoi dare all'orale se ti chiedono "spiegami com'è
fatta la vostra applicazione".

> Digito `/pratiche/1` nel browser. Cosa succede?

```
 1. wsgi.py          ha gia' chiamato create_app() all'avvio.
                     L'applicazione e' in ascolto.

 2. app/__init__.py  Flask cerca fra le rotte registrate dai blueprint
                     quella che combacia con /pratiche/<int:id_pratica>.
                     La trova: pratiche.dettaglio.

 3. Flask-SQLAlchemy apre una SESSIONE per questa richiesta.
                     Non e' una connessione: e' un blocco di appunti.

 4. Flask-Login      legge il cookie firmato, ne estrae l'id, e chiama
                     la user_loader registrata al passo 4 di create_app:
                         db.session.get(Utente, int(id_utente))
                     -> SELECT * FROM utente WHERE id = 1
                     Il risultato diventa current_user.

 5. before_request   SELECT set_config('app.utente_id', '1', true)
                     Da qui in poi i trigger sanno chi sta agendo.

 6. pratiche.py      parte dettaglio(id_pratica=1):

                         pratica = db.session.get(Pratica, 1)
                     -> SELECT * FROM pratica WHERE id = 1

 7. security.py      esigi_accesso(pratica)
                     -> puo_vedere_pratica: sei lo studente titolare?
                        il docente referente? l'ufficio?
                     Se no: abort(404). Fine.

 8. pratiche.py      carica versioni e storico con selectinload
                     -> poche query invece di decine

 9. dettaglio.html   {% extends "base.html" %}
                     Jinja costruisce base.html e ci infila dentro il
                     blocco "contenuto".
                     Le macro di _frammenti.html producono le etichette.
                     url_for costruisce i collegamenti.

10. Flask            chiude la sessione, spedisce l'HTML.
```

**Sei file**, in questo ordine: `wsgi.py` → `app/__init__.py` →
`app/blueprints/pratiche.py` → `app/security.py` → `app/models.py` →
`app/templates/pratiche/dettaglio.html`.

Se sai raccontare questo percorso, hai capito il progetto. Tutto il resto sono
dettagli che si cercano quando servono.

---

# Appendice A — Gli esperimenti in fila

Fanne almeno cinque. Sono venti minuti in tutto e valgono più di due ore di
lettura.

**1. L'import che sembra inutile.** Commenta `from app import models` in
`create_app`, poi `dropdb overseas && createdb overseas && python -m
scripts.init_db`. Crea zero tabelle, senza errori.

**2. La user_loader mancante.** Commenta il blocco
`@login_manager.user_loader` e apri una pagina.
→ `Missing user_loader or request_loader`

**3. Il vincolo che ti blocca.** In `psql`, inserisci un docente con matricola.
Leggi il nome del vincolo e ritrovalo in `models.py`.

**4. `extends` in azione.** Cambia `Overseas` in `CIAO` in `base.html`.
Ricarica una pagina qualsiasi.

**5. Il doppio invio.** Sostituisci il `redirect` finale di `auth.py` con un
`render_template`. Fai login e premi F5.

**6. Il buco di sicurezza.** Entra come studente, apri `/pratiche/2` (404).
Commenta `esigi_accesso(pratica)` e riprova.

**7. Il problema N+1.** `SQL_ECHO=1` nel `.env`, togli `.options(...)` da
`studente.py`, ricarica l'elenco e guarda il terminale.

**8. La rotta che non esiste.** In `base.html` scommenta
`url_for('docente.elenco')`.
→ `BuildError: Could not build url for endpoint`

**9. Il commit dimenticato.** In una rotta, modifica un oggetto e **non**
chiamare `db.session.commit()`. Ricarica: il dato non c'è.

**Rimetti sempre tutto a posto dopo.**

---

# Appendice B — Glossario

**blueprint** — un gruppo di rotte con un prefisso comune. Si registra in
`create_app`.

**decoratore** — la chiocciola sopra una funzione. `@x` significa
`funzione = x(funzione)`.

**`current_user`** — l'utente collegato. Lo mette a disposizione Flask-Login
in rotte e template, senza passarlo.

**flash** — un messaggio che sopravvive a un redirect, perché viaggia nel
cookie di sessione.

**hash** — trasformazione a senso unico. Dalla password si ricava l'hash, dal
l'hash non si ricava la password.

**lazy loading** — SQLAlchemy carica una relazione solo quando la usi. È
comodo e causa il problema N+1.

**macro** — una funzione Jinja che produce HTML.

**metadata** — il registro delle tabelle che `db.Model` riempie e che
`create_all()` legge.

**N+1** — una query per l'elenco più una per ogni riga. Si risolve con
`selectinload`.

**`NEW` / `OLD`** — dentro un trigger, la riga dopo e prima della modifica.

**ORM** — Object-Relational Mapping. Una classe è una tabella, un oggetto è
una riga.

**POST-redirect-GET** — dopo una POST si fa sempre redirect, così F5 non
reinvia il form.

**sessione (SQLAlchemy)** — il blocco di appunti che tiene traccia degli
oggetti modificati. `commit()` traduce tutto in SQL dentro una transazione.

**sessione (Flask)** — il cookie firmato in cui vivono l'id dell'utente e i
messaggi flash. Sono due cose diverse con lo stesso nome.

**vista** — una query salvata nel database con un nome, interrogabile come una
tabella.

---

# Appendice C — I comandi

```bash
# ambiente
source .venv/bin/activate
pip install -r requirements.txt

# database da zero
dropdb overseas && createdb overseas
python -m scripts.init_db
python -m scripts.seed

# solo i trigger e le viste
psql overseas -f scripts/schema_extra_postgres.sql

# verifica
psql overseas -c "\dt"     # tabelle: 11
psql overseas -c "\dv"     # viste: 4
psql overseas -c "\dft"    # funzioni di trigger: 7
psql overseas -f scripts/collaudo.sql   # 32 prove

# avvio
flask --app wsgi run --debug
flask --app wsgi routes    # elenco delle rotte registrate

# credenziali di prova (password: overseas)
studente@stud.unive.it
studente2@stud.unive.it
docente@unive.it
docente2@unive.it
ufficio@unive.it
```

## Quando qualcosa non va

**`BuildError: Could not build url for endpoint`**
Un template chiede `url_for` di una rotta che non esiste.
→ `flask --app wsgi routes`

**`Missing user_loader or request_loader`**
Un template nomina `current_user` ma la callback non è registrata.

**`init_db` crea zero tabelle**
Manca `from app import models` in `create_app`.

**I trigger non scattano**
`schema_extra_postgres.sql` non è stato eseguito.
→ `psql overseas -c "\dft"`

**`ImportError: cannot import name 'db' from partially initialized module`**
Qualcuno importa `app/__init__.py` invece di `app/extensions.py`.

**`IntegrityError: violates check constraint`**
Hai scritto una stringa a mano con un refuso. Usa le costanti di `enums.py`.

**Il dato non arriva nel database**
Manca `db.session.commit()`.

**`TemplateRuntimeError: extended multiple times`**
Un commento Jinja si è chiuso in anticipo: dentro c'era la sequenza
cancelletto-graffa.
