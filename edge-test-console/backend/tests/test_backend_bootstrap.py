import importlib
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


class BackendBootstrapTests(unittest.TestCase):
    def tearDown(self):
        sys.modules.pop("app.main", None)

    def test_backend_module_imports_without_shared_package(self):
        with patch("pathlib.Path.mkdir", return_value=None):
            module = importlib.import_module("app.main")

        self.assertTrue(hasattr(module, "logger"))

    def test_resolve_demo_samples_dir_falls_back_to_container_path(self):
        with patch("pathlib.Path.mkdir", return_value=None):
            module = importlib.import_module("app.main")

        with patch.dict(os.environ, {}, clear=False):
            resolved = module.resolve_demo_samples_dir(Path("/app/app/main.py"))

        self.assertEqual(resolved, Path("/app/demo-samples"))
