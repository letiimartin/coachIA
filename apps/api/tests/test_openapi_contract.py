from scripts.export_openapi import OPENAPI_PATH, render_openapi


def test_versioned_openapi_matches_generated() -> None:
    assert OPENAPI_PATH.exists(), "Falta openapi.json: uv run python -m scripts.export_openapi"
    assert OPENAPI_PATH.read_text(encoding="utf-8") == render_openapi(), (
        "openapi.json está desactualizado: uv run python -m scripts.export_openapi"
    )


def test_render_openapi_is_deterministic() -> None:
    assert render_openapi() == render_openapi()
