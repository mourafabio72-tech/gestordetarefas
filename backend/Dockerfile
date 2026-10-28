FROM python:3.11-slim

# Usuario sem privilegio. O processo do app roda como ele, nunca como root.
RUN groupadd -g 1000 app && useradd -u 1000 -g 1000 -M -d /app -s /usr/sbin/nologin app

WORKDIR /app

# SEM apt-get de gcc e libpq-dev, de proposito: o requirements usa
# psycopg2-binary, que ja vem compilado, e todas as outras dependencias tem
# wheel para linux. Aquele apt-get baixava 65 MB e ocupava 245 MB de disco em
# TODO build, sem servir para nada, e em 2026-09-01 derrubou o deploy: o build
# do backend e o npm install do frontend rodam ao mesmo tempo neste compose, e
# a maquina foi ao chao com "Killed" no meio da instalacao.
# Se um dia entrar dependencia que precise compilar, o build vai falhar dizendo
# qual e, e ai a linha volta so para ela.

# OCR do e-validador (2026-10-28): guia em imagem (PNG, JPG, PDF escaneado) e
# lida AQUI, e nao pela IA, para o documento do cliente nao sair do servidor.
# Pacote pronto do Debian, sem compilar nada: nao e o caso do gcc acima.
# --no-install-recommends deixa de fora os idiomas e extras que nao usamos.
RUN apt-get update \
 && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-por \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Codigo de dono root, so leitura para o processo. O carimbo (app/versao.py)
# sai do mtime, que o COPY preserva.
COPY . .

# Entrada fora do /app e de dono root: o usuario app nao consegue reescrever
# o script que roda como root no proximo start. O volume monta por cima do
# /app/data; quem ja tem dado nele recebe o dono certo do entrypoint.
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod 0755 /usr/local/bin/docker-entrypoint.sh && mkdir -p /app/data/uploads && chown -R app:app /app/data

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]