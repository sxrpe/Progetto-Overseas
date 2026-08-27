-- ===========================================================================
--  Vincoli, trigger e viste non esprimibili con l'ORM
--  Progetto Overseas - Basi di Dati Mod. 2
-- ===========================================================================
--
--  QUANDO VIENE ESEGUITO
--      Da scripts/init_db.py, subito dopo db.create_all(). Le tabelle devono
--      quindi esistere gia': qui non se ne crea nessuna.
--
--  PERCHE' QUESTO FILE ESISTE
--      Un vincolo CHECK vede una sola riga di una sola tabella, nella sua
--      versione nuova. Tutto cio' che ha bisogno di:
--          - leggere un'altra tabella
--          - conoscere il valore PRECEDENTE della riga
--          - contare righe correlate
--      esce dalla portata dell'ORM e finisce qui.
--
--  E' IDEMPOTENTE
--      Ogni oggetto e' preceduto da DROP ... IF EXISTS oppure dichiarato con
--      CREATE OR REPLACE. Si puo' rieseguire quante volte si vuole.
--
--  DA CHI VIENE COMPIUTA L'AZIONE
--      PostgreSQL non sa chi e' l'utente applicativo: la connessione e'
--      sempre la stessa. L'applicazione lo comunica all'inizio della
--      transazione con
--          SET LOCAL app.utente_id = '7';
--      e i trigger lo rileggono con current_setting('app.utente_id', true).
--      Il secondo parametro true significa "non fallire se non e' impostato":
--      in quel caso il controllo di ruolo viene saltato e lo storico registra
--      un utente nullo. Cosi' gli script di popolamento funzionano senza
--      dover fingere un'identita'.
-- ===========================================================================


-- ===========================================================================
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


-- ===========================================================================
--  PARTE 1 - FUNZIONE DI SERVIZIO
-- ===========================================================================

-- L'id dell'utente applicativo, se l'applicazione lo ha comunicato.
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


-- ===========================================================================
--  TRIGGER 1 - COERENZA DEI RUOLI
-- ===========================================================================
--  Nel modello concettuale la relazione "referenza" collegava la Pratica al
--  sottotipo Docente, non a Utente: il vincolo era espresso graficamente.
--  Il collasso della generalizzazione in un'unica tabella lo ha distrutto,
--  perche' tutte le chiavi esterne ora puntano a "utente" e nulla impedisce
--  di mettere uno studente come referente.
--
--  Il vincolo non nasce dal dominio: nasce dalla TRADUZIONE. E' la
--  giustificazione piu' pulita che avete per l'uso di un trigger.
--
--  Perche' non un CHECK: deve leggere la tabella utente.
-- ---------------------------------------------------------------------------

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


-- ===========================================================================
--  TRIGGER 2 - IMMUTABILITA' DELLA PRATICA CHIUSA
-- ===========================================================================
--  CHIUSA e' uno stato terminale: da li' non si torna indietro e non si
--  modifica piu' nulla.
--
--  Perche' non un CHECK: serve il valore PRECEDENTE della riga (OLD), che un
--  CHECK non conosce. Un CHECK vede solo la versione nuova, e non saprebbe
--  distinguere "questa riga era gia' chiusa" da "questa riga sta venendo
--  chiusa adesso".
-- ---------------------------------------------------------------------------

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


-- ===========================================================================
--  TRIGGER 3 - TRANSIZIONI DI STATO E LORO PRECONDIZIONI
-- ===========================================================================
--  Due controlli distinti, che conviene tenere separati anche mentalmente.
--
--  (a) LA TRANSIZIONE ESISTE?
--      La coppia (stato precedente, stato nuovo) deve comparire in
--      transizione_ammessa. La macchina a stati e' un DATO, non codice:
--      il corpo di questo trigger non cambia mai, si aggiunge una riga
--      alla tabella. La stessa tabella la interroga l'interfaccia per
--      decidere quali pulsanti mostrare, cosi' le regole stanno in un
--      posto solo.
--
--  (b) I DATI SONO PRONTI?
--      Non basta che la transizione sia ammessa: servono le condizioni
--      sostanziali richieste dalla traccia (un LA approvato, il Transcript
--      caricato, tutti gli esami valutati). Queste contano righe su altre
--      tabelle, quindi sono per forza qui.
--
--  Perche' non un CHECK: (a) ha bisogno di OLD, (b) legge altre tabelle.
-- ---------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION fn_transizione_stato()
RETURNS TRIGGER AS $$
DECLARE
    ruolo_attore   TEXT;
    id_attore      INTEGER;
    n              INTEGER;
    la_operativo   INTEGER;
