-- ===========================================================================
--  COLLAUDO DELL'INTEGRITA'
--  Progetto Overseas - Basi di Dati Mod. 2
-- ===========================================================================
--
--  COME SI LANCIA
--      psql overseas -f scripts/collaudo.sql
--
--  COSA FA
--      Prova, uno per uno, tutti i vincoli e tutti i trigger dello schema.
--      Per ogni prova stampa una riga:
--          [ok]     il database si e' comportato come previsto
--          [FALLITA] il database ha accettato qualcosa che doveva rifiutare,
--                    o ha rifiutato qualcosa che doveva accettare
--
--  NON SPORCA IL DATABASE
--      Tutto lo script gira dentro una transazione che alla fine viene
--      ANNULLATA. I dati di prova non restano. Si puo' rilanciare quante
--      volte si vuole, anche su un database pieno.
--
--  COME E' FATTA UNA PROVA
--      Ogni prova e' un blocco DO con un gestore di eccezioni:
--
--          BEGIN
--              <operazione che DEVE fallire>
--              RAISE NOTICE '[FALLITA] ...';   <- se arriva qui, male
--          EXCEPTION WHEN others THEN
--              RAISE NOTICE '[ok] ...';        <- l'errore era atteso
--          END;
--
--      In PL/pgSQL un blocco BEGIN...EXCEPTION crea una sotto-transazione:
--      quando scatta l'eccezione, viene annullato solo quel blocco e lo
--      script prosegue. E' il motivo per cui una prova fallita non ferma
--      tutte le altre.
--
--  A COSA SERVE OLTRE CHE A CONTROLLARE
--      L'esito di questo script e' il contenuto della sezione "collaudo"
--      della relazione, e la scaletta della parte tecnica del video: si
--      lancia, si inquadra l'output, e si e' dimostrato che i vincoli
--      esistono davvero e non solo sulla carta.
-- ===========================================================================

\set ON_ERROR_STOP off
\pset pager off
\set QUIET on
SET client_min_messages = notice;

BEGIN;

-- ---------------------------------------------------------------------------
-- DATI DI PROVA
-- Codici con prefisso ZZZ per non collidere con dati veri gia' presenti.
-- ---------------------------------------------------------------------------
INSERT INTO utente (email, password_hash, nome, cognome, ruolo, matricola) VALUES
    ('zzz.stud@test',  'x', 'Prova', 'Studente', 'STUDENTE', 'ZZZ001'),
    ('zzz.stud2@test', 'x', 'Prova', 'Studente2','STUDENTE', 'ZZZ002'),
    ('zzz.doc@test',   'x', 'Prova', 'Docente',  'DOCENTE',  NULL),
    ('zzz.uff@test',   'x', 'Prova', 'Ufficio',  'UFFICIO',  NULL);

INSERT INTO istituto (nome, paese, citta)
    VALUES ('ZZZ Test University', 'Testland', 'Testville');

INSERT INTO corso_interno (codice, titolo, crediti)
    VALUES ('ZZZ001', 'Corso di prova', 6);

\set QUIET off
\echo ''
\echo '========================================================'
\echo ' COLLAUDO INTEGRITA - progetto Overseas'
\echo '========================================================'
\echo ''
\echo '--- VINCOLI CHECK (una riga, una tabella) ---'

DO $$
BEGIN
    BEGIN
        INSERT INTO utente (email, password_hash, nome, cognome, ruolo, matricola)
        VALUES ('zzz.a@test','x','A','B','DOCENTE','123');
        RAISE NOTICE '[FALLITA] un docente con matricola e'' stato accettato';
    EXCEPTION WHEN others THEN
        RAISE NOTICE '[ok] docente con matricola: rifiutato';
    END;

    BEGIN
        INSERT INTO utente (email, password_hash, nome, cognome, ruolo, matricola)
        VALUES ('zzz.b@test','x','A','B','STUDENTE',NULL);
        RAISE NOTICE '[FALLITA] uno studente senza matricola e'' stato accettato';
    EXCEPTION WHEN others THEN
        RAISE NOTICE '[ok] studente senza matricola: rifiutato';
    END;

    BEGIN
        INSERT INTO utente (email, password_hash, nome, cognome, ruolo, matricola)
        VALUES ('zzz.c@test','x','A','B','RETTORE',NULL);
        RAISE NOTICE '[FALLITA] un ruolo inesistente e'' stato accettato';
    EXCEPTION WHEN others THEN
        RAISE NOTICE '[ok] ruolo inesistente: rifiutato';
    END;

    BEGIN
        INSERT INTO utente (email, password_hash, nome, cognome, ruolo, matricola)
        VALUES ('zzz.stud@test','x','A','B','DOCENTE',NULL);
        RAISE NOTICE '[FALLITA] email duplicata accettata';
    EXCEPTION WHEN others THEN
        RAISE NOTICE '[ok] email duplicata: rifiutata';
    END;

    BEGIN
        INSERT INTO corso_interno (codice, titolo, crediti)
        VALUES ('ZZZ999','Corso',0);
        RAISE NOTICE '[FALLITA] crediti a zero accettati';
    EXCEPTION WHEN others THEN
        RAISE NOTICE '[ok] crediti non positivi: rifiutati';
    END;
