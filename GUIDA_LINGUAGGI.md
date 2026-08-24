# Guida rapida ai linguaggi del progetto

### Python, Flask, Jinja2, SQLAlchemy — per chi arriva dal C++

Questa guida presuppone che tu sappia già programmare e che conosca la programmazione a oggetti. Quindi **non** spiega cosa sia una variabile, un ciclo o una classe: spiega **come si scrivono in Python** e quali differenze rispetto al C++ ti faranno perdere tempo se non le sai.

È un manuale di consultazione, non un libro da leggere tutto d'un fiato. Leggi il capitolo 1 una volta (venti minuti), poi torna sugli altri quando ti servono.

---

## Indice

1. Python per chi viene dal C++
2. Le trappole che ti faranno perdere un'ora
3. Flask: dalle richieste alle risposte
4. Jinja2: scrivere le pagine
5. SQLAlchemy: parlare al database
6. Flask-Login e i controlli di accesso
7. Ricettario: i venti pezzi di codice che scriverai davvero
8. Come si legge un errore

---

# 1. Python per chi viene dal C++

## 1.1 Le cinque differenze strutturali

**L'indentazione è sintassi.** Non ci sono le graffe. Il blocco è definito dai quattro spazi. Se sbagli l'indentazione, cambi il significato del programma o ottieni un errore. PyCharm lo gestisce da solo, ma sappilo.

```python
if voto >= 18:
    print("promosso")
    registra(voto)          # dentro l'if
print("fine")               # fuori dall'if
```

I due punti alla fine della riga aprono un blocco. Vanno sempre: dopo `if`, `for`, `while`, `def`, `class`, `try`, `with`.

**Non si dichiara il tipo.** Una variabile nasce quando le assegni un valore.

```python
n = 10                # int
nome = "Marco"        # str
attivo = True         # bool
niente = None         # nullptr
```

Le annotazioni di tipo esistono e nel progetto le usiamo, ma sono **documentazione**, non controlli: Python non le verifica a runtime.

```python
def somma(a: int, b: int) -> int:
    return a + b
```

**Non esiste `new`, non esiste `delete`, non esistono i puntatori.** Ogni variabile è un riferimento a un oggetto, e la memoria è gestita automaticamente. Quindi:

```python
a = [1, 2, 3]
b = a           # NON è una copia: a e b sono lo stesso oggetto
b.append(4)
print(a)        # [1, 2, 3, 4]

c = a.copy()    # questa è una copia
```

Per un programmatore C++ questa è la differenza che morde di più: **l'assegnamento non copia mai.**

**Non esiste l'overloading di funzioni.** Se definisci due funzioni con lo stesso nome, la seconda sostituisce la prima. Al suo posto si usano gli argomenti con valore di default e gli argomenti nominati.

```python
def crea_pratica(anno, periodo="primo_semestre", note=None):
    ...

crea_pratica("2025/26")
crea_pratica("2025/26", note="urgente")           # salto periodo, nomino note
crea_pratica(anno="2025/26", periodo="intero_anno")
```

Gli argomenti nominati li userai continuamente: `render_template("pagina.html", pratiche=pratiche)` è esattamente questo.

**Non ci sono file header.** Un file `.py` è un modulo, e si importa direttamente.

```python
from app.models import Pratica, Utente     # importa due nomi da un modulo
from app.extensions import db
import sqlalchemy as sa                    # importa un modulo con un alias
```

Il punto separa le cartelle: `app.blueprints.studente` è il file `app/blueprints/studente.py`. Perché una cartella sia importabile deve contenere un file `__init__.py`, anche vuoto: è il motivo per cui `app/blueprints/__init__.py` esiste nello scaffold.

## 1.2 I quattro contenitori

Sono quello che in C++ sono `vector`, `map`, `set` e le tuple.

```python
# LISTA — come std::vector. Ordinata, modificabile.
esami = ["CT0371", "CT0372"]
esami.append("CT0373")
esami[0]                      # primo
esami[-1]                     # ultimo (indice negativo = dalla fine)
esami[1:3]                    # sottolista dagli indici 1 a 2
len(esami)                    # dimensione
"CT0371" in esami             # True

# DIZIONARIO — come std::map. Coppie chiave/valore.
voti = {"CT0371": 28, "CT0372": 30}
voti["CT0373"] = 25           # inserisce o sovrascrive
voti["CT0371"]                # 28, ma solleva un errore se manca
voti.get("CT9999")            # None invece dell'errore
voti.get("CT9999", 0)         # 0 come valore di ripiego
for codice, voto in voti.items():
    print(codice, voto)

# INSIEME — come std::set. Senza duplicati, senza ordine.
paesi = {"Giappone", "Canada"}
paesi.add("Cina")

# TUPLA — sequenza immutabile. Utile per restituire più valori.
def dimensioni():
    return 1920, 1080          # restituisce una tupla
larghezza, altezza = dimensioni()   # scompattamento
```

