-- ---------------------------------------------------------------------------
-- Oggetti di database che l'ORM non esprime: trigger, viste, viste
-- materializzate, indici particolari, ruoli.
--
-- Eseguito automaticamente da scripts/init_db.py quando il DBMS e' PostgreSQL.
-- Ogni istruzione e' idempotente: il file si puo' rieseguire senza errori.
-- ---------------------------------------------------------------------------


-- ===========================================================================
-- 1. TRIGGER: transizioni di stato ammesse
--    Il ciclo di vita della pratica e' un grafo: qui impediamo i salti di
--    fase e i ritorni indietro non previsti, a livello di database, cosi'
--    la regola vale anche per chi scrive direttamente in SQL.
-- ===========================================================================
CREATE OR REPLACE FUNCTION verifica_transizione_stato()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.stato = OLD.stato THEN
        RETURN NEW;
    END IF;

    IF NOT (
        (OLD.stato = 'creata'                  AND NEW.stato = 'attesa_approvazione_la')
     OR (OLD.stato = 'attesa_approvazione_la'  AND NEW.stato IN ('creata', 'pre_partenza_completata'))
     OR (OLD.stato = 'pre_partenza_completata' AND NEW.stato = 'mobilita_in_corso')
     OR (OLD.stato = 'mobilita_in_corso'       AND NEW.stato = 'in_riconoscimento_esami')
     OR (OLD.stato = 'in_riconoscimento_esami' AND NEW.stato = 'chiusa')
    ) THEN
        RAISE EXCEPTION 'Transizione di stato non ammessa: % -> %', OLD.stato, NEW.stato;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_transizione_stato ON pratica;
CREATE TRIGGER trg_transizione_stato
    BEFORE UPDATE OF stato ON pratica
    FOR EACH ROW EXECUTE FUNCTION verifica_transizione_stato();


-- ===========================================================================
-- 2. TRIGGER: la fase pre-partenza richiede il Learning Agreement approvato
--    Regola che coinvolge due tabelle: non esprimibile con un CHECK.
-- ===========================================================================
CREATE OR REPLACE FUNCTION verifica_pre_partenza()
RETURNS TRIGGER AS $$
DECLARE
    documenti_approvati INTEGER;
    esami_presenti      INTEGER;
BEGIN
    IF NEW.stato <> 'pre_partenza_completata' THEN
        RETURN NEW;
    END IF;

    SELECT COUNT(*) INTO documenti_approvati
    FROM documento
    WHERE pratica_id = NEW.id
      AND tipo = 'learning_agreement'
      AND esito = 'approvato';

    IF documenti_approvati = 0 THEN
        RAISE EXCEPTION 'Pre-partenza non registrabile: Learning Agreement non approvato.';
    END IF;

    SELECT COUNT(*) INTO esami_presenti FROM esame_mappato WHERE pratica_id = NEW.id;
    IF esami_presenti = 0 THEN
        RAISE EXCEPTION 'Pre-partenza non registrabile: nessun esame mappato.';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_pre_partenza ON pratica;
CREATE TRIGGER trg_pre_partenza
    BEFORE UPDATE OF stato ON pratica
    FOR EACH ROW EXECUTE FUNCTION verifica_pre_partenza();


-- ===========================================================================
-- 3. TRIGGER: la chiusura richiede Transcript caricato e riconoscimento finito
-- ===========================================================================
CREATE OR REPLACE FUNCTION verifica_chiusura()
RETURNS TRIGGER AS $$
DECLARE
    transcript_presenti INTEGER;
    esami_pendenti      INTEGER;
BEGIN
    IF NEW.stato <> 'chiusa' THEN
        RETURN NEW;
    END IF;

    SELECT COUNT(*) INTO transcript_presenti
    FROM documento
    WHERE pratica_id = NEW.id AND tipo = 'transcript_of_records';

    IF transcript_presenti = 0 THEN
        RAISE EXCEPTION 'Chiusura non consentita: Transcript of Records mancante.';
    END IF;

    SELECT COUNT(*) INTO esami_pendenti
    FROM esame_mappato
    WHERE pratica_id = NEW.id AND esito = 'in_attesa';

    IF esami_pendenti > 0 THEN
        RAISE EXCEPTION 'Chiusura non consentita: % esami non ancora riconosciuti.', esami_pendenti;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_chiusura ON pratica;