END $$;

\echo ''
\echo '--- TRIGGER 1: coerenza dei ruoli ---'

DO $$
DECLARE
    s INTEGER; s2 INTEGER; d INTEGER; u INTEGER; i INTEGER;
BEGIN
    SELECT id INTO s  FROM utente WHERE email='zzz.stud@test';
    SELECT id INTO s2 FROM utente WHERE email='zzz.stud2@test';
    SELECT id INTO d  FROM utente WHERE email='zzz.doc@test';
    SELECT id INTO u  FROM utente WHERE email='zzz.uff@test';
    SELECT id INTO i  FROM istituto WHERE nome='ZZZ Test University';

    BEGIN
        INSERT INTO pratica (codice_pratica, anno_accademico, periodo, stato,
                             studente_id, data_apertura, docente_id, istituto_id)
        VALUES ('ZZZ-X', 2025, 'INTERO_ANNO', 'APERTA', s, CURRENT_DATE, s, i);
        RAISE NOTICE '[FALLITA] uno studente e'' stato accettato come referente';
    EXCEPTION WHEN others THEN
        RAISE NOTICE '[ok] studente come docente referente: rifiutato';
    END;

    BEGIN
        INSERT INTO pratica (codice_pratica, anno_accademico, periodo, stato,
                             studente_id, data_apertura, docente_id, istituto_id)
        VALUES ('ZZZ-Y', 2025, 'INTERO_ANNO', 'APERTA', d, CURRENT_DATE, d, i);
        RAISE NOTICE '[FALLITA] un docente e'' stato accettato come titolare';
    EXCEPTION WHEN others THEN
        RAISE NOTICE '[ok] docente come titolare: rifiutato';
    END;

    -- questa deve RIUSCIRE
    BEGIN
        INSERT INTO pratica (codice_pratica, anno_accademico, periodo, stato,
                             studente_id, data_apertura, docente_id, istituto_id)
        VALUES ('ZZZ-001', 2025, 'INTERO_ANNO', 'APERTA', s, CURRENT_DATE, d, i);
        RAISE NOTICE '[ok] pratica con ruoli corretti: accettata';
    EXCEPTION WHEN others THEN
        RAISE NOTICE '[FALLITA] una pratica corretta e'' stata rifiutata: %', SQLERRM;
    END;
END $$;

\echo ''
\echo '--- TRIGGER 4: registrazione automatica nello storico ---'

DO $$
DECLARE n INTEGER;
BEGIN
    SELECT count(*) INTO n
      FROM storico_stato s JOIN pratica p ON p.id = s.pratica_id
     WHERE p.codice_pratica = 'ZZZ-001' AND s.stato_a = 'APERTA';
    IF n = 1 THEN
        RAISE NOTICE '[ok] la nascita della pratica e'' finita nello storico';
    ELSE
        RAISE NOTICE '[FALLITA] lo storico non ha registrato la nascita (righe: %)', n;
    END IF;
END $$;

\echo ''
\echo '--- TRIGGER 3a: transizioni di stato ammesse ---'

DO $$
DECLARE p INTEGER;
BEGIN
    SELECT id INTO p FROM pratica WHERE codice_pratica='ZZZ-001';

    BEGIN
        UPDATE pratica SET stato='CHIUSA' WHERE id=p;
        RAISE NOTICE '[FALLITA] salto APERTA->CHIUSA accettato';
    EXCEPTION WHEN others THEN
        RAISE NOTICE '[ok] salto APERTA->CHIUSA: rifiutato';
    END;

    BEGIN
        UPDATE pratica SET stato='MOBILITA_IN_CORSO' WHERE id=p;
        RAISE NOTICE '[FALLITA] salto APERTA->MOBILITA accettato';
    EXCEPTION WHEN others THEN
        RAISE NOTICE '[ok] salto APERTA->MOBILITA: rifiutato';
    END;
END $$;

