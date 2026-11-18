#!/usr/bin/env python3
"""Comprueba y normaliza los workflows de n8n versionados en automation/n8n/workflows/.

    python3 automation/n8n/n8n_workflows.py check
        Valida todos los JSON (lo ejecuta el CI): JSON válido, `active: false`, sin datos fijados,
        las llamadas a la API usan `$env.API_BASE_URL` y la credencial de cabecera, y no hay claves,
        tokens ni URLs de producción.

    <exportación de n8n> | python3 automation/n8n/n8n_workflows.py normalize
        Lee de stdin la salida de `n8n export:workflow --all` y escribe cada workflow en
        workflows/, sin los campos propios de la instancia y con `active: false`. Ver README.md.

Sólo usa la biblioteca estándar de Python.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

WORKFLOWS_DIR = Path(__file__).resolve().parent / "workflows"

# Campos que se versionan. El resto (shared, staticData, versionId, fechas...) son de la instancia.
KEPT_FIELDS = ("id", "name", "active", "nodes", "connections", "settings", "pinData", "tags")

API_URL_PREFIX = "={{ $env.API_BASE_URL }}/"
CREDENTIAL_TYPE = "httpHeaderAuth"
# Hosts que pueden aparecer literalmente (ejemplos y valores por defecto locales).
LOCAL_HOSTS = {"localhost", "127.0.0.1", "host.docker.internal"}

URL_RE = re.compile(r"https?://([^/\s:'\"}]+)", re.IGNORECASE)
SECRET_PATTERNS = {
    "JWT": re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),
    "cabecera Authorization": re.compile(
        r"\b(Bearer|Basic)\s+[A-Za-z0-9._~+/=-]{8,}", re.IGNORECASE
    ),
    "clave Fernet": re.compile(r"\b[A-Za-z0-9_-]{43}=(?![A-Za-z0-9])"),
    "clave de Supabase": re.compile(r"\bsb_(secret|publishable)_[A-Za-z0-9_-]+"),
    "token de GitHub": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}"),
    "clave de API": re.compile(r"\b(sk|rk|pk)[-_](live|test|ant|proj)?[-_]?[A-Za-z0-9]{16,}"),
    "valor hexadecimal largo": re.compile(r"\b[0-9a-f]{32,}\b", re.IGNORECASE),
}
SECRET_KEY_RE = re.compile(
    r"(api[-_]?key|secret|token|password|passwd|authorization|x-internal-api-key)", re.IGNORECASE
)


def _strings(value: Any, path: str = "") -> Iterator[tuple[str, str, str]]:
    """Recorre el JSON y devuelve (ruta, clave, valor) de cada cadena."""
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            if isinstance(child, str):
                yield child_path, str(key), child
            else:
                yield from _strings(child, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            child_path = f"{path}[{index}]"
            if isinstance(child, str):
                yield child_path, "", child
            else:
                yield from _strings(child, child_path)


def check_workflow(workflow: Any) -> list[str]:
    """Devuelve los problemas del workflow (lista vacía si cumple las reglas)."""
    if not isinstance(workflow, dict):
        return ["el fichero debe contener un único workflow (un objeto JSON)"]
    problems: list[str] = []
    for field in ("id", "name", "nodes", "connections"):
        if field not in workflow:
            problems.append(f"falta el campo `{field}`")
    if workflow.get("active") is not False:
        problems.append("debe exportarse con `active: false`")
    if workflow.get("pinData"):
        problems.append("no puede llevar datos fijados (`pinData`): pueden contener datos reales")
    extra = sorted(set(workflow) - set(KEPT_FIELDS))
    if extra:
        problems.append(f"campos propios de la instancia (normaliza la exportación): {extra}")

    nodes = workflow.get("nodes")
    for node in nodes if isinstance(nodes, list) else []:
        problems.extend(_check_node(node))

    for path, key, text in _strings(workflow):
        for host in URL_RE.findall(text):
            if host.lower() not in LOCAL_HOSTS:
                problems.append(f"{path}: URL no local ({host}); usa {{{{ $env.API_BASE_URL }}}}")
        for label, pattern in SECRET_PATTERNS.items():
            if pattern.search(text):
                problems.append(f"{path}: parece contener un secreto ({label})")
        if SECRET_KEY_RE.search(key) and text.strip() and not text.startswith("={{"):
            problems.append(f"{path}: valor literal en un campo sensible ({key})")
    return problems


def _check_node(node: Any) -> list[str]:
    if not isinstance(node, dict):
        return ["nodo no válido"]
    name = node.get("name", "?")
    problems: list[str] = []
    credentials = node.get("credentials") or {}
    for cred_type, ref in credentials.items():
        if not isinstance(ref, dict) or set(ref) - {"id", "name"}:
            problems.append(
                f"nodo {name!r}: la credencial {cred_type} sólo puede referenciarse por id y nombre"
            )
    if node.get("type") != "n8n-nodes-base.httpRequest":
        return problems
    params = node.get("parameters") or {}
    url = params.get("url", "")
    if not isinstance(url, str) or not url.startswith(API_URL_PREFIX):
        problems.append(f"nodo {name!r}: la URL debe empezar por `{API_URL_PREFIX}`")
    if (
        params.get("authentication") != "genericCredentialType"
        or params.get("genericAuthType") != CREDENTIAL_TYPE
    ):
        problems.append(
            f"nodo {name!r}: la clave debe ir en una credencial de cabecera ({CREDENTIAL_TYPE})"
        )
    if CREDENTIAL_TYPE not in credentials:
        problems.append(f"nodo {name!r}: falta la referencia a la credencial {CREDENTIAL_TYPE}")
    if params.get("sendHeaders") or params.get("headerParameters"):
        problems.append(f"nodo {name!r}: las cabeceras no van en el workflow; usa la credencial")
    if params.get("sendQuery") or params.get("queryParameters"):
        problems.append(f"nodo {name!r}: sin parámetros de query (podrían llevar secretos)")
    return problems


def check(directory: Path = WORKFLOWS_DIR) -> int:
    files = sorted(directory.glob("*.json"))
    if not files:
        print(f"No hay workflows en {directory}", file=sys.stderr)
        return 1
    failed = False
    ids: dict[str, Path] = {}
    for path in files:
        try:
            workflow = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            print(f"{path.name}: JSON no válido: {exc}")
            failed = True
            continue
        problems = check_workflow(workflow)
        if isinstance(workflow, dict):
            wf_id = workflow.get("id")
            if isinstance(wf_id, str):
                if wf_id in ids:
                    problems.append(f"id repetido con {ids[wf_id].name}")
                ids[wf_id] = path
        for problem in problems:
            print(f"{path.name}: {problem}")
        failed = failed or bool(problems)
        if not problems:
            print(f"{path.name}: OK")
    return 1 if failed else 0


def normalize_workflow(workflow: dict[str, Any]) -> dict[str, Any]:
    normalized = {field: workflow[field] for field in KEPT_FIELDS if field in workflow}
    normalized["active"] = False
    normalized["pinData"] = {}
    tags = workflow.get("tags", [])
    normalized["tags"] = [tag["name"] if isinstance(tag, dict) else tag for tag in tags]
    return normalized


def _slug(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "workflow"


def normalize(stream: str, directory: Path = WORKFLOWS_DIR) -> int:
    data = json.loads(stream)
    workflows = data if isinstance(data, list) else [data]
    existing: dict[str, Path] = {}
    for path in directory.glob("*.json"):
        try:
            existing[json.loads(path.read_text(encoding="utf-8")).get("id")] = path
        except (json.JSONDecodeError, AttributeError):
            continue
    for workflow in workflows:
        slug = _slug(workflow.get("name", ""))
        target = existing.get(workflow.get("id")) or directory / f"{slug}.json"
        text = json.dumps(normalize_workflow(workflow), ensure_ascii=False, indent=2) + "\n"
        target.write_text(text, encoding="utf-8")
        print(f"{workflow.get('name')} -> {target.relative_to(directory.parent)}")
    return check(directory)


def main(argv: list[str]) -> int:
    if argv[1:] == ["check"]:
        return check()
    if argv[1:] == ["normalize"]:
        return normalize(sys.stdin.read())
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
