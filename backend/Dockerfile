FROM python:3.11-slim

WORKDIR /app

# SEM apt-get de gcc e libpq-dev, de proposito: o requirements usa
# psycopg2-binary, que ja vem compilado, e todas as outras dependencias tem
# wheel para linux. Aquele apt-get baixava 65 MB e ocupava 245 MB de disco em
# TODO build, sem servir para nada, e em 2026-09-01 derrubou o deploy: o build
# do backend e o npm install do frontend rodam ao mesmo tempo neste compose, e
# a maquina foi ao chao com "Killed" no meio da instalacao.
# Se um dia entrar dependencia que precise compilar, o build vai falhar dizendo
# qual e, e ai a linha volta so para ela.

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]