## 1.3 Stringhe

```python
nome = "Marco"
cognome = 'Rossi'                     # apici singoli o doppi, uguale

# f-string: il modo per comporre stringhe. Usalo sempre.
messaggio = f"{cognome} {nome} ha {len(esami)} esami"

# testo su più righe
sql = """
SELECT *
FROM pratica
"""

nome.upper()          # "MARCO"
nome.lower()
"  spazi  ".strip()   # toglie gli spazi ai lati: fondamentale sugli input
"a,b,c".split(",")    # ["a", "b", "c"]
", ".join(esami)      # "CT0371, CT0372"
nome.startswith("Ma") # True
```

Le stringhe sono immutabili: `nome[0] = "P"` è un errore.

## 1.4 Cicli e condizioni

```python
for esame in esami:                  # itera sugli elementi, non sugli indici
    print(esame)

for i, esame in enumerate(esami):    # se ti serve anche l'indice
    print(i, esame)

for i in range(5):                   # 0, 1, 2, 3, 4
    ...

while condizione:
    ...
    break        # esce
    continue     # salta al prossimo giro

if voto >= 30:
    esito = "ottimo"
elif voto >= 18:                     # "else if"
    esito = "sufficiente"
else:
    esito = "insufficiente"

# operatore condizionale: come  cond ? a : b
esito = "ok" if voto >= 18 else "no"

# operatori logici a parole
if voto >= 18 and not respinto or forzato:
    ...
```

## 1.5 Verità e falsità

Questa è comoda e va conosciuta, perché la userai ovunque. Sono considerati falsi: `False`, `None`, `0`, la stringa vuota, la lista vuota, il dizionario vuoto.

```python
if not pratiche:                 # "se la lista è vuota"
    ...

if utente:                       # "se utente non è None"
    ...

nome = richiesta.get("nome") or "anonimo"    # ripiego se vuoto o None
```

## 1.6 Comprehension

Sono la scorciatoia per costruire una lista da un'altra. Le vedrai spesso e conviene saperle leggere.

```python
# invece di:
codici = []
for e in esami:
    codici.append(e.codice_estero)

# si scrive:
codici = [e.codice_estero for e in esami]

# con filtro:
approvati = [e for e in esami if e.esito == Esito.APPROVATO]

# somma diretta:
totale = sum(e.cfu_estero for e in esami)
```

## 1.7 Classi

```python
class Studente:
    # variabile di classe, condivisa da tutte le istanze (come static)
    ateneo = "Ca' Foscari"

    def __init__(self, nome, matricola):    # il costruttore
        self.nome = nome                     # attributi di istanza
        self.matricola = matricola

    def saluta(self):                        # self = this, ma ESPLICITO
        return f"Ciao {self.nome}"

    @property                                # si legge come un attributo
    def etichetta(self):
        return f"{self.nome} ({self.matricola})"

    def __repr__(self):                      # come stamparlo in debug
        return f"<Studente {self.matricola}>"


s = Studente("Marco", "890123")     # niente "new"
print(s.saluta())
print(s.etichetta)                  # senza parentesi: è una property
```

Cinque cose da sapere:

- **`self` va scritto** come primo parametro di ogni metodo. Non è implicito come `this`.
- **Non esiste `private`.** La convenzione è che un nome che inizia con `_` è interno e non va toccato da fuori. È una convenzione, non un vincolo.
- **Non esistono i distruttori** nel senso del C++. Per liberare risorse si usa `with` (sezione 1.9).
- **L'ereditarietà** si scrive `class Studente(Persona):`, e più basi si separano con la virgola: `class Utente(UserMixin, db.Model):`.
- **`__init__`, `__repr__`** e simili si chiamano *metodi speciali*: Python li invoca da solo nei momenti giusti.

## 1.8 Eccezioni

Concettualmente identiche al C++, sintassi diversa.

```python
try:
    voto = int(richiesta["voto"])
except ValueError:
    voto = None                      # conversione fallita
except (KeyError, TypeError) as e:   # più tipi insieme, e cattura l'oggetto
    print(f"errore: {e}")
    raise                            # rilancia la stessa eccezione
finally:
    ...                              # eseguito comunque

raise ValueError("voto non valido")  # solleva
```

Nel progetto ne incontrerai principalmente tre: `ValueError` (conversione fallita), `KeyError` (chiave assente in un dizionario), `IntegrityError` (il database ha respinto una scrittura).

