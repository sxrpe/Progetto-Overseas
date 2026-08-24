"""Accesso e uscita.  ->  Da scrivere in FASE 6.

I CINQUE INGREDIENTI DI FLASK-LOGIN (visti a lezione)
    1. una classe utente con un identificatore univoco  -> app/models.py
    2. login_user(utente)   salva l'identita' nella sessione       -> qui
    3. logout_user()        la rimuove                             -> qui
    4. la callback user_loader, che dall'identita' ricostruisce
       l'oggetto utente                                  -> app/__init__.py
    5. il decoratore @login_required sulle route protette -> ovunque serva

    I punti 1 e 4 sono gli unici che devi scrivere tu obbligatoriamente.

TRACCIA DELLA ROUTE DI LOGIN
    - GET  -> mostra il form
    - POST -> cerca l'utente per email, verifica la password con
              security.verifica_password(), poi login_user()
    - in caso di errore: messaggio GENERICO ("credenziali non valide"),
      senza dire se e' sbagliata l'email o la password
    - dopo il login, torna alla pagina che l'utente voleva, ma solo se e'
      un percorso interno: accettare un URL esterno apre un redirect aperto
"""

from flask import Blueprint

auth_bp = Blueprint("auth", __name__)


# @auth_bp.route("/login", methods=["GET", "POST"])
# def login():
#     ...
#
#
# @auth_bp.route("/logout")
# @login_required
# def logout():
#     ...
