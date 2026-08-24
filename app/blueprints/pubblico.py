"""Pagine accessibili senza autenticazione."""

from flask import Blueprint, redirect, render_template, url_for
from flask_login import current_user

pubblico_bp = Blueprint("pubblico", __name__)


@pubblico_bp.route("/")
def home():
    if current_user.is_authenticated:
        return redirect(url_for("pubblico.cruscotto"))
    return render_template("home.html")


@pubblico_bp.route("/cruscotto")
def cruscotto():
    """Smista l'utente autenticato verso l'area del proprio ruolo."""
    from app.enums import Ruolo

    if not current_user.is_authenticated:
        return redirect(url_for("auth.login"))
    destinazioni = {
        Ruolo.STUDENTE: "studente.elenco_pratiche",
        Ruolo.DOCENTE: "docente.elenco_pratiche",
        Ruolo.UFFICIO: "ufficio.elenco_pratiche",
    }
    return redirect(url_for(destinazioni[current_user.ruolo]))
