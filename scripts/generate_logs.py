#!/usr/bin/env python3
"""Gera 120 acessos fictícios, com datas recentes e distribuição conhecida."""
import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path

STATUSES = [200] * 8 + [201, 404, 500, 500]
ROUTES = ["/", "/produtos", "/carrinho", "/checkout", "/api/pedidos"]


def generate(destination, overwrite=False):
    path = Path(destination)
    if path.exists() and not overwrite:
        print(f"Mantendo logs existentes: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).replace(microsecond=0)
    lines = []
    for i in range(120):
        timestamp = (now - timedelta(seconds=(120 - i) * 25)).isoformat()
        status = STATUSES[i % len(STATUSES)]
        route = ROUTES[i % len(ROUTES)]
        method = "POST" if route in ("/checkout", "/api/pedidos") else "GET"
        duration = 800 + i if status == 500 else 20 + i % 180
        message = {200: "Requisicao concluida", 201: "Pedido criado",
                   404: "Recurso nao encontrado", 500: "Falha no processamento"}[status]
        lines.append(f'{timestamp} 192.0.2.{i % 20 + 1} {method} {route} {status} {duration} "{message}"')
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    path.chmod(0o644)
    print(f"Gerados 120 eventos em {path}: 80 HTTP 200, 10 HTTP 201, 10 HTTP 404 e 20 HTTP 500.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", nargs="?", default=".runtime/application.log")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    generate(args.destination, args.overwrite)