## 1.9 `with` — l'equivalente del RAII

Se in C++ sei abituato a distruttori che chiudono file e connessioni, `with` è quello che ti manca: garantisce che la risorsa venga chiusa all'uscita dal blocco, anche in caso di eccezione.

```python
with open("file.txt") as f:
    contenuto = f.read()
# qui il file è già chiuso, comunque sia andata

with engine.begin() as conn:
    conn.execute(...)
# qui la transazione ha fatto commit, o rollback se c'è stata un'eccezione
```

## 1.10 Decoratori — il concetto chiave per Flask

Un decoratore è **una funzione che avvolge un'altra funzione** aggiungendole un comportamento. La sintassi con la chiocciola è solo zucchero:

```python
@login_required
def dettaglio():
    ...

# significa esattamente:
def dettaglio():
    ...
dettaglio = login_required(dettaglio)
```

Ti serve saperlo per tre motivi.

**Primo:** `@app.route("/pratiche")` non è una parola chiave del linguaggio. È una normale funzione che riceve la tua funzione e la registra in una tabella interna di Flask, associandola a un indirizzo.

**Secondo: l'ordine conta.** I decoratori si applicano dal basso verso l'alto, quindi il più esterno è quello scritto per primo. In questo progetto la route sta sempre in cima, e i controlli sotto:

```python
@studente_bp.route("/pratiche")     # 1. l'indirizzo
@login_required                      # 2. sei entrato?
@ruolo_richiesto(Ruolo.STUDENTE)     # 3. sei uno studente?
def elenco_pratiche():
    ...
```

**Terzo:** `@ruolo_richiesto(Ruolo.STUDENTE)` ha le parentesi e `@login_required` no. La differenza è che il primo è una *fabbrica di decoratori*: lo chiami con un argomento e ti restituisce il decoratore vero. Ti basta saperlo per non sbagliare a copiarlo.

---

# 2. Le trappole che ti faranno perdere un'ora

Sono specifiche di chi arriva dal C++. Leggile adesso, così quando succede le riconosci.

**La divisione `/` restituisce sempre un decimale.**

```python
10 / 3      # 3.3333333333333335
10 // 3     # 3      divisione intera
10 % 3      # 1      resto
```

**Non esiste `++`.** Si scrive `i += 1`.

**`==` confronta il valore, `is` confronta l'identità.** Sugli oggetti usa `==`. `is` si usa solo con `None` e con i membri di un `Enum`:

```python
if utente is None: ...
if pratica.stato is StatoPratica.CHIUSA: ...     # funziona: gli Enum sono singleton
if nome == "Marco": ...                          # sulle stringhe SEMPRE ==
```

**Gli argomenti di default mutabili sono un tranello.** Il valore di default è creato **una volta sola**, alla definizione della funzione, e condiviso fra tutte le chiamate.

```python
def sbagliato(elementi=[]):     # MAI fare così
    elementi.append(1)
    return elementi

def giusto(elementi=None):
    if elementi is None:
        elementi = []
    ...
```

**Le variabili non hanno scope di blocco.** Una variabile definita dentro un `if` o un `for` esiste anche dopo. Sopravvive per tutta la funzione.

**Modificare una lista mentre la si scorre** produce risultati imprevedibili. Se devi, itera su una copia: `for x in lista.copy():`.

**Il confronto fra tipi diversi non converte.** `"5" == 5` è `False`. I dati che arrivano da un form sono **sempre stringhe**: `request.form["voto"]` è `"28"`, non `28`. Vanno convertiti a mano.

**L'importazione circolare.** Se il modulo A importa B e B importa A, Python fallisce. È il motivo per cui nello scaffold `db` sta in `extensions.py` e i modelli vengono importati *dentro* `create_app()` e non in cima al file.

---
# 3. Flask: dalle richieste alle risposte

## 3.1 Una route

```python
from flask import Blueprint, render_template

studente_bp = Blueprint("studente", __name__)

@studente_bp.route("/pratiche")
def elenco_pratiche():
    return render_template("studente/elenco.html")
```

Il nome della funzione (`elenco_pratiche`) più il nome del blueprint (`studente`) formano l'**endpoint**: `studente.elenco_pratiche`. È il nome con cui costruirai i link.

## 3.2 Parametri nell'indirizzo

```python
@pratiche_bp.route("/pratiche/<int:pratica_id>")
def dettaglio(pratica_id: int):        # il nome DEVE combaciare
    ...
```

`<int:...>` converte già a intero e rifiuta con un 404 chi scrive testo. Esistono anche `<string:...>` (il default) e `<float:...>`.

