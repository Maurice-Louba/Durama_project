"""
Django settings for Durama project.

Les secrets et réglages qui changent entre le local et la production sont lus dans les
variables d'environnement (sur Render : Dashboard > Environment). En local, ils peuvent être
mis dans un fichier `.env` à la racine du projet (voir `.env.example`) ; ce fichier n'est
JAMAIS versionné.
"""

import importlib.util
import os
from datetime import timedelta
from pathlib import Path
from urllib.parse import unquote, urlparse

from django.core.exceptions import ImproperlyConfigured

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


def _charger_env(fichier):
    """Mini-lecteur de fichier .env (CLE=valeur). N'écrase pas une variable déjà définie."""
    if not fichier.exists():
        return
    for ligne in fichier.read_text(encoding="utf-8").splitlines():
        ligne = ligne.strip()
        if not ligne or ligne.startswith("#") or "=" not in ligne:
            continue
        cle, valeur = ligne.split("=", 1)
        os.environ.setdefault(cle.strip(), valeur.strip().strip('"').strip("'"))


_charger_env(BASE_DIR / ".env")


def env_bool(nom, defaut=False):
    valeur = os.environ.get(nom)
    if valeur is None:
        return defaut
    return valeur.strip().lower() in ("1", "true", "yes", "oui", "on")


def env_liste(nom):
    return [v.strip() for v in os.environ.get(nom, "").split(",") if v.strip()]


# Render définit automatiquement RENDER=true sur ses serveurs
EN_PRODUCTION = os.environ.get("RENDER", "").lower() == "true"

# SECURITY WARNING: don't run with debug turned on in production!
# Par défaut : activé en local, désactivé sur Render (forçable avec DJANGO_DEBUG=1/0)
DEBUG = env_bool("DJANGO_DEBUG", defaut=not EN_PRODUCTION)

# SECURITY WARNING: keep the secret key used in production secret!
# L'ancienne clé était écrite dans le code d'un dépôt public : elle ne doit plus servir
# (elle permettait de fabriquer des jetons JWT valides pour n'importe quel compte).
def _cle_secrete_de_secours():
    """
    Render sans variable SECRET_KEY : clé aléatoire (jamais écrite dans le code), partagée par
    tous les workers gunicorn via un fichier créé une seule fois. Elle change à chaque
    redémarrage du serveur -> les utilisateurs devront se reconnecter.
    Solution définitive : Render > Environment > SECRET_KEY (bouton « Generate »).
    """
    import secrets
    import sys

    fichier = BASE_DIR / ".cle_secrete_render"
    try:
        fd = os.open(fichier, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as f:
            f.write(secrets.token_urlsafe(64))
    except FileExistsError:
        pass  # un autre worker l'a déjà créée
    print(
        "ATTENTION : SECRET_KEY absente, clé temporaire générée. Ajoutez SECRET_KEY dans "
        "Render > Environment pour que les connexions survivent aux redémarrages.",
        file=sys.stderr,
    )
    return fichier.read_text().strip()


SECRET_KEY = os.environ.get("SECRET_KEY") or os.environ.get("DJANGO_SECRET_KEY")
if not SECRET_KEY:
    if EN_PRODUCTION:
        SECRET_KEY = _cle_secrete_de_secours()
    elif not DEBUG:
        raise ImproperlyConfigured(
            "La variable d'environnement SECRET_KEY est obligatoire en production."
        )
    else:
        SECRET_KEY = "dev-uniquement-cle-non-secrete-ne-pas-utiliser-en-production"

ALLOWED_HOSTS = [
    "localhost",
    "127.0.0.1",
    "durama-project.onrender.com",
    ".onrender.com",
    *env_liste("DJANGO_ALLOWED_HOSTS"),
]
if DEBUG:
    ALLOWED_HOSTS += ["earl-trademark-comic-pacific.trycloudflare.com", "testserver"]

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'DuramaProject',
    'rest_framework',
    'rest_framework.authtoken',
    'rest_framework_simplejwt',
    # Nécessaire pour que BLACKLIST_AFTER_ROTATION fonctionne vraiment
    # (sans cette app, l'invalidation des anciens refresh tokens était ignorée en silence)
    'rest_framework_simplejwt.token_blacklist',
    'drf_yasg',
    'corsheaders'
]

WHITENOISE_DISPONIBLE = importlib.util.find_spec("whitenoise") is not None

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    *(['whitenoise.middleware.WhiteNoiseMiddleware'] if WHITENOISE_DISPONIBLE else []),
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    # Réactivé : il protège l'admin Django (connexion par session). Les vues de l'API
    # (DRF + JWT/Token) en sont exemptées automatiquement, rien ne change pour le frontend.
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'Durama.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'Durama.wsgi.application'

