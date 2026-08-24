-- ===========================================================================
-- Oggetti di database che l'ORM NON sa esprimere.
-- Eseguito automaticamente da scripts/init_db.py, ma solo su PostgreSQL.
--
-- DA SCRIVERE IN FASE 4, dopo aver definito i modelli.
--
-- REGOLA: ogni istruzione dev'essere IDEMPOTENTE, cioe' rieseguibile senza
-- errori. Usa CREATE OR REPLACE, DROP ... IF EXISTS, CREATE ... IF NOT EXISTS.
-- Lo script viene rilanciato ogni volta che ricrei il database.
-- ===========================================================================


-- ---------------------------------------------------------------------------
-- 1. TRIGGER SULLE TRANSIZIONI DI STATO
--    Impedisce i salti di fase e i ritorni indietro non previsti dal
--    diagramma degli stati. Deve dire esattamente le stesse cose del
--    dizionario TRANSIZIONI_AMMESSE in app/enums.py.
--
-- CREATE OR REPLACE FUNCTION verifica_transizione_stato() ...
-- ---------------------------------------------------------------------------


-- ---------------------------------------------------------------------------
-- 2. TRIGGER SULLA VERIFICA PRE-PARTENZA
--    La fase pre-partenza si registra solo se il Learning Agreement risulta
--    approvato e c'e' almeno un esame mappato.
--    E' una regola su TRE tabelle: un CHECK non puo' esprimerla, perche'
--    vede solo la riga che sta controllando.
-- ---------------------------------------------------------------------------


-- ---------------------------------------------------------------------------
-- 3. TRIGGER SULLA CHIUSURA
--    Si chiude solo se il Transcript of Records e' stato caricato e non
--    restano esami in attesa di riconoscimento.
-- ---------------------------------------------------------------------------


-- ---------------------------------------------------------------------------
-- 4. TRIGGER SULLA DATA DI DECISIONE
--    Imposta automaticamente la data quando l'esito cambia da 'in_attesa'.
--    Cosi' la data non puo' essere dimenticata ne' falsificata dal codice.
-- ---------------------------------------------------------------------------


-- ---------------------------------------------------------------------------
-- 5. INDICE UNICO PARZIALE
--    "una sola versione corrente per tipo di documento".
--    Un UNIQUE normale non basta: il vincolo deve valere SOLO sulle righe
--    con corrente = true. E' un buon esempio da citare in relazione, perche'
--    mostra un vincolo che l'ORM non esprime.
--
-- CREATE UNIQUE INDEX IF NOT EXISTS uq_documento_corrente
--     ON documento (pratica_id, tipo) WHERE corrente;
-- ---------------------------------------------------------------------------


-- ---------------------------------------------------------------------------
-- 6. VISTA: pratiche incomplete
--    Incapsula una delle query piu' frequenti citate dalla traccia.
-- ---------------------------------------------------------------------------


-- ---------------------------------------------------------------------------
-- 7. VISTA MATERIALIZZATA: statistiche del cruscotto
--    I conteggi aggregati non devono essere in tempo reale. Documenta la
--    politica di aggiornamento: REFRESH MATERIALIZED VIEW ...
-- ---------------------------------------------------------------------------


-- ---------------------------------------------------------------------------
-- 8. RUOLI E PRIVILEGI
--    L'applicazione non deve MAI collegarsi come superutente.
--    Principio del privilegio minimo: nessun GRANT ALL.
--    Nota: niente DELETE per l'applicazione. I dati amministrativi non si
--    cancellano, si disattivano.
--
-- CREATE ROLE overseas_app LOGIN PASSWORD 'cambiami';
-- GRANT CONNECT ON DATABASE overseas TO overseas_app;
-- GRANT USAGE ON SCHEMA public TO overseas_app;
-- GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO overseas_app;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO overseas_app;
-- ---------------------------------------------------------------------------
