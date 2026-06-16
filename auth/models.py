"""
auth/models.py
--------------
Define e inicializa as tabelas de autenticação e controle de acesso
dentro de um banco SQLite existente (biblioteca.sqlite ou empresa.sqlite).

Tabelas criadas:
  - auth_cargos         : cargos criados pelo admin
  - auth_usuarios       : usuários do sistema de login
  - auth_permissoes     : quais (banco, tabela, coluna) cada cargo pode ver
"""

import sqlite3
import hashlib
import os



SQL_CRIAR_TABELAS = """
CREATE TABLE IF NOT EXISTS auth_cargos (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nome        TEXT    NOT NULL UNIQUE,
    descricao   TEXT,
    criado_em   TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS auth_usuarios (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    username        TEXT    NOT NULL UNIQUE,
    senha_hash      TEXT    NOT NULL,
    cargo_id        INTEGER,
    is_admin        INTEGER NOT NULL DEFAULT 0,   -- 1 = administrador
    ativo           INTEGER NOT NULL DEFAULT 1,
    criado_em       TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (cargo_id) REFERENCES auth_cargos(id)
);

CREATE TABLE IF NOT EXISTS auth_permissoes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    cargo_id    INTEGER NOT NULL,
    banco       TEXT    NOT NULL,   -- 'biblioteca' ou 'empresa'
    tabela      TEXT    NOT NULL,   -- nome da tabela; '*' = todas
    coluna      TEXT    NOT NULL,   -- nome da coluna; '*' = todas
    UNIQUE (cargo_id, banco, tabela, coluna),
    FOREIGN KEY (cargo_id) REFERENCES auth_cargos(id)
);
"""



def hash_senha(senha: str) -> str:
    """Retorna SHA-256 da senha em hex."""
    return hashlib.sha256(senha.encode()).hexdigest()