## 3.3 GET e POST nella stessa funzione

```python
from flask import request

@studente_bp.route("/pratiche/nuova", methods=["GET", "POST"])
def nuova_pratica():
    if request.method == "POST":
        # ... elabora l'invio
        return redirect(url_for("studente.elenco_pratiche"))
    # GET: mostra il modulo vuoto
    return render_template("studente/nuova.html")
```

Senza `methods` la route accetta solo GET, e un invio di form risponde "405 Method Not Allowed".

## 3.4 Leggere i dati in arrivo

```python
request.form["anno"]              # campo di un form; errore se manca
request.form.get("note", "")      # con valore di ripiego: preferisci questo
request.form.get("id", type=int)  # convertito, None se non convertibile

request.args.get("stato")         # querystring:  /pratiche?stato=chiusa
request.files["documento"]        # file caricato
request.method                    # "GET" o "POST"
```

**Tutto ciò che arriva è una stringa** e non è affidabile. Va convertito e validato.

## 3.5 Le quattro cose che una route può restituire

```python
return render_template("pagina.html", pratiche=pratiche, totale=12)
return redirect(url_for("studente.elenco_pratiche"))
return redirect(url_for("pratiche.dettaglio", pratica_id=7))
abort(404)                                  # interrompe subito
return render_template("pagina.html"), 400  # con un codice HTTP diverso
```

`render_template` prende il nome del file dentro `app/templates/` e poi quanti argomenti nominati vuoi: ognuno diventa una variabile utilizzabile nel template.

`url_for` costruisce l'indirizzo **a partire dall'endpoint**, non scrivendolo a mano. Se un giorno cambi il percorso nella route, tutti i link si aggiornano da soli. Scrivere `"/pratiche/7"` a mano è l'errore che ti si ritorce contro fra una settimana.

## 3.6 Messaggi all'utente

```python
from flask import flash

flash("Pratica creata.", "success")
flash("Controlla i campi.", "error")
flash("Attenzione: mancano gli esami.", "warning")
return redirect(url_for("pratiche.dettaglio", pratica_id=p.id))
```

Il messaggio sopravvive al redirect e viene mostrato nella pagina successiva. Il template base li stampa già tutti: tu devi solo chiamare `flash`. Le tre categorie usate nel progetto sono `success`, `warning`, `error`.

## 3.7 Perché dopo un POST ci vuole sempre un redirect

Se dopo un POST restituisci direttamente una pagina, quando l'utente preme F5 il browser **rimanda lo stesso POST** e l'operazione viene eseguita due volte: due pratiche identiche, due approvazioni.

Con il redirect, il refresh ricarica una pagina di sola lettura, innocua. Regola senza eccezioni: **POST che modifica → `redirect`**.

---

# 4. Jinja2: scrivere le pagine

## 4.1 Le tre sintassi

```text
{{ variabile }}     stampa un valore
{% if %} {% for %}  esegue un'istruzione
{# commento #}      non compare nell'HTML prodotto
```

## 4.2 Ereditarietà

Il file base definisce i buchi, gli altri li riempiono.

```html
<!-- base.html -->
<body>
  {% block contenuto %}{% endblock %}
</body>
```

```html
<!-- studente/elenco.html -->
{% extends "base.html" %}
{% block contenuto %}
  <h1>Le mie pratiche</h1>
{% endblock %}
```

`{% extends %}` deve essere la **prima riga** del file.

## 4.3 Cicli e condizioni

```html
{% for p in pratiche %}
  <p>{{ p.anno_accademico }} — {{ p.istituto.nome }}</p>
{% else %}
  <p>Nessuna pratica.</p>        <!-- eseguito se la lista è vuota -->
{% endfor %}

{% if pratica.stato.value == 'chiusa' %}
  <span>Chiusa</span>
{% elif modificabile %}
  <a href="...">Modifica</a>
{% endif %}

{{ loop.index }}      <!-- dentro un for: numero della riga, da 1 -->
```

Nota che nei template si naviga fra oggetti con il punto, esattamente come in Python: `p.istituto.nome` funziona, e la join la fa l'ORM.

## 4.4 Filtri

Trasformano un valore prima di stamparlo. Si concatenano con la barra verticale.

```html
{{ nome | upper }}
{{ stato.value | replace('_', ' ') }}
{{ note | default('nessuna nota') }}
{{ esami | length }}
{{ elenco | join(', ') }}
```

## 4.5 Link e file statici

```html
<a href="{{ url_for('pratiche.dettaglio', pratica_id=p.id) }}">Apri</a>
<link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
```

Mai scrivere gli indirizzi a mano.

## 4.6 Macro

