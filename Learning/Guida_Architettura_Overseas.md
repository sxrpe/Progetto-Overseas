# Guida all'architettura — come tutto si tiene insieme

Progetto Overseas, Basi di Dati Mod. 2, A.A. 2025/2026.

Questa guida non spiega *cosa* fa il progetto: quello sta nella Guida
Operativa. Spiega **dove vivono le cose e come si parlano fra loro**. È il
livello che serve per smettere di copiare codice e cominciare a scriverlo.

Si legge una volta dall'inizio alla fine. Dopo, si torna alla parte che
serve.

---

## Indice

    PARTE 1   I tre significati di "globale"
    PARTE 2   Mappa completa delle variabili del progetto
    PARTE 3   Come Flask gestisce le rotte
    PARTE 4   Il ciclo di vita di una richiesta
    PARTE 5   Le estensioni e init_app
    PARTE 6   Flask-Login dal cookie all'oggetto
    PARTE 7   SQLAlchemy: la sessione e la connessione
    PARTE 8   Jinja: come un template trova le sue variabili
    PARTE 9   Due percorsi completi, dall'inizio alla fine
    PARTE 10  Diagnostica: cosa dice ogni errore
    APPENDICE Glossario dei nomi che si somigliano

---

# PARTE 1 — I tre significati di "globale"

Nel progetto ci sono tre categorie di cose che sembrano variabili globali.
Funzionano in modo completamente diverso e confonderle è il motivo per cui
all'inizio sembra tutto magia.

## 1.1 Il globale dei moduli

Non c'entra niente con Flask. È il sistema di import di Python.

Una cartella con dentro un `__init__.py` è un **package**. I file dentro
sono **moduli**, e si raggiungono col punto:

    app/                       package "app"
      __init__.py              modulo  "app"
      extensions.py            modulo  "app.extensions"
      models.py                modulo  "app.models"
      enums.py                 modulo  "app.enums"
      security.py              modulo  "app.security"
      blueprints/
        __init__.py            package "app.blueprints"
        studente.py            modulo  "app.blueprints.studente"

`app.models` è **un percorso di file col punto al posto dello slash**.
Niente di più. È l'equivalente di `#include "app/models.h"`.

È una coincidenza infelice che la cartella si chiami `app` e che anche
l'oggetto Flask si chiami `app`. **Non si toccano.** Se rinominassi la
cartella in `overseas/`, scriveresti `from overseas.models import Utente` e
l'oggetto Flask resterebbe identico.

### La regola che rende tutto prevedibile

Un modulo viene **eseguito una volta sola**, alla prima importazione. Da
quel momento resta in memoria in un dizionario interno di Python
(`sys.modules`), e ogni import successivo restituisce lo stesso identico
oggetto.

Questa è la base di `extensions.py`:

```python
# app/extensions.py
db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()
```

Queste due righe girano **una volta in tutto il programma**. `db` e
`login_manager` sono due oggetti soli, e chiunque scriva

```python
from app.extensions import db
```

riceve quello stesso oggetto, non una copia. È il motivo per cui una
sessione aperta in `pubblico.py` e una aperta in `studente.py` sono la
stessa sessione.

### Perché extensions.py esiste come file separato

Per rompere un cerchio:

    models.py     ha bisogno di   db
    db            sta in          __init__.py
    __init__.py   importa         models.py     <-- cerchio

Con un terzo file che non importa nessuno dei due, il cerchio si spezza:

    extensions.py  non importa niente del progetto
    models.py      importa   extensions
    __init__.py    importa   extensions  e  models

Questo è anche il motivo per cui dentro `create_app` l'import delle
estensioni sta **dentro la funzione** e non in cima al file: importarlo
fuori ricrea il cerchio.

## 1.2 L'oggetto `app` e i suoi registri

`app = Flask(__name__)` costruisce un oggetto che dentro ha una serie di
**dizionari e liste vuote**. Tutto il lavoro di `create_app` consiste nel
riempirli.

```
app  (istanza di Flask)
│
├── import_name          "app"          <- il __name__ che hai passato
├── root_path            /.../overseas/app
│                                       <- dedotto dall'import_name
├── template_folder      "templates"    <- relativo a root_path
├── static_folder        "static"
│
├── config               dizionario     <- app.config.from_object(Config)
│                                          SECRET_KEY, SQLALCHEMY_DATABASE_URI,
│                                          UPLOAD_FOLDER, ...
│
├── url_map              Map di Werkzeug
│   └── Rule("/pratiche/<int:id_pratica>", endpoint="pratiche.dettaglio")
│                                       <- register_blueprint
│
├── view_functions       dizionario
│   └── "pratiche.dettaglio" -> la funzione Python
│                                       <- register_blueprint
│
├── error_handler_spec   dizionario annidato
│   └── 404 -> non_trovato              <- @app.errorhandler(404)
│
├── before_request_funcs lista
│   └── dichiara_utente_al_database     <- @app.before_request
│
├── after_request_funcs  lista
│   └── (Flask-Login ce ne mette una per rinnovare il cookie)
│
├── teardown_appcontext_funcs  lista
│   └── (Flask-SQLAlchemy ce ne mette una per chiudere la sessione)
│
├── jinja_env            Environment di Jinja  <- creato DA SOLO da Flask
│   ├── loader           sa che i template stanno in app/templates/
│   ├── filters          i filtri predefiniti + quelli di Flask
│   └── globals          url_for, get_flashed_messages, config, request, ...
│       └── StatoPratica, Ruolo, ...  <- app.jinja_env.globals.update(...)
│
├── extensions           dizionario
│   └── "sqlalchemy" -> l'oggetto db  <- db.init_app(app)
│
└── login_manager        l'oggetto login_manager
                                        <- login_manager.init_app(app)
```

Tre osservazioni che rispondono a domande frequenti.

**`render_template` funziona senza che tu abbia configurato niente** perché
`jinja_env` lo crea Flask da solo dentro `Flask(__name__)`. Il `__name__`
che passi è il modulo `app`; Flask ne ricava la cartella su disco
(`root_path`), e da lì cerca `templates/` e `static/`. Tutto qui.

