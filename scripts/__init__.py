"""Script eseguibili a mano, fuori dal ciclo dell'applicazione web.

Si lanciano dalla cartella RADICE del progetto, con l'opzione -m:

    python -m scripts.init_db
    python -m scripts.seed

L'opzione -m serve a far trovare a Python il pacchetto "app". Entrando nella
cartella scripts/ e lanciando "python init_db.py" si ottiene invece
ModuleNotFoundError: No module named 'app'.
"""
