"""
WSGI config for Durama project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Durama.settings')

application = get_wsgi_application()


def _preparer_render():
    """
    Sur Render : applique les migrations et prépare les fichiers statiques au démarrage, même si
    la « Build Command » du tableau de bord se limite à « pip install -r requirements.txt ».
    Un verrou de fichier évite que plusieurs workers gunicorn le fassent en même temps.
    Désactivable avec AUTO_MIGRATE=0 (et la démo seule avec CHARGER_DEMO=0).
    """
    if os.environ.get("RENDER", "").lower() != "true" or os.environ.get("AUTO_MIGRATE", "1") == "0":
        return
    import fcntl  # Linux uniquement (serveurs Render)

    from django.conf import settings
    from django.core.management import call_command

    with open(settings.BASE_DIR / ".demarrage_render.lock", "w") as verrou:
        fcntl.flock(verrou, fcntl.LOCK_EX)
        try:
            call_command("migrate", interactive=False, verbosity=1)
            call_command("collectstatic", interactive=False, verbosity=0)
            # Phase de développement : produits de démonstration (sans doublons).
            # À désactiver avec CHARGER_DEMO=0 quand le catalogue réel sera en place.
            if os.environ.get("CHARGER_DEMO", "1") != "0":
                try:
                    call_command("charger_demo")
                except Exception as erreur:  # la démo ne doit jamais empêcher le site de démarrer
                    print(f"charger_demo ignoré : {erreur}")
        finally:
            fcntl.flock(verrou, fcntl.LOCK_UN)


_preparer_render()