\echo ''
\echo '--- TRIGGER 3b: precondizioni sui dati ---'

DO $$
DECLARE p INTEGER; la INTEGER; ce INTEGER; ci INTEGER;
BEGIN
    SELECT id INTO p  FROM pratica WHERE codice_pratica='ZZZ-001';
    SELECT id INTO ci FROM corso_interno WHERE codice='ZZZ001';

    BEGIN
        UPDATE pratica SET stato='ATTESA_APPROVAZIONE_LA' WHERE id=p;
        RAISE NOTICE '[FALLITA] invio del LA accettato senza nessun LA';
    EXCEPTION WHEN others THEN
        RAISE NOTICE '[ok] invio senza Learning Agreement: rifiutato';
    END;

    INSERT INTO learning_agreement (pratica_id, numero_versione, esito, data_caricamento)
    VALUES (p, 1, 'IN_ATTESA', CURRENT_DATE) RETURNING id INTO la;

    INSERT INTO corso_esterno (learning_agreement_id, codice, titolo, crediti)
    VALUES (la, 'ZZZEXT1', 'Corso estero di prova', 6) RETURNING id INTO ce;

    BEGIN
        UPDATE pratica SET stato='ATTESA_APPROVAZIONE_LA' WHERE id=p;
        RAISE NOTICE '[FALLITA] invio accettato senza file e senza equivalenza';
    EXCEPTION WHEN others THEN
        RAISE NOTICE '[ok] invio senza file e senza equivalenza: rifiutato';
    END;

    INSERT INTO equivalenza VALUES (ce, ci);
    UPDATE learning_agreement
       SET file_path='prova.pdf', nome_file_originale='la.pdf' WHERE id=la;

    BEGIN
        UPDATE pratica SET stato='ATTESA_APPROVAZIONE_LA' WHERE id=p;
        RAISE NOTICE '[ok] invio con tutto a posto: accettato';
    EXCEPTION WHEN others THEN
        RAISE NOTICE '[FALLITA] invio corretto rifiutato: %', SQLERRM;
    END;
END $$;

\echo ''
\echo '--- Indice unico parziale: una sola proposta pendente ---'

DO $$
DECLARE p INTEGER;
BEGIN
    SELECT id INTO p FROM pratica WHERE codice_pratica='ZZZ-001';
    BEGIN
        INSERT INTO learning_agreement (pratica_id, numero_versione, esito, data_caricamento)
        VALUES (p, 2, 'IN_ATTESA', CURRENT_DATE);
        RAISE NOTICE '[FALLITA] due Learning Agreement in attesa accettati';
    EXCEPTION WHEN others THEN
        RAISE NOTICE '[ok] seconda proposta pendente: rifiutata';
    END;
END $$;

\echo ''
\echo '--- TRIGGER 6: il contenuto di una versione decisa e congelato ---'

DO $$
DECLARE p INTEGER; la INTEGER;
BEGIN
    SELECT id INTO p  FROM pratica WHERE codice_pratica='ZZZ-001';
    SELECT id INTO la FROM learning_agreement WHERE pratica_id=p AND numero_versione=1;

    UPDATE learning_agreement
       SET esito='APPROVATO', data_decisione=CURRENT_DATE WHERE id=la;

    BEGIN
        INSERT INTO corso_esterno (learning_agreement_id, codice, titolo, crediti)
        VALUES (la, 'ZZZEXT2', 'Aggiunto dopo l''approvazione', 6);
        RAISE NOTICE '[FALLITA] corso aggiunto a un LA gia'' approvato';
    EXCEPTION WHEN others THEN
        RAISE NOTICE '[ok] modifica di un LA approvato: rifiutata';
    END;

    BEGIN
        UPDATE corso_esterno SET crediti = 99
         WHERE learning_agreement_id = la AND codice='ZZZEXT1';
        RAISE NOTICE '[FALLITA] crediti modificati su un LA approvato';
    EXCEPTION WHEN others THEN
        RAISE NOTICE '[ok] modifica dei crediti su LA approvato: rifiutata';
    END;
END $$;

\echo ''
\echo '--- Motivazione obbligatoria sul rifiuto ---'

DO $$
DECLARE p INTEGER;
BEGIN
    SELECT id INTO p FROM pratica WHERE codice_pratica='ZZZ-001';
    BEGIN
        INSERT INTO learning_agreement (pratica_id, numero_versione, esito,
                                        data_caricamento, data_decisione)
        VALUES (p, 9, 'RIFIUTATO', CURRENT_DATE, CURRENT_DATE);
        RAISE NOTICE '[FALLITA] rifiuto senza motivazione accettato';
    EXCEPTION WHEN others THEN
        RAISE NOTICE '[ok] rifiuto senza motivazione: rifiutato';
    END;
