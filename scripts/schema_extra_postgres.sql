-- ===========================================================================
--  Vincoli, trigger e viste non esprimibili con l'ORM
-- ===========================================================================
--  QUANDO VIENE ESEGUITO
--      Da scripts/init_db.py, subito dopo db.create_all().
--
--  Un vincolo CHECK vede una sola riga di una sola tabella, nella sua
--  versione nuova. Tutto cio' che ha bisogno di:
--      - leggere un'altra tabella
--      - conoscere il valore PRECEDENTE della riga
--      - contare righe correlate
--  esce dalla portata dell'ORM e finisce qui.
--
--  Ogni oggetto è preceduto da DROP ... IF EXISTS oppure dichiarato con
--  CREATE OR REPLACE. Il file è quindi rieseguibile.
-- ===========================================================================


-- ===========================================================================
--  FIXME
--  PARTE 0 - LA MACCHINA A STATI COME DATO
-- ===========================================================================
--  Sei righe di configurazione, non dati applicativi: stanno qui e non nel
--  seed perche' senza di esse il trigger delle transizioni rifiuterebbe
--  qualunque cambio di stato.
-- ---------------------------------------------------------------------------

INSERT INTO transizione_ammessa (stato_da, stato_a, ruolo, descrizione) VALUES
    ('APERTA',                  'ATTESA_APPROVAZIONE_LA',  'STUDENTE',
     'Invia il Learning Agreement'),
    ('ATTESA_APPROVAZIONE_LA',  'APERTA',                  'DOCENTE',
     'Rifiuta il Learning Agreement'),
    ('ATTESA_APPROVAZIONE_LA',  'PRE_PARTENZA_COMPLETATA', 'UFFICIO',
     'Verifica la pratica pre-partenza'),
    ('PRE_PARTENZA_COMPLETATA', 'MOBILITA_IN_CORSO',       'STUDENTE',
     'Registra l''inizio della mobilita'''),
    ('MOBILITA_IN_CORSO',       'IN_RICONOSCIMENTO_ESAMI', 'STUDENTE',
     'Registra il rientro e carica il Transcript'),
    ('IN_RICONOSCIMENTO_ESAMI', 'CHIUSA',                  'UFFICIO',
     'Chiudi la pratica')
ON CONFLICT DO NOTHING;

-- Recupera l'id dell'utente corrente tramite la funzione current_setting
-- che legge le variabili di configurazione della sessione da cui ottiene l'id
CREATE OR REPLACE FUNCTION app_utente_corrente()
RETURNS INTEGER AS $$
DECLARE
    valore TEXT;
BEGIN
    valore := current_setting('app.utente_id', true);
    IF valore IS NULL OR valore = '' THEN
        RETURN NULL;
    END IF;
    RETURN valore::INTEGER;
END;
$$ LANGUAGE plpgsql STABLE;


-- Controlla che ogni pratica abbia prima uno studente e un docente collegato
-- Inoltre, verifica che se una pratica è stata verificata o chiusa,
-- l'operazione sia stata fatta dall'utente che ne compete (ufficio)

CREATE OR REPLACE FUNCTION fn_verifica_ruoli_pratica()
RETURNS TRIGGER AS $$
DECLARE
    r TEXT;
BEGIN
    SELECT ruolo INTO r FROM utente WHERE id = NEW.studente_id;
    IF r <> 'STUDENTE' THEN
        RAISE EXCEPTION
            'Il titolare della pratica deve avere ruolo STUDENTE (trovato: %)', r
            USING ERRCODE = 'check_violation';
    END IF;

    SELECT ruolo INTO r FROM utente WHERE id = NEW.docente_id;
    IF r <> 'DOCENTE' THEN
        RAISE EXCEPTION
            'Il referente della pratica deve avere ruolo DOCENTE (trovato: %)', r
            USING ERRCODE = 'check_violation';
    END IF;

    IF NEW.verificata_da_id IS NOT NULL THEN
        SELECT ruolo INTO r FROM utente WHERE id = NEW.verificata_da_id;
        IF r <> 'UFFICIO' THEN
            RAISE EXCEPTION
                'La verifica pre-partenza spetta al personale d''ufficio (trovato: %)', r
                USING ERRCODE = 'check_violation';
        END IF;
    END IF;

    IF NEW.chiusa_da_id IS NOT NULL THEN
        SELECT ruolo INTO r FROM utente WHERE id = NEW.chiusa_da_id;
        IF r <> 'UFFICIO' THEN
            RAISE EXCEPTION
                'La chiusura spetta al personale d''ufficio (trovato: %)', r
                USING ERRCODE = 'check_violation';
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_ruoli_pratica ON pratica;
CREATE TRIGGER trg_ruoli_pratica
    BEFORE INSERT OR UPDATE ON pratica
    FOR EACH ROW EXECUTE FUNCTION fn_verifica_ruoli_pratica();

