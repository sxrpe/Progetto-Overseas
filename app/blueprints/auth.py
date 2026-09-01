"""Accesso e uscita.

I CINQUE INGREDIENTI DI FLASK-LOGIN
    1. una classe utente con un identificatore univoco   -> models.py
    2. login_user(utente)   salva l'identita' nel cookie -> qui
    3. logout_user()        la rimuove                   -> qui
    4. la callback user_loader, che dall'identita' salvata ricostruisce
       l'oggetto utente                                  -> app/__init__.py
    5. il decoratore @login_required sulle rotte protette -> ovunque serva

COSA VIENE SALVATO NEL COOKIE
    Solo l'id dell'utente, e per giunta firmato con la SECRET_KEY. Non la
    password, non il ruolo. A ogni richiesta Flask-Login legge quell'id e
    richiama la user_loader per ricaricare l'utente dal database: cosi' se un
    utente viene disabilitato o cambia ruolo, la modifica ha effetto subito e
    non alla prossima scadenza del cookie.

    La firma serve perche' il cookie sta sul computer dell'utente, che
    potrebbe modificarlo. Senza firma, chiunque scriverebbe "id=1" e
    diventerebbe amministratore.
"""

from urllib.parse import urlsplit

import sqlalchemy as sa
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app.extensions import db
from app.models import Utente

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Singola rotta per due funzioni : Mostra il form (GET) e verifica le credenziali (POST).

    E' la stessa funzione per i due metodi HTTP: si distinguono con
    request.method. E' la convenzione di Flask e tiene vicine due cose che
    parlano dello stesso form.
    """

    # Chi e' gia' entrato non ha motivo di vedere il form.
    if current_user.is_authenticated:
        return redirect(url_for("pubblico.home"))

    if request.method == "POST":
        # request.form e' un dizionario con i campi del form. Il .get() con
        # valore di riserva evita l'errore se un campo manca del tutto:
        # non fidarsi mai della forma dei dati che arrivano dal browser.
        # Questa Sintassi con () e il campo vuoto consente di evitare il rendirizzamento automatico di flask
        # in caso di mancato inserimento del valore
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        utente = db.session.scalar(
            sa.select(Utente).where(Utente.email == email) # Query Parametrizzata
        )

        # UN SOLO MESSAGGIO PER I DUE CASI.
        # Dire "email inesistente" permetterebbe di scoprire quali indirizzi
        # sono registrati provandoli uno per uno.
        if utente is None or not utente.verifica_password(password):
            flash("Credenziali non valide.", "danger")
            # UTILIZZO DI FLASH nel template, get_flashed_messages(with_categories=true) cattura questo messaggio
            # (é come una scatola di sessione che si riempie e si svuota) con le categorie possiamo fare lo split delle due variabili passate
            # {% with messaggi = get_flashed_messages(with_categories=true) %}
            #   {% for categoria, testo in messaggi %}

            return render_template("auth/login.html", email=email) #il campo email rimane compilato

        # CREAZIONE COOKIE
        # Da qui in poi current_user esiste in tutta l'applicazione.
        # remember=False: la sessione finisce quando si chiude il browser.
        login_user(utente, remember=False)

        # RITORNO ALLA PAGINA CHE L'UTENTE VOLEVA.
        # @login_required, quando respinge qualcuno, mette la pagina di
        # partenza in ?next=... Va usata, ma NON ci si puo' fidare: e' un
        # parametro nell'URL, quindi lo scrive chi vuole.
        #
        # urlsplit(...).netloc e' il nome del sito. Se e' vuoto, l'indirizzo
        # e' interno ("/studente/pratiche"). Se e' pieno, punta fuori
        # ("https://sito-finto.it/login") e va scartato: altrimenti si crea
        # un "open redirect", cioe' un link del vostro dominio che porta a
        # una pagina di accesso contraffatta.

        # TODO Vedere ocme avviene il redirect se accedi ad una risorsa non loggata
        destinazione = request.args.get("next", "")
        #1. L'utente (non collegato) apre    /studente/pratiche
        #2. @login_required lo blocca e costruisce il redirect:
        # url_for("auth.login")  +  ?next=  +  l'indirizzo che voleva
        if not destinazione or urlsplit(destinazione).netloc != "":
            destinazione = url_for("pubblico.home")

        flash(f"Bentornato, {utente.nome}.", "success")
        return redirect(destinazione)

    # GET: mostra il form vuoto (non serve il ramo else, la richeista POST é gia stata elaborata)
    return render_template("auth/login.html", email="")


@auth_bp.route("/logout")
@login_required
def logout():
    """Cancella l'identita' dalla sessione.

    Perche' @login_required su un logout: senza, la rotta sarebbe raggiungibile
    anche da chi non e' entrato, e produrrebbe un messaggio di uscita a chi non
    era dentro.
    """
    logout_user()
    flash("Sei uscito.", "info")
    return redirect(url_for("pubblico.home"))