**I decoratori che "registrano" mettono roba in questi dizionari.** Non
avvolgono la funzione, non la chiamano: la infilano in un registro e la
restituiscono identica. Sarà il framework a guardarci dentro più tardi.

**Questi registri si riempiono all'avvio e poi non cambiano più.** Sono
uguali per tutte le richieste di tutti gli utenti.

## 1.3 I proxy di contesto

`request`, `session`, `g`, `current_user`, `current_app`.

Queste sono la parte strana. Le importi come se fossero variabili globali:

```python
from flask import request, session, g, current_app
from flask_login import current_user
```

ma **non contengono niente**. Sono dei rimandi, tecnicamente dei
`LocalProxy` di Werkzeug. Quando scrivi `request.form["email"]`, l'oggetto
`request` va a chiedere "qual è la richiesta in corso *in questo thread, in
questo istante*" e gira la domanda a quella.

### Perché non sono variabili globali vere

Il server gestisce più richieste contemporaneamente. Se `request` fosse una
vera variabile globale condivisa, due utenti che aprono una pagina nello
stesso momento si scambierebbero i dati fra loro. Con il proxy, ogni thread
vede la propria richiesta e nessun altro.

### I due contesti, e cosa vive in ciascuno

Flask ne apre due, uno dentro l'altro:

    CONTESTO DI APPLICAZIONE  (application context)
        current_app     l'oggetto Flask in uso
        g               un blocco per appunti, azzerato a ogni richiesta
        db.session      la sessione di SQLAlchemy e' legata a QUESTO

    CONTESTO DI RICHIESTA     (request context)
        request         metodo, URL, form, query string, file caricati
        session         il dizionario salvato nel cookie firmato
        current_user    fornito da Flask-Login, poggia su session

Il contesto di applicazione può esistere **da solo**, senza una richiesta:
è quello che apri a mano in `scripts/seed.py` e `scripts/init_db.py` con

```python
app = create_app()
with app.app_context():
    db.session.add(...)
```

Senza quel `with`, la prima riga che tocca `db.session` esplode con
`RuntimeError: Working outside of application context`. È il modo di Flask
per dire: non so a quale applicazione ti riferisci, quindi non so nemmeno
quale database aprire.

Il contesto di richiesta invece non esiste mai da solo: quando arriva una
richiesta HTTP, Flask apre prima quello di applicazione e poi quello di
richiesta.

### La regola per orientarsi

Quando non sai da dove arriva una cosa, chiediti a quale dei tre globali
appartiene:

    lo importi da un file tuo          -> oggetto creato una volta
    (from app.extensions import db)       in un modulo, esiste sempre

    lo prendi da app                   -> registro dell'applicazione,
    (app.config, app.jinja_env)           riempito all'avvio in create_app

    lo importi da flask e cambia       -> proxy di contesto, vale solo
    da utente a utente                    dentro una richiesta,
    (request, current_user)               fuori esplode

---

# PARTE 2 — Mappa completa delle variabili del progetto

Per ogni file: cosa nasce, quando, quante volte, chi lo vede.

## config.py

```python
class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", ...)
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", ...)
    UPLOAD_FOLDER = ...

CONFIGS = {"dev": DevConfig, "test": TestConfig, ...}
```

Nasce quando qualcuno importa `config`. Sono classi con soli attributi:
nessuna istanza viene mai creata, `from_object` legge gli attributi
direttamente dalla classe.

Chi lo vede: solo `create_app`. Da lì in poi i valori vivono dentro
`app.config` e si leggono con `current_app.config["..."]`.

`SECRET_KEY` arriva da `.env` e **non deve finire su GitHub**: è la chiave
con cui vengono firmati i cookie di sessione. Chi la conosce può fabbricare
un cookie che dice "sono l'utente numero 1".

## app/extensions.py

```python
class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()
login_manager.login_view = "auth.login"
```

Nasce alla prima importazione, una volta sola. Tre oggetti, condivisi da
tutto il progetto.

`Base` è la classe da cui SQLAlchemy 2.0 vuole che discendano tutti i
modelli: è lei a tenere il registro dei metadati (l'elenco delle tabelle
che poi `create_all` userà).

`login_manager.login_view = "auth.login"` è il nome dell'endpoint a cui
mandare chi non è autenticato. È una **stringa**, non una funzione: quando
serve, Flask-Login la passa a `url_for`. Ecco perché se sbagli quel nome
l'errore compare solo al primo redirect e non all'avvio.

## app/enums.py

```python
class StatoPratica:
    APERTA = "APERTA"
    ...
    TUTTI = (...)
    ETICHETTE = {...}
    COLORI = {...}
```

Classi usate come contenitori di costanti. Non si istanziano mai: si scrive
`StatoPratica.APERTA`, mai `StatoPratica()`.

Chi le vede: i modelli (nei CHECK), le rotte (nei confronti), e i template
— ma solo perché in `create_app` vengono registrate esplicitamente:

```python
app.jinja_env.globals.update(StatoPratica=StatoPratica, ...)
```

Senza quella riga, in un template `{{ StatoPratica.APERTA }}` darebbe
stringa vuota, perché Jinja vede solo quello che gli passi.

## app/models.py

Dieci classi che ereditano da `db.Model`.

Il momento in cui vengono **eseguite** è importante: SQLAlchemy conosce
solo le classi che sono state effettivamente definite. Se `create_app` non
contenesse

```python
from app import models  # noqa: F401
```

il registro dei metadati resterebbe vuoto e `db.create_all()` creerebbe
zero tabelle **senza dare nessun errore**. È la trappola numero uno del
pattern factory.

Ogni classe è due cose insieme:

    una descrizione di tabella   -> serve a create_all e ai CHECK
    una classe Python normale    -> istanze, metodi, @property

I metodi (`imposta_password`, `verifica_password`) e le `@property`
(`e_studente`, `nome_completo`) esistono **solo in Python**: nel database
non c'è traccia, vengono calcolati ogni volta.

## app/__init__.py

```python
def create_app(nome_config="dev") -> Flask:
    app = Flask(__name__)
    ...
    return app
```

`app` è una **variabile locale della funzione**. Non è globale, non è
importabile. Chi ne ha bisogno o se la fa passare come parametro, o usa il
proxy `current_app`.

