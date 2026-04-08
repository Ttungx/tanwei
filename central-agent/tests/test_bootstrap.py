import importlib
import asyncio
import os
import sys
import tempfile
import unittest
from pathlib import Path

SERVICE_DIR = Path(__file__).resolve().parents[1]
if str(SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(SERVICE_DIR))


class CentralAgentBootstrapTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.previous_db_path = os.environ.get("CENTRAL_AGENT_DB_PATH")
        os.environ["CENTRAL_AGENT_DB_PATH"] = str(Path(self.tmpdir.name) / "central-agent.db")
        sys.modules.pop("app.main", None)

    def tearDown(self):
        sys.modules.pop("app.main", None)
        if self.previous_db_path is None:
            os.environ.pop("CENTRAL_AGENT_DB_PATH", None)
        else:
            os.environ["CENTRAL_AGENT_DB_PATH"] = self.previous_db_path
        self.tmpdir.cleanup()

    def test_module_imports(self):
        module = importlib.import_module("app.main")
        self.assertTrue(hasattr(module, "app"))

    def test_health_endpoint(self):
        module = importlib.import_module("app.main")
        response = asyncio.run(module.health())
        self.assertEqual(response["status"], "healthy")
        self.assertEqual(response["service"], "central-agent")
