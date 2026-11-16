#!/usr/bin/env python3
"""Prepara os índices, importa o dashboard e verifica os dados usando APIs HTTP."""
import argparse
import json
import os
from pathlib import Path
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent
settings = {}
if (ROOT / ".env").exists():
    for line in (ROOT / ".env").read_text().splitlines():
        if line.strip() and not line.lstrip().startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            settings[key.strip()] = value.strip()
ES = os.environ.get("ELASTICSEARCH_URL", "http://localhost:" + os.environ.get("ELASTICSEARCH_PORT", settings.get("ELASTICSEARCH_PORT", "9200")))
KIBANA = os.environ.get("KIBANA_URL", "http://localhost:" + os.environ.get("KIBANA_PORT", settings.get("KIBANA_PORT", "5601")))


def request(base, path, method="GET", payload=None, raw=None, content_type=None):
    data = raw if raw is not None else (json.dumps(payload).encode() if payload is not None else None)
    headers = {"kbn-xsrf": "elk-lab"}
    if data is not None:
        headers["Content-Type"] = content_type or "application/json"
    req = Request(base + path, data=data, headers=headers, method=method)
    try:
        with urlopen(req, timeout=15) as response:
            return json.load(response)
    except HTTPError as error:
        detail = error.read().decode(errors="replace")[:1500]
        raise RuntimeError(f"{method} {path}: HTTP {error.code}: {detail}") from error


def wait(label, operation, ready=lambda value: bool(value), timeout=600):
    deadline = time.monotonic() + timeout
    last_error = "ainda não disponível"
    print(f"Aguardando {label}...", flush=True)
    while time.monotonic() < deadline:
        try:
            result = operation()
            if ready(result):
                print(f"OK: {label}", flush=True)
                return result
            last_error = str(result)[:300]
        except (URLError, OSError, RuntimeError, ValueError) as error:
            last_error = str(error)
        time.sleep(5)
    raise RuntimeError(f"Tempo esgotado aguardando {label}. Último resultado: {last_error}")


def prepare():
    wait("Elasticsearch", lambda: request(ES, "/_cluster/health"),
         lambda result: result.get("status") in ("yellow", "green"))
    request(ES, "/_index_template/elk-lab", "PUT", {
        "index_patterns": ["elk-lab-*"], "priority": 100,
        "template": {
            "settings": {"number_of_shards": 1, "number_of_replicas": 0},
            "mappings": {"properties": {
                "@timestamp": {"type": "date"},
                "client_ip": {"type": "ip"},
                "http_method": {"type": "keyword"},
                "route": {"type": "keyword"},
                "status_code": {"type": "integer"},
                "response_time_ms": {"type": "integer"},
                "service": {"type": "keyword"},
                "message": {"type": "text"},
                "event": {"properties": {"original": {"type": "text", "index": False}}}
            }}
        }
    })
    print("Template de índices configurado.")


def finish():
    wait("120 eventos processados pelo Logstash", lambda: request(ES, "/elk-lab-logs/_count"),
         lambda result: result.get("count", 0) >= 120)
    wait("Kibana", lambda: request(KIBANA, "/api/status"),
         lambda result: result.get("status", {}).get("overall", {}).get("level") == "available")
    boundary = "elk-lab-upload-boundary"
    content = (ROOT / "kibana/saved-objects.ndjson").read_bytes()
    body = (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="saved-objects.ndjson"\r\n'
            'Content-Type: application/ndjson\r\n\r\n').encode() + content + f"\r\n--{boundary}--\r\n".encode()
    result = request(KIBANA, "/api/saved_objects/_import?overwrite=true", "POST", raw=body,
                     content_type=f"multipart/form-data; boundary={boundary}")
    if not result.get("success"):
        raise RuntimeError(f"Falha ao importar objetos do Kibana: {result}")
    request(KIBANA, "/api/data_views/default", "POST", {"data_view_id": "elk-lab-data-view", "force": True})
    request(KIBANA, "/api/kibana/settings", "POST", {"changes": {
        "timepicker:timeDefaults": json.dumps({"from": "now-24h", "to": "now"})
    }})
    print(f"Importados {result.get('successCount')} objetos no Kibana.")


def verify():
    result = request(ES, "/elk-lab-logs/_search", "POST", {
        "size": 1, "track_total_hits": True,
        "aggs": {"status": {"terms": {"field": "status_code", "size": 10}}}
    })
    total = result["hits"]["total"]["value"]
    statuses = {bucket["key"]: bucket["doc_count"] for bucket in result["aggregations"]["status"]["buckets"]}
    expected = {200: 80, 201: 10, 404: 10, 500: 20}
    if total != 120 or statuses != expected:
        raise RuntimeError(f"Distribuição inesperada: total={total}, status={statuses}; esperado: 120, {expected}")
    source = result["hits"]["hits"][0]["_source"]
    required = ("@timestamp", "client_ip", "route", "http_method", "status_code", "response_time_ms", "message", "service")
    if not all(field in source for field in required) or "original" not in source.get("event", {}):
        raise RuntimeError(f"Campos ausentes no evento: {source}")
    if not isinstance(source["status_code"], int) or not isinstance(source["response_time_ms"], int):
        raise RuntimeError("Os campos numéricos não foram convertidos pelo Logstash.")
    if source.get("tags"):
        raise RuntimeError(f"Evento com falha de processamento: {source}")
    missing = request(ES, "/elk-lab-logs/_count", "POST", {"query": {"bool": {
        "should": [{"bool": {"must_not": [{"exists": {"field": field}}]}} for field in required],
        "minimum_should_match": 1
    }}})
    if missing["count"]:
        raise RuntimeError(f"Há {missing['count']} eventos sem os campos obrigatórios.")
    dashboard = request(KIBANA, "/api/saved_objects/dashboard/elk-lab-dashboard")
    if len(json.loads(dashboard["attributes"]["panelsJSON"])) != 4:
        raise RuntimeError("Dashboard deve conter quatro painéis.")
    data_view = request(KIBANA, "/api/data_views/data_view/elk-lab-data-view")
    if data_view["data_view"]["title"] != "elk-lab-*":
        raise RuntimeError("Data view incorreto.")
    for reference in dashboard["references"]:
        if reference["type"] == "visualization":
            visualization = request(KIBANA, "/api/saved_objects/visualization/" + reference["id"])
            state = json.loads(visualization["attributes"]["visState"])
            if not state.get("aggs"):
                raise RuntimeError(f"Visualização sem agregações: {reference['id']}")
    print("VALIDADO: 120 eventos; 80 HTTP 200, 10 HTTP 201, 10 HTTP 404 e 20 HTTP 500.")
    print("VALIDADO: campos estruturados, tipos numéricos, data view e dashboard com quatro painéis.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["prepare", "finish", "verify"])
    action = parser.parse_args().action
    try:
        {"prepare": prepare, "finish": finish, "verify": verify}[action]()
    except (RuntimeError, URLError, OSError, ValueError, KeyError) as error:
        parser.exit(1, f"ERRO: {error}\n")
