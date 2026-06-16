"""
web/core/views.py
-----------------
Views Django para login, painel admin e chat com IA.
"""

import sys
import os
import json

from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.conf import settings

# Adiciona a raiz do projeto ao path para importar auth e IA
sys.path.insert(0, str(settings.PROJECT_ROOT))

import auth.models as auth_db


# ---------------------------------------------------------------------------
# Helpers de sessão
# ---------------------------------------------------------------------------

def sessao_usuario(request) -> dict | None:
    uid = request.session.get("usuario_id")
    if not uid:
        return None
    return {
        "id":         uid,
        "username":   request.session.get("username"),
        "is_admin":   request.session.get("is_admin", False),
        "cargo_id":   request.session.get("cargo_id"),
        "cargo_nome": request.session.get("cargo_nome"),
        "banco_ativo":request.session.get("banco_ativo"),
    }


def exige_admin(view_func):
    """Decorador: redireciona para home se não for admin."""
    def wrapper(request, *args, **kwargs):
        u = sessao_usuario(request)
        if not u or not u["is_admin"]:
            return redirect("/")
        return view_func(request, *args, **kwargs)
    return wrapper


def db_path_ativo(request) -> str | None:
    banco = request.session.get("banco_ativo")
    if banco:
        return settings.DB_PATHS.get(banco)
    return None


# ---------------------------------------------------------------------------
# Login / Logout
# ---------------------------------------------------------------------------

def login_view(request):
    erro = None

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        senha    = request.POST.get("senha", "").strip()
        banco    = request.POST.get("banco", "biblioteca")

        db_path = settings.DB_PATHS.get(banco)
        if not db_path:
            erro = "Banco inválido."
        else:
            usuario = auth_db.autenticar(db_path, username, senha)
            if usuario:
                request.session["usuario_id"]  = usuario["id"]
                request.session["username"]     = usuario["username"]
                request.session["is_admin"]     = bool(usuario["is_admin"])
                request.session["cargo_id"]     = usuario["cargo_id"]
                request.session["cargo_nome"]   = usuario["cargo_nome"]
                request.session["banco_ativo"]  = banco
                next_url = request.GET.get("next", "/")
                return redirect(next_url)
            else:
                erro = "Usuário ou senha inválidos."

    return render(request, "login.html", {
        "erro": erro,
        "bancos": list(settings.DB_PATHS.keys()),
    })


def logout_view(request):
    request.session.flush()
    return redirect("/login/")


# ---------------------------------------------------------------------------
# Seleção de banco
# ---------------------------------------------------------------------------

def selecionar_banco(request, nome=None):
    u = sessao_usuario(request)
    if not u:
        return redirect("/login/")

    if nome and nome in settings.DB_PATHS:
        request.session["banco_ativo"] = nome
        return redirect("/chat/")

    return render(request, "selecionar_banco.html", {
        "usuario": u,
        "bancos": list(settings.DB_PATHS.keys()),
        "banco_ativo": u["banco_ativo"],
    })


# ---------------------------------------------------------------------------
# Chat / IA
# ---------------------------------------------------------------------------

def chat_view(request):
    u = sessao_usuario(request)
    if not u:
        return redirect("/login/")

    banco = u["banco_ativo"]
    if not banco:
        return redirect("/")

    db_path = settings.DB_PATHS[banco]

    # Descobre tabelas e colunas visíveis para o usuário
    import sqlite3
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name NOT LIKE 'auth_%';")
    todas_tabelas = [r[0] for r in cursor.fetchall()]

    if u["is_admin"]:
        tabelas_visiveis = todas_tabelas
        colunas_visiveis = {}
        for t in todas_tabelas:
            cursor.execute(f"PRAGMA table_info({t});")
            colunas_visiveis[t] = [r[1] for r in cursor.fetchall()]
    else:
        permissoes = auth_db.obter_permissoes(db_path, u["cargo_id"]) if u["cargo_id"] else []
        tabelas_visiveis = []
        colunas_visiveis = {}
        for t in todas_tabelas:
            cursor.execute(f"PRAGMA table_info({t});")
            cols_todas = [r[1] for r in cursor.fetchall()]
            cols_ok = auth_db.filtrar_colunas_permitidas(permissoes, banco, t, cols_todas)
            if cols_ok:
                tabelas_visiveis.append(t)
                colunas_visiveis[t] = cols_ok

    conn.close()

    return render(request, "chat.html", {
        "usuario": u,
        "banco": banco,
        "tabelas_visiveis": tabelas_visiveis,
        "colunas_visiveis": json.dumps(colunas_visiveis),
    })


