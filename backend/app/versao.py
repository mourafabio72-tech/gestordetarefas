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

O carimbo vem do mtime MAIS RECENTE de todo o pacote `app/`.

COMO ISSO FUNCIONA DE VERDADE, medido em 2026-09-03 nos nove apps: no contexto
de build todo arquivo carrega o timestamp do COMMIT, e nao a data em que aquele
arquivo mudou pela ultima vez. O COPY do Docker tem cache por conteudo, entao
commit que nao altera a imagem deixa a camada antiga e o carimbo anterior -- o
que esta certo, porque a imagem no ar e mesmo a de antes.

Ou seja: olhar o pacote inteiro em vez deste arquivo NAO conserta bug nenhum.
Ficou porque e inofensivo e um pouco mais robusto quando um servico do compose
acerta o cache. Este arquivo ja afirmou o contrario, dizendo que o carimbo
congelaria; era falso, e nasceu de ler um carimbo de 01/09 como congelamento
quando simplesmente nao havia commit no periodo.

CUIDADO AO DIAGNOSTICAR: carimbo velho nao e prova de deploy parado. Compare
com o timestamp do HEAD (`git log -1 --date=format:'%Y%m%d-%H%M'`) antes de
acusar o webhook.

`__pycache__` fica de fora: aquele .pyc nasce quando o container importa o
modulo, entao ele carimbaria a hora do boot, nao a do codigo.

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