Questo è il punto centrale del pattern factory: non esiste un oggetto
applicazione globale, ne esiste uno per ogni chiamata a `create_app`.

## wsgi.py

```python
from app import create_app
app = create_app()
```

**Qui** l'applicazione diventa una variabile di modulo, e questa è l'unica
che il server web e il comando `flask` vanno a cercare. Il comando

    flask --app wsgi routes

significa: importa il modulo `wsgi`, cercaci dentro una variabile chiamata
`app`, e usala.

## app/blueprints/*.py

```python
pubblico_bp = Blueprint("pubblico", __name__)
studente_bp = Blueprint("studente", __name__, url_prefix="/studente")
```

Un blueprint è un **raccoglitore di rotte non ancora registrate**. Nasce
all'importazione del file, e a quel punto non sa niente dell'applicazione:
tiene solo una lista di operazioni da eseguire più tardi.

Il primo argomento (`"pubblico"`) è il nome che finisce nei nomi degli
endpoint: `pubblico.home`. Il `__name__` serve, come per l'app, a trovare
la cartella dei template.

## app/security.py

```python
def ruolo_richiesto(*ruoli_ammessi): ...
def esigi_accesso(pratica): ...
def puo_vedere_pratica(pratica): ...
```

Funzioni pure, nessuno stato. Leggono `current_user`, che è un proxy,
quindi funzionano solo dentro una richiesta.

---

# PARTE 3 — Come Flask gestisce le rotte

## 3.1 I due dizionari

Tutto il sistema di routing sta in due strutture dentro `app`:

    url_map          l'indirizzo  ->  il NOME dell'endpoint
    view_functions   il NOME dell'endpoint  ->  la funzione Python

Il passaggio intermedio attraverso un nome sembra un giro inutile ma è
quello che rende possibile `url_for`: si può percorrere la mappa nei due
sensi.

## 3.2 Cosa succede quando scrivi @route

```python
@pratiche_bp.route("/<int:id_pratica>")
def dettaglio(id_pratica: int):
    ...
```

All'importazione del file, il decoratore **non registra niente
nell'applicazione**, perché il blueprint non sa ancora a quale applicazione
apparterrà. Aggiunge una voce a una lista interna del blueprint, che
significa: "quando verrai registrato da qualche parte, aggiungi questa
regola".

Il nome dell'endpoint, se non lo specifichi, è il nome della funzione:
`dettaglio`.

## 3.3 Cosa succede a register_blueprint

```python
app.register_blueprint(pratiche_bp)   # url_prefix="/pratiche" gia' nel Blueprint
```

Ora Flask esegue tutte le operazioni rimandate. Per ciascuna rotta:

    prende la regola          "/<int:id_pratica>"
    ci antepone il prefisso   "/pratiche/<int:id_pratica>"
    prende il nome funzione   "dettaglio"
    ci antepone il blueprint  "pratiche.dettaglio"

    aggiunge a url_map:        Rule("/pratiche/<int:id_pratica>",
                                    endpoint="pratiche.dettaglio",
                                    methods={"GET", "HEAD", "OPTIONS"})
    aggiunge a view_functions: "pratiche.dettaglio" -> funzione dettaglio

**Il punto nel nome dell'endpoint è quello che separa il blueprint dalla
funzione.** Per questo `url_for("pratiche.dettaglio", ...)` e non
`url_for("dettaglio")`.

Ed è per questo che due blueprint diversi possono avere entrambi una
funzione `elenco()` senza scontrarsi: diventano `studente.elenco` e
`ufficio.elenco`.

## 3.4 Perché serve @wraps nei decoratori

Il nome dell'endpoint viene preso da `funzione.__name__`. Un decoratore
scritto così:

```python
def ruolo_richiesto(*ruoli):
    def decoratore(vista):
        def wrapper(*args, **kwargs):
            ...
        return wrapper
    return decoratore
```

restituisce una funzione che si chiama `wrapper`. Se la applichi a tre
rotte diverse, Flask prova a registrare tre volte l'endpoint `wrapper` e
salta fuori un errore all'avvio.

```python
from functools import wraps

def decoratore(vista):
    @wraps(vista)          # <-- copia __name__, __doc__ e il resto
    def wrapper(*args, **kwargs):
        ...
    return wrapper
```

`@wraps` copia i metadati dell'originale sul wrapper, così `__name__` resta
`dettaglio` e tutto funziona. Non è un dettaglio estetico: senza, il
progetto non parte.

## 3.5 I convertitori

    /pratiche/<int:id_pratica>

`int:` è un **convertitore**. Fa due cose insieme:

    filtra    "/pratiche/abc"  non corrisponde a questa regola  -> 404
    converte  "/pratiche/7"    passa  id_pratica=7  come intero, non "7"

Gli altri utili: `string` (predefinito, un segmento senza slash), `float`,
`path` (accetta anche gli slash), `uuid`.

È la prima linea di difesa: un id che non è un numero non arriva mai al
tuo codice, e quindi non arriva mai al database.

## 3.6 I metodi HTTP

```python
@studente_bp.route("/pratiche/nuova", methods=["GET", "POST"])
def crea():
    if request.method == "POST":
        ...   # elabora il modulo inviato
    return render_template("studente/crea.html")
```

Se non scrivi `methods`, Flask assume `["GET"]`. Un POST su una rotta solo
GET riceve `405 Method Not Allowed` — arriva dal routing, prima ancora che
la tua funzione venga chiamata.

Lo schema GET+POST nella stessa funzione è quello che usiamo in `login()` e
useremo in tutti i moduli: una funzione sola che mostra il modulo vuoto e
ne riceve l'invio, così il modulo e la sua validazione stanno nello stesso
posto.

## 3.7 url_for, cioè la mappa letta al contrario

```python
url_for("pratiche.dettaglio", id_pratica=7)     ->  "/pratiche/7"
url_for("studente.elenco")                      ->  "/studente/pratiche"
url_for("static", filename="css/stile.css")     ->  "/static/css/stile.css"
```

I parametri che corrispondono a segmenti della regola vanno al loro posto;
quelli in più diventano query string:

```python
url_for("auth.login", next="/studente/pratiche")
    ->  "/auth/login?next=%2Fstudente%2Fpratiche"
```