# Database
# SQLite par défaut. PostgreSQL seulement si USE_POSTGRES=1 ET DATABASE_URL sont définis
# (render.yaml déclare déjà DATABASE_URL : le double interrupteur évite une bascule involontaire
# vers une base vide). Pour Postgres, ajouter aussi « psycopg[binary] » à requirements.txt.
DATABASE_URL = os.environ.get("DATABASE_URL", "")
if env_bool("USE_POSTGRES") and DATABASE_URL:
    _url = urlparse(DATABASE_URL)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': _url.path.lstrip('/'),
            'USER': unquote(_url.username or ''),
            'PASSWORD': unquote(_url.password or ''),
            'HOST': _url.hostname or '',
            'PORT': str(_url.port or 5432),
            'CONN_MAX_AGE': 60,
            'CONN_HEALTH_CHECKS': True,
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
            # Attend jusqu'à 20 s si la base est verrouillée au lieu d'échouer (« database is locked »)
            'OPTIONS': {'timeout': 20},
        }
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# REST Framework Configuration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        # TokenAuthentication retiré : aucun écran ne l'utilise (la connexion passe par JWT) et un
        # jeton DRF du compte superadmin a été publié dans data.json sur le dépôt public.
    ),
    # Filet de sécurité : une vue qui oublie de déclarer ses permissions est fermée par défaut.
    # (Toutes les vues publiques déclarent explicitement AllowAny.)
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    # Limitation de débit globale (anti-abus) + limite stricte sur la connexion
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': os.environ.get('THROTTLE_ANON', '200/min'),
        'user': os.environ.get('THROTTLE_USER', '600/min'),
        'connexion': os.environ.get('THROTTLE_CONNEXION', '10/min'),
    },
    # Pas de page HTML « browsable API » en production
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        *(['rest_framework.renderers.BrowsableAPIRenderer'] if DEBUG else []),
    ],
}

# JWT Settings
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=int(os.environ.get('JWT_ACCESS_HEURES', 24))),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=int(os.environ.get('JWT_REFRESH_JOURS', 7))),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
}

# CORS Configuration
CORS_ALLOW_ALL_ORIGINS = False

CORS_ALLOWED_ORIGINS = [
    "https://durama-front.vercel.app",
    *env_liste("CORS_ALLOWED_ORIGINS"),
]
if DEBUG:
    CORS_ALLOWED_ORIGINS += [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://192.168.56.1:5174",
        "https://earl-trademark-comic-pacific.trycloudflare.com",
    ]

CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

# CSRF (utilisé uniquement par l'admin Django)
CSRF_TRUSTED_ORIGINS = [
    "https://durama-front.vercel.app",
    "https://durama-project.onrender.com",
    *[o for o in CORS_ALLOWED_ORIGINS if o.startswith("http")],
]
CSRF_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_HTTPONLY = False

# Session (admin Django)
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_HTTPONLY = True

# Sécurité HTTPS en production (Render termine le HTTPS devant Django)
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = env_bool('SECURE_SSL_REDIRECT', True)
    # À augmenter (ex. 31536000) une fois sûr que tout le site est en HTTPS
    SECURE_HSTS_SECONDS = int(os.environ.get('SECURE_HSTS_SECONDS', 0))
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = 'same-origin'
    X_FRAME_OPTIONS = 'DENY'

# Limites d'upload (photos, images produits)
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024

# Internationalization
LANGUAGE_CODE = 'fr-fr'  # messages d'erreur de Django / DRF en français
TIME_ZONE = 'Africa/Conakry'
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
if WHITENOISE_DISPONIBLE and not DEBUG:
    STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
    }

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
# Sert les fichiers médias via Django même quand DEBUG=False (le disque de Render étant
# éphémère, prévoir à terme un stockage externe type Cloudinary / S3).
SERVE_MEDIA = env_bool('SERVE_MEDIA', True)

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom User Model
AUTH_USER_MODEL = "DuramaProject.User"

# Email Configuration
# SMTP seulement si un mot de passe est fourni ; sinon les emails s'affichent dans la console.
EMAIL_HOST = os.environ.get("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", 587))
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_TIMEOUT = 15  # évite de bloquer un worker si le serveur SMTP ne répond pas
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL") or EMAIL_HOST_USER or "no-reply@durama.com"
EMAIL_BACKEND = (
    "django.core.mail.backends.smtp.EmailBackend"
    if EMAIL_HOST_USER and EMAIL_HOST_PASSWORD
    else "django.core.mail.backends.console.EmailBackend"
)

# Logs : les erreurs 500 apparaissent dans les logs Render (avant, elles étaient perdues avec DEBUG=False)
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {'format': '[{asctime}] {levelname} {name}: {message}', 'style': '{'},
    },
    'handlers': {
        'console': {'class': 'logging.StreamHandler', 'formatter': 'simple'},
    },
    'root': {'handlers': ['console'], 'level': 'WARNING'},
    'loggers': {
        'django': {'handlers': ['console'], 'level': os.environ.get('DJANGO_LOG_LEVEL', 'INFO'), 'propagate': False},
        'DuramaProject': {'handlers': ['console'], 'level': 'INFO', 'propagate': False},
    },
}

# Swagger : documentation publique en local ; en production seulement si SWAGGER_PUBLIC=1
SWAGGER_PUBLIC = env_bool('SWAGGER_PUBLIC', DEBUG)
SWAGGER_SETTINGS = {
    "SECURITY_DEFINITIONS": {
        "Bearer": {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header"
        }
    }
}
