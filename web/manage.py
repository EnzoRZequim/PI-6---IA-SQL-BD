
"""web/manage.py — ponto de entrada Django."""

import os
import sys


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "projeto.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError("Django não encontrado. Rode: pip install django") from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