def get_conn(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn



def inicializar_auth(db_path: str, senha_admin: str = "admin123") -> None:
    """
    Cria as tabelas de auth no banco indicado e garante que o usuário
    'admin' exista com is_admin=1.

    Chamado por auth/setup.py na primeira execução.
    """
    conn = get_conn(db_path)
    try:
        conn.executescript(SQL_CRIAR_TABELAS)
        conn.commit()

        
        existe = conn.execute(
            "SELECT id FROM auth_usuarios WHERE username = 'admin'"
        ).fetchone()

        if not existe:
            conn.execute(
                """
                INSERT INTO auth_usuarios (username, senha_hash, is_admin)
                VALUES ('admin', ?, 1)
                """,
                (hash_senha(senha_admin),),
            )
            conn.commit()
            print(f"[auth] Admin padrão criado em '{db_path}' (senha: {senha_admin})")
        else:
            print(f"[auth] Tabelas já inicializadas em '{db_path}'.")
    finally:
        conn.close()



def autenticar(db_path: str, username: str, senha: str) -> dict | None:
    """
    Retorna dict com dados do usuário se credenciais forem válidas,
    ou None em caso de falha.
    """
    conn = get_conn(db_path)
    try:
        row = conn.execute(
            """
            SELECT u.id, u.username, u.is_admin, u.ativo, u.cargo_id,
                   c.nome AS cargo_nome
            FROM auth_usuarios u
            LEFT JOIN auth_cargos c ON c.id = u.cargo_id
            WHERE u.username = ? AND u.senha_hash = ? AND u.ativo = 1
            """,
            (username, hash_senha(senha)),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def obter_permissoes(db_path: str, cargo_id: int) -> list[dict]:
    """Retorna lista de permissões do cargo."""
    conn = get_conn(db_path)
    try:
        rows = conn.execute(
            "SELECT banco, tabela, coluna FROM auth_permissoes WHERE cargo_id = ?",
            (cargo_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def usuario_pode_ver(permissoes: list[dict], banco: str, tabela: str, coluna: str) -> bool:
    """
    Verifica se a lista de permissões do usuário permite ver
    banco/tabela/coluna específicos.
    Admin sempre pode ver tudo (checar is_admin antes de chamar).
    """
    for p in permissoes:
        banco_ok  = p["banco"]  in (banco,   "*")
        tabela_ok = p["tabela"] in (tabela,  "*")
        coluna_ok = p["coluna"] in (coluna,  "*")
        if banco_ok and tabela_ok and coluna_ok:
            return True
    return False


def filtrar_colunas_permitidas(
    permissoes: list[dict], banco: str, tabela: str, colunas: list[str]
) -> list[str]:
    """
    Dado um banco/tabela e uma lista de colunas retornadas pelo SQL,
    filtra apenas as que o usuário tem permissão de ver.
    """
    return [c for c in colunas if usuario_pode_ver(permissoes, banco, tabela, c)]


def listar_usuarios(db_path: str) -> list[dict]:
    conn = get_conn(db_path)
    try:
        rows = conn.execute(
            """
            SELECT u.id, u.username, u.is_admin, u.ativo, u.criado_em,
                   c.nome AS cargo_nome
            FROM auth_usuarios u
            LEFT JOIN auth_cargos c ON c.id = u.cargo_id
            ORDER BY u.id
            """
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def criar_usuario(db_path: str, username: str, senha: str, cargo_id: int | None = None, is_admin: int = 0) -> None:
    conn = get_conn(db_path)
    try:
        conn.execute(
            "INSERT INTO auth_usuarios (username, senha_hash, cargo_id, is_admin) VALUES (?, ?, ?, ?)",
            (username, hash_senha(senha), cargo_id, is_admin),
        )
        conn.commit()
    finally:
        conn.close()


def atualizar_cargo_usuario(db_path: str, usuario_id: int, cargo_id: int | None) -> None:
    conn = get_conn(db_path)
    try:
        conn.execute(
            "UPDATE auth_usuarios SET cargo_id = ? WHERE id = ?",
            (cargo_id, usuario_id),
        )
        conn.commit()
    finally:
        conn.close()


def deletar_usuario(db_path: str, usuario_id: int) -> None:
    conn = get_conn(db_path)
    try:
        conn.execute("DELETE FROM auth_usuarios WHERE id = ? AND is_admin = 0", (usuario_id,))
        conn.commit()
    finally:
        conn.close()


def listar_cargos(db_path: str) -> list[dict]:
    conn = get_conn(db_path)
    try:
        rows = conn.execute("SELECT * FROM auth_cargos ORDER BY id").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def criar_cargo(db_path: str, nome: str, descricao: str = "") -> int:
    conn = get_conn(db_path)
    try:
        cur = conn.execute(
            "INSERT INTO auth_cargos (nome, descricao) VALUES (?, ?)", (nome, descricao)
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def deletar_cargo(db_path: str, cargo_id: int) -> None:
    conn = get_conn(db_path)
    try:
        conn.execute("DELETE FROM auth_permissoes WHERE cargo_id = ?", (cargo_id,))
        conn.execute("UPDATE auth_usuarios SET cargo_id = NULL WHERE cargo_id = ?", (cargo_id,))
        conn.execute("DELETE FROM auth_cargos WHERE id = ?", (cargo_id,))
        conn.commit()
    finally:
        conn.close()


def definir_permissoes_cargo(db_path: str, cargo_id: int, permissoes: list[dict]) -> None:
    """
    Substitui todas as permissões do cargo pela nova lista.
    Cada item de permissoes deve ter: banco, tabela, coluna.
    """
    conn = get_conn(db_path)
    try:
        conn.execute("DELETE FROM auth_permissoes WHERE cargo_id = ?", (cargo_id,))
        conn.executemany(
            "INSERT OR IGNORE INTO auth_permissoes (cargo_id, banco, tabela, coluna) VALUES (?, ?, ?, ?)",
            [(cargo_id, p["banco"], p["tabela"], p["coluna"]) for p in permissoes],
        )
        conn.commit()
    finally:
        conn.close()


def listar_permissoes_cargo(db_path: str, cargo_id: int) -> list[dict]:
    conn = get_conn(db_path)
    try:
        rows = conn.execute(
            "SELECT banco, tabela, coluna FROM auth_permissoes WHERE cargo_id = ?",
            (cargo_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