-- Impedisce di modificare una pratica se è già stata chiusa

CREATE OR REPLACE FUNCTION fn_pratica_immutabile()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.stato = 'CHIUSA' THEN
        RAISE EXCEPTION
            'La pratica % e'' chiusa e non puo'' piu'' essere modificata',
            OLD.codice_pratica
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_pratica_immutabile ON pratica;
CREATE TRIGGER trg_pratica_immutabile
    BEFORE UPDATE ON pratica
    FOR EACH ROW EXECUTE FUNCTION fn_pratica_immutabile();


-- Controlla se una pratica sia pronta per cambiare stato

CREATE OR REPLACE FUNCTION fn_transizione_stato()
RETURNS TRIGGER AS $$
DECLARE
    ruolo_attore   TEXT;
    id_attore      INTEGER;
    n              INTEGER;
    la_operativo   INTEGER;
BEGIN
    -- Se lo stato non cambia, questo trigger non interviene.
    IF NEW.stato = OLD.stato THEN
        RETURN NEW;
    END IF;

    -- Verifica che la transizione sia ammessa dalla macchina a stati.
    SELECT count(*) INTO n
      FROM transizione_ammessa
     WHERE stato_da = OLD.stato AND stato_a = NEW.stato;

    IF n = 0 THEN
        RAISE EXCEPTION
            'Transizione non ammessa: da % a %', OLD.stato, NEW.stato
            USING ERRCODE = 'check_violation';
    END IF;

    -- Se l'utente è noto, il suo ruolo deve ammettere la transizione.
    id_attore := app_utente_corrente();
    IF id_attore IS NOT NULL THEN
        SELECT ruolo INTO ruolo_attore FROM utente WHERE id = id_attore;

        SELECT count(*) INTO n
          FROM transizione_ammessa
         WHERE stato_da = OLD.stato
           AND stato_a = NEW.stato
           AND ruolo   = ruolo_attore;

        IF n = 0 THEN
            RAISE EXCEPTION
                'Il ruolo % non puo'' portare la pratica da % a %',
                ruolo_attore, OLD.stato, NEW.stato
                USING ERRCODE = 'insufficient_privilege';
        END IF;
    END IF;

    -- Per passare a ATTESA_APPROVAZIONE_LA:
    -- serve un LA in attesa, con file, almeno un corso estero
    -- e un'equivalenza per ogni corso.
    IF NEW.stato = 'ATTESA_APPROVAZIONE_LA' THEN
        SELECT count(*) INTO n
          FROM learning_agreement la
         WHERE la.pratica_id = NEW.id
           AND la.esito = 'IN_ATTESA'
           AND la.file_path IS NOT NULL
           AND EXISTS (SELECT 1 FROM corso_esterno ce
                        WHERE ce.learning_agreement_id = la.id)
           AND NOT EXISTS (
                 SELECT 1 FROM corso_esterno ce
                  WHERE ce.learning_agreement_id = la.id
                    AND NOT EXISTS (SELECT 1 FROM equivalenza eq
                                     WHERE eq.corso_esterno_id = ce.id));

        IF n = 0 THEN
            RAISE EXCEPTION
                'Per inviare il Learning Agreement servono il file caricato e almeno un esame estero, ciascuno con un''equivalenza'
                USING ERRCODE = 'check_violation';
        END IF;
    END IF;

    -- Per passare a PRE_PARTENZA_COMPLETATA serve un Learning Agreement approvato.
    IF NEW.stato = 'PRE_PARTENZA_COMPLETATA' THEN
        SELECT count(*) INTO n
          FROM learning_agreement
         WHERE pratica_id = NEW.id AND esito = 'APPROVATO';

        IF n = 0 THEN
            RAISE EXCEPTION
                'La pratica non ha un Learning Agreement approvato'
                USING ERRCODE = 'check_violation';
        END IF;
    END IF;

    -- Per passare allo stato IN_RICONOSCIMENTO_ESAMI:
    -- il Transcript of Records deve essere stato caricato.
    IF NEW.stato = 'IN_RICONOSCIMENTO_ESAMI' THEN
        SELECT count(*) INTO n FROM transcript WHERE pratica_id = NEW.id;
        IF n = 0 THEN
            RAISE EXCEPTION
                'Il Transcript of Records non e'' stato caricato'
                USING ERRCODE = 'check_violation';
        END IF;
    END IF;

    -- Per passare a CHIUSA: Transcript caricato e nessun esame
    -- registrato ancora senza decisione.
    IF NEW.stato = 'CHIUSA' THEN
        SELECT count(*) INTO n FROM transcript WHERE pratica_id = NEW.id;
        IF n = 0 THEN
            RAISE EXCEPTION
                'Il Transcript of Records non e'' stato caricato'
                USING ERRCODE = 'check_violation';
        END IF;

        -- L'ultima versione approvata del LA.
        SELECT id INTO la_operativo
          FROM learning_agreement
         WHERE pratica_id = NEW.id AND esito = 'APPROVATO'
         ORDER BY numero_versione DESC
         LIMIT 1;

        IF la_operativo IS NULL THEN
            RAISE EXCEPTION
                'La pratica non ha un Learning Agreement approvato'
                USING ERRCODE = 'check_violation';
        END IF;

        -- Nessun esame registrato può essere rimasto senza decisione.
        SELECT count(*) INTO n
          FROM esame e
          JOIN corso_esterno ce ON ce.id = e.corso_esterno_id
         WHERE ce.learning_agreement_id = la_operativo
           AND e.esito_riconoscimento = 'NON_VALUTATO';

        IF n > 0 THEN
            RAISE EXCEPTION
                'Restano % esami senza decisione di riconoscimento', n
                USING ERRCODE = 'check_violation';
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_transizione_stato ON pratica;
CREATE TRIGGER trg_transizione_stato
    BEFORE UPDATE ON pratica
    FOR EACH ROW EXECUTE FUNCTION fn_transizione_stato();