Sono funzioni che producono HTML, per gli elementi che si ripetono.

```html
{# in _frammenti.html #}
{% macro etichetta(testo, colore) %}
  <span class="badge text-bg-{{ colore }}">{{ testo }}</span>
{% endmacro %}
```

```html
{# in un altro template #}
{% from "_frammenti.html" import etichetta %}
{{ etichetta("Chiusa", "success") }}
```

## 4.7 Una cosa gratis sulla sicurezza

Jinja2 **fa l'escape dell'HTML automaticamente**. Se uno studente scrive `<script>...</script>` nel campo note, viene stampato come testo, non eseguito. Sei protetto dagli attacchi XSS senza fare niente.

L'unico modo per bucarti è usare il filtro `| safe`. **Non usarlo mai** su dati che arrivano dagli utenti. Vale la pena scriverlo nella relazione, nella sezione sulla sicurezza.

---

# 5. SQLAlchemy: parlare al database

## 5.1 Definire una tabella

```python
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.extensions import db

class Istituto(db.Model):
    __tablename__ = "istituto"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(sa.String(150))
    paese: Mapped[str] = mapped_column(sa.String(80), index=True)
    attivo: Mapped[bool] = mapped_column(default=True)
    note: Mapped[str | None] = mapped_column(sa.Text)     # ammette NULL

    __table_args__ = (
        sa.UniqueConstraint("nome", "citta", name="uq_istituto_nome_citta"),
        sa.CheckConstraint("length(nome) > 0", name="ck_istituto_nome"),
    )
```

Le due regole da ricordare:

- **`Mapped[str]` genera `NOT NULL`. `Mapped[str | None]` ammette il nullo.** Il tipo dell'annotazione decide il vincolo: è il punto in cui Python e SQL si toccano.
- **`__table_args__` è una tupla**, quindi se contiene un solo elemento serve la virgola finale: `(vincolo,)`. Senza, Python non la considera una tupla ed è un errore poco chiaro.

## 5.2 Collegare due tabelle

```python
class Pratica(db.Model):
    __tablename__ = "pratica"

    id: Mapped[int] = mapped_column(primary_key=True)
    istituto_id: Mapped[int] = mapped_column(
        sa.ForeignKey("istituto.id", ondelete="RESTRICT"), index=True
    )

    # attributo navigabile: NON è una colonna, è la join già fatta
    istituto: Mapped["Istituto"] = relationship(back_populates="pratiche")
    esami: Mapped[list["EsameMappato"]] = relationship(
        back_populates="pratica", cascade="all, delete-orphan"
    )
```

Distinzione fondamentale: **`istituto_id` è la colonna, `istituto` è l'oggetto.** La prima contiene un numero, il secondo l'istituto intero. `back_populates` collega i due lati, così modificandone uno si aggiorna anche l'altro.

`cascade="all, delete-orphan"` significa: cancellando una pratica si cancellano i suoi esami. Va messo solo dove i figli non hanno senso senza il padre — mai verso utenti o istituti.

## 5.3 Leggere

```python
# per chiave primaria: il modo più veloce
pratica = db.session.get(Pratica, 7)         # None se non esiste

# un solo oggetto da una condizione
utente = db.session.scalar(
    db.select(Utente).where(Utente.email == email)
)

# molti oggetti
pratiche = db.session.scalars(
    db.select(Pratica)
    .where(Pratica.stato == StatoPratica.CREATA)
    .order_by(Pratica.id.desc())
).all()
```

**`scalar` restituisce un oggetto, `scalars` una sequenza di oggetti**, su cui `.all()` produce la lista. Se invece selezioni singole colonne o aggregati usi `db.session.execute(...)`, che restituisce righe.

Le condizioni più usate — sono frammenti da agganciare a `db.select(...)`, non codice a sé stante:

```text
.where(Pratica.stato == StatoPratica.CHIUSA)
.where(Pratica.anno_accademico == "2025/26", Pratica.studente_id == 3)  # AND
.where(sa.or_(A, B))                       # OR
.where(Pratica.note.is_(None))             # IS NULL — non "== None"
.where(Istituto.attivo.is_(True))
.where(Pratica.id.in_([1, 2, 3]))
.where(Istituto.nome.ilike("%tokyo%"))     # LIKE senza distinzione di maiuscole
.order_by(Pratica.data_creazione.desc())
.limit(10)
```

## 5.4 Scrivere

```python
# INSERT
p = Pratica(anno_accademico="2025/26", istituto=keio, studente=marco)
db.session.add(p)
db.session.commit()
print(p.id)              # l'id assegnato dal database è già qui

# UPDATE — non si scrive nessuna UPDATE
p = db.session.get(Pratica, 7)
p.stato = StatoPratica.IN_CORSO
db.session.commit()      # la UPDATE la genera SQLAlchemy

# DELETE
db.session.delete(p)
db.session.commit()
```

