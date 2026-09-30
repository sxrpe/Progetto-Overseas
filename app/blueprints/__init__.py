"""
DESCRIZIONE
    Rende questa cartella un pacchetto Python.
    I blueprint stanno nei moduli qui sotto e vengono registrati da create_app().
    Ogni blueprint raggruppa le rotte di un'area del sito sotto un prefisso URL.

    pubblico.py    /                 pagine accessibili senza login
    auth.py        /auth/...         accesso e uscita
    pratiche.py    /pratiche/...     dettaglio della pratica, comune ai tre ruoli
    studente.py    /studente/...     area studente
    docente.py     /docente/...      area docente
    ufficio.py     /ufficio/...      area ufficio
"""
