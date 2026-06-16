"""
web/core/middleware.py
----------------------
Verifica se o usuário está logado antes de permitir acesso às páginas.
Redireciona para /login/ caso não haja sessão válida.
"""

from django.shortcuts import redirect
from django.conf import settings


class AuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path

        
        publico = any(path.startswith(p) for p in settings.PUBLIC_PATHS)
        is_static = path.startswith("/static/")

        if not publico and not is_static:
            if not request.session.get("usuario_id"):
                return redirect(f"/login/?next={path}")

        return self.get_response(request)