CREATE TRIGGER trg_chiusura
    BEFORE UPDATE OF stato ON pratica
    FOR EACH ROW EXECUTE FUNCTION verifica_chiusura();


-- ===========================================================================
-- 4. TRIGGER: data della decisione registrata automaticamente
-- ===========================================================================
CREATE OR REPLACE FUNCTION imposta_data_decisione()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.esito <> OLD.esito AND NEW.esito <> 'in_attesa' AND NEW.deciso_il IS NULL THEN
        NEW.deciso_il := NOW();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_data_decisione_documento ON documento;
CREATE TRIGGER trg_data_decisione_documento
    BEFORE UPDATE OF esito ON documento
    FOR EACH ROW EXECUTE FUNCTION imposta_data_decisione();

DROP TRIGGER IF EXISTS trg_data_decisione_esame ON esame_mappato;
CREATE TRIGGER trg_data_decisione_esame
    BEFORE UPDATE OF esito ON esame_mappato
    FOR EACH ROW EXECUTE FUNCTION imposta_data_decisione();


-- ===========================================================================
-- 5. INDICE PARZIALE: una sola versione corrente per tipo di documento
--    Un UNIQUE normale non basta, perche' deve valere solo sulle righe
--    correnti. PostgreSQL permette l'indice unico parziale.
-- ===========================================================================
CREATE UNIQUE INDEX IF NOT EXISTS uq_documento_corrente
    ON documento (pratica_id, tipo)
    WHERE corrente;


-- ===========================================================================
-- 6. VISTA: pratiche incomplete, cioe' senza Learning Agreement approvato
--    Incapsula una delle query piu' frequenti citate dalla traccia.
-- ===========================================================================
CREATE OR REPLACE VIEW v_pratiche_incomplete AS
SELECT p.id,
       p.anno_accademico,
       p.stato,
       u.cognome || ' ' || u.nome AS studente,
       i.nome                     AS istituto,
       i.paese
FROM pratica  p
JOIN utente   u ON u.id = p.studente_id
JOIN istituto i ON i.id = p.istituto_id
WHERE p.stato <> 'chiusa'
  AND NOT EXISTS (
        SELECT 1 FROM documento d
        WHERE d.pratica_id = p.id
          AND d.tipo  = 'learning_agreement'
          AND d.esito = 'approvato'
  );


-- ===========================================================================
-- 7. VISTA MATERIALIZZATA: statistiche del cruscotto
--    I conteggi aggregati non devono essere in tempo reale: si ricalcolano
--    con  REFRESH MATERIALIZED VIEW mv_statistiche_mobilita;
-- ===========================================================================
DROP MATERIALIZED VIEW IF EXISTS mv_statistiche_mobilita;
CREATE MATERIALIZED VIEW mv_statistiche_mobilita AS
SELECT i.paese,
       p.anno_accademico,
       COUNT(*)                                        AS totale_pratiche,
       COUNT(*) FILTER (WHERE p.stato = 'chiusa')      AS pratiche_chiuse
FROM pratica  p
JOIN istituto i ON i.id = p.istituto_id
GROUP BY i.paese, p.anno_accademico;

CREATE INDEX IF NOT EXISTS ix_mv_statistiche_paese
    ON mv_statistiche_mobilita (paese);


-- ===========================================================================
-- 8. RUOLI E PRIVILEGI
--    L'applicazione non deve mai collegarsi come superutente.
--    Scommentare dopo aver creato l'utente overseas_app nel DBMS.
-- ===========================================================================
-- CREATE ROLE overseas_app LOGIN PASSWORD 'cambiami';
-- GRANT CONNECT ON DATABASE overseas TO overseas_app;
-- GRANT USAGE ON SCHEMA public TO overseas_app;
-- GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO overseas_app;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO overseas_app;
-- -- Nessun DELETE: i dati amministrativi non si cancellano, si disattivano.
--
-- CREATE ROLE overseas_report LOGIN PASSWORD 'cambiami';
-- GRANT CONNECT ON DATABASE overseas TO overseas_report;
-- GRANT USAGE ON SCHEMA public TO overseas_report;
-- GRANT SELECT ON v_pratiche_incomplete, mv_statistiche_mobilita TO overseas_report;
