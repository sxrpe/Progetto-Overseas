# Diario delle decisioni progettuali

> **A cosa serve.** Ogni volta che prendete una decisione non ovvia,
> annotatela qui in tre righe. Al momento di scrivere la sezione 5 della
> relazione ("Principali scelte progettuali") avrete già tutto il materiale,
> invece di dover ricostruire a memoria perché avevate fatto una certa cosa
> nove giorni prima.
>
> Costa trenta secondi a decisione e fa risparmiare almeno mezza giornata.

**Formato:** data, decisione, alternative scartate, motivo, chi ha deciso.

---

## Decisioni già prese (Fase 0)

**2026-xx-xx — DBMS: PostgreSQL**
Alternative: SQLite, MySQL.
Motivo: è quello consigliato dalla docente ed è l'unico che permette trigger
in PL/pgSQL, viste materializzate, indici unici parziali e ruoli con GRANT.
Con SQLite metà degli aspetti raccomandati dalla traccia sarebbero
indimostrabili.

**2026-xx-xx — Accesso ai dati: ORM (Flask-SQLAlchemy) + Expression Language**
Alternative: solo Core con Expression Language; SQL testuale.
Motivo: la traccia chiede "Expression Language **o** ORM", quindi sono
alternative e non un elenco. L'ORM copre il ciclo di vita delle entità con
molto meno codice; le query analitiche restano in `select()`, che è
Expression Language e mantiene l'indipendenza dal dialetto SQL. SQL testuale
solo dove la versione astratta sarebbe illeggibile, e ogni caso è motivato.

**2026-xx-xx — Schema definito nei modelli ORM, non in un DDL scritto a mano**
Alternative: script SQL come fonte di verità, con modelli che lo rispecchiano.
Motivo: definizione unica di ogni colonna, quindi nessun rischio di
disallineamento fra schema logico e schema fisico. Gli oggetti che l'ORM non
esprime (trigger, viste, indici parziali, ruoli) stanno in un file SQL
dedicato e versionato.

**2026-xx-xx — Front-end: Bootstrap 5 da CDN**
Alternative: W3.CSS, CSS scritto a mano.
Motivo: la traccia lo cita esplicitamente fra i framework ammessi, è il più
diffuso e quindi il più facile da cercare, e copre con classi già pronte tutto
ciò che serve. Nessun JavaScript applicativo: la traccia dice che non è
richiesto e non incide sulla valutazione.

**2026-xx-xx — Valori enumerati come VARCHAR + CHECK, non come ENUM nativo**
Alternative: tipo `ENUM` di PostgreSQL, tabella di lookup.
Motivo: un ENUM nativo è scomodissimo da modificare dopo la creazione; un
VARCHAR con CHECK è ispezionabile, si modifica con un ALTER e resta portabile.

---

## Da qui in avanti, aggiungete voi

**2026-xx-xx — [decisione]**
Alternative:
Motivo:
Deciso da:

---

## Registro dei contributi

> Per l'appendice della relazione, richiesta esplicitamente. Aggiornate man
> mano: alla fine ricostruirlo a memoria è impreciso e si nota.

**Nome 1**
- Progettazione:
- Sviluppo:
- Documentazione:

**Nome 2**
- Progettazione:
- Sviluppo:
- Documentazione:

**Nome 3**
- Progettazione:
- Sviluppo:
- Documentazione:
