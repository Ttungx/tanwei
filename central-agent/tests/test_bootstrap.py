import importlib
import sys
import unittest
from pathlib import Path

SERVICE_DIR = Path(__file__).resolve().parents[1]
if str(SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(SERVICE_DIR))


class CentralAgentBootstrapTests(unittest.TestCase):
    def test_module_imports(self):
        module = importlib.import_module("app.main")
        self.assertTrue(hasattr(module, "app"))

    def test_health_endpoint(self):
        module = importlib.import_module("app.main")
        response = module.health()
        self.assertEqual(response["status"], "healthy")
        self.assertEqual(response["service"], "central-agent")
