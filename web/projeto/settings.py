"""
web/projeto/settings.py
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "TROQUE-ESTA-CHAVE-EM-PRODUCAO-abc123xyz"

DEBUG = True

ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.staticfiles",
    "core",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",  
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "core.middleware.AuthMiddleware",  
]

ROOT_URLCONF = "projeto.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "core" / "templates"],
        "APP_DIRS": False,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
            ],
        },
    },
]


SESSION_ENGINE = "django.contrib.sessions.backends.file"
SESSION_FILE_PATH = BASE_DIR / ".sessions"
SESSION_FILE_PATH.mkdir(exist_ok=True)
SESSION_COOKIE_AGE = 3600  # 1 hora

STATIC_URL = "/static/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


PROJECT_ROOT = BASE_DIR.parent  

DB_PATHS = {
    "biblioteca": str(PROJECT_ROOT / "db" / "biblioteca.sqlite"),
    "empresa":    str(PROJECT_ROOT / "db" / "empresa.sqlite"),
}


PUBLIC_PATHS = ["/login/", "/logout/"]