@require_POST
def chat_query(request):
    """Recebe pergunta via AJAX, chama IA.py e retorna resposta JSON."""
    u = sessao_usuario(request)
    if not u:
        return JsonResponse({"erro": "Não autenticado."}, status=401)

    banco = u["banco_ativo"]
    if not banco:
        return JsonResponse({"erro": "Nenhum banco selecionado."}, status=400)

    db_path = settings.DB_PATHS[banco]

    try:
        body = json.loads(request.body)
        pergunta = body.get("pergunta", "").strip()
    except Exception:
        return JsonResponse({"erro": "Requisição inválida."}, status=400)

    if not pergunta:
        return JsonResponse({"erro": "Pergunta vazia."}, status=400)

    # Permissões do usuário
    if u["is_admin"]:
        permissoes = None  # admin vê tudo
    else:
        permissoes = auth_db.obter_permissoes(db_path, u["cargo_id"]) if u["cargo_id"] else []

    # Chama a lógica do IA.py via função importada
    try:
        from ia_bridge import consultar_ia
        resultado = consultar_ia(db_path, banco, pergunta, permissoes)
        return JsonResponse(resultado)
    except Exception as e:
        return JsonResponse({"erro": str(e)}, status=500)


# ---------------------------------------------------------------------------
# Painel Admin
# ---------------------------------------------------------------------------

@exige_admin
def admin_panel(request):
    u = sessao_usuario(request)
    db_path = db_path_ativo(request)

    usuarios = auth_db.listar_usuarios(db_path)
    cargos   = auth_db.listar_cargos(db_path)

    return render(request, "admin_panel.html", {
        "usuario": u,
        "usuarios": usuarios,
        "cargos": cargos,
        "banco": request.session.get("banco_ativo"),
    })


@exige_admin
def admin_criar_usuario(request):
    if request.method == "POST":
        db_path = db_path_ativo(request)
        username  = request.POST.get("username", "").strip()
        senha     = request.POST.get("senha", "").strip()
        cargo_id  = request.POST.get("cargo_id") or None
        is_admin  = int(request.POST.get("is_admin", 0))

        if username and senha:
            auth_db.criar_usuario(db_path, username, senha, cargo_id, is_admin)

    return redirect("/admin/")


@exige_admin
def admin_atribuir_cargo(request, uid):
    if request.method == "POST":
        db_path  = db_path_ativo(request)
        cargo_id = request.POST.get("cargo_id") or None
        auth_db.atualizar_cargo_usuario(db_path, uid, cargo_id)
    return redirect("/admin/")


@exige_admin
def admin_deletar_usuario(request, uid):
    if request.method == "POST":
        db_path = db_path_ativo(request)
        auth_db.deletar_usuario(db_path, uid)
    return redirect("/admin/")


@exige_admin
def admin_criar_cargo(request):
    if request.method == "POST":
        db_path   = db_path_ativo(request)
        nome      = request.POST.get("nome", "").strip()
        descricao = request.POST.get("descricao", "").strip()
        if nome:
            auth_db.criar_cargo(db_path, nome, descricao)
    return redirect("/admin/")


@exige_admin
def admin_deletar_cargo(request, cid):
    if request.method == "POST":
        db_path = db_path_ativo(request)
        auth_db.deletar_cargo(db_path, cid)
    return redirect("/admin/")


@exige_admin
def admin_permissoes_cargo(request, cid):
    u       = sessao_usuario(request)
    db_path = db_path_ativo(request)
    banco   = request.session.get("banco_ativo")

    import sqlite3

    # Monta mapa completo de tabelas/colunas do banco ativo
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name NOT LIKE 'auth_%';")
    tabelas = [r[0] for r in cursor.fetchall()]
    schema = {}
    for t in tabelas:
        cursor.execute(f"PRAGMA table_info({t});")
        schema[t] = [r[1] for r in cursor.fetchall()]
    conn.close()

    cargo_row = next((c for c in auth_db.listar_cargos(db_path) if c["id"] == cid), None)
    permissoes_atuais = auth_db.listar_permissoes_cargo(db_path, cid)

    # Indexa permissões atuais para checagem no template
    perms_set = {(p["banco"], p["tabela"], p["coluna"]) for p in permissoes_atuais}

    if request.method == "POST":
        novas = []
        for tabela, colunas in schema.items():
            for coluna in colunas:
                campo = f"{tabela}_{coluna}"
                if request.POST.get(campo):
                    novas.append({"banco": banco, "tabela": tabela, "coluna": coluna})
        auth_db.definir_permissoes_cargo(db_path, cid, novas)
        return redirect("/admin/")

    return render(request, "permissoes_cargo.html", {
        "usuario":   u,
        "cargo":     cargo_row,
        "schema":    schema,
        "banco":     banco,
        "perms_set": perms_set,
        "perms_json": json.dumps(permissoes_atuais),
    })
