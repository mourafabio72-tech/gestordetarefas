"""Conversa em texto da janela do mascote (2026-10-14, o modelo do FinControl).

Pedido do Fábio: "aplique esse modelo para os demais apps". Até aqui a janela
usava o /ia/perguntar, em que a IA só traduz a pergunta num filtro e o Tareffas
lista as tarefas. Agora ela conversa: o Tareffas monta os números das tarefas
no ESCOPO de quem pergunta e a IA responde em texto. O /ia/perguntar segue.

DECISÕES QUE VALEM SER LIDAS ANTES DE MEXER AQUI:

1. NOME DE EMPRESA ATENDIDA E DE PESSOA NÃO SAI. Empresa vira X01, pessoa vira
   P01, achados e trocados aqui, e destrocados na resposta. Prefixos distintos
   para a IA não confundir empresa com pessoa. CNPJ, descrição e comprovante não
   saem; o título da tarefa sai com o nome da própria empresa trocado pelo
   código. Decisão do Fábio em 2026-10-14 ("pode, como no FinControl"), que
   troca a regra antiga desta janela (só a pergunta saía).
2. O ESCOPO É O DA TELA DE TAREFAS: `_aplicar_escopo`, o mesmo corte da lista.
3. PRECISÃO: gpt-4.1-mini na OpenAI (ou OPENAI_MODEL), temperatura 0,
   histórico de 4, instruções que proíbem estimar.
"""
from __future__ import annotations

import json
import os
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import date, timedelta

import httpx

from . import ia as ia_mod

MAX_HISTORICO = 4
MAX_TEXTO_HISTORICO = 2000
MAX_LISTA = 80
TOP = 30
MAX_CITADOS = 8
MAX_POR_TERMO = 4
MODELO_OPENAI = "gpt-4.1-mini"

INSTRUCOES = """Você é o assistente do Tareffas, o gestor de tarefas e obrigações acessórias da BPS4 (escritório de contabilidade).
Responda SOMENTE com base nos DADOS em JSON que vêm a seguir, que já estão no escopo de quem pergunta.
Se o dado não estiver lá, diga que não tem; nunca estime, complete ou invente tarefa, prazo, empresa ou pessoa.

QUEM É QUEM:
- Empresas atendidas (clientes da BPS4) aparecem como X01, X02...; pessoas da equipe aparecem como P01, P02...
  Nunca troque um pelo outro. Escreva o código exatamente como veio; o sistema troca pelo nome antes de mostrar.
- "voce" é o código de quem está perguntando ("minhas tarefas" = as que têm esse código como responsável).

OS DADOS:
- "resumo": contagem das tarefas abertas, atrasadas, que vencem hoje e nos próximos 7 dias, e concluídas no mês.
- "por_setor", "por_responsavel", "por_empresa": as mesmas contagens separadas.
- "atrasadas", "vencem_hoje", "proximos_7_dias": as tarefas, com obrigação, competência (MM/AAAA), empresa,
  setor, prazo interno e vencimento legal. "Atrasada" é a tarefa aberta com prazo antes de hoje.
- Datas vêm como AAAA-MM-DD. Escreva "13/10" ou "13 de outubro".
- Se a pergunta cita uma empresa ou pessoa que não virou código, diga que não achou no seu acesso.

COMO RESPONDER: português do Brasil, curto e direto; lista quando houver mais de dois itens; em cada tarefa
listada, diga a obrigação, a empresa e o prazo."""


# ---- Nomes citados: achar, codificar, destrocar (o mesmo do FinControl) ------

GENERICAS = set((
    "comercio servicos servico industria engenharia energia solar construcoes construtora consultoria "
    "assessoria contabilidade contabil transportes transporte distribuidora representacoes empreendimentos "
    "participacoes holding tecnologia sistemas solucoes grupo brasil brasileira nacional materiais produtos "
    "alimentos importacao exportacao administracao administradora associacao condominio instituto centro "
    "clinica hotel hoteis restaurante posto banco caixa receita federal prefeitura municipal estado governo "
    "secretaria fundo cliente fornecedor empresa pagou pagamento hoje semana valor quanto clientes "
    "fornecedores empresas pagamentos recebimento recebimentos recebido recebidos recebeu pago pagos pagar "
    "receber aberto vencido vencidos vencer venceu ontem amanha mes ano dia dias todas todos todo liste "
    "lista listar mostre mostra olhe existe existem quais qual quem onde quando como total totais valores "
    "saldo saldos conta contas despesa despesas receitas maior maiores menor menores faturou faturamento "
    "gastou gasto gastos custo custos lucro resultado margem mkb gnileb consolidado janeiro fevereiro marco "
    "abril maio junho julho agosto setembro outubro novembro dezembro ltda eireli tarefa tarefas obrigacao obrigacoes "
    "atrasada atrasadas atrasado atrasados pendente pendentes concluida concluidas aberta abertas vence vencem "
    "prazo prazos setor setores fiscal pessoal responsavel responsaveis minhas meus minha meu dctfweb reinf efd "
    "sped esocial darf das gia ecd ecf balancete folha"
).split())
_SUFIXOS = ("ltda", "me", "epp", "eireli", "s a", "sa", "s/a", "mei", "ss", "limitada")


