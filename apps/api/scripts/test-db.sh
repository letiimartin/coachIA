#!/usr/bin/env bash
# Postgres local y desechable para los tests de BD.
#
#   scripts/test-db.sh          # inicializa (si hace falta) y arranca; imprime export TEST_DATABASE_URL=...
#   scripts/test-db.sh stop     # lo para (los datos se conservan hasta borrar el directorio)
#
# Uso típico:  eval "$(scripts/test-db.sh)" && uv run pytest
#
# Variables opcionales:
#   TEST_DB_PORT  puerto local (5433 por defecto)
#   TEST_DB_DIR   directorio del clúster (${TMPDIR:-/tmp}/coachia-test-db por defecto)
#   PG_BIN        directorio con initdb/pg_ctl (por defecto, la versión más alta de
#                 /usr/lib/postgresql/*/bin o, si no hay, los del PATH)
#
# Sólo la línea export va a stdout; los mensajes van a stderr. El clúster usa auth `trust` y sólo
# escucha en localhost: es para tests, nunca para datos reales.
set -euo pipefail

PORT="${TEST_DB_PORT:-5433}"
DIR="${TEST_DB_DIR:-${TMPDIR:-/tmp}/coachia-test-db}"
DATA="$DIR/data"
LOG="$DIR/postgres.log"
DB_NAME="coachia_test"
DB_USER="postgres"
URL="postgresql://${DB_USER}@localhost:${PORT}/${DB_NAME}"

log() { echo "test-db: $*" >&2; }
die() {
  log "$*"
  exit 1
}

find_pg_bin() {
  if [[ -n "${PG_BIN:-}" ]]; then
    echo "$PG_BIN"
    return
  fi
  local candidate
  candidate="$(find /usr/lib/postgresql -mindepth 2 -maxdepth 2 -name bin -type d 2>/dev/null | sort -V | tail -n 1)"
  if [[ -n "$candidate" ]]; then
    echo "$candidate"
  elif command -v pg_ctl >/dev/null 2>&1; then
    dirname "$(command -v pg_ctl)"
  else
    die "no encuentro los binarios de Postgres (initdb, pg_ctl). Instálalos o define PG_BIN."
  fi
}

BIN="$(find_pg_bin)"
for tool in initdb pg_ctl pg_isready psql; do
  [[ -x "$BIN/$tool" ]] || die "falta $BIN/$tool"
done

# initdb y postgres no se ejecutan como root: en ese caso se usa el usuario del sistema postgres.
as_owner() {
  if [[ "$(id -u)" -eq 0 ]]; then
    id postgres >/dev/null 2>&1 || die "se ejecuta como root y no existe el usuario postgres"
    runuser -u postgres -- "$@"
  else
    "$@"
  fi
}

is_running() {
  [[ -f "$DATA/PG_VERSION" ]] && as_owner "$BIN/pg_ctl" -D "$DATA" status >/dev/null 2>&1
}

psql_admin() {
  as_owner "$BIN/psql" -h "$DIR" -p "$PORT" -U "$DB_USER" -d postgres -v ON_ERROR_STOP=1 -qAt "$@"
}

start() {
  if is_running; then
    log "ya está en marcha en el puerto $PORT ($DATA)"
    echo "export TEST_DATABASE_URL=$URL"
    return
  fi

  mkdir -p "$DIR"
  if [[ "$(id -u)" -eq 0 ]]; then
    chown postgres: "$DIR"
  fi

  if [[ ! -f "$DATA/PG_VERSION" ]]; then
    log "inicializando el clúster en $DATA"
    as_owner "$BIN/initdb" -D "$DATA" -U "$DB_USER" --auth=trust --encoding=UTF8 --locale=C \
      >"$DIR/initdb.log" 2>&1 || die "initdb ha fallado; ver $DIR/initdb.log"
  fi

  if "$BIN/pg_isready" -h localhost -p "$PORT" >/dev/null 2>&1; then
    die "el puerto $PORT ya está ocupado por otro Postgres; usa TEST_DB_PORT"
  fi

  log "arrancando en el puerto $PORT"
  # El socket Unix va en el propio directorio para no depender de /var/run/postgresql.
  as_owner "$BIN/pg_ctl" -D "$DATA" -l "$LOG" -w -t 30 \
    -o "-p $PORT -k $DIR -c listen_addresses=localhost" start >/dev/null ||
    die "no ha arrancado; ver $LOG"

  if [[ "$(psql_admin -c "SELECT 1 FROM pg_database WHERE datname = '$DB_NAME'")" != "1" ]]; then
    log "creando la BD $DB_NAME"
    psql_admin -c "CREATE DATABASE $DB_NAME"
  fi

  echo "export TEST_DATABASE_URL=$URL"
}

stop() {
  if is_running; then
    as_owner "$BIN/pg_ctl" -D "$DATA" -m fast -w stop >/dev/null
    log "parado (los datos siguen en $DIR; bórralo para empezar de cero)"
  else
    log "no está en marcha"
  fi
}

case "${1:-start}" in
  start) start ;;
  stop) stop ;;
  *) die "uso: $0 [start|stop]" ;;
esac
