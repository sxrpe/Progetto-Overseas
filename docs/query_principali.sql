-- ===========================================================================
-- QUERY PRINCIPALI — raccolta per la sezione 4 della relazione.
--
-- A COSA SERVE QUESTO FILE
--   La relazione chiede "una selezione delle query piu' interessanti,
--   utilizzando una sintassi SQL opportuna". Le query nel codice sono scritte
--   in Expression Language: qui si tiene la versione SQL corrispondente,
--   pronta da incollare.
--
-- COME OTTENERE L'SQL VERO
--   Metti SQL_ECHO=1 nel file .env, carica la pagina, e copia dal terminale
--   l'istruzione che SQLAlchemy ha generato. Non trascriverla a mano: cosi'
--   sei sicuro che quello che scrivi in relazione e' quello che gira davvero.
--
-- QUANTE
--   Quattro o cinque, non dieci. Meglio poche query che mostrano join,
--   aggregazioni, sottointerrogazioni e viste, che un elenco di SELECT banali.
--
-- PER OGNUNA, ANNOTA
--   - a cosa serve nell'applicazione
--   - perche' e' interessante
--   - come l'hai resa efficiente (quale indice la sostiene)
-- ===========================================================================


-- ---------------------------------------------------------------------------
-- Q1. Pratiche incomplete: avviate ma senza Learning Agreement approvato.
--     Interessante perche': usa NOT EXISTS, che e' il modo efficiente di
--     esprimere "non esiste alcuna riga collegata che soddisfi X".
--     Indice che la sostiene: ix_documento_in_attesa (esito, tipo).
--     Citata dalla traccia fra le query frequenti previste.
-- ---------------------------------------------------------------------------

-- (da scrivere in Fase 7)


-- ---------------------------------------------------------------------------
-- Q2. Distribuzione delle mobilita' per paese e anno accademico.
--     Interessante perche': aggregazione con join, ed e' il caso d'uso
--     naturale per la vista materializzata del cruscotto.
-- ---------------------------------------------------------------------------

-- (da scrivere in Fase 10 o 12)


-- ---------------------------------------------------------------------------
-- Q3. Documenti in attesa di valutazione, per docente referente.
--     Interessante perche': e' la query piu' eseguita dell'applicazione
--     (ogni docente la lancia a ogni accesso) e giustifica un indice.
-- ---------------------------------------------------------------------------

-- (da scrivere in Fase 7)


-- ---------------------------------------------------------------------------
-- Q4. Riepilogo dei crediti riconosciuti per pratica.
--     Interessante perche': aggregazione condizionale, cioe' somma solo dei
--     crediti degli esami con esito approvato. In PostgreSQL si scrive
--     elegantemente con COUNT/SUM ... FILTER (WHERE ...).
-- ---------------------------------------------------------------------------

-- (da scrivere in Fase 7.10)


-- ---------------------------------------------------------------------------
-- Q5. Pratiche ferme da piu' tempo in uno stato intermedio.
--     Interessante perche': combina un filtro sullo stato con un calcolo
--     sulle date, ed e' la base delle notifiche per pratiche incomplete.
-- ---------------------------------------------------------------------------

-- (facoltativa, Fase 12)


-- ===========================================================================
-- CONFRONTO CON E SENZA INDICE — per la sezione 5.3 della relazione.
--
-- Una misura vale piu' di un'affermazione. Per ogni indice importante:
--
--   EXPLAIN ANALYZE <la query>;          -- prima
--   CREATE INDEX ...;
--   EXPLAIN ANALYZE <la query>;          -- dopo
--
-- Annota qui sotto i due piani di esecuzione e i tempi. Serve poco spazio in
-- relazione e dimostra una scelta misurata invece che dichiarata.
-- ===========================================================================
