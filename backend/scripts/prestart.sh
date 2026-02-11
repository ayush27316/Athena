#! /usr/bin/env bash

set -e
set -x

# Let the DB start
python app/backend_pre_start.py

# Flush DB if DB_FLUSH is set to true
if [ "$DB_FLUSH" = "true" ]; then
  echo "DB_FLUSH is enabled — dropping all tables..."
  PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$POSTGRES_SERVER" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
  echo "Database flushed."
fi

# Create initial data in DB
python app/initial_data.py
