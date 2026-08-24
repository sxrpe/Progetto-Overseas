# Checklist di collaudo

> Da percorrere nella **Fase 13**, prima della relazione e prima del video.
> Segnate ogni riga solo quando l'avete davvero provata.
>
> Consiglio: **collaudo incrociato**. Ognuno prova l'area scritta da un altro.
> Si trova il triplo dei problemi, perché chi ha scritto una funzione tende a
> usarla nel modo in cui l'ha pensata.

---

## 1. Flusso completo

- [ ] Percorso lineare, dalla creazione alla chiusura, con i tre account
- [ ] Ogni passaggio di stato avviene nel momento giusto
- [ ] Nessun intervento manuale sul database durante il percorso

## 2. Casi non lineari

- [ ] Learning Agreement rifiutato con motivazione, poi corretto e approvato
- [ ] Modifica al LA proposta e approvata
- [ ] Modifica al LA proposta e **rifiutata**, con ripristino del mapping precedente
- [ ] Due modifiche successive sulla stessa pratica
- [ ] Esami parzialmente riconosciuti (alcuni sì, alcuni no)
- [ ] Studente con due pratiche in anni accademici diversi
- [ ] Pratica chiusa: diventa di sola lettura per tutti e tre i ruoli

## 3. I dieci requisiti minimi

Ognuno deve essere dimostrabile con una sequenza concreta di clic.
Se non è dimostrabile, non è implementato.

- [ ] 1. Gestione utenti e ruoli
- [ ] 2. Gestione istituti ospitanti
- [ ] 3. Creazione pratiche di mobilità
- [ ] 4. Caricamento e valutazione del Learning Agreement
- [ ] 5. Verifica pre-partenza
- [ ] 6. Gestione della mobilità in corso (date effettive)
- [ ] 7. Modifiche al Learning Agreement
- [ ] 8. Caricamento del Transcript of Records
- [ ] 9. Riconoscimento degli esami
- [ ] 10. Chiusura della pratica

## 4. Permessi

- [ ] Studente: cambiando l'id nell'URL non vede la pratica di un altro
- [ ] Studente: non vede pratiche altrui in nessun elenco
- [ ] Docente: non vede pratiche di cui non è referente
- [ ] Docente: non può decidere su pratiche non sue
- [ ] Route protette inaccessibili senza autenticazione
- [ ] Documenti non scaricabili da chi non ha diritto
- [ ] Comandi non permessi: rifiutati anche inviando la richiesta a mano

## 5. Vincoli e integrità (provare **direttamente in SQL**)

- [ ] Transizione di stato illegale: respinta dal trigger
- [ ] Chiusura senza Transcript: respinta
- [ ] Pre-partenza senza LA approvato: respinta
- [ ] Voto fuori intervallo: respinto dal CHECK
- [ ] Rifiuto senza motivazione: respinto dal CHECK
- [ ] Data di partenza precedente all'arrivo: respinta
- [ ] Operazione composta interrotta a metà: nessun dato parziale resta

Conservate gli esiti: sono ottimo materiale per la sezione 5.1 della relazione.

## 6. Casi limite

- [ ] Campi vuoti e campi con soli spazi
- [ ] Testi molto lunghi
- [ ] Caratteri accentati e speciali nei nomi e nei titoli
- [ ] Date implausibili: futuro remoto, passato remoto, invertite
- [ ] Crediti negativi o nulli
- [ ] File non PDF, file troppo grande, file vuoto, file senza estensione
- [ ] Doppio invio dello stesso form
- [ ] Pulsanti avanti/indietro del browser dopo un'azione
- [ ] Sessione scaduta durante la compilazione

## 7. Interfaccia

- [ ] Ogni elenco vuoto mostra un messaggio utile, non una pagina bianca
- [ ] Gli errori di validazione compaiono accanto al campo sbagliato
- [ ] I dati già inseriti sono ripresentati dopo un errore
- [ ] Lo stato della pratica è sempre nella stessa posizione
- [ ] Terminologia coerente fra interfaccia, database e relazione
- [ ] Leggibile a finestra stretta (durante il video potrebbe non essere a
      schermo intero)

## 8. Codice e consegna

- [ ] Nessuna credenziale scritta nel codice
- [ ] Nessuna stampa di debug rimasta
- [ ] Nessun codice morto
- [ ] `requirements.txt` completo: verificato in un ambiente virtuale nuovo
- [ ] Il progetto parte da zero in una cartella pulita, seguendo solo il README
- [ ] Nessuna query a cascata sulle pagine di elenco (verificare con `SQL_ECHO=1`)