END $$;

\echo ''
\echo '--- Avanzamento fino al rientro ---'

DO $$
DECLARE p INTEGER; u INTEGER;
BEGIN
    SELECT id INTO p FROM pratica WHERE codice_pratica='ZZZ-001';
    SELECT id INTO u FROM utente WHERE email='zzz.uff@test';

    BEGIN
        UPDATE pratica SET stato='PRE_PARTENZA_COMPLETATA',
               verificata_da_id=(SELECT id FROM utente WHERE email='zzz.stud@test'),
               pre_partenza_verificata_il=CURRENT_DATE
         WHERE id=p;
        RAISE NOTICE '[FALLITA] verifica pre-partenza fatta da uno studente';
    EXCEPTION WHEN others THEN
        RAISE NOTICE '[ok] verifica pre-partenza da studente: rifiutata';
    END;

    BEGIN
        UPDATE pratica SET stato='PRE_PARTENZA_COMPLETATA',
               verificata_da_id=u, pre_partenza_verificata_il=CURRENT_DATE
         WHERE id=p;
        RAISE NOTICE '[ok] verifica pre-partenza dall''ufficio: accettata';
    EXCEPTION WHEN others THEN
        RAISE NOTICE '[FALLITA] verifica corretta rifiutata: %', SQLERRM;
    END;

    UPDATE pratica SET stato='MOBILITA_IN_CORSO',
           data_inizio_effettivo=CURRENT_DATE WHERE id=p;

    BEGIN
        UPDATE pratica SET stato='IN_RICONOSCIMENTO_ESAMI',
               data_fine_effettiva=CURRENT_DATE WHERE id=p;
        RAISE NOTICE '[FALLITA] rientro accettato senza Transcript';
    EXCEPTION WHEN others THEN
        RAISE NOTICE '[ok] rientro senza Transcript: rifiutato';
    END;

    INSERT INTO transcript (pratica_id, file_path, nome_file_originale, data_caricamento)
    VALUES (p, 'tor.pdf', 'tor.pdf', CURRENT_DATE);

    UPDATE pratica SET stato='IN_RICONOSCIMENTO_ESAMI',
           data_fine_effettiva=CURRENT_DATE WHERE id=p;
    RAISE NOTICE '[ok] rientro con Transcript: accettato';
END $$;

\echo ''
\echo '--- TRIGGER 5: il piano si congela al rientro ---'

DO $$
DECLARE p INTEGER;
BEGIN
    SELECT id INTO p FROM pratica WHERE codice_pratica='ZZZ-001';
    BEGIN
        INSERT INTO learning_agreement (pratica_id, numero_versione, esito, data_caricamento)
        VALUES (p, 3, 'IN_ATTESA', CURRENT_DATE);
        RAISE NOTICE '[FALLITA] nuova versione del piano dopo il rientro';
    EXCEPTION WHEN others THEN
        RAISE NOTICE '[ok] nuova versione dopo il rientro: rifiutata';
    END;
END $$;

\echo ''
\echo '--- TRIGGER 7 e chiusura ---'

DO $$
DECLARE p INTEGER; ce INTEGER; u INTEGER;
BEGIN
    SELECT id INTO p  FROM pratica WHERE codice_pratica='ZZZ-001';
    SELECT id INTO u  FROM utente  WHERE email='zzz.uff@test';
    SELECT ce2.id INTO ce
      FROM corso_esterno ce2
      JOIN learning_agreement la ON la.id = ce2.learning_agreement_id
     WHERE la.pratica_id = p AND ce2.codice='ZZZEXT1';

    BEGIN
        INSERT INTO esame (corso_esterno_id, voto, data_esame, esito_riconoscimento)
        VALUES (ce, 35, CURRENT_DATE, 'NON_VALUTATO');
        RAISE NOTICE '[FALLITA] voto 35 accettato';
    EXCEPTION WHEN others THEN
        RAISE NOTICE '[ok] voto fuori scala: rifiutato';
    END;

    INSERT INTO esame (corso_esterno_id, voto, data_esame, esito_riconoscimento)
    VALUES (ce, 28, CURRENT_DATE, 'NON_VALUTATO');
    RAISE NOTICE '[ok] registrazione dell''esame: accettata';

    BEGIN
        UPDATE pratica SET stato='CHIUSA', chiusa_da_id=u, chiusa_il=CURRENT_DATE
         WHERE id=p;
        RAISE NOTICE '[FALLITA] chiusura accettata con un esame non valutato';
    EXCEPTION WHEN others THEN
        RAISE NOTICE '[ok] chiusura con esami da valutare: rifiutata';
    END;

    UPDATE esame SET esito_riconoscimento='ACCETTATO',
           data_riconoscimento=CURRENT_DATE WHERE corso_esterno_id=ce;

    BEGIN
        UPDATE pratica SET stato='CHIUSA', chiusa_da_id=u, chiusa_il=CURRENT_DATE
         WHERE id=p;
        RAISE NOTICE '[ok] chiusura con tutto a posto: accettata';
    EXCEPTION WHEN others THEN
        RAISE NOTICE '[FALLITA] chiusura corretta rifiutata: %', SQLERRM;
    END;
