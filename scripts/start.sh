#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")/.."

diagnostics() {
  echo 'Falha ao iniciar o laboratório. Estado e últimas mensagens dos serviços:' >&2
  docker compose ps -a
  docker compose logs --tail=60
}
trap diagnostics ERR

python3 scripts/generate_logs.py
docker compose config --quiet
docker compose up -d elasticsearch kibana
python3 scripts/bootstrap.py prepare
docker compose up -d logstash
python3 scripts/bootstrap.py finish
python3 scripts/bootstrap.py verify
echo 'Laboratório pronto. Dashboard: http://localhost:5601/app/dashboards#/view/elk-lab-dashboard'