def sem_acento(t) -> str:
    t = unicodedata.normalize("NFD", str(t or "")).encode("ascii", "ignore").decode().lower()
    return " ".join(re.sub(r"[^a-z0-9]+", " ", t).split())


def chave_do_nome(nome) -> str:
    """Núcleo do nome: sem acento, caixa, pontuação e forma jurídica no fim."""
    t = sem_acento(nome)
    mudou = True
    while mudou and t:
        mudou = False
        for suf in _SUFIXOS:
            if t.endswith(" " + suf) and len(t) > len(suf) + 1:
                t = t[: -len(suf) - 1].strip()
                mudou = True
    return t


def rotulo_do_nome(nome) -> str:
    return " ".join(str(nome or "").split()).title()


_VARIANTES = {"a": "aáàâãä", "e": "eéèêë", "i": "iíìîï", "o": "oóòôõö", "u": "uúùûü", "c": "cç"}
_FORA = r"[^0-9A-Za-zÀ-ÿ]"


def _regex_do_termo(termo: str):
    corpo = f"{_FORA}+".join("".join(f"[{_VARIANTES[ch]}]" if ch in _VARIANTES else re.escape(ch) for ch in w)
                             for w in termo.split())
    return re.compile(rf"(^|{_FORA})({corpo})(?=$|{_FORA})", re.IGNORECASE)


def pseudonimizar(pergunta: str, historico: list, nomes: list, prefixo: str = "X") -> dict:
    """Acha os nomes citados (inteiros, ou por palavra/par de palavras contido no
    nome sem espaços) e troca por código. Devolve pergunta e histórico já
    codificados e a lista `citados` [{codigo, nomes, rotulo}]."""
    grupos: dict[str, dict] = {}
    for n in nomes or []:
        k = chave_do_nome(n)
        if not k:
            continue
        marca = next((w for w in k.split() if len(w) >= 4 and not w.isdigit() and w not in GENERICAS), None)
        g = grupos.setdefault(k, {"nucleo": k, "compacto": k.replace(" ", ""), "nomes": [], "marca": marca})
        if n not in g["nomes"]:
            g["nomes"].append(n)
    textos = [pergunta or ""] + [str((h or {}).get("texto") or "") for h in historico or []]
    palavras = sem_acento(" \n ".join(textos)).split()
    alvo = " " + " ".join(palavras) + " "
    termos_de: dict[str, set] = {}
    for k, g in grupos.items():
        if f" {k} " in alvo:
            termos_de.setdefault(k, set()).add(k)
    candidatos = set(palavras) | {f"{a} {b}" for a, b in zip(palavras, palavras[1:])}
    for termo in candidatos:
        ws = termo.split()
        if any(w in GENERICAS or len(w) < 2 for w in ws):
            continue
        compacto = "".join(ws)
        if compacto.isdigit():
            continue
        hits = [g for g in grupos.values()
                if (len(compacto) >= 5 and compacto in g["compacto"]) or (len(ws) == 1 and g["marca"] == termo)]
        if hits and len(hits) <= MAX_POR_TERMO:
            for g in hits:
                termos_de.setdefault(g["nucleo"], set()).add(termo)
    achados = sorted(termos_de, key=lambda k: k)[:MAX_CITADOS]
    citados = []
    for i, k in enumerate(achados, 1):
        g = grupos[k]
        termos = set(termos_de[k]) | {g["nucleo"]} | ({g["marca"]} if g["marca"] else set())
        citados.append({"codigo": f"{prefixo}{i:02d}", "nomes": g["nomes"], "termos": termos,
                        "rotulo": rotulo_do_nome(max(g["nomes"], key=len))})
    por_termo: dict[str, list] = {}
    for c in citados:
        for t in c["termos"]:
            por_termo.setdefault(t, []).append(c["codigo"])

    def codificar(texto: str) -> str:
        t = str(texto or "")
        for termo in sorted(por_termo, key=len, reverse=True):
            t = _regex_do_termo(termo).sub(lambda m, cod="/".join(por_termo[termo]): m.group(1) + cod, t)
        return t

    return {"pergunta": codificar(pergunta),
            "historico": [{**h, "texto": codificar((h or {}).get("texto"))} for h in historico or []],
            "citados": [{k: c[k] for k in ("codigo", "nomes", "rotulo")} for c in citados]}