END $$;

\echo ''
\echo '--- TRIGGER 2: la pratica chiusa e immutabile ---'

DO $$
DECLARE p INTEGER;
BEGIN
    SELECT id INTO p FROM pratica WHERE codice_pratica='ZZZ-001';
    BEGIN
        UPDATE pratica SET note='modifica dopo la chiusura' WHERE id=p;
        RAISE NOTICE '[FALLITA] pratica chiusa modificata';
    EXCEPTION WHEN others THEN
        RAISE NOTICE '[ok] modifica di una pratica chiusa: rifiutata';
    END;
END $$;

\echo ''
\echo '--- Storico completo e viste ---'

DO $$
DECLARE p INTEGER; n INTEGER; v INTEGER;
BEGIN
    SELECT id INTO p FROM pratica WHERE codice_pratica='ZZZ-001';

    SELECT count(*) INTO n FROM storico_stato WHERE pratica_id=p;
    IF n = 6 THEN
        RAISE NOTICE '[ok] lo storico ha registrato tutte e 6 le transizioni';
    ELSE
        RAISE NOTICE '[FALLITA] lo storico ha % righe invece di 6', n;
    END IF;

    SELECT numero_versione INTO v
      FROM v_learning_agreement_corrente WHERE pratica_id=p;
    IF v = 1 THEN
        RAISE NOTICE '[ok] la vista indica la versione 1 come piano operativo';
    ELSE
        RAISE NOTICE '[FALLITA] la vista indica la versione %', v;
    END IF;

    SELECT crediti_riconosciuti INTO n
      FROM v_stato_riconoscimento_pratica WHERE pratica_id=p;
    IF n = 6 THEN
        RAISE NOTICE '[ok] la vista calcola 6 crediti riconosciuti';
    ELSE
        RAISE NOTICE '[FALLITA] crediti riconosciuti: % invece di 6', n;
    END IF;
END $$;

\echo ''
\echo '--- Controllo di ruolo sulla transizione (variabile di sessione) ---'

DO $$
DECLARE s INTEGER; d INTEGER; u INTEGER; i INTEGER; p INTEGER;
BEGIN
    SELECT id INTO s FROM utente WHERE email='zzz.stud2@test';
    SELECT id INTO d FROM utente WHERE email='zzz.doc@test';
    SELECT id INTO u FROM utente WHERE email='zzz.uff@test';
    SELECT id INTO i FROM istituto WHERE nome='ZZZ Test University';

    INSERT INTO pratica (codice_pratica, anno_accademico, periodo, stato,
                         studente_id, data_apertura, docente_id, istituto_id)
    VALUES ('ZZZ-002', 2026, 'PRIMO_SEMESTRE', 'APERTA', s, CURRENT_DATE, d, i)
    RETURNING id INTO p;

    -- ci dichiariamo UFFICIO: l'invio del LA spetta allo studente
    PERFORM set_config('app.utente_id', u::TEXT, true);
    BEGIN
        UPDATE pratica SET stato='ATTESA_APPROVAZIONE_LA' WHERE id=p;
        RAISE NOTICE '[FALLITA] l''ufficio ha potuto inviare il Learning Agreement';
    EXCEPTION WHEN others THEN
        RAISE NOTICE '[ok] transizione compiuta dal ruolo sbagliato: rifiutata';
    END;

    PERFORM set_config('app.utente_id', '', true);
END $$;

\echo ''
\echo '========================================================'
\echo ' Fine del collaudo: 32 prove.'
\echo ' Se sopra ci sono solo righe [ok], l integrita e a posto.'
\echo ' I dati di prova vengono ora annullati.'
\echo ''
\echo ' Per contare gli esiti:'
\echo '   psql overseas -f scripts/collaudo.sql 2>&1 | grep -c ok\]'
\echo '========================================================'
\echo ''

ROLLBACK;
