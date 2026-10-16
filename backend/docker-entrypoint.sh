#!/bin/sh
# Entrada do container: acerta o dono do volume e larga o root.
#
# POR QUE EXISTE: ate 2026-10 o backend do Tareffas rodava como root, e o volume
# /app/data de producao (comprovantes do cliente e documentos de saida, em
# UPLOAD_DIR=/app/data/uploads) nasceu com arquivos de root. O processo agora
# roda como o usuario app (1000), que nao grava em arquivo de root. Este script
# roda como root SO o tempo de passar o dono para app, e troca de usuario antes
# de subir o uvicorn. Mesmo padrao do Zoaria Hub (a401203).
#
# O volume mora DENTRO do /app, entao o alvo e so o diretorio de dados (o pai do
# UPLOAD_DIR), nunca o /app inteiro. O chown so acontece quando acha arquivo de
# outro dono, entao do segundo start em diante nao custa nada. Nao apaga, nao
# move, nao muda permissao: muda o dono.
set -e

APP_UID=1000
APP_GID=1000

if [ "$(id -u)" = "0" ]; then
    alvo="$(dirname "${UPLOAD_DIR:-/app/data/uploads}")"
    case "$alvo" in
        /|/app|/app/|/app/app*|/etc|/usr|/proc|/sys|.|./*)
            echo "entrypoint: recusado ajustar dono de '$alvo'" >&2
            exit 1 ;;
    esac
    mkdir -p "$alvo"
    if [ -n "$(find "$alvo" \( ! -user "$APP_UID" -o ! -group "$APP_GID" \) -print -quit)" ]; then
        echo "entrypoint: passando $alvo para app ($APP_UID:$APP_GID)"
        chown -R "$APP_UID:$APP_GID" "$alvo"
    fi
    exec setpriv --reuid="$APP_UID" --regid="$APP_GID" --init-groups "$@"
fi

exec "$@"
