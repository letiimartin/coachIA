"""Tests del comprobador de workflows: python3 -m unittest discover -s automation/n8n/tests"""

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

N8N_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(N8N_DIR))

import n8n_workflows as wf  # noqa: E402


def _load(name: str) -> dict:
    return json.loads((N8N_DIR / "workflows" / name).read_text(encoding="utf-8"))


def _http_node(workflow: dict) -> dict:
    return next(n for n in workflow["nodes"] if n["type"] == "n8n-nodes-base.httpRequest")


class VersionedWorkflowsTest(unittest.TestCase):
    def test_repository_workflows_pass(self) -> None:
        self.assertEqual(wf.check(), 0)

    def test_sync_wahoo_is_inactive_every_3_hours(self) -> None:
        workflow = _load("sync-wahoo.json")
        self.assertIs(workflow["active"], False)
        trigger = next(
            n for n in workflow["nodes"] if n["type"] == "n8n-nodes-base.scheduleTrigger"
        )
        self.assertEqual(
            trigger["parameters"]["rule"]["interval"],
            [{"field": "cronExpression", "expression": "0 */3 * * *"}],
        )
        node = _http_node(workflow)
        self.assertEqual(node["parameters"]["method"], "POST")
        self.assertTrue(node["parameters"]["url"].endswith("/internal/sync/wahoo"))

    def test_ping_calls_internal_ping(self) -> None:
        node = _http_node(_load("ping.json"))
        self.assertEqual(node["parameters"]["url"], "={{ $env.API_BASE_URL }}/internal/ping")


class CheckWorkflowTest(unittest.TestCase):
    def setUp(self) -> None:
        self.workflow = _load("sync-wahoo.json")

    def assert_problem(self, workflow: dict, fragment: str) -> None:
        problems = wf.check_workflow(workflow)
        self.assertTrue(any(fragment in p for p in problems), problems)

    def test_valid_workflow_has_no_problems(self) -> None:
        self.assertEqual(wf.check_workflow(self.workflow), [])

    def test_active_workflow_is_rejected(self) -> None:
        self.workflow["active"] = True
        self.assert_problem(self.workflow, "active: false")

    def test_missing_active_is_rejected(self) -> None:
        del self.workflow["active"]
        self.assert_problem(self.workflow, "active: false")

    def test_production_url_is_rejected(self) -> None:
        _http_node(self.workflow)["parameters"]["url"] = (
            "https://letismartcoach.onrender.com/internal/ping"
        )
        self.assert_problem(self.workflow, "letismartcoach.onrender.com")
        self.assert_problem(self.workflow, "API_BASE_URL")

    def test_local_url_in_text_is_allowed(self) -> None:
        self.workflow["nodes"][0]["notes"] = "Por defecto http://host.docker.internal:8000"
        self.assertEqual(wf.check_workflow(self.workflow), [])

    def test_header_in_node_is_rejected(self) -> None:
        params = _http_node(self.workflow)["parameters"]
        params["sendHeaders"] = True
        header = {"name": "X-Internal-API-Key", "value": "abc"}
        params["headerParameters"] = {"parameters": [header]}
        self.assert_problem(self.workflow, "credencial")

    def test_inline_credential_data_is_rejected(self) -> None:
        _http_node(self.workflow)["credentials"]["httpHeaderAuth"]["data"] = {"value": "x"}
        self.assert_problem(self.workflow, "por id y nombre")

    def test_missing_credential_auth_is_rejected(self) -> None:
        _http_node(self.workflow)["parameters"]["authentication"] = "none"
        self.assert_problem(self.workflow, "credencial de cabecera")

    def test_secrets_are_rejected(self) -> None:
        secrets = [
            "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.abc",
            "Bearer abcdefghijklmnop",
            "Y29hY2hpYS1mZXJuZXQta2V5LWZvci10ZXN0cy0zMmI=",
            "0123456789abcdef0123456789abcdef",
            "sb_" + "secret_abcdef123456",  # partido para no disparar el escáner de secretos
        ]
        for secret in secrets:
            with self.subTest(secret=secret):
                workflow = copy.deepcopy(self.workflow)
                workflow["nodes"][0]["notes"] = secret
                self.assert_problem(workflow, "secreto")

    def test_literal_value_in_sensitive_field_is_rejected(self) -> None:
        self.workflow["nodes"][0]["parameters"]["apiKey"] = "clave-de-prueba"
        self.assert_problem(self.workflow, "campo sensible")

    def test_pinned_data_is_rejected(self) -> None:
        self.workflow["pinData"] = {"Ejecutar a mano": [{"json": {"token": "x"}}]}
        self.assert_problem(self.workflow, "pinData")

    def test_instance_fields_are_rejected(self) -> None:
        self.workflow["shared"] = [{"role": "workflow:owner"}]
        self.assert_problem(self.workflow, "shared")


class NormalizeTest(unittest.TestCase):
    def test_normalize_strips_instance_fields_and_deactivates(self) -> None:
        exported = _load("ping.json")
        exported.update(
            active=True,
            shared=[{"project": {"name": "Alguien <alguien@example.com>"}}],
            staticData={"x": 1},
            versionId="v1",
            updatedAt="2026-01-01T00:00:00.000Z",
            pinData={"Ejecutar a mano": [{"json": {}}]},
            tags=[{"id": "t1", "name": "coachia"}],
        )
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp) / "workflows"
            directory.mkdir()
            (directory / "ping.json").write_text(json.dumps(_load("ping.json")), encoding="utf-8")

            self.assertEqual(wf.normalize(json.dumps([exported]), directory), 0)

            result = json.loads((directory / "ping.json").read_text(encoding="utf-8"))
        self.assertIs(result["active"], False)
        self.assertEqual(result["pinData"], {})
        self.assertEqual(result["tags"], ["coachia"])
        self.assertEqual(sorted(result), sorted(wf.KEPT_FIELDS))


if __name__ == "__main__":
    unittest.main()