**Usa sempre `url_for`, mai indirizzi scritti a mano.** Se domani cambi
`url_prefix="/studente"` in `"/mobilita"`, con `url_for` non tocchi niente;
con gli indirizzi a mano hai venti link rotti da cercare.

Quando l'endpoint non esiste ottieni:

    werkzeug.routing.exceptions.BuildError:
    Could not build url for endpoint 'auth.login'

che significa quasi sempre una di tre cose: il blueprint non è registrato,
il file è ancora uno stub senza quella rotta, oppure hai sbagliato a
scrivere il nome. Si verifica in tre secondi:

    flask --app wsgi routes

Se in quell'elenco l'endpoint non compare, non esiste.

---

# PARTE 4 — Il ciclo di vita di una richiesta

Questa è la sequenza completa. È la parte da rileggere quando non capisci
"chi chiama cosa".

```
Il browser chiede:   GET /pratiche/7      con il cookie di sessione

 1. Il server WSGI passa la richiesta all'oggetto app.

 2. Flask apre il CONTESTO DI APPLICAZIONE.
       Da qui funzionano:  current_app,  g,  db.session

 3. Flask apre il CONTESTO DI RICHIESTA.
       Da qui funzionano:  request,  session,  current_user
       Il cookie viene letto e verificato con la SECRET_KEY:
       se la firma non torna, il cookie viene buttato via del tutto.

 4. ROUTING.  Flask confronta "/pratiche/7" con url_map.
       trova   ->  endpoint "pratiche.dettaglio",  id_pratica=7
       non trova ->  solleva NotFound  ->  salta al punto 9
       trova l'indirizzo ma non il metodo -> MethodNotAllowed (405)

 5. BEFORE_REQUEST.  Esegue in ordine tutte le funzioni della lista.
       Qui gira  dichiara_utente_al_database().
       Nominando  current_user  fa scattare Flask-Login, che legge l'id
       dal cookie e chiama  carica_utente(id)  ->  una SELECT sul database.

       Se una before_request restituisce qualcosa di diverso da None,
       quella diventa la risposta e la rotta NON viene mai eseguita.
       (E' cosi' che si scrive una manutenzione programmata.)

 6. DISPATCH.  Prende  view_functions["pratiche.dettaglio"]
       ed esegue la catena dei decoratori dall'esterno verso l'interno:

           @login_required          autenticato?  no -> redirect al login
             @ruolo_richiesto(...)  ruolo giusto? no -> abort(403)
               dettaglio(id_pratica=7)   il tuo codice

 7. Il corpo della rotta gira.  Tre esiti possibili:
       return render_template(...)   ->  vai al punto 8
       abort(404)                    ->  solleva NotFound, vai al 9
       eccezione qualsiasi           ->  vai al 9

 8. AFTER_REQUEST.  Esegue le funzioni della lista, ognuna riceve la
       risposta e puo' modificarla.  Flask-Login qui rinnova il cookie.
       Se qualcosa nella sessione e' cambiato, il cookie viene rifirmato
       e riscritto nell'intestazione Set-Cookie.
       Poi la risposta parte.  Salta al punto 10.

 9. GESTIONE DELL'ERRORE.

       e' una HTTPException?  (NotFound, Forbidden, Unauthorized, ...)
           SI  -> cerca in  error_handler_spec  il gestore per quel codice
                  trova  non_trovato()  e la chiama, passandole l'oggetto
                  eccezione (quel  "_"  che ignori)
                  la risposta e' quella che ritorna il gestore

           NO  -> scrive il traceback completo nel log del server
                  (in debug mode mostra anche la pagina interattiva)
                  trasforma tutto in InternalServerError
                  chiama il gestore del 500  ->  errore_interno()
                  che fa  db.session.rollback()

       Poi passa comunque dal punto 8 (after_request).

10. TEARDOWN.  Flask chiude i due contesti.
       Il gancio di Flask-SQLAlchemy chiude  db.session  e restituisce
       la connessione al pool.
       g  viene buttato via.
```

## Cosa risponde questo alle tue domande

**Le funzioni degli errori chi le chiama.** Flask, al punto 9, andando a
pescare nel dizionario che il decoratore ha riempito all'avvio. Non le
chiami mai tu, e nessuna rotta le nomina. È lo stesso schema di `@app.route`:
registri in un dizionario, il framework ci guarda dentro quando serve.

**Perché il 500 fa rollback.** Se un'eccezione arriva a metà di una
transazione, la sessione di SQLAlchemy resta in stato di errore. Senza il
rollback, ogni query successiva **nella stessa richiesta** fallirebbe con un
messaggio che non c'entra niente con il problema vero, e passeresti mezz'ora
a inseguire il sintomo sbagliato.

**Perché `_registra_pagine_errore` è una funzione a parte.** Solo per non
lasciare ottanta righe dentro `create_app`. La chiami tu, esegue i quattro
decoratori, riempie il registro, torna. Il trattino basso davanti al nome è
la convenzione Python per "roba interna a questo file".

---

# PARTE 5 — Le estensioni e init_app

## 5.1 Perché due passaggi

```python
# app/extensions.py    -- il pezzo nasce, non sa a chi appartiene
db = SQLAlchemy(model_class=Base)

# app/__init__.py      -- il pezzo viene collegato a QUESTA applicazione
db.init_app(app)
```

Se `SQLAlchemy(app)` prendesse subito l'applicazione, `db` dovrebbe
esistere dopo `app`, e i modelli — che hanno bisogno di `db` — non
potrebbero essere importati prima. Si tornerebbe al cerchio.

Con i due passaggi lo stesso `db` può servire più applicazioni: quella di
sviluppo e quella dei test, con database diversi.

## 5.2 Cosa fa init_app davvero

Va in due direzioni, ed è il punto che ti mancava.

**L'estensione si registra dentro l'app**, così chiunque abbia `app` la
ritrova:

```python
app.extensions["sqlalchemy"] = db     # per db
app.login_manager = login_manager     # per login_manager
```

**L'estensione aggancia i propri ganci ai registri dell'app.** Non è l'app
che va a cercare l'estensione: è l'estensione che si infila nelle liste che
l'app scorrerà.