class Codificador:
    """Código para os clientes e fornecedores que aparecem nos DADOS: o citado
    mantém o código que já tem; os outros ganham os seguintes."""
    def __init__(self, citados: list, prefixo: str = "X"):
        self.prefixo = prefixo
        self.lista = list(citados)
        self._por_chave = {chave_do_nome(n): c["codigo"] for c in citados for n in c["nomes"]}

    def codigo(self, nome) -> str | None:
        k = chave_do_nome(nome)
        if not k:
            return None
        if k not in self._por_chave:
            cod = f"{self.prefixo}{len(self.lista) + 1:02d}"
            self._por_chave[k] = cod
            self.lista.append({"codigo": cod, "nomes": [nome], "rotulo": rotulo_do_nome(nome)})
        return self._por_chave[k]


def destrocar(texto: str, citados: list) -> str:
    mapa = {c["codigo"]: c["rotulo"] for c in citados}
    return re.sub(r"\b[XP]\d{2,3}\b", lambda m: mapa.get(m.group(0), m.group(0)), str(texto or ""))



# ---- Os dados ----------------------------------------------------------------

def _dia(dt):
    return dt.date() if hasattr(dt, "date") else dt


def _iso(d):
    return d.isoformat() if d else None


def montar_contexto(pergunta: str, historico: list, tarefas: list, hoje: date, usuario) -> tuple:
    """(pergunta codificada, histórico codificado, JSON dos dados, lista para destrocar).
    `tarefas` já vem no escopo de quem pergunta, sem as canceladas."""
    empresas = {}
    pessoas = {}
    for t in tarefas:
        if t.empresa:
            empresas[t.empresa_id] = t.empresa
        for r in (t.responsaveis or []):
            pessoas[r.id] = r
    pessoas[usuario.id] = usuario
    nomes_emp = [n for e in empresas.values() for n in (e.razao_social, e.nome_fantasia) if n]
    nomes_pes = [p.nome for p in pessoas.values() if p.nome]
    c_emp = pseudonimizar(pergunta, historico, nomes_emp, "X")
    c_pes = pseudonimizar(c_emp["pergunta"], c_emp["historico"], nomes_pes, "P")
    cod_emp = Codificador(c_emp["citados"], "X")
    cod_pes = Codificador(c_pes["citados"], "P")

    def emp_cod(t):
        return cod_emp.codigo(t.empresa.razao_social or t.empresa.nome_fantasia) if t.empresa else None

    def resp_cod(t):
        rs = t.responsaveis or []
        return [cod_pes.codigo(r.nome) for r in rs if r.nome] or None

    def titulo(t):
        # O título carrega, quase sempre, o nome da própria empresa: ele sai trocado pelo código.
        txt = t.obrigacao.nome if t.obrigacao and t.obrigacao.nome else (t.titulo or "")
        if t.empresa:
            for n in sorted({t.empresa.razao_social, t.empresa.nome_fantasia} - {None, ""}, key=len, reverse=True):
                k = chave_do_nome(n)
                for termo in {k, *([k.split()[0]] if k and len(k.split()[0]) >= 4 else [])}:
                    if termo:
                        txt = _regex_do_termo(termo).sub(lambda m: m.group(1) + emp_cod(t), txt)
        return txt

    abertas = [t for t in tarefas if getattr(t.status, "value", t.status) != "concluida"]
    semana = hoje + timedelta(days=7)
    mes_ini = hoje.replace(day=1)

    def item(t):
        return {"obrigacao": titulo(t), "competencia": t.competencia, "empresa": emp_cod(t),
                "setor": t.setor.nome if t.setor else None, "responsaveis": resp_cod(t),
                "prazo": _iso(_dia(t.data_prazo)), "vencimento": _iso(_dia(t.data_vencimento)),
                "situacao": getattr(t.status, "value", t.status)}

    def classe(t):
        d = _dia(t.data_prazo)
        if d is None:
            return "sem_prazo"
        if d < hoje:
            return "atrasada"
        if d == hoje:
            return "hoje"
        if d <= semana:
            return "semana"
        return "depois"

    atrasadas = sorted([t for t in abertas if classe(t) == "atrasada"], key=lambda t: _dia(t.data_prazo))
    hoje_l = [t for t in abertas if classe(t) == "hoje"]
    semana_l = sorted([t for t in abertas if classe(t) == "semana"], key=lambda t: _dia(t.data_prazo))
    concluidas_mes = [t for t in tarefas if getattr(t.status, "value", t.status) == "concluida"
                      and t.data_conclusao and _dia(t.data_conclusao) >= mes_ini]

    def contagem(chave_fn, lista_rotulo):
        c = defaultdict(Counter)
        for t in abertas:
            for k in chave_fn(t) or []:
                c[k]["abertas"] += 1
                c[k][{"atrasada": "atrasadas", "hoje": "vencem_hoje", "semana": "proximos_7_dias"}.get(classe(t), "outras")] += 1
        linhas = [{lista_rotulo: k, "abertas": v["abertas"], "atrasadas": v["atrasadas"],
                   "vencem_hoje": v["vencem_hoje"], "proximos_7_dias": v["proximos_7_dias"]} for k, v in c.items()]
        return sorted(linhas, key=lambda x: (-x["atrasadas"], -x["abertas"]))[:TOP]

    dados = {
        "hoje": hoje.isoformat(), "voce": cod_pes.codigo(usuario.nome) if usuario.nome else None,
        "resumo": {"abertas": len(abertas), "atrasadas": len(atrasadas), "vencem_hoje": len(hoje_l),
                   "proximos_7_dias": len(semana_l), "concluidas_no_mes": len(concluidas_mes)},
        "por_setor": contagem(lambda t: [t.setor.nome] if t.setor else ["(sem setor)"], "setor"),
        "por_responsavel": contagem(lambda t: resp_cod(t) or ["(sem responsável)"], "responsavel"),
        "por_empresa": contagem(lambda t: [emp_cod(t)] if t.empresa else [], "empresa"),
        "atrasadas": [item(t) for t in atrasadas[:MAX_LISTA]],
        "vencem_hoje": [item(t) for t in hoje_l[:MAX_LISTA]],
        "proximos_7_dias": [item(t) for t in semana_l[:MAX_LISTA]],
    }
    return c_pes["pergunta"], c_pes["historico"], json.dumps(dados, ensure_ascii=False), cod_emp.lista + cod_pes.lista


