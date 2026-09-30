"""
DESCRIZIONE
    Accesso e uscita dall'applicazione.
    login_user e logout_user gestiscono il cookie di sessione;
    la ricostruzione dell'utente a ogni richiesta sta in app/__init__.py
    (user_loader). Le rotte protette usano @login_required.
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
    """Mostra il form (GET) e verifica le credenziali (POST)."""

    # Gia autenticato va alla Home
    if current_user.is_authenticated:
        return redirect(url_for("pubblico.home"))

    if request.method == "POST":
        # .get con valore di riserva evita errori se un campo manca del tutto.
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        utente = db.session.scalar(
            sa.select(Utente).where(Utente.email == email)
        )

        # Stesso messaggio se l'email non esiste o la password è sbagliata,
        # così non si scopre quali indirizzi sono registrati.
        if utente is None or not utente.verifica_password(password):
            flash("Credenziali non valide.", "danger")
            return render_template("auth/login.html", email=email)

        # Da qui current_user è valorizzato. remember=False: la sessione
        # termina alla chiusura del browser.
        login_user(utente, remember=False)

        # @login_required può aver messo in ?next= la pagina richiesta.
        # in questo modo de veniamo renderizzati al login, poi torniamo alla risorsa interna richiesta (se abbiamo l'accesso)
        destinazione = request.args.get("next", "")
        if not destinazione or urlsplit(destinazione).netloc != "":
            destinazione = url_for("pubblico.home")

        flash(f"Bentornato, {utente.nome}.", "success")
        return redirect(destinazione)

    return render_template("auth/login.html", email="")


@auth_bp.route("/logout")
@login_required
def logout():
    """Chiude la sessione e torna alla home.

    @login_required evita un messaggio di uscita a chi non era entrato.
    """
    logout_user()
    flash("Sei uscito.", "info")
    return redirect(url_for("pubblico.home"))
