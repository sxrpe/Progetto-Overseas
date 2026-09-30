"""
DESCRIZIONE
    Pagine pubbliche (senza login). Per ora solo la home:
    presentazione e, se sei entrato, chi sei.

MAPPA
    GET  /     home
"""

from flask import Blueprint, render_template

# Blueprint "pubblico": __name__ = app.blueprints.pubblico (per i template/errori)
pubblico_bp = Blueprint("pubblico", __name__)


# ============================================================================
# HOME
# GET  /  ->  home
# ============================================================================
@pubblico_bp.route("/")
def home():
    """Home: testo di presentazione, oppure saluto e ruolo se sei entrato."""
    return render_template("home.html")
