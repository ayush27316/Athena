#!/usr/bin/env sh
clear
cd backend || exit 1

docker compose --env-file ../.env build \
  && docker compose --env-file ../.env up -d

echo "Waiting for backend..."
until curl -s http://localhost:8000/api/v1/utils/health-check/ > /dev/null; do
  sleep 1
done


cd ..