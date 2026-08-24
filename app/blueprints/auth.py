"""Accesso e uscita."""

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required, login_user, logout_user

from app.extensions import db
from app.models import Utente
from app.security import verifica_password

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        utente = db.session.scalar(db.select(Utente).where(Utente.email == email))

        # Messaggio volutamente generico: non riveliamo se l'email esiste.
        if utente is None or not utente.attivo or not verifica_password(
            password, utente.password_hash
        ):
            flash("Credenziali non valide.", "error")
            return render_template("auth/login.html", email=email), 401

        login_user(utente)
        flash(f"Benvenuto, {utente.nome}.", "success")

        # Si torna alla pagina richiesta prima del login, verificando che sia
        # un percorso interno: altrimenti si apre un redirect aperto.
        prossima = request.args.get("next", "")
        if prossima.startswith("/") and not prossima.startswith("//"):
            return redirect(prossima)
        return redirect(url_for("pubblico.cruscotto"))

    return render_template("auth/login.html", email="")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Sessione terminata.", "success")
    return redirect(url_for("pubblico.home"))
