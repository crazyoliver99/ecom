#!/bin/sh
# Runs automatically the FIRST time the postgres volume is initialized
# (files in /docker-entrypoint-initdb.d/ are only executed on a fresh volume).
# Creates the dedicated test database the pytest suite requires.
set -e
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  -c "CREATE DATABASE \"${POSTGRES_DB}_test\""
