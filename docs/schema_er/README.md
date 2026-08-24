# Schema Entità-Relazione

Qui dentro vanno i file del diagramma ER e dello schema logico.

## Cosa mettere in questa cartella

- il **sorgente** del diagramma (il file modificabile dello strumento usato)
- l'**esportazione in PNG o PDF**, quella che finirà nella relazione
- eventuali versioni intermedie, se volete tenere traccia di come è evoluto

Nominate i file in modo che l'ordine sia chiaro: `er_v1.png`, `er_finale.png`,
`schema_logico.png`.

## La regola che conta

**Il diagramma deve usare la notazione grafica introdotta nel Modulo 1 del
corso.** È un requisito esplicito della traccia, non uno stile a scelta. Usare
la notazione di un altro corso o di uno strumento generico è un errore che si
paga in sede di valutazione.

Prima di disegnare, riaprite le slide del Modulo 1 e verificate come si
rappresentano: cardinalità, partecipazione obbligatoria e facoltativa,
identificatori, generalizzazioni (totale/parziale, esclusiva/sovrapposta),
attributi composti e multivalore.

## Strumenti

Va bene qualunque cosa produca un diagramma leggibile una volta stampato in
bianco e nero. Anche disegnato a mano e fotografato bene, se la fotografia è
nitida e dritta — ma un file vettoriale è più facile da correggere quando lo
schema cambia, e cambierà.

## Cosa serve, in totale

1. **Schema concettuale (ER)** — entità, relazioni, cardinalità, attributi.
2. **Schema ristrutturato** — dopo l'eliminazione delle generalizzazioni e la
   reificazione delle relazioni molti a molti. Va mostrato accanto al primo:
   il confronto rende visibile il ragionamento.
3. **Schema logico** — le relazioni con chiavi primarie ed esterne. Può essere
   testuale invece che grafico.
4. **Diagramma degli stati della pratica** — non è richiesto esplicitamente,
   ma è uno dei modi più efficaci per mostrare che la logica è stata pensata e
   non improvvisata. Costa dieci minuti.

## Coerenza

Lo schema che finisce nella relazione deve corrispondere al database
realmente implementato. Se in Fase 4 cambiate qualcosa nei modelli, tornate
qui e aggiornate il diagramma **subito**: presentare uno schema che non
corrisponde al codice consegnato è uno degli errori più gravi e più facili da
individuare per chi corregge.
