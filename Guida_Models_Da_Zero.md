# Capire `models.py` partendo da zero

Guida per chi programma in C++ e non ha mai scritto Python.

Non si parte da SQLAlchemy. Si parte da come Python organizza i file, come
funzionano le classi, e solo dopo si guarda il modello. Ogni concetto ha
accanto il corrispettivo C++ quando ce n'è uno, e la nota su dove il
corrispettivo è fuorviante.

---

## Indice

1. [Un file Python è un modulo](#1-un-file-python-è-un-modulo)
2. [`import`: le quattro forme e cosa fanno davvero](#2-import-le-quattro-forme-e-cosa-fanno-davvero)
3. [Le cartelle sono pacchetti](#3-le-cartelle-sono-pacchetti)
4. [Dove vive `flask_login` se non è nel tuo progetto](#4-dove-vive-flask_login-se-non-è-nel-tuo-progetto)
5. [Le classi](#5-le-classi)
6. [Ereditarietà, ereditarietà multipla, mixin](#6-ereditarietà-ereditarietà-multipla-mixin)
7. [Le annotazioni di tipo](#7-le-annotazioni-di-tipo)
8. [`from __future__ import annotations`, spiegato bene](#8-from-__future__-import-annotations-spiegato-bene)
9. [I decoratori](#9-i-decoratori)
10. [Cosa succede quando scrivi `class Utente(db.Model)`](#10-cosa-succede-quando-scrivi-class-utentedbmodel)
11. [`enums.py`: solo costanti](#11-enumspy-solo-costanti)
12. [`models.py` pezzo per pezzo](#12-modelspy-pezzo-per-pezzo)
13. [Come `models.py` si aggancia a Flask](#13-come-modelspy-si-aggancia-a-flask)
14. [Il viaggio di una richiesta](#14-il-viaggio-di-una-richiesta)
15. [Gli errori che farete](#15-gli-errori-che-farete)

---

## 1. Un file Python è un modulo

In C++ hai due file per ogni componente: `utente.h` con le dichiarazioni e
`utente.cpp` con le definizioni. Il compilatore prende i `.cpp` uno per uno,
il linker li unisce alla fine.

In Python non esiste niente di tutto questo. **Un file `.py` è un modulo, e
basta.** Non c'è header, non c'è dichiarazione separata dalla definizione,
non c'è compilazione, non c'è linker.

E soprattutto: **il file non viene "compilato", viene eseguito dall'alto verso
il basso.**

Questa è la differenza più importante da interiorizzare. Prendi questo file:

```python
# esempio.py

print("sto partendo")

def saluta(nome):
    print(f"ciao {nome}")

class Persona:
    def __init__(self, nome):
        self.nome = nome

print("ho finito")
```

Quando questo file viene importato, Python **esegue tutte e cinque le
istruzioni in ordine**:

1. stampa `sto partendo`
2. crea un oggetto funzione e lo chiama `saluta`
3. crea un oggetto classe e lo chiama `Persona`
4. stampa `ho finito`

Sì: `def` e `class` non sono dichiarazioni, sono **istruzioni eseguibili** che
costruiscono un oggetto e gli danno un nome. Una classe in Python è un oggetto
come un altro, creato a runtime.

Questa cosa sembra un dettaglio filosofico e invece spiega metà dei problemi
che incontrerete. Per esempio spiega perché l'ordine delle righe conta:

```python
class Pratica:
    studente: Utente      # ERRORE: Utente non esiste ancora

class Utente:
    pass
```

Quando Python esegue la prima `class`, la seconda non è ancora stata eseguita,
quindi il nome `Utente` non esiste. In C++ risolveresti con una forward
declaration. In Python la forward declaration non esiste, e la soluzione è
un'altra: la trovi al capitolo 8.

---

## 2. `import`: le quattro forme e cosa fanno davvero

`import` non è `#include`. `#include` incolla il testo di un file dentro un
altro. `import` **esegue un modulo una volta sola** e ti dà accesso ai nomi
che quel modulo ha definito.

"Una volta sola" è letterale: se dieci file importano lo stesso modulo, il
codice di quel modulo viene eseguito una volta e le altre nove volte Python
restituisce quello che aveva già in memoria. Non esistono le include guard
perché non servono.

Le quattro forme:

```python
import sqlalchemy
# Esegue il modulo. Per usarlo scrivi il nome completo:
sqlalchemy.String(120)
```

```python
import sqlalchemy as sa
# Identico, ma con un alias piu' corto.
sa.String(120)
```

```python
from sqlalchemy.orm import Mapped, relationship
# Esegue il modulo e prende SOLO quei due nomi, portandoli nel tuo file.
# Ora li usi nudi:
relationship(...)
```

```python
from app.enums import Ruolo
# Stessa cosa, ma il modulo e' uno dei nostri.
```

La terza forma è quella che userete di più, e ha una conseguenza che va
capita: **il nome importato diventa un nome del tuo file, come se l'avessi
definito tu.** Se in `models.py` scrivi `from app.extensions import db`, da
quel momento `db` è un nome valido dentro `models.py`, e chi importa
`models.py` potrebbe perfino scrivere `from app.models import db`. Funziona,
ma è una pessima idea: rende impossibile capire da dove viene una cosa.

**Regola pratica:** ogni nome che usi in un file deve essere o definito lì,
o importato lì. Non esiste "l'ho già importato nell'altro file". Ogni file
ha il suo elenco di import in cima, e li riscrive tutti.

---

## 3. Le cartelle sono pacchetti

Una cartella che contiene un file `__init__.py` è un **pacchetto**: un modulo
composto da più file.

```
app/
    __init__.py        <- questo rende "app" un pacchetto
    models.py
    enums.py
    extensions.py
    blueprints/
        __init__.py    <- e questo rende "app.blueprints" un sottopacchetto
        auth.py
        pratiche.py
```

Il punto nel percorso di import corrisponde alla barra nel percorso su disco:

```python
from app.models import Pratica              # app/models.py
from app.blueprints.auth import auth_bp     # app/blueprints/auth.py
```

`__init__.py` è il file che viene eseguito quando importi il pacchetto. Nel
vostro progetto `app/__init__.py` contiene `create_app()`, quindi scrivere
`from app import create_app` esegue quel file e prende quella funzione.

Ecco perché avete **due** `__init__.py`: uno in `app/` e uno in
`app/blueprints/`. Non sono duplicati, sono i marcatori di due pacchetti
diversi. Quello dentro `blueprints/` è vuoto o quasi, ed è normale: serve solo
a dire "questa cartella è un pacchetto".

Da dove partono i percorsi? Dalla cartella in cui lanci il programma. Voi
lanciate dalla radice del progetto, dove c'è `app/`, quindi `app.models`
si risolve. Se lanciaste da dentro `app/`, non funzionerebbe niente.

---

## 4. Dove vive `flask_login` se non è nel tuo progetto

`UserMixin` da dove esce, se non hai un file che si chiama così?

Quando lanci `pip install flask-login`, pip scarica il pacchetto e lo copia
dentro il tuo ambiente virtuale, qui:

```
.venv/lib/python3.13/site-packages/flask_login/
    __init__.py
    mixins.py          <- UserMixin sta qui dentro
    login_manager.py
    utils.py
    ...
```

Sono file `.py` normalissimi, scritti da qualcuno, che puoi aprire e leggere.
In PyCharm ci arrivi con ctrl+click (cmd+click su Mac) sul nome: si apre il
sorgente della libreria. **Fallo davvero almeno una volta**, perché toglie la
sensazione che le librerie siano magia.

`UserMixin` è una classe, come la tua `Utente`. Ecco più o meno cosa contiene,
per intero:

```python
class UserMixin:
    @property
    def is_active(self):
        return True

    @property
    def is_authenticated(self):
        return self.is_active

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)
```

Tutto qui. Flask-Login, per funzionare, ha bisogno che l'oggetto utente sappia
rispondere a queste quattro domande. Invece di farvele scrivere a mano,
vi offre una classe che le implementa nel modo ragionevole e ve la fa
ereditare.

Quando la tua `Utente` eredita da `UserMixin`, `utente.get_id()` esiste anche
se tu non l'hai scritto. E `get_id` restituisce `str(self.id)` — cioè l'`id`
della **tua** tabella, convertito in stringa. È per questo che nel
`user_loader` fai `int(id_utente)`: Flask-Login te lo restituisce come stringa
perché lo ha salvato in un cookie, e i cookie contengono solo testo.

L'ambiente virtuale è la ragione per cui il progetto è riproducibile: le
librerie stanno dentro la cartella del progetto, non installate nel sistema.
`requirements.txt` è l'elenco di cosa serve, e `pip install -r
requirements.txt` lo ricrea identico sul computer di un compagno.

---

## 5. Le classi

La sintassi minima:

```python
class Persona:
    def __init__(self, nome, eta):
        self.nome = nome
        self.eta = eta

    def saluta(self):
        print(f"ciao, sono {self.nome}")
```

Uso:

```python
p = Persona("Leo", 22)     # nota: niente "new"
p.saluta()
print(p.nome)
```

Sei differenze rispetto al C++, in ordine di quanto vi daranno fastidio.

**`self` va scritto sempre.** È il `this`, ma in C++ è implicito e in Python è
il primo parametro esplicito di ogni metodo. Lo scrivi nella definizione e
*non* lo passi nella chiamata: `p.saluta()` diventa internamente
`Persona.saluta(p)`. Dimenticare `self` è l'errore numero uno dei principianti.

**`self` esiste solo dentro i metodi.** Ci sono tre livelli:

```python
class Studente(Persona):        # 1. la RIGA DI DEFINIZIONE della classe
    materia = "informatica"     # 2. il CORPO della classe
    def saluta(self):           # 3. dentro un METODO
        print(self.nome)
```

Ai livelli 1 e 2 nessun oggetto esiste ancora: la classe si sta costruendo, e
`self` non avrebbe a cosa riferirsi. Le parentesi del livello 1 non c'entrano
con `self`: sono l'elenco delle classi base, e basta.

**Gli attributi si accedono sempre con `self.`** Dentro un metodo, `nome` da
solo è una variabile locale; l'attributo dell'oggetto è `self.nome`.

**`__init__` è il costruttore**, ma non "costruisce": l'oggetto esiste già
quando `__init__` viene chiamato, e il suo compito è solo inizializzarne gli
attributi. Non restituisce niente.

**Non c'è dichiarazione degli attributi.** In C++ i membri li elenchi nella
classe. In Python un attributo nasce nel momento in cui gli assegni un valore,
anche fuori dal costruttore e anche fuori dalla classe:

```python
p.altezza = 180     # legale: l'attributo nasce ora
```

Al vostro livello conviene non sfruttarlo mai, ma dovete sapere che è
possibile, perché spiega perché Python non vi avvisa se scrivete male il nome
di un attributo in un'assegnazione.

**Non c'è `private`, `protected`, `public`.** Tutto è accessibile. La
convenzione è che un nome che inizia con underscore (`_metodo_interno`) è
privato per gentile accordo, e nessuno lo fa rispettare.

**Non c'è overloading.** Non puoi avere due metodi con lo stesso nome e
parametri diversi: il secondo sovrascrive il primo, silenziosamente. Si
ottiene lo stesso effetto con i parametri di default:

```python
def crea(self, nome, eta=None):
    ...
```

---

## 6. Ereditarietà, ereditarietà multipla, mixin

### La sintassi

```python
class Studente(Persona):
    ...
```

Le parentesi dopo il nome della classe elencano le **classi base**. Non stai
creando un oggetto: stai dichiarando da chi eredita. È l'equivalente esatto di
`class Studente : public Persona`. In Python l'ereditarietà è sempre pubblica,
non esiste altro.

`class Persona:` senza parentesi eredita implicitamente da `object`, che è la
radice di tutto.

### Cosa si eredita, esattamente

Esistono **due** tipi di attributo e si comportano in modo diverso.

**Attributi di classe** — scritti nel corpo della classe. Appartengono alla
classe, sono condivisi da tutte le istanze, e si ereditano come i metodi:

```python
class Persona:
    specie = "homo sapiens"

class Studente(Persona):
    pass

print(Studente.specie)   # "homo sapiens" — ereditato
```

**Attributi di istanza** — creati con `self.x = ...`, tipicamente in
`__init__`. Appartengono al singolo oggetto. Si "ereditano" perché **si eredita
il costruttore**:

```python
class Persona:
    def __init__(self, nome):
        self.nome = nome

class Studente(Persona):
    pass

s = Studente("Leo")
print(s.nome)      # "Leo"
```

`Studente` non definisce `__init__`, quindi Python risale la catena e trova
quello di `Persona`. Lo esegue con `self` che punta all'oggetto `Studente`, e
`self.nome = nome` crea l'attributo su quell'oggetto.

### La trappola

Se `Studente` definisce il proprio `__init__`, quello del padre **non viene
chiamato da solo**. In C++ il costruttore base viene invocato automaticamente;
in Python no.

```python
class Studente(Persona):
    def __init__(self, nome, matricola):
        super().__init__(nome)          # <- obbligatorio, senno' self.nome non esiste
        self.matricola = matricola
```

`super()` è l'equivalente della lista di inizializzazione `: Persona(nome)`,
ma devi scriverla tu.

### Ereditarietà multipla

```python
class Utente(UserMixin, db.Model):
    ...
```

Qui `Utente` eredita da **due** classi contemporaneamente. In C++ si può fare
e si sconsiglia, per via del problema del diamante. In Python è normale e
usata continuamente, perché Python ha una regola deterministica per risolvere
i conflitti.

La regola si chiama **MRO**, Method Resolution Order. Quando scrivi
`u.qualcosa`, Python cerca in questo ordine:

1. nell'istanza `u`
2. nella classe `Utente`
3. in `UserMixin`
4. in `db.Model`
5. nelle basi di quelle, ricorsivamente
6. in `object`

Il primo che trova, vince. Quindi **l'ordine delle basi conta**: `class
Utente(UserMixin, db.Model)` e `class Utente(db.Model, UserMixin)` non sono
identiche. Se entrambe definissero lo stesso metodo, vincerebbe quella scritta
prima.

Puoi guardare l'ordine effettivo:

```python
print(Utente.__mro__)
```

### Cos'è un mixin

Un **mixin** non è un costrutto del linguaggio: è un modo di usare
l'ereditarietà. Un mixin è una classe che:

- non ha senso da sola (non istanzieresti mai un `UserMixin`)
- non ha stato proprio, o quasi
- aggiunge un gruppo di metodi coerenti a chi la eredita

L'idea è "componi la tua classe prendendo pezzi". In C++ ci si arriva coi
template e con l'ereditarietà multipla privata; in Python si fa così ed è la
prassi.

Nel vostro caso:

```python
class Utente(UserMixin, db.Model):
```

si legge: **`Utente` è una tabella del database (`db.Model`) a cui aggiungo
la capacità di essere un utente autenticabile (`UserMixin`).** Due
responsabilità che vengono da due librerie diverse, che non si conoscono fra
loro, e che si combinano senza attriti perché toccano metodi diversi.

---

## 7. Le annotazioni di tipo

```python
nome: str = "Leo"

def saluta(nome: str) -> None:
    print(nome)
```

I due punti dopo un nome, e la freccia dopo i parametri, sono **annotazioni di
tipo**. Sintatticamente Python le accetta e **poi le ignora**: non c'è nessun
controllo, e questo codice gira senza un lamento:

```python
def raddoppia(x: int) -> int:
    return x * 2

raddoppia("ciao")     # restituisce "ciaociao". Nessun errore.
```

Servono a tre destinatari, nessuno dei quali è l'interprete:

- **a te**, come documentazione che non può andare fuori sincrono col codice
- **a PyCharm**, che da lì costruisce l'autocompletamento e segnala gli errori
  evidenti
- **a certe librerie**, che le leggono a runtime e ci fanno qualcosa

L'ultimo punto è il vostro caso. SQLAlchemy 2.0 **legge le annotazioni** e da
`Mapped[int]` deduce che la colonna è un `INTEGER`, da `Mapped[str | None]`
che ammette `NULL`. Qui l'annotazione non è documentazione: è configurazione.
È una scelta di design della libreria, non una regola del linguaggio, e
confonderle è normale all'inizio.

Notazioni che vi servono:

```python
str | None            # stringa oppure niente. Come std::optional<string>
list[Pratica]         # lista di Pratica. Come std::vector<Pratica>
dict[str, int]        # dizionario stringa -> intero. Come std::map
tuple[int, str]       # tupla di due elementi
```

### Il caso particolare di `Mapped[...]`

`Mapped` è un **tipo generico** importato da `sqlalchemy.orm`. Le parentesi
quadre sono la sintassi Python per i generici, come le angolari del C++:

```
std::vector<int>     ->     list[int]
Mapped<std::string>  ->     Mapped[str]
```

`Mapped[str]` si legge "colonna mappata che contiene una stringa". Da lì
SQLAlchemy ricava due cose:

*Il tipo SQL*, se non glielo dici tu. Da `Mapped[int]` deduce `INTEGER`, da
`Mapped[dt.date]` deduce `DATE`.

*Se ammette NULL.* `Mapped[str]` diventa `NOT NULL`, `Mapped[str | None]`
ammette i NULL. È l'unica informazione che passa **solo** da lì.

**Non è il tipo del valore che leggi.** A runtime `u.email` è una normalissima
stringa, non un oggetto `Mapped`. `Mapped` esiste solo nell'annotazione.

**Nelle relazioni cambia significato**: lì non c'è nessuna colonna, e serve a
indicare la cardinalità.

```python
studente:  Mapped[Utente]         # uno solo
pratiche:  Mapped[list[Pratica]]  # molti
```

---

## 8. `from __future__ import annotations`, spiegato bene

### Il problema

Ricorda il capitolo 1: **un file viene eseguito dall'alto in basso**, e `class`
è un'istruzione eseguibile. Quindi:

```python
class Pratica:
    studente: Utente          # <-- riga eseguita ADESSO

class Utente:
    pass                      # <-- questa classe nascera' fra un istante
```

Quando Python arriva alla riga `studente: Utente`, la classe `Utente` non
esiste ancora. Il nome non è definito. Errore:

```
NameError: name 'Utente' is not defined
```

In C++ non hai il problema perché il compilatore fa più passate e perché puoi
scrivere `class Utente;` come forward declaration. In Python non c'è una
forward declaration.

### Perché non basta invertire l'ordine

Perché il riferimento è **circolare**. `Pratica` nomina `Utente` e `Utente`
nomina `Pratica`:

```python
class Utente:
    pratiche: list[Pratica]   # serve Pratica

class Pratica:
    studente: Utente          # serve Utente
```

Qualunque ordine scegli, una delle due nomina qualcosa che non esiste ancora.
Non è un problema di disciplina: è strutturale.

### La soluzione vecchia: le virgolette

Storicamente si scriveva il tipo come stringa:

```python
class Utente:
    pratiche: "list[Pratica]"      # e' solo testo, Python non lo valuta
```

Python vede una stringa e la mette da parte senza cercare di capirla. Chi ha
bisogno di sapere il tipo (PyCharm, SQLAlchemy) legge la stringa e la
interpreta **dopo**, quando tutte le classi esistono.

Funziona, ma se lo devi fare su ogni annotazione il file si riempie di
virgolette.

### La soluzione nuova: la riga magica

```python
from __future__ import annotations
```

Questa riga dice all'interprete: **in questo file, tratta TUTTE le annotazioni
di tipo come se fossero fra virgolette.** Non valutarne nessuna. Conservale
come testo.

Quindi da quel momento puoi scrivere:

```python
from __future__ import annotations

class Utente:
    pratiche: list[Pratica]        # nessun errore: e' solo testo

class Pratica:
    studente: Utente               # nessun errore: e' solo testo
```

e non c'è più nessun ordine da rispettare. Chi ha bisogno del tipo vero lo
risolve più tardi, quando il file è stato letto tutto.

### Perché si chiama `__future__`

È un meccanismo storico di Python per attivare in anticipo comportamenti che
diventeranno il default nelle versioni successive. `from __future__ import
qualcosa` non importa una libreria: è un'istruzione speciale per l'interprete,
e **deve stare in cima al file**, prima di ogni altro import.

### La regola meccanica che ti basta ricordare

Nel file troverai comunque alcune classi scritte fra virgolette:

```python
pratiche_come_studente: Mapped[list[Pratica]] = relationship(
    foreign_keys="Pratica.studente_id",       # <-- stringa
)
```

Non è un'incoerenza. La regola è puramente posizionale:

- **prima dell'uguale** (l'annotazione) → nome nudo, ci pensa la riga magica
- **dopo l'uguale** (gli argomenti della funzione) → fra virgolette

Il motivo è che `from __future__` agisce **solo sulle annotazioni**, e gli
argomenti di una chiamata non lo sono: quelli Python li valuta sempre, subito.
SQLAlchemy accetta le stringhe lì proprio perché sa che non può fare
altrimenti, e le risolve più tardi.

Non ti serve capirlo più a fondo di così.

---

## 9. I decoratori

```python
@property
def e_studente(self) -> bool:
    return self.ruolo == Ruolo.STUDENTE
```

La chiocciola sopra una funzione è un **decoratore**. Significa: prendi la
funzione che sto per definire, passala a `property`, e chiama il risultato
`e_studente`.

Cioè queste due scritture sono equivalenti:

```python
@property
def e_studente(self): ...

# identico a:
def e_studente(self): ...
e_studente = property(e_studente)
```

Un decoratore è quindi una funzione che prende una funzione e ne restituisce
un'altra. Non è magia sintattica: è una riscrittura meccanica.

`@property` in particolare fa sì che si usi **senza parentesi**:

```python
if utente.e_studente:        # non e_studente()
```

Perché serve: nei template Jinja2 scrivere `{% if current_user.e_studente %}`
è molto più leggibile di un confronto con una costante dentro l'HTML.

Gli altri decoratori che incontrerete:

```python
@app.route("/pratiche/<int:id>")    # registra la funzione come rotta
@login_required                      # rifiuta se non sei autenticato
@login_manager.user_loader           # registra la funzione come callback
```

Tutti fanno la stessa cosa concettuale: **prendono la tua funzione e la
consegnano a qualcuno che se ne servirà**, eventualmente avvolgendola in
controlli.

---

## 10. Cosa succede quando scrivi `class Utente(db.Model)`

Qui sta il pezzo che rende SQLAlchemy diverso da tutto il resto.

### `db` non è un modulo, è un oggetto

In `app/extensions.py` c'è:

```python
db = SQLAlchemy(model_class=Base)
```

`db` è un **oggetto**, un'istanza della classe `SQLAlchemy`. Ha attributi e
metodi: `db.Model`, `db.session`, `db.create_all()`, `db.init_app(app)`.

`db.Model` è quindi un attributo di quell'oggetto, e quell'attributo **è una
classe**. In Python le classi sono oggetti, quindi possono stare dentro altri
oggetti come qualunque valore. Ereditare da `db.Model` è legittimo.

### La registrazione automatica

Quando Python esegue `class Utente(db.Model):`, non si limita a creare una
classe. `db.Model` porta con sé un meccanismo (tecnicamente una metaclasse)
che al momento della creazione della classe:

1. legge le annotazioni `Mapped[...]` e le chiamate `mapped_column(...)`
2. costruisce un oggetto `Table` che descrive la tabella SQL
3. lo aggiunge a un registro globale chiamato **metadata**
4. sostituisce gli attributi di classe con dei descrittori, così che
   `u.email` restituisca il valore dell'istanza e non l'oggetto colonna

Il punto 4 spiega una cosa che altrimenti confonde. Quando scrivi

```python
class Utente(db.Model):
    email: Mapped[str] = mapped_column(sa.String(120))
```

quella riga sta nel **corpo della classe**, quindi sembra un attributo di
classe condiviso da tutte le istanze. E tecnicamente lo è. Ma `mapped_column`
restituisce un oggetto speciale (un *descrittore*) che intercetta letture e
scritture e le devia sull'istanza. Risultato: `u1.email` e `u2.email` danno
valori diversi, come se fosse un attributo di istanza.

È anche il motivo per cui nei modelli non scrivi mai `__init__`: SQLAlchemy ne
fornisce uno che accetta le colonne come parametri con nome.

```python
u = Utente(email="a@b.it", nome="Leo", cognome="Rossi", ruolo=Ruolo.STUDENTE)
```

Il punto 3 è quello che vi serve per il capitolo 13. Esiste **un registro
unico** di tutte le tabelle, e ci finiscono solo le classi che sono state
**effettivamente eseguite**.

Se un file di modelli non viene mai importato, quelle classi non vengono mai
eseguite, quindi non finiscono nel registro, quindi `db.create_all()` non crea
quelle tabelle — **e non dà nessun errore**. Crea zero tabelle in silenzio.

È il motivo per cui in `create_app()` c'è questa riga:

```python
from app import models  # noqa: F401
```

Non serve a usare `models`: serve a **eseguirlo**, perché le classi si
registrino. Il commento `# noqa: F401` dice agli strumenti di controllo "so
che sembra un import inutilizzato, lascialo stare".

---

## 11. `enums.py`: solo costanti

Questo file è il più semplice del progetto, e conviene guardarlo prima di
`models.py`.

```python
class Ruolo:
    STUDENTE = "STUDENTE"
    DOCENTE = "DOCENTE"
    UFFICIO = "UFFICIO"

    TUTTI = (STUDENTE, DOCENTE, UFFICIO)
```

Non c'è niente di speciale. È una classe usata come **contenitore di nomi**:
non viene mai istanziata, nessuno scrive `Ruolo()`. Serve solo a poter
scrivere `Ruolo.STUDENTE` invece della stringa nuda.

`utente.ruolo` è una **stringa normale**. Il confronto è un confronto fra
stringhe:

```python
if utente.ruolo == Ruolo.STUDENTE:      # confronta "STUDENTE" con "STUDENTE"
```

### Perché non scrivere la stringa e basta

Perché un refuso in una stringa non dà errore:

```python
if utente.ruolo == "STUEDNTE":     # Python non protesta. Risponde False.
```

Il programma non si rompe, semplicemente non funziona, e ci perdi un'ora.
Con la costante:

```python
if utente.ruolo == Ruolo.STUEDNTE:  # AttributeError, e PyCharm lo segna rosso
```

**L'unica disciplina che ti serve** è: mai scrivere le stringhe a mano nel
codice. Sempre `StatoPratica.CHIUSA`, mai `"CHIUSA"`.

### `TUTTI`, `ETICHETTE`, `COLORI`

`TUTTI` è la tupla di tutti i valori, comoda per ciclare (nel seed, in un menù
a tendina). Serve perché su una classe normale non puoi fare `for r in Ruolo`.

`ETICHETTE` e `COLORI` sono dizionari da usare nei template:

```jinja
{{ StatoPratica.ETICHETTE[pratica.stato] }}
{# stampa "Mobilita' in corso" invece di MOBILITA_IN_CORSO #}

<span class="badge bg-{{ StatoPratica.COLORI[pratica.stato] }}">
```

### Come finiscono nel database

Come colonne di testo, con un `CHECK` scritto per esteso in `models.py`:

```python
ruolo: Mapped[str] = mapped_column(sa.String(20), nullable=False)
# e in __table_args__:
sa.CheckConstraint("ruolo IN ('STUDENTE', 'DOCENTE', 'UFFICIO')",
                   name="ck_utente_ruolo"),
```

che produce nel `CREATE TABLE`:

```sql
ruolo VARCHAR(20) NOT NULL,
CONSTRAINT ck_utente_ruolo CHECK (ruolo IN ('STUDENTE','DOCENTE','UFFICIO'))
```

L'alternativa sarebbe il tipo `ENUM` nativo di PostgreSQL:

```sql
CREATE TYPE ruolo AS ENUM ('STUDENTE', 'DOCENTE', 'UFFICIO');
```

Scartata per due motivi. Non è standard SQL, quindi lo schema non girerebbe su
un altro DBMS — ed è proprio l'"astrazione dal DBMS sottostante" che la traccia
raccomanda. E modificarlo è scomodo: togliere o riordinare un valore richiede
di creare un tipo nuovo e convertire tutte le colonne, mentre con il CHECK è un
`ALTER TABLE` di due righe.

C'è anche un vantaggio pratico per l'esame: i valori ammessi si leggono
guardando la tabella, non bisogna andare a cercare la definizione di un tipo
da un'altra parte.

---

## 12. `models.py` pezzo per pezzo

Il file contiene **quattro forme di riga**, ripetute. Se riconosci queste, lo
leggi tutto.

### Forma 1: una colonna

```python
email: Mapped[str] = mapped_column(sa.String(120), nullable=False)
```

Tre pezzi:

- `email` — il nome della colonna nel database e dell'attributo in Python
- `Mapped[str]` — annotazione. Serve a PyCharm e a SQLAlchemy, che da qui
  deduce il tipo SQL se non glielo dici, e la nullabilità
- `mapped_column(...)` — la definizione vera: tipo SQL, vincoli, default

Da `Mapped[str]` senza `| None` SQLAlchemy deduce `NOT NULL`. Il
`nullable=False` esplicito che trovi nel file è ridondante: l'ho lasciato
perché rende il `CREATE TABLE` prevedibile a colpo d'occhio.

Una nota sui default:

```python
data_apertura: Mapped[dt.date] = mapped_column(sa.Date, default=dt.date.today)
```

`dt.date.today` è scritto **senza parentesi**. Stai passando la funzione, non
il suo risultato. Con le parentesi il valore verrebbe calcolato una volta sola
all'avvio del server e tutte le pratiche avrebbero la stessa data.

### Forma 2: una colonna che punta a un'altra tabella

```python
studente_id: Mapped[int] = mapped_column(
    sa.ForeignKey("utente.id", ondelete="RESTRICT"), nullable=False
)
```

`"utente.id"` è `"nome_tabella.nome_colonna"`, **non** il nome della classe.
La classe è `Utente` maiuscola, la tabella è `utente` minuscola. Sono due spazi
di nomi diversi e confonderli è l'errore più frequente.

`ondelete` è la clausola SQL: cosa fa il database se cancelli la riga puntata.
`RESTRICT` la impedisce, `CASCADE` cancella a catena. Nel file `CASCADE` compare
dove il figlio è entità debole: cancellata la pratica spariscono i suoi
Learning Agreement, perché fuori dalla pratica non significano niente.

### Forma 3: la scorciatoia verso l'oggetto puntato

```python
studente: Mapped[Utente] = relationship(
    back_populates="pratiche_come_studente",
    foreign_keys=[studente_id],
)
```

**Non genera nessuna colonna.** La colonna è `studente_id`, che esiste già.
`relationship` è la scorciatoia che percorre quella chiave esterna.

Guardale in coppia, perché è la cosa che confonde di più:

```python
studente_id: Mapped[int]    = mapped_column(sa.ForeignKey("utente.id"))
studente:    Mapped[Utente] = relationship(foreign_keys=[studente_id])
```

Con dati veri:

```python
p = db.session.get(Pratica, 7)

p.studente_id       # 3                    <- il numero scritto nella tabella
p.studente          # <Utente s@s.it>      <- l'oggetto, preso con una SELECT
p.studente.nome     # "Leo"
```

In C++ è come avere sia `int studente_id` sia `Utente* studente`, con la
differenza che il puntatore si risolve da solo la prima volta che lo usi.

Le opzioni che incontrerai:

- `Mapped[list[...]]` significa "molti", `Mapped[Utente]` significa "uno". Da
  questo SQLAlchemy capisce la direzione.
- `back_populates` collega le due direzioni: `pratica.studente` e
  `utente.pratiche_come_studente` sono la stessa relazione vista dai due lati.
  Il nome che passi è quello dell'attributo **sull'altra classe**, e se lo
  sbagli l'errore arriva all'avvio, non alla prima query.
- `foreign_keys=[...]` è obbligatorio quando ci sono più chiavi esterne verso
  la stessa tabella. In `Pratica` ce ne sono quattro verso `utente`, quindi
  SQLAlchemy non può indovinare quale seguire. Dove ce n'è una sola, si omette.
- `uselist=False` nei casi (0,1), per dire "uno solo, non una lista".
- `cascade="all, delete-orphan"` riguarda gli oggetti Python: se togli un
  figlio dalla lista, viene cancellato dal database invece di restare orfano.
  È il gemello lato ORM di `ondelete="CASCADE"`, che agisce lato database.
  Servono entrambi perché coprono percorsi diversi.

### Forma 4: un vincolo, dentro `__table_args__`

```python
__table_args__ = (
    sa.UniqueConstraint("email", name="uq_utente_email"),
    sa.CheckConstraint("crediti > 0", name="ck_corso_interno_crediti"),
    sa.Index("ix_pratica_stato", "stato"),
)
```

È una **tupla** — la virgola dopo l'ultimo elemento è obbligatoria anche con un
solo vincolo, altrimenti Python non la considera una tupla e SQLAlchemy dà un
errore incomprensibile.

Le stringhe dentro `CheckConstraint` sono **SQL puro**: SQLAlchemy le copia nel
`CREATE TABLE` senza interpretarle. Quello che leggi è quello che finisce nel
database. Se sbagli la sintassi non te ne accorgi finché non lanci `init_db`.

I nomi (`name=`) non sono decorativi: senza, PostgreSQL genera nomi automatici
e quando un vincolo viene violato il messaggio d'errore non ti dice quale. Con
i nomi, l'errore è leggibile e puoi anche intercettarlo nel codice per mostrare
un messaggio decente all'utente.

**Due forme SQL ricorrono spesso e conviene riconoscerle a colpo d'occhio.**

*"Se A allora B"* — in SQL non esiste l'operatore di implicazione. Si scrive
`NOT A OR B`, che è logicamente equivalente:

```python
sa.CheckConstraint(
    "NOT (esito = 'RIFIUTATO')"
    " OR (motivazione IS NOT NULL AND length(trim(motivazione)) > 0)",
    name="ck_la_motivazione_se_rifiutato",
),
```

(Le due stringhe una sotto l'altra senza virgola in mezzo si concatenano da
sole: è una comodità di Python per spezzare le stringhe lunghe.)

*"O entrambi o nessuno dei due"* — vero quando sono tutti e due nulli o tutti e
due valorizzati:

```python
sa.CheckConstraint(
    "(verificata_da_id IS NULL) = (pre_partenza_verificata_il IS NULL)",
    name="ck_pratica_verifica_coerente",
),
```

Questa forma nasce dalla traduzione delle relazioni (0,1) in colonne: una
relazione o c'è tutta o non c'è, quindi chiave esterna e attributo devono
comparire insieme. Nel modello concettuale non serviva scriverlo.

*Sui confronti fra date*, la forma è sempre `X IS NULL OR Y IS NULL OR X <= Y`:
senza i due controlli sui NULL, il confronto darebbe NULL appena una delle due
date manca, e il vincolo smetterebbe di dire qualcosa.

**Una cosa importante sui CHECK sullo stato.** Nel file troverai vincoli scritti
solo in una direzione:

```python
# corretto: dallo stato al fatto
"stato NOT IN ('MOBILITA_IN_CORSO', ...) OR data_inizio_effettivo IS NOT NULL"
```

e mai il contrario. Il motivo è che un CHECK viene rivalutato **a ogni modifica
della riga**, non solo quando scrivi quella colonna. Un vincolo del tipo "puoi
valorizzare l'inizio solo se lo stato è PRE_PARTENZA_COMPLETATA" si romperebbe
da solo appena la pratica passa a MOBILITA_IN_CORSO: la data sarebbe ancora lì
ma lo stato no, e l'UPDATE verrebbe rifiutato.

La regola: un CHECK che nomina lo stato è valido solo se la condizione resta
vera anche in tutti gli stati successivi.

### `@property` e `__repr__`

```python
@property
def nome_completo(self) -> str:
    return f"{self.nome} {self.cognome}"

def __repr__(self) -> str:
    return f"<Utente {self.email}>"
```

La prima è calcolata, non memorizzata: non c'è nessuna colonna
`nome_completo`. Si usa senza parentesi.

`__repr__` è il vostro `operator<<`: è quello che il debugger di PyCharm mostra
al posto di `<Utente object at 0x7f8b2c>`. Sembra un dettaglio finché non
passate mezz'ora a capire quale delle quaranta pratiche state guardando.

### Quello che in `models.py` non c'è

I trigger e le viste. Non sono esprimibili con l'ORM e stanno in
`scripts/schema_extra_postgres.sql`, eseguito da `init_db` subito dopo
`create_all()`. Dove un vincolo vive lì, il commento della classe lo dice con
la sigla `[SQL]`.

---

## 13. Come `models.py` si aggancia a Flask

Questa è la parte che nessuno spiega e che serve per non impazzire.

### Il problema dell'import circolare

Il modo ingenuo di scrivere l'applicazione sarebbe questo:

```python
# app/__init__.py
app = Flask(__name__)
db = SQLAlchemy(app)
from app import models      # models importa db da qui
```

```python
# app/models.py
from app import db          # ...e app importa models. Cerchio chiuso.
```

`app/__init__.py` importa `models`, che importa `app/__init__.py`, che non ha
ancora finito di essere eseguito. Python non può risolverlo e vi restituisce
un `ImportError` con un messaggio poco chiaro.

### La soluzione: `extensions.py`

Si mette l'oggetto `db` in un file terzo, che **non importa nulla del vostro
progetto**:

```python
# app/extensions.py
db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()
```

Ora la dipendenza è un albero, non un cerchio:

```
extensions.py            (non importa niente di nostro)
    ^          ^
    |          |
 models.py   __init__.py
    ^          |
    |          |
    +----------+
```

`models.py` importa `extensions`. `__init__.py` importa `extensions` e
`models`. Nessuno importa `__init__.py`. Cerchio rotto.

Sono quattro righe e non le toccherete mai più.

### Ma `db` non sa ancora a quale database parlare

`SQLAlchemy()` viene creato senza applicazione: non conosce l'URL del
database. Il collegamento avviene dopo, dentro `create_app()`:

```python
def create_app(nome_config="dev"):
    app = Flask(__name__)
    app.config.from_object(CONFIGS[nome_config])   # 1. carica la configurazione

    from app.extensions import db, login_manager
    db.init_app(app)                                # 2. collega db a QUESTA app
    login_manager.init_app(app)

    from app import models                          # 3. registra le tabelle

    from app.blueprints.auth import auth_bp         # 4. monta le rotte
    app.register_blueprint(auth_bp, url_prefix="/auth")

    return app
```

Questo schema si chiama **application factory**, e le due fasi (crea l'oggetto
vuoto, poi collegalo a un'applicazione) sono ciò che permette di avere più
applicazioni con configurazioni diverse — una per lo sviluppo, una per i test
— usando gli stessi modelli.

**L'ordine di quelle righe non è negoziabile:**

1. la configurazione prima di tutto, perché `init_app` legge l'URL da lì
2. `init_app` prima dei modelli
3. i modelli prima di `create_all()`, altrimenti il registro è vuoto
4. i blueprint per ultimi, perché usano i modelli

### `db.session`: il blocco di appunti

Dopo `init_app`, `db.session` è utilizzabile ovunque. Non è una connessione:
è una **sessione**, cioè un blocco di appunti che tiene traccia degli oggetti
che hai letto e modificato.

```python
p = db.session.get(Pratica, 7)          # SELECT ... WHERE id = 7
p.stato = StatoPratica.CHIUSA            # nessun SQL: annotato negli appunti
db.session.commit()                      # UPDATE + COMMIT, in una transazione
```

Il `commit()` traduce tutto quello che è cambiato in SQL, nell'ordine giusto,
dentro **un'unica transazione**. Se qualcosa fallisce, `db.session.rollback()`
e non è successo niente. È per questo che le transazioni richieste dalla
traccia non le scrivete a mano: le fa la sessione.

Flask-SQLAlchemy crea una sessione nuova per ogni richiesta HTTP e la chiude
alla fine. Due utenti che navigano contemporaneamente hanno due sessioni
separate e non si disturbano.

### E `init_db`?

```python
# scripts/init_db.py
from app import create_app
from app.extensions import db

app = create_app()
with app.app_context():
    db.create_all()
```

`create_all()` legge il registro delle tabelle e genera tutti i `CREATE TABLE`
per quelle che non esistono ancora. **Non modifica le tabelle esistenti:** se
aggiungete una colonna a un modello, `create_all()` non ve la aggiunge e non
vi avvisa. Durante lo sviluppo, quando cambiate i modelli, si cancella il
database e si rilancia:

```
dropdb overseas && createdb overseas && python -m scripts.init_db
```

`with app.app_context():` serve perché `db` deve sapere a quale applicazione
sta parlando, e fuori da una richiesta HTTP non c'è nessuno a dirglielo. Il
`with` è la struttura Python equivalente al RAII: apre un contesto all'inizio
del blocco e lo chiude all'uscita, anche se salta un'eccezione.

---

## 14. Il viaggio di una richiesta

Mettendo tutto insieme. L'utente clicca su una pratica.

```
1.  Il browser chiede GET /pratiche/7

2.  Flask cerca fra le rotte registrate dai blueprint quella che combacia
    e trova @pratiche_bp.route("/<int:id>")

3.  Flask-SQLAlchemy apre una sessione per questa richiesta

4.  Flask-Login legge il cookie, ne estrae l'id, e chiama la user_loader:
        db.session.get(Utente, int(id_utente))
    Il risultato diventa current_user

5.  @login_required verifica che current_user non sia anonimo

6.  Parte la tua funzione:
        pratica = db.session.get(Pratica, 7)
    -> SELECT * FROM pratica WHERE id = 7
    -> SQLAlchemy costruisce un oggetto Pratica e lo mette nella sessione

7.  Controlli di autorizzazione:
        if pratica.studente_id != current_user.id: abort(403)
    Nessuna query: studente_id e' una colonna, e' gia' in memoria

8.  Il template legge pratica.istituto.nome
    -> SELECT * FROM istituto WHERE id = ...
    La relationship scatta ADESSO, non prima. Si chiama lazy loading, ed e'
    la causa del problema N+1: in un ciclo su 50 pratiche fa 50 query.
    Si risolve con selectinload() nella query iniziale.

9.  render_template produce l'HTML

10. Flask chiude la sessione e spedisce la risposta
```

---

## 15. Gli errori che farete

**`ModuleNotFoundError: No module named 'app'`**
Stai lanciando da dentro `app/` invece che dalla radice del progetto. Oppure
l'interprete di PyCharm non è quello del venv.

**`ImportError: cannot import name 'db' from partially initialized module`**
Import circolare. Qualcuno importa `app/__init__.py` invece di
`app/extensions.py`. È letteralmente il capitolo 13.

**`NameError: name 'Pratica' is not defined`**
Manca `from __future__ import annotations` in cima al file, oppure il
riferimento è dentro un argomento di funzione e va messo fra virgolette.

**`init_db` crea zero tabelle senza errori**
Manca `from app import models` in `create_app()`. Il registro è vuoto.

**`Exception: Missing user_loader or request_loader`**
Un template usa `current_user` ma la callback `@login_manager.user_loader` non
è registrata. Flask-Login non tollera che manchi.

**`IntegrityError: violates check constraint "ck_utente_ruolo"`**
Hai scritto una stringa a mano con un refuso, o hai usato un valore che non
esiste. È il prezzo di avere le costanti invece di un enum vero: l'errore
arriva dal database al `commit()` invece che da Python. La cura è la
disciplina: sempre `Ruolo.STUDENTE`, mai `"STUDENTE"`.

**`AttributeError: 'Pratica' object has no attribute 'stduente'`**
Refuso in *lettura*. Nota che in *scrittura* Python non protesta: crea un
attributo nuovo. Se scrivi `p.stduente = x` non succede niente di visibile e
il dato non arriva nel database.

**`TypeError: __table_args__ value must be a tuple`**
Manca la virgola dopo l'ultimo vincolo.

**`sqlalchemy.exc.ArgumentError: Could not determine join condition`**
Più chiavi esterne verso la stessa tabella e manca `foreign_keys=`.

**Il metodo non funziona e l'errore parla di argomenti**
Hai dimenticato `self` come primo parametro.

**Tutte le pratiche hanno la stessa data di apertura**
Hai scritto `default=dt.date.today()` con le parentesi. Va senza: si passa la
funzione, non il suo risultato calcolato una volta all'avvio.

**Hai cambiato un modello e il database non se ne accorge**
`create_all()` non modifica le tabelle esistenti. Ricrea il database.

---

## In due righe

Un file è un modulo che viene **eseguito**. Le classi sono oggetti creati a
runtime, e `db.Model` le registra in un elenco al momento in cui vengono
eseguite. Da quell'elenco nasce il `CREATE TABLE`. Tutto il resto — la riga
`__future__`, l'esistenza di `extensions.py`, l'import apparentemente inutile
dei modelli — sono conseguenze del fatto che in Python non esiste la
compilazione separata.