Il meccanismo si chiama *unit of work*: la sessione tiene traccia di cosa hai toccato e al `commit` emette le istruzioni necessarie. Per chi viene da SQL è la cosa più straniante, e la più comoda.

## 5.5 La transazione

```python
from sqlalchemy.exc import IntegrityError

try:
    documento.esito = Esito.APPROVATO
    documento.pratica.stato = StatoPratica.PRE_PARTENZA_OK
    db.session.commit()                  # UN SOLO commit: le due insieme
except IntegrityError:
    db.session.rollback()
    flash("Operazione non consentita.", "error")
except Exception:
    db.session.rollback()
    raise
```

Un `commit` per operazione, alla fine. Se salta, `rollback`, sempre.

## 5.6 Aggregati

Qui si usa `execute` invece di `scalars`, perché non tornano oggetti ma righe.

```python
righe = db.session.execute(
    sa.select(Istituto.paese, sa.func.count(Pratica.id).label("totale"))
    .join(Pratica, Pratica.istituto_id == Istituto.id)
    .group_by(Istituto.paese)
    .order_by(sa.desc("totale"))
).all()

for riga in righe:
    print(riga.paese, riga.totale)       # accesso per nome
```

Funzioni utili: `sa.func.count()`, `sa.func.sum()`, `sa.func.avg()`, `sa.func.max()`, `sa.func.now()`.

## 5.7 Evitare le query a cascata

```python
from sqlalchemy.orm import selectinload

pratiche = db.session.scalars(
    db.select(Pratica)
    .options(selectinload(Pratica.istituto), selectinload(Pratica.studente))
).all()
```

Senza `selectinload`, se il template legge `p.istituto.nome` per cinquanta pratiche, parte una query per riga. Con, ne parte una sola in più.

Per accorgertene: `SQL_ECHO=1` nel `.env` e conta le righe nel terminale.

---

# 6. Flask-Login e i controlli di accesso

## 6.1 I quattro pezzi

```python
# 1. la classe utente eredita anche da UserMixin
class Utente(UserMixin, db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(sa.String(120), unique=True)

# 2. la callback che ricostruisce l'utente dal cookie, in create_app()
@login_manager.user_loader
def carica_utente(id_utente: str) -> Utente | None:
    return db.session.get(Utente, int(id_utente))

# 3. entrare e uscire
login_user(utente)
logout_user()

# 4. proteggere una route
@login_required
def pagina_riservata(): ...
```

`current_user` è disponibile ovunque, route e template, e rappresenta chi è collegato in quel momento. Se nessuno è entrato, `current_user.is_authenticated` è `False`.

## 6.2 Password

```python
from passlib.hash import pbkdf2_sha256

hash_da_salvare = pbkdf2_sha256.hash("password-in-chiaro")
pbkdf2_sha256.verify("tentativo", hash_da_salvare)     # True o False
```

Nel database va **solo l'hash**. La password in chiaro non si scrive da nessuna parte, nemmeno nei dati di prova.

## 6.3 Il decoratore di ruolo

Questo è il pezzo che devi scrivere tu. È il codice più "avanzato" del progetto e sono dodici righe:

```python
from functools import wraps
from flask import abort
from flask_login import current_user

def ruolo_richiesto(*ruoli):
    def decoratore(vista):
        @wraps(vista)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated or current_user.ruolo not in ruoli:
                abort(403)
            return vista(*args, **kwargs)
        return wrapper
    return decoratore
```

Come si legge: `ruolo_richiesto(Ruolo.UFFICIO)` viene chiamata e restituisce `decoratore`; Python applica `decoratore` alla tua funzione e ottiene `wrapper`, che d'ora in poi prende il suo posto. Quando arriva una richiesta viene eseguito `wrapper`, che controlla e poi — se tutto va bene — chiama la funzione vera.

`*args, **kwargs` significa "qualunque argomento": serve perché il wrapper deve funzionare con route che ricevono parametri diversi. `@wraps` conserva il nome originale della funzione, che a Flask serve per costruire l'endpoint.

## 6.4 Il controllo di appartenenza

```python
def esigi_accesso(pratica) -> None:
    if current_user.ruolo is Ruolo.UFFICIO:
        return
    if current_user.ruolo is Ruolo.STUDENTE and pratica.studente_id == current_user.id:
        return
    if current_user.ruolo is Ruolo.DOCENTE and pratica.docente_id == current_user.id:
        return
    abort(404)      # 404 e non 403: un 403 confermerebbe che la pratica esiste
```