-- Nuove versioni del LA solo in APERTA, ATTESA_APPROVAZIONE_LA
-- o MOBILITA_IN_CORSO.

CREATE OR REPLACE FUNCTION fn_la_creabile()
RETURNS TRIGGER AS $$
DECLARE
    stato_pratica TEXT;
BEGIN
    SELECT stato INTO stato_pratica FROM pratica WHERE id = NEW.pratica_id;

    IF stato_pratica NOT IN ('APERTA', 'ATTESA_APPROVAZIONE_LA', 'MOBILITA_IN_CORSO') THEN
        RAISE EXCEPTION
            'Non e'' possibile proporre un Learning Agreement con la pratica in stato %',
            stato_pratica
            USING ERRCODE = 'check_violation';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_la_creabile ON learning_agreement;
CREATE TRIGGER trg_la_creabile
    BEFORE INSERT ON learning_agreement
    FOR EACH ROW EXECUTE FUNCTION fn_la_creabile();


-- Impedisce la modifica del LA se si trova negli stati APPROVATO o RIFIUTATO.

CREATE OR REPLACE FUNCTION fn_piano_modificabile()
RETURNS TRIGGER AS $$
DECLARE
    id_corso  INTEGER;
    id_la     INTEGER;
    esito_la  TEXT;
BEGIN
    -- Siccome il LA è presente sia in Corso Estero che in Equivalenza,
    -- per avere un solo controllo per entrambi i trigger:
    -- se stiamo lavorando su corso_esterno, recuperiamo l'id del LA direttamente dalla tabella
    -- se stiamo lavorando su altre tabelle, dobbiamo prima passare da corso_esterno per ottenere l'id dell'LA
    IF TG_TABLE_NAME = 'corso_esterno' THEN
        id_la := COALESCE(NEW.learning_agreement_id, OLD.learning_agreement_id);
    ELSE
        id_corso := COALESCE(NEW.corso_esterno_id, OLD.corso_esterno_id);
        SELECT learning_agreement_id INTO id_la
          FROM corso_esterno WHERE id = id_corso;
    END IF;

    SELECT esito INTO esito_la FROM learning_agreement WHERE id = id_la;

    IF esito_la IS NOT NULL AND esito_la <> 'IN_ATTESA' THEN
        RAISE EXCEPTION
            'Il Learning Agreement e'' gia'' stato valutato (%): il suo contenuto non e'' piu'' modificabile',
            esito_la
            USING ERRCODE = 'check_violation';
    END IF;

    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_corso_esterno_modificabile ON corso_esterno;
CREATE TRIGGER trg_corso_esterno_modificabile
    BEFORE INSERT OR UPDATE OR DELETE ON corso_esterno
    FOR EACH ROW EXECUTE FUNCTION fn_piano_modificabile();

DROP TRIGGER IF EXISTS trg_equivalenza_modificabile ON equivalenza;
CREATE TRIGGER trg_equivalenza_modificabile
    BEFORE INSERT OR UPDATE OR DELETE ON equivalenza
    FOR EACH ROW EXECUTE FUNCTION fn_piano_modificabile();


-- Controlla la registrazione degli esami sostenuti all'estero.