Per `db.init_app(app)`:

    legge   app.config["SQLALCHEMY_DATABASE_URI"]
    crea    il motore e il pool di connessioni
    aggiunge a  teardown_appcontext_funcs  una funzione che chiude la
            sessione a fine richiesta

Per `login_manager.init_app(app)`:

    imposta  app.login_manager = self
    aggiunge a  after_request_funcs  una funzione che rinnova il cookie
    installa il meccanismo per cui, la prima volta che qualcuno nomina
            current_user durante una richiesta, viene letto il cookie e
            chiamata la tua user_loader

Quindi la tua intuizione era giusta nella sostanza — "colleghiamo il login
manager all'oggetto applicazione" — ma il verso è l'opposto: è il login
manager che si aggancia ai registri dell'app, non l'app che se lo accolla.

## 5.3 Perché l'ordine in create_app non è negoziabile

```python
app = Flask(__name__)
app.config.from_object(...)     # 1. init_app legge da qui
db.init_app(app)                # 2.
login_manager.init_app(app)     #
from app import models          # 3. altrimenti create_all crea 0 tabelle
@login_manager.user_loader      # 4. serve prima che un template
def carica_utente(...): ...     #    nomini current_user
app.jinja_env.globals.update()  # 5.
app.register_blueprint(...)     # 6.
_registra_pagine_errore(app)    # 7.
```

Ogni passo dipende dai precedenti. In particolare: senza il punto 3 il
database si crea vuoto in silenzio, senza il punto 4 il primo template che
nomina `current_user` solleva un'eccezione.

---

# PARTE 6 — Flask-Login dal cookie all'oggetto

## 6.1 Cosa c'è davvero nel cookie

Solo l'id, e nient'altro. Quando in `auth.py` fai:

```python
login_user(utente, remember=False)
```

Flask-Login scrive nel dizionario `session`:

    session["_user_id"]  =  "5"
    session["_fresh"]    =  True
    session["_id"]       =  un'impronta del browser

`session` è un dizionario che Flask serializza, **firma con la SECRET_KEY**
e manda al browser come cookie.

Attenzione a una parola: **firmato, non cifrato**. L'utente può leggere il
contenuto del proprio cookie (è codificato, non protetto), ma non può
modificarlo senza invalidare la firma. Regola pratica: nel cookie non ci va
mai niente di segreto, solo cose che l'utente può già sapere di sé.

## 6.2 La catena completa a ogni richiesta

```
cookie firmato
    │  Flask verifica la firma con SECRET_KEY
    ▼
session = {"_user_id": "5", ...}
    │  Flask-Login legge la chiave "_user_id"
    ▼
id_utente = "5"                  <- stringa: nei cookie c'e' solo testo
    │  chiama la funzione registrata con @login_manager.user_loader
    ▼
carica_utente("5")
    │  return db.session.get(Utente, int(5))     <- una SELECT
    ▼
oggetto Utente completo
    │  Flask-Login lo appoggia nel contesto della richiesta
    ▼
current_user       ora ha ruolo, email, matricola, tutti i metodi
```

## 6.3 Le conseguenze, che sono la parte importante

**Ogni richiesta rilegge l'utente dal database.** Costa una SELECT su
chiave primaria, che è la query più veloce che esista.

**Se aggiungi una colonna al modello, la vedi subito** in `current_user`,
senza rifare il login: perché l'oggetto viene ricostruito ogni volta.

**Se cambi il ruolo di un utente nel database, il cambiamento vale già
alla richiesta successiva.** Se il ruolo stesse nel cookie, l'utente
continuerebbe ad avere il vecchio ruolo fino alla scadenza — e il cookie sta
sul suo computer, non sul tuo server. È una differenza di sicurezza, non di
comodità.

**Se `carica_utente` restituisce `None`** (utente cancellato), Flask-Login
tratta la richiesta come anonima. Nessun errore, semplicemente non sei più
collegato.

## 6.4 current_user quando non c'è nessuno

Non è `None`: è un oggetto `AnonymousUserMixin`, per il quale
`is_authenticated` vale `False` e `is_anonymous` vale `True`.

Questo è il motivo per cui nei template puoi scrivere sempre

```jinja
{% if current_user.is_authenticated %}
```

senza dover prima controllare che esista. Ed è il motivo per cui in
`security.py` il controllo su un utente anonimo non esplode ma produce
tranquillamente un 404.

## 6.5 @login_required, e perché va SOPRA @ruolo_richiesto

```python
@studente_bp.route("/pratiche")
@login_required
@ruolo_richiesto(Ruolo.STUDENTE)
def elenco():
    ...
```

I decoratori si applicano dal basso verso l'alto, ma si **eseguono**
dall'alto verso il basso. Quindi `login_required` vede la richiesta per
primo.

Se non sei autenticato: `login_required` ti manda alla pagina di login con
`?next=/studente/pratiche`, così dopo l'accesso torni dove volevi andare.

Se fossero invertiti, un utente non collegato riceverebbe un 403 "non hai i
permessi", che è vero ma inutile: non gli dice che deve collegarsi.

## 6.6 UserMixin

```python
class Utente(UserMixin, db.Model):
```

Flask-Login pretende che l'oggetto utente abbia quattro cose:
`is_authenticated`, `is_active`, `is_anonymous`, `get_id()`. `UserMixin` le
fornisce già fatte, con l'implementazione ovvia.

Due librerie che non si conoscono fra loro (`flask_login` e `sqlalchemy`)
si combinano senza attriti perché toccano metodi diversi. In C++ sarebbe
ereditarietà multipla; qui il primo nella lista ha la precedenza in caso di
conflitto, ma qui conflitti non ce ne sono.

---

# PARTE 7 — SQLAlchemy: la sessione e la connessione

## 7.1 Cos'è db.session

Non è una connessione al database. È un **quaderno degli appunti**:

    tiene traccia degli oggetti che hai caricato
    tiene traccia delle modifiche che hai fatto
    al momento giusto le traduce in INSERT / UPDATE / DELETE

Il modello si chiama *unit of work*: accumuli le modifiche in memoria, e al
`commit()` partono tutte insieme in una transazione.

```python
pratica = Pratica(codice_pratica="OV-001", ...)
db.session.add(pratica)      # niente e' ancora andato al database
db.session.commit()          # ORA parte l'INSERT, e la transazione chiude
```

## 7.2 Una sessione per richiesta

`db.session` non è un oggetto solo: è legato al **contesto di
applicazione**. Ogni richiesta ha il suo contesto, quindi ogni richiesta ha
la sua sessione, e due utenti simultanei non si vedono le modifiche a metà.

A fine richiesta il gancio di teardown che `db.init_app(app)` ha registrato
chiude la sessione e restituisce la connessione al pool.

## 7.3 Il pool di connessioni, e perché conta per i trigger

Aprire una connessione a PostgreSQL costa. SQLAlchemy ne tiene aperte un
certo numero e le presta a chi serve.

**Conseguenza importante**: la connessione che serve la tua richiesta era
già stata usata da qualcun altro un attimo prima, e sarà usata da qualcun
altro un attimo dopo.

È esattamente il motivo per cui in `create_app` la propagazione
dell'identità al database deve essere legata alla **transazione**, non alla
connessione:

```python
@app.before_request
def dichiara_utente_al_database():
    if current_user.is_authenticated:
        db.session.execute(
            sa.text("SELECT set_config('app.utente_id', :id, true)"),
            {"id": str(current_user.id)},
        )
```

Il terzo argomento `true` significa *is_local*: il valore sparisce alla fine
della transazione. Se fosse `false`, resterebbe attaccato alla connessione,
e la richiesta successiva di un altro utente si troverebbe l'identità del
precedente. Sarebbe una falla di sicurezza vera.

Due dettagli su quella riga:

**Perché `set_config` e non `SET LOCAL`.** `SET LOCAL` è un comando di
configurazione, non una query, e non accetta parametri: `SET LOCAL x = :id`
fallisce con `syntax error at or near "$1"`. `set_config()` è una funzione
SQL normale e i parametri li prende.

**Perché non concatenare l'id nella stringa.** Perché sarebbe SQL injection.
Il parametro `:id` viene passato separatamente al driver, che lo tratta come
dato e mai come codice.

Dal lato PostgreSQL i trigger rileggono il valore con:

```sql
current_setting('app.utente_id', true)
```

Il `true` lì significa "non lanciare un errore se non è stato impostato":
torna NULL. Serve perché `scripts/seed.py` scrive nel database senza passare
da una richiesta HTTP, quindi senza nessuna identità impostata.

## 7.4 select, scalars, scalar, get

```python
db.session.get(Pratica, 7)        # per chiave primaria, un oggetto o None
                                  # controlla prima in memoria: puo' non
                                  # fare nessuna query

db.session.scalar(               # UNA riga, o None
    sa.select(Utente).where(Utente.email == email)
)

db.session.scalars(              # MOLTE righe
    sa.select(Pratica).where(Pratica.studente_id == current_user.id)
).all()
```

"Scalar" qui significa: dammi il primo elemento di ogni riga, cioè
l'oggetto, invece di una tupla con dentro un oggetto solo.

## 7.5 Il problema N+1 e selectinload

Se scrivi un elenco di pratiche e nel template stampi
`pratica.istituto.nome`, SQLAlchemy va a prendere l'istituto **al momento in
cui lo nomini**. Con venti pratiche fai una query per l'elenco più venti per
gli istituti: ventuno viaggi al database per una pagina sola.

```python
db.session.scalars(
    sa.select(Pratica)
    .where(Pratica.studente_id == current_user.id)
    .options(selectinload(Pratica.istituto), selectinload(Pratica.docente))
).all()
```

`selectinload` dice: caricali subito, tutti insieme, con una query
aggiuntiva sola. Tre query invece di ventuno.

E `selectinload(A).selectinload(B)` segue la catena di un livello in più:
"caricami i corsi di ogni versione del piano, e per ogni corso anche le sue
equivalenze".

## 7.6 Dove finiscono i vincoli del database

Un `CheckConstraint` violato non è un errore Python: è un errore che arriva
dal database, al momento del `commit()` o del `flush()`. Diventa una
`sqlalchemy.exc.IntegrityError`, che se non la catturi arriva al gestore del
500.

Lo stesso vale per le eccezioni sollevate dai trigger con
`RAISE EXCEPTION`: il messaggio che hai scritto in PL/pgSQL arriva fino in
Python dentro l'eccezione.

Quando implementerai le azioni sulle pratiche, il modo giusto è:

```python
try:
    db.session.commit()
except sa.exc.IntegrityError as errore:
    db.session.rollback()
    flash("Operazione non consentita nello stato attuale.", "danger")
```

Il `rollback()` è obbligatorio: senza, la sessione resta inutilizzabile.

---

# PARTE 8 — Jinja: come un template trova le sue variabili

## 8.1 Le quattro sorgenti

Dentro un template, un nome può arrivare da quattro posti diversi:

**Quello che passi a `render_template`** — visibile solo in quella pagina:

```python
return render_template("pratiche/dettaglio.html",
                       pratica=pratica, versioni=versioni)
```

**I globali di Jinja registrati in `create_app`** — visibili ovunque:

```python
app.jinja_env.globals.update(StatoPratica=StatoPratica, Ruolo=Ruolo, ...)
```

**I globali che Flask registra da solo** — `url_for`,
`get_flashed_messages`, `config`, `request`, `session`, `g`.

**Quelli aggiunti da un'estensione** — Flask-Login registra `current_user`.

## 8.2 Il silenzio di Jinja

Un nome che non esiste **non dà errore**: produce stringa vuota. È comodo e
pericoloso insieme. Se una pagina non mostra qualcosa e non c'è nessun
errore, il sospetto numero uno è un nome sbagliato.

## 8.3 L'ereditarietà: extends e block

`base.html` ha tre buchi:

```jinja
<title>{% block titolo %}Overseas{% endblock %} · Mobilità Overseas</title>
...
{% block contenuto %}{% endblock %}
...
{% block script %}{% endblock %}
```

Una pagina figlia li riempie **per nome**:

```jinja
{% extends "base.html" %}

{% block titolo %}Le mie pratiche{% endblock %}

{% block contenuto %}
  ...
{% endblock %}
```

