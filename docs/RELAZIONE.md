# Relazione di progetto — Piattaforma Overseas

> **Scheletro della relazione, da riempire man mano.**
>
> La struttura qui sotto è **esattamente** quella raccomandata dalla docente:
> non cambiare l'ordine e non saltare sezioni.
>
> **Scrivi ogni sezione quando fai la fase corrispondente, non alla fine.**
> Questa è la singola regola che vi farà risparmiare più tempo. La sezione 3
> si scrive nei giorni 3–4, quando lo schema è fresco in testa; ricostruire a
> memoria al giorno 13 costa il triplo.
>
> Alla fine si esporta in **un unico PDF**.
>
> Promemoria costante: la parola che ricorre più spesso nella traccia è
> **motivare**. Descrivere cosa avete fatto vale poco; spiegare perché lo
> avete fatto così vale il voto.

---

## 1. Introduzione

*(Da scrivere per ultima, anche se sta per prima. Fase 14.)*

- Descrizione ad alto livello dell'applicazione, due o tre paragrafi.
- Contesto del programma Overseas e problema che l'applicazione risolve.
- Struttura del documento: cosa il lettore troverà nelle sezioni seguenti.

---

## 2. Funzionalità principali

*(Scrivere durante la Fase 7, aggiornando man mano che le implementate.)*

- Descrizione delle funzionalità, organizzata per ruolo oppure per fase della
  mobilità. Scegliete un criterio e mantenetelo.
- Come avete interpretato lo spunto della traccia, e cosa avete aggiunto di
  vostro.
- Qualche schermata a supporto, numerata e referenziata nel testo.

Da coprire, i dieci requisiti minimi: gestione utenti e ruoli; istituti
ospitanti; creazione pratiche; caricamento e valutazione del Learning
Agreement; verifica pre-partenza; mobilità in corso; modifiche al LA;
Transcript of Records; riconoscimento esami; chiusura.

---

## 3. Progettazione concettuale e logica

*(Scrivere alla fine della Fase 3, prima di toccare il codice. È la sezione
più pesante e quella su cui si guadagna di più.)*

### 3.1 Schema concettuale

- Diagramma ER **nella notazione grafica del Modulo 1 del corso**. Usare una
  notazione diversa è un errore che si paga.
- Descrizione delle entità e dei loro attributi.
- Descrizione delle relazioni, con cardinalità minime e massime.
- Scelta sulla gestione dei ruoli utente (generalizzazione, attributo, o
  entità Ruolo separata) e **perché**.
- Trattamento del mapping degli esami: è il punto concettualmente più
  delicato, spiegatelo bene.

### 3.2 Vincoli non esprimibili nello schema ER

Elenco delle regole che il diagramma non riesce a rappresentare. Per ciascuna:
formulazione precisa in italiano, livello a cui verrà garantita (CHECK,
chiave, trigger, transazione, codice), e motivo della scelta.

### 3.3 Ristrutturazione

Cosa avete cambiato passando dal concettuale al logico e perché: eliminazione
delle generalizzazioni, reificazione delle relazioni molti a molti,
eliminazione degli attributi multivalore, scelta degli identificatori.

### 3.4 Schema logico

Lo schema relazionale risultante, relazione per relazione, con chiavi primarie
e chiavi esterne. Politica di integrità referenziale su ogni chiave esterna,
con motivazione.

### 3.5 Dipendenze funzionali e normalizzazione

**Questa sottosezione va svolta per esteso, non liquidata con una frase.**

- Dipendenze funzionali di ogni relazione.
- Copertura canonica, con i passaggi: riduzione dei membri destri,
  eliminazione degli attributi estranei, eliminazione delle ridondanze.
- Verifica di 1NF, 2NF, 3NF e BCNF, una relazione alla volta.
- Eventuali decomposizioni, con verifica di join senza perdita e conservazione
  delle dipendenze.
- Eventuali denormalizzazioni **consapevoli**, con la loro motivazione.

---

## 4. Query principali

*(Scrivere durante le Fasi 7 e 10, copiando da `app/queries.py` e da
`docs/query_principali.sql`.)*

Quattro o cinque interrogazioni, non dieci `SELECT` banali. Scegliete quelle
che mostrano join, aggregazioni, sottointerrogazioni, viste.

Per ciascuna: cosa serve a fare, perché è interessante, come l'avete resa
efficiente, e l'SQL in una sintassi leggibile.

Suggerimento: le query scritte in Expression Language si possono riportare
accanto all'SQL realmente generato, che si legge attivando `SQL_ECHO=1`.
Mostrare i due accostati dimostra che sapete cosa succede sotto.

---

## 5. Principali scelte progettuali

*(Scrivere man mano, attingendo a `docs/decisioni.md`.)*

### 5.1 Politiche di integrità

Dove vive ciascuna regola e perché: vincoli di dominio, chiavi, integrità
referenziale, trigger, transazioni, controlli applicativi. Il principio
adottato e le sue conseguenze.

### 5.2 Ruoli e politiche di autorizzazione

I tre ruoli applicativi, i due livelli di controllo (ruolo e appartenenza),
i ruoli e i privilegi definiti a livello di DBMS, e la protezione dei dati
personali e dei documenti caricati.

### 5.3 Uso di indici e viste

Ogni indice con la query che lo giustifica. Viste e viste materializzate, con
la politica di aggiornamento. Se avete misurato un prima/dopo, riportatelo.

### 5.4 Gestione degli allegati

Dove risiedono i file e perché, quali metadati sono nel database, come è
protetto l'accesso, eventuale storico delle versioni.

### 5.5 Stati della pratica

Il diagramma degli stati, le transizioni ammesse, e come sono imposte.

### 5.6 Transazioni e livelli di isolamento

Quali operazioni sono transazionali e perché. Dove avete alzato il livello di
isolamento oltre il `READ COMMITTED` predefinito di PostgreSQL, e quali
anomalie state evitando.

---

## 6. Ulteriori informazioni

- DBMS scelto e motivazione.
- Perché ORM per il grosso ed Expression Language per le query analitiche.
- Librerie utilizzate e ruolo di ciascuna.
- Struttura del codice e organizzazione in moduli e blueprint.
- Istruzioni per l'installazione e l'avvio.
- Limiti noti e possibili sviluppi futuri. Dichiararli è un punto di forza,
  non di debolezza: mostra che sapete cosa manca.

---

## Appendice — Contributo al progetto

*(Richiesta esplicitamente dalla traccia. Non ometterla e non liquidarla con
una riga.)*

Per ciascun componente del gruppo: a quali parti del design ha contribuito, e
quali parti dello sviluppo ha realizzato.

Tenete aggiornato `docs/decisioni.md` durante il lavoro: ricostruire questa
appendice a memoria alla fine è impreciso e si vede.
