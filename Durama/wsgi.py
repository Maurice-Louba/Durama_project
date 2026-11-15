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
    Désactivable avec AUTO_MIGRATE=0.
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
        finally:
            fcntl.flock(verrou, fcntl.LOCK_UN)


_preparer_render()