Regole:

    l'ordine in cui li scrivi nel figlio non conta
    un blocco che non riempi conserva il contenuto scritto nel padre
    un nome che nel padre non esiste viene ignorato in silenzio
    tutto cio' che nel figlio sta FUORI dai blocchi viene buttato via
    {{ super() }} stampa il contenuto che il padre aveva nel blocco

Il buco `script` sta in fondo per un motivo tecnico: il browser legge la
pagina dall'alto in basso, e uno script in cima verrebbe eseguito quando gli
elementi che deve manipolare non esistono ancora.

## 8.4 Le macro

`_frammenti.html` contiene funzioni riutilizzabili:

```jinja
{% macro stato_pratica(stato) %}
  <span class="badge text-bg-{{ StatoPratica.COLORI[stato] }}">
    {{ StatoPratica.ETICHETTE[stato] }}
  </span>
{% endmacro %}
```

e si portano dentro con:

```jinja
{% from "_frammenti.html" import stato_pratica, data %}
```

`extends` serve per la struttura che **avvolge** la pagina; `import` di
macro per i pezzetti che si **ripetono dentro**. Sono due meccanismi
diversi e si usano insieme.

## 8.5 L'escape automatico

In un file `.html`, Jinja passa tutto quello che stampa attraverso una
funzione che trasforma `<` in `&lt;`, `>` in `&gt;` e così via.

Se uno studente scrive nelle note

    <script>alert(document.cookie)</script>

quello che finisce nella pagina è testo visibile, non codice eseguito.
Senza questa protezione avresti una vulnerabilità XSS: chiunque potrebbe
far girare codice nel browser di chi apre la sua pratica.

Il filtro `|safe` disattiva la protezione. **Non usarlo mai su dati che
vengono dagli utenti.**

---

# PARTE 9 — Due percorsi completi

Le parti precedenti descrivono i pezzi. Qui si vedono in fila.

## 9.1 Dal database al pixel: aprire /pratiche/7

```
 1. Browser:   GET /pratiche/7   +  Cookie: session=eyJfdXNlcl9pZCI6...

 2. Flask apre i due contesti.
       Verifica la firma del cookie con SECRET_KEY  ->  ok
       session = {"_user_id": "5", "_fresh": true, ...}

 3. url_map:  "/pratiche/7"  ->  ("pratiche.dettaglio", {"id_pratica": 7})
       il convertitore  int:  ha gia' trasformato "7" in 7

 4. before_request:  dichiara_utente_al_database()
       nomina current_user  ->  Flask-Login legge "_user_id" = "5"
                            ->  carica_utente("5")
                            ->  SELECT * FROM utente WHERE id = 5
                            ->  oggetto Utente(ruolo="STUDENTE")
       poi:  SELECT set_config('app.utente_id', '5', true)
             ora PostgreSQL sa chi sta agendo, per questa transazione

 5. view_functions["pratiche.dettaglio"]  ->  la funzione dettaglio

 6. Nel corpo:
       db.session.get(Pratica, 7)          SELECT sulla pratica
       esigi_accesso(pratica)              legge current_user.ruolo
                                           studente -> pratica.studente_id
                                           deve essere 5, altrimenti 404
       db.session.scalars(...)             le versioni del piano,
                                           con selectinload per i corsi,
                                           gli esami e le equivalenze

 7. render_template("pratiche/dettaglio.html", pratica=..., versioni=...)
       Jinja carica dettaglio.html
       vede  {% extends "base.html" %}  e carica anche quello
       vede  {% from "_frammenti.html" import ... %}  e carica anche quello
       riempie i blocchi
       risolve i nomi:  pratica     ->  passato a render_template
                        StatoPratica ->  jinja_env.globals
                        url_for      ->  globale di Flask
                        current_user ->  globale di Flask-Login
       stampa tutto passando dall'escape automatico

 8. after_request:  Flask-Login rinnova il cookie se serve

 9. La pagina HTML parte verso il browser.

10. teardown:  db.session chiusa, connessione restituita al pool,
       il valore  app.utente_id  sparisce con la transazione.
```

## 9.2 Dal modulo al trigger: inviare il Learning Agreement

```
 1. Browser:   POST /studente/pratiche/7/invia-la
                    corpo del modulo + token CSRF se lo aggiungerete

 2-5. come sopra: contesti, routing, before_request, dispatch.
       Qui pero' i decoratori sono tre:
           @login_required        sei collegato?
           @ruolo_richiesto(STUDENTE)   sei uno studente?
           poi nel corpo: esigi_modifica(pratica)   e' TUA?

 6. Il corpo legge  request.form  e modifica gli oggetti:
       pratica.stato = StatoPratica.ATTESA_APPROVAZIONE_LA
       Ancora niente e' andato al database: solo appunti nella sessione.

 7. db.session.commit()
       SQLAlchemy traduce gli appunti in UPDATE e apre la transazione.
       PostgreSQL, PRIMA di scrivere, verifica in quest'ordine:

           i CHECK della riga        ck_pratica_stato_implica_verifica, ...
           i vincoli di unicita'     uq_la_una_sola_in_attesa, ...
           le chiavi esterne
           i TRIGGER                 trg_transizione_stato:
                                       legge OLD.stato e NEW.stato
                                       cerca la coppia in transizione_ammessa
                                       legge current_setting('app.utente_id')
                                       ricava il ruolo di chi agisce
                                       controlla le precondizioni sui dati
                                       se qualcosa non va: RAISE EXCEPTION

 8a. Tutto ok  ->  COMMIT.  redirect alla pagina di dettaglio.
       Lo schema e' POST-REDIRECT-GET: dopo un POST si risponde SEMPRE
       con un redirect, cosi' se l'utente ricarica la pagina non reinvia
       il modulo una seconda volta.
       Il messaggio per l'utente viaggia con  flash(), che lo mette nella
       sessione e quindi sopravvive al redirect.

 8b. Un trigger ha sollevato un'eccezione
       ->  psycopg la propaga, SQLAlchemy la avvolge in IntegrityError
       ->  se la catturi:   rollback + flash + torni al modulo
       ->  se non la catturi: arriva al gestore del 500, che fa il
           rollback e mostra la pagina di errore
```