CREATE OR REPLACE FUNCTION fn_esame_registrabile()
RETURNS TRIGGER AS $$
DECLARE
    id_pratica    INTEGER;
    stato_pratica TEXT;
    id_la_corso   INTEGER;
    la_operativo  INTEGER;
BEGIN
    SELECT ce.learning_agreement_id, la.pratica_id
      INTO id_la_corso, id_pratica
      FROM corso_esterno ce
      JOIN learning_agreement la ON la.id = ce.learning_agreement_id
     WHERE ce.id = NEW.corso_esterno_id;

    SELECT stato INTO stato_pratica FROM pratica WHERE id = id_pratica;

    -- Se la pratica non e' in stato IN_RICONOSCIMENTO_ESAMI, non e' possibile registrare gli esami.
    IF stato_pratica <> 'IN_RICONOSCIMENTO_ESAMI' THEN
        RAISE EXCEPTION
            'Gli esami si registrano solo con la pratica in IN_RICONOSCIMENTO_ESAMI (stato attuale: %)',
            stato_pratica
            USING ERRCODE = 'check_violation';
    END IF;

    -- Controlla che il corso appartenga alla versione operativa del LA.
    SELECT id INTO la_operativo
      FROM learning_agreement
     WHERE pratica_id = id_pratica AND esito = 'APPROVATO'
     ORDER BY numero_versione DESC
     LIMIT 1;

    IF id_la_corso IS DISTINCT FROM la_operativo THEN
        RAISE EXCEPTION
            'Il corso non appartiene alla versione operativa del Learning Agreement'
            USING ERRCODE = 'check_violation';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_esame_registrabile ON esame;
CREATE TRIGGER trg_esame_registrabile
    BEFORE INSERT OR UPDATE ON esame
    FOR EACH ROW EXECUTE FUNCTION fn_esame_registrabile();


-- ===========================================================================
--  VISTE
-- ===========================================================================

-- Recupera la versione del LA più recente che è stata approvata.
-- Recupera tutte le versioni approvate, le ordina e restituisce solo la più recente.
CREATE OR REPLACE VIEW v_learning_agreement_corrente AS
SELECT DISTINCT ON (la.pratica_id)
       la.pratica_id,
       la.id                AS learning_agreement_id,
       la.numero_versione,
       la.data_decisione,
       la.file_path,
       la.nome_file_originale
  FROM learning_agreement la
 WHERE la.esito = 'APPROVATO'
 ORDER BY la.pratica_id, la.numero_versione DESC;


-- Calcola il numero di esami valutati, in attesa, accettati e la somma dei crediti riconosciuti
CREATE OR REPLACE VIEW v_stato_riconoscimento_pratica AS
SELECT p.id                                     AS pratica_id,
       p.codice_pratica,
       p.stato,
       lac.learning_agreement_id,
       count(e.id)                              AS esami_registrati,
       count(e.id) FILTER (
           WHERE e.esito_riconoscimento <> 'NON_VALUTATO')  AS esami_valutati,
       count(e.id) FILTER (
           WHERE e.esito_riconoscimento =  'NON_VALUTATO')  AS esami_da_valutare,
       count(e.id) FILTER (
           WHERE e.esito_riconoscimento =  'ACCETTATO')     AS esami_accettati,
       COALESCE(sum(ci.crediti) FILTER (
           WHERE e.esito_riconoscimento = 'ACCETTATO'), 0)  AS crediti_riconosciuti
  FROM pratica p
  LEFT JOIN v_learning_agreement_corrente lac ON lac.pratica_id = p.id
  LEFT JOIN corso_esterno ce
         ON ce.learning_agreement_id = lac.learning_agreement_id
  LEFT JOIN esame e        ON e.corso_esterno_id = ce.id
  LEFT JOIN equivalenza eq ON eq.corso_esterno_id = ce.id
  LEFT JOIN corso_interno ci ON ci.id = eq.corso_interno_id
 GROUP BY p.id, p.codice_pratica, p.stato, lac.learning_agreement_id;


-- Interroga la vista precedente per ottenere lo stato della pratica.
-- Se lo stato della pratica è IN_RICONOSCIMENTO_ESAMI, non ci sono altri esami da valutare
-- e il Transcript è stato caricato, la pratica è pronta per la chiusura.
CREATE OR REPLACE VIEW v_pratiche_pronte_per_chiusura AS
SELECT sr.pratica_id,
       sr.codice_pratica,
       sr.esami_registrati,
       sr.esami_accettati,
       sr.crediti_riconosciuti
  FROM v_stato_riconoscimento_pratica sr
 WHERE sr.stato = 'IN_RICONOSCIMENTO_ESAMI'
   AND sr.esami_da_valutare = 0
   AND EXISTS (SELECT 1 FROM transcript t WHERE t.pratica_id = sr.pratica_id);