Va chiamato in **ogni** route che riceve un id.

---

# 7. Ricettario

I pezzi che scriverai davvero, pronti da adattare.

## 7.1 Pagina di elenco filtrata per utente

```python
@studente_bp.route("/pratiche")
@login_required
@ruolo_richiesto(Ruolo.STUDENTE)
def elenco_pratiche():
    pratiche = db.session.scalars(
        db.select(Pratica)
        .where(Pratica.studente_id == current_user.id)     # filtro NELLA query
        .options(selectinload(Pratica.istituto))
        .order_by(Pratica.id.desc())
    ).all()
    return render_template("studente/elenco.html", pratiche=pratiche)
```

## 7.2 Pagina di dettaglio protetta

```python
@pratiche_bp.route("/pratiche/<int:pratica_id>")
@login_required
def dettaglio(pratica_id: int):
    pratica = db.session.get(Pratica, pratica_id)
    if pratica is None:
        abort(404)
    esigi_accesso(pratica)
    return render_template("pratiche/dettaglio.html", pratica=pratica)
```

## 7.3 Form: mostrare e ricevere

```python
@studente_bp.route("/pratiche/nuova", methods=["GET", "POST"])
@login_required
@ruolo_richiesto(Ruolo.STUDENTE)
def nuova_pratica():
    istituti = db.session.scalars(
        db.select(Istituto).where(Istituto.attivo.is_(True)).order_by(Istituto.nome)
    ).all()

    if request.method == "POST":
        errori = []
        anno = request.form.get("anno_accademico", "").strip()
        if len(anno) != 7 or anno[4] != "/":
            errori.append("Anno accademico non valido (formato 2025/26).")

        istituto_id = request.form.get("istituto_id", type=int)
        if istituto_id not in {i.id for i in istituti}:
            errori.append("Istituto non valido.")

        if errori:
            for e in errori:
                flash(e, "error")
            # si rimanda indietro il modulo CON i valori già digitati
            return render_template("studente/nuova.html",
                                   istituti=istituti, dati=request.form), 400

        pratica = Pratica(studente_id=current_user.id,
                          istituto_id=istituto_id,
                          anno_accademico=anno)
        db.session.add(pratica)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("Hai già una pratica per questo anno e istituto.", "error")
            return render_template("studente/nuova.html",
                                   istituti=istituti, dati=request.form), 409

        flash("Pratica creata.", "success")
        return redirect(url_for("pratiche.dettaglio", pratica_id=pratica.id))

    return render_template("studente/nuova.html", istituti=istituti, dati={})
```

Questo è il modello di **tutte** le pagine con un modulo. Cambiano i campi, non la struttura.

## 7.4 Il template del modulo

```html
<form method="post">
  <div class="mb-3">
    <label class="form-label" for="anno_accademico">Anno accademico</label>
    <input class="form-control" id="anno_accademico" name="anno_accademico"
           value="{{ dati.get('anno_accademico', '') }}" required>
  </div>

  <div class="mb-3">
    <label class="form-label" for="istituto_id">Istituto</label>
    <select class="form-select" id="istituto_id" name="istituto_id" required>
      <option value="">— scegli —</option>
      {% for i in istituti %}
        <option value="{{ i.id }}">{{ i.nome }} ({{ i.paese }})</option>
      {% endfor %}
    </select>
  </div>

  <button class="btn btn-dark" type="submit">Crea</button>
</form>
```

Il valore di `name` nell'HTML è la chiave che leggi in `request.form`. Devono combaciare.

## 7.5 Due pulsanti nello stesso modulo

```html
<button type="submit" name="azione" value="approva" class="btn btn-success">Approva</button>
<button type="submit" name="azione" value="rifiuta" class="btn btn-danger">Rifiuta</button>
```

```python
approvato = request.form.get("azione") == "approva"
```

## 7.6 Azione che cambia stato, in transazione

```python
@docente_bp.route("/documenti/<int:documento_id>/decidi", methods=["POST"])
@login_required
@ruolo_richiesto(Ruolo.DOCENTE)
def decidi_documento(documento_id: int):
    documento = db.session.get(Documento, documento_id)
    if documento is None:
        abort(404)
    esigi_accesso(documento.pratica)

    approvato = request.form.get("azione") == "approva"
    motivazione = request.form.get("motivazione", "").strip() or None

    if not approvato and not motivazione:
        flash("Il rifiuto richiede una motivazione.", "error")
        return redirect(url_for("pratiche.dettaglio", pratica_id=documento.pratica_id))

    try:
        documento.esito = Esito.APPROVATO if approvato else Esito.RIFIUTATO
        documento.motivazione = motivazione
        documento.deciso_il = datetime.now()
        if approvato:
            documento.pratica.stato = StatoPratica.PRE_PARTENZA_OK
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    flash("Decisione registrata.", "success")
    return redirect(url_for("pratiche.dettaglio", pratica_id=documento.pratica_id))
```

