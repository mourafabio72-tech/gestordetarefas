"""Matriz de permissões do Gestor de Tarefas.

Cada usuário tem um `grupo` (papel = preset) e, opcionalmente, um JSON
`permissoes` que sobrescreve o preset ponto a ponto. A permissão efetiva
é `merge(PRESET[grupo], overrides)`. Usuário sem JSON herda 100% do preset.
"""
import json

# Recursos com nível graduado
NIVEL_ORDEM = {"nenhum": 0, "ver": 1, "editar": 2}
RECURSOS = ("empresas", "setores", "tarefas", "obrigacoes",
            "usuarios", "relatorios", "evalidador")
ESCOPOS = ("proprias", "setor", "todas")
FLAGS = ("alterar_prazo_legal", "alterar_prazo_tecnico", "dispensar_demanda",
         "apagar_anexo", "alocar_obrigacao", "disparar_emails")

# Todas as chaves válidas de uma permissão efetiva
CHAVES = set(RECURSOS) | {"escopo_tarefas"} | set(FLAGS)

PRESETS = {
    "admin": {
        "empresas": "editar", "setores": "editar", "tarefas": "editar",
        "obrigacoes": "editar", "usuarios": "editar", "relatorios": "editar",
        "evalidador": "editar", "escopo_tarefas": "todas",
        "alterar_prazo_legal": True, "alterar_prazo_tecnico": True,
        "dispensar_demanda": True, "apagar_anexo": True,
        "alocar_obrigacao": True, "disparar_emails": True,
    },
    "gestor": {
        "empresas": "editar", "setores": "editar", "tarefas": "editar",
        "obrigacoes": "editar", "usuarios": "ver", "relatorios": "ver",
        "evalidador": "editar", "escopo_tarefas": "todas",
        "alterar_prazo_legal": True, "alterar_prazo_tecnico": True,
        "dispensar_demanda": True, "apagar_anexo": False,
        "alocar_obrigacao": True, "disparar_emails": True,
    },
    "analista": {
        "empresas": "ver", "setores": "ver", "tarefas": "editar",
        "obrigacoes": "nenhum", "usuarios": "nenhum", "relatorios": "ver",
        "evalidador": "ver", "escopo_tarefas": "proprias",
        "alterar_prazo_legal": False, "alterar_prazo_tecnico": True,
        "dispensar_demanda": False, "apagar_anexo": False,
        "alocar_obrigacao": False, "disparar_emails": True,
    },
    "estagiario": {
        # Mais restrito que analista: edita só as próprias tarefas, sem mexer em prazos.
        "empresas": "ver", "setores": "ver", "tarefas": "editar",
        "obrigacoes": "nenhum", "usuarios": "nenhum", "relatorios": "ver",
        "evalidador": "nenhum", "escopo_tarefas": "proprias",
        "alterar_prazo_legal": False, "alterar_prazo_tecnico": False,
        "dispensar_demanda": False, "apagar_anexo": False,
        "alocar_obrigacao": False, "disparar_emails": False,
    },
    "consulta": {
        "empresas": "ver", "setores": "ver", "tarefas": "ver",
        "obrigacoes": "ver", "usuarios": "nenhum", "relatorios": "ver",
        "evalidador": "nenhum", "escopo_tarefas": "todas",
        "alterar_prazo_legal": False, "alterar_prazo_tecnico": False,
        "dispensar_demanda": False, "apagar_anexo": False,
        "alocar_obrigacao": False, "disparar_emails": False,
    },
}

# 'usuario' é o papel legado (default histórico). Mantém o comportamento
# anterior — só leitura, enxerga tudo — para NÃO quebrar contas existentes.
# Migrar para 'analista' quando quiser o escopo "só as próprias".
PRESETS["usuario"] = {
    "empresas": "ver", "setores": "ver", "tarefas": "ver",
    "obrigacoes": "ver", "usuarios": "nenhum", "relatorios": "ver",
    "evalidador": "nenhum", "escopo_tarefas": "todas",
    "alterar_prazo_legal": False, "alterar_prazo_tecnico": False,
    "dispensar_demanda": False, "apagar_anexo": False,
    "alocar_obrigacao": False, "disparar_emails": False,
}

PAPEIS = tuple(PRESETS.keys())


def preset_do_grupo(grupo: str) -> dict:
    """Cópia do preset do papel; papel desconhecido cai no mais restrito."""
    return dict(PRESETS.get(grupo, PRESETS["consulta"]))


def resolver(grupo: str, permissoes_json=None) -> dict:
    """Permissão efetiva = preset do papel + overrides do JSON (se houver)."""
    efetiva = preset_do_grupo(grupo)
    if permissoes_json:
        if isinstance(permissoes_json, str):
            try:
                overrides = json.loads(permissoes_json)
            except (ValueError, TypeError):
                overrides = {}
        elif isinstance(permissoes_json, dict):
            overrides = permissoes_json
        else:
            overrides = {}
        for chave, valor in overrides.items():
            if chave in CHAVES:
                efetiva[chave] = valor
    return efetiva


def pode(perm: dict, recurso: str, nivel: str = "ver") -> bool:
    """True se a permissão efetiva atinge ao menos `nivel` no recurso."""
    atual = perm.get(recurso, "nenhum")
    return NIVEL_ORDEM.get(atual, 0) >= NIVEL_ORDEM.get(nivel, 0)


def tem_flag(perm: dict, flag: str) -> bool:
    return bool(perm.get(flag, False))