def conversar(pergunta: str, historico: list, tarefas: list, hoje: date, usuario, cfg: dict) -> dict:
    """{'resposta': texto} ou {'erro': frase}."""
    perg, hist, contexto, lista = montar_contexto(pergunta, historico or [], tarefas, hoje, usuario)
    provedor = ia_mod.provedor_escolhido(cfg)
    nome, key, modelo, url = ia_mod.credenciais(cfg, provedor)
    if not key:
        return {"erro": "IA não configurada."}
    if provedor == "openai":
        modelo = os.getenv("OPENAI_MODEL", "").strip() or MODELO_OPENAI
    mensagens = [{"role": "system", "content": INSTRUCOES}, {"role": "system", "content": "DADOS:\n" + contexto}]
    for h in hist[-MAX_HISTORICO:]:
        texto = str(h.get("texto") or "")[:MAX_TEXTO_HISTORICO]
        if texto:
            mensagens.append({"role": "assistant" if h.get("papel") == "assistente" else "user", "content": texto})
    mensagens.append({"role": "user", "content": perg})
    try:
        r = ia_mod.httpx.post(url, headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                              json={"model": modelo, "temperature": 0, "max_tokens": 900, "messages": mensagens},
                              timeout=45.0)
        if r.status_code != 200:
            return {"erro": ia_mod._erro_http(nome, r.status_code, modelo)}
        texto = r.json()["choices"][0]["message"]["content"]
    except Exception:
        return {"erro": f"Não consegui falar com a {nome} agora."}
    return {"resposta": destrocar(str(texto or "").strip(), lista)}
