"""
Carimbo de versao e build, para saber DE FORA o que producao esta servindo.

POR QUE EXISTE: em 2026-09-01 o XmlHub revelou que o repositorio dele nao tinha
webhook no GitHub. Seis commits ficaram parados no servidor sem nenhum sinal:
site respondendo 200, historico do EasyPanel cheio de "Success", e o container
antigo servindo. Um deles ja tinha sido dado como publicado. So se descobriu
porque aquele app ganhou este carimbo horas antes.

Sem isto, a unica forma de saber qual versao esta no ar e entrar no app ou no
painel. Com isto, um curl responde:

    curl -s https://gestordetarefas.zoaria.com.br/api/health

O carimbo vem do mtime MAIS RECENTE de todo o pacote `app/`, e nao do mtime
deste arquivo.

A primeira versao usava so este arquivo, e ficou congelada em 20260901-1155
por tres dias enquanto tres deploys entravam. O motivo: o EasyPanel faz
checkout por cima do diretorio que ja existe, e so o arquivo ALTERADO ganha
mtime novo. Commit que nao toca no versao.py nao move o mtime do versao.py, a
camada do Docker vem do cache, e o carimbo mente dizendo que producao e velha.

Isso e pior do que nao ter carimbo: em 2026-09-03 quase demos o webhook como
morto por causa dele, quando o deploy tinha chegado. Falso negativo em
instrumento de verificacao custa mais caro que instrumento nenhum.

Olhando o pacote inteiro, QUALQUER arquivo de codigo que mude move o carimbo,
que e exatamente a pergunta que se quer responder: que codigo esta no ar.
`__pycache__` fica de fora de proposito -- aquele .pyc nasce quando o
container importa o modulo, entao ele carimbaria a hora do boot, nao a do
codigo.

Nao depende de variavel de ambiente, que alguem esqueceria de atualizar.
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path

_ESTE_ARQUIVO = Path(__file__).resolve()

# -03:00 fixo em vez do banco de fusos: o Brasil nao tem horario de verao desde
# 2019, e o container pode subir sem tzdata.
_FUSO_BR = timezone(timedelta(hours=-3))


_PACOTE = _ESTE_ARQUIVO.parent


def _mtime_mais_recente() -> float:
    """O mtime do arquivo de codigo mais novo do pacote `app/`.

    Volta ao mtime deste arquivo se a varredura nao achar nada, para o carimbo
    nunca ficar pior do que era.
    """
    novo = 0.0
    for caminho in _PACOTE.rglob("*.py"):
        if "__pycache__" in caminho.parts:
            continue
        try:
            novo = max(novo, caminho.stat().st_mtime)
        except OSError:
            continue          # arquivo sumiu no meio da varredura: segue
    return novo or _ESTE_ARQUIVO.stat().st_mtime


def _carimbo_de_build() -> str:
    """AAAAMMDD-HHMM no relogio de Brasilia. Falha vira 'desconhecido'."""
    try:
        quando = datetime.fromtimestamp(_mtime_mais_recente(), _FUSO_BR)
        return quando.strftime("%Y%m%d-%H%M")
    except OSError:
        return "desconhecido"


BUILD = _carimbo_de_build()

#: O que aparece na tela: "build 20260901-1046".
VERSAO_COMPLETA = f"build {BUILD}"