BEGIN
    -- Nessun cambio di stato: questo trigger non ha niente da dire.
    IF NEW.stato = OLD.stato THEN
        RETURN NEW;
    END IF;

    ------------------------------------------------------------------
    -- (a) la transizione e' prevista dalla macchina a stati?
    ------------------------------------------------------------------
    SELECT count(*) INTO n
      FROM transizione_ammessa
     WHERE stato_da = OLD.stato AND stato_a = NEW.stato;

    IF n = 0 THEN
        RAISE EXCEPTION
            'Transizione non ammessa: da % a %', OLD.stato, NEW.stato
            USING ERRCODE = 'check_violation';
    END IF;

    -- ...e chi la sta compiendo ha il ruolo giusto?
    -- Solo se l'applicazione ha dichiarato l'utente: gli script di
    -- popolamento non lo fanno e devono poter lavorare.
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

    ------------------------------------------------------------------
    -- (b) precondizioni sui dati
    ------------------------------------------------------------------

    -- Invio del Learning Agreement: deve esistere una versione pendente,
    -- col file caricato, con almeno un corso estero, e ogni corso deve
    -- avere almeno un'equivalenza. Un piano senza mapping non e' un piano.
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

    -- Verifica pre-partenza: requisito 5 della traccia, "solo se il
    -- Learning Agreement e' stato approvato dal docente referente".
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

    -- Rientro: il Transcript deve essere stato caricato.
    IF NEW.stato = 'IN_RICONOSCIMENTO_ESAMI' THEN
        SELECT count(*) INTO n FROM transcript WHERE pratica_id = NEW.id;
        IF n = 0 THEN
            RAISE EXCEPTION
                'Il Transcript of Records non e'' stato caricato'
                USING ERRCODE = 'check_violation';
        END IF;
    END IF;

    -- Chiusura: requisito 10 della traccia, "solo quando il Transcript of
    -- Records e' stato caricato e il riconoscimento degli esami e' stato
    -- completato".
    IF NEW.stato = 'CHIUSA' THEN
        SELECT count(*) INTO n FROM transcript WHERE pratica_id = NEW.id;
        IF n = 0 THEN
            RAISE EXCEPTION
                'Il Transcript of Records non e'' stato caricato'
                USING ERRCODE = 'check_violation';
        END IF;

        -- La versione operativa del piano: l'ultima approvata.
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

        -- Nessun esame registrato puo' essere rimasto senza decisione.
        -- Nota: i corsi pianificati e non sostenuti NON hanno una riga in
        -- esame, e giustamente non richiedono alcuna valutazione.
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


-- ===========================================================================
--  TRIGGER 4 - REGISTRAZIONE DELLO STORICO
-- ===========================================================================
--  L'unico trigger che scrive invece di validare.
--
--  Sta nel database e non nell'applicazione perche' cosi' la traccia esiste
--  anche per le modifiche fatte da uno script o a mano sul DBMS. Un registro
--  che si puo' aggirare non e' un registro.
--
--  E' AFTER e non BEFORE: si registra un fatto avvenuto, non uno che potrebbe
--  ancora essere rifiutato da un altro trigger.
-- ---------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION fn_registra_storico()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO storico_stato (pratica_id, stato_da, stato_a, utente_id)
        VALUES (NEW.id, NULL, NEW.stato, app_utente_corrente());

    ELSIF NEW.stato <> OLD.stato THEN
        INSERT INTO storico_stato (pratica_id, stato_da, stato_a, utente_id)
        VALUES (NEW.id, OLD.stato, NEW.stato, app_utente_corrente());
    END IF;

    RETURN NULL;   -- in un trigger AFTER il valore di ritorno viene ignorato
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_registra_storico ON pratica;
CREATE TRIGGER trg_registra_storico
    AFTER INSERT OR UPDATE ON pratica
    FOR EACH ROW EXECUTE FUNCTION fn_registra_storico();


-- ===========================================================================
--  TRIGGER 5 - QUANDO SI PUO' CREARE UNA NUOVA VERSIONE DEL PIANO
-- ===========================================================================
--  Ammesso in APERTA (prima stesura), in ATTESA_APPROVAZIONE_LA (correzione
--  dopo un rifiuto) e in MOBILITA_IN_CORSO (modifica in corso d'opera,
--  prevista esplicitamente dalla traccia).
--
--  VIETATO da IN_RICONOSCIMENTO_ESAMI in poi: il piano si congela al rientro.
--  E' questo congelamento a garantire che i voti si registrino su una
--  versione che non cambiera' piu', eliminando alla radice il problema della
--  migrazione dei voti fra versioni.
-- ---------------------------------------------------------------------------

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


