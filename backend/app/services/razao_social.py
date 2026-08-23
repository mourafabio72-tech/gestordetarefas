"""Uniformiza a razão social na EXIBIÇÃO — não mexe no cadastro.

Porte do `frontend/src/pages/razaoSocial.js`. Existe em dois lugares porque a
mesma razão social aparece na tela e na mensagem que vai para o cliente, e a
mensagem é onde o nome mal escrito incomoda mais: chega na caixa de entrada
dele, com o "OLÁ, RIO BRAVO COM. DE ARMAS MUNIÇÕES E ACESS. LTDA" gritando.

Os dois arquivos precisam andar juntos; a prova compara a saída dos dois nos
mesmos casos, para uma correção num lado não passar despercebida no outro.
"""
import re

# Vão em minúscula quando não são a primeira palavra.
ATONAS = {"de", "da", "do", "das", "dos", "e", "em", "a", "o", "as", "os", "à", "às"}

# Siglas e formas jurídicas com grafia própria. Lista fixa porque nenhuma regra
# automática separa sigla de palavra: "MKB" e "RIO" têm três letras cada, e só
# quem conhece o cliente sabe que a primeira é sigla.
SIGLAS = {
    "LTDA": "Ltda", "ME": "ME", "EPP": "EPP", "EIRELI": "Eireli", "MEI": "MEI",
    "SA": "S.A.", "S/A": "S.A.", "S.A": "S.A.", "CIA": "Cia", "JR": "Jr",
    "MKB": "MKB", "IWC": "IWC", "BPS4": "BPS4", "CW": "CW", "SPE": "SPE",
}


def _parece_sigla(bruto: str) -> bool:
    """Sem vogal e curta: CW, MKB, BPS. Pega sigla fora da lista fixa."""
    so = re.sub(r"[^A-Za-zÀ-ÿ0-9]", "", bruto or "")
    if not so or len(so) > 4:
        return False
    if re.search(r"\d", so):
        return True                      # BPS4, 3M
    return not re.search(r"[AEIOUÀ-ÿaeiou]", so)


def _pedaco(bruto: str, primeiro: bool) -> str:
    nu = re.sub(r"[.,]+$", "", bruto)
    pontuacao = bruto[len(nu):]
    chave = nu.upper()
    if chave in SIGLAS:
        return SIGLAS[chave] + pontuacao
    # Abreviação (terminou em ponto) é palavra encurtada, nunca sigla: "Com.".
    if not pontuacao and _parece_sigla(nu):
        return chave + pontuacao
    baixo = nu.lower()
    if not primeiro and baixo in ATONAS:
        return baixo + pontuacao
    return (baixo[:1].upper() + baixo[1:]) + pontuacao


def formatar(nome) -> str:
    """Razão social pronta para exibir.

    Nome que JÁ tem minúscula é devolvido intacto: quem cadastrou "Mark Building
    Gerenc. Predial Ltda." escreveu do jeito que quer ver.
    """
    texto = re.sub(r"\s+", " ", (nome or "").strip())
    if not texto:
        return ""
    if re.search(r"[a-zà-ÿ]", texto):
        return texto

    saida = []
    for i, palavra in enumerate(texto.split(" ")):
        # A palavra inteira antes da repartição: "S/A" está no mapa e não pode
        # ser quebrada na barra.
        inteira = re.sub(r"[.,]+$", "", palavra).upper()
        if inteira in SIGLAS:
            saida.append(SIGLAS[inteira])
            continue
        primeiro = i == 0
        partes = []
        for parte in re.split(r"([-/])", palavra):
            if parte in ("-", "/"):
                partes.append(parte)
                continue
            partes.append(_pedaco(parte, primeiro))
            primeiro = False
        saida.append("".join(partes))
    return " ".join(saida)