## 7.7 Caricare un file

```html
<form method="post" enctype="multipart/form-data">
  <input class="form-control" type="file" name="documento" accept=".pdf" required>
  <button class="btn btn-dark mt-2" type="submit">Carica</button>
</form>
```

```python
from pathlib import Path
import uuid

file_ricevuto = request.files.get("documento")
if file_ricevuto is None or file_ricevuto.filename == "":
    flash("Nessun file selezionato.", "error")
    return redirect(...)

estensione = Path(file_ricevuto.filename).suffix.lower()
if estensione not in current_app.config["ALLOWED_UPLOAD_EXTENSIONS"]:
    flash("Sono ammessi solo file PDF.", "error")
    return redirect(...)

nome_archivio = f"p{pratica.id}_{uuid.uuid4().hex}{estensione}"
percorso = current_app.config["UPLOAD_FOLDER"] / nome_archivio
file_ricevuto.save(percorso)
```

Senza `enctype="multipart/form-data"` il file **non arriva** e `request.files` è vuoto. È l'errore più frequente e non dà nessun messaggio utile.

## 7.8 Scaricare un file con controllo dei permessi

```python
from flask import send_from_directory

@pratiche_bp.route("/documenti/<int:documento_id>/scarica")
@login_required
def scarica(documento_id: int):
    documento = db.session.get(Documento, documento_id)
    if documento is None:
        abort(404)
    esigi_accesso(documento.pratica)          # PRIMA di restituire il file
    return send_from_directory(
        current_app.config["UPLOAD_FOLDER"],
        documento.nome_archivio,
        as_attachment=True,
        download_name=documento.nome_originale,
    )
```

## 7.9 Filtro da querystring

```python
query = db.select(Pratica).order_by(Pratica.id.desc())
stato = request.args.get("stato")
if stato:
    try:
        query = query.where(Pratica.stato == StatoPratica(stato))
    except ValueError:
        abort(400)                            # valore inventato nell'URL
pratiche = db.session.scalars(query).all()
```

## 7.10 Enum: dalla stringa al valore

```python
StatoPratica("chiusa")            # dal valore al membro; ValueError se non esiste
StatoPratica.CHIUSA.value         # "chiusa"
list(StatoPratica)                # tutti i membri, per popolare un menu
```

Nei template si usa sempre `.value`: `{{ pratica.stato.value }}`.

---

# 8. Come si legge un errore

Quando Flask è in modalità debug, l'errore compare direttamente nel browser con lo stack completo. **La riga che ti serve è l'ultima**, quella con il nome dell'eccezione, e subito sopra il file e il numero di riga del tuo codice — ignora le righe che parlano di file dentro `.venv`, sono le viscere delle librerie.

I messaggi che incontrerai più spesso:

- **`IndentationError` / `TabError`** — hai mescolato tabulazioni e spazi. In PyCharm: *Edit → Convert Indents → To Spaces*.
- **`NameError: name 'x' is not defined`** — nome scritto male, o import mancante.
- **`AttributeError: 'NoneType' object has no attribute '...'`** — il classico. Qualcosa che credevi essere un oggetto è `None`: quasi sempre un `db.session.get()` che non ha trovato niente. Controlla sempre `if x is None`.
- **`KeyError: 'campo'`** — hai letto `request.form["campo"]` e il campo non è arrivato. Usa `.get()`, e verifica che il `name` nell'HTML combaci.
- **`jinja2.exceptions.UndefinedError`** — il template usa una variabile che la route non gli ha passato.
- **`werkzeug.routing.BuildError`** — `url_for` punta a un endpoint che non esiste. Nome del blueprint o della funzione sbagliato, oppure blueprint non registrato.
- **`sqlalchemy.exc.IntegrityError`** — il database ha respinto la scrittura. Nel messaggio c'è il nome del vincolo violato: da lì risali alla regola. **Non è un bug**, è il database che fa il suo lavoro.
- **`RuntimeError: Working outside of application context`** — stai usando `db.session` fuori da una richiesta HTTP. Negli script serve `with app.app_context():`.
- **`405 Method Not Allowed`** — hai inviato un POST a una route che non lo dichiara in `methods`.

Regola generale: **leggi il messaggio prima di cercare su internet.** In Python è quasi sempre esatto e dice cosa manca.
