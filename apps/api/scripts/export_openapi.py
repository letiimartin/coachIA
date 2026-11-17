"""Exporta el contrato OpenAPI de la API a `apps/api/openapi.json`.

Uso (desde `apps/api`):  uv run python -m scripts.export_openapi

La salida es determinista: se genera con una configuración vacía (sin leer variables de entorno
ni ficheros .env), con las claves ordenadas y un salto de línea final.
"""

import json
from pathlib import Path
from typing import Any

from pydantic_settings import BaseSettings, PydanticBaseSettingsSource

from app.core.config import Settings
from app.main import create_app

OPENAPI_PATH = Path(__file__).resolve().parent.parent / "openapi.json"


class _EmptySettings(Settings):
    """Configuración con los valores por defecto: ignora el entorno y los ficheros .env."""

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (init_settings,)


def build_openapi() -> dict[str, Any]:
    app = create_app(_EmptySettings())
    return app.openapi()


def render_openapi() -> str:
    return json.dumps(build_openapi(), indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def main() -> None:
    OPENAPI_PATH.write_text(render_openapi(), encoding="utf-8")
    print(f"Contrato OpenAPI escrito en {OPENAPI_PATH}")


if __name__ == "__main__":
    main()