-- ===========================================================================
--  TRIGGER 6 - IL CONTENUTO DI UNA VERSIONE DECISA E' CONGELATO
-- ===========================================================================
--  Corsi esterni ed equivalenze si possono toccare solo finche' la versione
--  a cui appartengono e' IN_ATTESA. Una volta approvata o rifiutata, quella
--  versione e' un documento storico.
--
--  E' cio' che rende vero l'assunto su cui poggia tutto il versionamento:
--  "la versione precedente non e' mai stata alterata". Senza questo trigger
--  il ripristino dopo un rifiuto, che la traccia richiede, sarebbe una
--  promessa non mantenuta.
--
--  Lo stesso trigger serve due tabelle: una funzione, due CREATE TRIGGER.
-- ---------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION fn_piano_modificabile()
RETURNS TRIGGER AS $$
DECLARE
    id_corso  INTEGER;
    id_la     INTEGER;
    esito_la  TEXT;
BEGIN
    -- Su DELETE la riga interessata e' OLD, altrimenti NEW.
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


-- ===========================================================================
--  TRIGGER 7 - REGISTRAZIONE E RICONOSCIMENTO DEGLI ESAMI
-- ===========================================================================
--  Due condizioni, entrambe fuori portata per un CHECK perche' attraversano
--  tre tabelle.
--
--  (a) la pratica deve essere in IN_RICONOSCIMENTO_ESAMI: prima del rientro
--      un voto non esiste, dopo la chiusura non si tocca piu';
--  (b) il corso su cui si registra il voto deve appartenere alla VERSIONE
--      OPERATIVA del piano, cioe' l'ultima approvata. Senza questo controllo
--      si potrebbe registrare un voto su un esame di una versione respinta,
--      o addirittura su un corso di un'altra pratica.
--
--  (b) e' il vincolo che l'architettura a versioni rende necessario: e' il
--      prezzo della flessibilita', e va dichiarato come tale.
-- ---------------------------------------------------------------------------

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

    IF stato_pratica <> 'IN_RICONOSCIMENTO_ESAMI' THEN
        RAISE EXCEPTION
            'Gli esami si registrano solo con la pratica in IN_RICONOSCIMENTO_ESAMI (stato attuale: %)',
            stato_pratica
            USING ERRCODE = 'check_violation';
    END IF;

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
--  Una vista e' una query salvata con un nome, interrogabile come una
--  tabella. Non contiene dati: ogni lettura riesegue la query sottostante.
--
--  Ognuna di queste esiste perche' la stessa domanda ricorre in molti punti
--  dell'applicazione. Tenerla in un posto solo evita di riscrivere la stessa
--  logica in cinque rotte diverse e di dimenticarne una il giorno che cambia.
-- ===========================================================================


-- ---------------------------------------------------------------------------
--  Il piano operativo: per ogni pratica, l'ultima versione approvata.
--
--  Alternativa scartata: una colonna "corrente" mantenuta da un trigger.
--  Sarebbe dato derivato, quindi ridondanza da giustificare. La vista da'
--  la stessa comodita' senza aggiungere nulla allo schema.
--
--  DISTINCT ON e' specifico di PostgreSQL: tiene la prima riga di ogni
--  gruppo secondo l'ORDER BY. Piu' leggibile della sottoquery con MAX.
-- ---------------------------------------------------------------------------
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


-- ---------------------------------------------------------------------------
--  Avanzamento del riconoscimento, per ogni pratica.
--
--  Alimenta il "mancano 3 riconoscimenti su 7" mostrato all'ufficio: molto
--  piu' utile di far sparire un pulsante senza spiegazione.
--
--  I corsi pianificati e non sostenuti non compaiono fra gli esami, e non
--  vengono conteggiati: e' il vantaggio di avere Esame come entita' separata
--  invece che come colonne nulle su Corso esterno.
-- ---------------------------------------------------------------------------
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


-- ---------------------------------------------------------------------------
--  Le pratiche che l'ufficio puo' effettivamente chiudere.
--
--  Le stesse condizioni che il trigger verifica in scrittura, qui espresse
--  in lettura. Non e' duplicazione inutile: sono i due livelli della difesa
--  in profondita'. Questa vista dice all'interfaccia cosa proporre, il
--  trigger garantisce che nessuno faccia altro.
-- ---------------------------------------------------------------------------
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


-- ---------------------------------------------------------------------------
--  Pratiche ferme da piu' tempo in uno stato intermedio.
--
--  E' la query che ha giustificato l'introduzione dello storico: senza,
--  bisognerebbe ricostruire l'informazione dalle singole date sparse fra le
--  relazioni, e per gli stati che non hanno una data dedicata sarebbe
--  semplicemente impossibile.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_pratiche_ferme AS
SELECT p.id                AS pratica_id,
       p.codice_pratica,
       p.stato,
       u.nome || ' ' || u.cognome           AS studente,
       max(s.quando)                        AS in_questo_stato_dal,
       (CURRENT_DATE - max(s.quando)::date) AS giorni_fermi
  FROM pratica p
  JOIN utente u        ON u.id = p.studente_id
  JOIN storico_stato s ON s.pratica_id = p.id AND s.stato_a = p.stato
 WHERE p.stato <> 'CHIUSA'
 GROUP BY p.id, p.codice_pratica, p.stato, u.nome, u.cognome;