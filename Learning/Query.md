# Query in SQLAlchemy 2.0 — foglio di riferimento

## L'anatomia

Una query si compone a pezzi, e **non viene eseguita** finché non la chiudi.

```python
sa.select(Pratica)                                   # cosa voglio
  .where(Pratica.studente_id == current_user.id)     # filtro         -> WHERE
  .options(selectinload(Pratica.istituto))           # carica anche...
  .order_by(Pratica.anno_accademico.desc())          # ordine         -> ORDER BY
  .limit(10)                                         # quante         -> LIMIT
```

Ogni pezzo restituisce una nuova query, quindi puoi anche costruirla a rate:

```python
q = sa.select(Pratica).where(Pratica.stato == StatoPratica.CHIUSA)
if anno:
    q = q.where(Pratica.anno_accademico == anno)     # riassegni, non modifichi
pratiche = db.session.scalars(q).all()
```

## Come si chiude

```python
db.session.get(Pratica, 7)              # per chiave primaria  -> oggetto o None
db.session.scalar(q)                    # una cosa sola        -> oggetto o None
db.session.scalars(q).all()             # un elenco            -> lista di oggetti
db.session.execute(q).all()             # piu' colonne         -> lista di tuple
```

Nel 90% dei casi ti servono le prime tre.

## I confronti

```python
Pratica.stato == StatoPratica.CHIUSA          # =
Pratica.stato != StatoPratica.CHIUSA          # <>
Pratica.anno_accademico >= 2025               # >=

Pratica.stato.in_([StatoPratica.APERTA,
                   StatoPratica.MOBILITA_IN_CORSO])   # IN (...)
Pratica.stato.not_in([...])                            # NOT IN

Pratica.chiusa_il.is_(None)                   # IS NULL      <- non "== None"
Pratica.chiusa_il.is_not(None)                # IS NOT NULL

Istituto.nome.ilike(f"%{cerca}%")             # LIKE senza distinzione maiuscole
Pratica.anno_accademico.between(2020, 2025)   # BETWEEN
```

Attenzione a `is_(None)`: con `== None` funziona lo stesso ma gli strumenti di controllo protestano, e `!= None` su alcune versioni non traduce come ti aspetti. Usa `is_` / `is_not`.

## Più condizioni

Più `.where()` in fila si sommano con AND:

```python
.where(Pratica.studente_id == 5)
.where(Pratica.stato == StatoPratica.CHIUSA)     # AND
```

Per l'OR serve la forma esplicita:

```python
from sqlalchemy import and_, or_

.where(or_(Pratica.stato == StatoPratica.APERTA,
           Pratica.stato == StatoPratica.MOBILITA_IN_CORSO))
```

## Ordinamento

```python
.order_by(Pratica.codice_pratica)                    # crescente
.order_by(Pratica.anno_accademico.desc())            # decrescente
.order_by(Pratica.anno_accademico.desc(),
          Pratica.codice_pratica)                    # due criteri
```

Il `.desc()` sta sulla colonna, non sull'`order_by`.

## Caricamento anticipato

```python
.options(selectinload(Pratica.istituto))                    # un livello

.options(selectinload(LearningAgreement.corsi_esterni)      # due livelli
         .selectinload(CorsoEsterno.esame))
```

Regola unica: **`selectinload` sempre**. Su molti-a-uno è equivalente a `joinedload`, su uno-a-molti è meglio.

## Filtrare su una tabella collegata

Se il filtro tocca un'altra tabella serve la JOIN:

```python
# le pratiche dirette in Cile
sa.select(Pratica)
  .join(Pratica.istituto)
  .where(Istituto.paese == "Cile")
```

`.join()` serve per **filtrare o ordinare**, `.options()` per **caricare**. Sono due cose diverse e spesso servono insieme.

## Contare e raggruppare

```python
from sqlalchemy import func

# quante pratiche per stato -> i contatori del cruscotto
righe = db.session.execute(
    sa.select(Pratica.stato, func.count())
      .group_by(Pratica.stato)
).all()
# [ ("APERTA", 3), ("CHIUSA", 21), ... ]

conteggi = dict(righe)          # comodo per il template
```

Qui `execute` e non `scalars`, perché due colonne servono davvero.

Un conteggio secco:

```python
quante = db.session.scalar(
    sa.select(func.count()).select_from(Pratica)
      .where(Pratica.docente_id == current_user.id)
      .where(Pratica.stato == StatoPratica.ATTESA_APPROVAZIONE_LA)
)
```

## Leggere una vista

Le viste non sono classi, quindi si interrogano con SQL grezzo:

```python
righe = db.session.execute(
    sa.text("SELECT pratica_id, codice_pratica FROM v_pratiche_pronte_per_chiusura")
).all()

for r in righe:
    print(r.codice_pratica)     # si accede per NOME di colonna
```

Con parametri, **sempre così**, mai concatenando:

```python
db.session.execute(
    sa.text("SELECT * FROM v_stato_riconoscimento_pratica WHERE pratica_id = :id"),
    {"id": id_pratica},
)
```

## Scrivere

```python
# creare
pratica = Pratica(codice_pratica="OV-2025-014", anno_accademico=2025,
                  studente_id=current_user.id, docente_id=3, istituto_id=1)
db.session.add(pratica)
db.session.commit()             # solo ORA parte l'INSERT
# dopo il commit, pratica.id e' valorizzato

# modificare: nessun metodo, si assegna e basta
pratica.stato = StatoPratica.ATTESA_APPROVAZIONE_LA
db.session.commit()

# cancellare
db.session.delete(corso)
db.session.commit()
```

Niente `save()`, niente `update()`. La sessione tiene traccia degli oggetti che hai caricato e al `commit()` traduce le differenze in `UPDATE`.

## Lo schema per ogni scrittura

Tutti i tuoi CHECK e i tuoi trigger scattano al `commit()`. Vanno catturati:

```python
try:
    pratica.stato = StatoPratica.ATTESA_APPROVAZIONE_LA
    db.session.commit()
    flash("Learning Agreement inviato al docente.", "success")
except sa.exc.IntegrityError:
    db.session.rollback()
    flash("Operazione non consentita nello stato attuale.", "danger")
except sa.exc.DatabaseError as errore:
    db.session.rollback()
    flash(str(errore.orig).split("\n")[0], "danger")

return redirect(url_for("pratiche.dettaglio", id_pratica=pratica.id))
```

Tre cose importanti:

**Il `rollback()` non è opzionale.** Senza, la sessione resta in errore e ogni query successiva della stessa richiesta fallisce con un messaggio che non c'entra.

**`IntegrityError`** copre CHECK, UNIQUE e chiavi esterne. **`DatabaseError`** è più larga e prende anche le eccezioni sollevate dai tuoi trigger con `RAISE EXCEPTION`.

**`errore.orig`** è l'eccezione originale di psycopg, e la sua prima riga è il messaggio che hai scritto tu in PL/pgSQL. È il modo per far arrivare all'utente "transizione non ammessa: ..." invece di un testo generico.

## Le tre regole che valgono più della sintassi

**Il filtro di sicurezza sta nella query.** `.where(Pratica.studente_id == current_user.id)`. Caricare tutto e nascondere in Jinja non è un filtro.

**Mai concatenare un valore nella stringa SQL.** Con `select()` non succede mai; con `sa.text()` usa `:nome` e il dizionario.

**Se il template segue una relazione, mettila in `.options()`.** Regola meccanica: apri il template, cerca ogni punto che attraversa una relazione, e assicurati che ci sia il `selectinload` corrispondente.