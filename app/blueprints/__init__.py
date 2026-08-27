"""Pacchetto dei blueprint.

Un blueprint e' una "sotto-applicazione" Flask: raggruppa un insieme di route
che condividono uno scopo e un prefisso di URL.

In questo progetto ce n'e' uno per area funzionale:

    pubblico.py   /                 pagine accessibili senza login
    auth.py       /auth/...         accesso e uscita
    pratiche.py   /pratiche/...     dettaglio pratica, condiviso dai tre ruoli
    studente.py   /studente/...     area studente
    docente.py    /docente/...      area docente referente
    ufficio.py    /ufficio/...      area ufficio Overseas

Il vantaggio non e' estetico: siccome ogni area ha il suo prefisso, guardando
un URL sai gia' chi dovrebbe poterci accedere. Questo rende i permessi
verificabili a colpo d'occhio.

Questo file consente al linguaggio di interpretare questa cartella come insieme di pacchetti che poi vengono assemblati dall'altro init
con create_app()
"""
