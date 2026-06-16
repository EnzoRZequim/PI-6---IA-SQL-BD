"""
ia_bridge.py
------------
Ponte entre o Django (views.py) e a lógica do IA.py.
Fica na RAIZ do projeto, ao lado do IA.py.

Importado por web/core/views.py via:
    from ia_bridge import consultar_ia

O que faz:
  - Recebe pergunta + db_path + permissões do usuário
  - Chama as funções do IA.py (sem abrir loop interativo)
  - Filtra colunas do resultado conforme permissões
  - Retorna dict com sql, colunas, linhas, resposta
"""

import sqlite3
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from IA import (
    gerar_sql,
    limpar_sql,
    sql_valido,
    regenerar_sql_com_erro,
    executar_sql_readonly,
    montar_resposta_direta,
    obter_schema,
    obter_mapa_colunas,
    carregar_arquivo_texto,
    montar_exemplos_prompt,
    obter_exemplos_bd_path,
    MODEL_SQL,
    EXEMPLOS_GERAIS_PATH,
)
from langchain_ollama import OllamaLLM
import auth.models as auth_db



_llm_cache: dict = {}


def _get_llm() -> OllamaLLM:
    if "sql" not in _llm_cache:
        _llm_cache["sql"] = OllamaLLM(model=MODEL_SQL)
    return _llm_cache["sql"]


def consultar_ia(
    db_path: str,
    banco_nome: str,
    pergunta: str,
    permissoes: list[dict] | None,
) -> dict:
    """
    Parâmetros:
        db_path     : caminho para o .sqlite
        banco_nome  : 'biblioteca' ou 'empresa'
        pergunta    : pergunta em linguagem natural
        permissoes  : lista de dicts {banco, tabela, coluna}
                      ou None (admin, sem restrições)

    Retorna dict:
        {
          "sql": str,
          "colunas": list[str],
          "linhas": list[list],
          "resposta": str,
          "erro": str | None
        }
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        schema       = obter_schema(cursor)
        mapa_colunas = obter_mapa_colunas(cursor)
        exemplos_bd  = carregar_arquivo_texto(obter_exemplos_bd_path(db_path))
        exemplos_g   = carregar_arquivo_texto(EXEMPLOS_GERAIS_PATH)
        exemplos     = montar_exemplos_prompt(exemplos_bd, exemplos_g)
        llm          = _get_llm()

        
        sql_bruto = gerar_sql(llm, schema, mapa_colunas, pergunta, exemplos)
        sql       = limpar_sql(sql_bruto)
        valido, motivo = sql_valido(sql)

        if not valido:
            return {"sql": sql, "colunas": [], "linhas": [], "resposta": "", "erro": f"SQL bloqueado: {motivo}"}

        
        try:
            colunas, linhas = executar_sql_readonly(cursor, sql)
        except Exception as e_exec:
            err_str = str(e_exec)
            if "no such column" in err_str.lower() or "no such table" in err_str.lower():
                sql_bruto = regenerar_sql_com_erro(llm, schema, mapa_colunas, pergunta, sql, err_str, exemplos)
                sql = limpar_sql(sql_bruto)
                valido, motivo = sql_valido(sql)
                if not valido:
                    return {"sql": sql, "colunas": [], "linhas": [], "resposta": "", "erro": f"SQL regenerado bloqueado: {motivo}"}
                colunas, linhas = executar_sql_readonly(cursor, sql)
            else:
                return {"sql": sql, "colunas": [], "linhas": [], "resposta": "", "erro": err_str}


        tabela_principal = _inferir_tabela(sql)

        if permissoes is not None and tabela_principal:
            indices_ok = [
                i for i, col in enumerate(colunas)
                if auth_db.usuario_pode_ver(permissoes, banco_nome, tabela_principal, col)
            ]
            colunas = [colunas[i] for i in indices_ok]
            linhas  = [[linha[i] for i in indices_ok] for linha in linhas]

        resposta = montar_resposta_direta(colunas, linhas)

        return {
            "sql":     sql,
            "colunas": colunas,
            "linhas":  [list(l) for l in linhas],
            "resposta": resposta,
            "erro":    None,
        }

    finally:
        conn.close()


def _inferir_tabela(sql: str) -> str:
    """Extrai o nome da primeira tabela após FROM no SQL (melhor esforço)."""
    import re
    match = re.search(r"\bFROM\s+(\w+)", sql, re.IGNORECASE)
    return match.group(1) if match else ""