Il punto da portare a casa: **le regole di dominio sono controllate dal
database, non dall'applicazione.** L'applicazione le anticipa per
mostrare messaggi decenti e nascondere i pulsanti inutili, ma se qualcuno
manda una richiesta a mano, o se un domani un altro programma scrive nello
stesso database, i vincoli valgono lo stesso.

È la giustificazione di tutto il lavoro su CHECK, indici parziali e trigger,
e va detta così nella relazione.

---

# PARTE 10 — Diagnostica: cosa dice ogni errore

Ogni errore tipico punta a uno dei tre globali. Sapere quale accorcia la
diagnosi da mezz'ora a un minuto.

## Errori del globale n.1 (i moduli)

    ImportError: cannot import name 'db' from partially initialized module

Import circolare. Qualcuno importa in cima al file una cosa che va importata
dentro la funzione.

    SyntaxError: from __future__ imports must occur at the beginning

`from __future__ import annotations` deve essere la prima istruzione dopo
la docstring. Se hai incollato del testo sopra, spostalo dentro la
docstring.

    ModuleNotFoundError: No module named 'app'

Stai lanciando lo script dalla cartella sbagliata, oppure manca un
`__init__.py`.

## Errori del globale n.2 (i registri dell'app)

    BuildError: Could not build url for endpoint 'auth.login'

L'endpoint non è in `view_functions`. Verifica con
`flask --app wsgi routes`: se non compare, il blueprint non è registrato o
la rotta non esiste ancora.

    View function mapping is overwriting an existing endpoint function

Due rotte con lo stesso nome di endpoint. Quasi sempre è un decoratore
senza `@wraps`, che le fa chiamare tutte `wrapper`.

    TemplateNotFound: pratiche/dettaglio.html

Il file non è dove Flask lo cerca. La cartella è `app/templates/`, e il
percorso che scrivi è relativo a quella.

    create_all() non crea nessuna tabella, senza errori

Manca `from app import models` in `create_app`.

## Errori del globale n.3 (i contesti)

    RuntimeError: Working outside of application context

Stai usando `db.session` o `current_app` fuori da una richiesta. Negli
script serve `with app.app_context():`.

    RuntimeError: Working outside of request context

Stai usando `request` o `current_user` fuori da una richiesta. Se succede
dentro una rotta, probabilmente è in un thread o in un callback.

    Missing user_loader or request_loader

Manca `@login_manager.user_loader`, oppure è definita dopo il primo uso di
`current_user`.

## Errori che vengono dal database

    IntegrityError: violates check constraint "ck_pratica_..."

Un CHECK ha fatto il suo lavoro. Il nome del vincolo ti dice esattamente
quale regola hai violato: è il motivo per cui tutti i vincoli hanno un nome
parlante.

    IntegrityError: duplicate key value violates unique constraint

Un UNIQUE. Se il nome è `uq_la_una_sola_in_attesa`, stai creando una
seconda versione del piano mentre una è ancora in attesa.

    InternalError_ / RaiseException: transizione non ammessa ...

Un trigger. Il messaggio è quello che hai scritto tu in PL/pgSQL.

    syntax error at or near "$1"

Stai passando parametri a un comando che non li accetta (`SET LOCAL`,
`CREATE ...`). Usa una funzione SQL, come `set_config()`.

    OperationalError

Il database non risponde: non è avviato, o l'indirizzo in `.env` è
sbagliato.

---

# APPENDICE — Glossario dei nomi che si somigliano

**`app` cartella** e **`app` oggetto Flask** — la prima è un package
Python, il secondo è l'applicazione. `from app.models import X` usa la
prima. `app.config` usa il secondo. Non si toccano.

**`__name__` di modulo** e **`__name__` di classe** — in
`Flask(__name__)` e `Blueprint("pubblico", __name__)` è il nome del modulo,
che serve a trovare la cartella dei template. In
`errore.__class__.__name__` è il nome della classe dell'eccezione, cioè una
stringa tipo `"OperationalError"`. Stesso nome, meccanismi diversi.

**`session` di Flask** e **`db.session` di SQLAlchemy** — la prima è il
dizionario nel cookie del browser. La seconda è la sessione di lavoro con il
database. Non hanno niente in comune tranne la parola.

**decoratori che avvolgono** e **decoratori che registrano** — i primi
sostituiscono la funzione con una versione che fa dei controlli prima
(`@login_required`, `@ruolo_richiesto`); i secondi la infilano in un
dizionario e la restituiscono identica (`@app.route`,
`@app.errorhandler`, `@login_manager.user_loader`, `@app.before_request`).
I primi girano a ogni richiesta, i secondi una volta sola all'avvio.

**endpoint** e **URL** — l'endpoint è il nome interno
(`pratiche.dettaglio`), l'URL è l'indirizzo (`/pratiche/7`). `url_for`
converte dal primo al secondo; il routing converte dal secondo al primo.

**colonna** e **relationship** — nei modelli, `studente_id` è la colonna
vera che esiste nel database; `studente` è la scorciatoia dell'ORM per
arrivare all'oggetto. Nel `CREATE TABLE` c'è solo la prima.

**autenticazione** e **autorizzazione** — chi sei (Flask-Login) contro
cosa puoi fare (`security.py`). Sono due controlli distinti e servono
entrambi.

**`abort(404)`** e **`return`** — `abort` solleva un'eccezione, quindi
tutto il codice che sta dopo non viene eseguito. `return` restituisce una
risposta normalmente. Per questo `abort` funziona anche dentro una funzione
chiamata da un'altra.

---

## Le cinque frasi da ricordare

1. `app.models` è un percorso di file, non un pezzo dell'oggetto Flask.

2. L'oggetto `app` è un contenitore di dizionari che `create_app` riempie
   all'avvio; i decoratori "che registrano" ci mettono roba dentro, e il
   framework ci guarda dentro quando serve.

3. `request`, `session`, `current_user`, `g` esistono solo dentro una
   richiesta: sono proxy, non variabili.

4. Nel cookie c'è solo l'id; l'utente viene riletto dal database a ogni
   richiesta.

5. Le regole di dominio le fa rispettare il database, non l'applicazione.
   L'applicazione le anticipa per essere gentile con l'utente.
