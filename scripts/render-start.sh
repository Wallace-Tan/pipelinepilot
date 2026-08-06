#!/usr/bin/env bash
set -euo pipefail

# Render's filesystem is ephemeral unless a disk is attached. The blueprint
# mounts the SQLite database at /var/data and keeps CoCo's credential metadata
# in a temporary directory instead of the persistent application disk.
if [[ "${PIPELINEPILOT_COCO_ENABLED:-false}" == "true" ]]; then
  connection_name="${PIPELINEPILOT_COCO_CONNECTION:-pipelinepilot}"
  if [[ ! "$connection_name" =~ ^[A-Za-z0-9_-]+$ ]]; then
    echo "PIPELINEPILOT_COCO_CONNECTION must contain only letters, numbers, '_' or '-'" >&2
    exit 1
  fi
  : "${SNOWFLAKE_ACCOUNT:?SNOWFLAKE_ACCOUNT is required when CoCo is enabled}"
  : "${SNOWFLAKE_USER:?SNOWFLAKE_USER is required when CoCo is enabled}"
  : "${SNOWFLAKE_PASSWORD:?SNOWFLAKE_PASSWORD is required by the Render password-authenticated connection setup}"
  authenticator="${SNOWFLAKE_AUTHENTICATOR:-snowflake}"

  export PATH="${HOME}/.local/bin:${PATH}"
  snowflake_home="${SNOWFLAKE_HOME:-/tmp/pipelinepilot-snowflake}"
  mkdir -p "$snowflake_home"
  chmod 700 "$snowflake_home"
  connection_file="$snowflake_home/connections.toml"
  {
    printf 'default_connection_name = "%s"\n\n' "$connection_name"
    printf '[%s]\n' "$connection_name"
    printf 'account = "${SNOWFLAKE_ACCOUNT}"\n'
    printf 'user = "${SNOWFLAKE_USER}"\n'
    printf 'authenticator = "%s"\n' "$authenticator"
    printf 'password = "${SNOWFLAKE_PASSWORD}"\n'
    printf 'role = "${SNOWFLAKE_ROLE}"\n'
    printf 'warehouse = "${SNOWFLAKE_WAREHOUSE}"\n'
    printf 'database = "${SNOWFLAKE_DATABASE}"\n'
    printf 'schema = "${SNOWFLAKE_SCHEMA}"\n'
  } > "$connection_file"
  chmod 600 "$connection_file"
  export SNOWFLAKE_HOME="$snowflake_home"
fi

cd backend
exec uv run --no-dev uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
