"""
auth/setup.py
-------------
Execute UMA VEZ para inicializar as tabelas de auth nos dois bancos.

Uso:
    python auth/setup.py

O que faz:
  - Cria as tabelas auth_cargos, auth_usuarios e auth_permissoes
    em biblioteca.sqlite e empresa.sqlite (se ainda não existirem).
  - Cria o usuário 'admin' com senha padrão 'admin123' em cada banco.

  IMPORTANTE: após rodar, trocar a senha do admin pelo painel.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from auth.models import inicializar_auth


BANCOS = [
    "./db/biblioteca.sqlite",
    "./db/empresa.sqlite",
]

SENHA_ADMIN_PADRAO = "admin123"


if __name__ == "__main__":
    print("=" * 60)
    print("Inicializando sistema de autenticação...")
    print("=" * 60)

    for caminho in BANCOS:
        if not os.path.exists(caminho):
            print(f"[AVISO] Banco não encontrado: {caminho} — pulando.")
            continue
        inicializar_auth(caminho, senha_admin=SENHA_ADMIN_PADRAO)

    print("=" * 60)
    print("Pronto! Acesse o painel em http://127.0.0.1:8000/")
    print(f"Login padrão → usuário: admin | senha: {SENHA_ADMIN_PADRAO}")
    print("⚠️  Troque a senha do admin após o primeiro acesso.")
    print("=" * 60)
